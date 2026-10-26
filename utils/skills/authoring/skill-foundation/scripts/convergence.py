#!/usr/bin/env python3
"""収束テスト: 作成に関わっていない独立エージェント（Claude Code と Codex）に同じ依頼を解かせ、出力の違いを測る。

サブコマンド:
  prepare        課題 × runner × 人数の分だけ、一時プロジェクトを作ってスキルを置き、plan.json を書く。
                 課題ごとに、作業の前からある名前（英字の識別子）を記録する（names の指標に使う）
  prompts        runner subagent の実行ごとに、Agent ツールに渡すプロンプトと、最終の返答の保存先を出す
  run            plan の各プロジェクトで runner（claude -p / codex exec）を実行し、結果を _results/ に保存する。
                 runner subagent は起動せず、保存された最終の返答を集める
  diff           課題ごとにプロジェクト同士を比べ、指標とレポート（report.json / report.md / *.patch）を書く。
                 スキル自身を変えたか、このスキルの hooks の登録を外したエージェントがいる課題は基準を満たさない
  review-prepare dev/probes.json の reviews の見本ごとに、違反を入れた出力のあるプロジェクトを作り、
                 「完了前チェックリストで確かめて」という依頼を plan.json に書く（prompts と run は --kind review）
  review-score   レビューの返答に出たルールIDを数え、見本ごとの検出率・余計な指摘・エージェント間の一致を
                 review.json / review.md に書く

runner の既定（spec の convergence.runner_commands で上書きできる。{prompt} と {dir} が置き換わる）:
  claude: claude -p --output-format json --permission-mode acceptEdits --no-session-persistence
          --setting-sources project,local --allowedTools ...（ユーザー単位の設定を読まない）
  codex : codex exec --json --sandbox workspace-write --skip-git-repo-check --ephemeral
          --dangerously-bypass-hook-trust（一時プロジェクトの hooks は信頼の手続きを経ていないため）
  subagent: このスクリプトは起動しない。呼び出し元の AI が、prompts の出したプロンプトを、文脈を引き継がない
          新しいエージェント（Agent ツール）にそのまま渡す。hooks は働かず、自動の起動は説明文を渡した近似になる

例:
  python3 convergence.py prepare <スキル> --round 1 [--runners subagent]
  python3 convergence.py prompts --workdir <W> --round 1      # runner subagent のときだけ
  python3 convergence.py run --workdir <W> --round 1
  python3 convergence.py diff --workdir <W> --round 1 --out <スキル>/dev/results/convergence/round-1
  python3 convergence.py review-prepare <スキル> --round 2 --workdir <W>   # 最後のラウンド
  python3 convergence.py run --workdir <W> --round 2 --kind review
  python3 convergence.py review-score --workdir <W> --round 2 --out <スキル>/dev/results/convergence/round-2
"""

from __future__ import annotations

import argparse
import difflib
import glob
import hashlib
import itertools
import json
import os
import re
import shutil
import sys
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _lib  # noqa: E402
import _skillrt as rt  # noqa: E402

PLACES = {"claude": ".claude/skills", "codex": ".agents/skills"}
CLAUDE_TOOLS = ["Skill", "Read", "Write", "Edit", "Glob", "Grep", "Bash(python3 *)", "Bash(git diff *)",
                "Bash(git status *)", "Bash(git log *)", "Bash(ls *)", "Bash(cat *)"]
INVOKE = {"claude": "/{name} ", "codex": "${name} "}
RUNNERS = ["claude", "codex", "subagent"]
# subagent は呼び出し元のセッションの作業ディレクトリで動き、一時プロジェクトのスキル一覧を見ない。それを前置きで補う
SUBAGENT_HEAD = {
    "ja": {"dir": "作業ディレクトリは `{dir}` である。この中だけで作業する。\n"
                  "- コマンドは、毎回 `cd {dir} && ` を先頭に付けて実行する\n"
                  "- ファイルは `{dir}` の下の絶対パスで読み書きする。このディレクトリの外は読まず、変えない\n\n",
           "implicit": "このプロジェクトには次のスキルがある。依頼に合うスキルがあれば、その SKILL.md を読み、書かれた手順に従う。\n"
                       "- {name}（`{path}`）: {description}\n\n",
           "explicit": "スキル {name} を使う。`{path}` を読み、書かれた手順に従う。\n\n",
           "request": "依頼:\n"},
    "en": {"dir": "Your working directory is `{dir}`. Work only inside it.\n"
                  "- Prefix every command with `cd {dir} && `\n"
                  "- Read and write files by absolute paths under `{dir}`. Do not read or change anything outside it\n\n",
           "implicit": "This project has the following skill. If it fits the request, read its SKILL.md and follow the steps in it.\n"
                       "- {name} (`{path}`): {description}\n\n",
           "explicit": "Use the skill {name}. Read `{path}` and follow the steps in it.\n\n",
           "request": "Request:\n"},
}
REVIEW_ASK = {
    "ja": "{name} スキルで作った出力 {paths} を、`{skill_md}` の「6. 完了前チェックリスト」の項目ごとに確かめてください。"
          "この出力は、依頼「{text}」と入力 {inputs} から作られました。守られていない項目があれば、その項目の ID と理由を"
          "`<ID> <理由>` の形で1行に1つ書いてください。すべて守られていれば「指摘なし」とだけ書いてください。ファイルは変えないでください。",
    "en": "Check the outputs {paths} made with the {name} skill against each item of \"6. Pre-completion checklist\" in "
          "`{skill_md}`. They were made from the request \"{text}\" and the inputs {inputs}. For each item that is not met, "
          "write its ID and the reason as `<ID> <reason>`, one per line. If every item is met, write only \"no findings\". "
          "Do not change any file.",
}
SKIP = {".git", "__pycache__", "node_modules", ".venv"}
MAX_BYTES = 1_000_000
IDENT = re.compile(r"[A-Za-z_][A-Za-z0-9_]*(?:-[A-Za-z0-9_]+)*")


