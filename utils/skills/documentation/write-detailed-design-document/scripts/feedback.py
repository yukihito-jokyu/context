#!/usr/bin/env python3
"""利用中の指摘・修正前後の成果物・ユーザーの承認を集める。skill-foundation の共通ランタイム（スキルごとに書き換えない）。

hooks の追加機能で、スキル本来の処理（run.py の start・check・finish）とは分けてある。SKILL.md からは呼ばない。
AI への案内は、hook.py が UserPromptSubmit の additionalContext で伝える。収集が失敗しても、本来の検査と完了は
止めない（hook.py が例外を握りつぶす）。仕組みは references/feedback.md。

記録の置き場: <プロジェクト>/.skill-feedback/<スキル名>/feedback.json と objects/<sha256>（成果物とスキルのファイルを
元のバイト列で保存する）。.skill-feedback/.gitignore で Git の管理から外す。記録は足すだけで、上書きしない。

hooks から（hook.py が呼ぶ）:
  stop        完了（done）で、提示した成果物とスキルの版を delivery に保存する（作成中の質問待ちは保存しない）。対応中の指摘が
              あれば、成果物が変わった版を修正版（revisions）に足す
  prompt      成果物を提示した後の発言の原文と、そのとき提示済みの版を記録し、分類の方法を AI に返す（発言は止めない）
  pre-tool    収集記録（.skill-feedback/）への編集ツールでの直接の編集を拒否する

AI が行う操作:
  feedback  発言（--event の message ID）を成果物への指摘として記録する。同じ版への対応中の指摘があれば、それに足す
  ignore    発言を無関係として記録する（原文は残す）
  context   再現に必要な入力ファイルを、変える前に保存する
  review    修正前後の確認画面（feedback_review.py）をバックグラウンドで起動し、URL を出す。承認はユーザーが画面のボタンで行う
  status    未分類の発言と、対応中・承認済みの指摘を出す
  validate  記録の形と、参照・実ファイルの整合を確かめる

改善に使う（skill-foundation の feedback_eval.py に渡す）:
  export    承認済みの指摘だけを、指摘の原文・承認・修正前と承認した版の実ファイル・入力ファイル・その時のスキルごと、
            新しいディレクトリに取り出す（dataset.json）。承認待ちの修正版は入れない。取り出した後に参照と内容を確かめる

使い方:
  python3 <skill>/scripts/feedback.py feedback --event m-0001 [--summary 要点]
  python3 <skill>/scripts/feedback.py ignore --event m-0001 --reason 理由
  python3 <skill>/scripts/feedback.py context --file 相対パス
  python3 <skill>/scripts/feedback.py review [--port 0]
  python3 <skill>/scripts/feedback.py status [--json] | validate
  python3 <skill>/scripts/feedback.py export --out <新しいディレクトリ>
"""

from __future__ import annotations

import argparse
import contextlib
import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _skillrt as rt  # noqa: E402

SCHEMA_VERSION = 1
DIRNAME = ".skill-feedback"
SCHEMA_REL = "assets/feedback.schema.json"
WINDOW = 3  # 成果物を提示した後、対応中の指摘が無いまま記録する発言の数（それより後の雑談は集めない）
SKILL_SKIP = {"dev", "__pycache__", ".DS_Store", ".skill-runs"}
PRIVATE = {"settings/user-setting.yaml", rt.SETTINGS_BACKUP_REL}  # 人ごとの設定とその写しはスキルの版に入れない
SYNTHETIC_ENV = "SKILL_FEEDBACK_SYNTHETIC"  # 合成データのテストで作った記録の印（実ユーザーの承認と区別する）
DATASET_KIND = "skill-feedback-dataset"  # export が書く dataset.json の印

