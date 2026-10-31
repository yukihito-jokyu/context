#!/usr/bin/env python3
"""収束テスト: 作成に関わっていない独立エージェント（Claude Code と Codex）に同じ依頼を解かせ、出力の違いを測る。

サブコマンド:
  prepare        課題 × runner × 人数の分だけ、一時プロジェクトを作ってスキルを置き、plan.json を書く。
                 runner・人数・ラウンドの上限・基準・モデル・推論エフォートは、引数 → 作るスキルの spec の convergence →
                 settings/user-setting.yaml → settings/skill-setting.yaml（skill-foundation の設定）の順に、null でない
                 最初の値に決め、出どころを表示して plan.json の settings に残す。
                 課題ごとに、作業の前からある名前（英字の識別子）を記録する（names の指標に使う）。
                 ラウンド2からは、前のラウンドの AI の分析と、それを締め込みで分類した記録（convergence-report.md の
                 「## 動きの指摘」）が揃っていないと止まる
  prompts        runner subagent の実行ごとに、Agent ツールに渡すプロンプトと、最終の返答の保存先を出す
  run            plan の各プロジェクトで runner（claude -p / codex exec）を実行し、結果を _results/ に保存する。
                 runner claude の --output-format stream-json と runner codex の --json の出力は、行に届いた時刻を付けて
                 _results/<実行ID>.events.jsonl にも保存する（codex の出来事に時刻が無いため）。runner subagent は起動せず、
                 保存された最終の返答を集める
  diff           課題ごとにプロジェクト同士を比べ、指標とレポート（report.json / report.md / *.patch）を書く。
                 エージェントが作った・変えたファイルの写しを records/outputs/<課題>__<エージェント>/ に置く（catalog.py が見せる）。
                 独立エージェントの作業ディレクトリ制限（fence.py）の登録を外した課題は基準を満たさない。
                 Eval（dev/eval/eval.json）があれば、各エージェントの出力を採点する（STEP-07）。code の判定はここで当て、
                 model の判定は分析役に頼む（判定する中身を <課題>/<エージェント>.eval.json に書く）。Eval に落ちた出力が
                 ある課題も基準を満たさない
                 各エージェントの動き（traces.json）と、エージェントが読んだ SKILL.md の写し（used-SKILL.md）も書く
  trace          各エージェントの動きだけを traces.json に書く（diff より前のラウンドに後から足すとき）。
                 実行の記録（start・check・finish）と、次の記録から、道具の呼び出しを時刻・道具・対象・成否の列にする。
                 runner subagent: Claude Code の Agent ツールの記録（~/.claude/projects/ に置く。プロンプトの全文が
                 一致するもの）。無ければ Codex のサブエージェントの記録（~/.codex/sessions/ に置く。依頼文は暗号化されて
                 残るので、コマンドとファイルのパスに作業ディレクトリが一番多く出るもの）
                 runner claude・codex: run が保存した stream-json・--json の出力（events.jsonl）。
                 実行ごとのモデルと推論エフォート（model・effort）も書く。subagent は記録（Claude Code は message.model と
                 effort、Codex は turn_context）から、claude は claude -p の出力の modelUsage から（推論エフォートは残らない）、
                 codex は --json の出力にモデルが無いので、コマンドの -m・-c か ~/.codex/config.toml から読み、settings を付ける
  review-prepare dev/probes.json の reviews の見本ごとに、違反を入れた出力のあるプロジェクトを作り、
                 「完了前チェックリストで確かめて」という依頼を plan.json に書く（prompts と run は --kind review）
  review-score   レビューの返答に出たルールIDを数え、見本ごとの検出率・余計な指摘・エージェント間の一致を
                 review.json / review.md に書く
  analysis-prepare
                 traces.json の各エージェントの記録（手順・依頼・操作の入力と出力・成否・手順との照合・最終の返答）を、
                 分析役のエージェントの作業ディレクトリに record.md として置く（エージェント1人の記録ごとに1件）。
                 エージェント自身の考えは記録に残らない（Codex は暗号化、Claude Code は空）ので、分析役が推し量る
  analysis-collect
                 分析役が書いた analysis.json（操作ごとの理由の推定と当てはまり、流れの評価、ほかのエージェントとの違い）を
                 確かめ、dev/results/convergence/round-<R>/analysis.json に集める。catalog.py が「エージェントの動き」に出す。
                 分析役の model の判定を report.json の採点に入れ、課題の基準を決め直す。
                 指摘と直し方の案を手順ごとに集めたまとめ（analysis.md）も書く。締め込みで読み、convergence-report.md の
                 「## 動きの指摘」の表に分類と対処を書く。prepare は、前のラウンドのこの表が揃うまで次のラウンドを準備しない

runner の既定（spec の convergence.runner_commands で上書きできる。{prompt} と {dir} が置き換わる）。
plan.json の settings に runner のモデル・推論エフォートがあれば、既定の起動コマンドに足す（claude は --model・--effort、
codex は -m・-c model_reasoning_effort。runner_commands で上書きしたときは足さない。subagent は prompts が Agent ツールの
model・effort を示す）:
  claude: claude -p --output-format stream-json --verbose --permission-mode acceptEdits --no-session-persistence
          --setting-sources project,local --allowedTools ...（ユーザー単位の設定を読まない）
  codex : codex exec --json --sandbox workspace-write --skip-git-repo-check --ephemeral
          --dangerously-bypass-hook-trust（一時プロジェクトの hooks は信頼の手続きを経ていないため）
          -c で /tmp と $TMPDIR を書き込み先から外す（作業ディレクトリの外への書き込みを OS の側で止める）
  subagent: このスクリプトは起動しない。呼び出し元の AI が、prompts の出したプロンプトを、専用のエージェント型
          skill-foundation-tester（Agent ツール）にそのまま渡す。スキルの hooks は働かず、自動の起動は説明文を渡した近似になる

作業ディレクトリの外への操作の停止（fence.py）: prepare が各一時プロジェクトに印（.skill-runs/_fence/）を置き、runner claude・codex は
一時プロジェクトの設定に、runner subagent は専用のエージェント型（--agents-dir、既定はこのスキルの置き場の .claude/agents/）の
frontmatter に、fence.py を PreToolUse の hook として登録する。run は TMPDIR を .skill-runs/_fence/tmp に向ける。
止めた操作は diff・trace が traces.json の操作に印（fenced）を付ける。.skill-runs/_fence/ は変わったファイルに数えない

例:
  python3 convergence.py prepare <スキル> --round 1 [--runners subagent]
  python3 convergence.py prompts --workdir <W> --round 1      # runner subagent のときだけ
  python3 convergence.py run --workdir <W> --round 1
  python3 convergence.py diff --workdir <W> --round 1 --out <スキル>/dev/results/convergence/round-1
  python3 convergence.py trace --workdir <W> --round 1 --out <スキル>/dev/results/convergence/round-1
  python3 convergence.py review-prepare <スキル> --round 2 --workdir <W>   # 最後のラウンド
  python3 convergence.py run --workdir <W> --round 2 --kind review
  python3 convergence.py review-score --workdir <W> --round 2 --out <スキル>/dev/results/convergence/round-2
  python3 convergence.py analysis-prepare <スキル> --round 1 [--runner subagent] --workdir <W>   # 各ラウンドの diff の後
  python3 convergence.py prompts --workdir <W> --round 1 --kind analysis   # runner subagent。claude・codex は run --kind analysis
  python3 convergence.py analysis-collect --workdir <W> --round 1
"""

from __future__ import annotations

import argparse
import datetime
import difflib
import glob
import gzip
import hashlib
import itertools
import json
import os
import re
import shlex
import shutil
import sys
import subprocess
import tempfile
import threading
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _lib  # noqa: E402
import _skillrt as rt  # noqa: E402
import eval_check  # noqa: E402

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
SKIP = {".git", "__pycache__", "node_modules", ".venv", ".skill-feedback"}
MAX_BYTES = 1_000_000
IDENT = re.compile(r"[A-Za-z_][A-Za-z0-9_]*(?:-[A-Za-z0-9_]+)*")
FENCE = Path(__file__).resolve().parent / "fence.py"
FENCE_REL = ".skill-runs/_fence"  # fence.py の FENCE_REL と同じ
FENCE_CONFIGS = {"claude": (".claude/settings.json", ["*"]), "codex": (".codex/hooks.json", ["Bash", "apply_patch"])}
FENCED = re.compile(r"\[skill-foundation (?:の fence\.py|fence|の柵)\]")  # fence.py が止める理由の先頭に付ける目印（「の柵」は前の版の記録）
TESTER = "skill-foundation-tester"
USED_SKILL = "used-SKILL.md"  # ラウンドでエージェントが読んだ SKILL.md の写し（dev/results/convergence/round-<R>/。分析が手順と比べる）


def default_runner(runner: str) -> list[str]:
    if runner == "claude":
        return ["claude", "-p", "{prompt}", "--output-format", "stream-json", "--verbose", "--permission-mode", "acceptEdits",
                "--no-session-persistence", "--setting-sources", "project,local", "--allowedTools", *CLAUDE_TOOLS]
    return [codex_binary(), "exec", "--json", "--sandbox", "workspace-write", "--skip-git-repo-check", "--ephemeral",
            "--dangerously-bypass-hook-trust", "-c", 'projects."{dir}".trust_level="trusted"',
            "-c", "sandbox_workspace_write.exclude_slash_tmp=true", "-c", "sandbox_workspace_write.exclude_tmpdir_env_var=true",
            "-C", "{dir}", "-o", "{last}", "{prompt}"]


def with_model(template: list[str], runner: str, model: str | None, effort: str | None) -> list[str]:
    """既定の起動コマンドに、設定のモデルと推論エフォートを足す。"""
    if runner == "claude":
        at = template.index("--allowedTools") if "--allowedTools" in template else len(template)  # 道具の一覧の前に入れる
        extra = (["--model", model] if model else []) + (["--effort", effort] if effort else [])
        return template[:at] + extra + template[at:]
    if runner == "codex":
        at = template.index("exec") + 1
        extra = (["-m", model] if model else []) + (["-c", f'model_reasoning_effort="{effort}"'] if effort else [])
        return template[:at] + extra + template[at:]
    return template


def chosen(plan: dict, runner: str) -> tuple[str | None, str | None]:
    """prepare が plan.json に残した、runner のモデルと推論エフォート。"""
    settings = plan.get("settings", {})
    return settings.get("model", {}).get(runner), settings.get("effort", {}).get(runner)


def per_runner(items: list[str] | None) -> dict:
    """--model・--effort の値。runner=値 はその runner に、値だけなら全部の runner に当てる。"""
    found = {}
    for item in items or []:
        runner, sep, value = item.partition("=")
        found.update({runner.strip(): value.strip()} if sep else {r: item.strip() for r in RUNNERS})
    return found


def plan_settings(spec: dict, args) -> tuple[dict, dict]:
    """prepare と review-prepare の、収束テストの動かし方（_lib.convergence_settings）。足りない項目があれば止まる。"""
    runners = [r for r in (args.runners or "").split(",") if r]
    unknown = [r for r in runners if r not in RUNNERS]
    if unknown:
        _lib.fail(f"未知の runner: {unknown}（{', '.join(RUNNERS)} のどれか）")
    over = {"runners": runners or None, "agents": args.agents, "model": per_runner(args.model), "effort": per_runner(args.effort)}
    cfg, sources, warnings = _lib.convergence_settings(spec, over)
    for warning in warnings:
        print(f"注意: {warning}")
    missing = [path for path in _lib.CONVERGENCE_REQUIRED if _lib.setting_value(cfg, path) is None]
    if missing:
        _lib.fail(f"収束テストの設定 {missing} が、引数・spec の convergence・settings のどこにもありません"
                  "（skill-foundation の settings/skill-setting.yaml の convergence に書く）")
    return cfg, sources


def show_settings(cfg: dict, sources: dict, runners: list[str]) -> None:
    """決めた動かし方と出どころ。モデルと推論エフォートは、指定が無ければ runner の既定で動く。"""
    def where(path: str) -> str:
        return _lib.SETTING_SOURCES.get(sources.get(path), "指定なし（runner の既定）")
    print("動かし方（強い順: 引数 → spec の convergence → ユーザーの設定 → スキルの設定）:")
    for path in ("runners", "agents", "max_rounds", "thresholds.files", "thresholds.structure", "thresholds.names"):
        print(f"  {path} = {json.dumps(_lib.setting_value(cfg, path), ensure_ascii=False)}（{where(path)}）")
    for kind in ("model", "effort"):
        for runner in runners:
            value = cfg[kind].get(runner)
            print(f"  {kind}.{runner} = {value or '-'}（{where(f'{kind}.{runner}')}）")


def fence_command(platform: str, lab: Path | None = None) -> str:
    where = f"--lab {shlex.quote(str(lab))}" if lab else "--agent"
    return f"python3 {shlex.quote(str(FENCE))} --platform {platform} {where}"


