#!/usr/bin/env python3
"""スキルの実行を始め、出力を検査し、終える。skill-foundation の共通ランタイム（スキルごとに書き換えない）。

AI はスキルの手順の最初に start、出力を書いたら check、最後に finish を実行する。hooks が使える環境では、
編集の直後と応答を終える前に、hook.py が同じ検査を自動で回す。

  start   入力を正規化（表記ゆれ・全角・未知のキーを受け入れ、既定値で補う）し、実行記録を作る。依頼に無い入力は、
          settings/user-setting.yaml → settings/skill-setting.yaml → --guess → 契約の既定値の順に補う。
  check   契約（assets/contract.json）の format で出力を直してから検査する。--file でファイル1つだけ
  finish  検査に通れば実行を終え、報告の本文を出す。通らなければ指摘を出して終わらない
  wait    ユーザーへの質問を待つ間、hooks の強制を止める（返答の後に resume）
  resume  wait を解く
  abort   理由を付けて実行をやめ、中断の報告の本文を出す
  status  実行記録を表示する

終了コード: 0 成功、1 検査の指摘あり、2 使い方・状態の誤り、3 start の前にユーザーへの質問が必要

使い方:
  python3 <skill>/scripts/run.py start [--set key=value ...] [--guess key=value ...] [--input-json JSON] [--input-file F]
                                       [--restart] [依頼文...]
  python3 <skill>/scripts/run.py check [--file 相対パス]
  python3 <skill>/scripts/run.py finish
"""

from __future__ import annotations

import argparse
import json
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _skillrt as rt  # noqa: E402


def resolve_root(arg: str | None) -> Path:
    return Path(arg).resolve() if arg else rt.project_root(Path.cwd())


def require_state(root: Path, name: str) -> dict:
    state = rt.load_state(root, name)
    if state is None:
        rt.emit(f"ERROR 実行記録がありません（{rt.state_path(root, name)}）。先に start を実行してください", sys.stderr)
        sys.exit(2)
    return state


def parse_raw(args) -> tuple[dict, str]:
    raw: dict = {}
    text_parts = list(args.text or [])
    if args.input_file:
        content = Path(args.input_file).read_text(encoding="utf-8")
        try:
            loaded = json.loads(content)
            if isinstance(loaded, dict):
                raw.update(loaded)
            else:
                text_parts.append(content)
        except json.JSONDecodeError:
            text_parts.append(content)  # JSON でなければ自由記述として読む
    if args.input_json:
        try:
            loaded = json.loads(args.input_json)
            if isinstance(loaded, dict):
                raw.update(loaded)
            else:
                text_parts.append(args.input_json)
        except json.JSONDecodeError:
            text_parts.append(args.input_json)
    for item in args.set or []:
        key, sep, value = item.partition("=")
        if not sep:
            key, sep, value = item.partition(":")
        if sep:
            raw[key.strip()] = value.strip()
        else:
            text_parts.append(item)
    return raw, "\n".join(text_parts)


def parse_guess(args) -> dict:
    """--guess の値。依頼文から推した値で、設定より弱く、契約の既定値より強い。"""
    pairs = [item.partition("=") for item in args.guess or []]
    return {key.strip(): value.strip() for key, sep, value in pairs if sep}


def source_text(key: str, state: dict, contract: dict) -> str:
    """依頼に無かった入力を、どこから補ったか（ユーザーの設定・スキルの設定・推定・ほかの入力・既定値）。"""
    source = state.get("default_from", {}).get(key)
    if source is None:
        return ""
    by = next((i.get("default_by", {}) for i in contract.get("inputs", []) if i["key"] == key), {})
    return report_text(contract)["from"].get(source, source).replace("{input}", by.get("input", ""))