TEXT = {
    "ja": {
        "guide": "[{skill} の利用中の指摘の収集] この発言（{mid}）は、{skill} の成果物（{did}: {files}）を提示した後のものです。"
                 "応答の前に、次のどちらかで分類してください。この記録はスキルの手順とは別の追加機能で、失敗しても作業を止めません。\n"
                 "- 成果物への指摘（違う・足りない・直してほしい など）なら、編集の前に: {py} feedback --event {mid} --summary \"<要点>\"\n"
                 "- 指摘でなければ: {py} ignore --event {mid} --reason \"<理由>\"\n"
                 "- 直すために読む入力ファイルは、変える前に: {py} context --file <パス>\n"
                 "- 直したら、応答の最後に {py} review を実行し、出た URL をユーザーに渡して、確認画面で確かめて承認するよう伝える\n"
                 "- 承認はユーザーが確認画面のボタンで行う。AI は承認ボタンを押さず、承認の URL に送信しない。会話の「OK」を承認として扱わない",
        "denied": "{rel} は利用中の指摘の記録で、feedback.py だけが書きます。手で編集しないでください。",
        "files_more": "ほか {n} 件",
    },
    "en": {
        "guide": "[{skill} feedback collection] This message ({mid}) came after {skill} presented its outputs ({did}: {files}). "
                 "Before replying, classify it with one of the commands below. This record is an add-on separate from the skill's steps; "
                 "if it fails, keep working.\n"
                 "- If it is feedback on the outputs (wrong, missing, please change), before editing: {py} feedback --event {mid} --summary \"<gist>\"\n"
                 "- If it is not feedback: {py} ignore --event {mid} --reason \"<reason>\"\n"
                 "- Before changing an input file you read to fix the outputs, save it: {py} context --file <path>\n"
                 "- After fixing, run {py} review at the end of your reply, give the user the URL, and ask them to check and approve on that page\n"
                 "- Only the user approves, with the button on the review page. Do not press the approve button or post to the approval URL. "
                 "An \"OK\" in the conversation is not an approval",
        "denied": "{rel} is the feedback record and only feedback.py writes it. Do not edit it by hand.",
        "files_more": "{n} more",
    },
}


# ---------------------------------------------------------------- 記録

def text(contract: dict) -> dict:
    return TEXT.get(contract.get("language"), TEXT["ja"])


def store_dir(root: Path, name: str) -> Path:
    return root / DIRNAME / name


def store_path(root: Path, name: str) -> Path:
    return store_dir(root, name) / "feedback.json"


def new_store(name: str) -> dict:
    return {"schema_version": SCHEMA_VERSION, "skill": name, "synthetic": os.environ.get(SYNTHETIC_ENV) == "1",
            "messages": [], "deliveries": [], "cases": [], "pending_inputs": []}


def load(root: Path, name: str) -> dict:
    path = store_path(root, name)
    if not path.is_file():
        return new_store(name)
    store = rt.load_json(path)
    if store.get("schema_version") != SCHEMA_VERSION:
        raise ValueError(f"{path}: schema_version {store.get('schema_version')} は読めません（{SCHEMA_VERSION} だけ）")
    return store


def save(root: Path, store: dict) -> None:
    ignore = root / DIRNAME / ".gitignore"
    if not ignore.exists():
        ignore.parent.mkdir(parents=True, exist_ok=True)
        ignore.write_text("*\n", encoding="utf-8")  # 利用者の .gitignore を変えずに、ローカルの記録を Git から外す
    rt.write_json(store_path(root, store["skill"]), store)


@contextlib.contextmanager
def locked(root: Path, name: str, wait: float = 10.0):
    """hooks と確認画面のサーバーが同時に書かないようにする。30 秒より古い印は、落ちた処理の残りとして消す。"""
    path = store_dir(root, name) / ".lock"
    path.parent.mkdir(parents=True, exist_ok=True)
    deadline = time.time() + wait
    while True:
        try:
            os.close(os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY))
            break
        except FileExistsError:
            try:
                if time.time() - path.stat().st_mtime > 30:
                    path.unlink()
                    continue
            except FileNotFoundError:
                continue
            if time.time() > deadline:
                raise TimeoutError(f"{path} が使われています")
            time.sleep(0.05)
    try:
        yield
    finally:
        with contextlib.suppress(FileNotFoundError):
            path.unlink()


def next_id(items: list, prefix: str) -> str:
    return f"{prefix}-{len(items) + 1:04d}"


def object_path(root: Path, name: str, sha: str) -> Path:
    return store_dir(root, name) / "objects" / sha


def put_object(root: Path, name: str, data: bytes) -> str:
    sha = hashlib.sha256(data).hexdigest()
    path = object_path(root, name, sha)
    if not path.is_file():
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_name(sha + ".tmp")
        tmp.write_bytes(data)
        tmp.replace(path)
    return sha


def is_text(data: bytes) -> bool:
    try:
        data.decode("utf-8")
        return b"\0" not in data
    except UnicodeDecodeError:
        return False


def file_entry(root: Path, name: str, rel: str, output: str | None = None, binary: bool = False) -> dict:
    """成果物1つ。実体を objects に保存する。無くなったファイルは sha256 を null にする。"""
    path = root / rel
    if not path.is_file():
        return {"path": rel, "sha256": None, "size": 0, "binary": binary, "output": output}
    data = path.read_bytes()
    return {"path": rel, "sha256": put_object(root, name, data), "size": len(data),
            "binary": binary or not is_text(data), "output": output}