def register_fence(target: Path, runner: str) -> None:
    """runner claude・codex の一時プロジェクトの設定に、fence.py を足す。git の初回コミットの前に呼ぶ。"""
    if runner not in FENCE_CONFIGS:
        return
    rel, matchers = FENCE_CONFIGS[runner]
    path = target / rel
    data = _lib.load_json(path) if path.is_file() else {}
    groups = data.setdefault("hooks", {}).setdefault("PreToolUse", [])
    for matcher in matchers:
        groups.append({"matcher": matcher, "hooks": [{"type": "command", "command": fence_command(runner, target), "timeout": 10}]})
    _lib.write_json(path, data)


def mark_lab(target: Path, rdir: Path, run_id: str, runner: str, language: str | None) -> None:
    """fence.py の印と一時ファイルの置き場（.skill-runs/_fence/）。fence.py がこれで一時プロジェクトを見分ける。git には出さない。"""
    fence = target / FENCE_REL
    (fence / "tmp").mkdir(parents=True, exist_ok=True)
    (fence / ".gitignore").write_text("*\n", encoding="utf-8")
    _lib.write_json(fence / "lab.json", {"lab": os.path.realpath(target), "round": os.path.realpath(rdir), "run": run_id,
                                         "runner": runner, "language": language or "ja"})


def place_tester(agents_dir: str | None) -> str:
    """runner subagent の専用のエージェント型を置き、案内の文を返す。frontmatter の hooks に fence.py を登録する。"""
    if agents_dir:
        folder = Path(agents_dir).resolve()
    else:
        here = Path(os.path.abspath(__file__)).parents
        if here[2].name != "skills" or here[3].name != ".claude":
            _lib.fail("runner subagent の fence.py は、専用のエージェント型を .claude/agents/ に置いて働かせる。"
                      "skill-foundation が .claude/skills/ の下に無いので、置き場を --agents-dir で指定してください")
        folder = here[3] / "agents"
    path = folder / f"{TESTER}.md"
    text = ((_lib.FOUNDATION_DIR / "assets/agents" / f"{TESTER}.md").read_text(encoding="utf-8")
            .replace("{fence}", json.dumps(fence_command("claude"), ensure_ascii=False)))
    if path.is_file() and path.read_text(encoding="utf-8") == text:
        return f"専用のエージェント型: {path}（変更なし）"
    existed = folder.is_dir()
    folder.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    if not existed:
        return (f"専用のエージェント型を置きました: {path}。Claude Code は、セッションを始めた後に作った {folder.name}/ を"
                "読まないので、再起動してから prompts のエージェントを起動してください")
    return f"専用のエージェント型を置きました: {path}（Claude Code は数秒で読み込む）"


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
    return workdir / (f"round-{rnd}" if kind == "task" else f"{kind}-{rnd}")


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

def recorded_inputs(skill_dir: Path, task: dict) -> list[tuple[Path, str]]:
    """Only replay captured input files, never the feedback or expected outputs."""
    result = []
    for item in task.get("input_files", []):
        source = (skill_dir / item["source"]).resolve()
        relative = Path(item["path"])
        if (not source.is_relative_to((skill_dir / "dev/feedback-inputs").resolve()) or not source.is_file()
                or relative.is_absolute() or ".." in relative.parts or not relative.parts
                or relative.parts[0] in {".git", ".claude", ".agents", ".codex", ".skill-runs", ".skill-feedback"}):
            _lib.fail(f"課題 {task.get('id')} の input_files が入力ファイルの範囲を外れています")
        result.append((source, relative.as_posix()))
    return result


def cmd_prepare(args) -> int:
    skill_dir = Path(args.skill).resolve()
    spec = _lib.load_spec(skill_dir)
    conv = spec.get("convergence", {})
    if str(conv.get("skip_reason") or "").strip():  # measure が skip のとき（STEP-02）は、一時プロジェクトを作らない
        _lib.fail(f"spec の convergence.skip_reason に、収束テストを省くと書いてあります（{conv['skip_reason']}）。"
                  "実行するなら、skip_reason を消してから準備してください（STEP-02）")
    cfg, sources = plan_settings(spec, args)
    agents, runners = cfg["agents"], cfg["runners"]
    tasks = _lib.load_json(skill_dir / "dev/evals.json").get("tasks", [])
    if args.only_tasks:
        tasks = [t for t in tasks if t.get("id") in set(args.only_tasks.split(","))]
    elif not args.include_holdout:
        tasks = [t for t in tasks if t.get("kind") != "holdout"]
    if not tasks:
        _lib.fail("課題が0件です")
    for task in tasks:
        recorded_inputs(skill_dir, task)
        if _lib.TODO_MARKER in task.get("prompt", ""):
            _lib.fail(f"課題 {task.get('id')} の prompt がひな形のままです")
    if eval_check.scoring(skill_dir) is not None:  # 各エージェントの出力を Eval で採点する（STEP-07）
        errors, stale = eval_check.check(skill_dir)[0], eval_check.stale(skill_dir)
        lacking = eval_check.missing_targets(skill_dir)
        problem = (f"Eval が eval_check.py に通っていません（指摘 {len(errors)} 件）" if errors else
                   f"{eval_check.RESULT_REL} が{stale}" if stale else
                   f"判定するファイルの場所（target）が無い振る舞いがあります（{', '.join(lacking)}）" if lacking else "")
        if problem:
            _lib.fail(f"{problem}。収束テストで出力を Eval で採点できません（references/eval.md の7章、STEP-07）")
    if args.round > 1:  # 前のラウンドの AI の分析と Eval の採点を締め込みに使ってから、次のラウンドに進む
        prev, report = args.round - 1, skill_dir / "dev/convergence-report.md"
        text = report.read_text(encoding="utf-8") if report.is_file() else ""
        stale = _lib.stale_analyses(skill_dir, prev)
        gaps = ([f"AI の分析が無いか、記録を取り直す前の分析です（{', '.join(stale)}）"] if stale else []) + \
            _lib.uncited_findings(skill_dir, prev, text)
        if gaps:
            _lib.fail(f"ラウンド {prev} のエージェントの動きの分析を、締め込みに使った記録がありません。analysis-collect の後に "
                      f"round-{prev}/analysis.md の指摘を分類し、dev/convergence-report.md の「## 動きの指摘」に書いてから準備してください"
                      "（convergence-test.md の5章）\n" + "\n".join(f"- {g}" for g in gaps))
        gaps = eval_check.round_gaps(skill_dir, prev, text) + [g for g in [eval_check.realign_gap(skill_dir, prev, text)] if g]
        if gaps:
            _lib.fail(f"ラウンド {prev} の Eval の採点を、締め込みに使った記録がありません。落ちた判定を分類して dev/convergence-report.md の"
                      "「## Eval の採点」に書き、Eval の疑いか抜けがあれば、ユーザーとすり合わせて Eval を直してから準備してください"
                      "（references/eval.md の7章）\n" + "\n".join(f"- {g}" for g in gaps))
    workdir = Path(args.workdir).resolve() if args.workdir else Path(tempfile.gettempdir()) / "skill-foundation" / spec["name"]
    rdir = round_dir(workdir, args.round)
    if rdir.exists():
        if not args.force:
            _lib.fail(f"{rdir} は準備済みです（作り直すなら --force）")
        shutil.rmtree(rdir)
    place = PLACES[spec["targets"][0]]
    tester = place_tester(args.agents_dir) if "subagent" in runners else ""
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
                for source, relative in recorded_inputs(skill_dir, task):
                    destination = target / relative
                    if not destination.resolve().is_relative_to(target.resolve()):
                        _lib.fail("入力ファイルの配置先が作業ディレクトリを外れています")
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(source, destination)
                # スキルと hooks と fence.py を置いてから git の初回コミットを作る（エージェントの git status に出さない）
                installed = target / place / spec["name"]
                installed.parent.mkdir(parents=True, exist_ok=True)
                _lib.copy_tree(skill_dir, installed, exclude=("__pycache__", ".skill-runs", ".DS_Store", "dev"))
                code, out = _lib.run([sys.executable, str(installed / "scripts/install.py"), "--project", str(target),
                                      "--targets", ",".join(spec["targets"])], target)
                if code != 0:
                    _lib.fail(f"install.py が失敗しました: {_lib.tail(out, 5)}")
                register_fence(target, runner)
                _lib.git_init(target)
                for command in task.get("setup", []):
                    code, out = _lib.run(command, target)
                    if code != 0:
                        _lib.fail(f"{task['id']} の setup `{command}` が失敗しました: {_lib.tail(out, 5)}")
                prompt = task["prompt"]
                if task.get("input_values"):
                    prompt += "\n\n入力: " + json.dumps(task["input_values"], ensure_ascii=False)
                if runner == "subagent":
                    prompt = subagent_prompt(spec, {**task, "prompt": prompt}, target, installed)
                elif task.get("invoke") == "explicit":
                    prompt = INVOKE[runner].replace("{name}", spec["name"]) + prompt
                runs.append({"id": run_id, "task": task["id"], "runner": runner, "dir": str(target), "prompt": prompt,
                             "baseline": snapshot(target)})
                vocab.setdefault(task["id"], vocabulary(target))
                mark_lab(target, rdir, run_id, runner, spec.get("language"))
    plan = {"skill": str(skill_dir), "name": spec["name"], "round": args.round, "runners": runners, "agents": agents,
            "tasks": [t["id"] for t in tasks], "expect": {t["id"]: t.get("expect_status", "done") for t in tasks},
            "place": place, "runs": runs, "vocab": vocab, "fence": True, "prepared_at": rt.now(),
            "settings": {k: cfg[k] for k in ("max_rounds", "thresholds", "model", "effort")}, "setting_sources": sources}
    _lib.write_json(rdir / "plan.json", plan)
    print(f"準備しました: {rdir}")
    print(f"課題 {len(tasks)} 件 × runner {len(runners)} 種 × {agents} 人 = セッション {len(runs)} 回")
    show_settings(cfg, sources, runners)
    if tester:
        print(tester)
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
    if str(conv.get("skip_reason") or "").strip():  # measure が skip のとき（STEP-02）は、一時プロジェクトを作らない
        _lib.fail(f"spec の convergence.skip_reason に、収束テストを省くと書いてあります（{conv['skip_reason']}）。"
                  "実行するなら、skip_reason を消してから準備してください（STEP-02）")
    cfg, sources = plan_settings(spec, args)
    agents, runners = cfg["agents"], cfg["runners"]
    doc = _lib.load_json(skill_dir / "dev/probes.json")
    samples = doc.get("reviews", [])
    if not samples:
        _lib.fail("dev/probes.json に reviews がありません（control に review を持つルールの、違反の見本を書く）")
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
    tester = place_tester(args.agents_dir) if "subagent" in runners else ""
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
                register_fence(target, runner)
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
                mark_lab(target, rdir, runs[-1]["id"], runner, spec.get("language"))
    plan = {"kind": "review", "skill": str(skill_dir), "name": spec["name"], "round": args.round, "runners": runners,
            "agents": agents, "samples": [{"id": x["id"], "rule": x["rule"]} for x in samples], "place": place, "runs": runs,
            "fence": True, "prepared_at": rt.now(),
            "settings": {k: cfg[k] for k in ("model", "effort")}, "setting_sources": sources}
    _lib.write_json(rdir / "plan.json", plan)
    print(f"準備しました: {rdir}")
    print(f"見本 {len(samples)} 件 × runner {len(runners)} 種 × {agents} 人 = セッション {len(runs)} 回")
    show_settings(cfg, sources, runners)
    if tester:
        print(tester)
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
             "convergence.py review-score が生成する。見本ごとに、違反のルールID を返答に挙げたエージェントの割合を数える。"
             "基準は検出率 1.0（全員が見つける）。余計な指摘は見本に無いルールID、一致はエージェント同士で挙げた ID の集合が同じこと。", "",
             "| 見本 | ルール | 検出率 | 余計な指摘 | 一致 | ファイルを変えたエージェント |", "|---|---|---|---|---|---|"]
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
    analysis = plan.get("kind") == "analysis"
    print(f"各プロンプトファイルの中身を、そのまま新しいエージェントに渡す（Agent ツール。subagent_type は {TESTER}。"
          "前後に説明を足さない。並べて起動してよい）。"
          + ("エージェントは結果を作業ディレクトリの analysis.json に自分で書く（最終の返答は保存しなくてよい）。"
             "全件を書いたら analysis-collect を実行する。" if analysis else
             "エージェントの最終の返答は、保存先にそのまま書く。全件を書いたら run を実行する。"))
    print(f"{TESTER} が見つからないと言われたら、Claude Code を再起動してから起動し直す。ほかの型で代わりに動かさない"
          "（fence.py が働かない）。")
    model, effort = chosen(plan, "subagent")
    if model or effort:
        print("Agent ツールに、設定の " + "、".join(f"{k} {v}" for k, v in (("model", model), ("effort", effort)) if v)
              + " を指定して起動する（設定に無い方は指定しない）。")
    for run in runs:
        prompt_file = prompts / f"{safe(run['id'])}.md"
        prompt_file.write_text(run["prompt"], encoding="utf-8")
        last = Path(run["dir"]) / ANALYSIS_OUT if analysis else results / f"{safe(run['id'])}.last.txt"
        print(f"- {run['id']}: プロンプト {prompt_file} → {'結果' if analysis else '保存先'} {last}{'（書き済み）' if last.is_file() else ''}")
    return 0


