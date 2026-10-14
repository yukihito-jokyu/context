#!/usr/bin/env python3
"""Versioned skill refinement workflow. Standard library only."""
import argparse
import contextlib
import copy
import fcntl
import hashlib
import json
import math
import os
from pathlib import Path
import re
import shutil
import sys
import tempfile
import uuid
from datetime import datetime, timezone


class RefineError(ValueError):
    pass


def require(condition, message):
    if not condition:
        raise RefineError(message)


def now():
    return datetime.now(timezone.utc).isoformat()


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def atomic_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=".write-")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as out:
            json.dump(value, out, ensure_ascii=False, indent=2)
            out.write("\n")
            out.flush()
            os.fsync(out.fileno())
        os.replace(tmp, path)
    finally:
        if Path(tmp).exists():
            Path(tmp).unlink()


def digest(path):
    path = Path(path)
    require(path.exists(), f"missing: {path}")
    h = hashlib.sha256()
    files = sorted(path.rglob("*")) if path.is_dir() else [path]
    require(not path.is_symlink(), "symlinks are not supported")
    for item in files:
        if "__pycache__" in item.parts or item.name.endswith(".pyc") or item.name == ".DS_Store":
            continue
        require(not item.is_symlink(), f"symlink is not supported: {item}")
        if item.is_file():
            h.update(str(item.relative_to(path) if path.is_dir() else item.name).encode())
            h.update(b"\0")
            h.update(item.read_bytes())
            h.update(b"\0")
    return h.hexdigest()


def contained(root, path):
    root, path = Path(root).resolve(), Path(path).resolve()
    require(path.is_relative_to(root), "path leaves its allowed root")
    return path


def text(value, label):
    require(isinstance(value, str) and bool(value.strip()), f"{label} is required")
    return value


def skill_name(path):
    raw = (Path(path) / "SKILL.md").read_text(encoding="utf-8")
    match = re.match(r"\A---\s*\n(.*?)\n---", raw, re.S)
    require(match, "SKILL.md frontmatter is required")
    name = re.search(r"^name:\s*([a-z0-9-]+)\s*$", match[1], re.M)
    require(name, "a lowercase skill name is required")
    return name[1]


def resolve_skill(value):
    path = Path(value).expanduser()
    if path.is_dir():
        return path.resolve()
    require(re.fullmatch(r"[a-z0-9-]+", value), "skill path or name is invalid")
    project = next((p for p in (Path.cwd(), *Path.cwd().parents) if (p / ".git").exists()), Path.cwd())
    roots = [project / "utils/skills", project / ".agents/skills", project / ".codex/skills",
             project / ".claude/skills", Path.home() / ".agents/skills",
             Path.home() / ".codex/skills", Path.home() / ".claude/skills"]
    found = set()
    for root in roots:
        if not root.is_dir():
            continue
        for folder, dirs, files in os.walk(root, followlinks=True):
            relative = Path(folder).relative_to(root)
            if len(relative.parts) > 3:
                dirs[:] = []
                continue
            if "SKILL.md" in files:
                if Path(folder).name == value:
                    found.add(Path(folder).resolve())
                dirs[:] = []  # A bundled skill is not a separately discoverable candidate.
    require(len(found) == 1, "skill name is missing or ambiguous; supply its canonical path")
    return found.pop()


