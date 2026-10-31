#!/usr/bin/env python3
"""Prepare an isolated skill + Eval/convergence draft from approved feedback.

Approval of one corrected artifact is evidence for that example, not approval of a
general evaluation rubric. The draft therefore has pending user questions and cannot
pass eval_check.py or start convergence runs until the normal Eval review is complete.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil
import sys

import _lib
import feedback as fb


def safe_path(base: Path, rel: str) -> Path:
    path = (base / rel).resolve()
    if Path(rel).is_absolute() or not path.is_relative_to(base.resolve()):
        raise fb.FeedbackError("Invalid stored path: " + rel)
    return path


def example(dataset: Path, destination: Path, delivery: dict) -> None:
    """Readable artifact set, with the original bytes preserved alongside the manifest."""
    artifacts = []
    for index, item in enumerate(delivery["artifacts"], 1):
        raw = fb.blob(dataset, item)
        file = destination.parent / (destination.stem + "-files") / str(index) / Path(item["path"]).name
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_bytes(raw)
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError:
            text = None
        artifacts.append({"path": item["path"], "output": item["output"], "media_type": item["media_type"],
                          "sha256": item["sha256"], "file": file.relative_to(destination.parent).as_posix(), "text": text})
    fb.atomic_json(destination, {"artifacts": artifacts})


def prepare(dataset: Path, skill: Path, output: Path) -> dict:
    data = json.loads((dataset / "feedback.json").read_text(encoding="utf-8"))
    fb.validate(dataset, data)
    cases = [c for c in data["cases"] if c["status"] == "approved"]
    if not cases:
        raise fb.FeedbackError("No approved feedback cases")
    contract = json.loads((skill / "assets/contract.json").read_text(encoding="utf-8"))
    if data["skill"] != contract["skill"]:
        raise fb.FeedbackError("Feedback and skill names do not match")
    if output.exists() or output.is_relative_to(skill):
        raise fb.FeedbackError("Choose a new workspace outside the source skill")
    if any(p.is_symlink() for p in skill.rglob("*")):
        raise fb.FeedbackError("Use the resolved skill directory without nested symbolic links")
    candidate_rel = "skills/" + data["skill"]
    candidate = output / candidate_rel
    shutil.copytree(skill, candidate, ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".git", ".skill-runs", fb.DIRECTORY))
    # Keep the previous development material for reference, outside the candidate.
    for relative in ("dev/eval", "dev/evals.json", "dev/results"):
        source = candidate / relative
        if source.exists():
            destination = output / "previous" / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(source), str(destination))
    shutil.copytree(dataset, output / "feedback-corpus")
    doc = {"skip_reason": "", "materials": {k: [] for k in ("scenes", "pains", "wants", "unacceptable")},
           "dialog": [], "hypotheses": [], "values": [], "behaviors": [], "cases": [],
           "questions": {"talk": "talk-1", "items": []},
           "feedback_sources": [c["id"] for c in cases]}
    tasks = []
    deliveries = {d["id"]: d for d in data["deliveries"]}
    for n, case in enumerate(cases, 1):
        before, after = deliveries[case["before"]], deliveries[case["after"]]
        issue = case["issue"]["text"]
        situation = case["request"] or json.dumps(case["inputs"], ensure_ascii=False)
        for key, prefix, text in (("scenes", "scene", situation), ("pains", "pain", issue),
                                  ("wants", "want", "この指摘について承認済みの修正版と同じ条件を満たす成果物"),
                                  ("unacceptable", "ng", issue)):
            doc["materials"][key].append({"id": f"{prefix}-{n}", "text": text, "feedback": case["id"]})
        doc["hypotheses"].append({"id": f"hyp-{n}", "text": issue,
                                  "from": [f"scene-{n}", f"pain-{n}", f"want-{n}"]})
        doc["values"].append({"id": f"value-{n}", "text": issue, "from": [f"hyp-{n}"], "confirmed_in": "talk-1"})
        targets = [o["path"] for o in after["contract"].get("outputs", [])]
        doc["behaviors"].append({"id": f"behavior-{n}", "value": f"value-{n}", "text": issue,
                                 "target": targets[0] if targets else "",
                                 "judge": {"type": "model", "rubric":
                                           "依頼の状況で、次の指摘を解消する条件を満たすかを判定する。指摘: " + issue
                                           + "。承認済み修正版と修正前の事例を比較し、この指摘に関係する差だけを採点する。"}})
        for phase, delivery, expect in (("before", before, "fail"), ("after", after, "pass")):
            relative = f"cases/feedback-{n}-{phase}.json"
            example(dataset, candidate / "dev/eval" / relative, delivery)
            doc["cases"].append({"id": f"case-{2*n-1 if phase == 'before' else 2*n}", "behavior": f"behavior-{n}",
                                 "expect": expect, "situation": situation, "output": relative,
                                 "reason": issue if phase == "before" else case["approval"]["text"],
                                 "agreed_in": ["talk-1"], "feedback": case["id"],
                                 **({"covers": [f"ng-{n}"]} if phase == "before" else {})})
        input_files = []
        for item in case["context"]:
            relative = f"dev/feedback-inputs/{case['id']}/{item['path']}"
            destination = safe_path(candidate, relative)
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(fb.blob(dataset, item))
            input_files.append({"source": relative, "path": item["path"]})
        # The producer gets the original request and inputs, never the correction,
        # approval, expected outputs, or evaluation rubric.
        tasks.append({"id": f"T-feedback-{n}", "kind": "typical", "prompt": situation,
                      "aim": "実際に指摘があった依頼で、承認済みの評価条件を満たすか", "fixture": None,
                      "setup": [], "input_files": input_files,
                      "feedback_source": case["id"], "input_values": case["inputs"]})
        doc["questions"]["items"].append({"title": f"指摘 {n} を評価条件にする",
            "ask": f"指摘「{issue}」について、修正前を失敗、承認した修正版を成功とする判定に同意しますか。"
                   "この条件を一般化する範囲、判定対象のファイル、元の依頼・入力ファイルで再現できるかも確認してください。",
            "why": "修正版の承認と、一般的な評価条件・再現条件への同意を分けて確かめるため。",
            "refs": [f"value-{n}", f"behavior-{n}", f"case-{2*n-1}", f"case-{2*n}", f"T-feedback-{n}"]})
    fb.atomic_json(candidate / "dev/eval/eval.json", doc)
    fb.atomic_json(candidate / "dev/evals.json", {"tasks": tasks})
    spec_path = candidate / "dev/spec.json"
    if spec_path.exists():
        spec = json.loads(spec_path.read_text(encoding="utf-8"))
        spec.setdefault("convergence", {}).pop("skip_reason", None)
        fb.atomic_json(spec_path, spec)
    fb.atomic_json(output / "preparation.json", {"schema_version": 1, "skill": data["skill"],
        "feedback_cases": [c["id"] for c in cases], "candidate": candidate_rel, "rubric_status": "awaiting_user_review",
        "source_skill": {"files": {str(p.relative_to(skill)): rt_hash(p) for p in sorted(skill.rglob('*')) if p.is_file()}},
        "recorded_versions": sorted({c["skill"]["revision"] for c in cases})})
    (output / "README.md").write_text(
        "# 収集した指摘からスキルを改善する\n\n"
        f"`{candidate_rel}/` は作業用コピー、`feedback-corpus/` は承認済みの事例と元のスキルの版です。元のスキルは変更していません。\n\n"
        "1. 指摘の原文、修正前後の実ファイル、承認の原文を読み、一般化する評価条件を作ります。"
        f"`{candidate_rel}/dev/eval/eval.json` は候補です。修正版への承認を、評価基準への承認に読み替えません。\n"
        "2. 元の依頼と入力を確かめます。未記録の入力は `dev/feedback-inputs/` に補い、題材の `input_files` に登録します。"
        "画像・PDF等の原本も保存されています。バイナリを文字列として採点せず、実ファイルを見られる判定方法を決めます。\n"
        "3. 通常の Eval 作成の対話で価値・判定・成功失敗の事例・入力条件を確認し、`eval_check.py` に通します。"
        "一般的な依頼、既定値、境目、holdout の課題も加えます。収集事例だけで未知の依頼まで改善したとは扱いません。\n"
        f"4. `convergence.py prepare {candidate_rel} --round 1 --workdir <新しい作業場所>` で独立実行を準備します。"
        "実行回数の確認は既存の規則に従います。生成担当へ指摘・修正版・正解・採点基準を渡さず、別の評価担当が Eval で採点します。\n"
        "5. 元の版と候補版を同じ題材・Evalで比べ、改善内容と残った問題を確認してから採用します。\n",
        encoding="utf-8")
    return {"workspace": str(output), "cases": len(cases), "eval": candidate_rel + "/dev/eval/eval.json",
            "tasks": candidate_rel + "/dev/evals.json", "status": "awaiting_user_review"}


def rt_hash(path: Path) -> str:
    return fb.digest(path.read_bytes())


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, required=True, help="feedback.py export が書いたディレクトリ")
    parser.add_argument("--skill", type=Path, required=True, help="改善するスキルの正本")
    parser.add_argument("--out", type=Path, required=True, help="新しい作業用ディレクトリ")
    args = parser.parse_args()
    print(json.dumps(prepare(args.dataset.resolve(), args.skill.resolve(), args.out.resolve()), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (fb.FeedbackError, OSError, KeyError, ValueError) as exc:
        print("ERROR feedback Eval: " + str(exc), file=sys.stderr)
        sys.exit(1)
