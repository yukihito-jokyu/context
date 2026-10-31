#!/usr/bin/env python3
"""Claude Code と Codex の hooks から呼ばれ、実行中のスキルの出力を検査する。skill-foundation の共通ランタイム。

出力の検査は status: active のときに働く。成果物の保存とユーザーの指摘・承認の収集は完了後も働く。
スキル自身のファイルは編集でき、変更後に特別な手続きは不要。

  pre-tool   編集の前: 実行記録への直接の編集を止める
  post-tool  編集の後: 契約の出力に当たるファイルを format で直し、検査し、指摘を AI に返す
  stop       応答を終える前: 出力全体を検査し、通っていなければ終わらせずに直させる（回数に上限あり）
  prompt     ユーザーの発言: 指摘と承認の原文を保存し、質問待ちを解く。発言を止めたり書き換えたりしない

製品ごとの違い（stdin の形、編集ツールの名前、返し方）はここで吸収する。
  Claude Code: 編集は Edit/Write/MultiEdit/NotebookEdit の tool_input.file_path。止めるのは permissionDecision
  Codex      : 編集は apply_patch の tool_input.command（パッチ本文）。ask は使えないので deny

使い方（設定ファイルから呼ぶ）:
  python3 <skill>/scripts/hook.py --platform claude|codex pre-tool|post-tool|stop|prompt
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _skillrt as rt  # noqa: E402

PATCH_FILE = re.compile(r"^\*\*\* (?:Add File|Update File|Delete File|Move to):\s*(.+?)\s*$", re.M)
EDIT_TOOLS = {"Edit", "Write", "MultiEdit", "NotebookEdit", "apply_patch"}


def read_event() -> dict:
    try:
        data = json.loads(sys.stdin.read() or "{}")
        return data if isinstance(data, dict) else {}
    except (json.JSONDecodeError, UnicodeDecodeError):
        return {}


def detect_platform(event: dict) -> str:
    if "turn_id" in event or event.get("tool_name") == "apply_patch":
        return "codex"
    return "claude"


def edited_paths(event: dict, base: Path) -> list[Path]:
    """ツール呼び出しが書き換えるファイルの絶対パス。Codex の apply_patch はパッチ本文から読む。"""
    if event.get("tool_name") not in EDIT_TOOLS:
        return []
    tool_input = event.get("tool_input") or {}
    raw = []
    if isinstance(tool_input, dict):
        for key in ("file_path", "notebook_path", "path"):
            if tool_input.get(key):
                raw.append(str(tool_input[key]))
        if event.get("tool_name") == "apply_patch":
            raw += PATCH_FILE.findall(str(tool_input.get("command") or tool_input.get("patch") or tool_input.get("input") or ""))
    elif isinstance(tool_input, str):
        raw += PATCH_FILE.findall(tool_input)
    paths = []
    for item in raw:
        path = Path(item)
        paths.append((path if path.is_absolute() else base / path).resolve())
    return paths


def relative(path: Path, base: Path) -> str | None:
    try:
        return path.relative_to(base.resolve()).as_posix()
    except ValueError:
        return None


def feedback(reason: str) -> int:
    rt.emit(json.dumps({"decision": "block", "reason": reason}, ensure_ascii=False))
    return 0


def pre_tool(event: dict, platform: str, root: Path, state: dict, contract: dict) -> int:
    name = state["skill"]
    for path in edited_paths(event, Path(event.get("cwd") or root)):
        in_root = relative(path, root)
        if in_root is not None and in_root.startswith(f".skill-feedback/{name}/"):
            rt.emit(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny",
                                "permissionDecisionReason": "指摘・承認の記録は feedback.py が管理します。直接編集しないでください。"}},
                               ensure_ascii=False))
            return 0
        if in_root is not None and in_root.startswith(rt.run_rel(name) + "/") and \
                Path(in_root).name in ("state.json", "report.md"):
            rt.emit(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny",
                                                       "permissionDecisionReason": f"{in_root} は run.py だけが書きます。手で編集しないでください。"}},
                               ensure_ascii=False))
            return 0
    return 0


def post_tool(event: dict, root: Path, state: dict, contract: dict) -> int:
    findings, fixes = [], []
    for path in edited_paths(event, Path(event.get("cwd") or root)):
        rel = relative(path, root)
        if rel is None or not path.is_file():
            continue
        found, _ = rt.check_outputs(root, state, contract, only=rel, fixes=fixes)
        findings += found
    if fixes:
        rt.record_fixes(state, fixes)
        rt.save_state(root, state)
    if not findings and not fixes:
        return 0
    lines = [rt.format_fix(f) for f in fixes] + [f["message"] if f.get("raw") else rt.format_finding(f) for f in findings]
    head = (f"{state['skill']} の出力の契約に合っていません。ルールIDを SKILL.md の「4. ルール」で引いて直してください" if findings else
            f"{state['skill']} の出力を契約の format で自動で直しました。編集を続ける前にファイルを読み直してください")
    return feedback(head + ":\n" + "\n".join(lines))


def stop(event: dict, root: Path, state: dict, contract: dict) -> int:
    name = state["skill"]
    if event.get("background_tasks"):
        return 0  # バックグラウンドの作業を待って応答を終えるときは止めない（終われば再開される）
    limit = int(contract.get("control", {}).get("max_stop_blocks", 3))
    fixes: list = []
    findings, _ = rt.check_outputs(root, state, contract, fixes=fixes)
    rt.record_fixes(state, fixes)
    run_py = f"python3 {rt.SKILL_DIR}/scripts/run.py"
    if not findings:
        reason = (f"{name} の出力は検査に通っています。`{run_py} finish` を実行し、その本文で最終の返答をしてください。")
    else:
        lines = [f["message"] if f.get("raw") else rt.format_finding(f) for f in findings]
        reason = (f"{name} の出力に、まだ指摘が {len(findings)} 件あります。直してから `{run_py} finish` を実行してください。"
                  f"ユーザーに質問が必要なら、先に `{run_py} wait --question <質問>` を実行してから質問してください。\n"
                  + "\n".join(lines[:30]))
    if state.get("stop_blocks", 0) >= limit:
        state["status"] = "failed"
        rt.log_event(state, "stop-released", f"{len(findings)} 件")
        rt.save_state(root, state)
        rt.emit(json.dumps({"systemMessage": f"{name}: 検査を通らないまま終了しました（終了の差し戻し {limit} 回で打ち切り）。"
                                             f"指摘 {len(findings)} 件。.skill-runs/{name}/state.json を確認してください。"},
                           ensure_ascii=False))
        return 0
    state["stop_blocks"] = state.get("stop_blocks", 0) + 1
    rt.log_event(state, "stop-blocked", f"{len(findings)} 件")
    rt.save_state(root, state)
    return feedback(reason)


def collect(action: str, event: dict, platform: str, root: Path, state: dict, contract: dict) -> tuple[bool, str]:
    """The optional collector cannot prevent normal output checks or completion."""
    try:
        import feedback as fb
        extension = dict(state)
        if not fb.bind_session(root, extension, event):
            return False, ""
        if action == "prompt":
            return True, fb.observe_prompt(root, extension, contract, event, platform)
        if action == "stop" and state.get("status") in ("done", "waiting", "aborted", "failed"):
            fb.presented(root, extension, contract, validation="passed" if state["status"] == "done" else "unchecked")
        if action in ("pre-tool", "post-tool") and event.get("tool_name") not in EDIT_TOOLS:
            return True, fb.activation_context(root, extension)
    except Exception as exc:
        print(f"Feedback collection skipped: {exc}", file=sys.stderr)
    return True, ""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--platform", choices=["claude", "codex"])
    parser.add_argument("event", choices=["pre-tool", "post-tool", "stop", "prompt"])
    args = parser.parse_args()
    event = read_event()
    platform = args.platform or detect_platform(event)
    base = event.get("cwd") or os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
    root = rt.project_root(Path(base))
    try:
        contract = rt.load_contract()
    except (OSError, json.JSONDecodeError):
        return 0  # 契約が読めないときは何もしない（hooks の失敗で利用者の作業を止めない）
    name = contract.get("skill") or rt.SKILL_DIR.name
    state = rt.load_state(root, name)
    if state is None:
        return 0
    matched, context = collect(args.event, event, platform, root, state, contract)
    if not matched:
        return 0
    if args.event == "prompt":
        if state.get("status") == "waiting":
            state["status"] = "active"
            rt.log_event(state, "resume", "user-prompt")
            rt.save_state(root, state)
        if context:
            rt.emit(json.dumps({"hookSpecificOutput": {"hookEventName": "UserPromptSubmit", "additionalContext": context}},
                               ensure_ascii=False))
        return 0
    if context:
        event_name = "PreToolUse" if args.event == "pre-tool" else "PostToolUse"
        rt.emit(json.dumps({"hookSpecificOutput": {"hookEventName": event_name, "additionalContext": context}}, ensure_ascii=False))
    if args.event == "pre-tool" and state.get("status") in ("done", "waiting"):
        # Feedback records stay owned by the collector after the generation run ends.
        return pre_tool(event, platform, root, state, contract)
    if state.get("status") not in rt.ENFORCING:
        return 0
    if args.event == "pre-tool":
        return pre_tool(event, platform, root, state, contract)
    if args.event == "post-tool":
        return post_tool(event, root, state, contract)
    return stop(event, root, state, contract)


if __name__ == "__main__":
    sys.exit(main())