def init(workspace, spec):
    require(isinstance(spec.get("skill"), str), "exactly one skill path is required")
    target = resolve_skill(spec["skill"])
    name = skill_name(target)
    cases = spec.get("cases")
    require(isinstance(cases, list) and cases, "at least one task is required")
    ids = set()
    for case in cases:
        require(isinstance(case, dict), "each case is an object")
        cid = text(case.get("id"), "case id")
        require(re.fullmatch(r"[a-zA-Z0-9_-]+", cid), "invalid case id")
        require(cid not in ids, "duplicate case id")
        ids.add(cid)
        text(case.get("task"), "task")
        require(isinstance(case.get("files", []), list), "files must be a list")
        for file in case.get("files", []):
            require(isinstance(file, str) and Path(file).is_file(), "input file is missing")
            digest(Path(file))
    workspace = Path(workspace).resolve()
    require(not workspace.is_relative_to(target), "workspace must be outside the target skill")
    require(not (workspace / "state.json").exists(), "workspace already initialized; use status to resume")
    require(not any((workspace / name).exists() for name in
                    ("skill-snapshot", "inputs", "candidate-skill", "evals", "analyses")),
            "workspace contains workflow data without state; choose a new workspace")
    source_hash = digest(target)
    workspace.mkdir(parents=True, exist_ok=True)
    snapshot = workspace / "skill-snapshot" / name
    shutil.copytree(target, snapshot, ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".DS_Store"))
    safe_cases = []
    for case in cases:
        files = []
        for index, source in enumerate(case.get("files", [])):
            dest = workspace / "inputs" / case["id"] / f"{index}-{Path(source).name}"
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, dest)
            files.append({"path": str(dest), "hash": digest(dest)})
        safe_cases.append({"id": case["id"], "task": case["task"], "files": files})
    state = {"schema": 1, "revision": 1, "name": name, "target": str(target),
             "target_hash": source_hash, "skill": str(snapshot), "skill_hash": digest(snapshot),
             "workspace": str(workspace), "cases": safe_cases, "iteration": 0,
             "stage": "input_review", "runs": [], "rubric": None, "analysis": None,
             "loop": None, "approvals": [], "responses": [], "history": [],
             "hook_checks": [], "created_at": now()}
    log(state, "initialized")
    atomic_json(workspace / "state.json", state)
    return state


def log(state, event, **fields):
    state["history"].append({"at": now(), "event": event, **fields})


def integrity(state):
    require(digest(state["target"]) == state["target_hash"], "target changed outside promotion")
    for case in state["cases"]:
        for file in case["files"]:
            require(digest(file["path"]) == file["hash"], "an input changed")
    require(digest(state["skill"]) == state["skill_hash"], "frozen skill changed")
    if state["rubric"]:
        require(digest(state["rubric"]["path"]) == state["rubric"]["hash"], "rubric changed")
    if state["analysis"]:
        require(digest(state["analysis"]["path"]) == state["analysis"]["hash"], "analysis changed")
    for run in state["runs"]:
        if run.get("artifacts_hash"):
            require(digest(run["output"]) == run["artifacts_hash"], "a completed artifact changed")


