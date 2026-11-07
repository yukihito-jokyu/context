#!/usr/bin/env python3
"""Eval（dev/eval/eval.json）そのものが妥当かを確かめる（STEP-06）。SKILL.md の手順3で Eval を書いた後、受付の前に実行する。

Eval は、ユーザーとの対話で確定した価値を、外から確かめられる振る舞い・成功と失敗の事例・正解の根拠・判定方法の形に
したもの。収束テストの課題（dev/evals.json）が「AI ごとに出力が揃うか」を測るのに対し、Eval は「出力が価値を満たすか」を
判定する。次を確かめる（references/eval.md の6章）。
  材料      利用場面・今の不満や失敗・望む結果・許容できない結果が、それぞれ1つ以上ある
  仮説      AI の価値仮説が、もとにした材料を持つ。利用場面・不満・望む結果は、どれも1つ以上の仮説に使う
  確定      確定した価値が、もとにした仮説と、ユーザーが確かめた対話（dialog の ID）を持つ
  振る舞い  確定した価値ごとに1つ以上あり、判定方法（code・model・human）を持つ
  事例      振る舞いごとに成功と失敗の事例が両方あり、事例ごとに状況・出力の見本・正解の根拠がある。
            許容できない結果は、どれも1つ以上の失敗の事例が確かめる（covers）
  判定      code の判定は出力の見本に実際に当て、成功の事例が通り、失敗の事例が落ちる。model と human の判定は、
            事例ごとに、判定にユーザーが同意した対話（agreed_in）がある
  target    振る舞いの判定するファイル（フェーズ4で書く）は、プロジェクトのルートからの相対パスの型にする
  質問      ユーザーに聞くこと（questions）が決まりの形で、答えを待っている質問が無い（references/eval.md の2章）
skip_reason を書いた Eval（省いた）は、中身を確かめない。答えを待っている質問があるときは、質問の形と、答えを待っていることだけを出す。
結果は dev/results/eval-check.json に書く（skill_lint.py --final とカタログが読む）。

--answer には、カタログの「Eval 作成」タブの「回答をコピー」でユーザーが写して貼った文を渡す。その文を言い換えずに dialog に足し、
questions を消してから確かめる。このときの Eval の項目の写し（before）を結果に残し、カタログが、回答の後に足した項目を「新規」、
直した項目を「更新」、変えていない項目を「既存」と示す。

収束テストの採点（STEP-07。references/eval.md の7章）に使う関数も置く。convergence.py の diff が code の判定を各エージェントの
出力に当て（score_run）、analysis-collect が分析役の model の判定を取り込む。締め込みで dev/convergence-report.md の
「## Eval の採点」の表に落ちた判定を分類し（round_gaps）、Eval の疑いか抜けがあれば Eval を直してから次のラウンドに進む（realign_gap）。

終了コード: 0 妥当、1 指摘あり、2 引数の誤り

使い方:
  python3 eval_check.py <作るスキルのディレクトリ>
  python3 eval_check.py <作るスキルのディレクトリ> --answer - < 貼られた回答
"""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import re
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _lib  # noqa: E402
import _skillrt as rt  # noqa: E402
from skill_lint import CHECK_FIELDS  # noqa: E402

EVAL_DIR = "dev/eval"
EVAL_REL = "dev/eval/eval.json"
RESULT_REL = "dev/results/eval-check.json"
# 材料の種類: (materials のキー, ID の接頭辞, 見せる名前)
MATERIALS = [("scenes", "scene", "利用場面"), ("pains", "pain", "今の不満や失敗"), ("wants", "want", "望む結果"),
             ("unacceptable", "ng", "許容できない結果")]
JUDGES = {"code": "スクリプトの検査", "model": "AI が基準の文で判定", "human": "人が基準の文で判定"}
JUDGE_CHECKS = {k: v for k, v in CHECK_FIELDS.items() if k != "command"}  # 手順3では、作るスキルのスクリプトがまだ無い
SCORE_TITLES = ["Eval の採点", "Eval scoring"]  # convergence-report.md の、落ちた判定を締め込みで分類した表の節
SCORE_CLASSES = ["出力の誤り", "Eval の疑い", "Eval の抜け"]  # 分類。疑いと抜けは、ユーザーとすり合わせて Eval を直す
REALIGN_CLASSES = SCORE_CLASSES[1:]
MODEL_TEXT_MAX = 12000  # 分析役に渡す、model の判定の対象の字数
ANSWER_HEAD = re.compile(r"^Eval 作成の回答（(?P<name>[^、）]+)、(?P<talk>talk-\d+)）$")  # カタログの「回答をコピー」の1行目
UNANSWERED = "（まだ答えていない）"
SNAPSHOT_KEYS = [("hypotheses", "text"), ("values", "text"), ("behaviors", "text"), ("cases", "situation")]  # (キー, 見せる文)。材料は text
TASKS_REL = "dev/evals.json"