def skill_version(root: Path, name: str, skill_dir: Path = rt.SKILL_DIR) -> dict:
    """スキルのファイル（dev/ と人ごとの設定を除く）を内容ごと保存し、一覧（manifest）のハッシュを版にする。"""
    files = {}
    for dirpath, dirnames, filenames in os.walk(skill_dir, followlinks=False):
        rel_dir = Path(dirpath).relative_to(skill_dir).as_posix()
        dirnames[:] = sorted(d for d in dirnames if d not in SKILL_SKIP and not (Path(dirpath) / d).is_symlink())
        for f in sorted(filenames):
            rel = f if rel_dir == "." else f"{rel_dir}/{f}"
            if f in SKILL_SKIP or rel in PRIVATE or (Path(dirpath) / f).is_symlink():
                continue
            files[rel] = put_object(root, name, (Path(dirpath) / f).read_bytes())
    manifest = json.dumps(files, ensure_ascii=False, sort_keys=True).encode("utf-8")
    sha = put_object(root, name, manifest)
    return {"version": sha, "manifest": sha, "contract": files.get(rt.CONTRACT_REL)}


def output_files(root: Path, state: dict, contract: dict) -> list[tuple[str, str, bool]]:
    """start の後に変わった契約の出力（相対パス, 出力ID, バイナリか）。"""
    values, baseline, name = state.get("input", {}), state.get("baseline", {}), state["skill"]
    found = []
    for out in contract.get("outputs", []):
        for rel in rt.iter_glob(root, rt.expand(out["path"], name, values)):
            if baseline.get(rel) != rt.sha256(root / rel):
                found.append((rel, out["id"], bool(out.get("binary"))))
    return found


def marker(state: dict) -> str:
    """提示の印。同じ完了を2回保存しない（Stop は応答のたびに呼ばれる）。"""
    return f"{state.get('started_at')}|done|{state.get('finished_at')}"


def add_delivery(store: dict, root: Path, state: dict | None, contract: dict, files: list[dict], trigger: str,
                 platform: str, session: str, mark: str) -> dict:
    name = store["skill"]
    run = (state or {}).get("started_at")
    inputs = [i for i in store["pending_inputs"] if i.get("run") == run]
    store["pending_inputs"] = [i for i in store["pending_inputs"] if i.get("run") != run]
    delivery = {"id": next_id(store["deliveries"], "d"), "at": rt.now(), "trigger": trigger, "platform": platform,
                "session": session, "marker": mark, "run": run, "request": (state or {}).get("text", ""),
                "input": (state or {}).get("input", {}), "extra": (state or {}).get("extra", {}),
                "input_files": [{k: v for k, v in i.items() if k != "run"} for i in inputs], "files": files,
                "skill": skill_version(root, name), "contract": contract.get("contract_version")}
    store["deliveries"].append(delivery)
    return delivery


def find(items: list, key: str) -> dict | None:
    return next((x for x in items if x["id"] == key), None)


def latest(store: dict, case: dict) -> dict:
    return find(store["deliveries"], case["revisions"][-1] if case["revisions"] else case["before"])


def open_cases(store: dict, session: str | None = None) -> list[dict]:
    return [c for c in store["cases"] if c["status"] == "open" and (session is None or c.get("session") == session)]


def hashes(delivery: dict) -> dict:
    return {f["path"]: f["sha256"] for f in delivery["files"]}


def revise(store: dict, root: Path, state: dict | None, contract: dict, platform: str, session: str | None) -> bool:
    """対応中の指摘の最新の版から成果物が変わっていれば、修正版として保存して指摘に足す。"""
    changed = False
    if state and state.get("status") in ("active", "waiting"):
        return False  # 実行中（質問待ちを含む）の変更は finish の後に1つの版として保存する
    outputs = {rel: (out, binary) for rel, out, binary in (output_files(root, state, contract) if state else [])}
    for case in open_cases(store, session):
        last = latest(store, case)
        paths = sorted(set(hashes(last)) | set(outputs))
        before = {f["path"]: f for f in last["files"]}
        current = {rel: rt.sha256(root / rel) if (root / rel).is_file() else None for rel in paths}
        if current == {rel: hashes(last).get(rel) for rel in paths}:
            continue
        files = [file_entry(root, store["skill"], rel, (before.get(rel) or {}).get("output") or outputs.get(rel, (None,))[0],
                            bool((before.get(rel) or {}).get("binary")) or outputs.get(rel, (None, False))[1]) for rel in paths]
        delivery = add_delivery(store, root, state, contract, files, "revision", platform, session or case.get("session", ""),
                                "revision|" + hashlib.sha256(json.dumps(current, sort_keys=True).encode()).hexdigest())
        for other in open_cases(store, session):
            if latest(store, other)["id"] == last["id"]:
                other["revisions"].append(delivery["id"])
        changed = True
    return changed