@contextlib.contextmanager
def locked(workspace):
    workspace = Path(workspace).resolve()
    require((workspace / "state.json").is_file(), "workspace is not initialized")
    with (workspace / ".lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        state = read_json(workspace / "state.json")
        integrity(state)
        yield state
        state["revision"] += 1
        state["updated_at"] = now()
        atomic_json(workspace / "state.json", state)


def current_runs(state, role):
    return [r for r in state["runs"] if r["iteration"] == state["iteration"] and r["role"] == role]


def run_by_id(state, run_id):
    found = [r for r in state["runs"] if r["id"] == run_id]
    require(len(found) == 1, "unknown run")
    return found[0]


def ticket(state, case_id, role):
    require(not any(not r["processed"] for r in state["responses"]), "handle submitted HTML responses first")
    require(role in ("generate", "evaluate"), "unknown role")
    require((role == "generate" and state["stage"] in ("generating", "editing")) or
            (role == "evaluate" and state["stage"] == "evaluating"), "this run is not allowed now")
    case = next((c for c in state["cases"] if c["id"] == case_id), None)
    require(case is not None, "unknown case")
    require(not any(r["case"] == case_id for r in current_runs(state, role)), "case already has a run")
    if state["stage"] == "editing":
        state["skill_hash"] = digest(state["skill"])
        state["stage"] = "generating"
    run_id = uuid.uuid4().hex
    output = Path(state["workspace"]) / f"iteration-{state['iteration']}" / case_id / role / run_id
    output.mkdir(parents=True, exist_ok=False)
    if role == "generate":
        # No parent history, rubric, human feedback, improvement analysis or orchestrator skill.
        prompt = (f"このスキルを使ってタスクを実行してください。\nスキル: {state['skill']}\n"
                  f"タスク: {case['task']}\n入力ファイル: " +
                  json.dumps([f["path"] for f in case["files"]], ensure_ascii=False) +
                  f"\n成果物の保存先: {output}\n実行ID: {run_id}")
        rubric_hash = None
    else:
        generated = next((r for r in current_runs(state, "generate") if r["case"] == case_id), None)
        require(generated and generated["status"] == "complete", "generation is incomplete")
        prompt = (f"成果物を次の評価基準で評価してください。\n題材: {case['task']}\n"
                  f"成果物: {generated['output']}\n評価基準: {state['rubric']['path']}\n"
                  f"結果の保存先: {output}\n実行ID: {run_id}\n"
                  'result.jsonを保存してください。形式: {"status":"ok","grades":'
                  '[{"id":"評価項目ID","score":0.0,"evidence":"根拠"}]}。'
                  'scoreは0〜1。評価不能ならstatusをerrorにし、reasonを記載してください。')
        rubric_hash = state["rubric"]["hash"]
    run = {"id": run_id, "case": case_id, "iteration": state["iteration"], "role": role,
           "prompt": prompt, "prompt_hash": hashlib.sha256(prompt.encode()).hexdigest(),
           "output": str(output), "skill_hash": state["skill_hash"], "rubric_hash": rubric_hash,
           "status": "pending", "agent_id": None}
    state["runs"].append(run)
    log(state, "ticket", run_id=run_id, role=role, case=case_id)
    return {"run_id": run_id, "prompt": prompt, "fork_turns": "none", "output": str(output)}


def register(state, run_id, agent_id):
    run = run_by_id(state, run_id)
    text(agent_id, "agent id")
    if run["status"] == "running" and run["agent_id"] == agent_id:
        return
    require(run["status"] == "pending", "run is not pending")
    require(not any(r["agent_id"] == agent_id for r in state["runs"]), "agent id was already used")
    run["agent_id"], run["status"] = agent_id, "running"
    log(state, "registered", run_id=run_id, agent_id=agent_id)


def fail_run(state, run, reason):
    run["status"], run["error"] = "error", text(reason, "failure reason")
    state["loop"] = None
    state["stage"] = "error_review"
    log(state, "run_failed", run_id=run["id"], reason=reason)


def finish(state, run_id, result=None):
    run = run_by_id(state, run_id)
    require(run["status"] == "running" and run["agent_id"], "a fresh agent must be registered first")
    require(run["iteration"] == state["iteration"], "run belongs to an old iteration")
    require(state["stage"] in ("generating", "evaluating"), "workflow is not accepting results")
    if result and result.get("status") == "error":
        fail_run(state, run, result.get("reason"))
        return
    require(any(p.is_file() for p in Path(run["output"]).rglob("*")), "run produced no artifacts")
    if run["role"] == "evaluate":
        require(result and result.get("status") == "ok", "evaluation result is required")
        rubric = read_json(state["rubric"]["path"])
        grades = result.get("grades", [])
        require(isinstance(grades, list) and all(isinstance(g, dict) for g in grades), "invalid grades")
        expected = {c["id"] for c in rubric["criteria"]}
        require(len(grades) == len(expected) and {g.get("id") for g in grades} == expected,
                "every criterion needs exactly one grade")
        for grade in grades:
            score = grade.get("score")
            require(isinstance(score, (int, float)) and not isinstance(score, bool) and
                    math.isfinite(score) and 0 <= score <= 1, "score must be between 0 and 1")
            text(grade.get("evidence"), "grading evidence")
        scores = {g["id"]: g["score"] for g in grades}
        total = sum(c["weight"] for c in rubric["criteria"])
        run["score"] = sum(c["weight"] * scores[c["id"]] for c in rubric["criteria"]) / total
        run["passed"] = run["score"] >= rubric["threshold"] and all(
            scores[c["id"]] >= c.get("minimum", 0) for c in rubric["criteria"])
        run["grades"] = grades
        atomic_json(Path(run["output"]) / "result.json", result)
    run["status"], run["artifacts_hash"] = "complete", digest(run["output"])
    log(state, "completed", run_id=run_id, score=run.get("score"), passed=run.get("passed"))
    runs = current_runs(state, run["role"])
    if len(runs) == len(state["cases"]) and all(r["status"] == "complete" for r in runs):
        if run["role"] == "generate":
            state["stage"] = "feedback_review" if state["iteration"] == 0 else "evaluating"
        elif state["iteration"] == 0:
            state["stage"] = "analysis_needed"
        elif all(r["passed"] for r in runs):
            state["stage"] = "final_review"
            state["loop"] = None
        elif state["loop"] and state["iteration"] - state["loop"]["start"] < state["loop"]["limit"]:
            state["stage"] = "analysis_needed"
        else:
            state["stage"] = "results_review"
            state["loop"] = None


def publish_rubric(state, rubric):
    require(not any(not r["processed"] for r in state["responses"]), "handle submitted HTML responses first")
    require(state["stage"] in ("rubric_needed", "rubric_review"), "cannot publish a rubric now")
    criteria = rubric.get("criteria")
    require(isinstance(criteria, list) and criteria, "criteria are required")
    ids = set()
    for criterion in criteria:
        require(isinstance(criterion, dict), "each criterion is an object")
        cid = text(criterion.get("id"), "criterion id")
        require(cid not in ids, "duplicate criterion")
        ids.add(cid)
        for key in ("label", "method", "feedback"):
            text(criterion.get(key), key)
        weight = criterion.get("weight")
        require(isinstance(weight, (int, float)) and not isinstance(weight, bool) and
                math.isfinite(weight) and weight > 0, "weight must be positive")
        minimum = criterion.get("minimum", 0)
        require(isinstance(minimum, (int, float)) and not isinstance(minimum, bool) and
                math.isfinite(minimum) and 0 <= minimum <= 1, "minimum must be 0..1")
    threshold = rubric.get("threshold")
    require(isinstance(threshold, (int, float)) and not isinstance(threshold, bool) and
            math.isfinite(threshold) and 0 <= threshold <= 1, "threshold must be 0..1")
    dest = Path(state["workspace"]) / "evals" / f"rubric-{uuid.uuid4().hex}.json"
    atomic_json(dest, rubric)
    state["rubric"] = {"path": str(dest), "hash": digest(dest)}
    state["stage"] = "rubric_review"
    log(state, "rubric_published", hash=state["rubric"]["hash"])


def validate_analysis(state, analysis):
    text(analysis.get("summary"), "analysis summary")
    changes = analysis.get("changes")
    require(isinstance(changes, list) and changes, "at least one change is required")
    paths = set()
    for change in changes:
        require(isinstance(change, dict), "each change is an object")
        path = text(change.get("path"), "change path")
        require(not Path(path).is_absolute() and ".." not in Path(path).parts, "invalid change path")
        require(path not in paths, "one replacement per file is supported")
        paths.add(path)
        text(change.get("reason"), "change reason")
        require(isinstance(change.get("after"), str), "replacement text is required")
        dest = contained(state["skill"], Path(state["skill"]) / path)
        before = change.get("before")
        if before is None:
            require(not dest.exists(), "new file already exists")
        else:
            text(before, "original text")
            require(dest.is_file() and dest.read_text(encoding="utf-8").count(before) == 1,
                    "original text must occur exactly once")


def apply_analysis(state):
    analysis = read_json(state["analysis"]["path"])
    validate_analysis(state, analysis)
    iteration = state["iteration"] + 1
    dest = Path(state["workspace"]) / "candidate-skill" / f"iteration-{iteration}" / state["name"]
    require(not dest.exists(), "candidate directory already exists")
    dest.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(dir=dest.parent, prefix=".candidate-"))
    try:
        shutil.copytree(state["skill"], staging, dirs_exist_ok=True,
                        ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".DS_Store"))
        for change in analysis["changes"]:
            path = contained(staging, staging / change["path"])
            path.parent.mkdir(parents=True, exist_ok=True)
            if change.get("before") is None:
                value = change["after"]
            else:
                value = path.read_text(encoding="utf-8").replace(change["before"], change["after"], 1)
            path.write_text(value, encoding="utf-8")
        require(skill_name(staging) == state["name"], "candidate must preserve the skill name")
        os.replace(staging, dest)
    finally:
        if staging.exists():
            shutil.rmtree(staging)
    state["skill"], state["skill_hash"] = str(dest), digest(dest)
    state["iteration"], state["stage"] = iteration, "editing"
    log(state, "candidate_created", iteration=iteration, hash=state["skill_hash"])