def cmd_start(args, contract: dict, name: str) -> int:
    root = resolve_root(args.root)
    existing = rt.load_state(root, name)
    if existing and existing.get("status") in ("active", "waiting") and not args.restart:
        rt.emit(f"ERROR {name} の実行が続いています（status: {existing['status']}）。"
                "続けるなら check / finish、最初からやり直すなら start --restart を実行してください", sys.stderr)
        return 2
    raw, text = parse_raw(args)
    settings, setting_warnings = rt.load_settings()
    normalized = rt.normalize_input(raw, text, contract, settings, parse_guess(args))
    normalized["warnings"] = setting_warnings + normalized["warnings"]
    if normalized["questions"]:
        rt.emit("start の前にユーザーに聞くこと（聞いた答えを --set で渡して start をやり直す）:")
        for q in normalized["questions"]:
            rt.emit(f"  - {q}")
        return 3
    state = {
        "runtime": rt.RUNTIME_VERSION, "skill": name, "status": "active", "started_at": rt.now(),
        "run_id": uuid.uuid4().hex,
        "root": str(root), "skill_dir": str(rt.SKILL_DIR), "input": normalized["values"],
        "defaulted": normalized["defaulted"], "default_from": normalized["default_from"],
        "warnings": normalized["warnings"], "extra": normalized["extra"],
        "text": normalized["text"], "baseline": rt.snapshot(root, contract, name, normalized["values"]),
        "stop_blocks": 0, "history": [], "restarts": 0, "previous": [],
    }
    if existing and existing.get("status") in ("active", "waiting"):
        # 出力の比較基準と実行履歴は、最初の start から引き継ぐ
        for key in ("started_at", "stop_blocks", "history", "previous", "run_id"):
            if key in existing:
                state[key] = existing[key]
        state["baseline"] = existing.get("baseline", {})
        state["restarts"] = existing.get("restarts", 0) + 1
    else:
        if existing and existing.get("status") in ("aborted", "failed"):
            # 中断や打ち切りの後に始め直しても、報告の「検証」に前の実行が残る
            reason = existing.get("abort_reason") or "検査を通らないまま終了した（終了の差し戻しの上限）"
            state["previous"] = existing.get("previous", []) + [{"status": existing["status"], "reason": reason,
                                                                 "started_at": existing.get("started_at")}]
    rt.log_event(state, "restart" if state["restarts"] else "start")
    rt.save_state(root, state)
    if args.json:
        rt.emit(json.dumps({k: state[k] for k in ("skill", "root", "skill_dir", "input", "defaulted", "default_from", "warnings",
                                                 "extra")},
                           ensure_ascii=False, indent=2))
        return 0
    labels = {s["key"]: s.get("label", s["key"]) for s in contract.get("inputs", [])}
    rt.emit(f"{name} を始めました。実行記録: {rt.state_path(root, name).relative_to(root)}")
    rt.emit(f"スキルのディレクトリ: {rt.SKILL_DIR}")
    rt.emit("入力（正規化の後）:")
    if not normalized["values"]:
        rt.emit("  なし")
    for key, value in normalized["values"].items():
        mark = f"（{source_text(key, state, contract)}）" if key in normalized["defaulted"] else ""
        rt.emit(f"  {labels.get(key, key)}（{key}）= {json.dumps(value, ensure_ascii=False)}{mark}")
    for warning in normalized["warnings"]:
        rt.emit(f"  注意: {warning}")
    if normalized["extra"]:
        rt.emit(f"  契約に無いので使わない指定: {', '.join(normalized['extra'])}")
    rt.emit("作る出力:")
    for out in contract.get("outputs", []):
        count = out.get("count", {})
        rt.emit(f"  {out['id']} {out.get('label', '')}: {rt.expand(out['path'], name, normalized['values'])}"
                f"（{count.get('min', 1 if out.get('required', True) else 0)}〜{count.get('max', '')} 件）")
    rt.emit("次: SKILL.md の手順に従って出力を書く。書いたら check、最後に finish を実行する")
    return 0


def print_findings(findings: list[dict]) -> None:
    for f in findings:
        rt.emit(f["message"] if f.get("raw") else rt.format_finding(f))


def cmd_check(args, contract: dict, name: str) -> int:
    root = resolve_root(args.root)
    state = require_state(root, name)
    if state.get("status") == "waiting":
        state["status"] = "active"
        rt.log_event(state, "resume", "check")
    only = Path(args.file).as_posix() if args.file else None
    if only and Path(only).is_absolute():
        only = Path(only).resolve().relative_to(root).as_posix()
    fixes: list = []
    findings, changed = rt.check_outputs(root, state, contract, only=only, fixes=fixes)
    rt.record_fixes(state, fixes)
    if not only and not findings:
        _, findings = rt.report_sections(root, state, contract, stage="check")  # finish で落ちないよう、報告の節もここで作ってみる
    rt.log_event(state, "check", f"{len(findings)} 件")
    rt.save_state(root, state)
    for f in fixes:
        rt.emit(rt.format_fix(f))
    print_findings(findings)
    if not only:
        for out_id, files in changed.items():
            rt.emit(f"出力 {out_id}: {', '.join(files) if files else 'なし'}")
    rt.emit(f"check: 指摘 {len(findings)} 件")
    return 1 if findings else 0


