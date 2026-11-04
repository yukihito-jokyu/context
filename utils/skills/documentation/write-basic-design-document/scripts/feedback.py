#!/usr/bin/env python3
"""Keep user feedback, immutable output versions and explicit approval in one format.

The shared runtime copies this file into every generated skill. Hooks record actual
user messages; the assistant classifies their meaning with feedback/ignore. Approval
is submitted from the before/after review page and identifies its exact revision.
There is no CLI command to mark a correction user-approved.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
import datetime
import fcntl
import hashlib
import json
import mimetypes
import os
from pathlib import Path
import re
import sys
import tempfile
import uuid

import _skillrt as rt

SCHEMA_VERSION = 1
DIRECTORY = ".skill-feedback"


class FeedbackError(ValueError):
    pass


def ident(prefix: str) -> str:
    return prefix + "-" + uuid.uuid4().hex


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def directory(root: Path, name: str) -> Path:
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]*", name):
        raise FeedbackError("Invalid skill name")
    base = root.resolve() / DIRECTORY
    if base.is_symlink() or (base / name).is_symlink():
        raise FeedbackError("Feedback storage must be a local directory")
    return base / name


def atomic_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=".write-", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(value, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


@contextmanager
def locked(root: Path, name: str):
    base = directory(root, name)
    base.mkdir(parents=True, exist_ok=True)
    ignored = base.parent / ".gitignore"
    if not ignored.exists():
        ignored.write_text("*\n", encoding="utf-8")
    with (base / ".lock").open("a+") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        path = base / "feedback.json"
        data = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {
            "schema_version": SCHEMA_VERSION, "skill": name,
            "messages": [], "deliveries": [], "cases": []}
        if data.get("schema_version") != SCHEMA_VERSION or data.get("skill") != name:
            raise FeedbackError("Unsupported feedback format or skill identity")
        yield base, data
        atomic_json(path, data)


def put_blob(base: Path, content: bytes) -> dict:
    key = digest(content)
    path = base / "objects" / key
    if path.parent.is_symlink():
        raise FeedbackError("Feedback objects must be stored locally")
    path.parent.mkdir(exist_ok=True)
    if path.is_symlink():
        raise FeedbackError("Invalid feedback object")
    if not path.exists():
        path.write_bytes(content)
    if digest(path.read_bytes()) != key:
        raise FeedbackError("Feedback object was changed: " + key)
    return {"sha256": key, "object": "objects/" + key, "size": len(content)}


def blob(base: Path, item: dict) -> bytes:
    key = item.get("sha256", "")
    if not re.fullmatch(r"[a-f0-9]{64}", key) or item.get("object") != "objects/" + key:
        raise FeedbackError("Invalid feedback object reference")
    path = base / "objects" / key
    if path.is_symlink() or not path.is_file():
        raise FeedbackError("Missing feedback object: " + key)
    value = path.read_bytes()
    if digest(value) != key or len(value) != item.get("size"):
        raise FeedbackError("Feedback object content does not match its reference")
    return value


def artifact(base: Path, root: Path, rel: str, output: str = "") -> dict:
    path = root / rel
    if path.is_symlink() or not path.resolve().is_relative_to(root.resolve()) or not path.is_file():
        raise FeedbackError("Output is missing or outside the project: " + rel)
    return {"path": rel, "output": output,
            "media_type": mimetypes.guess_type(rel)[0] or "application/octet-stream",
            **put_blob(base, path.read_bytes())}


def output_files(root: Path, state: dict, contract: dict) -> dict[str, str]:
    result = {}
    for output in contract.get("outputs", []):
        for rel in rt.iter_glob(root, rt.expand(output["path"], state["skill"], state.get("input"))):
            result[rel] = output["id"]
    return result


def source_version(base: Path, skill: Path) -> dict:
    files = []
    for path in sorted(skill.rglob("*")):
        rel = path.relative_to(skill)
        if (not path.is_file() or path.is_symlink() or any(part in {
                ".git", "__pycache__", ".skill-runs", DIRECTORY, "node_modules"} for part in rel.parts)
                or rel.parts[:2] == ("dev", "results")
                or path.suffix == ".pyc" or path.name == "user-setting.yaml"):
            continue
        files.append({"path": rel.as_posix(), **put_blob(base, path.read_bytes())})
    revision = digest(json.dumps([(f["path"], f["sha256"]) for f in files]).encode())
    return {"name": skill.name, "revision": revision, "files": files}


def same_session(item: dict, session: str) -> bool:
    return not item.get("session_id") or not session or item["session_id"] == session


def presented(root: Path, state: dict, contract: dict, validation: str = "unchecked") -> str | None:
    """Snapshot output bytes before the next user message or edit can replace them."""
    paths = output_files(root, state, contract)
    if not paths:
        return None
    with locked(root, state["skill"]) as (base, data):
        artifacts = [artifact(base, root, rel, output) for rel, output in sorted(paths.items())]
        session = state.get("session_id", "")
        origin = next((c for c in data["cases"] if c["id"] in state.get("feedback_case_ids", [])
                       and c["status"] == "pending"), None)
        current = next((d for d in reversed(data["deliveries"]) if same_session(d, session)), None)
        fingerprint = [(a["path"], a["sha256"]) for a in artifacts]
        if current and current["run_id"] == state.get("run_id", state["started_at"]) and [
                (a["path"], a["sha256"]) for a in current["artifacts"]] == fingerprint:
            return current["id"]
        delivery = {"id": ident("delivery"), "at": rt.now(),
                    "run_id": state.get("run_id", state["started_at"]), "session_id": session,
                    "request": origin["request"] if origin else state.get("text", ""),
                    "inputs": origin["inputs"] if origin else state.get("input", {}),
                    "correction_request": state.get("text", "") if origin else None,
                    "skill": source_version(base, rt.SKILL_DIR), "contract": contract,
                    "validation": validation, "artifacts": artifacts,
                    "context": state.get("feedback_context", [])}
        data["deliveries"].append(delivery)
        for case in data["cases"]:
            if case["id"] in state.get("feedback_case_ids", []) and case["status"] == "pending":
                if delivery["id"] not in case["revisions"]:
                    case["revisions"].append(delivery["id"])
        return delivery["id"]


def runtime(data: dict, state: dict) -> dict:
    """Extension metadata belongs to the collector, never to the skill's state."""
    key = state.get("run_id", state["started_at"])
    entries = data.setdefault("runtime", {})
    if key not in entries:
        entries[key] = {"run_id": key, "session_id": "", "feedback_case_ids": [], "feedback_context": []}
    return entries[key]