def publish_analysis(state, analysis):
    require(not any(not r["processed"] for r in state["responses"]), "handle submitted HTML responses first")
    require(state["stage"] in ("analysis_needed", "analysis_review"), "cannot publish analysis now")
    validate_analysis(state, analysis)
    if state["loop"]:
        require({c["path"] for c in analysis["changes"]}.issubset(state["loop"]["paths"]),
                "automatic improvement leaves the approved file scope; pause for review")
    dest = Path(state["workspace"]) / "analyses" / f"analysis-{uuid.uuid4().hex}.json"
    atomic_json(dest, analysis)
    state["analysis"] = {"path": str(dest), "hash": digest(dest)}
    state["stage"] = "analysis_review"
    log(state, "analysis_published", hash=state["analysis"]["hash"])
    if state["loop"]:
        apply_analysis(state)


def human_response(state, response):
    require(isinstance(response, dict), "response must be an object")
    require(isinstance(response.get("revision"), int) and not isinstance(response.get("revision"), bool),
            "revision must be an integer")
    require(response.get("revision") == state["revision"], "page is stale; reload before submitting")
    require(response.get("stage") == state["stage"], "page stage changed")
    action = response.get("action")
    notes = response.get("notes", "")
    require(isinstance(notes, str), "notes must be text")
    record = {"id": uuid.uuid4().hex, "at": now(), "revision": state["revision"],
              "stage": state["stage"], "action": action, "notes": notes,
              "skill_hash": state["skill_hash"], "rubric_hash": (state["rubric"] or {}).get("hash"),
              "analysis_hash": (state["analysis"] or {}).get("hash"), "processed": False}
    if action == "comment":
        text(notes, "comment")
    elif action == "pause":
        state["resume_stage"], state["stage"] = state["stage"], "paused"
        state["loop"] = None
    elif state["stage"] == "paused" and action == "resume":
        state["stage"] = state.pop("resume_stage")
    elif state["stage"] == "input_review" and action == "approve":
        state["stage"] = "generating"
    elif state["stage"] == "feedback_review" and action == "feedback":
        text(notes, "human feedback")
        state["stage"] = "rubric_needed"
    elif state["stage"] == "rubric_review" and action == "approve":
        state["stage"] = "evaluating"
    elif state["stage"] == "analysis_review" and action == "approve":
        apply_analysis(state)
    elif state["stage"] == "results_review" and action in ("step", "loop"):
        if action == "loop":
            state["loop"] = {"start": state["iteration"], "limit": 3,
                             "rubric_hash": state["rubric"]["hash"], "response_id": record["id"],
                             "paths": [c["path"] for c in read_json(state["analysis"]["path"])["changes"]]}
        state["stage"] = "analysis_needed"
    elif state["stage"] == "final_review" and action == "approve":
        state["stage"] = "promotion_ready"
    elif state["stage"] == "error_review" and action == "retry":
        role = next(r["role"] for r in current_runs(state, "generate") +
                    current_runs(state, "evaluate") if r["status"] == "error")
        # Keep the failed agent in the ledger; a new ticket is required.
        for run in state["runs"]:
            if run["iteration"] == state["iteration"] and run["status"] == "error":
                run["role"] = "failed_" + run["role"]
        state["stage"] = "generating" if role == "generate" else "evaluating"
    else:
        raise RefineError("this human action is not available at this stage")
    state["responses"].append(record)
    if action == "approve":
        state["approvals"].append(copy.deepcopy(record))
    log(state, "human_response", response_id=record["id"], action=action)
    return record