REPORT = {
    "ja": {"result": "結果", "done": "{name}: 完了（検証に合格）", "outputs": "出力", "defaults": "既定値で決めた値",
           "unread": "入力で読めなかった値", "checks": "検証", "none": "- なし", "passed": "- `run.py finish`: 指摘 0 件",
           "notes_head": "補足",
           "notes": "最終の返答は、次の本文をそのまま使う。前後に文を足さず、要約しない。",
           "aborted": "{name}: 中断（理由: {reason}）", "not_checked": "- 中断したため、検証していない",
           "restarts": "- `run.py start --restart`: {n} 回（実行履歴は最初の start から引き継いだ）",
           "previous": "- 前の実行: {status}（理由: {reason}）",
           "formatted": "- 自動で直した（format）: {items}",
           "from": {"user": "ユーザーの設定 settings/user-setting.yaml", "skill": "スキルの設定 settings/skill-setting.yaml",
                    "guess": "依頼文からの推定", "derived": "{input} から決まる既定値", "default": "既定値"}},
    "en": {"result": "Result", "done": "{name}: done (checks passed)", "outputs": "Outputs", "defaults": "Values decided by default",
           "unread": "Inputs that could not be read", "checks": "Checks", "none": "- None", "passed": "- `run.py finish`: 0 findings",
           "notes_head": "Notes",
           "notes": "Reply with the text below unchanged. Do not add text before or after it, and do not summarize it.",
           "aborted": "{name}: aborted (reason: {reason})", "not_checked": "- Not checked because the run was aborted",
           "restarts": "- `run.py start --restart`: {n} time(s) (run history was carried over from the first start)",
           "previous": "- Previous run: {status} (reason: {reason})",
           "formatted": "- Fixed automatically (format): {items}",
           "from": {"user": "user setting settings/user-setting.yaml", "skill": "skill setting settings/skill-setting.yaml",
                    "guess": "guessed from the request", "derived": "default from {input}", "default": "default"}},
}


def report_text(contract: dict) -> dict:
    return REPORT.get(contract.get("language"), REPORT["ja"])


def changed_outputs(root: Path, state: dict, contract: dict) -> dict:
    """出力ID → start の後に変わったファイル。検査はしない（abort の報告で使う）。"""
    values, baseline = state.get("input", {}), state.get("baseline", {})
    return {out["id"]: [rel for rel in rt.iter_glob(root, rt.expand(out["path"], state["skill"], values))
                        if baseline.get(rel) != rt.sha256(root / rel)] for out in contract.get("outputs", [])}


def render_report(state: dict, contract: dict, changed: dict, sections: list[str], notes: list[str],
                  aborted: str | None = None) -> str:
    """報告の本文。結果 → 契約の report.sections の出力 → 出力 → 既定値 → 読めなかった値 → 検証 → 補足 の順に固定する。
    aborted を渡すと中断の本文になる（結果の行と検証の行だけが変わる）。"""
    t = report_text(contract)
    labels = {s["key"]: s.get("label", s["key"]) for s in contract.get("inputs", [])}
    out_labels = {o["id"]: o.get("label", o["id"]) for o in contract.get("outputs", [])}
    result = (t["aborted"].replace("{reason}", aborted) if aborted is not None else t["done"]).replace("{name}", state["skill"])
    lines = [f"## {t['result']}", "", result, ""]
    for text in sections:
        lines += [text, ""]
    lines += [f"## {t['outputs']}", ""]
    files = [(out_id, rel) for out_id, rels in changed.items() for rel in rels]
    lines += [f"- `{rel}`（{out_id} {out_labels.get(out_id, '')}）" for out_id, rel in files] or [t["none"]]
    lines += ["", f"## {t['defaults']}", ""]
    lines += [f"- {labels.get(k, k)}（{k}）: {json.dumps(state['input'].get(k), ensure_ascii=False)}"
              + (f"（{source_text(k, state, contract)}）" if source_text(k, state, contract) else "")
              for k in state.get("defaulted", [])] or [t["none"]]
    lines += ["", f"## {t['unread']}", ""]
    lines += [f"- {w}" for w in state.get("warnings", [])] or [t["none"]]
    lines += ["", f"## {t['checks']}", "", t["not_checked"] if aborted is not None else t["passed"]]
    if state.get("formatted"):
        items = "、".join(f"{item.split(' ', 1)[0]} `{item.split(' ', 1)[1]}`" for item in state["formatted"][:10])
        lines.append(t["formatted"].replace("{items}", items))
    if state.get("restarts"):
        lines.append(t["restarts"].replace("{n}", str(state["restarts"])))
    for prev in state.get("previous", []):
        lines.append(t["previous"].replace("{status}", prev["status"]).replace("{reason}", prev["reason"]))
    lines += ["", f"## {t['notes_head']}", ""] + (notes or [t["none"]])
    return "\n".join(lines) + "\n"