def on_stop(event: dict, root: Path, contract: dict, state: dict | None, platform: str) -> None:
    session = str(event.get("session_id") or "")
    name = contract.get("skill") or rt.SKILL_DIR.name
    if not state and not store_path(root, name).is_file():
        return
    with locked(root, name):
        store = load(root, name)
        changed = False
        if state and state.get("status") == "done":  # 質問待ちは作成の途中なので、提示した成果物にしない
            mark = marker(state)
            if not any(d.get("marker") == mark for d in store["deliveries"]):
                found = [(rel, out, bool(next((o.get("binary") for o in contract.get("outputs", []) if o["id"] == out), False)))
                         for out, rels in (state.get("outputs") or {}).items() for rel in rels]
                if found:
                    files = [file_entry(root, name, rel, out, binary) for rel, out, binary in found]
                    delivery = add_delivery(store, root, state, contract, files, "finish", platform, session, mark)
                    for case in open_cases(store, session):
                        if latest(store, case)["id"] != delivery["id"]:
                            case["revisions"].append(delivery["id"])  # 指摘を受けて実行し直した版
                    changed = True
        changed = revise(store, root, state, contract, platform, session) or changed
        if changed:
            save(root, store)


def on_prompt(event: dict, root: Path, contract: dict, state: dict | None, platform: str) -> str | None:
    """提示した後の発言を記録し、AI に分類の方法を返す。実行中（質問待ちを含む）の発言は依頼の続きなので集めない。"""
    prompt = event.get("prompt")
    name = contract.get("skill") or rt.SKILL_DIR.name
    if not isinstance(prompt, str) or not prompt.strip() or (state and state.get("status") in ("active", "waiting")):
        return None
    if not store_path(root, name).is_file():
        return None
    session = str(event.get("session_id") or "")
    with locked(root, name):
        store = load(root, name)
        shown = [d for d in store["deliveries"] if d.get("session") == session]
        if not shown:
            return None
        delivered = shown[-1]
        since = [m for m in store["messages"] if m.get("delivered") == delivered["id"] and m["kind"] == "prompt"]
        if not open_cases(store, session) and len(since) >= WINDOW:
            return None
        message = {"id": next_id(store["messages"], "m"), "at": rt.now(), "kind": "prompt", "platform": platform,
                   "session": session, "text": prompt, "delivered": delivered["id"], "class": None, "reason": None,
                   "case": None}
        store["messages"].append(message)
        save(root, store)
    t = text(contract)
    paths = [f["path"] for f in delivered["files"]]
    files = "、".join(paths[:5]) + (f"、{t['files_more'].replace('{n}', str(len(paths) - 5))}" if len(paths) > 5 else "")
    py = f'python3 "{rt.SKILL_DIR / "scripts" / "feedback.py"}"'
    return (t["guide"].replace("{skill}", name).replace("{mid}", message["id"]).replace("{did}", delivered["id"])
            .replace("{files}", files).replace("{py}", py))


def on_pre_tool(paths: list[Path], root: Path, contract: dict) -> str | None:
    for path in paths:
        try:
            rel = path.relative_to(root.resolve()).as_posix()
        except ValueError:
            continue
        if rel == DIRNAME or rel.startswith(DIRNAME + "/"):
            return text(contract)["denied"].replace("{rel}", rel)
    return None


def on_hook(action: str, event: dict, root: Path, contract: dict, state: dict | None, platform: str,
            paths: list[Path] | None = None) -> str | None:
    """hook.py の入口。pre-tool は拒否の理由、prompt は AI への案内を返す。"""
    if action == "pre-tool":
        return on_pre_tool(paths or [], root, contract)
    if action == "prompt":
        return on_prompt(event, root, contract, state, platform)
    if action == "stop":
        on_stop(event, root, contract, state, platform)
    return None


# ---------------------------------------------------------------- AI が行う操作

def fail(message: str) -> int:
    rt.emit(f"ERROR {message}", sys.stderr)
    return 2


def resolve_root(arg: str | None) -> Path:
    return Path(arg).resolve() if arg else rt.project_root(Path.cwd())


def require(root: Path, name: str) -> dict | None:
    if not store_path(root, name).is_file():
        return None
    return load(root, name)