# ---------------------------------------------------------------- run

def last_message(runner: str, stdout: str, last_file: Path) -> str:
    if runner == "claude":  # --output-format stream-json の最後の result 行（json の1行の出力も読む）
        for line in reversed(stdout.splitlines()):
            try:
                event = json.loads(line)
            except ValueError:
                continue
            if isinstance(event, dict) and "result" in event:
                return str(event.get("result", ""))
        return stdout[-4000:]
    if last_file.is_file():
        return last_file.read_text(encoding="utf-8", errors="replace")
    return _lib.tail(stdout, 40)


def model_info(models: list, efforts: list, **extra) -> dict:
    """モデルと推論エフォート（応答ごとの値で一番多いもの）。分からないものは入れない。"""
    def most(values):
        values = [v for v in values if isinstance(v, str) and v and not v.startswith("<")]  # <synthetic> は製品が足した応答
        return max(sorted(set(values)), key=values.count) if values else ""
    found = {"model": most(models), "effort": most(efforts)}
    return {**{k: v for k, v in found.items() if v}, **extra} if any(found.values()) else {}


def claude_model(out: str) -> dict:
    """claude -p の結果（stream-json の最後の result 行）の modelUsage で、出力のトークンが一番多いモデル。推論エフォートは結果に無い。"""
    for text in [out, *reversed(out.splitlines())]:
        try:
            usage = json.loads(text).get("modelUsage")
        except (ValueError, AttributeError):
            continue
        if isinstance(usage, dict) and usage:
            tokens = {m: (u.get("outputTokens", 0) if isinstance(u, dict) else 0) for m, u in usage.items()}
            return model_info([max(sorted(tokens), key=tokens.get)], [])
    return {}


def codex_settings(command: list[str]) -> dict:
    """runner codex のモデルと推論エフォート。コマンドの -m・-c に無ければ、Codex の設定ファイル（config.toml）の最上位の値。
    codex exec --json の出来事には、モデルも推論エフォートも出ないため、実行の前に設定から読む。"""
    found = {}
    for arg, value in zip(command, command[1:]):
        key = value.partition("=")[0].strip() if arg in ("-c", "--config") else ""
        if arg in ("-m", "--model"):
            found.setdefault("model", value)
        elif key in ("model", "model_reasoning_effort"):
            found.setdefault("model" if key == "model" else "effort", value.partition("=")[2].strip().strip("\"'"))
    config = Path(os.environ.get("CODEX_HOME") or Path.home() / ".codex") / "config.toml"
    try:
        top = re.split(r"^\[", config.read_text(encoding="utf-8"), maxsplit=1, flags=re.M)[0]  # 最初の [表] より前
    except OSError:
        top = ""
    for key, name in (("model", "model"), ("model_reasoning_effort", "effort")):
        match = re.search(rf'^\s*{key}\s*=\s*["\']([^"\']+)["\']', top, re.M)
        if match:
            found.setdefault(name, match.group(1))
    return model_info([found.get("model")], [found.get("effort")], settings=True)


def run_logged(command: list[str], cwd: Path, timeout: int, env: dict, log: Path) -> tuple[int, str]:
    """command を実行し、出力の行を、届いた時刻を付けて log に書く（codex exec --json の出来事には時刻が無いため）。
    戻り値は _lib.run と同じ（終了コード、出力）。"""
    try:
        proc = subprocess.Popen(command, cwd=cwd, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                                encoding="utf-8", errors="replace")
    except FileNotFoundError as exc:
        return 127, str(exc)
    expired = threading.Event()

    def stop():
        expired.set()
        proc.kill()

    timer = threading.Timer(timeout, stop)
    timer.start()
    lines = []
    try:
        with log.open("w", encoding="utf-8") as f:
            for line in proc.stdout:
                lines.append(line)
                at = datetime.datetime.now().astimezone().isoformat(timespec="milliseconds")
                f.write(json.dumps({"at": at, "line": line.rstrip("\n")}, ensure_ascii=False) + "\n")
        code = proc.wait()
    finally:
        timer.cancel()
    return (124, f"[timeout] {timeout} 秒で打ち切りました") if expired.is_set() else (code, "".join(lines))


def cmd_run(args) -> int:
    workdir = Path(args.workdir).resolve()
    rdir = round_dir(workdir, args.round, args.kind)
    plan = _lib.load_json(rdir / "plan.json")
    spec = _lib.load_spec(Path(plan["skill"]))
    conv = spec.get("convergence", {})
    overrides = conv.get("runner_commands", {})
    cfg = _lib.convergence_settings(spec)[0]
    parallel, timeout = args.parallel or cfg["parallel"] or 3, args.timeout or cfg["timeout"] or 1800
    runs = plan["runs"]
    if args.only:
        runs = [r for r in runs if r["id"] in set(args.only.split(","))]
    results = rdir / "_results"
    results.mkdir(parents=True, exist_ok=True)
    env = {k: v for k, v in os.environ.items() if k not in ("CLAUDECODE", "CLAUDE_PROJECT_DIR")}

    def execute(run: dict):
        last = results / f"{safe(run['id'])}.last.txt"
        template = overrides.get(run["runner"]) or with_model(default_runner(run["runner"]), run["runner"], *chosen(plan, run["runner"]))
        command = [a.replace("{prompt}", run["prompt"]).replace("{dir}", run["dir"]).replace("{last}", str(last))
                   for a in template]
        tmp = Path(run["dir"]) / FENCE_REL / "tmp"  # 入力にパスが出ない一時ファイルも、一時プロジェクトの中に入れる
        started = time.monotonic()
        run_env = {**env, "TMPDIR": str(tmp) + "/"} if tmp.is_dir() else env
        if run["runner"] in ("codex", "claude"):  # 操作の列は trace が読む
            code, out = run_logged(command, Path(run["dir"]), timeout, run_env, results / EVENTS.format(id=safe(run["id"])))
        else:
            code, out = _lib.run(command, Path(run["dir"]), timeout=timeout, env=run_env)
        model = codex_settings(command) if run["runner"] == "codex" else claude_model(out) if run["runner"] == "claude" else {}
        record = {"id": run["id"], "runner": run["runner"], "exit": code, "seconds": round(time.monotonic() - started, 1),
                  "message": last_message(run["runner"], out, last), "output_tail": _lib.tail(out, 60), **model}
        _lib.write_json(results / f"{safe(run['id'])}.json", record)
        return run["id"], code, record["seconds"]

    failed = 0
    if plan.get("kind") == "analysis" and any(r["runner"] == "subagent" for r in runs):
        print("runner subagent の分析役は、作業ディレクトリの analysis.json を analysis-collect が直接集める（run では集めない）")
        runs = [r for r in runs if r["runner"] != "subagent"]
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
    unused = sorted({r["runner"] for r in runs if r["runner"] in overrides and any(chosen(plan, r["runner"]))})
    if unused:
        print(f"注意: {', '.join(unused)} は spec の convergence.runner_commands で起動するので、設定のモデル・推論エフォートを足さない")
    print(f"{len(runs)} 件を最大 {parallel} 並列で実行します（1件の上限 {timeout} 秒）")
    with ThreadPoolExecutor(max_workers=parallel) as pool:
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


def fence_changes(run: dict, plan: dict) -> list[str]:
    """独立エージェントの作業ディレクトリ制限を外した証拠だけを返す。"""
    found = []
    if plan.get("fence") and run.get("runner") in FENCE_CONFIGS:
        rel = FENCE_CONFIGS[run["runner"]][0]
        config = Path(run["dir"]) / rel
        if "fence.py" not in (config.read_text(encoding="utf-8", errors="replace") if config.is_file() else ""):
            found.append(f"{rel} から fence.py の登録が外された")
    return found


def changed_files(run: dict, name: str, ignore: list[str], now: dict[str, str]) -> dict[str, str | None]:
    directory = Path(run["dir"])
    base = run["baseline"]
    skip = {f".skill-runs/{name}/state.json", ".skill-runs/.gitignore", _lib.CATALOG_REL}  # カタログはほかの出力から作る図
    result = {}
    for rel in sorted(set(base) | set(now)):
        if (base.get(rel) == now.get(rel) or rel in skip or rel.startswith((FENCE_REL + "/", _lib.CATALOG_PAGES_REL + "/"))
                or rt.matches_any(rel, ignore)):
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


def eval_asks(project: Path, scores: dict) -> dict:
    """model の判定を分析役に頼む振る舞いと、判定する中身（analysis-prepare が record.md に入れる）。"""
    asks = {}
    for bid, score in scores.items():
        if score["result"] == "pending":
            rel, _, frag = score["target"].partition("#")
            asks[bid] = {"target": score["target"], "text": eval_check.model_text(eval_check.target_text(project, rel, frag) or "", rel)}
    return asks


def cmd_diff(args) -> int:
    workdir = Path(args.workdir).resolve()
    rdir = round_dir(workdir, args.round)
    plan = _lib.load_json(rdir / "plan.json")
    skill_dir = Path(plan["skill"])
    spec = _lib.load_spec(skill_dir)
    conv = spec.get("convergence", {})
    thresholds = plan.get("settings", {}).get("thresholds") or _lib.convergence_settings(spec)[0]["thresholds"]
    ignore = conv.get("ignore", [])
    out = Path(args.out).resolve() if args.out else skill_dir / f"dev/results/convergence/round-{plan['round']}"
    out.mkdir(parents=True, exist_ok=True)
    name = plan["name"]
    scored = eval_check.scoring(skill_dir)
    report = {"round": plan["round"], "runners": plan["runners"], "thresholds": thresholds, "fence": bool(plan.get("fence")),
              "eval": {"hash": scored["hash"], "dialog": scored["dialog"]} if scored else {}, "tasks": []}
    for tid in plan["tasks"]:
        runs = sorted([r for r in plan["runs"] if r["task"] == tid], key=lambda r: r["id"])
        names, changes, contents, statuses, checks, messages, broken, events = [], {}, {}, {}, {}, {}, {}, {}
        expected, grades = plan.get("expect", {}).get(tid, "done"), {}
        for run in runs:
            label = run["id"].split("/", 1)[1]
            names.append(label)
            now = snapshot(Path(run["dir"]))
            found = changed_files(run, name, ignore, now)
            evidence = fence_changes(run, plan)
            if evidence:
                broken[label] = evidence
            changes[label] = set(found)
            contents[label] = found
            state_path = Path(run["dir"]) / ".skill-runs" / name / "state.json"
            state = json.loads(state_path.read_text(encoding="utf-8")) if state_path.is_file() else None
            statuses[label] = state.get("status") if state else "unused"
            events[label] = [h.get("event", "") for h in state.get("history", [])] if state else []  # catalog.py がチェックポイントの回数に使う
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
            keep = out / "records" / "outputs" / f"{tid}__{label}"  # catalog.py が画像と HTML を見せる写し。records/ は git に入れない
            shutil.rmtree(keep, ignore_errors=True)
            for rel in found:
                if (Path(run["dir"]) / rel).is_file():
                    (keep / rel).parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(Path(run["dir"]) / rel, keep / rel)
            (out / tid / f"{label}.eval.json").unlink(missing_ok=True)
            if scored and expected != "unused":  # スキルを使わないのが正解の課題には、Eval を当てない
                grades[label] = eval_check.score_run(skill_dir, scored["doc"], Path(run["dir"]), name,
                                                     state.get("input", {}) if state else {})
                asks = eval_asks(Path(run["dir"]), grades[label])
                if asks:
                    _lib.write_json(out / tid / f"{label}.eval.json", asks)
        vocab = set(plan.get("vocab", {}).get(tid, []))
        overall = metrics(names, changes, contents, vocab)
        by_runner = {}
        for runner in plan["runners"]:
            group = [n for n in names if n.startswith(runner + "-")]
            if len(group) >= 2:
                by_runner[runner] = {k: v for k, v in metrics(group, changes, contents, vocab).items() if k != "new_names"}
        check_ok = all(c["exit"] == 0 for c in checks.values())
        variance_ok = (set(statuses.values()) == {expected} and check_ok and not broken
                       and overall["files"] >= thresholds["files"] and overall["structure"] >= thresholds["structure"]
                       and overall["names"] >= thresholds["names"])
        eval_ok = eval_check.task_ok(grades)  # model の判定待ちが残れば None（analysis-collect が決め直す）
        converged = variance_ok and eval_ok is True
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
                                "variance_ok": variance_ok, "eval": grades, "eval_ok": eval_ok,
                                "fence_changed": broken, "events": events,
                                "changed_files": {n: sorted(changes[n]) for n in names}, "partial_files": partial,
                                "excerpts": excerpts, "check_failures": {n: c["tail"] for n, c in checks.items() if c["exit"]},
                                "messages": {n: messages[n][-1500:] for n in names}})
    _lib.write_json(out / "report.json", report)
    (out / "report.md").write_text(render_report(report), encoding="utf-8")
    lost = [line for line in write_traces(plan, rdir, out) if "（記録が見つからない）" in line]
    print(summary(report))
    if lost:
        print("操作の記録が見つからないエージェント（動きを分析できない。skill_lint.py --final が止める。convergence-test.md の7章）:\n"
              + "\n".join(lost))
    print(f"レポート: {out / 'report.md'}")
    return 0 if all(t["converged"] for t in report["tasks"]) else 1