def default_runner(runner: str) -> list[str]:
    if runner == "claude":
        return ["claude", "-p", "{prompt}", "--output-format", "json", "--permission-mode", "acceptEdits",
                "--no-session-persistence", "--setting-sources", "project,local", "--allowedTools", *CLAUDE_TOOLS]
    return [codex_binary(), "exec", "--json", "--sandbox", "workspace-write", "--skip-git-repo-check", "--ephemeral",
            "--dangerously-bypass-hook-trust", "-c", 'projects."{dir}".trust_level="trusted"', "-C", "{dir}",
            "-o", "{last}", "{prompt}"]


def codex_binary() -> str:
    found = shutil.which("codex") or os.environ.get("SKILL_FOUNDATION_CODEX")
    if found:
        return found
    home = os.environ.get("CODEX_HOME", str(Path.home() / ".codex"))
    candidates = sorted(glob.glob(f"{home}/packages/*/current/bin/codex"))
    return candidates[0] if candidates else "codex"


def subagent_prompt(spec: dict, task: dict, target: Path, installed: Path) -> str:
    t = SUBAGENT_HEAD.get(spec.get("language"), SUBAGENT_HEAD["ja"])
    skill_md = installed / "SKILL.md"
    front, _ = _lib.parse_frontmatter(skill_md.read_text(encoding="utf-8"))
    skill = t["explicit" if task.get("invoke") == "explicit" else "implicit"]
    return (t["dir"].replace("{dir}", str(target))
            + skill.replace("{name}", spec["name"]).replace("{path}", str(skill_md))
            .replace("{description}", (front or {}).get("description", ""))
            + t["request"] + task["prompt"])


def round_dir(workdir: Path, rnd: int, kind: str = "task") -> Path:
    return workdir / (f"round-{rnd}" if kind == "task" else f"review-{rnd}")


def identifiers(text: str | None) -> set[str]:
    """英字で始まる3〜40文字の語（snake_case・kebab-case の名前を1語に数える）。40文字を超えるのは base64 などのデータで、名前ではない。"""
    return {w for w in IDENT.findall(text or "") if 3 <= len(w) <= 40}


def vocabulary(directory: Path) -> list[str]:
    """作業の前からプロジェクトにある名前。新しく作った名前だけを比べるために除く。"""
    words: set[str] = set()
    for rel in snapshot(directory):
        words |= identifiers(decode(directory / rel))
    return sorted(words)


def safe(run_id: str) -> str:
    return run_id.replace("/", "__")