def cmd_classify(args, root: Path, name: str, feedback: bool) -> int:
    with locked(root, name):
        store = require(root, name)
        message = find(store["messages"], args.event) if store else None
        if message is None or message["kind"] != "prompt":
            return fail(f"発言 {args.event} がありません（feedback.py status で未分類の発言を確かめる）")
        if message["class"] == "feedback":
            return fail(f"発言 {message['id']} は既に指摘 {message['case']} として記録しています")
        if not feedback:
            message.update({"class": "ignored", "reason": args.reason})
            save(root, store)
            rt.emit(f"発言 {message['id']} を指摘ではないとして記録しました（原文は残す）")
            return 0
        message["class"] = "feedback"
        case = next((c for c in open_cases(store, message.get("session"))
                     if latest(store, c)["id"] == message["delivered"]), None)
        if case is None:
            case = {"id": next_id(store["cases"], "c"), "status": "open", "opened_at": rt.now(),
                    "session": message.get("session"), "issue": {"messages": [], "quotes": [], "summary": None},
                    "before": message["delivered"], "revisions": [], "after": None, "approval": None}
            store["cases"].append(case)
        case["issue"]["messages"].append(message["id"])
        case["issue"]["quotes"].append(message["text"])
        if args.summary:
            case["issue"]["summary"] = args.summary
        message["case"] = case["id"]
        save(root, store)
    rt.emit(f"発言 {message['id']} を指摘 {case['id']} に記録しました（修正前の版 {case['before']}）。"
            "直したら、応答の最後に feedback.py review で確認画面の URL を出してユーザーに渡してください")
    return 0


def cmd_context(args, root: Path, name: str) -> int:
    path = Path(args.file)
    path = (path if path.is_absolute() else root / path).resolve()
    try:
        rel = path.relative_to(root.resolve()).as_posix()
    except ValueError:
        return fail(f"{args.file} はプロジェクトの外です")
    if not path.is_file():
        return fail(f"{rel} がありません")
    if rel.startswith((DIRNAME + "/", rt.RUNS_DIRNAME + "/")):
        return fail(f"{rel} は記録の置き場です。入力ファイルを指定してください")
    state = rt.load_state(root, name)
    with locked(root, name):
        store = load(root, name)
        entry = {**file_entry(root, name, rel), "at": rt.now()}
        if state and state.get("status") == "active" or not store["deliveries"]:
            store["pending_inputs"].append({**entry, "run": (state or {}).get("started_at")})
            where = "次に保存する版"
        else:
            delivery = store["deliveries"][-1]
            delivery["input_files"].append(entry)
            where = f"版 {delivery['id']}"
        save(root, store)
    rt.emit(f"入力ファイル {rel} を保存しました（{where}に付ける。sha256 {entry['sha256'][:12]}）")
    return 0


def summary(store: dict) -> dict:
    return {"unclassified": [m for m in store["messages"] if m["kind"] == "prompt" and m["class"] is None],
            "open": open_cases(store), "approved": [c for c in store["cases"] if c["status"] == "approved"]}


def cmd_status(args, root: Path, name: str) -> int:
    store = require(root, name) or new_store(name)
    s = summary(store)
    if args.json:
        rt.emit(json.dumps({"skill": name, "deliveries": len(store["deliveries"]), "messages": len(store["messages"]),
                            "unclassified": [m["id"] for m in s["unclassified"]],
                            "open": [{"id": c["id"], "before": c["before"], "revisions": c["revisions"]} for c in s["open"]],
                            "approved": [{"id": c["id"], "after": c["after"]} for c in s["approved"]]},
                           ensure_ascii=False, indent=2))
        return 0
    rt.emit(f"{name}: 提示した版 {len(store['deliveries'])} 件、発言 {len(store['messages'])} 件")
    for m in s["unclassified"]:
        rt.emit(f"  未分類 {m['id']}（版 {m['delivered']}）: {m['text'].strip().splitlines()[0][:60]}")
    for c in s["open"]:
        state = f"修正版 {len(c['revisions'])} 件、承認待ち" if c["revisions"] else "修正版がまだ無い"
        rt.emit(f"  対応中 {c['id']}（修正前 {c['before']}、{state}）: {c['issue']['quotes'][0].strip().splitlines()[0][:60]}")
    for c in s["approved"]:
        rt.emit(f"  承認済み {c['id']}（修正前 {c['before']} → 承認した版 {c['after']}）")
    return 0