def cmd_finish(args, contract: dict, name: str) -> int:
    root = resolve_root(args.root)
    state = require_state(root, name)
    if state.get("status") in ("done", "aborted"):
        rt.emit(f"ERROR この実行は既に {state['status']} です。新しく始めるなら start", sys.stderr)
        return 2
    fixes: list = []
    findings, changed = rt.check_outputs(root, state, contract, fixes=fixes)
    rt.record_fixes(state, fixes)
    sections = []
    if not findings:
        sections, findings = rt.report_sections(root, state, contract)
    if findings:
        state["status"] = "active"
        rt.log_event(state, "finish-rejected", f"{len(findings)} 件")
        rt.save_state(root, state)
        print_findings(findings)
        rt.emit(f"finish: 指摘 {len(findings)} 件。直してから、もう一度 finish を実行してください")
        return 1
    report = render_report(state, contract, changed, sections, rt.read_notes(root, name))
    include = contract.get("report", {}).get("include_output")
    body = ""
    if include and changed.get(include):
        body = "\n\n".join((root / rel).read_text(encoding="utf-8").rstrip() for rel in changed[include]) + "\n\n---\n\n"
    (root / rt.run_rel(name) / "report.md").write_text(body + report, encoding="utf-8")
    state["status"] = "done"
    state["finished_at"] = rt.now()
    state["outputs"] = changed
    rt.log_event(state, "finish")
    rt.save_state(root, state)
    rt.emit(report_text(contract)["notes"])
    rt.emit("=" * 40)
    rt.emit(body + report)
    return 0


def cmd_set_status(args, contract: dict, name: str, status: str, detail: str) -> int:
    root = resolve_root(args.root)
    state = require_state(root, name)
    if state.get("status") in ("done", "aborted"):
        rt.emit(f"ERROR この実行は既に {state['status']} です", sys.stderr)
        return 2
    state["status"] = status
    if status == "aborted":
        state["abort_reason"] = detail
        state["finished_at"] = rt.now()
        state["outputs"] = changed_outputs(root, state, contract)
    if status == "waiting":
        state["question"] = detail
    rt.log_event(state, status, detail)
    rt.save_state(root, state)
    if status == "aborted":
        # 中断の報告も finish と同じ固定の本文にする（RPT-01）。AI が手で書くと、理由や途中の出力が抜ける
        report = render_report(state, contract, state["outputs"], [], rt.read_notes(root, name), aborted=detail)
        (root / rt.run_rel(name) / "report.md").write_text(report, encoding="utf-8")
        rt.emit(report_text(contract)["notes"])
        rt.emit("=" * 40)
        rt.emit(report)
        return 0
    messages = {
        "waiting": "質問を待っています。ユーザーの返答を受けたら resume（または check）を実行してください",
        "active": "再開しました",
    }
    rt.emit(messages[status])
    return 0


def cmd_status(args, contract: dict, name: str) -> int:
    root = resolve_root(args.root)
    state = rt.load_state(root, name)
    if state is None:
        rt.emit(f"{name}: 実行記録なし")
        return 0
    shown = {k: state.get(k) for k in ("skill", "status", "started_at", "finished_at", "input", "defaulted",
                                        "warnings", "stop_blocks", "restarts", "previous", "question", "abort_reason")
             if state.get(k) is not None}
    rt.emit(json.dumps(shown, ensure_ascii=False, indent=2))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("start", help="入力を正規化して実行を始める")
    p.add_argument("text", nargs="*", help="依頼文（自由記述）。「キー: 値」の行も読む")
    p.add_argument("--set", action="append", metavar="KEY=VALUE")
    p.add_argument("--guess", action="append", metavar="KEY=VALUE", help="依頼文から推した値。設定（settings/）より弱く、既定値より強い")
    p.add_argument("--input-json")
    p.add_argument("--input-file")
    p.add_argument("--restart", action="store_true")
    p.add_argument("--json", action="store_true", help="結果を JSON で出す（スクリプトから呼ぶとき）")
    p = sub.add_parser("check", help="出力を契約で検査する")
    p.add_argument("--file")
    sub.add_parser("finish", help="検査に通れば実行を終え、報告の本文を出す")
    p = sub.add_parser("wait", help="ユーザーへの質問を待つ")
    p.add_argument("--question", required=True)
    sub.add_parser("resume", help="wait を解く")
    p = sub.add_parser("abort", help="理由を付けて実行をやめ、中断の報告の本文を出す")
    p.add_argument("--reason", required=True)
    sub.add_parser("status", help="実行記録を表示する")
    for action in sub.choices.values():
        action.add_argument("--root", help="プロジェクトのルート（既定: 作業ディレクトリから .git を辿った場所）")
    args = parser.parse_args()

    contract = rt.load_contract()
    name = contract.get("skill") or rt.SKILL_DIR.name
    if args.command == "start":
        return cmd_start(args, contract, name)
    if args.command == "check":
        return cmd_check(args, contract, name)
    if args.command == "finish":
        return cmd_finish(args, contract, name)
    if args.command == "wait":
        return cmd_set_status(args, contract, name, "waiting", args.question)
    if args.command == "resume":
        return cmd_set_status(args, contract, name, "active", "")
    if args.command == "abort":
        return cmd_set_status(args, contract, name, "aborted", args.reason)
    return cmd_status(args, contract, name)


if __name__ == "__main__":
    sys.exit(main())