def bind_session(root: Path, state: dict, event: dict) -> bool:
    session = str(event.get("session_id") or "")
    with locked(root, state["skill"]) as (_, data):
        meta = runtime(data, state)
        if meta["session_id"] and session and meta["session_id"] != session:
            return False
        if session and not meta["session_id"]:
            meta["session_id"] = session
        latest = data["messages"][-1] if data["messages"] else None
        if latest and latest.get("kind") == "feedback" and not meta["feedback_case_ids"] and same_session(meta, latest["session_id"]):
            meta["session_id"] = latest["session_id"]
            meta["feedback_case_ids"] = latest.get("case_ids", [])
        state.update(meta)
    return True


def activation_context(root: Path, state: dict) -> str:
    """Only a hook supplies the optional extension's instructions to the model."""
    with locked(root, state["skill"]) as (_, data):
        meta = runtime(data, state)
        if meta.get("instructed") or state.get("status") != "active":
            return ""
        meta["instructed"] = True
    command = "python3 " + rt.shell_quote(str(rt.SKILL_DIR / "scripts/feedback.py"))
    return ("指摘収集hooksが有効です。再現に必要な入力ファイルを使うときは、変更する前に "
            f"`{command} context --file <入力ファイル>` で内容を保存してください。"
            "成果物への指摘の分類と修正前後の確認画面は、後続のhooksの案内に従ってください。"
            "収集は追加機能です。収集処理の失敗や承認待ちを理由に、スキル本来の成果物の作成を止めないでください。"
            f"詳しい操作方法は {rt.SKILL_DIR / 'references/feedback.md'} にあります。")