def problems(root: Path, store: dict) -> list[str]:
    """記録の形（assets/feedback.schema.json）、ID の参照、objects の実体とハッシュを確かめる。"""
    found = []
    schema_file = rt.SKILL_DIR / SCHEMA_REL
    if schema_file.is_file():
        found += rt.schema_errors(store, rt.load_json(schema_file))
    name = store.get("skill", "")
    deliveries = {d["id"]: d for d in store.get("deliveries", [])}
    messages = {m["id"]: m for m in store.get("messages", [])}
    shas = set()
    for d in deliveries.values():
        shas |= {f["sha256"] for f in d.get("files", []) + d.get("input_files", []) if f.get("sha256")}
        shas.add(d.get("skill", {}).get("manifest"))
    for m in messages.values():
        if m.get("delivered") and m["delivered"] not in deliveries:
            found.append(f"発言 {m['id']} の版 {m['delivered']} がありません")
    for c in store.get("cases", []):
        for key in [c.get("before"), *c.get("revisions", []), c.get("after")]:
            if key and key not in deliveries:
                found.append(f"指摘 {c['id']} の版 {key} がありません")
        for mid in c.get("issue", {}).get("messages", []):
            if mid not in messages:
                found.append(f"指摘 {c['id']} の発言 {mid} がありません")
        if (c.get("after") is None) != (c.get("approval") is None) or (c.get("status") == "approved") != (c.get("after") is not None):
            found.append(f"指摘 {c['id']} の status・after・approval が揃っていません")
        if c.get("after") and c["after"] not in c.get("revisions", []):
            found.append(f"指摘 {c['id']} の承認した版 {c['after']} が修正版にありません")
    manifests = [d.get("skill", {}).get("manifest") for d in deliveries.values()]
    for sha in manifests:
        path = object_path(root, name, sha) if sha else None
        if path and path.is_file():
            shas |= set(json.loads(path.read_text(encoding="utf-8")).values())
    for sha in sorted(s for s in shas if s):
        path = object_path(root, name, sha)
        if not path.is_file():
            found.append(f"objects/{sha} がありません")
        elif rt.sha256(path) != sha:
            found.append(f"objects/{sha} の中身がハッシュと合いません")
    return found


def cmd_validate(args, root: Path, name: str) -> int:
    store = require(root, name)
    if store is None:
        rt.emit(f"{name}: 記録はまだありません")
        return 0
    found = problems(root, store)
    for p in found:
        rt.emit(f"ERROR {p}")
    rt.emit(f"validate: 問題 {len(found)} 件")
    return 1 if found else 0


def inside(base: Path, rel: str) -> Path:
    """base の下の rel。外を指す rel（絶対パス、..）は ValueError。"""
    path = (base / rel).resolve()
    if Path(rel).is_absolute() or not path.is_relative_to(base.resolve()):
        raise ValueError(f"{rel} は取り出し先の外を指します")
    return path


def dataset_problems(out: Path) -> list[str]:
    """取り出したもの（dataset.json）の参照と、実ファイルの中身がハッシュと合うかを確かめる。"""
    try:
        data = rt.load_json(out / "dataset.json")
    except (OSError, ValueError) as exc:
        return [f"dataset.json が読めません（{exc}）"]
    if data.get("kind") != DATASET_KIND or data.get("schema_version") != SCHEMA_VERSION:
        return [f"dataset.json が {DATASET_KIND}（schema_version {SCHEMA_VERSION}）ではありません"]
    found = []

    def same(path: Path, sha: str, what: str) -> None:
        if not path.is_file():
            found.append(f"{what} がありません")
        elif rt.sha256(path) != sha:
            found.append(f"{what} の中身がハッシュと合いません")

    for case in data.get("cases", []):
        cid = case.get("id", "?")
        approval = case.get("approval") or {}
        if not approval or approval.get("delivery") != case.get("after", {}).get("delivery"):
            found.append(f"指摘 {cid} に、承認した版と同じ版の承認がありません")
        try:
            for side in ("before", "after"):
                for f in case.get(side, {}).get("files", []):
                    if f.get("sha256"):
                        same(inside(out / "cases" / cid / side, f["path"]), f["sha256"], f"指摘 {cid} の {side}/{f['path']}")
            for f in case.get("input_files", []):
                if f.get("sha256"):
                    same(inside(out / "cases" / cid / "inputs", f["path"]), f["sha256"], f"指摘 {cid} の inputs/{f['path']}")
            skill = case.get("skill", {})
            manifest = out / f"{skill.get('dir', '?')}.manifest.json"
            same(manifest, skill.get("version", ""), f"指摘 {cid} のスキルの一覧")
            if manifest.is_file():
                for rel, sha in rt.load_json(manifest).items():
                    same(inside(out / skill["dir"], rel), sha, f"指摘 {cid} のスキルの {rel}")
        except ValueError as exc:
            found.append(f"指摘 {cid}: {exc}")
    return found