# ---------------------------------------------------------------- trace

TRANSCRIPTS = Path.home() / ".claude" / "projects"  # Claude Code が Agent ツールのエージェントの記録を置く場所
CODEX_SESSIONS = Path.home() / ".codex" / "sessions"  # Codex がセッションの記録（<年>/<月>/<日>/rollout-*.jsonl）を置く場所
INPUT_LIMIT = 4000  # 操作の入力を残す長さ。Codex は1回の実行にコマンドをつなぐので、後ろの run.py まで残す
OUTPUT_HEAD, OUTPUT_TAIL = 400, 200  # 操作の出力を残す字数（先頭と末尾）。AI の分析が、出力から次の操作のわけを推す
EVENTS = "{id}.events.jsonl"  # runner claude の stream-json と runner codex の --json の出力（行ごとに届いた時刻つき）。_results/ に置く


def plan_time(plan: dict, rdir: Path) -> float:
    """plan を作った時刻（エポック秒）。prepared_at の無い古い plan は、plan.json と _prompts/ の更新日時の早い方
    （plan.json は後から書き直されることがあり、その日時で絞ると、それより前に終わったエージェントの記録を落とす）。"""
    try:
        return datetime.datetime.fromisoformat(plan["prepared_at"]).timestamp()
    except (KeyError, TypeError, ValueError):
        pass
    times = [p.stat().st_mtime for p in [rdir / "plan.json", *(rdir / "_prompts").glob("*")] if p.is_file()]
    return min(times) if times else 0.0


def first_message(path: Path) -> str:
    """記録の最初のメッセージ（エージェントに渡したプロンプト）。"""
    try:
        with path.open(encoding="utf-8") as f:
            first = json.loads(f.readline())
    except (OSError, ValueError):
        return ""
    content = first.get("message", {}).get("content") if isinstance(first, dict) else None
    if isinstance(content, list):
        content = "".join(p.get("text", "") for p in content if isinstance(p, dict))
    return content.strip() if isinstance(content, str) else ""


def find_transcripts(prompts: dict[str, str], root: Path, since: float) -> dict[str, Path]:
    """プロンプトの全文が一致する記録。同じプロンプトの記録が複数あれば新しい方。{実行の ID: 記録}"""
    found: dict[str, Path] = {}
    try:
        candidates = list(root.glob("*/*/subagents/agent-*.jsonl"))
    except OSError:
        return found
    for path in candidates:
        try:
            mtime = path.stat().st_mtime
        except OSError:
            continue
        run_id = prompts.get(first_message(path)) if mtime >= since else None
        if run_id and (run_id not in found or found[run_id].stat().st_mtime < mtime):
            found[run_id] = path
    return found


def dir_variants(directory: str) -> list[str]:
    """一時プロジェクトのパスの書き方（そのまま、実体、macOS の /private を外した形）。長い順。"""
    variants = {directory, os.path.realpath(directory)}
    variants |= {v[len("/private"):] for v in list(variants) if v.startswith("/private/")}
    return sorted(variants, key=len, reverse=True)


def relative(text: str, directory: str) -> str:
    """一時プロジェクトの絶対パスを相対にし、先頭の `cd <一時プロジェクト> && ` を除く。"""
    for prefix in dir_variants(directory):
        text = text.replace(prefix + "/", "").replace(prefix, ".")
    return re.sub(r"^cd \. && ", "", text)


def tool_input(name: str, data: dict, directory: str) -> str:
    if name == "Bash":
        value = data.get("command", "")
    elif data.get("file_path"):
        value = data["file_path"]
    elif name in ("Grep", "Glob"):
        value = " ".join(str(data[k]) for k in ("pattern", "path") if data.get(k))
    else:
        value = data.get("url") or data.get("query") or data.get("skill") or ""
    return relative(str(value), directory)[:INPUT_LIMIT]


def result_text(part: dict) -> str:
    content = part.get("content")
    if isinstance(content, list):
        content = " ".join(str(c.get("text", "")) for c in content if isinstance(c, dict))
    return content if isinstance(content, str) else ""


def excerpt(text: str, directory: str) -> dict:
    """操作の出力の先頭と末尾（間は略した字数を書く）。出力が無ければ何も足さない。"""
    text = relative(str(text or ""), directory).strip()
    if len(text) > OUTPUT_HEAD + OUTPUT_TAIL + 20:
        text = f"{text[:OUTPUT_HEAD]}\n…（{len(text) - OUTPUT_HEAD - OUTPUT_TAIL} 字を略）…\n{text[-OUTPUT_TAIL:]}"
    return {"out": text} if text else {}


def transcript_actions(path: Path, directory: str, fenced: set | None = None) -> list[dict]:
    """記録の道具の呼び出しを、時刻・道具・主な入力・成否（tool_result の is_error）・出力の抜粋の列にする。
    fence.py が止めた呼び出し（fence.py の記録にある ID か、結果に fence.py の目印があるもの）には fenced を付ける。
    api-request-blob などの項目は、API に送った会話の写しで前の呼び出しをもう一度含むので、読まない。
    runner claude の stream-json の出力（run_logged が届いた時刻を付けて包んだ行）も、包みを外して同じに読む。"""
    calls, results, outputs, stopped = [], {}, {}, set(fenced or ())
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            entry = json.loads(line)
            if isinstance(entry, dict) and "line" in entry and "type" not in entry:
                entry = {"timestamp": entry.get("at", ""), **json.loads(entry["line"])}
        except (ValueError, TypeError):
            continue
        if not isinstance(entry, dict) or entry.get("type") not in ("assistant", "user"):
            continue
        content = entry.get("message", {}).get("content")
        for part in content if isinstance(content, list) else []:
            if not isinstance(part, dict):
                continue
            if part.get("type") == "tool_use" and all(call[1] != part.get("id") for call in calls):
                calls.append((entry.get("timestamp", ""), part.get("id"), part.get("name", ""), part.get("input") or {}))
            elif part.get("type") == "tool_result":
                results[part.get("tool_use_id")] = not part.get("is_error")
                outputs[part.get("tool_use_id")] = result_text(part)
                if part.get("is_error") and FENCED.search(result_text(part)):
                    stopped.add(part.get("tool_use_id"))
    return [{"at": at, "tool": name, "input": tool_input(name, data if isinstance(data, dict) else {}, directory),
             "ok": results.get(call_id), **excerpt(outputs.get(call_id, ""), directory), **({"fenced": True} if call_id in stopped else {})}
            for at, call_id, name, data in calls]


def shell_script(command) -> str:
    """Codex が記録するコマンド（["/bin/zsh", "-lc", "<スクリプト>"] か、その形の文字列）から、シェルに渡したスクリプト。"""
    words = command
    if isinstance(command, str):
        try:
            words = shlex.split(command)
        except ValueError:
            return command
    if not isinstance(words, list):
        return str(command or "")
    if len(words) >= 3 and Path(str(words[0])).name in ("sh", "bash", "zsh") and words[1] in ("-c", "-lc"):
        return str(words[2])
    return command if isinstance(command, str) else shlex.join(str(w) for w in words)


CODEX_ITEMS = {"CommandExecution": "command", "command_execution": "command", "FileChange": "file", "file_change": "file",
               "ImageView": "image", "McpToolCall": "mcp", "mcp_tool_call": "mcp", "WebSearch": "web", "web_search": "web"}


def codex_actions(entries: list[tuple[str, dict]], directory: str, fenced: set | None = None) -> list[dict]:
    """Codex の記録の項目（(時刻, 項目)。サブエージェントの記録と codex exec --json の両方の書き方）を、traces.json の操作に
    する。道具の名前は Claude Code の名前（Bash・Write・Edit・Read・WebSearch）にそろえ、catalog.py が同じに読む。
    考えたこと（reasoning）と返答の文は、操作に数えない（Codex の reasoning は暗号化されて残り、読めない）。"""
    actions, stopped = [], set(fenced or ())
    for at, item in entries:
        kind, status = CODEX_ITEMS.get(item.get("type")), item.get("status")
        done = status == "completed" if status else None
        if kind == "command":
            code, output = item.get("exit_code"), str(item.get("aggregated_output") or "")
            ok = code == 0 if code is not None else (False if status in ("failed", "declined") else None)
            mark = item.get("id") in stopped or item.get("call_id") in stopped or bool(FENCED.search(output))
            actions.append({"at": at, "tool": "Bash", "input": relative(shell_script(item.get("command")), directory)[:INPUT_LIMIT],
                            "ok": ok, **excerpt(output, directory), **({"fenced": True} if mark else {})})
        elif kind == "file":
            changes = item.get("changes") or {}
            pairs = (sorted(changes.items()) if isinstance(changes, dict)
                     else [(c.get("path", ""), c) for c in changes if isinstance(c, dict)])
            for path, change in pairs:
                how = (change or {}).get("type") or (change or {}).get("kind")
                actions.append({"at": at, "tool": {"add": "Write", "delete": "Delete"}.get(how, "Edit"),
                                "input": relative(str(path), directory), "ok": done})
        elif kind == "image":
            path = re.sub(r"^file://", "", str(item.get("path", "")))
            actions.append({"at": at, "tool": "Read", "input": relative(path, directory), "ok": True})
        elif kind == "mcp":
            arguments = item.get("arguments")
            actions.append({"at": at, "tool": f"mcp {item.get('server', '')} {item.get('tool', '')}".strip(),
                            "input": (json.dumps(arguments, ensure_ascii=False) if arguments else "")[:INPUT_LIMIT],
                            "ok": False if item.get("error") else done})
        elif kind == "web":
            actions.append({"at": at, "tool": "WebSearch", "input": str(item.get("query", "")), "ok": True if done is None else done})
    return actions