def eval_hash(skill_dir: Path) -> str:
    """結果が今の Eval のものかを判定するハッシュ。dev/eval/ の下のファイルのどれかが変われば変わる。
    振る舞いの target（フェーズ4で書く、収束テストで判定するファイルの場所）は事例の判定に使わないので含めない。"""
    digest = hashlib.sha256()
    base = skill_dir / EVAL_DIR
    for rel in _lib.iter_files(base) if base.is_dir() else []:
        if Path(rel).name != ".DS_Store":
            digest.update(rel.encode() + b"\0" + without_targets(base / rel) if rel == Path(EVAL_REL).name else
                          rel.encode() + b"\0" + (base / rel).read_bytes())
    return digest.hexdigest()


def without_targets(path: Path) -> bytes:
    data = path.read_bytes()
    try:
        doc = json.loads(data.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return data
    for b in doc.get("behaviors", []) if isinstance(doc, dict) and isinstance(doc.get("behaviors"), list) else []:
        if isinstance(b, dict):
            b.pop("target", None)
    return json.dumps(doc, ensure_ascii=False, sort_keys=True).encode("utf-8")


def entries(doc: dict, key: str) -> list[dict]:
    value = doc.get(key)
    return [x for x in value if isinstance(x, dict)] if isinstance(value, list) else []


def questions(doc: dict) -> tuple[str, list[dict]]:
    """ユーザーの答えを待っている質問の (対話の ID, 質問)。無ければ ("", [])。"""
    q = doc.get("questions") if isinstance(doc.get("questions"), dict) else {}
    return str(q.get("talk") or ""), entries(q, "items")


def tasks_of(skill_dir: Path) -> list[dict]:
    """収束テストの題材（dev/evals.json の tasks）。手順3で Eval の後にユーザーと確かめる（eval.md の8章）。ひな形の目印のままの題材は入れない。"""
    try:
        doc = json.loads((skill_dir / TASKS_REL).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    return [t for t in entries(doc, "tasks") if t.get("id") and _lib.TODO_MARKER not in json.dumps(t, ensure_ascii=False)] \
        if isinstance(doc, dict) else []


def snapshot(doc: dict, tasks: list[dict] = ()) -> dict:
    """ラベル（新規・更新・既存）で比べる元にする、Eval の項目と収束テストの題材の写し（ID → 見せる文と中身のハッシュ）。
    ひな形の目印のままの項目は入れない。"""
    materials = doc.get("materials") if isinstance(doc.get("materials"), dict) else {}
    groups = [(entries(materials, key), "text") for key, _, _ in MATERIALS] + [(entries(doc, key), field) for key, field in SNAPSHOT_KEYS]
    groups.append((list(tasks), "prompt"))
    items = {}
    for found, field in groups:
        for e in found:
            body = json.dumps({k: v for k, v in e.items() if k != "target"}, ensure_ascii=False, sort_keys=True)
            if e.get("id") and _lib.TODO_MARKER not in body:
                items[str(e["id"])] = {"text": str(e.get(field) or ""), "sig": hashlib.sha256(body.encode("utf-8")).hexdigest()[:16]}
    return items


def changes(doc: dict, before, tasks: list[dict] = ()) -> tuple[dict, list[tuple[str, str]]]:
    """前の回答の時の写し（before）と比べた、項目ごとの (new・upd・keep, 前の文) と、外した項目の (ID, 前の文)。
    前の文は、更新で見せる文が変わったときだけ入れる。写しが無ければ ({}, [])。"""
    old = before.get("items") if isinstance(before, dict) else None
    if not isinstance(old, dict):
        return {}, []
    now, marks = snapshot(doc, tasks), {}
    for rid, x in now.items():
        prev = old.get(rid) if isinstance(old.get(rid), dict) else None
        marks[rid] = (("new", "") if prev is None else ("keep", "") if prev.get("sig") == x["sig"] else
                      ("upd", str(prev.get("text") or "") if prev.get("text") != x["text"] else ""))
    return marks, [(rid, str(x.get("text") or "") if isinstance(x, dict) else "") for rid, x in old.items() if rid not in now]


def load(skill_dir: Path) -> tuple[dict | None, str]:
    """(eval.json の中身, 読めないときの理由)。"""
    path = skill_dir / EVAL_REL
    if not path.is_file():
        return None, "ありません。SKILL.md の手順3で Eval を書くか、省くときは skip_reason だけを書いてください"
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return None, f"JSON として読めません（{exc.lineno} 行目）: {exc.msg}"
    return (doc, "") if isinstance(doc, dict) else (None, "中身は JSON のオブジェクトにしてください")


def check(skill_dir: Path) -> tuple[list[tuple[str, str]], list[dict], str]:
    """(指摘の（場所, 文）, 事例ごとの判定の結果, 省いた理由)。"""
    doc, problem = load(skill_dir)
    if doc is None:
        return [(EVAL_REL, problem)], [], ""
    skip = str(doc.get("skip_reason") or "").strip()
    if skip:
        return [], [], skip
    errors: list[tuple[str, str]] = []
    ids: dict[str, str] = {}  # ID → 種類

    def err(where: str, message: str) -> None:
        errors.append((f"{EVAL_REL} {where}", message))

    def register(kind: str, prefix: str, entry: dict, where: str) -> str:
        rid = str(entry.get("id", ""))
        if not re.fullmatch(re.escape(prefix) + r"-\d+", rid):
            err(where, f"ID「{rid}」は {prefix}-<番号> の形にしてください")
        elif rid in ids:
            err(where, f"ID {rid} が重複しています")
        else:
            ids[rid] = kind
        return rid

    def text(entry: dict, key: str, where: str) -> None:
        if not str(entry.get(key) or "").strip():
            err(where, f"{key} が空です")

    def refs(entry: dict, key: str, kind: str, where: str, required: bool = True) -> list[str]:
        value = entry.get(key)
        got = value if isinstance(value, list) else ([value] if isinstance(value, str) and value else [])
        if required and not got:
            err(where, f"{key} に{kind}の ID を書いてください")
        for rid in got:
            if ids.get(rid) != kind:
                err(where, f"{key} の {rid} は{kind}の ID ではありません")
        return [rid for rid in got if ids.get(rid) == kind]

    materials = doc.get("materials") if isinstance(doc.get("materials"), dict) else {}
    for key, prefix, label in MATERIALS:
        found = entries(materials, key)
        if not found:
            err(f"materials.{key}", f"{label}が1つもありません。ユーザーに聞いて書いてください")
        for e in found:
            where = f"materials.{key} {e.get('id', '?')}"
            register("材料", prefix, e, where)
            text(e, "text", where)
    talks = entries(doc, "dialog")
    if not talks:
        err("dialog", "ユーザーとの対話の記録がありません。価値も model・human の判定も、ユーザーに確かめてから確定させてください")
    for e in talks:
        where = f"dialog {e.get('id', '?')}"
        register("対話", "talk", e, where)
        text(e, "asked", where)
        text(e, "answer", where)
    hypotheses = entries(doc, "hypotheses")
    if not hypotheses:
        err("hypotheses", "価値仮説がありません。材料から仮説を立ててください")
    used = set()
    for e in hypotheses:
        where = f"hypotheses {e.get('id', '?')}"
        register("仮説", "hyp", e, where)
        text(e, "text", where)
        used.update(refs(e, "from", "材料", where))
    for key, prefix, label in MATERIALS[:3]:
        for e in entries(materials, key):
            if e.get("id") in ids and e["id"] not in used:
                err(f"materials.{key} {e['id']}", f"どの仮説の from にもありません。{label}を仮説に使うか、価値に関わらないなら材料から外してください")
    values = entries(doc, "values")
    if not values:
        err("values", "確定した価値がありません。仮説をユーザーに示して確定させてください")
    for e in values:
        where = f"values {e.get('id', '?')}"
        register("価値", "value", e, where)
        text(e, "text", where)
        refs(e, "from", "仮説", where)
        refs(e, "confirmed_in", "対話", where)
    behaviors = {}
    for e in entries(doc, "behaviors"):
        where = f"behaviors {e.get('id', '?')}"
        rid = register("振る舞い", "behavior", e, where)
        text(e, "text", where)
        refs(e, "value", "価値", where)
        judge = e.get("judge") if isinstance(e.get("judge"), dict) else {}
        kind = judge.get("type")
        if kind not in JUDGES:
            err(where, f"judge.type は {'・'.join(JUDGES)} のどれかにしてください")
        elif kind == "code":
            checks = judge.get("checks") if isinstance(judge.get("checks"), list) else []
            if not checks:
                err(where, "judge.type が code なので、judge.checks に検査を1つ以上書いてください（契約の checks と同じ書き方）")
            for i, c in enumerate(checks):
                ctype = c.get("type") if isinstance(c, dict) else None
                if ctype not in JUDGE_CHECKS:
                    err(where, f"judge.checks[{i}] の type は {'・'.join(JUDGE_CHECKS)} のどれかにしてください（command は使わない）")
                else:
                    for field in JUDGE_CHECKS[ctype]:
                        if field not in c:
                            err(where, f"judge.checks[{i}]（{ctype}）に {field} がありません")
        else:
            text(judge, "rubric", where + " judge")
        if "target" in e and target_problem(e["target"]):
            err(where, target_problem(e["target"]))
        behaviors[rid] = {**e, "judge": judge}
    for e in values:
        if e.get("id") in ids and not any(b.get("value") == e["id"] for b in behaviors.values()):
            err(f"values {e['id']}", "この価値を確かめる振る舞いがありません")
    results, expects, covered = [], {}, set()
    base = (skill_dir / EVAL_DIR).resolve()
    for e in entries(doc, "cases"):
        cid = str(e.get("id", "?"))
        where = f"cases {cid}"
        register("事例", "case", e, where)
        behavior = behaviors.get(str(e.get("behavior")))
        refs(e, "behavior", "振る舞い", where)
        expect = e.get("expect")
        if expect not in ("pass", "fail"):
            err(where, "expect は pass（成功の事例）か fail（失敗の事例）にしてください")
        text(e, "situation", where)
        text(e, "reason", where)
        covers = refs(e, "covers", "材料", where, required=False)
        if expect == "fail":
            covered.update(covers)
        output = str(e.get("output") or "")
        path = (base / output).resolve() if output else None
        if path is None or not path.is_relative_to(base) or not path.is_file():
            err(where, f"output には、出力の見本のファイルを {EVAL_DIR}/ からの相対パスで書いてください（今: {output or '空'}）")
            path = None
        if behavior is None or expect not in ("pass", "fail"):
            continue
        expects.setdefault(behavior["id"], set()).add(expect)
        kind = behavior["judge"].get("type")
        if kind == "code" and path is not None and not any(w[0] == f"{EVAL_REL} behaviors {behavior['id']}" for w in errors):
            checks = [{"rule": "STEP-06", **c} for c in behavior["judge"]["checks"]]
            found = rt.check_file(base, path.relative_to(base).as_posix(), {"rule": "STEP-06", "checks": checks},
                                  skill_dir.name, skill_dir, values=e.get("inputs") if isinstance(e.get("inputs"), dict) else {})
            got = "fail" if found else "pass"
            if got != expect:
                err(where, f"{'成功' if expect == 'pass' else '失敗'}の事例なのに、判定（code）で{'落ちます' if found else '通ります'}"
                           + (f"（{found[0]['message']}）" if found else "") + "。判定の検査か、事例の出力の見本を直してください")
            results.append({"id": cid, "expect": expect, "judge": kind, "got": got, "detail": found[0]["message"] if found else ""})
        elif kind in ("model", "human"):
            agreed = refs(e, "agreed_in", "対話", where, required=False)
            if not agreed:
                err(where, f"判定が {kind} なので、この事例の判定にユーザーが同意した対話の ID を agreed_in に書いてください")
            results.append({"id": cid, "expect": expect, "judge": kind, "got": "agreed" if agreed else "", "detail": "、".join(agreed)})
    for rid in behaviors:
        missing = [label for kind, label in (("pass", "成功"), ("fail", "失敗")) if kind not in expects.get(rid, set())]
        if rid in ids and missing:
            err(f"behaviors {rid}", f"{'と'.join(missing)}の事例がありません。振る舞いごとに成功と失敗の事例を両方書いてください")
    for e in entries(materials, "unacceptable"):
        if e.get("id") in ids and e["id"] not in covered:
            err(f"materials.unacceptable {e['id']}", "この許容できない結果を確かめる失敗の事例がありません。失敗の事例の covers に書いてください")
    mark = len(errors)
    talk, items = questions(doc)
    if "questions" in doc:
        if not re.fullmatch(r"talk-\d+", talk) or talk in ids:
            err("questions", f"talk は、まだ dialog に無い talk-<番号> にしてください（次は talk-{len(talks) + 1}。今: {talk or '空'}）")
        if not items:
            err("questions", "items が空です。答えを待つ質問が無いなら、questions を消してください")
    task_ids = {str(t["id"]) for t in tasks_of(skill_dir)}
    for n, q in enumerate(items, 1):
        where = f"questions Q{n}"
        text(q, "title", where)
        text(q, "ask", where)
        for rid in q.get("refs") if isinstance(q.get("refs"), list) else []:
            if str(rid) not in ids and str(rid) not in task_ids:
                err(where, f"refs の {rid} が Eval にも収束テストの題材（{TASKS_REL}）にもありません")
        options = q.get("options")
        if options is None:
            continue
        keys = [o.get("key") for o in options if isinstance(o, dict)] if isinstance(options, list) else []
        if len(keys) < 2 or len(keys) != len(options):
            err(where, "options は、選べる答え（key と text）を2つ以上並べてください。書いて答えるだけの質問なら options を消してください")
        if any(not re.fullmatch(r"[A-Z]", str(k)) for k in keys) or len(set(keys)) != len(keys):
            err(where, "options の key は、重ならない大文字の英字1字（A、B、C）にしてください")
        for o in options if isinstance(options, list) else []:
            if isinstance(o, dict):
                text(o, "text", f"{where} {o.get('key', '?')}")
    if items:  # 答えを待っている間は、ほかの指摘（まだ書いていない価値・事例）を出さない
        err("questions", f"ユーザーの答えを待っている質問が {len(items)} 件あります（{talk}）。カタログの「Eval 作成」タブで答えてもらい、"
                         "貼られた回答を eval_check.py --answer で記録してください")
        return errors[mark:], results, ""
    return errors, results, ""


def record_answer(skill_dir: Path, text: str) -> tuple[str, dict]:
    """貼られた回答を dialog に足し、questions を消す。(問題, 回答した時の Eval の項目の写し)。問題が無ければ問題は空。"""
    doc, problem = load(skill_dir)
    if doc is None:
        return f"{EVAL_REL}: {problem}", {}
    talk, items = questions(doc)
    if not items:
        return "答えを待っている質問（questions）がありません", {}
    lines = [line.rstrip() for line in text.strip().splitlines()]
    head = ANSWER_HEAD.match(lines[0].strip()) if lines else None
    if head is None:
        return ("1行目が「Eval 作成の回答（<スキルの名前>、talk-<番号>）」ではありません。カタログの「回答をコピー」で写した文を"
                "そのまま渡してください"), {}
    if (head["name"], head["talk"]) != (skill_dir.name, talk):
        return f"{head['name']} の {head['talk']} への回答です。今の質問は {skill_dir.name} の {talk} です", {}
    if not isinstance(doc.get("dialog"), list):
        doc["dialog"] = []
    doc["dialog"].append({"id": talk, "asked": "\n".join(f"Q{n} {q.get('title', '')}: {q.get('ask', '')}" for n, q in enumerate(items, 1)),
                          "answer": "\n".join(lines)})
    del doc["questions"]
    _lib.write_json(skill_dir / EVAL_REL, doc)
    return "", {"talk": talk, "items": snapshot(doc, tasks_of(skill_dir))}


def stale(skill_dir: Path) -> str:
    """dev/results/eval-check.json が今の Eval の結果でなければ、その理由。"""
    path = skill_dir / RESULT_REL
    if not path.is_file():
        return "ありません。eval_check.py を実行してください"
    try:
        result = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return "読めません。eval_check.py を実行し直してください"
    return "" if result.get("hash") == eval_hash(skill_dir) else "Eval を変えた後の結果ではありません。eval_check.py を実行し直してください"


# ---------------------------------------------------------------- 収束テストでの採点（STEP-07）

def target_problem(target) -> str:
    """振る舞いの target（判定するファイルの場所）が決まりに合わなければ、その理由。"""
    path = str(target).partition("#")[0] if isinstance(target, str) else ""
    if not path.strip():
        return "target には、判定するファイルの場所をプロジェクトのルートからの相対パスで書いてください（references/eval.md の7章）"
    if path.startswith(("/", "~")) or ".." in Path(path).parts:
        return f"target はプロジェクトのルートからの相対パスにしてください（今: {target}）"
    return ""


def missing_targets(skill_dir: Path) -> list[str]:
    """Eval を作ったのに、判定するファイルの場所（target）が無いか、ひな形の目印のままの code・model の振る舞い。"""
    doc, _ = load(skill_dir)
    if doc is None or str(doc.get("skip_reason") or "").strip():
        return []
    return [str(b.get("id")) for b in entries(doc, "behaviors")
            if (b.get("judge") or {}).get("type") in ("code", "model")
            and (not str(b.get("target") or "").strip() or _lib.TODO_MARKER in str(b.get("target")))]


def scoring(skill_dir: Path) -> dict | None:
    """収束テストで採点に使う Eval（中身・ハッシュ・対話の数）。Eval が無いか省いたなら None。"""
    doc, _ = load(skill_dir)
    if doc is None or str(doc.get("skip_reason") or "").strip():
        return None
    return {"doc": doc, "hash": eval_hash(skill_dir), "dialog": len(entries(doc, "dialog"))}


def natural(text: str) -> list:
    return [int(t) if t.isdigit() else t for t in re.split(r"(\d+)", text)]


def find_target(project: Path, target: str, name: str, values: dict) -> tuple[str, str]:
    """(当たったファイルのプロジェクトからの相対パス, # の後の要素の id)。複数に当たれば、名前の順で最後のもの
    （round-10 が round-9 の後）。当たらないか、入力の値が無くて場所が決まらなければ、パスは空。"""
    path, _, frag = target.partition("#")
    pattern, frag = rt.expand(path, name, values), rt.expand(frag, name, values)
    if rt.IN_PLACEHOLDER.search(pattern) or rt.IN_PLACEHOLDER.search(frag):
        return "", frag
    hits = sorted((p.relative_to(project).as_posix() for p in project.glob(pattern) if p.is_file()), key=natural)
    return (hits[-1] if hits else ""), frag


def element(text: str, ident: str) -> str | None:
    """HTML の id が ident の要素（開始タグから対応する終了タグまで）。無ければ None。"""
    start = re.search(r'<([a-zA-Z][\w-]*)\b[^>]*\bid="' + re.escape(ident) + '"', text)
    if not start:
        return None
    depth = 0
    for tag in re.finditer(r"<(/?)" + start.group(1) + r"\b[^>]*>", text[start.start():]):
        depth += -1 if tag.group(1) else 1
        if depth == 0:
            return text[start.start():start.start() + tag.end()]
    return text[start.start():]


def visible_text(text: str) -> str:
    """HTML の、画面に出る文字（分析役が読む形）。"""
    text = re.sub(r"<(script|style|svg)\b.*?</\1>", " ", text, flags=re.S)
    text = re.sub(r"</(tr|p|h[1-6]|li|div|summary|details|table|section)>|<br\s*/?>", "\n", text)
    lines = (re.sub(r"\s+", " ", line).strip() for line in html.unescape(re.sub(r"<[^>]+>", " ", text)).split("\n"))
    return "\n".join(line for line in lines if line)


def target_text(project: Path, rel: str, frag: str) -> str | None:
    """判定する中身。# の後に id があれば、その要素だけ。読めないか要素が無ければ None。"""
    try:
        text = (project / rel).read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None
    return element(text, frag) if frag else text


def model_text(text: str, rel: str) -> str:
    """model の判定で分析役に渡す形。HTML は画面に出る文字にし、長ければ先頭を残す。"""
    text = visible_text(text) if rel.endswith((".html", ".htm")) else text
    return text if len(text) <= MODEL_TEXT_MAX else text[:MODEL_TEXT_MAX] + f"\n…（以下 {len(text) - MODEL_TEXT_MAX} 字を略）"


def score_run(skill_dir: Path, doc: dict, project: Path, name: str, values: dict) -> dict:
    """1人のエージェントの出力を Eval で採点する。{振る舞い ID: {type, result, target, detail}}。
    result は pass・fail・na（判定するファイルが無い。失敗にしない）・pending（model。分析役が判定する）・human（基準に入れない）。"""
    scores = {}
    for b in entries(doc, "behaviors"):
        judge = b.get("judge") if isinstance(b.get("judge"), dict) else {}
        kind = judge.get("type")
        rel, frag = find_target(project, str(b.get("target") or ""), name, values) if b.get("target") else ("", "")
        entry = {"type": kind, "target": rel + (f"#{frag}" if rel and frag else ""), "result": "na", "detail": ""}
        text = target_text(project, rel, frag) if rel else None
        if kind == "human":
            entry["result"] = "human"
        elif not rel:
            entry["detail"] = "判定するファイルが無い"
        elif text is None:
            entry["detail"] = f"#{frag} の要素が無い" if frag else "UTF-8 のテキストとして読めない"
        elif kind == "code":
            with tempfile.TemporaryDirectory() as tmp:
                (Path(tmp) / "target").write_text(text, encoding="utf-8")
                checks = [{"rule": "STEP-07", **c} for c in judge.get("checks", []) if isinstance(c, dict)]
                found = rt.check_file(Path(tmp), "target", {"rule": "STEP-07", "checks": checks}, name, skill_dir, values=values)
            entry.update(result="fail" if found else "pass", detail=found[0]["message"] if found else "")
        else:
            entry["result"] = "pending"
        scores[str(b.get("id"))] = entry
    return scores


def task_ok(agents: dict) -> bool | None:
    """課題の全員の採点が通ったか。落ちた判定があれば False、model の判定待ちが残れば None。"""
    results = [s.get("result") for scores in agents.values() for s in scores.values()]
    return False if "fail" in results else (None if "pending" in results else True)


def score_rows(report_text: str, rnd: int) -> list[list[str]]:
    """convergence-report.md の「Eval の採点」の表のうち、ラウンドの列が rnd の行（セルの列）。"""
    body = "".join(_lib.section(report_text, title) for title in SCORE_TITLES)
    rows = [[c.strip() for c in line.strip().strip("|").split("|")] for line in body.splitlines() if line.strip().startswith("|")]
    return [row for row in rows if row[0] == str(rnd)]


def round_report(skill_dir: Path, rnd: int) -> dict:
    path = skill_dir / f"dev/results/convergence/round-{rnd}/report.json"
    return _lib.load_json(path) if path.is_file() else {}


def judgments(report: dict, result: str) -> list[tuple[str, str]]:
    """(課題/エージェント, 振る舞い ID) のうち、採点が result のもの。"""
    return [(f"{t.get('id')}/{agent}", bid) for t in report.get("tasks", []) for agent, scores in (t.get("eval") or {}).items()
            for bid, s in scores.items() if s.get("result") == result]


def round_gaps(skill_dir: Path, rnd: int, report_text: str) -> list[str]:
    """ラウンド rnd の採点を、締め込みに使った記録（「## Eval の採点」の表）が足りないところ。
    model の判定待ちが残っている、落ちた判定が表に無い、分類か対処が埋まっていない。"""
    report = round_report(skill_dir, rnd)
    if not (report.get("eval") or {}).get("hash"):
        return []
    problems = []
    pending = judgments(report, "pending")
    if pending:
        problems.append(f"ラウンド {rnd} に model の判定がまだ無い出力があります（{', '.join(f'{r} {b}' for r, b in pending[:4])}"
                        + (f" ほか {len(pending) - 4} 件" if len(pending) > 4 else "") + "）。analysis-collect で分析役の判定を取り込んでください")
    rows = score_rows(report_text, rnd)
    for row in rows:
        if len(row) < 5 or row[3] not in SCORE_CLASSES or not row[4]:
            problems.append(f"ラウンド {rnd} の「Eval の採点」の行「{row[1][:40] if len(row) > 1 else ''}」の分類（"
                            + "・".join(SCORE_CLASSES) + "）か対処が埋まっていません")
    missing = [f"{rid} {bid}" for rid, bid in judgments(report, "fail")
               if not any(len(row) > 2 and re.search(re.escape(rid) + r"(?![\w-])", row[1]) and re.search(re.escape(bid) + r"(?!\d)", row[2])
                          for row in rows)]
    if missing:
        problems.append(f"ラウンド {rnd} で Eval に落ちた判定が、「Eval の採点」の表にありません（{', '.join(missing[:4])}"
                        + (f" ほか {len(missing) - 4} 件" if len(missing) > 4 else "") + "）")
    return problems


def realign_gap(skill_dir: Path, rnd: int, report_text: str, conclusion: str | None = None) -> str:
    """ラウンド rnd の表に Eval の疑いか抜けがあるのに、ユーザーとすり合わせて Eval を直していなければ、その理由。
    conclusion（そのラウンドで収束テストを終えたときの「結論」）を渡すと、直さずに疑いと抜けの振る舞いか価値の ID を
    「結論」に残していれば理由を返さない。直した Eval で採点するラウンドが無いので、直すのは次のラウンドの前（prepare）でよい。"""
    rows = [row for row in score_rows(report_text, rnd) if len(row) > 3 and row[3] in REALIGN_CLASSES]
    if not rows:
        return ""
    scored, now = round_report(skill_dir, rnd).get("eval") or {}, scoring(skill_dir)
    if now is None or now["hash"] == scored.get("hash") or now["dialog"] <= int(scored.get("dialog") or 0):
        if conclusion is not None:
            ids = dict.fromkeys(i for row in rows for i in (re.findall(r"(?:behavior|value)-\d+", row[2]) or [row[2]]))
            left = [i for i in ids if not re.search(re.escape(i) + r"(?!\d)", conclusion)]
            if not left:
                return ""
            return (f"ラウンド {rnd} の「Eval の採点」の {'か'.join(REALIGN_CLASSES)} を、Eval を直さずに残すなら、"
                    f"dev/convergence-report.md の「結論」に {', '.join(left)} の分類と残した理由を書いてください。"
                    "続けるなら、run.py wait --question の後にユーザーとすり合わせ、dev/eval/eval.json を直してください")
        return (f"ラウンド {rnd} の「Eval の採点」に {'か'.join(REALIGN_CLASSES)} があるのに、Eval が採点の後に直されていないか、"
                "直すためにユーザーと話した対話（dialog）が増えていません。run.py wait --question の後にユーザーとすり合わせ、"
                "dev/eval/eval.json を直してください")
    errors, _, _ = check(skill_dir)
    if errors or stale(skill_dir):
        return "直した Eval が eval_check.py に通っていません。eval_check.py のエラーを0件にしてください"
    return ""


def unchecked(report: dict) -> list[str]:
    """ラウンドの全員で「判定するファイルが無い」だった code・model の振る舞い（確かめられなかったもの）。"""
    seen: dict[str, set] = {}
    for t in report.get("tasks", []):
        for scores in (t.get("eval") or {}).values():
            for bid, s in scores.items():
                if s.get("type") in ("code", "model"):
                    seen.setdefault(bid, set()).add(s.get("result"))
    return sorted((b for b, got in seen.items() if got == {"na"}), key=natural)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("dir", help="作るスキルのディレクトリ")
    parser.add_argument("--answer", metavar="TEXT", help="カタログの「Eval 作成」タブから貼られた回答（- なら標準入力から読む）。dialog に足してから確かめる")
    args = parser.parse_args()
    skill_dir = Path(args.dir).resolve()
    if not skill_dir.is_dir():
        _lib.fail(f"{skill_dir} がありません")
    previous = json.loads((skill_dir / RESULT_REL).read_text(encoding="utf-8")) if (skill_dir / RESULT_REL).is_file() else {}
    before = previous.get("before") if isinstance(previous, dict) else None
    if args.answer is not None:
        pasted = sys.stdin.read() if args.answer == "-" else args.answer
        problem, before = record_answer(skill_dir, pasted)
        if problem:
            print(f"ERROR --answer: {problem}")
            return 1
        missing = [line.split(" ", 1)[0] for line in pasted.splitlines() if line.rstrip().endswith(UNANSWERED)]
        print(f"[eval] {skill_dir.name}: {before['talk']} の回答を dialog に記録し、questions を消した。"
              + (f"答えていない質問（{'、'.join(missing)}）は、次の questions で聞き直す。" if missing else "")
              + "回答を Eval に反映し、まだ聞くことがあれば questions に書く")
    errors, results, skip = check(skill_dir)
    if (skill_dir / EVAL_REL).is_file():
        _lib.write_json(skill_dir / RESULT_REL, {"hash": eval_hash(skill_dir), "skip_reason": skip,
                                                 "errors": [f"{w}: {m}" for w, m in errors], "cases": results,
                                                 **({"before": before} if before else {})})
    for where, message in errors:
        print(f"ERROR {where}: {message}")
    if skip:
        print(f"[eval] {skill_dir.name}: Eval を省いた（{skip}）")
    else:
        hit = sum(r["got"] in (r["expect"], "agreed") for r in results)
        print(f"[eval] {skill_dir.name}: 事例 {len(results)} 件（判定が期待どおり・同意あり {hit} 件）、エラー {len(errors)} 件")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
