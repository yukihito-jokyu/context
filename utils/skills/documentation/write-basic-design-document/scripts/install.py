#!/usr/bin/env python3
"""このスキルを、Claude Code と Codex が見つける場所に置き、hooks を登録する。skill-foundation の共通ランタイム。

置き場所（プロジェクトのルートからの相対パス）:
  claude: .claude/skills/<name>   codex: .agents/skills/<name>
スキルの本体（このファイルの2つ上のディレクトリ）がどちらかにあれば、もう一方は本体への相対リンクにする
（--mode copy なら複製）。どちらにも無ければ、両方をリンクにする。

hooks（スキルの contract.json の control.hooks が true のとき）:
  Claude Code: .claude/settings.json の PreToolUse・PostToolUse（全ツール。編集時の検査は編集ツールだけ）、Stop、UserPromptSubmit
  Codex      : .codex/hooks.json の PreToolUse・PostToolUse（全ツール。編集時の検査は apply_patch だけ）、Stop、UserPromptSubmit
既にある設定は残し、このスキルの項目だけを足す（同じ項目があれば何もしない）。Codex は、足した hooks を
利用者が `/hooks` で信頼するまで実行しない。

--targets を省くと、契約（assets/contract.json）の targets、つまり作るときに決めた対象の製品だけに置く。

使い方:
  python3 <skill>/scripts/install.py --project <ルート> [--targets claude,codex] [--mode link|copy] [--no-hooks]
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
    "claude": [("PreToolUse", None, "pre-tool", 30),
               ("PostToolUse", None, "post-tool", 120),
               ("Stop", None, "stop", 300), ("UserPromptSubmit", None, "prompt", 10)],
    "codex": [("PreToolUse", None, "pre-tool", 30), ("PostToolUse", None, "post-tool", 120),
              ("Stop", None, "stop", 300), ("UserPromptSubmit", None, "prompt", 10)],
}


def hook_command(platform: str, name: str, event: str) -> str:
    if platform == "claude":
        base = f'"$CLAUDE_PROJECT_DIR/{PLACES["claude"]}/{name}/scripts/hook.py"'
    else:  # Codex には CLAUDE_PROJECT_DIR が無い。hook はセッションの作業ディレクトリで動く
        base = f'"$(git rev-parse --show-toplevel 2>/dev/null || pwd)/{PLACES["codex"]}/{name}/scripts/hook.py"'
    return f"python3 {base} --platform {platform} {event}"


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


def wanted_entries(platform: str, name: str) -> list[tuple[str, dict]]:
    entries = []
    for event, matcher, action, timeout in EVENTS[platform]:
        group = {"hooks": [{"type": "command", "command": hook_command(platform, name, action), "timeout": timeout}]}
        if matcher:
            group = {"matcher": matcher, **group}
        entries.append((event, group))
    return entries


def has_entry(groups: list, group: dict) -> bool:
    return any(g.get("matcher") == group.get("matcher") and any(h == group["hooks"][0] for h in g.get("hooks", []))
               for g in groups if isinstance(g, dict))


def apply_hooks(root: Path, platform: str, name: str, remove: bool, dry: bool) -> list[str]:
    path = root / CONFIGS[platform]
    data = load_config(path)
    hooks = data.setdefault("hooks", {})
    changes = []
    if remove:
        for event, groups in list(hooks.items()):
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
    else:
        for event, group in wanted_entries(platform, name):
            groups = hooks.setdefault(event, [])
            if not has_entry(groups, group):
                # 古い形の自分の項目は外してから足す（Codex の信頼は配列の位置に結び付くため、他人の項目は動かさない）
                for g in groups:
                    g["hooks"] = [h for h in g.get("hooks", []) if not is_ours(h, name)]
                groups[:] = [g for g in groups if g.get("hooks")]
                groups.append(group)
                changes.append(f"{CONFIGS[platform]}: {event} に {name} の hook を足す")
    if changes and not dry:
        if not hooks:
            data.pop("hooks", None)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
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


def check(root: Path, platforms: list[str], name: str, hooks_on: bool, mode: str) -> list[str]:
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
        if hooks_on:
            data = load_config(root / CONFIGS[platform])
            for event, group in wanted_entries(platform, name):
                if not has_entry(data.get("hooks", {}).get(event, []), group):
                    problems.append(f"{CONFIGS[platform]} の {event} に {name} の hook がありません")
    return problems


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--project", required=True, help="プロジェクトのルート")
    parser.add_argument("--targets", help="カンマ区切り（claude、codex）。省くと契約の targets（作るときに決めた対象の製品）")
    parser.add_argument("--mode", choices=["link", "copy"], default="link")
    parser.add_argument("--no-hooks", action="store_true", help="hooks を登録しない")
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
    hooks_on = contract.get("control", {}).get("hooks", True) and not args.no_hooks
    if args.check:
        problems = check(root, platforms, name, hooks_on, args.mode)
        for problem in problems:
            rt.emit(f"ERROR {problem}")
        rt.emit(f"install --check: 問題 {len(problems)} 件")
        return 1 if problems else 0
    changes = []
    for platform in platforms:
        changes += place(root, platform, name, args.mode, args.uninstall, args.dry_run)
        if hooks_on or args.uninstall:
            changes += apply_hooks(root, platform, name, args.uninstall, args.dry_run)
    for change in changes:
        rt.emit(("予定  " if args.dry_run else "") + change)
    rt.emit(f"install: 変更 {len(changes)} 件")
    if "codex" in platforms and hooks_on and not args.uninstall and any(".codex/hooks.json" in c for c in changes):
        rt.emit("注意: Codex は、足した hooks を利用者が Codex の `/hooks` で信頼するまで実行しない。"
                "信頼するまでは run.py の check と finish だけで検査される")
    return 0


if __name__ == "__main__":
    sys.exit(main())
