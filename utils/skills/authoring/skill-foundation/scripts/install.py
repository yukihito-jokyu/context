#!/usr/bin/env python3
"""このスキルを、Claude Code と Codex が見つける場所に置き、hooks を登録する。skill-foundation の共通ランタイム。

置き場所（プロジェクトのルートからの相対パス）:
  claude: .claude/skills/<name>   codex: .agents/skills/<name>
スキルの本体（このファイルの2つ上のディレクトリ）がどちらかにあれば、もう一方は本体への相対リンクにする
（--mode copy なら複製）。どちらにも無ければ、両方をリンクにする。

hooks（スキルの contract.json の control.hooks が true のとき）:
  Claude Code: .claude/settings.json の PreToolUse・PostToolUse（Edit|Write|MultiEdit|NotebookEdit）、Stop、UserPromptSubmit
  Codex      : .codex/hooks.json の PreToolUse・PostToolUse（apply_patch）、Stop、UserPromptSubmit
既にある設定は残し、このスキルの項目だけを足す（同じ項目があれば何もしない）。Codex は、足した hooks を
利用者が `/hooks` で信頼するまで実行しない。

機能（--features。既定は check,feedback）: check は出力の検査、feedback は利用中の指摘の収集（feedback.py）。
両方なら上の4つ、feedback だけなら PostToolUse を除く3つを登録する。契約の control.feedback が false なら
feedback は登録しない。既定の登録の文字列は機能を足す前と同じなので、Codex の信頼はそのまま使える。

--targets を省くと、契約（assets/contract.json）の targets、つまり作るときに決めた対象の製品だけに置く。
hooks は、そのうち契約の control.hook_targets（作るときに hooks の方針で選んだ製品。無ければ全部）にだけ登録する。

選んで登録するとき（書く前に差分を見せる）は setup.py を使う。setup.py は、ここの登録の処理をそのまま使う。

使い方:
  python3 <skill>/scripts/install.py --project <ルート> [--targets claude,codex] [--mode link|copy] [--no-hooks]
                                    [--no-feedback | --features check,feedback]
  python3 <skill>/scripts/install.py --project <ルート> --check       # 置き場所と hooks が揃っているか（もう一方の置き場が本体へのリンクかも。--mode copy なら複製でよい）
  python3 <skill>/scripts/install.py --project <ルート> --uninstall   # このスキルの置き場所と hooks を外す
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _skillrt as rt  # noqa: E402

PLACES = {"claude": ".claude/skills", "codex": ".agents/skills"}
CONFIGS = {"claude": ".claude/settings.json", "codex": ".codex/hooks.json"}
EVENTS = {
    "claude": [("PreToolUse", "Edit|Write|MultiEdit|NotebookEdit", "pre-tool", 30),
               ("PostToolUse", "Edit|Write|MultiEdit|NotebookEdit", "post-tool", 120),
               ("Stop", None, "stop", 300), ("UserPromptSubmit", None, "prompt", 10)],
    "codex": [("PreToolUse", "apply_patch", "pre-tool", 30), ("PostToolUse", "apply_patch", "post-tool", 120),
              ("Stop", None, "stop", 300), ("UserPromptSubmit", None, "prompt", 10)],
}
FEATURES = ["check", "feedback"]  # 出力の検査、利用中の指摘の収集
CHECK_ONLY = {"post-tool"}  # 収集だけのときは登録しないイベント


def hook_command(platform: str, name: str, event: str, features: set[str] | None = None) -> str:
    if platform == "claude":
        base = f'"$CLAUDE_PROJECT_DIR/{PLACES["claude"]}/{name}/scripts/hook.py"'
    else:  # Codex には CLAUDE_PROJECT_DIR が無い。hook はセッションの作業ディレクトリで動く
        base = f'"$(git rev-parse --show-toplevel 2>/dev/null || pwd)/{PLACES["codex"]}/{name}/scripts/hook.py"'
    features = set(FEATURES) if features is None else features
    flags = "".join(f" --no-{f}" for f in FEATURES if f not in features)
    return f"python3 {base} --platform {platform}{flags} {event}"


def is_ours(handler: dict, name: str) -> bool:
    return f"/{name}/scripts/hook.py" in str(handler.get("command", ""))


def load_config(path: Path) -> dict:
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8") or "{}")
    except json.JSONDecodeError as exc:
        rt.emit(f"ERROR {path} の JSON が不正です（{exc.lineno} 行目）。直してから実行してください", sys.stderr)
        sys.exit(2)
    return data if isinstance(data, dict) else {}


def wanted_entries(platform: str, name: str, features: set[str] | None = None) -> list[tuple[str, dict]]:
    features = set(FEATURES) if features is None else features
    entries = []
    for event, matcher, action, timeout in EVENTS[platform]:
        if not features or ("check" not in features and action in CHECK_ONLY):
            continue
        group = {"hooks": [{"type": "command", "command": hook_command(platform, name, action, features), "timeout": timeout}]}
        if matcher:
            group = {"matcher": matcher, **group}
        entries.append((event, group))
    return entries


def has_entry(groups: list, group: dict) -> bool:
    return any(g.get("matcher") == group.get("matcher") and any(h == group["hooks"][0] for h in g.get("hooks", []))
               for g in groups if isinstance(g, dict))


def registered(root: Path, platform: str, name: str) -> set[str] | None:
    """設定ファイルに今登録されている、このスキルの機能（登録の文字列の --no-<機能> から読む）。登録が無ければ None。"""
    found = None
    for groups in load_config(root / CONFIGS[platform]).get("hooks", {}).values():
        for group in groups if isinstance(groups, list) else []:
            for handler in group.get("hooks", []) if isinstance(group, dict) else []:
                if is_ours(handler, name):
                    found = (found or set()) | {f for f in FEATURES if f"--no-{f}" not in str(handler.get("command", ""))}
    return found


def config_text(data: dict) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2) + "\n"


def plan_hooks(root: Path, platform: str, name: str, remove: bool, features: set[str] | None = None) -> tuple[dict, list[str]]:
    """登録した後の設定ファイルの中身と、変わること。ファイルには書かない（setup.py が書く前の差分に使う）。"""
    data = load_config(root / CONFIGS[platform])
    hooks = data.setdefault("hooks", {})
    changes = []
    wanted = wanted_entries(platform, name, features)
    if remove or len(wanted) < len(EVENTS[platform]):
        # 外すとき、または機能を減らしたときは、要らなくなったイベントから自分の項目を外す
        keep = set() if remove else {event for event, _ in wanted}
        for event, groups in list(hooks.items()):
            if event in keep:
                continue
            kept = []
            for group in groups if isinstance(groups, list) else []:
                handlers = [h for h in group.get("hooks", []) if not is_ours(h, name)]
                if len(handlers) != len(group.get("hooks", [])):
                    changes.append(f"{CONFIGS[platform]}: {event} から {name} の hook を外す")
                if handlers:
                    kept.append({**group, "hooks": handlers})
            if kept:
                hooks[event] = kept
            else:
                hooks.pop(event)
    if not remove:
        for event, group in wanted:
            groups = hooks.setdefault(event, [])
            if not has_entry(groups, group):
                # 古い形の自分の項目は外してから足す（Codex の信頼は配列の位置に結び付くため、他人の項目は動かさない）
                for g in groups:
                    g["hooks"] = [h for h in g.get("hooks", []) if not is_ours(h, name)]
                groups[:] = [g for g in groups if g.get("hooks")]
                groups.append(group)
                changes.append(f"{CONFIGS[platform]}: {event} に {name} の hook を足す")
    if not hooks:
        data.pop("hooks", None)
    return data, changes


def apply_hooks(root: Path, platform: str, name: str, remove: bool, dry: bool, features: set[str] | None = None) -> list[str]:
    data, changes = plan_hooks(root, platform, name, remove, features)
    if changes and not dry:
        path = root / CONFIGS[platform]
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(config_text(data), encoding="utf-8")
    return changes


def place(root: Path, platform: str, name: str, mode: str, remove: bool, dry: bool) -> list[str]:
    target = root / PLACES[platform] / name
    body = rt.SKILL_DIR
    if target.resolve() == body and not target.is_symlink():
        return []  # 本体がここにある
    changes = []
    if remove:
        if target.is_symlink() or target.exists():
            changes.append(f"{target.relative_to(root)} を外す")
            if not dry:
                if target.is_symlink() or target.is_file():
                    target.unlink()
                else:
                    shutil.rmtree(target)
        return changes
    if target.is_symlink() and target.resolve() == body and mode == "link":
        return []
    if target.exists() or target.is_symlink():
        if target.is_symlink() or mode == "copy":
            changes.append(f"{target.relative_to(root)} を置き直す")
            if not dry:
                if target.is_symlink() or target.is_file():
                    target.unlink()
                else:
                    shutil.rmtree(target)
        else:
            rt.emit(f"ERROR {target} は本体ではないディレクトリとして既にあります。中身を確かめて、外してから実行してください", sys.stderr)
            sys.exit(2)
    changes.append(f"{target.relative_to(root)} を{'リンク' if mode == 'link' else '複製'}で置く")
    if not dry:
        target.parent.mkdir(parents=True, exist_ok=True)
        if mode == "link":
            target.symlink_to(os.path.relpath(body, target.parent), target_is_directory=True)
        else:
            shutil.copytree(body, target, ignore=shutil.ignore_patterns("__pycache__", ".skill-runs", "dev"))
    return changes


def check(root: Path, platforms: list[str], name: str, hooks_on: bool, mode: str, features: set[str] | None = None,
          hooked: list[str] | None = None) -> list[str]:
    problems, body = [], rt.SKILL_DIR
    for platform in platforms:
        target = root / PLACES[platform] / name
        if not (target / "SKILL.md").is_file():
            problems.append(f"{target.relative_to(root)}/SKILL.md がありません（{platform} がスキルを見つけられない）")
        elif target.resolve() != body and (target.is_symlink() or mode == "link"):
            what = "本体ではない場所へのリンク" if target.is_symlink() else "本体へのリンクではなく、別のディレクトリ（複製）"
            where = body.relative_to(root).as_posix() if body.is_relative_to(root) else body.as_posix()
            problems.append(f"{target.relative_to(root)} が{what}です（本体は {where}）。中身を確かめて外し、本体の install.py を実行し直す"
                            + ("" if target.is_symlink() else "。複製で置いたなら --mode copy を付けて確かめる"))
        if hooks_on and (hooked is None or platform in hooked):
            data = load_config(root / CONFIGS[platform])
            for event, group in wanted_entries(platform, name, features):
                if not has_entry(data.get("hooks", {}).get(event, []), group):
                    problems.append(f"{CONFIGS[platform]} の {event} に {name} の hook がありません")
    return problems


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--project", required=True, help="プロジェクトのルート")
    parser.add_argument("--targets", help="カンマ区切り（claude、codex）。省くと契約の targets（作るときに決めた対象の製品）")
    parser.add_argument("--mode", choices=["link", "copy"], default="link")
    parser.add_argument("--no-hooks", action="store_true", help="hooks を登録しない（収集も含めて何も登録しない）")
    parser.add_argument("--no-feedback", action="store_true", help="利用中の指摘の収集を外す（出力の検査だけ）")
    parser.add_argument("--features", help="カンマ区切り（check、feedback）。既定は両方")
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--uninstall", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    root = Path(args.project).resolve()
    contract = rt.load_contract()
    name = contract.get("skill") or rt.SKILL_DIR.name
    platforms = ([p.strip() for p in args.targets.split(",") if p.strip()] if args.targets
                 else contract.get("targets") or ["claude", "codex"])
    unknown = [p for p in platforms if p not in PLACES]
    if unknown:
        rt.emit(f"ERROR 未知の targets: {unknown}（claude、codex のどれか）", sys.stderr)
        return 2
    features = set(FEATURES) if not args.features else {f.strip() for f in args.features.split(",") if f.strip()}
    if features - set(FEATURES):
        rt.emit(f"ERROR 未知の features: {sorted(features - set(FEATURES))}（{'、'.join(FEATURES)} のどれか）", sys.stderr)
        return 2
    if args.no_feedback or contract.get("control", {}).get("feedback", True) is False:
        features.discard("feedback")
    hooks_on = contract.get("control", {}).get("hooks", True) and not args.no_hooks and bool(features)
    hooked = contract.get("control", {}).get("hook_targets", platforms)
    if args.check:
        problems = check(root, platforms, name, hooks_on, args.mode, features, hooked)
        for problem in problems:
            rt.emit(f"ERROR {problem}")
        rt.emit(f"install --check: 問題 {len(problems)} 件")
        return 1 if problems else 0
    changes = []
    for platform in platforms:
        changes += place(root, platform, name, args.mode, args.uninstall, args.dry_run)
        if (hooks_on and platform in hooked) or args.uninstall:
            changes += apply_hooks(root, platform, name, args.uninstall, args.dry_run, features)
    for change in changes:
        rt.emit(("予定  " if args.dry_run else "") + change)
    rt.emit(f"install: 変更 {len(changes)} 件")
    if "codex" in platforms and "codex" in hooked and hooks_on and not args.uninstall and any(".codex/hooks.json" in c for c in changes):
        rt.emit("注意: Codex は、足した hooks を利用者が Codex の `/hooks` で信頼するまで実行しない。"
                "信頼するまでは run.py の check と finish だけで検査される")
    return 0


if __name__ == "__main__":
    sys.exit(main())