def acknowledge(state, response_id, answer):
    found = next((r for r in state["responses"] if r["id"] == response_id), None)
    require(found and not found["processed"], "response is missing or already processed")
    found["answer"], found["processed"] = text(answer, "answer"), True
    log(state, "response_handled", response_id=response_id)


def promote(state):
    require(state["stage"] == "promotion_ready", "final HTML approval is required")
    require(state["iteration"] > 0, "there is no candidate to promote")
    require(all(r["passed"] for r in current_runs(state, "evaluate")), "candidate has failed grades")
    require(digest(state["skill"]) == state["skill_hash"], "candidate changed after approval")
    shutil.copytree(state["skill"], state["target"], dirs_exist_ok=True)
    state["target_hash"] = digest(state["target"])
    require(state["target_hash"] == state["skill_hash"], "promotion did not match candidate")
    state["stage"] = "complete"
    log(state, "promoted", hash=state["target_hash"])


def status(state):
    return {"stage": state["stage"], "revision": state["revision"], "iteration": state["iteration"],
            "pending_responses": [r for r in state["responses"] if not r["processed"]],
            "runs": [{k: r[k] for k in ("id", "case", "role", "status", "agent_id")} for r in state["runs"]]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", required=True)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("init").add_argument("--input", required=True)
    sub.add_parser("status")
    prepare = sub.add_parser("ticket")
    prepare.add_argument("--case", required=True)
    prepare.add_argument("--role", choices=["generate", "evaluate"], required=True)
    reg = sub.add_parser("register")
    reg.add_argument("--run", required=True)
    reg.add_argument("--agent", required=True)
    done = sub.add_parser("finish")
    done.add_argument("--run", required=True)
    done.add_argument("--result")
    for command in ("rubric", "analysis"):
        sub.add_parser(command).add_argument("--input", required=True)
    ack = sub.add_parser("ack")
    ack.add_argument("--response", required=True)
    ack.add_argument("--answer", required=True)
    sub.add_parser("promote")
    imported = sub.add_parser("import-response")
    imported.add_argument("--input", required=True)
    imported.add_argument("--user-statement", required=True,
                          help="actual user statement that explicitly shares this HTML response")
    active = sub.add_parser("activate")
    active.add_argument("--root", required=True)
    args = parser.parse_args()
    if args.command == "init":
        result = status(init(args.workspace, read_json(args.input)))
    elif args.command in ("status", "activate"):
        state = read_json(Path(args.workspace) / "state.json")
        integrity(state)
        if args.command == "activate":
            atomic_json(Path(args.root) / ".skill-refiner-active.json",
                        {"workspace": str(Path(args.workspace).resolve())})
        result = status(state)
    else:
        with locked(args.workspace) as state:
            result = None
            if args.command == "ticket":
                result = ticket(state, args.case, args.role)
            elif args.command == "register":
                register(state, args.run, args.agent)
            elif args.command == "finish":
                finish(state, args.run, read_json(args.result) if args.result else None)
            elif args.command == "rubric":
                publish_rubric(state, read_json(args.input))
            elif args.command == "analysis":
                publish_analysis(state, read_json(args.input))
            elif args.command == "ack":
                acknowledge(state, args.response, args.answer)
            elif args.command == "promote":
                promote(state)
            elif args.command == "import-response":
                record = human_response(state, read_json(args.input))
                record["source"] = "HTML response explicitly shared in conversation"
                record["user_statement"] = text(args.user_statement, "actual user statement")
                for approval in state["approvals"]:
                    if approval["id"] == record["id"]:
                        approval.update({"source": record["source"], "user_statement": record["user_statement"]})
            if result is None:
                result = status(state)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    try:
        main()
    except (RefineError, OSError, json.JSONDecodeError) as exc:
        print(f"STOP: {exc}", file=sys.stderr)
        sys.exit(2)
