#!/usr/bin/env python3
"""承認済みの利用中の指摘（feedback.py export で取り出したもの）から、改善するスキルの作業用コピーと、Eval・収束テストの
候補を作る（references/eval.md の9章）。正本のスキルと既存の Eval は変えない。

作るもの（<out> は新しいディレクトリ。作業用のプロジェクトとして使う）:
  <out>/<置き場>/<name>/            改善するスキルの作業用コピー（dev/results/ は写さない）。置き場は spec の targets の先頭から
                                    決める（.claude/skills か .agents/skills）ので、catalog.py --project <out> で開ける
    dev/eval/eval.json              既存の Eval に、指摘ごとの材料・価値仮説・価値・振る舞い・成功と失敗の事例を、指摘の ID
                                    （feedback）付きで下書きして足す。questions に、ユーザーに確かめる4つのことを書く
    dev/eval/cases/feedback/<指摘>/  事例の出力の見本（判定するファイルの、before- が修正前、after- が承認した版）
    dev/evals.json                  既存の課題に、指摘ごとの課題（T-feedback-<番号>）を足す。元の依頼（prompt）と入力の値
                                    （input）と、保存した入力ファイルの置き先（feedback_inputs）を書く
    dev/feedback-inputs/<課題>/      保存した入力ファイル（convergence.py prepare が課題の作業ディレクトリに置く）
  <out>/dataset/                    取り出したものの写し
  <out>/candidate.json              候補の状態（ユーザーの確認待ち）と、指摘・課題・振る舞い・事例の対応

候補の質問（questions）は、今の Eval 作成と同じく、カタログの「Eval 作成」タブで答えてもらい、eval_check.py --answer で
記録する。答えるまで eval_check.py は先へ進ませない。確認画面での成果物の承認は「この修正版で OK」の意味で、「今後この条件で
評価してよい」という同意ではないので、判定への同意は質問で確かめ直す。候補を正本に反映するのは、作業用コピーで Eval 作成と
収束テストを通した後に、人が判断して行う。

終了コード: 0 作った、1 取り出したものか改善するスキルに問題がある、2 引数の誤り

使い方:
  python3 feedback_eval.py --dataset <取り出したもの> --skill <改善するスキル> --out <新しい作業場所>
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _lib  # noqa: E402
import _skillrt as rt  # noqa: E402
import feedback  # noqa: E402

PLACES = {"claude": ".claude/skills", "codex": ".agents/skills"}  # convergence.py の PLACES と同じ
EVAL_REL, TASKS_REL, INPUTS_REL = "dev/eval/eval.json", "dev/evals.json", "dev/feedback-inputs"
CASES_REL = "cases/feedback"  # dev/eval/ からの相対
STATUS = {"status": "awaiting-user", "label": "ユーザーの確認待ち"}


def tree_hash(directory: Path) -> str:
    """ディレクトリの中のファイルの一覧と中身のハッシュ（正本が変わっていないことを確かめる）。"""
    digest = hashlib.sha256()
    for dirpath, dirnames, filenames in os.walk(directory):
        dirnames.sort()
        for f in sorted(filenames):
            path = Path(dirpath) / f
            digest.update(path.relative_to(directory).as_posix().encode("utf-8") + b"\0")
            digest.update(path.read_bytes() if path.is_file() else b"")
    return digest.hexdigest()


def next_id(doc_items: list, prefix: str) -> int:
    numbers = [int(str(e.get("id", "")).rsplit("-", 1)[-1]) for e in doc_items
               if str(e.get("id", "")).startswith(prefix + "-") and str(e.get("id", "")).rsplit("-", 1)[-1].isdigit()]
    return max(numbers, default=0) + 1


def first_line(text: str, limit: int = 80) -> str:
    line = (text or "").strip().splitlines()[0] if (text or "").strip() else ""
    return line if len(line) <= limit else line[:limit] + "…"


def judged_file(case: dict) -> dict | None:
    """判定するファイルの案: 承認した版で、修正前から変わった契約の出力（文字列を先に）。"""
    before = {f["path"]: f.get("sha256") for f in case["before"]["files"]}
    changed = [f for f in case["after"]["files"] if f.get("sha256") and before.get(f["path"]) != f["sha256"]]
    changed.sort(key=lambda f: (f.get("output") is None, bool(f.get("binary"))))
    return changed[0] if changed else None


def build(dataset: Path, skill: Path, out: Path) -> dict:
    data = rt.load_json(dataset / "dataset.json")
    spec = _lib.load_spec(skill)
    name = spec["name"]
    copy = out / PLACES[spec.get("targets", ["claude"])[0]] / name
    _lib.copy_tree(skill, copy)
    shutil.rmtree(copy / "dev/results", ignore_errors=True)  # 正本の検査と収束テストの結果は、作業用コピーには当てはまらない
    shutil.copytree(dataset, out / "dataset")  # 成果物のパスに .skill-runs を含むことがあるので、除外なしで写す
    contract = rt.load_json(copy / "assets/contract.json") if (copy / "assets/contract.json").is_file() else {}
    patterns = {o["id"]: o["path"] for o in contract.get("outputs", [])}
    labels = {o["id"]: o.get("label", o["id"]) for o in contract.get("outputs", [])}

    eval_path = copy / EVAL_REL
    doc = rt.load_json(eval_path) if eval_path.is_file() else {}
    if str(doc.get("skip_reason") or "").strip() or not doc:
        doc = {"skip_reason": "", "materials": {}, "dialog": [], "hypotheses": [], "values": [], "behaviors": [], "cases": []}
    if doc.get("questions"):
        _lib.fail(f"{skill / EVAL_REL} に答えを待っている質問があります。先に答えてもらってから候補を作ってください")
    doc["skip_reason"] = ""
    materials = doc.setdefault("materials", {})
    for key in ("scenes", "pains", "wants", "unacceptable"):
        materials.setdefault(key, [])
    for key in ("dialog", "hypotheses", "values", "behaviors", "cases"):
        doc.setdefault(key, [])
    talk = f"talk-{next_id(doc['dialog'], 'talk')}"
    tasks_doc = rt.load_json(copy / TASKS_REL) if (copy / TASKS_REL).is_file() else {"tasks": []}
    tasks = tasks_doc.setdefault("tasks", [])

    links, quotes, picks, inputs = [], [], [], []
    for case in sorted(data["cases"], key=lambda c: c["id"]):
        cid = case["id"]
        pick = judged_file(case)
        if pick is None:
            _lib.fail(f"指摘 {cid} の承認した版に、修正前から変わったファイルがありません")
        point = case["issue"]["summary"] or first_line(case["issue"]["quotes"][0])
        scene = f"scene-{next_id(materials['scenes'], 'scene')}"
        materials["scenes"].append({"id": scene, "text": f"「{first_line(case['request'], 120)}」と頼んで使った（利用中の指摘 {cid}）",
                                    "feedback": cid})
        pains = []
        for message, quote in zip(case["issue"]["messages"], case["issue"]["quotes"]):
            pains.append(f"pain-{next_id(materials['pains'], 'pain')}")
            materials["pains"].append({"id": pains[-1], "text": quote, "feedback": cid, "message": message["id"]})
        hyp = f"hyp-{next_id(doc['hypotheses'], 'hyp')}"
        doc["hypotheses"].append({"id": hyp, "text": f"（候補）「{point}」という指摘に沿って直すと、{cid} で承認した版のような出力になる",
                                  "from": [scene, *pains], "feedback": cid})
        value = f"value-{next_id(doc['values'], 'value')}"
        doc["values"].append({"id": value, "text": f"（候補）「{point}」という指摘が直った出力を受け取れる", "from": [hyp],
                              "confirmed_in": talk, "feedback": cid})
        behavior = f"behavior-{next_id(doc['behaviors'], 'behavior')}"
        said = first_line(case["issue"]["quotes"][0])
        doc["behaviors"].append({
            "id": behavior, "value": value, "text": f"（候補）出力が「{point}」という指摘に沿っている",
            "target": patterns.get(pick.get("output"), pick["path"]),
            "judge": {"type": "model", "rubric": f"成功: {cid} で承認した版（修正後）のように、「{said}」という指摘が直っている。"
                                                 f"失敗: 指摘を受けた版（修正前）のように、「{said}」と言われた状態のまま。"},
            "feedback": cid})
        situation = f"利用中の指摘 {cid}: 「{first_line(case['request'], 120)}」と頼んだとき"
        before_pick = next((f for f in case["before"]["files"] if f["path"] == pick["path"] and f.get("sha256")), None)
        samples = {}
        for side, f in (("after", pick), ("before", before_pick)):
            if f is None:
                continue
            samples[side] = f"{CASES_REL}/{cid}/{side}-{Path(f['path']).name}"
            target = copy / "dev/eval" / samples[side]
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(feedback.inside(dataset / "cases" / cid / side, f["path"]), target)
        ids = []
        for expect, side, reason in (
                ("pass", "after", f"ユーザーが確認画面で承認した版（{case['after']['delivery']}）。「{said}」という指摘が直っている"),
                ("fail", "before", f"ユーザーが「{said}」と指摘した版（{case['before']['delivery']}）")):
            if side not in samples:  # 修正前に無かったファイル（新しく作った出力）は、失敗の見本が無い
                continue
            ids.append(f"case-{next_id(doc['cases'], 'case')}")
            doc["cases"].append({"id": ids[-1], "behavior": behavior, "expect": expect, "situation": situation,
                                 "inputs": case.get("input", {}), "output": samples[side],
                                 "reason": reason, "agreed_in": talk,
                                 "feedback": {"case": cid, "delivery": case[side]["delivery"]}})
        tid = f"T-feedback-{next_id(tasks, 'T-feedback'):03d}"
        placed = []
        for f in case.get("input_files", []):
            if f.get("sha256"):
                rel = f"{INPUTS_REL}/{tid}/{f['path']}"
                target = feedback.inside(copy / INPUTS_REL / tid, f["path"])
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(feedback.inside(dataset / "cases" / cid / "inputs", f["path"]), target)
                placed.append({"from": rel, "to": f["path"]})
        tasks.append({"id": tid, "kind": "feedback", "prompt": case["request"], "input": case.get("input", {}),
                      "feedback_inputs": placed, "feedback": cid})
        links.append({"case": cid, "task": tid, "behavior": behavior, "eval_cases": ids, "file": pick["path"]})
        quotes.append(f"{cid}「{said}」（依頼「{first_line(case['request'], 60)}」）")
        picks.append(f"{cid} は {pick['path']}（{labels.get(pick.get('output'), '契約の出力ではない')}）")
        inputs.append(f"{tid} は入力の値 {json.dumps(case.get('input', {}), ensure_ascii=False)} と入力ファイル "
                      + ("・".join(p["to"] for p in placed) or "なし"))
    behaviors = [x["behavior"] for x in links]
    doc["questions"] = {"talk": talk, "items": [
        {"title": "一般化の範囲", "ask": "次の指摘を、どこまで一般化して評価しますか。" + "、".join(quotes),
         "why": "1回の指摘を広げすぎると別の依頼の出力まで縛り、狭すぎると同じ指摘が別の依頼で繰り返されるため。",
         "refs": behaviors,
         "options": [{"key": "A", "text": "その依頼と入力のときだけ"}, {"key": "B", "text": "同じ種類の依頼すべて"},
                     {"key": "C", "text": "ほかの範囲（書く）", "free": True}]},
        {"title": "成功と失敗の判定", "ask": "指摘を受けた版（修正前）を失敗、確認画面で承認した版（修正後）を成功とする判定に同意しますか。"
                                    "確認画面での承認は「この修正版で OK」という意味で、「今後この条件で評価してよい」という同意とは別に、ここで確かめます。",
         "why": "成果物の承認を、評価の条件への同意として扱わないため。",
         "refs": [i for x in links for i in x["eval_cases"]],
         "options": [{"key": "A", "text": "同意する"}, {"key": "B", "text": "同意しない（理由を書く）", "free": True}]},
        {"title": "判定するファイル", "ask": "判定するファイルは次でよいですか。" + "、".join(picks),
         "why": "指摘が向いていたファイルと、判定するファイルがずれると、直っていない出力を通すため。",
         "refs": behaviors,
         "options": [{"key": "A", "text": "よい"}, {"key": "B", "text": "ほかのファイル（書く）", "free": True}]},
        {"title": "足りない入力条件", "ask": "収束テストでは、元の依頼と次の入力だけで出力を作らせます。再現するのに足りない条件"
                                    "（ファイル、設定、git の状態など）はありますか。" + "、".join(inputs),
         "why": "指摘を受けたときと同じ条件で作らせないと、直ったかを確かめられないため。",
         "refs": [x["task"] for x in links],
         "options": [{"key": "A", "text": "無い"}, {"key": "B", "text": "ある（書く）", "free": True}]},
    ]}
    _lib.write_json(eval_path, doc)
    _lib.write_json(copy / TASKS_REL, tasks_doc)
    return {"copy": copy, "talk": talk, "links": links, "name": name, "synthetic": bool(data.get("synthetic"))}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--dataset", required=True, help="feedback.py export で取り出したディレクトリ")
    parser.add_argument("--skill", required=True, help="改善するスキル（正本。変えない）")
    parser.add_argument("--out", required=True, help="新しい作業場所（無いか空のディレクトリ）")
    args = parser.parse_args()
    dataset, skill, out = (Path(p).expanduser().resolve() for p in (args.dataset, args.skill, args.out))
    if not (skill / _lib.SPEC_REL).is_file():
        _lib.fail(f"{skill / _lib.SPEC_REL} がありません。skill-foundation で作ったスキルを指定してください")
    if out.exists() and (not out.is_dir() or any(out.iterdir())):
        _lib.fail(f"{out} は空ではありません。新しいディレクトリを指定してください")
    if out.is_relative_to(skill) or skill.is_relative_to(out):
        _lib.fail("作業場所は、改善するスキルの外の、スキルを含まない場所にしてください")
    found = feedback.dataset_problems(dataset)
    if found:
        print("\n".join(f"ERROR {p}" for p in found))
        print(f"feedback_eval: 取り出したものに問題が {len(found)} 件あります。feedback.py export で取り出し直してください")
        return 1
    data = rt.load_json(dataset / "dataset.json")
    spec = _lib.load_spec(skill)
    if data.get("skill") != spec.get("name"):
        _lib.fail(f"取り出したものは {data.get('skill')} の指摘です。改善するスキルは {spec.get('name')} です")
    if not data.get("cases"):
        _lib.fail("取り出したものに承認済みの指摘がありません")
    before = tree_hash(skill)
    made = build(dataset, skill, out)
    if tree_hash(skill) != before:
        _lib.fail("正本のスキルが変わりました。作業場所を消して、作り直してください")
    _lib.write_json(out / "candidate.json", {
        **STATUS, "skill": made["name"], "source": str(skill), "source_hash": before, "copy": made["copy"].relative_to(out).as_posix(),
        "dataset": "dataset", "talk": made["talk"], "synthetic": made["synthetic"], "created_at": rt.now(), "cases": made["links"]})
    copy = made["copy"]
    print(f"作業用コピー: {copy}（正本 {skill} は変えていない）")
    for x in made["links"]:
        print(f"  指摘 {x['case']} → 課題 {x['task']}、振る舞い {x['behavior']}、事例 {'・'.join(x['eval_cases'])}（判定するファイル {x['file']}）")
    print(f"状態: {STATUS['label']}（{made['talk']} の質問 4 件）")
    print(f"次: python3 {Path(__file__).parent / 'eval_check.py'} {copy} と python3 {Path(__file__).parent / 'catalog.py'} --project {out} を"
          f"実行し、カタログの {out / '.skill-runs/catalog' / (made['name'] + '.html')} の「Eval 作成」タブで答えてもらう。"
          "以降は作業用コピーを <base>/<name> として、SKILL.md の手順3から Eval 作成と収束テストを進める")
    return 0


if __name__ == "__main__":
    sys.exit(main())