def cmd_export(args, root: Path, name: str) -> int:
    store = require(root, name)
    if store is None:
        return fail("記録がまだありません")
    found = problems(root, store)
    if found:
        return fail(f"記録に問題があるので取り出しません（feedback.py validate で確かめる）: {found[0]}")
    out = Path(args.out).expanduser().resolve()
    if out.is_relative_to(store_dir(root, name).parent.resolve()):
        return fail(f"{out} は記録の置き場（{DIRNAME}/）の中です。別のディレクトリを指定してください")
    if out.exists() and (not out.is_dir() or any(out.iterdir())):
        return fail(f"{out} は空ではありません。新しいディレクトリを指定してください")
    s = summary(store)
    approved = [c for c in s["approved"] if c.get("after") and c.get("approval")]
    if not approved:
        return fail(f"承認済みの指摘がありません（承認待ち・修正版がまだ無い指摘 {len(s['open'])} 件は取り出さない）")
    deliveries, messages = {d["id"]: d for d in store["deliveries"]}, {m["id"]: m for m in store["messages"]}

    def put(sha: str, dest: Path) -> None:
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(object_path(root, name, sha).read_bytes())

    def files(entries: list[dict], base: Path) -> list[dict]:
        for f in entries:
            if f.get("sha256"):
                put(f["sha256"], inside(base, f["path"]))
        return [{k: f.get(k) for k in ("path", "sha256", "size", "binary", "output")} for f in entries]

    cases = []
    try:
        for c in approved:
            before, after = deliveries[c["before"]], deliveries[c["after"]]
            chain = [before] + [deliveries[r] for r in c["revisions"][:c["revisions"].index(c["after"]) + 1]]
            inputs: dict[str, dict] = {}
            for d in chain:  # 同じ入力ファイルは、いちばん前（直す前）に保存したものを使う
                for f in d.get("input_files", []):
                    inputs.setdefault(f["path"], f)
            base = out / "cases" / c["id"]
            version = before["skill"]["manifest"]
            skill_dir = out / "skills" / version[:12]
            if not skill_dir.exists():
                manifest = json.loads(object_path(root, name, version).read_text(encoding="utf-8"))
                for rel, sha in manifest.items():
                    put(sha, inside(skill_dir, rel))
                put(version, out / "skills" / f"{version[:12]}.manifest.json")
            approval = c["approval"]
            cases.append({
                "id": c["id"], "synthetic": bool(approval.get("synthetic")),
                "issue": {"summary": c["issue"]["summary"], "quotes": c["issue"]["quotes"],
                          "messages": [{k: messages[m].get(k) for k in ("id", "at", "platform", "text")} for m in c["issue"]["messages"]]},
                "approval": {k: approval.get(k) for k in ("at", "comment", "delivery")},
                "request": before["request"], "input": before["input"], "extra": before["extra"],
                "before": {"delivery": before["id"], "at": before["at"], "files": files(before["files"], base / "before")},
                "after": {"delivery": after["id"], "at": after["at"], "files": files(after["files"], base / "after")},
                "input_files": [{k: f.get(k) for k in ("path", "sha256", "size")} for f in files(list(inputs.values()), base / "inputs")],
                "skill": {"version": version, "dir": f"skills/{version[:12]}", "contract": before["skill"].get("contract"),
                          "contract_version": before.get("contract")},
            })
    except (KeyError, ValueError, OSError) as exc:
        return fail(f"取り出せませんでした: {exc}")
    rt.write_json(out / "dataset.json", {"schema_version": SCHEMA_VERSION, "kind": DATASET_KIND, "skill": name,
                                         "exported_at": rt.now(), "synthetic": bool(store.get("synthetic")),
                                         "left_out": len(s["open"]), "cases": cases})
    found = dataset_problems(out)
    for p in found:
        rt.emit(f"ERROR {p}")
    rt.emit(f"export: 承認済みの指摘 {len(cases)} 件を {out} に取り出しました（承認待ち・修正版がまだ無い指摘 {len(s['open'])} 件は"
            f"入れていない）。確かめた問題 {len(found)} 件")
    return 1 if found else 0