def ms_time(ms: float) -> str:
    return datetime.datetime.fromtimestamp(ms / 1000, datetime.timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def rollout_entries(path: Path) -> tuple[dict, list[tuple[str, dict]]]:
    """Codex の記録（rollout-*.jsonl）の、セッションの情報と、終わった項目（(始めた時刻, 項目)。始めた順）。"""
    meta, entries = {}, []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            entry = json.loads(line)
        except ValueError:
            continue
        payload = entry.get("payload") if isinstance(entry, dict) else None
        if not isinstance(payload, dict):
            continue
        if entry.get("type") == "session_meta":
            meta = payload
        elif entry.get("type") == "event_msg" and payload.get("type") == "item_completed" and isinstance(payload.get("item"), dict):
            ms = payload.get("started_at_ms") or payload.get("completed_at_ms")
            moment = ms / 1000 if isinstance(ms, (int, float)) else None
            if moment is None:
                try:
                    moment = datetime.datetime.fromisoformat(str(entry.get("timestamp", "")).replace("Z", "+00:00")).timestamp()
                except ValueError:
                    continue
            entries.append((moment, payload["item"]))
    return meta, [(ms_time(moment * 1000), item) for moment, item in sorted(entries, key=lambda e: e[0])]


def transcript_model(path: Path) -> dict:
    """Agent ツールの記録の、モデル（応答の message.model）と推論エフォート（応答の effort）。"""
    models, efforts = [], []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            entry = json.loads(line)
        except ValueError:
            continue
        if isinstance(entry, dict) and entry.get("type") == "assistant":
            message = entry.get("message") if isinstance(entry.get("message"), dict) else {}
            models.append(message.get("model") or entry.get("requestedModel"))
            efforts.append(entry.get("effort"))
    return model_info(models, efforts)


def rollout_model(path: Path) -> dict:
    """Codex の記録の、モデルと推論エフォート（turn_context の model と effort）。"""
    models, efforts = [], []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            entry = json.loads(line)
        except ValueError:
            continue
        payload = entry.get("payload") if isinstance(entry, dict) else None
        if entry.get("type") == "turn_context" and isinstance(payload, dict):
            models.append(payload.get("model"))
            efforts.append(payload.get("effort"))
    return model_info(models, efforts)


def codex_places(items: list[dict]) -> str:
    """項目のうち、場所を表すもの（コマンド、cwd、変えたファイル、見た画像）。コマンドの出力は含めない。"""
    parts = []
    for item in items:
        changes = item.get("changes")
        paths = list(changes) if isinstance(changes, dict) else [c.get("path", "") for c in changes or [] if isinstance(c, dict)]
        parts += [str(item[k]) for k in ("command", "cwd", "path") if item.get(k)] + [str(p) for p in paths]
    return "\n".join(parts)


def find_codex_rollouts(dirs: dict[str, str], root: Path, since: float) -> dict[str, tuple[Path, list]]:
    """Codex のサブエージェントの記録のうち、コマンドとファイルのパスに、その実行の作業ディレクトリが一番多く出るもの。
    Codex の記録では依頼文が暗号化されて残るので、プロンプトでは突き合わせられない。{実行の ID: (記録, 項目)}"""
    patterns = {rid: re.compile("(?:" + "|".join(re.escape(v) for v in dir_variants(d)) + r")(?![\w.-])") for rid, d in dirs.items()}
    found: dict[str, tuple[Path, list, int]] = {}
    try:
        candidates = sorted(root.glob("*/*/*/rollout-*.jsonl"))
    except OSError:
        return {}
    for path in candidates:
        try:
            if path.stat().st_mtime < since:
                continue
        except OSError:
            continue
        meta, entries = rollout_entries(path)
        source = meta.get("source")
        if meta.get("thread_source") != "subagent" and not (isinstance(source, dict) and "subagent" in source):
            continue
        text = codex_places([item for _, item in entries])
        hits = {rid: len(rx.findall(text)) for rid, rx in patterns.items()}
        best = max(hits.values(), default=0)
        owners = [rid for rid, n in hits.items() if n == best]
        if best and len(owners) == 1 and (owners[0] not in found or found[owners[0]][2] < best):
            found[owners[0]] = (path, entries, best)
    return {rid: (path, entries) for rid, (path, entries, _) in found.items()}


def exec_entries(path: Path) -> list[tuple[str, dict]]:
    """runner codex の --json の出力（run_logged が行ごとに届いた時刻を付けたもの）の、終わった項目（(始まった時刻, 項目)）。"""
    started, entries = {}, []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            record = json.loads(line)
            event = json.loads(record.get("line", ""))
        except (ValueError, AttributeError, TypeError):
            continue
        item = event.get("item") if isinstance(event, dict) else None
        if not isinstance(item, dict):
            continue
        if event.get("type") == "item.started":
            started.setdefault(item.get("id"), record.get("at", ""))
        elif event.get("type") == "item.completed":
            entries.append((started.get(item.get("id"), record.get("at", "")), item))
    return sorted(entries, key=lambda e: e[0])


def fence_log(directory: str) -> list[dict]:
    """fence.py が止めた操作の記録（一時プロジェクトの .skill-runs/_fence/log.jsonl）。"""
    path = Path(directory) / FENCE_REL / "log.jsonl"
    entries = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines() if path.is_file() else []:
        try:
            entries.append(json.loads(line))
        except ValueError:
            continue
    return entries


def keep_procedure(plan: dict, out: Path) -> None:
    """エージェントが読んだ SKILL.md（一時プロジェクトに置いた写し）を out/USED_SKILL に残す。締め込みで SKILL.md が変わった後も、
    分析はそのラウンドの手順と比べる。"""
    for run in plan["runs"]:
        used = Path(run["dir"]) / plan.get("place", PLACES["claude"]) / plan["name"] / "SKILL.md"
        if used.is_file():
            shutil.copyfile(used, out / USED_SKILL)
            return


def round_procedure(skill_dir: Path, rnd: int) -> str:
    """ラウンド rnd でエージェントが読んだ SKILL.md。残っていなければ今の SKILL.md。"""
    used = skill_dir / f"dev/results/convergence/round-{rnd}" / USED_SKILL
    return (used if used.is_file() else skill_dir / "SKILL.md").read_text(encoding="utf-8")


RUN_EVENTS = {"start": "start", "restart": "start --restart", "check": "check", "finish": "finish", "finish-rejected": "finish",
              "waiting": "wait --question", "aborted": "abort --reason"}  # 実行記録の出来事と、それを書いた run.py のサブコマンド
CLAUDE_PARTIAL = ("一部だけ（stream-json を保存する前の版の claude -p で実行した。操作は run.py の実行記録から、許可されなかった操作は"
                  " claude -p の出力から作った。読む・書く・ほかのコマンドは残っていない）")


def claude_result_actions(outcome: dict, state: dict, end: float, script: str, directory: str) -> tuple[list[dict], list[dict]]:
    """stream-json を保存する前の版の runner claude の、残った記録から作る（操作, 許可されなかった操作）。操作は、実行の間に
    run.py が書いた実行記録（state.json の history。hooks の出来事と、実行の後の diff などの check は除く）。start のコマンドは
    記録に無いので、run.py が記録した入力と依頼文から組み立て、そのことを出力に書く。許可されなかった操作は、claude -p の
    json の出力の permission_denials（時刻が無いので、操作の列には入れない）。end は実行が終わった時刻（結果を書いた時刻）。"""
    begin, actions = end - float(outcome.get("seconds") or 0) - 5, []
    given = "".join(f" --set {k}={shlex.quote(str(v))}" for k, v in (state.get("input") if isinstance(state.get("input"), dict) else {}).items())
    given += f" {shlex.quote(str(state['text']))}" if state.get("text") else ""
    for event in state.get("history", []):
        sub = RUN_EVENTS.get(event.get("event")) if isinstance(event, dict) else None
        try:
            moment = datetime.datetime.fromisoformat(str(event.get("at", ""))).timestamp() if sub else None
        except ValueError:
            moment = None
        if moment is None or not begin <= moment <= end + 2:
            continue
        detail = str(event.get("detail", ""))
        count = re.match(r"(\d+) 件", detail)
        if sub.startswith("start"):
            argument, note = given, {"out": "コマンドは記録に無い。引数は run.py が記録した入力と依頼文から組み立てた"}
        else:
            argument = f" {shlex.quote(detail)}" if sub.endswith(("--question", "--reason")) else ""
            note = {"out": f"指摘 {detail}"} if count else {}
        actions.append({"at": event["at"], "tool": "Bash", "input": f"{script} {sub}{argument}",
                        "ok": int(count.group(1)) == 0 if count else True, **note})
    try:
        output = json.loads(str(outcome.get("output_tail", "")))
    except ValueError:
        output = {}
    denials = output.get("permission_denials", []) if isinstance(output, dict) else []
    denied = [{"tool": str(d.get("tool_name", "")),
               "input": tool_input(str(d.get("tool_name", "")), d["tool_input"] if isinstance(d.get("tool_input"), dict) else {}, directory)}
              for d in denials if isinstance(d, dict)]
    return actions, denied


RECORDS = "records"  # 元の記録の写し（gzip）。一時ディレクトリや製品の記録が消えても trace で動きを作り直せるよう、結果の置き場に残す


def keep_record(src: Path | None, out: Path, name: str) -> None:
    """src を out/records/<name>.gz に写す。gzip の見出しの時刻に src の更新日時を入れ、戻すときに使う（中身が同じなら書き直さない）。"""
    if not src or not src.is_file():
        return
    dest, data = out / RECORDS / f"{name}.gz", src.read_bytes()
    if dest.is_file() and gzip.decompress(dest.read_bytes()) == data:
        return
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(gzip.compress(data, mtime=int(src.stat().st_mtime)))


def restore_record(out: Path, name: str, dest: Path) -> bool:
    """dest が無く、out/records/<name>.gz があれば、dest に戻す（更新日時も戻す）。戻した後に dest があるか。"""
    archived = out / RECORDS / f"{name}.gz"
    if dest.is_file() or not archived.is_file():
        return dest.is_file()
    blob = archived.read_bytes()
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(gzip.decompress(blob))
    moment = int.from_bytes(blob[4:8], "little")  # gzip の見出しの MTIME
    os.utime(dest, (moment, moment))
    return True


def record_files(plan: dict, rdir: Path, run: dict) -> dict[str, Path]:
    """実行ごとに写す記録（写しの名前の後ろ: 元の場所）。製品の記録（Agent ツール、Codex のセッション）は write_traces が足す。"""
    sid, home = safe(run["id"]), Path(run["dir"])
    return {"events.jsonl": rdir / "_results" / EVENTS.format(id=sid), "result.json": rdir / "_results" / f"{sid}.json",
            "state.json": home / rt.RUNS_DIRNAME / plan["name"] / "state.json", "fence.jsonl": home / FENCE_REL / "log.jsonl",
            "prompt.md": rdir / "_prompts" / f"{sid}.md"}


def write_traces(plan: dict, rdir: Path, out: Path, root: Path = TRANSCRIPTS, codex_root: Path = CODEX_SESSIONS) -> list[str]:
    """各エージェントの動きを out/traces.json に書く。catalog.py がワークフロー図に重ねる。元の記録の写しを out/records に残し、
    元の記録が消えていれば写しから戻して使う。"""
    keep_procedure(plan, out)
    keep_record(rdir / "plan.json", out, "plan.json")
    for run in plan["runs"]:
        for kind, src in record_files(plan, rdir, run).items():
            restore_record(out, f"{safe(run['id'])}.{kind}", src)
    prompts = {}
    for run in plan["runs"]:
        prompt_file = rdir / "_prompts" / f"{safe(run['id'])}.md"
        if run.get("runner") == "subagent" and prompt_file.is_file():
            prompts[prompt_file.read_text(encoding="utf-8").strip()] = run["id"]
    since = plan_time(plan, rdir) - 60
    found = find_transcripts(prompts, root, since) if prompts else {}
    lost = {run["id"]: run["dir"] for run in plan["runs"] if run.get("runner") == "subagent" and run["id"] not in found}
    codex = find_codex_rollouts(lost, codex_root, since) if lost else {}
    for rid in [r for r in lost if r not in codex]:  # 製品の記録が消えた後は、写しを使う
        sid = safe(rid)
        if restore_record(out, f"{sid}.transcript.jsonl", rdir / RECORDS / f"{sid}.transcript.jsonl"):
            found[rid] = rdir / RECORDS / f"{sid}.transcript.jsonl"
        elif restore_record(out, f"{sid}.rollout.jsonl", rdir / RECORDS / f"{sid}.rollout.jsonl"):
            codex[rid] = (rdir / RECORDS / f"{sid}.rollout.jsonl", rollout_entries(rdir / RECORDS / f"{sid}.rollout.jsonl")[1])
    runs, lines = {}, []
    for run in sorted(plan["runs"], key=lambda r: r["id"]):
        state_path = Path(run["dir"]) / rt.RUNS_DIRNAME / plan["name"] / "state.json"
        try:
            state = json.loads(state_path.read_text(encoding="utf-8")) if state_path.is_file() else {}
            events = state.get("history", [])
        except (OSError, ValueError, AttributeError):
            state, events = {}, []
        stopped = fence_log(run["dir"])
        ids = {e.get("tool_use_id") for e in stopped}
        runner = run.get("runner", "")
        exec_log = rdir / "_results" / EVENTS.format(id=safe(run["id"]))
        result = rdir / "_results" / f"{safe(run['id'])}.json"
        try:  # runner claude・codex のモデルは、run が実行の結果に書く
            outcome = _lib.load_json(result) if result.is_file() else {}
            model = {k: v for k, v in outcome.items() if k in ("model", "effort", "settings")}
        except (OSError, ValueError, AttributeError):
            outcome, model = {}, {}
        denied = []
        if run["id"] in found:
            actions, source = transcript_actions(found[run["id"]], run["dir"], ids), f"Agent ツールの記録 {found[run['id']].name}"
            model = transcript_model(found[run["id"]])
        elif run["id"] in codex:
            path, entries = codex[run["id"]]
            actions, source = codex_actions(entries, run["dir"], ids), f"Codex のサブエージェントの記録 {path.name}"
            model = rollout_model(path)
        elif runner == "codex" and exec_log.is_file():
            actions, source = codex_actions(exec_entries(exec_log), run["dir"], ids), f"codex exec の出力 {exec_log.name}"
        elif runner == "claude" and exec_log.is_file():
            actions, source = transcript_actions(exec_log, run["dir"], ids), f"claude -p の出力 {exec_log.name}"
        elif runner == "claude" and outcome:
            script = f"python3 {plan.get('place', PLACES['claude'])}/{plan['name']}/scripts/run.py"
            (actions, denied), source = claude_result_actions(outcome, state, result.stat().st_mtime, script, run["dir"]), CLAUDE_PARTIAL
        else:
            actions, source = [], "記録が見つからない"
        runs[run["id"]] = {"runner": runner, "source": source, "events": events, "actions": actions, **model,
                           **({"denied": denied} if denied else {}), **({"fenced": len(stopped)} if stopped else {})}
        lines.append(f"- {run['id']}: 操作 {len(actions)} 件（{source}）、実行の記録 {len(events)} 件"
                     + (f"、fence.py が止めた操作 {len(stopped)} 件" if stopped else ""))
        sid = safe(run["id"])
        for kind, src in record_files(plan, rdir, run).items():
            keep_record(src, out, f"{sid}.{kind}")
        keep_record(found.get(run["id"]), out, f"{sid}.transcript.jsonl")
        keep_record(codex[run["id"]][0] if run["id"] in codex else None, out, f"{sid}.rollout.jsonl")
    _lib.write_json(out / "traces.json", {"round": plan["round"], "runs": runs})
    return lines


def cmd_trace(args) -> int:
    workdir = Path(args.workdir).resolve()
    rdir = round_dir(workdir, args.round)
    if args.out:  # 一時ディレクトリが消えていれば、結果の置き場の写しから plan を戻す
        restore_record(Path(args.out).resolve(), "plan.json", rdir / "plan.json")
    plan = _lib.load_json(rdir / "plan.json")
    out = Path(args.out).resolve() if args.out else Path(plan["skill"]) / f"dev/results/convergence/round-{plan['round']}"
    out.mkdir(parents=True, exist_ok=True)
    lines = write_traces(plan, rdir, out, Path(args.transcripts).expanduser() if args.transcripts else TRANSCRIPTS,
                         Path(args.codex_sessions).expanduser() if args.codex_sessions else CODEX_SESSIONS)
    print("\n".join(lines))
    print(f"動き: {out / 'traces.json'}")
    return 0


# ---------------------------------------------------------------- analysis

ANALYSIS_IN, ANALYSIS_OUT = "record.md", "analysis.json"  # 分析役に読ませる記録と、分析役が書く結果（どちらも分析役の作業ディレクトリ）
ANALYSIS_ASK = ("作業ディレクトリは `{dir}` である。この中だけで作業する。\n\n"
                f"`{{dir}}/{ANALYSIS_IN}` を読み、そこに書かれた指示に従って、エージェントの動きの分析を `{{dir}}/{ANALYSIS_OUT}` に書く。"
                f"{ANALYSIS_IN} を読むことと {ANALYSIS_OUT} を書くこと以外はしない（ほかのファイルは読まず、変えない）。"  # Codex は読むのもコマンド
                "最終の返答は「書きました」とだけ返す。")
WHY_MAX, SUMMARY_MAX, ITEM_MAX, ITEMS_MAX = 100, 300, 150, 5  # 分析の文の長さ（分析役に頼む上限。カタログの表と札に収める）
SLACK = 1.5  # analysis-collect が受け入れる長さは、頼んだ上限のこの倍まで（字数を正確に数えられないため）
EVAL_RESULTS = ("pass", "fail", "na")  # 分析役の model の判定
RECORD_INPUT = 1500  # 記録に載せる操作の入力の字数


def fenced_text(text: str) -> str:
    """text を、中に出るより長いバッククォートの並びで囲む。"""
    longest = max((len(m) for m in re.findall(r"`+", text)), default=0)
    mark = "`" * max(3, longest + 1)
    return f"{mark}\n{text}\n{mark}"


def procedure_text(skill_md: str) -> str:
    """SKILL.md の「2.」の節（手順）の本文。"""
    match = re.search(r"^## 2\.[^\n]*\n(.*?)(?=^## |\Z)", skill_md, re.S | re.M)
    return match.group(1).strip() if match else ""


def step_flow(nos: list) -> str:
    """いた手順の並び（続けて同じ手順は1つにまとめる）。"""
    flow = [n for i, n in enumerate(nos) if n is not None and (i == 0 or n != nos[i - 1])]
    return " → ".join(str(n) for n in flow) or "なし"


def analysis_record(name: str, rnd: int, task: str, prompt: str, procedure: str, steps: list, agent: str, run: dict,
                    others: list[tuple[str, dict]], status: dict, message: str, target: Path, asks: dict | None = None,
                    behaviors: dict | None = None) -> str:
    """分析役に読ませる記録。手順・依頼・操作（入力・出力・成否・手順との照合）・最終の返答と、書き方の決まり。"""
    import catalog  # 操作を手順に当てる処理は、カタログと同じものを使う
    acts = [catalog.interpret(a) for a in run["actions"]]
    walked = catalog.walk(acts, steps)
    moments = [catalog.parse_time(a.get("at", "")) for a in run["actions"]]
    first = next((m for m in moments if m), None)
    limits = {"WHY": WHY_MAX, "SUMMARY": SUMMARY_MAX, "ITEM": ITEM_MAX, "ITEMS": ITEMS_MAX, "N": len(acts)}
    example = {"ops": [{"n": 1, "fit": "ok", "why": "手順を知るため、最初に SKILL.md を読んだ"}],
               "flow": {"verdict": "fair", "summary": "…", "issues": ["#5 …"], "suggestions": ["手順 3 に …と書く"]},
               "compare": "…"}
    if asks:
        example["eval"] = [{"behavior": next(iter(asks)), "result": "pass", "reason": "…"}]
    lines = [f"# エージェントの動きの分析（{name}、ラウンド {rnd}、{task}/{agent}）", "",
             f"スキル `{name}` の収束テストで、作成に関わっていない独立エージェント `{agent}` が、課題 `{task}` の依頼を解いた。"
             "その記録を読み、各操作をした理由と、流れが妥当かを分析する。", "",
             "- エージェント自身の考えは記録に残っていない（Codex は暗号化され、Claude Code は空になる）。下の手順・依頼・操作の入力と出力・"
             "成否・最終の返答から推し量る",
             "- 記録から分からないことは「記録からは分からない」と書く。作らない",
             "- 読み手はこのスキルを作った人である。すぐ意味が通る言葉で書き、内部の略語や比喩を使わない",
             "- 「手順との照合」は、操作を SKILL.md の手順に機械で当てたもの（コマンドは書かれた手順へ、読む・書くは本文にそのパスがある"
             "手順へ）。誤っていることがある", "",
             "## 書くもの", "",
             f"`{target}/{ANALYSIS_OUT}` に、次の形の JSON を書く（UTF-8。JSON だけ）。", "",
             fenced_text(json.dumps(example, ensure_ascii=False, indent=2)), "",
             "- `ops`: 操作の全件を、#1 から #{N} まで番号順に1件ずつ書く（{N} 件）",
             "- `why`: その操作をした理由の推定を1文で（{WHY} 字以内）。直前の操作の出力や失敗、手順のどこに当たるか、依頼のどの部分の"
             "ためかを根拠にする",
             "- `fit`: `ok`（手順か依頼のために要る操作）、`detour`（手順に無いが、確かめるためなどの理由があり、害の無い寄り道）、"
             "`waste`（やらなくてよかった操作。同じものの読み直し、すぐ取り消した書き込みなど）、`wrong`（手順やルールに反する操作、"
             "誤った操作）",
             "- `flow.verdict`: `good`（手順どおりで、無駄が無い）、`fair`（おおむね手順どおりだが、寄り道や無駄がある）、"
             "`poor`（手順を抜かした、順番を誤った、誤った操作が結果に響いた）",
             "- `flow.summary`: 流れ全体の評価を2〜3文で（{SUMMARY} 字以内）。最後の結果と、そこまでの道筋の両方に触れる",
             "- `flow.issues`: 問題だった点（無ければ空の配列）。1つ {ITEM} 字以内、{ITEMS} 個まで。操作の番号（#3 など）を添える",
             "- `flow.suggestions`: スキル（SKILL.md の手順、スクリプト、ルール）をどう直せば防げるか（無ければ空の配列）。1つ {ITEM} 字以内、"
             "{ITEMS} 個まで。どの手順・どのファイルかを書く",
             "- `compare`: 同じ課題のほかのエージェント（最後の節）との違いと、そのわけの推定を1〜3文で（{SUMMARY} 字以内）。"
             "ほかにいなければ空の文字列", ""]
    if asks:
        lines[-1:-1] = ["- `eval`: 最後の節「Eval の判定」の振る舞いごとに1件。`behavior` は振る舞いの ID、`result` は `pass`（基準を満たす）・"
                        "`fail`（満たさない）・`na`（判定の対象が出力に無い。依頼がその出力を求めていないなど）、`reason` は判定の根拠を、"
                        "出力のどこを見たかとともに1〜2文で（{ITEM} 字以内）。動きの良し悪しは混ぜず、基準の文と出力の中身だけで判定する"]
    for key, value in limits.items():  # 決まりの文だけを埋める（記録の入力や出力にある同じ文字は変えない）
        lines = [line.replace("{" + key + "}", str(value)) for line in lines]
    lines += ["## 手順（SKILL.md の「2.」の節）", "", procedure, "",
             f"## 依頼（課題 {task}）", "", fenced_text(prompt or "（記録に無い）"), "",
             f"## エージェント {agent}", "",
             f"- 動かし方: {run.get('runner') or '不明'}、モデル: {run.get('model') or '不明'}、推論エフォート: {run.get('effort') or '不明'}",
             f"- 記録の出典: {run.get('source') or '不明'}" + ("。この記録に無い操作（読む・書く・scan などのコマンド）は、しなかったのではなく"
                                                           "残っていない。記録に無いことを理由に、手順を飛ばしたとは書かず、`wrong` にしない"
                                                           if run.get("source") == CLAUDE_PARTIAL else ""),
             f"- 結果: {status or '不明'}",
             "- チェックポイント（run.py）の記録: " + ("、".join(str(e.get("event", "")) + (f"（{e['detail']}）" if e.get("detail") else "")
                                                       for e in run.get("events", []) if isinstance(e, dict)) or "なし"),
             f"- いた手順の並び（機械の照合）: {step_flow([no for no, _ in walked])}", "",
             f"### 操作（{len(acts)} 件）"]
    for n, (raw, act, (no, hit), moment) in enumerate(zip(run["actions"], acts, walked, moments), 1):
        sec = f"{(moment - first).total_seconds():.0f} 秒" if moment and first else "時刻不明"
        result = {True: "成功", False: "失敗", None: "成否不明"}[act["ok"]] + ("、fence.py が止めた" if act["fenced"] else "")
        where = ("どの手順にも当たらない" + (f"（手順 {no} の途中）" if no else "（手順を始める前）") if hit is None
                 else f"手順 {hit}" + (f"（手順 {no} の途中）" if no != hit else ""))
        text = str(raw.get("input", ""))
        lines += ["", f"#### #{n}（{sec}、{raw.get('tool', '')}、{result}、手順との照合: {where}）", "", "入力:",
                  fenced_text(text if len(text) <= RECORD_INPUT else text[:RECORD_INPUT] + f"\n…（{len(text) - RECORD_INPUT} 字を略）")]
        if raw.get("out"):
            lines += ["出力（抜粋）:", fenced_text(str(raw["out"]))]
    if run.get("denied"):
        lines += ["", f"### Claude Code が許可しなかった操作（{len(run['denied'])} 件。時刻が無く、上の操作との前後は分からない）", "",
                  "上の操作の列には入れていない（番号が無い）。触れるときは「許可されなかった操作 1」のように書く。"]
        for k, item in enumerate(run["denied"], 1):
            text = str(item.get("input", ""))
            lines += ["", f"#### 許可されなかった操作 {k}（{item.get('tool', '')}）", "",
                      fenced_text(text if len(text) <= RECORD_INPUT else text[:RECORD_INPUT] + f"\n…（{len(text) - RECORD_INPUT} 字を略）")]
    lines += ["", "### 最終の返答（末尾）", "", fenced_text(message or "（記録に無い）"), "",
              "## ほかのエージェントの流れ（同じ課題）", ""]
    for other, data in others:
        oacts = [catalog.interpret(a) for a in data.get("actions", [])]
        lines.append(f"- {other}: 操作 {len(oacts)} 件。いた手順の並び: {step_flow([no for no, _ in catalog.walk(oacts, steps)])}")
        lines += [f"  - #{k} {catalog.KINDS[a['kind']]} {a['label'][:60]}" + ("（失敗）" if a["ok"] is False else "")
                  for k, a in enumerate(oacts, 1)]
    if not others:
        lines.append("（ほかにいない）")
    if asks:
        lines += ["", "## Eval の判定（出力がスキルの価値を満たすか）", "",
                  "このスキルを作った人が、ユーザーと確かめた価値を判定する基準である。振る舞いごとに、判定するファイル（このエージェントの"
                  "出力）の中身を基準の文に照らして判定し、`eval` に書く。"]
        for bid, ask in asks.items():
            behavior = (behaviors or {}).get(bid, {})
            lines += ["", f"### {bid}", "", f"- 振る舞い: {behavior.get('text', '（記録に無い）')}",
                      f"- 基準: {(behavior.get('judge') or {}).get('rubric', '（記録に無い）')}",
                      f"- 判定するファイル: `{ask.get('target', '')}`", "", fenced_text(ask.get("text") or "（中身が無い）")]
    return "\n".join(lines) + "\n"


def cmd_analysis_prepare(args) -> int:
    import catalog
    skill_dir = Path(args.skill).resolve()
    spec = _lib.load_spec(skill_dir)
    results = skill_dir / f"dev/results/convergence/round-{args.round}"
    traces = _lib.load_json(results / "traces.json")
    report = _lib.load_json(results / "report.json") if (results / "report.json").is_file() else {}
    text = round_procedure(skill_dir, args.round)
    steps, procedure = catalog.parse_steps(text), procedure_text(text)
    evals = _lib.load_json(skill_dir / "dev/evals.json") if (skill_dir / "dev/evals.json").is_file() else {}
    prompts = {t.get("id"): t.get("prompt", "") for t in evals.get("tasks", []) if isinstance(t, dict)}
    info = {t.get("id"): t for t in report.get("tasks", []) if isinstance(t, dict)}
    cfg, sources, warnings = _lib.convergence_settings(spec, {"analysis": {"runner": args.runner, "model": args.model,
                                                                           "effort": args.effort}})
    for warning in warnings:
        print(f"注意: {warning}")
    runner = cfg["analysis"]["runner"] or (cfg["runners"] or ["claude"])[0]
    model, effort = cfg["analysis"]["model"] or cfg["model"].get(runner), cfg["analysis"]["effort"] or cfg["effort"].get(runner)
    scored = eval_check.scoring(skill_dir)
    behaviors = {str(b.get("id")): b for b in eval_check.entries(scored["doc"], "behaviors")} if scored else {}
    workdir = Path(args.workdir).resolve() if args.workdir else Path(tempfile.gettempdir()) / "skill-foundation" / spec["name"]
    rdir = round_dir(workdir, args.round, "analysis")
    if rdir.exists():
        if not args.force:
            _lib.fail(f"{rdir} は準備済みです（作り直すなら --force）")
        shutil.rmtree(rdir)
    rdir.mkdir(parents=True)
    tester = place_tester(args.agents_dir) if runner == "subagent" else ""
    tasks: dict[str, list[str]] = {}
    for rid in sorted(traces.get("runs", {})):
        tasks.setdefault(rid.split("/", 1)[0], []).append(rid)
    runs, skipped = [], []
    for task, rids in tasks.items():
        for rid in rids:
            run = traces["runs"][rid]
            if not run.get("actions"):
                skipped.append(rid)
                continue
            agent = rid.split("/", 1)[1]
            target = rdir / task / agent
            target.mkdir(parents=True)
            others = [(r.split("/", 1)[1], traces["runs"][r]) for r in rids if r != rid]
            t = info.get(task, {})
            asks_path = results / task / f"{agent}.eval.json"
            asks = _lib.load_json(asks_path) if asks_path.is_file() else {}
            record = analysis_record(spec["name"], args.round, task, prompts.get(task, ""), procedure, steps, agent, run, others,
                                     t.get("status", {}).get(agent, ""), t.get("messages", {}).get(agent, ""), target, asks, behaviors)
            (target / ANALYSIS_IN).write_text(record, encoding="utf-8")
            mark_lab(target, rdir, rid, runner, spec.get("language"))
            register_fence(target, runner)
            runs.append({"id": rid, "task": task, "agent": agent, "runner": runner, "dir": str(target),
                         "prompt": ANALYSIS_ASK.replace("{dir}", str(target)), "hash": _lib.actions_hash(run["actions"]),
                         "ops": len(run["actions"]), "eval": sorted(asks, key=eval_check.natural)})
    plan = {"kind": "analysis", "skill": str(skill_dir), "name": spec["name"], "round": args.round, "runners": [runner],
            "runs": runs, "prepared_at": rt.now(), "settings": {"model": {runner: model}, "effort": {runner: effort}}}
    _lib.write_json(rdir / "plan.json", plan)
    print(f"準備しました: {rdir}")
    print(f"分析 {len(runs)} 件（エージェント1人の記録ごとに1件。runner {runner}、model {model or '-'}、effort {effort or '-'}）"
          + (f"。操作の記録が無いので分析しない: {', '.join(skipped)}" if skipped else ""))
    if tester:
        print(tester)
    command = "prompts" if runner == "subagent" else "run"
    print(f"次: python3 {Path(__file__).name} {command} --workdir {workdir} --round {args.round} --kind analysis"
          f" の後に analysis-collect --workdir {workdir} --round {args.round}")
    return 0


def parse_analysis(text: str) -> dict | None:
    start, end = text.find("{"), text.rfind("}")
    try:
        data = json.loads(text[start:end + 1]) if 0 <= start < end else None
    except ValueError:
        return None
    return data if isinstance(data, dict) else None


def analysis_problems(data: dict | None, ops: int, wanted: list[str] | tuple = ()) -> list[str]:
    """分析の結果が決まり（record.md の「書くもの」）に合わないところ。"""
    if data is None:
        return ["JSON として読めない"]
    def text_ok(value, limit: int, empty: bool = False) -> bool:
        return isinstance(value, str) and (empty or bool(value.strip())) and len(value) <= limit * SLACK
    problems = []
    flow = data.get("flow") if isinstance(data.get("flow"), dict) else None
    if flow is None:
        problems.append("flow がない")
    else:
        if flow.get("verdict") not in _lib.ANALYSIS_VERDICTS:
            problems.append(f"flow.verdict は {'・'.join(_lib.ANALYSIS_VERDICTS)} のどれか")
        if not text_ok(flow.get("summary"), SUMMARY_MAX):
            problems.append(f"flow.summary は {SUMMARY_MAX} 字ほどまでの文")
        for key in ("issues", "suggestions"):
            items = flow.get(key)
            if not isinstance(items, list) or len(items) > ITEMS_MAX or not all(text_ok(x, ITEM_MAX) for x in items):
                problems.append(f"flow.{key} は {ITEM_MAX} 字ほどまでの文を {ITEMS_MAX} 個までの配列")
    if not text_ok(data.get("compare", ""), SUMMARY_MAX, empty=True):
        problems.append(f"compare は {SUMMARY_MAX} 字ほどまでの文")
    if wanted:  # 頼んだ model の判定（record.md の「Eval の判定」）
        given = {str(x.get("behavior")): x for x in data.get("eval", []) if isinstance(x, dict)} if isinstance(data.get("eval"), list) else {}
        lacking = [b for b in wanted if b not in given or given[b].get("result") not in EVAL_RESULTS or not text_ok(given[b].get("reason"), ITEM_MAX)]
        if lacking:
            problems.append(f"eval に {', '.join(lacking)} の判定が無いか、決まりに合わない（result は {'・'.join(EVAL_RESULTS)}、"
                            f"reason は {ITEM_MAX} 字ほどまでの文）")
    items = data.get("ops")
    if not isinstance(items, list):
        return problems + ["ops がない"]
    numbers = [x.get("n") for x in items if isinstance(x, dict)]
    if numbers != list(range(1, ops + 1)):
        problems.append(f"ops は #1 から #{ops} までの {ops} 件を番号順に（今は {len(numbers)} 件）")
    bad = [str(x.get("n")) for x in items if isinstance(x, dict)
           and (x.get("fit") not in _lib.ANALYSIS_FITS or not text_ok(x.get("why"), WHY_MAX))]
    if bad:
        problems.append(f"fit か why が決まりに合わない操作: #{', #'.join(bad[:8])}" + (f" ほか {len(bad) - 8} 件" if len(bad) > 8 else ""))
    return problems


def finding_step(text: str, walked: list) -> int | None:
    """指摘の文が当たる手順。最初の「#番号」の操作がいた手順。番号が無ければ、文に出る「手順 N」。"""
    match = re.search(r"(?<!&)#(\d+)", text)
    if match and 1 <= int(match.group(1)) <= len(walked):
        return walked[int(match.group(1)) - 1][0]
    match = re.search(r"手順\s*(\d+)", text)
    return int(match.group(1)) if match else None


def analysis_digest(skill_dir: Path, rnd: int, traces: dict, analyses: dict) -> str:
    """ラウンドの AI の分析のまとめ（analysis.md）。指摘と直し方の案を手順ごとに集め、前のラウンドの「動きの指摘」の表を添える。"""
    import catalog
    steps = catalog.parse_steps(round_procedure(skill_dir, rnd))
    names = {s["no"]: (s["phase"] or s["title"])[:40] for s in steps}
    groups: dict = {}
    fits: dict = {}
    table = ["| エージェント | 流れの評価 | 操作 | " + " | ".join(catalog.FIT_NAMES[k][1] for k in _lib.ANALYSIS_FITS) + " |",
             "|---|---|---|" + "---|" * len(_lib.ANALYSIS_FITS)]
    for rid, data in sorted(analyses.items()):
        walked = catalog.walk([catalog.interpret(a) for a in traces.get(rid, {}).get("actions", [])], steps)
        for (no, _), op in zip(walked, data.get("ops", [])):
            fits.setdefault(no, Counter())[op.get("fit")] += 1
        count = Counter(op.get("fit") for op in data.get("ops", []))
        verdict = catalog.VERDICT_NAMES.get(data["flow"].get("verdict"), ("", "不明"))[1]
        table.append(f"| {rid} | {verdict} | {len(data.get('ops', []))} | " + " | ".join(str(count[k]) for k in _lib.ANALYSIS_FITS) + " |")
        for key in ("issues", "suggestions"):
            for item in data["flow"].get(key, []):
                group = groups.setdefault(finding_step(item, walked), {"issues": [], "suggestions": [], "who": set()})
                group[key].append(f"- {rid}: {item}")
                if key == "issues":
                    group["who"].add(rid)
    lines = [f"# ラウンド {rnd} のエージェントの動きの指摘（AI の推定）", "",
             "`convergence.py analysis-collect` が、同じ場所の analysis.json から作る。締め込み（convergence-test.md の5章）の材料である。"
             "指摘は AI の推定なので、#番号の操作を traces.json（カタログの「エージェントの動き」）で確かめてから、"
             "dev/convergence-report.md の「## 動きの指摘」の表に、分類（V1〜V8。記録と合わなければ推定違い）と対処を書く。"
             "基準を満たした課題の指摘も分類する。", "", "## 流れの評価", "", *table, "", "## 手順ごとの指摘", "",
             "指摘の最初の「#番号」の操作がいた手順（番号が無ければ、文に出る「手順 N」）でまとめ、指摘したエージェントが多い手順から並べる。"
             "操作の当てはまりは、その手順にいた操作を全エージェント分数えたもの。"]
    for no in sorted(groups, key=lambda n: (-len(groups[n]["who"]), n is None, n or 0)):
        group, tally = groups[no], fits.get(no, Counter())
        head = f"手順 {no}: {names.get(no, '')}" if no is not None else "手順の外（手順を始める前か、手順を特定できない）"
        lines += ["", f"### {head}（指摘したエージェント {len(group['who'])} 人。操作の当てはまり: "
                  + ("、".join(f"{catalog.FIT_NAMES[k][1]} {tally[k]}" for k in _lib.ANALYSIS_FITS if tally[k]) or "なし") + "）"]
        for key, label in (("issues", "問題だった点"), ("suggestions", "直し方の案")):
            if group[key]:
                lines += ["", f"{label}:", "", *group[key]]
    report = skill_dir / "dev/convergence-report.md"
    prev = _lib.finding_rows(report.read_text(encoding="utf-8"), rnd - 1) if report.is_file() and rnd > 1 else []
    lines += ["", f"## 前のラウンドの動きの指摘（dev/convergence-report.md のラウンド {rnd - 1}）", "",
              "前のラウンドで締め込んだ指摘が上に再び出ていれば、その締め込みは効いていない。締め込み方を変える。", ""]
    lines += (["| エージェントと操作 | 指摘 | 分類 | 対処 |", "|---|---|---|---|"] + ["| " + " | ".join(row[1:]) + " |" for row in prev]
              if prev else ["（表に前のラウンドの行が無い）"])
    return "\n".join(lines) + "\n"


def cmd_analysis_collect(args) -> int:
    workdir = Path(args.workdir).resolve()
    rdir = round_dir(workdir, args.round, "analysis")
    plan = _lib.load_json(rdir / "plan.json")
    out = Path(args.out).resolve() if args.out else Path(plan["skill"]) / f"dev/results/convergence/round-{plan['round']}"
    traces = _lib.load_json(out / "traces.json").get("runs", {})
    old = _lib.load_json(out / "analysis.json") if (out / "analysis.json").is_file() else {}
    kept = {rid: a for rid, a in (old.get("runs", {}) if old.get("round") == plan["round"] else {}).items()
            if rid in traces and a.get("based_on") == _lib.actions_hash(traces[rid].get("actions", []))}
    prompts = {r["prompt"].strip(): r["id"] for r in plan["runs"] if r["runner"] == "subagent"}
    since = plan_time(plan, rdir) - 60
    found = find_transcripts(prompts, Path(args.transcripts).expanduser() if args.transcripts else TRANSCRIPTS, since) if prompts else {}
    lost = {r["id"]: r["dir"] for r in plan["runs"] if r["runner"] == "subagent" and r["id"] not in found}
    codex = find_codex_rollouts(lost, Path(args.codex_sessions).expanduser() if args.codex_sessions else CODEX_SESSIONS,
                                since) if lost else {}
    lines, bad = [], []
    for run in plan["runs"]:
        if _lib.actions_hash(traces.get(run["id"], {}).get("actions", [])) != run["hash"]:
            bad.append(f"{run['id']}: 記録（traces.json）が analysis-prepare の後に変わった。analysis-prepare --force からやり直す")
            continue
        path = Path(run["dir"]) / ANALYSIS_OUT
        if not path.is_file():
            bad.append(f"{run['id']}: {path} がない")
            continue
        data = parse_analysis(path.read_text(encoding="utf-8", errors="replace"))
        problems = analysis_problems(data, run["ops"], run.get("eval", []))
        if problems:
            bad.append(f"{run['id']}: " + "／".join(problems))
            continue
        result = rdir / "_results" / f"{safe(run['id'])}.json"
        try:  # runner claude・codex のモデルは、run が実行の結果に書く
            model = {k: v for k, v in _lib.load_json(result).items() if k in ("model", "effort", "settings")} if result.is_file() else {}
        except (OSError, ValueError, AttributeError):
            model = {}
        if run["id"] in found:
            model = transcript_model(found[run["id"]])
        elif run["id"] in codex:  # Codex のサブエージェントの分析役は、trace と同じく作業ディレクトリで記録を突き合わせる
            model = rollout_model(codex[run["id"]][0])
        flow = data["flow"]
        kept[run["id"]] = {"based_on": run["hash"], "runner": run["runner"], **model,
                           "flow": {"verdict": flow["verdict"], "summary": flow["summary"].strip(),
                                    "issues": [x.strip() for x in flow["issues"]], "suggestions": [x.strip() for x in flow["suggestions"]]},
                           "compare": str(data.get("compare", "")).strip(),
                           "ops": [{"fit": x["fit"], "why": x["why"].strip()} for x in data["ops"]],
                           "eval": [{"behavior": str(x["behavior"]), "result": x["result"], "reason": str(x["reason"]).strip()}
                                    for x in data.get("eval", []) if isinstance(x, dict) and str(x.get("behavior")) in run.get("eval", [])]}
        fits = Counter(x["fit"] for x in data["ops"])
        lines.append(f"- {run['id']}: {flow['verdict']}（" + "、".join(f"{k} {fits[k]}" for k in _lib.ANALYSIS_FITS if fits[k]) + "）")
    _lib.write_json(out / "analysis.json", {"round": plan["round"], "runs": dict(sorted(kept.items()))})
    report = merge_eval(out, kept)
    (out / "analysis.md").write_text(analysis_digest(Path(plan["skill"]), plan["round"], traces, kept) + eval_digest(report),
                                     encoding="utf-8")
    print("\n".join(lines))
    if (report.get("eval") or {}).get("hash"):
        counts = Counter(s.get("result") for t in report.get("tasks", []) for scores in (t.get("eval") or {}).values() for s in scores.values())
        print(f"Eval の採点: 通過 {counts['pass']}、落ちた {counts['fail']}、判定するファイルが無い {counts['na']}、"
              f"model の判定待ち {counts['pending']}（report.json の基準を決め直した）")
    print(f"分析: {out / 'analysis.json'}（{len(kept)} 件）")
    print(f"まとめ: {out / 'analysis.md'}（指摘を手順ごとに集めたもの。締め込みで読む。convergence-test.md の5章）")
    if bad:
        print("\n決まりに合わない、またはまだ無い分析（その分析役だけやり直す: prompts か run に --kind analysis --only <ID> を付ける）:")
        print("\n".join(f"- {b}" for b in bad))
        return 1
    return 0


def merge_eval(out: Path, analyses: dict) -> dict:
    """分析役の model の判定を report.json の採点に入れ、課題の基準（ばらつき かつ Eval）を決め直す。
    判定は今の分析だけから取る（記録を取り直して捨てた分析の判定は、判定待ちに戻す）。"""
    path = out / "report.json"
    if not path.is_file():
        return {}
    report = _lib.load_json(path)
    if not (report.get("eval") or {}).get("hash"):  # Eval で採点していないラウンドの記録は変えない
        return report
    for t in report.get("tasks", []):
        grades = t.get("eval") or {}
        for agent, scores in grades.items():
            judged = {x["behavior"]: x for x in analyses.get(f"{t['id']}/{agent}", {}).get("eval", [])}
            for bid, score in scores.items():
                if score.get("result") == "pending" or score.get("by") == "analysis":
                    hit = judged.get(bid)
                    score.update(result=hit["result"], detail=hit["reason"], by="analysis") if hit else \
                        score.update(result="pending", detail="", by="")
        if grades:
            t["eval_ok"] = eval_check.task_ok(grades)
            t["converged"] = bool(t.get("variance_ok", t.get("converged"))) and t["eval_ok"] is True
    _lib.write_json(path, report)
    (out / "report.md").write_text(render_report(report), encoding="utf-8")
    return report


def eval_digest(report: dict) -> str:
    """analysis.md に足す、Eval に落ちた判定の一覧。締め込みで分類し、convergence-report.md の「## Eval の採点」に書く。"""
    if not (report.get("eval") or {}).get("hash"):
        return ""
    lines = ["", f"## Eval に落ちた判定（ラウンド {report.get('round')}）", "",
             "落ちた判定ごとに、出力の誤り（スキルを直す）か Eval の疑い（判定がずれている）かを確かめ、dev/convergence-report.md の"
             "「## Eval の採点」の表に分類と対処を書く。上の動きの指摘のうち、Eval で確かめていない問題は Eval の抜けとして同じ表に書く。"
             "疑いか抜けがあれば、ユーザーとすり合わせて Eval を直してから次のラウンドに進む（references/eval.md の7章）。", ""]
    fails = [f"- {t['id']}/{agent} {bid}（{s.get('type')}）: {s.get('detail') or '理由の記録なし'}"
             for t in report.get("tasks", []) for agent, scores in (t.get("eval") or {}).items()
             for bid, s in scores.items() if s.get("result") == "fail"]
    return "\n".join(lines + (fails or ["（落ちた判定は無い）"])) + "\n"


def eval_cell(task: dict) -> str:
    counts = Counter(s.get("result") for scores in (task.get("eval") or {}).values() for s in scores.values())
    if not counts:
        return "—"
    return f"落ちた {counts['fail']}" if counts["fail"] else (f"判定待ち {counts['pending']}" if counts["pending"] else "通過")


def fmt(value) -> str:
    return "—" if value is None else f"{value:.3f}"


def summary(report: dict) -> str:
    lines = ["| 課題 | status | files | structure | names | content | check | runner 別 files | Eval | 基準 |", "|---|---|---|---|---|---|---|---|---|---|"]
    for t in report["tasks"]:
        status = "、".join(sorted(set(t["status"].values())))
        check = "—" if not t["check"] else ("全員通過" if all(v == 0 for v in t["check"].values()) else "失敗あり")
        runner = "、".join(f"{k} {fmt(v['files'])}" for k, v in t["by_runner"].items()) or "—"
        lines.append(f"| {t['id']} | {status} | {fmt(t['files'])} | {fmt(t['structure'])} | {fmt(t.get('names'))} | {fmt(t['content'])} | "
                     f"{check} | {runner} | {eval_cell(t)} | {'満たす' if t['converged'] else '満たさない'} |")
    return "\n".join(lines)


def render_report(report: dict) -> str:
    th = report["thresholds"]
    lines = [f"# 収束テスト ラウンド {report['round']}", "",
             "convergence.py diff が生成する。ばらつきの分類（V1〜V8）と対処は dev/convergence-report.md に書く。", "",
             f"基準: status が全員、課題の expect_status（既定 done）と同じ。check が全員通過。独立エージェントの作業ディレクトリ制限"
             f"（fence.py）の登録が維持されている。files ≥ {th['files']}、structure ≥ {th['structure']}、names ≥ {th.get('names', 0.8)}"
             + ("。Eval の採点で落ちた出力が無く、model の判定待ちが無い（STEP-07）" if (report.get("eval") or {}).get("hash") else ""), "",
             "## 指標", "", summary(report)]
    if "subagent" in report.get("runners", []):
        lines[6:6] = ["runner subagent は Agent ツールで実行した。一時プロジェクトの hooks は働かず、run.py の check と finish だけで"
                      "検査された。自動の起動は、スキルの説明文を前置きで渡した近似である（convergence-test.md の3章）。", ""]
    if report.get("fence"):
        lines[6:6] = ["作業ディレクトリの外への操作は、fence.py で止めた。止めた操作は traces.json に印がある"
                      "（convergence-test.md の3章）。", ""]
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
        if t.get("fence_changed"):
            lines += ["", "### 作業ディレクトリの制限を外したエージェント（失格）", ""]
            lines += [f"- {n}: {'、'.join(paths)}" for n, paths in t["fence_changed"].items()]
        if t.get("eval"):
            names = {"pass": "通過", "fail": "落ちた", "na": "判定するファイルが無い", "pending": "model の判定待ち", "human": "人が確かめる"}
            lines += ["", "### Eval の採点", ""]
            for n, scores in t["eval"].items():
                lines.append(f"- {n}: " + "、".join(f"{bid} {names.get(sc.get('result'), sc.get('result'))}"
                                                     + (f"（{sc['detail']}）" if sc.get("result") == "fail" and sc.get("detail") else "")
                                                     for bid, sc in scores.items()))
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
    p.add_argument("--runners", help="カンマ区切り（claude、codex、subagent。既定 settings の convergence.runners）")
    p.add_argument("--model", action="append", metavar="[RUNNER=]MODEL", help="エージェントのモデル（既定 settings の convergence.model）")
    p.add_argument("--effort", action="append", metavar="[RUNNER=]EFFORT", help="推論エフォート（既定 settings の convergence.effort）")
    p.add_argument("--include-holdout", action="store_true")
    p.add_argument("--only-tasks")
    p.add_argument("--workdir")
    p.add_argument("--force", action="store_true")
    p.add_argument("--agents-dir", help=f"runner subagent の専用のエージェント型（{TESTER}.md）の置き場（既定 このスキルの置き場の .claude/agents）")
    p.set_defaults(func=cmd_prepare)
    p = sub.add_parser("review-prepare")
    p.add_argument("skill")
    p.add_argument("--round", type=int, required=True)
    p.add_argument("--agents", type=int)
    p.add_argument("--runners", help="カンマ区切り（claude、codex、subagent）")
    p.add_argument("--model", action="append", metavar="[RUNNER=]MODEL", help="エージェントのモデル（既定 settings の convergence.model）")
    p.add_argument("--effort", action="append", metavar="[RUNNER=]EFFORT", help="推論エフォート（既定 settings の convergence.effort）")
    p.add_argument("--workdir")
    p.add_argument("--force", action="store_true")
    p.add_argument("--agents-dir", help=f"runner subagent の専用のエージェント型（{TESTER}.md）の置き場（既定 このスキルの置き場の .claude/agents）")
    p.set_defaults(func=cmd_review_prepare)
    p = sub.add_parser("review-score")
    p.add_argument("--workdir", required=True)
    p.add_argument("--round", type=int, required=True)
    p.add_argument("--out")
    p.set_defaults(func=cmd_review_score)
    p = sub.add_parser("prompts")
    p.add_argument("--workdir", required=True)
    p.add_argument("--round", type=int, required=True)
    p.add_argument("--kind", choices=["task", "review", "analysis"], default="task")
    p.add_argument("--only", help="カンマ区切りの実行ID")
    p.set_defaults(func=cmd_prompts)
    p = sub.add_parser("run")
    p.add_argument("--workdir", required=True)
    p.add_argument("--round", type=int, required=True)
    p.add_argument("--kind", choices=["task", "review", "analysis"], default="task")
    p.add_argument("--parallel", type=int, help="同時に動かす数（既定 settings の convergence.parallel）")
    p.add_argument("--timeout", type=int, help="1件の上限の秒数（既定 settings の convergence.timeout）")
    p.add_argument("--only", help="カンマ区切りの実行ID")
    p.set_defaults(func=cmd_run)
    p = sub.add_parser("diff")
    p.add_argument("--workdir", required=True)
    p.add_argument("--round", type=int, required=True)
    p.add_argument("--out")
    p.set_defaults(func=cmd_diff)
    p = sub.add_parser("trace")
    p.add_argument("--workdir", required=True)
    p.add_argument("--round", type=int, required=True)
    p.add_argument("--out")
    p.add_argument("--transcripts", help="Agent ツールの記録を探す場所（既定 ~/.claude/projects）")
    p.add_argument("--codex-sessions", help="Codex のセッションの記録を探す場所（既定 ~/.codex/sessions）")
    p.set_defaults(func=cmd_trace)
    p = sub.add_parser("analysis-prepare")
    p.add_argument("skill")
    p.add_argument("--round", type=int, required=True)
    p.add_argument("--runner", choices=RUNNERS, help="分析役の runner（既定 settings の convergence.analysis.runner、無ければ runners の先頭）")
    p.add_argument("--model", help="分析役のモデル（既定 settings の convergence.analysis.model、無ければ その runner の model）")
    p.add_argument("--effort", help="分析役の推論エフォート（既定 settings の convergence.analysis.effort、無ければ その runner の effort）")
    p.add_argument("--workdir")
    p.add_argument("--force", action="store_true")
    p.add_argument("--agents-dir", help=f"runner subagent の専用のエージェント型（{TESTER}.md）の置き場（既定 このスキルの置き場の .claude/agents）")
    p.set_defaults(func=cmd_analysis_prepare)
    p = sub.add_parser("analysis-collect")
    p.add_argument("--workdir", required=True)
    p.add_argument("--round", type=int, required=True)
    p.add_argument("--out")
    p.add_argument("--transcripts", help="Agent ツールの記録を探す場所（既定 ~/.claude/projects）")
    p.add_argument("--codex-sessions", help="Codex のセッションの記録を探す場所（既定 ~/.codex/sessions）")
    p.set_defaults(func=cmd_analysis_collect)
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