def snapshot(directory: Path) -> dict[str, str]:
    files = {}
    for dirpath, dirnames, filenames in os.walk(directory):
        dirnames[:] = sorted(d for d in dirnames if d not in SKIP and not (Path(dirpath) / d).is_symlink())
        for f in filenames:
            path = Path(dirpath) / f
            if path.is_symlink():
                continue
            files[path.relative_to(directory).as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
    return files


# ---------------------------------------------------------------- prepare

def cmd_prepare(args) -> int:
    skill_dir = Path(args.skill).resolve()
    spec = _lib.load_spec(skill_dir)
    conv = spec.get("convergence", {})
    agents = args.agents or conv.get("agents", 2)
    runners = [r for r in (args.runners or ",".join(conv.get("runners", ["claude", "codex"]))).split(",") if r]
    unknown = [r for r in runners if r not in RUNNERS]
    if unknown:
        _lib.fail(f"未知の runner: {unknown}（{', '.join(RUNNERS)} のどれか）")
    tasks = _lib.load_json(skill_dir / "dev/evals.json").get("tasks", [])
    if args.only_tasks:
        tasks = [t for t in tasks if t.get("id") in set(args.only_tasks.split(","))]
    elif not args.include_holdout:
        tasks = [t for t in tasks if t.get("kind") != "holdout"]
    if not tasks:
        _lib.fail("課題が0件です")
    for task in tasks:
        if _lib.TODO_MARKER in task.get("prompt", ""):
            _lib.fail(f"課題 {task.get('id')} の prompt がひな形のままです")
    workdir = Path(args.workdir).resolve() if args.workdir else Path(tempfile.gettempdir()) / "skill-foundation" / spec["name"]
    rdir = round_dir(workdir, args.round)
    if rdir.exists():
        if not args.force:
            _lib.fail(f"{rdir} は準備済みです（作り直すなら --force）")
        shutil.rmtree(rdir)
    place = PLACES[spec["targets"][0]]
    runs, vocab = [], {}
    for task in tasks:
        for runner in runners:
            for k in range(1, agents + 1):
                run_id = f"{task['id']}/{runner}-{k}"
                target = rdir / task["id"] / f"{runner}-{k}"
                if task.get("fixture"):
                    shutil.copytree(skill_dir / task["fixture"], target)
                else:
                    target.mkdir(parents=True)
                # スキルと hooks を置いてから git の初回コミットを作る（エージェントの git status に出さない）
                installed = target / place / spec["name"]
                installed.parent.mkdir(parents=True, exist_ok=True)
                _lib.copy_tree(skill_dir, installed, exclude=("__pycache__", ".skill-runs", ".DS_Store", "dev"))
                code, out = _lib.run([sys.executable, str(installed / "scripts/install.py"), "--project", str(target),
                                      "--targets", ",".join(spec["targets"])], target)
                if code != 0:
                    _lib.fail(f"install.py が失敗しました: {_lib.tail(out, 5)}")
                _lib.git_init(target)
                for command in task.get("setup", []):
                    code, out = _lib.run(command, target)
                    if code != 0:
                        _lib.fail(f"{task['id']} の setup `{command}` が失敗しました: {_lib.tail(out, 5)}")
                prompt = task["prompt"]
                if runner == "subagent":
                    prompt = subagent_prompt(spec, task, target, installed)
                elif task.get("invoke") == "explicit":
                    prompt = INVOKE[runner].replace("{name}", spec["name"]) + prompt
                runs.append({"id": run_id, "task": task["id"], "runner": runner, "dir": str(target), "prompt": prompt,
                             "baseline": snapshot(target)})
                vocab.setdefault(task["id"], vocabulary(target))
    plan = {"skill": str(skill_dir), "name": spec["name"], "round": args.round, "runners": runners, "agents": agents,
            "tasks": [t["id"] for t in tasks], "expect": {t["id"]: t.get("expect_status", "done") for t in tasks},
            "place": place, "runs": runs, "vocab": vocab}
    _lib.write_json(rdir / "plan.json", plan)
    print(f"準備しました: {rdir}")
    print(f"課題 {len(tasks)} 件 × runner {len(runners)} 種 × {agents} 人 = セッション {len(runs)} 回")
    command = "prompts" if "subagent" in runners else "run"
    print(f"次: python3 {Path(__file__).name} {command} --workdir {workdir} --round {args.round}")
    return 0


# ---------------------------------------------------------------- review-prepare

def put_files(target: Path, installed: Path, changes: list[dict], name: str, values: dict) -> None:
    """probe と同じ書式の files を、レビューのプロジェクトに書く（probe.py の Lab.apply と同じ扱い）。"""
    for change in changes:
        path = target / rt.expand(change["path"], name, values)
        mode = change.get("mode", "create")
        path.parent.mkdir(parents=True, exist_ok=True)
        if mode == "delete":
            if path.exists():
                path.unlink()
        elif mode == "append":
            with path.open("a", encoding="utf-8") as fh:
                fh.write(change.get("content", ""))
        elif mode == "sub":
            text, count = re.subn(change["pattern"], change.get("replacement", ""), path.read_text(encoding="utf-8"), flags=re.M)
            if count == 0:
                _lib.fail(f"{change['path']} に /{change['pattern']}/ が見つかりません（reviews の mode: sub）")
            path.write_text(text, encoding="utf-8")
        elif change.get("from"):
            path.write_bytes((installed / change["from"]).read_bytes())
        else:
            path.write_text(change.get("content", ""), encoding="utf-8")


def cmd_review_prepare(args) -> int:
    skill_dir = Path(args.skill).resolve()
    spec = _lib.load_spec(skill_dir)
    conv = spec.get("convergence", {})
    agents = args.agents or conv.get("agents", 2)
    runners = [r for r in (args.runners or ",".join(conv.get("runners", ["claude", "codex"]))).split(",") if r]
    doc = _lib.load_json(skill_dir / "dev/probes.json")
    samples = doc.get("reviews", [])
    if not samples:
        _lib.fail("dev/probes.json に reviews がありません（control に review を持つ決定の、違反の見本を書く）")
    baseline = doc.get("baseline", {})
    contract = _lib.load_json(skill_dir / "assets/contract.json")
    values = rt.normalize_input(baseline.get("input", {}), baseline.get("text", ""), contract)["values"]
    workdir = Path(args.workdir).resolve() if args.workdir else Path(tempfile.gettempdir()) / "skill-foundation" / spec["name"]
    rdir = round_dir(workdir, args.round, "review")
    if rdir.exists():
        if not args.force:
            _lib.fail(f"{rdir} は準備済みです（作り直すなら --force）")
        shutil.rmtree(rdir)
    rdir.mkdir(parents=True)
    place = PLACES[spec["targets"][0]]
    t = SUBAGENT_HEAD.get(spec.get("language"), SUBAGENT_HEAD["ja"])
    runs = []
    for sample in samples:
        for runner in runners:
            for k in range(1, agents + 1):
                target = rdir / sample["id"] / f"{runner}-{k}"
                lab = rdir / "_lab" / f"{sample['id']}-{runner}-{k}"  # probe.py と同じく、1件ごとに別の一時ディレクトリ
                lab.mkdir(parents=True)
                if baseline.get("fixture"):
                    shutil.copytree(skill_dir / baseline["fixture"], target)
                else:
                    target.mkdir(parents=True)
                # 課題の準備（prepare）と同じく、スキルと hooks を置いてから git の初回コミットを作る
                installed = target / place / spec["name"]
                installed.parent.mkdir(parents=True, exist_ok=True)
                _lib.copy_tree(skill_dir, installed, exclude=("__pycache__", ".skill-runs", ".DS_Store", "dev"))
                code, out = _lib.run([sys.executable, str(installed / "scripts/install.py"), "--project", str(target),
                                      "--targets", ",".join(spec["targets"])], target)
                if code != 0:
                    _lib.fail(f"install.py が失敗しました: {_lib.tail(out, 5)}")
                _lib.git_init(target)
                for command in baseline.get("setup", []):
                    command = command.replace("{skill}", rt.shell_quote(str(skill_dir))).replace("{lab}", rt.shell_quote(str(lab)))
                    code, out = _lib.run(command, target, timeout=900)
                    if code != 0:
                        _lib.fail(f"baseline.setup の `{command}` が失敗しました: {_lib.tail(out, 5)}")
                put_files(target, installed, baseline.get("files", []), spec["name"], values)
                for command in baseline.get("commands", []):
                    command = (command.replace("{skill}", rt.shell_quote(str(installed))).replace("{root}", rt.shell_quote(str(target)))
                               .replace("{lab}", rt.shell_quote(str(lab))))
                    code, out = _lib.run(command, target, timeout=900)
                    if code != 0:
                        _lib.fail(f"baseline.commands の `{command}` が失敗しました: {_lib.tail(out, 5)}")
                put_files(target, installed, sample.get("files", []), spec["name"], values)
                paths = sorted({rel for out in contract.get("outputs", [])
                                for rel in rt.iter_glob(target, rt.expand(out["path"], spec["name"], values))})
                ask = REVIEW_ASK.get(spec.get("language"), REVIEW_ASK["ja"])
                prompt = (ask.replace("{name}", spec["name"]).replace("{paths}", "、".join(f"`{p}`" for p in paths))
                          .replace("{skill_md}", f"{place}/{spec['name']}/SKILL.md").replace("{text}", baseline.get("text", ""))
                          .replace("{inputs}", json.dumps(values, ensure_ascii=False)))
                if runner == "subagent":
                    prompt = t["dir"].replace("{dir}", str(target)) + prompt
                runs.append({"id": f"{sample['id']}/{runner}-{k}", "task": sample["id"], "rule": sample["rule"],
                             "runner": runner, "dir": str(target), "prompt": prompt, "baseline": snapshot(target)})
    plan = {"kind": "review", "skill": str(skill_dir), "name": spec["name"], "round": args.round, "runners": runners,
            "agents": agents, "samples": [{"id": x["id"], "rule": x["rule"]} for x in samples], "place": place, "runs": runs}
    _lib.write_json(rdir / "plan.json", plan)
    print(f"準備しました: {rdir}")
    print(f"見本 {len(samples)} 件 × runner {len(runners)} 種 × {agents} 人 = セッション {len(runs)} 回")
    command = "prompts" if "subagent" in runners else "run"
    print(f"次: python3 {Path(__file__).name} {command} --workdir {workdir} --round {args.round} --kind review")
    return 0


def cmd_review_score(args) -> int:
    workdir = Path(args.workdir).resolve()
    rdir = round_dir(workdir, args.round, "review")
    plan = _lib.load_json(rdir / "plan.json")
    skill_dir = Path(plan["skill"])
    spec = _lib.load_spec(skill_dir)
    known = {d["id"] for d in spec.get("decisions", [])}
    out = Path(args.out).resolve() if args.out else skill_dir / f"dev/results/convergence/round-{plan['round']}"
    out.mkdir(parents=True, exist_ok=True)
    result = {"round": plan["round"], "runners": plan["runners"], "samples": []}
    for sample in plan["samples"]:
        runs = sorted([r for r in plan["runs"] if r["task"] == sample["id"]], key=lambda r: r["id"])
        detected, extra, found_sets, changed = {}, {}, {}, {}
        for run in runs:
            label = run["id"].split("/", 1)[1]
            result_file = rdir / "_results" / f"{safe(run['id'])}.json"
            message = _lib.load_json(result_file).get("message", "") if result_file.is_file() else ""
            found = set(_lib.ID_IN_TEXT.findall(message)) & known
            found_sets[label] = found
            detected[label] = sample["rule"] in found
            extra[label] = sorted(found - {sample["rule"]})
            now = snapshot(Path(run["dir"]))
            changed[label] = sorted(rel for rel in set(run["baseline"]) | set(now)
                                    if run["baseline"].get(rel) != now.get(rel) and not rel.startswith(".skill-runs/"))
        rate = round(sum(detected.values()) / len(detected), 3) if detected else 0.0
        result["samples"].append({"id": sample["id"], "rule": sample["rule"], "rate": rate, "detected": detected,
                                  "extra": extra, "agree": len({tuple(sorted(v)) for v in found_sets.values()}) <= 1,
                                  "changed": {k: v for k, v in changed.items() if v}})
    _lib.write_json(out / "review.json", result)
    lines = [f"# レビューの検出率 ラウンド {plan['round']}", "",
             "convergence.py review-score が生成する。見本ごとに、違反の決定の ID を返答に挙げたエージェントの割合を数える。"
             "基準は検出率 1.0（全員が見つける）。余計な指摘は見本に無い決定の ID、一致はエージェント同士で挙げた ID の集合が同じこと。", "",
             "| 見本 | 決定 | 検出率 | 余計な指摘 | 一致 | ファイルを変えたエージェント |", "|---|---|---|---|---|---|"]
    for x in result["samples"]:
        extra_text = "、".join(f"{k}: {', '.join(v)}" for k, v in x["extra"].items() if v) or "なし"
        lines.append(f"| {x['id']} | {x['rule']} | {x['rate']:.3f} | {extra_text} | {'はい' if x['agree'] else 'いいえ'} | "
                     f"{'、'.join(x['changed']) or 'なし'} |")
    (out / "review.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines[4:]))
    print(f"結果: {out / 'review.json'}")
    return 0 if all(x["rate"] == 1 for x in result["samples"]) else 1


# ---------------------------------------------------------------- prompts

def cmd_prompts(args) -> int:
    rdir = round_dir(Path(args.workdir).resolve(), args.round, args.kind)
    plan = _lib.load_json(rdir / "plan.json")
    runs = [r for r in plan["runs"] if r["runner"] == "subagent"]
    if args.only:
        runs = [r for r in runs if r["id"] in set(args.only.split(","))]
    if not runs:
        _lib.fail("runner subagent の実行がありません（prepare --runners subagent で準備する）")
    prompts, results = rdir / "_prompts", rdir / "_results"
    prompts.mkdir(parents=True, exist_ok=True)
    results.mkdir(parents=True, exist_ok=True)
    print("各プロンプトファイルの中身を、そのまま新しいエージェントに渡す（Agent ツール。会話の文脈を引き継がない種類を使い、"
          "fork は使わない。前後に説明を足さない。並べて起動してよい）。エージェントの最終の返答は、保存先にそのまま書く。"
          "全件を書いたら run を実行する。")
    for run in runs:
        prompt_file = prompts / f"{safe(run['id'])}.md"
        prompt_file.write_text(run["prompt"], encoding="utf-8")
        last = results / f"{safe(run['id'])}.last.txt"
        print(f"- {run['id']}: プロンプト {prompt_file} → 保存先 {last}{'（保存済み）' if last.is_file() else ''}")
    return 0


# ---------------------------------------------------------------- run

def last_message(runner: str, stdout: str, last_file: Path) -> str:
    if runner == "claude":
        try:
            return str(json.loads(stdout).get("result", ""))
        except (json.JSONDecodeError, AttributeError):
            return stdout[-4000:]
    if last_file.is_file():
        return last_file.read_text(encoding="utf-8", errors="replace")
    return _lib.tail(stdout, 40)


def cmd_run(args) -> int:
    workdir = Path(args.workdir).resolve()
    rdir = round_dir(workdir, args.round, args.kind)
    plan = _lib.load_json(rdir / "plan.json")
    spec = _lib.load_spec(Path(plan["skill"]))
    conv = spec.get("convergence", {})
    overrides = conv.get("runner_commands", {})
    runs = plan["runs"]
    if args.only:
        runs = [r for r in runs if r["id"] in set(args.only.split(","))]
    results = rdir / "_results"
    results.mkdir(parents=True, exist_ok=True)
    env = {k: v for k, v in os.environ.items() if k not in ("CLAUDECODE", "CLAUDE_PROJECT_DIR")}

    def execute(run: dict):
        last = results / f"{safe(run['id'])}.last.txt"
        template = overrides.get(run["runner"]) or default_runner(run["runner"])
        command = [a.replace("{prompt}", run["prompt"]).replace("{dir}", run["dir"]).replace("{last}", str(last))
                   for a in template]
        started = time.monotonic()
        code, out = _lib.run(command, Path(run["dir"]), timeout=args.timeout, env=env)
        record = {"id": run["id"], "runner": run["runner"], "exit": code, "seconds": round(time.monotonic() - started, 1),
                  "message": last_message(run["runner"], out, last), "output_tail": _lib.tail(out, 60)}
        _lib.write_json(results / f"{safe(run['id'])}.json", record)
        return run["id"], code, record["seconds"]

    failed = 0
    for run in [r for r in runs if r["runner"] == "subagent"]:
        last = results / f"{safe(run['id'])}.last.txt"
        if not last.is_file():
            failed += 1
            print(f"未実行  {run['id']}  最終の返答がありません（prompts の手順で {last} に保存する）")
            continue
        _lib.write_json(results / f"{safe(run['id'])}.json",
                        {"id": run["id"], "runner": "subagent", "exit": 0, "seconds": None,
                         "message": last.read_text(encoding="utf-8", errors="replace"), "output_tail": ""})
        print(f"完了  {run['id']}  Agent ツールの結果を集めた")
    runs = [r for r in runs if r["runner"] != "subagent"]
    print(f"{len(runs)} 件を最大 {args.parallel} 並列で実行します（1件の上限 {args.timeout} 秒）")
    with ThreadPoolExecutor(max_workers=args.parallel) as pool:
        for run_id, code, seconds in pool.map(execute, runs):
            failed += code != 0
            print(f"{'完了' if code == 0 else '失敗'}  {run_id}  終了コード {code}（{seconds:.0f} 秒）")
    print(f"結果: {results}")
    return 1 if failed else 0


# ---------------------------------------------------------------- diff

def decode(path: Path) -> str | None:
    if not path.is_file() or path.stat().st_size > MAX_BYTES:
        return None
    data = path.read_bytes()
    if b"\0" in data[:8192]:
        return None
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        return None


def skeleton(rel: str, text: str | None) -> str:
    """中身の言い回しを除いた形。JSON はキーの道筋と型、それ以外は行の種類の並び。"""
    if text is None:
        return "binary"
    if rel.endswith(".json"):
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            return "invalid-json"
        paths = []

        def walk(value, prefix):
            if isinstance(value, dict):
                for key in sorted(value):
                    walk(value[key], f"{prefix}.{key}")
            elif isinstance(value, list):
                paths.append(f"{prefix}[]:{len(value)}")
                for item in value[:1]:
                    walk(item, prefix + "[]")
            else:
                paths.append(f"{prefix}:{type(value).__name__}")
        walk(data, "$")
        return "\n".join(paths)
    kinds, inside = [], False
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith(("```", "~~~")):
            inside = not inside
            kinds.append("F")
        elif inside:
            kinds.append("C")
        elif not stripped:
            kinds.append("B")
        elif re.match(r"#{1,6} ", stripped):
            kinds.append("H" + str(len(stripped.split(" ")[0])))
        elif re.match(r"[-*+] ", stripped):
            kinds.append("L")
        elif re.match(r"\d+\. ", stripped):
            kinds.append("N")
        elif stripped.startswith("|"):
            kinds.append("|")
        elif stripped.startswith(">"):
            kinds.append(">")
        else:
            kinds.append("T")
    return " ".join(kinds)


def jaccard(a: set, b: set) -> float:
    return 1.0 if not a and not b else len(a & b) / len(a | b)


def mean(values: list[float]) -> float | None:
    return round(sum(values) / len(values), 3) if values else None


def tampered(run: dict, plan: dict, targets: list[str], now: dict[str, str]) -> list[str]:
    """スキル自身のファイルを変えたか、このスキルの hooks の登録を外した・変えたエージェントの証拠。"""
    prefix = f"{plan['place']}/{plan['name']}/"
    base = run["baseline"]
    found = sorted(rel for rel in set(base) | set(now) if rel.startswith(prefix) and base.get(rel) != now.get(rel))
    code, output = _lib.run([sys.executable, str(Path(plan["skill"]) / "scripts/install.py"), "--project", run["dir"],
                             "--targets", ",".join(targets), "--check"], Path(run["dir"]))
    if code != 0:
        found += [line[len("ERROR "):] for line in output.splitlines() if line.startswith("ERROR ")] or ["install.py --check が失敗"]
    return found


def changed_files(run: dict, name: str, ignore: list[str], now: dict[str, str]) -> dict[str, str | None]:
    directory = Path(run["dir"])
    base = run["baseline"]
    skip = {f".skill-runs/{name}/state.json", ".skill-runs/.gitignore"}
    result = {}
    for rel in sorted(set(base) | set(now)):
        if base.get(rel) == now.get(rel) or rel in skip or rt.matches_any(rel, ignore):
            continue
        result[rel] = decode(directory / rel) if rel in now else None
    return result


def metrics(names: list[str], changes: dict, contents: dict, vocab: set[str] | None = None) -> dict:
    pairs = list(itertools.combinations(names, 2))
    files = mean([jaccard(set(changes[a]), set(changes[b])) for a, b in pairs]) if pairs else 1.0
    new = {n: set().union(*(identifiers(t) for t in contents[n].values())) - (vocab or set()) for n in names}
    named = mean([jaccard(new[a], new[b]) for a, b in pairs]) if pairs else 1.0
    structure, content = [], []
    for a, b in pairs:
        common = sorted(set(changes[a]) & set(changes[b]))
        for rel in common:
            ta, tb = contents[a].get(rel), contents[b].get(rel)
            structure.append(1.0 if skeleton(rel, ta) == skeleton(rel, tb) else 0.0)
            if ta is not None and tb is not None:
                la = [l.rstrip() for l in ta.splitlines() if l.strip()]
                lb = [l.rstrip() for l in tb.splitlines() if l.strip()]
                content.append(difflib.SequenceMatcher(None, la, lb, autojunk=False).ratio())
    return {"files": files, "structure": mean(structure) if structure else (1.0 if files == 1.0 else 0.0),
            "names": named, "content": mean(content), "new_names": {n: sorted(new[n])[:40] for n in names}}


def cmd_diff(args) -> int:
    workdir = Path(args.workdir).resolve()
    rdir = round_dir(workdir, args.round)
    plan = _lib.load_json(rdir / "plan.json")
    skill_dir = Path(plan["skill"])
    spec = _lib.load_spec(skill_dir)
    conv = spec.get("convergence", {})
    thresholds = {"files": 1.0, "structure": 1.0, "names": 0.8, **conv.get("thresholds", {})}
    ignore = conv.get("ignore", [])
    out = Path(args.out).resolve() if args.out else skill_dir / f"dev/results/convergence/round-{plan['round']}"
    out.mkdir(parents=True, exist_ok=True)
    name = plan["name"]
    report = {"round": plan["round"], "runners": plan["runners"], "thresholds": thresholds, "tasks": []}
    for tid in plan["tasks"]:
        runs = sorted([r for r in plan["runs"] if r["task"] == tid], key=lambda r: r["id"])
        names, changes, contents, statuses, checks, messages, broken = [], {}, {}, {}, {}, {}, {}
        for run in runs:
            label = run["id"].split("/", 1)[1]
            names.append(label)
            now = snapshot(Path(run["dir"]))
            found = changed_files(run, name, ignore, now)
            evidence = tampered(run, plan, spec["targets"], now)
            if evidence:
                broken[label] = evidence
            changes[label] = set(found)
            contents[label] = found
            state_path = Path(run["dir"]) / ".skill-runs" / name / "state.json"
            state = json.loads(state_path.read_text(encoding="utf-8")) if state_path.is_file() else None
            statuses[label] = state.get("status") if state else "unused"
            if state and state.get("status") == "done":
                code, output = _lib.run([sys.executable, str(Path(run["dir"]) / plan["place"] / name / "scripts/run.py"),
                                         "check", "--root", run["dir"]], Path(run["dir"]), timeout=300)
                checks[label] = {"exit": code, "tail": "" if code == 0 else _lib.tail(output, 15)}
            result_file = rdir / "_results" / f"{safe(run['id'])}.json"
            messages[label] = _lib.load_json(result_file).get("message", "") if result_file.is_file() else ""
            patch = []
            for rel, text in sorted(found.items()):
                patch.append(f"=== {rel}\n{text if text is not None else '(削除・バイナリ)'}\n")
            (out / tid).mkdir(parents=True, exist_ok=True)
            (out / tid / f"{label}.patch").write_text("".join(patch), encoding="utf-8")
        vocab = set(plan.get("vocab", {}).get(tid, []))
        overall = metrics(names, changes, contents, vocab)
        by_runner = {}
        for runner in plan["runners"]:
            group = [n for n in names if n.startswith(runner + "-")]
            if len(group) >= 2:
                by_runner[runner] = {k: v for k, v in metrics(group, changes, contents, vocab).items() if k != "new_names"}
        expected = plan.get("expect", {}).get(tid, "done")
        check_ok = all(c["exit"] == 0 for c in checks.values())
        converged = (set(statuses.values()) == {expected} and check_ok and not broken
                     and overall["files"] >= thresholds["files"] and overall["structure"] >= thresholds["structure"]
                     and overall["names"] >= thresholds["names"])
        partial = [{"path": p, "who": [n for n in names if p in changes[n]]}
                   for p in sorted(set().union(*changes.values())) if 0 < sum(p in changes[n] for n in names) < len(names)]
        excerpts = []
        for a, b in itertools.combinations(names, 2):
            for rel in sorted(changes[a] & changes[b]):
                ta, tb = contents[a].get(rel), contents[b].get(rel)
                if ta is not None and tb is not None and ta != tb and len(excerpts) < 6:
                    excerpts.append({"path": rel, "pair": [a, b],
                                     "diff": list(difflib.unified_diff(ta.splitlines(), tb.splitlines(), f"{a}/{rel}",
                                                                       f"{b}/{rel}", lineterm=""))[:60]})
        report["tasks"].append({"id": tid, "agents": names, "expect_status": expected, "status": statuses, **overall, "by_runner": by_runner,
                                "check": {n: c["exit"] for n, c in checks.items()}, "converged": converged,
                                "tampered": broken,
                                "changed_files": {n: sorted(changes[n]) for n in names}, "partial_files": partial,
                                "excerpts": excerpts, "check_failures": {n: c["tail"] for n, c in checks.items() if c["exit"]},
                                "messages": {n: messages[n][-1500:] for n in names}})
    _lib.write_json(out / "report.json", report)
    (out / "report.md").write_text(render_report(report), encoding="utf-8")
    print(summary(report))
    print(f"レポート: {out / 'report.md'}")
    return 0 if all(t["converged"] for t in report["tasks"]) else 1


def fmt(value) -> str:
    return "—" if value is None else f"{value:.3f}"


def summary(report: dict) -> str:
    lines = ["| 課題 | status | files | structure | names | content | check | runner 別 files | 基準 |", "|---|---|---|---|---|---|---|---|---|"]
    for t in report["tasks"]:
        status = "、".join(sorted(set(t["status"].values())))
        check = "—" if not t["check"] else ("全員通過" if all(v == 0 for v in t["check"].values()) else "失敗あり")
        runner = "、".join(f"{k} {fmt(v['files'])}" for k, v in t["by_runner"].items()) or "—"
        lines.append(f"| {t['id']} | {status} | {fmt(t['files'])} | {fmt(t['structure'])} | {fmt(t.get('names'))} | {fmt(t['content'])} | "
                     f"{check} | {runner} | {'満たす' if t['converged'] else '満たさない'} |")
    return "\n".join(lines)


def render_report(report: dict) -> str:
    th = report["thresholds"]
    lines = [f"# 収束テスト ラウンド {report['round']}", "",
             "convergence.py diff が生成する。揺れの分類（V1〜V8）と対処は dev/convergence-report.md に書く。", "",
             f"基準: status が全員、課題の expect_status（既定 done）と同じ。check が全員通過。スキル自身や hooks の登録を"
             f"変えたエージェントがいない。files ≥ {th['files']}、structure ≥ {th['structure']}、names ≥ {th.get('names', 0.8)}", "",
             "## 指標", "", summary(report)]
    if "subagent" in report.get("runners", []):
        lines[6:6] = ["runner subagent は Agent ツールで実行した。一時プロジェクトの hooks は働かず、run.py の check と finish だけで"
                      "検査された。自動の起動は、スキルの説明文を前置きで渡した近似である（convergence-test.md の3章）。", ""]
    for t in report["tasks"]:
        lines += ["", f"## {t['id']}", "", f"### 実行の状態（期待: {t['expect_status']}）", ""]
        lines += [f"- {n}: {s}" for n, s in t["status"].items()]
        lines += ["", "### 新しく作った名前（names。先頭 40 件）", ""]
        lines += [f"- {n}: {', '.join(f'`{w}`' for w in words) or 'なし'}" for n, words in t.get("new_names", {}).items()]
        lines += ["", "### 一部のエージェントだけが作った・変えたファイル", ""]
        lines += [f"- `{p['path']}`: {', '.join(p['who'])}" for p in t["partial_files"]] or ["なし"]
        lines += ["", "### 中身の違い（抜粋）", ""]
        for ex in t["excerpts"]:
            lines += [f"#### `{ex['path']}`（{ex['pair'][0]} と {ex['pair'][1]}）", "", "```diff", *ex["diff"], "```", ""]
        if not t["excerpts"]:
            lines.append("なし")
        if t.get("tampered"):
            lines += ["", "### スキル自身や hooks の登録を変えたエージェント（失格）", ""]
            lines += [f"- {n}: {'、'.join(paths)}" for n, paths in t["tampered"].items()]
        if t["check_failures"]:
            lines += ["", "### check に失敗したエージェント", ""]
            for n, tail in t["check_failures"].items():
                lines += [f"#### {n}", "", "```", tail, "```"]
    return "\n".join(lines).rstrip() + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("prepare")
    p.add_argument("skill")
    p.add_argument("--round", type=int, required=True)
    p.add_argument("--agents", type=int)
    p.add_argument("--runners", help="カンマ区切り（claude、codex）")
    p.add_argument("--include-holdout", action="store_true")
    p.add_argument("--only-tasks")
    p.add_argument("--workdir")
    p.add_argument("--force", action="store_true")
    p.set_defaults(func=cmd_prepare)
    p = sub.add_parser("review-prepare")
    p.add_argument("skill")
    p.add_argument("--round", type=int, required=True)
    p.add_argument("--agents", type=int)
    p.add_argument("--runners", help="カンマ区切り（claude、codex、subagent）")
    p.add_argument("--workdir")
    p.add_argument("--force", action="store_true")
    p.set_defaults(func=cmd_review_prepare)
    p = sub.add_parser("review-score")
    p.add_argument("--workdir", required=True)
    p.add_argument("--round", type=int, required=True)
    p.add_argument("--out")
    p.set_defaults(func=cmd_review_score)
    p = sub.add_parser("prompts")
    p.add_argument("--workdir", required=True)
    p.add_argument("--round", type=int, required=True)
    p.add_argument("--kind", choices=["task", "review"], default="task")
    p.add_argument("--only", help="カンマ区切りの実行ID")
    p.set_defaults(func=cmd_prompts)
    p = sub.add_parser("run")
    p.add_argument("--workdir", required=True)
    p.add_argument("--round", type=int, required=True)
    p.add_argument("--kind", choices=["task", "review"], default="task")
    p.add_argument("--parallel", type=int, default=3)
    p.add_argument("--timeout", type=int, default=1800)
    p.add_argument("--only", help="カンマ区切りの実行ID")
    p.set_defaults(func=cmd_run)
    p = sub.add_parser("diff")
    p.add_argument("--workdir", required=True)
    p.add_argument("--round", type=int, required=True)
    p.add_argument("--out")
    p.set_defaults(func=cmd_diff)
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