def review_alive(root: Path, name: str) -> str | None:
    """動いている確認画面のサーバーの URL。応答が無ければ None。"""
    info_path = store_dir(root, name) / "review.json"
    if not info_path.is_file():
        return None
    try:
        info = rt.load_json(info_path)
        import urllib.request
        with urllib.request.urlopen(f"{info['url']}health", timeout=2) as response:
            if json.loads(response.read().decode("utf-8")).get("server") == info.get("server"):
                return info["url"]
    except (OSError, ValueError, KeyError):
        pass
    return None


def cmd_review(args, root: Path, name: str, contract: dict) -> int:
    state = rt.load_state(root, name)
    with locked(root, name):
        store = require(root, name)
        if store is None:
            return fail("記録がまだありません。スキルの成果物を提示した後の指摘から作られます")
        if revise(store, root, state, contract, "cli", None):
            save(root, store)
    script = rt.SKILL_DIR / "scripts" / "feedback_review.py"
    if args.foreground:
        return subprocess.call([sys.executable, str(script), "--root", str(root), "--port", str(args.port),
                                "--idle", str(args.idle)])
    url = review_alive(root, name)
    if url is None:
        log = store_dir(root, name) / "review.log"
        ready = store_dir(root, name) / "review.json"
        with contextlib.suppress(FileNotFoundError):
            ready.unlink()  # 前のサーバーの記録。新しいサーバーが起動したら書き直す
        options = {"start_new_session": True} if os.name != "nt" else {"creationflags": 0x00000008}  # DETACHED_PROCESS
        with log.open("ab") as out:
            subprocess.Popen([sys.executable, str(script), "--root", str(root), "--port", str(args.port), "--idle", str(args.idle)],
                             stdout=out, stderr=out, stdin=subprocess.DEVNULL, **options)
        for _ in range(100):
            url = review_alive(root, name)
            if url:
                break
            time.sleep(0.1)
        if url is None:
            return fail(f"確認画面のサーバーを起動できませんでした（{log.relative_to(root)} を見る）")
    s = summary(load(root, name))
    rt.emit(f"確認画面: {url}")
    rt.emit(f"承認待ち {sum(1 for c in s['open'] if c['revisions'])} 件、修正版がまだ無い {sum(1 for c in s['open'] if not c['revisions'])} 件。"
            "この URL をユーザーに渡し、確認画面で確かめて承認するよう伝える。AI は承認ボタンを押さない"
            f"（サーバーは操作が {args.idle} 分無いと止まる。止まったら同じコマンドで起動し直す）")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("feedback", help="発言を成果物への指摘として記録する")
    p.add_argument("--event", required=True, help="hooks の案内にある発言の ID（m-0001 など）")
    p.add_argument("--summary", help="指摘の要点（原文は置き換えない）")
    p = sub.add_parser("ignore", help="発言を指摘ではないとして記録する")
    p.add_argument("--event", required=True)
    p.add_argument("--reason", required=True)
    p = sub.add_parser("context", help="再現に必要な入力ファイルを、変える前に保存する")
    p.add_argument("--file", required=True)
    p = sub.add_parser("review", help="修正前後の確認画面を起動し、URL を出す")
    p.add_argument("--port", type=int, default=0, help="待ち受けるポート（0 なら空いているもの）")
    p.add_argument("--idle", type=int, default=30, help="操作が無いまま止まるまでの分")
    p.add_argument("--foreground", action="store_true", help="バックグラウンドにせず、この端末で動かす")
    p = sub.add_parser("status", help="未分類の発言と、対応中・承認済みの指摘を出す")
    p.add_argument("--json", action="store_true")
    sub.add_parser("validate", help="記録の形と、参照・実ファイルの整合を確かめる")
    p = sub.add_parser("export", help="承認済みの指摘を、改善に使うために新しいディレクトリに取り出す")
    p.add_argument("--out", required=True, help="取り出し先（無いか空のディレクトリ）")
    for action in sub.choices.values():
        action.add_argument("--root", help="プロジェクトのルート（既定: 作業ディレクトリから .git を辿った場所）")
    args = parser.parse_args()

    contract = rt.load_contract()
    name = contract.get("skill") or rt.SKILL_DIR.name
    root = resolve_root(args.root)
    try:
        if args.command in ("feedback", "ignore"):
            return cmd_classify(args, root, name, args.command == "feedback")
        if args.command == "context":
            return cmd_context(args, root, name)
        if args.command == "review":
            return cmd_review(args, root, name, contract)
        if args.command == "status":
            return cmd_status(args, root, name)
        if args.command == "export":
            return cmd_export(args, root, name)
        return cmd_validate(args, root, name)
    except (ValueError, TimeoutError) as exc:
        return fail(str(exc))


if __name__ == "__main__":
    sys.exit(main())