def delivery_by_id(data: dict, ident_: str) -> dict:
    found = next((d for d in data["deliveries"] if d["id"] == ident_), None)
    if found is None:
        raise FeedbackError("Unknown output revision")
    return found


def message_by_id(data: dict, ident_: str) -> dict:
    found = next((m for m in data["messages"] if m["id"] == ident_), None)
    if found is None:
        raise FeedbackError("Use a message recorded by UserPromptSubmit")
    return found


def approve_record(root: Path, state: dict, contract: dict, base: Path, data: dict, message: dict) -> list[str]:
    if message.get("source") != "review-ui" or message.get("action") != "approve":
        raise FeedbackError("Approval must be submitted from the before/after review page")
    delivery = delivery_by_id(data, message["delivery"])
    if not same_session(delivery, message["session_id"]):
        raise FeedbackError("Approval belongs to a different session")
    actual = rt.snapshot(root, contract, state["skill"], state.get("input"))
    if actual != {a["path"]: a["sha256"] for a in delivery["artifacts"]}:
        raise FeedbackError("Outputs changed since the revision shown to the user; show the new revision first")
    findings, _ = rt.check_outputs(root, state, contract)
    if findings or actual != rt.snapshot(root, contract, state["skill"], state.get("input")):
        raise FeedbackError("The approved revision must pass output checks without further changes")
    cases = [c for c in data["cases"] if c["id"] == message.get("case_id") and c["status"] == "pending"
             and c["session_id"] == message["session_id"] and c["revisions"]
             and message["delivery"] == c["revisions"][-1]]
    if not cases:
        raise FeedbackError("No feedback case has this presented revision")
    for case in cases:
        for item in delivery["artifacts"]:
            blob(base, item)
        case.update(status="approved", after=delivery["id"], approval={
            "message_id": message["id"], "text": message["text"], "at": message["at"],
            "delivery": delivery["id"], "source": "review-ui"})
    message["kind"] = "approval"
    return [c["id"] for c in cases]


def observe_prompt(root: Path, state: dict, contract: dict, event: dict, platform: str) -> str:
    raw = event.get("prompt") or event.get("user_prompt")
    if not isinstance(raw, str) or not raw.strip():
        return ""
    session = str(event.get("session_id") or state.get("session_id") or "")
    base = directory(root, state["skill"])
    if not (base / "feedback.json").exists():
        presented(root, state, contract)
        if not (base / "feedback.json").exists():
            return ""
    with locked(root, state["skill"]) as (base, data):
        delivery = next((d for d in reversed(data["deliveries"]) if same_session(d, session)), None)
        if delivery is None:
            return ""
        event_id = str(event.get("prompt_id") or event.get("turn_id") or "")
        if event_id and any(m.get("event_id") == event_id and m["session_id"] == session for m in data["messages"]):
            return ""
        latest = data["messages"][-1] if data["messages"] else None
        if not event_id and latest and (latest["text"], latest["session_id"], latest["delivery"]) == (raw, session, delivery["id"]):
            age = datetime.datetime.fromisoformat(rt.now()) - datetime.datetime.fromisoformat(latest["at"])
            if age.total_seconds() < 2:
                return ""
        message = {"id": ident("message"), "event_id": event_id, "at": rt.now(), "platform": platform,
                   "session_id": session, "text": raw, "delivery": delivery["id"], "kind": "unclassified",
                   "source": "UserPromptSubmit"}
        data["messages"].append(message)
        command = "python3 " + rt.shell_quote(str(rt.SKILL_DIR / "scripts/feedback.py"))
        return (f"成果物の提示後のユーザー発言を {message['id']} に原文と修正前の版を保存しました。成果物への指摘なら、編集前に "
                f"`{command} feedback --event {message['id']}` を実行してください。"
                f"無関係な発言なら `feedback.py ignore --event {message['id']} --reason <理由>` で分類してください。"
                "承認は feedback.py review の修正前後の確認画面で受け取ります。会話から承認済みにしないでください。AI は承認ボタンを操作せず、承認 API へ送信しないでください。")


def classify(root: Path, state: dict, contract: dict, event_id: str, kind: str, summary: str = "") -> str:
    with locked(root, state["skill"]) as (base, data):
        message = message_by_id(data, event_id)
        if message["kind"] not in ("unclassified", kind):
            raise FeedbackError("Message has already been classified")
        if kind == "ignore":
            if not summary.strip():
                raise FeedbackError("A reason is required")
            message.update(kind="ignore", reason=summary)
            return message["id"]
        existing = next((c for c in data["cases"] if c["issue"]["message_id"] == event_id), None)
        if existing:
            return existing["id"]
        before = delivery_by_id(data, message["delivery"])
        case = {"schema_version": SCHEMA_VERSION, "id": ident("feedback"), "status": "pending",
                "session_id": message["session_id"], "skill": before["skill"],
                "request": before["request"], "inputs": before["inputs"], "context": before["context"],
                "issue": {"message_id": message["id"], "text": message["text"], "summary": summary,
                          "at": message["at"]}, "before": before["id"], "revisions": [], "after": None, "approval": None}
        data["cases"].append(case)
        message["kind"] = "feedback"
        chained = [c["id"] for c in data["cases"] if c["status"] == "pending"
                   and c["session_id"] == message["session_id"] and c["revisions"]
                   and c["revisions"][-1] == before["id"]]
        message["case_ids"] = [*chained, case["id"]]
        # A correction can continue the completed run or start a new run.
        runtime(data, state).update(feedback_case_ids=message["case_ids"], session_id=message["session_id"])
        return case["id"]


def validate(base: Path, data: dict) -> None:
    if data.get("schema_version") != SCHEMA_VERSION:
        raise FeedbackError("Unsupported schema version")
    for key in ("messages", "deliveries", "cases"):
        if not isinstance(data.get(key), list) or len({x["id"] for x in data[key]}) != len(data[key]):
            raise FeedbackError("Invalid or duplicate records in " + key)
    for delivery in data["deliveries"]:
        for item in delivery["artifacts"] + delivery["context"] + delivery["skill"]["files"]:
            blob(base, item)
        version = delivery["skill"]
        if version.get("name") != data["skill"]:
            raise FeedbackError("A different skill's feedback cannot be mixed into this corpus")
        if version["revision"] != digest(json.dumps([(f["path"], f["sha256"]) for f in version["files"]]).encode()):
            raise FeedbackError("Skill revision does not match the stored files")
    for case in data["cases"]:
        if case.get("schema_version") != SCHEMA_VERSION or case.get("status") not in ("pending", "approved"):
            raise FeedbackError("Invalid feedback case")
        before = delivery_by_id(data, case["before"])
        message = message_by_id(data, case["issue"]["message_id"])
        if (case["issue"]["text"] != message["text"] or before["id"] != message["delivery"]
                or message["kind"] != "feedback" or case["skill"] != before["skill"]):
            raise FeedbackError("Feedback no longer matches the observed user message")
        if case["status"] == "approved":
            approval = case.get("approval") or {}
            message = message_by_id(data, approval.get("message_id"))
            if (message.get("source") != "review-ui" or message.get("action") != "approve" or approval.get("text") != message["text"]
                    or case["after"] != message["delivery"] or case["after"] not in case["revisions"]
                    or message["session_id"] != case["session_id"] or message["kind"] != "approval"
                    or approval.get("source") != "review-ui" or approval.get("delivery") != case["after"]
                    or message.get("case_id") != case["id"]):
                raise FeedbackError("Approval does not identify the actual approved revision")
            delivery_by_id(data, case["after"])
        elif case.get("after") is not None or case.get("approval") is not None:
            raise FeedbackError("Pending cases cannot contain approval")


def export(root: Path, name: str, output: Path) -> dict:
    if output.exists():
        raise FeedbackError("Choose a new export directory")
    with locked(root, name) as (base, data):
        validate(base, data)
        cases = [c for c in data["cases"] if c["status"] == "approved"]
        if not cases:
            raise FeedbackError("No user-approved corrections are available")
        deliveries = {key for c in cases for key in [c["before"], c["after"], *c["revisions"]]}
        messages = {m for c in cases for m in (c["issue"]["message_id"], c["approval"]["message_id"])}
        exported = {"schema_version": SCHEMA_VERSION, "skill": name, "cases": cases,
                    "messages": [m for m in data["messages"] if m["id"] in messages],
                    "deliveries": [d for d in data["deliveries"] if d["id"] in deliveries]}
        output.mkdir(parents=True)
        for delivery in exported["deliveries"]:
            for item in delivery["artifacts"] + delivery["context"] + delivery["skill"]["files"]:
                put_blob(output, blob(base, item))
        atomic_json(output / "feedback.json", exported)
        return exported


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", type=Path)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("status")
    sub.add_parser("validate")
    for kind in ("feedback", "ignore"):
        p = sub.add_parser(kind)
        p.add_argument("--event", required=True)
        p.add_argument("--summary" if kind == "feedback" else "--reason", default="")
    p = sub.add_parser("context")
    p.add_argument("--file", action="append", required=True)
    p = sub.add_parser("export")
    p.add_argument("--out", type=Path, required=True)
    p = sub.add_parser("review")
    p.add_argument("--port", type=int, default=0)
    args = parser.parse_args()
    root = args.project.resolve() if args.project else rt.project_root(Path.cwd())
    contract = rt.load_contract()
    name = contract["skill"]
    state = rt.load_state(root, name)
    if state is None:
        raise FeedbackError("Start the skill before collecting feedback")
    bind_session(root, state, {})
    if args.command == "review":
        import feedback_review
        feedback_review.serve(root, contract, args.port)
    elif args.command in ("feedback", "ignore"):
        print(classify(root, state, contract, args.event,
                       args.command,
                       getattr(args, "summary", "") or getattr(args, "reason", "")))
    elif args.command == "context":
        if state["status"] != "active":
            raise FeedbackError("Record input context before finishing the run")
        with locked(root, name) as (base, data):
            inputs = {}
            for given in args.file:
                path = Path(given)
                path = (root / path).resolve() if not path.is_absolute() else path.resolve()
                if not path.is_relative_to(root):
                    raise FeedbackError("Context must be inside the project")
                rel = path.relative_to(root).as_posix()
                inputs[rel] = artifact(base, root, rel)
            meta = runtime(data, state)
            previous = {item["path"]: item for item in meta["feedback_context"]}
            meta["feedback_context"] = list({**previous, **inputs}.values())
        print("Input files recorded")
    elif args.command == "export":
        data = export(root, name, args.out.resolve())
        print(f"Exported {len(data['cases'])} approved feedback cases to {args.out}")
    else:
        with locked(root, name) as (base, data):
            if args.command == "validate":
                validate(base, data)
                print("Feedback records and stored content are valid")
            else:
                print(json.dumps({"storage": str(base), "cases": [{k: c[k] for k in
                                 ("id", "status", "issue", "before", "revisions", "after", "approval")} for c in data["cases"]],
                                  "unclassified": [m for m in data["messages"] if m["kind"] == "unclassified"]},
                                 ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (FeedbackError, OSError, KeyError, json.JSONDecodeError) as exc:
        print("ERROR feedback: " + str(exc), file=sys.stderr)
        sys.exit(1)
