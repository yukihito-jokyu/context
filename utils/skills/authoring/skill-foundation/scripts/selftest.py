#!/usr/bin/env python3
"""自己テスト: 見本（assets/example/<名前>/）から一時プロジェクトにスキルを組み立て、作成用スクリプトが通しで動くことを確かめる。

  1. 見本の spec・probes・evals・research・fixtures・固有スクリプト・出力の見本を、一時プロジェクトのスキルの dev/、
     scripts/、assets/examples/ に置く
  2. init_skill.py で骨組みを作り、見本の procedure.md を SKILL.md の「2. 手順」に入れる
  3. render_skill.py --check、skill_lint.py --phase 5、probe.py を実行する
  4. 収束テストの記録の見本（report.json と traces.json）を置いて catalog.py でカタログを書き、一覧からスキルの
     ページへのリンクがあり、ページにスキルの欄、ワークフロー図、エージェントの動きの図があり、図（SVG）が XML として
     読めることを確かめる。catalog.py の「見せ方の約束」（BANNED_WORDS の語を見せない、ページ内のリンクの飛び先が
     ある、「先に見るもの」が操作の行へ飛ぶ、系列を浮かび上がらせる凡例、モデルと推論エフォート）も確かめる。
     カタログに載る skill-foundation の文書と、新しいスキルに写るひな形に DOC_WORDS の語が無いことも確かめる
  5. convergence.py prepare で、全課題の fixture と setup が動くことを確かめる（エージェントは起動しない）。spec に
     convergence.skip_reason があると、prepare が一時プロジェクトを作らずに止まることも確かめる
  6. fence.py（作業ディレクトリの外への操作を止める仕組み）が、5 で作った一時プロジェクトで止める操作を止め、通す操作を通すことを確かめる
  7. 5 の plan に、Codex のサブエージェントの記録と codex exec --json の出力の見本を置き、convergence.py trace が
     それを操作の列（出力の抜粋つき）にすることを確かめる。Agent ツールの記録の、API に送った会話の写しを二重に数えないことと、
     エージェントが読んだ SKILL.md の写し（used-SKILL.md）を残すことも確かめる
  8. install.py で .agents/skills にリンクを置いた後、それを複製に変え、install.py --check と skill_lint.py が置き違いを
     見つけ、catalog.py が同じ名前のスキルを要確認に出すことを確かめる
  9. 4 の記録の見本で convergence.py analysis-prepare を実行し、分析役の結果の見本（決まりどおりのものと、操作が
     1件足りないもの）を置いて、analysis-collect が前者だけを取り込むこと、カタログが流れの評価・操作ごとの理由・
     「#番号」の行へのリンクを出すこと、記録を取り直した後の分析を出さず、skill_lint.py --final が作り直しを求めることを確かめる。
     分析を締め込みに使う仕組み（analysis-collect が指摘を手順ごとに集めた analysis.md を書くこと、convergence-report.md の
     「## 動きの指摘」の表に指摘のあるエージェントが無いか、分類が決まりに無いと、次のラウンドの prepare と
     skill_lint.py --final が止めること）も確かめる。
     Codex で分析したとき（サブエージェントの分析役のモデルを Codex の記録から読むこと、偽の codex で run --kind analysis
     を動かして分析を集めること）も確かめる

skill-foundation のスクリプトやひな形を変えたら、これを実行してから使う。

--build <ディレクトリ> を付けると、検証せずに見本をそのディレクトリ（プロジェクト）に組み立てるだけにする。
さらに --ready を付けると、probe を実行して status を ready にし、収束テストを省いた形（skill_lint.py --final が
通る形）に仕上げる。skill-foundation 自身の probe（dev/probes.json の baseline.setup）が使う。

使い方:
  python3 selftest.py [--example write-commit-message] [--keep]
  python3 selftest.py --build <プロジェクト> [--ready]
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _lib  # noqa: E402

EXAMPLES = _lib.FOUNDATION_DIR / "assets" / "example"
SCRIPTS = _lib.FOUNDATION_DIR / "scripts"
DEV_FILES = ["spec.json", "probes.json", "evals.json", "research.md"]
# カタログに見せない、作る側の呼び名と、意味のすぐ通らない語（catalog.py の「見せ方の約束」1）。言い換えは catalog.py の TERMS
BANNED_WORDS = ["封印", "答えの決め方", "観測", "書き直す", "関門", "柵", "配線", "揺れ", "担保", "所要"]
# 文書でも使わない語。目的語のある「ルールの文を書き直す」などは普通の言い方なので、文書では止めない
DOC_WORDS = [w for w in BANNED_WORDS if w not in ("書き直す", "担保", "所要")]
DOC_GLOBS = ["SKILL.md", "references/*.md", "dev/*.json", "dev/convergence-report.md", "assets/templates/*", "assets/contract.json"]
PROCEDURE = re.compile(r"(^## (?:2\. 手順|2\. Procedure)\n.*?\n)(1\. .*?)(?=\n\n## )", re.S | re.M)


def build(example: Path, project: Path) -> Path:
    spec = _lib.load_json(example / "spec.json")
    place = ".claude/skills" if spec["targets"][0] == "claude" else ".agents/skills"
    skill = project / place / spec["name"]
    (skill / "dev").mkdir(parents=True)
    for name in DEV_FILES:
        shutil.copy2(example / name, skill / "dev" / name)
    if (example / "fixtures").is_dir():
        _lib.copy_tree(example / "fixtures", skill / "dev" / "fixtures")
    if (example / "scripts").is_dir():
        _lib.copy_tree(example / "scripts", skill / "scripts")
    if (example / "examples").is_dir():
        _lib.copy_tree(example / "examples", skill / _lib.EXAMPLES_DIR)
    return skill


READY_REPORT = """# {name} 収束テストの記録

skill-foundation の自己テストのために見本から組み立てたスキルなので、収束テストを省いた（dev/spec.json の
convergence.skip_reason）。

## 結論

収束テストは実施していない。
"""


def assemble(example: Path, project: Path) -> Path | None:
    """見本を組み立て、SKILL.md の「2. 手順」を入れる。失敗したら None。"""
    skill = build(example, project)
    if not step("init_skill.py", [sys.executable, str(SCRIPTS / "init_skill.py"), "--dir", str(skill)], project):
        return None
    text = (skill / "SKILL.md").read_text(encoding="utf-8")
    procedure = (example / "procedure.md").read_text(encoding="utf-8").strip()
    replaced, count = PROCEDURE.subn(lambda m: m.group(1) + procedure, text)
    print(f"{'成功' if count == 1 else '失敗'}  SKILL.md の「2. 手順」に procedure.md を入れる")
    (skill / "SKILL.md").write_text(replaced, encoding="utf-8")
    return skill if count == 1 else None


def make_ready(skill: Path) -> bool:
    spec = _lib.load_spec(skill)
    spec["status"] = "ready"
    spec.setdefault("convergence", {})["skip_reason"] = "skill-foundation の自己テスト用に見本から組み立てたため"
    _lib.write_json(skill / _lib.SPEC_REL, spec)
    (skill / "dev/convergence-report.md").write_text(READY_REPORT.replace("{name}", spec["name"]), encoding="utf-8")
    return (step("render_skill.py", [sys.executable, str(SCRIPTS / "render_skill.py"), "--dir", str(skill)], skill)
            and step("probe.py", [sys.executable, str(SCRIPTS / "probe.py"), str(skill)], skill))


def step(title: str, command: list[str], cwd: Path, timeout: int = 900) -> bool:
    code, out = _lib.run(command, cwd, timeout=timeout)
    print(f"{'成功' if code == 0 else '失敗'}  {title}（終了コード {code}）")
    print("    " + _lib.tail(out, 3 if code == 0 else 25).replace("\n", "\n    "))
    return code == 0


def sample_round(skill: Path) -> None:
    """カタログの動きの図を通すための、収束テストの記録の見本（エージェント2人、操作は一部だけ）。"""
    name = skill.name
    out = f".skill-runs/{name}/out/commit-message.txt"
    rdir = skill / "dev/results/convergence/round-1"
    _lib.write_json(rdir / "report.json", {"round": 1, "runners": ["subagent"], "thresholds": {}, "tasks": [
        {"id": "T1-typical", "agents": ["subagent-1", "subagent-2"], "status": {"subagent-1": "done", "subagent-2": "done"},
         "files": 1.0, "structure": 1.0, "names": 1.0, "content": 0.9, "converged": True,
         "changed_files": {"subagent-1": [out], "subagent-2": [out]}, "partial_files": [], "messages": {}}]})
    def actions(fail: bool) -> list[dict]:
        return [{"at": "2026-01-01T00:00:00Z", "tool": "Read", "input": f".claude/skills/{name}/SKILL.md", "ok": True},
                {"at": "2026-01-01T00:01:00Z", "tool": "Bash", "input": f"python3 .claude/skills/{name}/scripts/run.py start", "ok": True},
                {"at": "2026-01-01T00:03:00Z", "tool": "Write", "input": out, "ok": True},
                {"at": "2026-01-01T00:04:00Z", "tool": "Bash", "input": f"python3 .claude/skills/{name}/scripts/run.py check", "ok": not fail},
                {"at": "2026-01-01T00:05:00Z", "tool": "Bash", "input": "ls /tmp/elsewhere", "ok": True},
                {"at": "2026-01-01T00:05:30Z", "tool": "Bash", "input": "mkdir -p /tmp/fenced", "ok": False, "fenced": True},
                {"at": "2026-01-01T00:06:00Z", "tool": "Bash", "input": f"python3 .claude/skills/{name}/scripts/run.py finish", "ok": True}]
    events = [{"at": "2026-01-01T09:01:00+09:00", "event": e, "detail": ""} for e in ("start", "check", "finish")]
    models = {1: {"model": "claude-opus-5-5", "effort": "xhigh"}, 2: {"model": "gpt-6-luna", "effort": "high", "settings": True}}
    _lib.write_json(rdir / "traces.json", {"round": 1, "runs": {
        f"T1-typical/subagent-{i}": {"runner": "subagent", "source": "自己テストの見本", "events": events, "actions": actions(i == 2),
                                     **models[i]} for i in (1, 2)}})


def literal_words(path: Path) -> list[str]:
    """ファイルの文字列（説明文は除く。コメントは ast に残らない）に出る BANNED_WORDS の語と行。"""
    import ast
    tree = ast.parse(path.read_text(encoding="utf-8"))
    docs = {id(n.body[0].value) for n in ast.walk(tree) if isinstance(n, (ast.Module, ast.FunctionDef, ast.ClassDef))
            and n.body and isinstance(n.body[0], ast.Expr) and isinstance(n.body[0].value, ast.Constant)}
    return [f"{word}（{path.name} {node.lineno} 行目）" for node in ast.walk(tree)
            if isinstance(node, ast.Constant) and isinstance(node.value, str) and id(node) not in docs
            for word in BANNED_WORDS if word in node.value]


def doc_words() -> list[str]:
    """カタログに載る skill-foundation の文書と、新しいスキルに写るひな形に出る DOC_WORDS の語と行。"""
    found = []
    for pattern in DOC_GLOBS:
        for path in sorted(_lib.FOUNDATION_DIR.glob(pattern)):
            for no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
                found += [f"{w}（{path.relative_to(_lib.FOUNDATION_DIR)} {no} 行目）" for w in DOC_WORDS if w in line]
    return found


def view_problems(text: str) -> list[str]:
    """catalog.py の「見せ方の約束」の 3〜5 が、書いたページに出ているか。"""
    ids = set(re.findall(r'\bid="([^"]+)"', text))
    problems = [f"ページ内のリンク #{h} の飛び先が無い" for h in dict.fromkeys(re.findall(r'href="#([^"]*)"', text)) if h not in ids]
    attn = re.search(r'<section class="attn".*?</section>', text, re.S)
    if not attn or not re.search(r'href="#[^"]*-op-[^"]*-\d+"', attn.group(0)):
        problems.append("「先に見るもの」に、操作の行へ飛ぶリンクが無い")
    if text.count("data-focus-scope") < 2 or 'data-focus="s2"' not in text:
        problems.append("系列を浮かび上がらせる凡例（data-focus）が、収束テストとエージェントの動きに無い")
    for want in ('<td class="mdl"><code>claude-opus-5-5</code><span class="eff">xhigh</span>', "（設定から）"):
        if want not in text:
            problems.append(f"エージェントのモデルと推論エフォートが出ていない（{want}）")
    return problems


def check_catalog(skill: Path, project: Path, out: Path) -> bool:
    sample_round(skill)
    if not step("catalog.py", [sys.executable, str(SCRIPTS / "catalog.py"), "--project", str(project), "--out", str(out)], project):
        return False
    page = out.with_suffix("") / f"{skill.name}.html"
    problems = [] if f'href="{out.stem}/{skill.name}.html"' in out.read_text(encoding="utf-8") else [f"一覧に {page.name} へのリンクが無い"]
    text = page.read_text(encoding="utf-8") if page.is_file() else ""
    svgs = re.findall(r"<svg\b.*?</svg>", text, re.S)
    if f'id="skill-{skill.name}"' not in text:
        problems.append(f"{page.name} に skill-{skill.name} の欄が無い")
    if not any('class="wf"' in svg for svg in svgs):
        problems.append("ワークフロー図が無い")
    if not any('class="mv"' in svg for svg in svgs):
        problems.append("エージェントの動きの図が無い")
    if "外への操作を止めた記録" not in text:
        problems.append("fence.py が止めた操作のカードが無い")
    problems += view_problems(text) + [f"見せない語が catalog.py の文字列にある: {w}" for w in literal_words(SCRIPTS / "catalog.py")]
    problems += [f"見せない語が skill-foundation の文書にある: {w}" for w in doc_words()]
    for i, svg in enumerate(svgs, 1):
        try:
            ET.fromstring(svg)
        except ET.ParseError as exc:
            problems.append(f"図 {i} が XML として読めない: {exc}")
    print(f"{'成功' if not problems else '失敗'}  カタログの図（SVG {len(svgs)} 個）")
    for problem in problems:
        print(f"    {problem}")
    return not problems



def check_analysis(skill: Path, project: Path, temp: Path) -> bool:
    """エージェントの動きの AI の分析（convergence.py analysis-prepare・analysis-collect と、カタログ・skill_lint.py）。"""
    py, conv, work = sys.executable, str(SCRIPTS / "convergence.py"), temp / "analysis"
    if not step("convergence.py analysis-prepare", [py, conv, "analysis-prepare", str(skill), "--round", "1", "--runner", "subagent",
                                                    "--workdir", str(work), "--agents-dir", str(temp / "agents")], temp):
        return False
    plan, problems = _lib.load_json(work / "analysis-1/plan.json"), []
    for run in plan["runs"]:
        record = Path(run["dir"]) / "record.md"
        text = record.read_text(encoding="utf-8") if record.is_file() else ""
        if f"### 操作（{run['ops']} 件）" not in text or "## 手順（SKILL.md の「2.」の節）" not in text:
            problems.append(f"{run['id']} の record.md に操作か手順が無い")
        ops = [{"n": n, "fit": "ok" if n != 5 else "detour", "why": f"#{n} の理由の見本"} for n in range(1, run["ops"] + 1)]
        bad = run["id"].endswith("-2")
        _lib.write_json(Path(run["dir"]) / "analysis.json", {"ops": ops[:-1] if bad else ops, "compare": "",
                        "flow": {"verdict": "poor", "summary": "#2 で始めて #4 で失敗した見本", "issues": ["#4 の失敗"], "suggestions": []}})
    collect = [py, conv, "analysis-collect", "--workdir", str(work), "--round", "1"]
    code, out = _lib.run(collect, temp)
    saved = _lib.load_json(skill / "dev/results/convergence/round-1/analysis.json").get("runs", {})
    if code != 1 or "T1-typical/subagent-2" not in out or sorted(saved) != ["T1-typical/subagent-1"]:
        problems.append(f"analysis-collect が、決まりに合わない分析をはじいて、合うものだけを残していない（終了コード {code}）")
    run2 = next(r for r in plan["runs"] if r["id"].endswith("-2"))
    _lib.write_json(Path(run2["dir"]) / "analysis.json", {"ops": [{"n": n, "fit": "ok", "why": "見本"} for n in range(1, run2["ops"] + 1)],
                    "compare": "", "flow": {"verdict": "good", "summary": "見本", "issues": [], "suggestions": []}})
    if _lib.run(collect, temp)[0] != 0:
        problems.append("analysis-collect が、決まりどおりの分析を受け入れない")
    page = temp / "analysis.html"
    if not step("catalog.py（AI の分析つき）", [py, str(SCRIPTS / "catalog.py"), "--project", str(project), "--out", str(page)], project):
        return False
    text = (page.with_suffix("") / f"{skill.name}.html").read_text(encoding="utf-8")
    prefix = f"{skill.name}-op-1-T1-typical-subagent-1"
    for want, what in (('class="fl-ai" id="' + prefix + '-ai"', "流れの評価の欄"), ("見直しが要る", "流れの評価の札"),
                       (f'href="#{prefix}-2"', "AI の文の「#番号」の行へのリンク"), ("</a> の理由の見本", "操作ごとの理由"),
                       ('class="fl-mech"', "手順との照合の欄"), ("流れに見直しが要る", "「先に見るもの」の見直しの項目")):
        if want not in text:
            problems.append(f"カタログに{what}が無い")
    problems += findings_problems(skill, temp)
    problems += codex_analysis_problems(skill, temp, work)
    traces_path = skill / "dev/results/convergence/round-1/traces.json"
    traces = _lib.load_json(traces_path)
    traces["runs"]["T1-typical/subagent-1"]["actions"][0]["input"] += " "  # 記録を取り直して操作が変わった形
    _lib.write_json(traces_path, traces)
    _lib.run([py, str(SCRIPTS / "catalog.py"), "--project", str(project), "--out", str(page)], project)
    text = (page.with_suffix("") / f"{skill.name}.html").read_text(encoding="utf-8")
    if f'id="{prefix}-ai"' in text or "取り直された後の分析ではない" not in text:
        problems.append("記録を取り直した後の分析を、カタログが出している")
    if "AI の分析が無いか、記録（traces.json）を取り直す前の分析です" not in _lib.run([py, str(SCRIPTS / "skill_lint.py"), str(skill), "--final"], temp)[1]:
        problems.append("skill_lint.py --final が、記録を取り直す前の分析の作り直しを求めない")
    print(f"{'成功' if not problems else '失敗'}  エージェントの動きの AI の分析（準備・取り込み・カタログ・締め込みの記録・検査・Codex）")
    for problem in problems:
        print(f"    {problem}")
    return not problems


FINDINGS_ROW = "| 1 | T1-typical/subagent-1 #4 | 検査に落ちた | {cls} | 見本の対処 |\n"  # 「## 動きの指摘」の表の行の見本


def findings_problems(skill: Path, temp: Path) -> list[str]:
    """分析を締め込みに使う仕組み: analysis-collect が指摘を手順ごとに集めた analysis.md を書き、次のラウンドの prepare と
    skill_lint.py --final が、指摘のあるエージェントの載った「## 動きの指摘」の表（分類と対処が埋まったもの）を求めるか。"""
    py, problems = sys.executable, []
    digest = skill / "dev/results/convergence/round-1/analysis.md"
    text = digest.read_text(encoding="utf-8") if digest.is_file() else ""
    if not re.search(r"^### 手順 \d+: [^\n]*\n\n問題だった点:\n\n- T1-typical/subagent-1: #4 の失敗$", text, re.M):
        problems.append("analysis-collect が、指摘を手順ごとに集めたまとめ（analysis.md）を書かない")
    report = skill / "dev/convergence-report.md"
    original = report.read_text(encoding="utf-8")
    prepare = [py, str(SCRIPTS / "convergence.py"), "prepare", str(skill), "--round", "2", "--only-tasks", "T1-typical",
               "--agents", "1", "--runners", "claude", "--workdir", str(temp / "conv-2"), "--force"]
    lint = [py, str(SCRIPTS / "skill_lint.py"), str(skill), "--final"]
    cases = [("", "「動きの指摘」の表のどの行にも無い", "指摘のあるエージェントが表に無い"),
             ("V9", "分類（V1〜V8 か推定違い）か対処が埋まっていません", "表の分類が決まりに無い"),
             ("V3", "", "表が揃った")]
    try:
        for cls, message, what in cases:
            if cls:
                report.write_text(re.sub(r"(^## 動きの指摘\n.*?^\|---\|---\|---\|---\|---\|\n)", lambda m: m.group(1)
                                         + FINDINGS_ROW.replace("{cls}", cls), original, count=1, flags=re.M | re.S), encoding="utf-8")
            code, out = _lib.run(prepare, temp)
            linted = _lib.run(lint, temp)[1]
            if message and (code == 0 or message not in out or message not in linted):
                problems.append(f"{what}のに、次のラウンドの prepare（終了コード {code}）か skill_lint.py --final が止めない")
            if not message and (code != 0 or "動きの指摘" in linted):
                problems.append(f"{what}のに、次のラウンドの prepare（終了コード {code}）か skill_lint.py --final が止める")
    finally:
        report.write_text(original, encoding="utf-8")
    return problems


FAKE_CODEX = '''import json, sys
from pathlib import Path
args = sys.argv[1:]
where, prompt = Path(args[args.index("-C") + 1]), args[-1]
run = next(r for r in json.loads((where.parent.parent / "plan.json").read_text(encoding="utf-8"))["runs"] if r["dir"] == str(where))
if f"{where}/record.md" not in prompt or f"{where}/analysis.json" not in prompt:
    sys.exit(3)
ops = [{"n": n, "fit": "ok", "why": "Codex の分析役の見本"} for n in range(1, run["ops"] + 1)]
(where / "analysis.json").write_text(json.dumps({"ops": ops, "compare": "", "flow": {"verdict": "good", "summary": "見本",
                                     "issues": [], "suggestions": []}}, ensure_ascii=False), encoding="utf-8")
Path(args[args.index("-o") + 1]).write_text("書きました", encoding="utf-8")
print(json.dumps({"type": "thread.started"}))
'''  # codex exec の代わり。プロンプトに record.md と analysis.json の場所があれば、決まりどおりの分析を書く


def codex_analysis_problems(skill: Path, temp: Path, work: Path) -> list[str]:
    """Codex で分析したとき: サブエージェントの分析役のモデルを Codex の記録から読み、run --kind analysis（runner codex）で集める。"""
    py, conv, problems = sys.executable, str(SCRIPTS / "convergence.py"), []
    analysis = skill / "dev/results/convergence/round-1/analysis.json"
    run1 = next(r for r in _lib.load_json(work / "analysis-1/plan.json")["runs"] if r["id"].endswith("-1"))

    def item(data):
        return {"type": "event_msg", "payload": {"type": "item_completed", "started_at_ms": 1767225600000, "item": data}}

    rollout = [{"type": "session_meta", "payload": {"thread_source": "subagent"}},
               {"type": "turn_context", "payload": {"model": "gpt-6-luna", "effort": "high"}},
               item({"type": "CommandExecution", "command": ["/bin/zsh", "-lc", f"cat {run1['dir']}/record.md"], "exit_code": 0}),
               item({"type": "FileChange", "changes": {f"{run1['dir']}/analysis.json": {"type": "add"}}, "status": "completed"})]
    sessions = temp / "analysis-codex-sessions"
    (sessions / "2026/01/01").mkdir(parents=True)
    (sessions / "2026/01/01/rollout-analyst.jsonl").write_text("".join(json.dumps(e) + "\n" for e in rollout), encoding="utf-8")
    _lib.run([py, conv, "analysis-collect", "--workdir", str(work), "--round", "1", "--transcripts", str(temp / "no-transcripts"),
              "--codex-sessions", str(sessions)], temp)
    got = {k: _lib.load_json(analysis)["runs"].get(run1["id"], {}).get(k) for k in ("model", "effort")}
    if got != {"model": "gpt-6-luna", "effort": "high"}:
        problems.append(f"analysis-collect が、Codex のサブエージェントの分析役のモデルを Codex の記録から読まない: {got}")
    (temp / "fake-codex.py").write_text(FAKE_CODEX, encoding="utf-8")
    spec_path = skill / _lib.SPEC_REL
    original = spec_path.read_text(encoding="utf-8")
    spec = json.loads(original)
    spec.setdefault("convergence", {}).setdefault("runner_commands", {})["codex"] = [
        py, str(temp / "fake-codex.py"), "exec", "--json", "-m", "gpt-x", "-c", "model_reasoning_effort=low",
        "-C", "{dir}", "-o", "{last}", "{prompt}"]
    spec_path.write_text(json.dumps(spec, ensure_ascii=False, indent=2), encoding="utf-8")
    cwork = str(temp / "analysis-codex")
    try:
        codes = [_lib.run([py, conv, *c], temp)[0] for c in (
            ["analysis-prepare", str(skill), "--round", "1", "--runner", "codex", "--workdir", cwork],
            ["run", "--workdir", cwork, "--round", "1", "--kind", "analysis"],
            ["analysis-collect", "--workdir", cwork, "--round", "1"])]
    finally:
        spec_path.write_text(original, encoding="utf-8")
    want = {"runner": "codex", "model": "gpt-x", "effort": "low"}
    saved = _lib.load_json(analysis)["runs"]
    if codes != [0, 0, 0] or len(saved) != 2 or any({k: a.get(k) for k in want} != want for a in saved.values()):
        problems.append(f"run --kind analysis（runner codex）で、分析とモデルを集められない（終了コード {codes}）")
    return problems


def check_skip(skill: Path, temp: Path) -> bool:
    """spec に convergence.skip_reason がある（measure が skip）と、prepare が一時プロジェクトを作らずに止まるか（STEP-02）。"""
    spec_path = skill / _lib.SPEC_REL
    original = spec_path.read_text(encoding="utf-8")
    spec = json.loads(original)
    spec.setdefault("convergence", {})["skip_reason"] = "利用者が収束テストを省くと指定した"
    spec_path.write_text(json.dumps(spec, ensure_ascii=False, indent=2), encoding="utf-8")
    try:
        code, out = _lib.run([sys.executable, str(SCRIPTS / "convergence.py"), "prepare", str(skill), "--round", "1",
                              "--workdir", str(temp / "conv-skip")], temp)
    finally:
        spec_path.write_text(original, encoding="utf-8")
    ok = code != 0 and "skip_reason" in out and not (temp / "conv-skip").exists()
    print(f"{'成功' if ok else '失敗'}  収束テストを省くと書いたとき、prepare が止まる（終了コード {code}）")
    return ok


FENCE_CASES = [  # (一時プロジェクトの runner, 道具, 入力, 期待)。{lab} は自分、{other} はほかのエージェントの一時プロジェクト
    ("subagent", "Bash", {"command": "ls"}, "deny"),
    ("subagent", "Bash", {"command": "cd {lab} && ls"}, "rewrite"),
    ("subagent", "Read", {"file_path": "{other}/SKILL.md"}, "deny"),
    ("subagent", "Bash", {"command": "cd {lab} && mkdir -p /tmp/elsewhere"}, "deny"),
    ("subagent", "Bash", {"command": "cd {lab} && cat > a.md <<'EOF'\nsee /tmp/x\nEOF"}, "rewrite"),
    ("subagent", "Skill", {"skill": "x"}, "deny"),
    ("claude", "Write", {"file_path": "{lab}/out.txt", "content": "x"}, "allow"),
    ("claude", "Bash", {"command": "cat ~/.gitconfig"}, "deny"),
    ("codex", "apply_patch", {"command": "*** Begin Patch\n*** Add File: ../x.txt\n+x\n*** End Patch"}, "deny"),
]


def check_fence(temp: Path) -> bool:
    """prepare が fence.py を登録し、fence.py が FENCE_CASES のとおりに止める・通す・書き換えるか。"""
    labs: dict[str, list[str]] = {}
    for run in _lib.load_json(temp / "conv/round-1/plan.json")["runs"]:
        labs.setdefault(run["runner"], []).append(run["dir"])
    problems = []
    tester = temp / "agents" / "skill-foundation-tester.md"
    if not tester.is_file() or "fence.py" not in tester.read_text(encoding="utf-8"):
        problems.append("専用のエージェント型に fence.py の登録が無い")
    for runner, rel in (("claude", ".claude/settings.json"), ("codex", ".codex/hooks.json")):
        problems += [f"{d} の {rel} に fence.py の登録が無い" for d in labs.get(runner, [])
                     if "fence.py" not in (Path(d) / rel).read_text(encoding="utf-8")]
    for runner, tool, data, want in FENCE_CASES:
        lab = labs[runner][0]
        other = next(d for ds in labs.values() for d in ds if d != lab)
        data = json.loads(json.dumps(data).replace("{lab}", lab).replace("{other}", other))
        where = ["--agent"] if runner == "subagent" else ["--lab", lab]
        event = {"tool_name": tool, "tool_input": data, "agent_id": "selftest", "cwd": str(temp)}
        out = subprocess.run([sys.executable, str(SCRIPTS / "fence.py"), "--platform", "codex" if runner == "codex" else "claude",
                              *where], input=json.dumps(event), capture_output=True, text=True, timeout=30).stdout.strip()
        got = "allow" if not out else (json.loads(out)["hookSpecificOutput"].get("permissionDecision") or "rewrite")
        if got != want:
            problems.append(f"{runner} の {tool} {json.dumps(data, ensure_ascii=False)[:80]}: {got}（期待 {want}）")
    print(f"{'成功' if not problems else '失敗'}  作業ディレクトリの外への操作の停止（fence.py、{len(FENCE_CASES)} 例）")
    for problem in problems:
        print(f"    {problem}")
    return not problems


def check_codex_trace(temp: Path) -> bool:
    """trace が、Codex のサブエージェントの記録（作業ディレクトリで突き合わせる）と runner codex の出力を操作にするか。"""
    import catalog  # noqa: E402
    import convergence  # noqa: E402
    rdir = temp / "conv/round-1"
    plan = _lib.load_json(rdir / "plan.json")
    sub = next(r for r in plan["runs"] if r["runner"] == "subagent")
    cdx = next(r for r in plan["runs"] if r["runner"] == "codex")
    run_py = f"python3 {plan['place']}/{plan['name']}/scripts/run.py check"

    def item(ms, data):
        return {"type": "event_msg", "payload": {"type": "item_completed", "started_at_ms": ms, "item": data}}

    t0 = 1767225600000
    rollout = [{"type": "session_meta", "payload": {"thread_source": "subagent", "cwd": str(temp)}},
               {"type": "turn_context", "payload": {"model": "gpt-6-luna", "effort": "high"}},
               item(t0, {"type": "CommandExecution", "command": ["/bin/zsh", "-lc", f"cd {sub['dir']} && cat SKILL.md"], "exit_code": 0,
                         "aggregated_output": f"{sub['dir']}/SKILL.md の先頭\n" + "x" * 2000 + "\n末尾の行"}),
               item(t0 + 1000, {"type": "FileChange", "changes": {f"{sub['dir']}/out.txt": {"type": "add"}}, "status": "completed"}),
               item(t0 + 2000, {"type": "CommandExecution", "command": ["/bin/zsh", "-lc",
                                f"cd {sub['dir']} && cat > notes.md <<'EOF'\n- x\nEOF\n{run_py}"], "exit_code": 1, "status": "failed"}),
               item(t0 + 3000, {"type": "Reasoning"})]
    parent = [{"type": "session_meta", "payload": {"thread_source": "user"}},
              item(t0, {"type": "CommandExecution", "command": f"ls {sub['dir']} {sub['dir']}", "exit_code": 0})]
    sessions = temp / "codex-sessions/2026/01/01"
    sessions.mkdir(parents=True)
    for name, entries in (("rollout-sub.jsonl", rollout), ("rollout-parent.jsonl", parent)):
        (sessions / name).write_text("".join(json.dumps(e) + "\n" for e in entries), encoding="utf-8")
    lines = [("00.000", {"type": "thread.started"}),
             ("00.500", {"type": "item.started", "item": {"id": "item_0", "type": "command_execution", "command": "bash -lc ls"}}),
             ("01.000", {"type": "item.completed", "item": {"id": "item_0", "type": "command_execution", "command": "bash -lc ls",
                                                            "exit_code": 0, "status": "completed"}}),
             ("02.000", {"type": "item.completed", "item": {"id": "item_1", "type": "file_change", "status": "completed",
                                                            "changes": [{"path": f"{cdx['dir']}/out.txt", "kind": "add"}]}})]
    (rdir / "_results").mkdir(exist_ok=True)
    (rdir / "_results" / convergence.EVENTS.format(id=convergence.safe(cdx["id"]))).write_text(
        "".join(json.dumps({"at": f"2026-01-01T09:00:{at}+09:00", "line": json.dumps(e)}) + "\n" for at, e in lines) + "not json\n",
        encoding="utf-8")
    if not step("convergence.py trace（Codex の記録）", [sys.executable, str(SCRIPTS / "convergence.py"), "trace", "--workdir", str(temp / "conv"),
                "--round", "1", "--out", str(temp / "trace"), "--codex-sessions", str(temp / "codex-sessions"),
                "--transcripts", str(temp / "no-transcripts")], temp):
        return False
    runs = _lib.load_json(temp / "trace/traces.json")["runs"]
    got_sub = [(a["tool"], a["input"].splitlines()[0], a["ok"]) for a in runs[sub["id"]]["actions"]]
    got_cdx = [(a["at"][-12:-6], a["tool"], a["input"], a["ok"]) for a in runs[cdx["id"]]["actions"]]
    want_sub = [("Bash", "cat SKILL.md", True), ("Write", "out.txt", True), ("Bash", "cat > notes.md <<'EOF'", False)]
    want_cdx = [("00.500", "Bash", "ls", True), ("02.000", "Write", "out.txt", True)]
    problems = [f"{label}: {got}（期待 {want}）" for label, got, want in (("subagent", got_sub, want_sub), ("codex", got_cdx, want_cdx))
                if got != want]
    last = runs[sub["id"]]["actions"][-1:] if len(got_sub) == 3 else []
    if last and "run.py check" not in catalog.interpret(last[0])["commands"]:
        problems.append("ヒアドキュメントの後ろの run.py check を読めない")
    used = Path(plan["runs"][0]["dir"]) / plan["place"] / plan["name"] / "SKILL.md"
    if not (temp / "trace/used-SKILL.md").is_file() or (temp / "trace/used-SKILL.md").read_bytes() != used.read_bytes():
        problems.append("trace が、エージェントが読んだ SKILL.md の写し（used-SKILL.md）を残さない")
    out = runs[sub["id"]]["actions"][0].get("out", "")
    if not (out.startswith("SKILL.md の先頭") and out.endswith("末尾の行") and "字を略" in out and len(out) < 700):
        problems.append(f"操作の出力を、作業ディレクトリを相対にして先頭と末尾に縮めて残していない: {out[:60]!r}")
    got_model = {k: runs[sub["id"]].get(k) for k in ("model", "effort")}
    if got_model != {"model": "gpt-6-luna", "effort": "high"}:
        problems.append(f"Codex のサブエージェントの記録からモデルを読めない: {got_model}")
    settings = convergence.codex_settings(["codex", "exec", "-m", "gpt-x", "-c", "model_reasoning_effort=low", "--json", "x"])
    if settings != {"model": "gpt-x", "effort": "low", "settings": True}:
        problems.append(f"codex exec のコマンドからモデルを読めない: {settings}")
    call = {"type": "tool_use", "id": "t1", "name": "Bash", "input": {"command": "ls"}}
    transcript = temp / "agent-blob.jsonl"
    transcript.write_text("".join(json.dumps(e) + "\n" for e in [
        {"type": "user", "message": {"content": "プロンプト"}},
        {"type": "assistant", "timestamp": "2026-01-01T00:00:00Z", "message": {"content": [call]}},
        {"type": "user", "message": {"content": [{"type": "tool_result", "tool_use_id": "t1", "content": "a"}]}},
        {"type": "api-request-blob", "message": {"content": [call]}}]), encoding="utf-8")
    if len(convergence.transcript_actions(transcript, str(temp))) != 1:
        problems.append("Agent ツールの記録の、API に送った会話の写し（api-request-blob）の呼び出しを二重に数える")
    print(f"{'成功' if not problems else '失敗'}  Codex の記録から操作の列を作る（subagent {len(got_sub)} 件、codex {len(got_cdx)} 件）")
    for problem in problems:
        print(f"    {problem}")
    return not problems


def check_places(skill: Path, project: Path, out: Path) -> bool:
    """もう一方の置き場の複製を、install.py --check が問題にし、skill_lint.py が本体の場所を見分け、カタログが要確認に出すか。"""
    import skill_lint  # noqa: E402
    install = [sys.executable, str(skill / "scripts/install.py"), "--project", str(project), "--no-hooks"]
    twin = project / ".agents/skills" / skill.name
    _lib.run(install, project)
    problems = [] if twin.is_symlink() and _lib.run(install + ["--check"], project)[0] == 0 else ["リンクで置いても install.py --check が通らない"]
    if twin.is_symlink():
        twin.unlink()
        shutil.copytree(skill, twin)
        code, text = _lib.run(install + ["--check"], project)
        if code == 0 or "複製" not in text:
            problems.append("複製を install.py --check が問題にしない")
        if _lib.run(install + ["--check", "--mode", "copy"], project)[0] != 0:
            problems.append("--mode copy の install.py --check が複製を通さない")
        spec = _lib.load_spec(skill)
        if skill_lint.place_problem(skill, spec, project) or not skill_lint.place_problem(twin, spec, project):
            problems.append("skill_lint.py が本体の場所を見分けない")
        if _lib.run([sys.executable, str(SCRIPTS / "catalog.py"), "--project", str(project), "--out", str(out)], project, timeout=300)[0] != 0:
            problems.append("catalog.py が失敗した")
        elif "同じ名前のスキルが別の場所にもある" not in (out.with_suffix("") / f"{skill.name}.html").read_text(encoding="utf-8"):
            problems.append("カタログが同じ名前のスキルを要確認に出さない")
    print(f"{'成功' if not problems else '失敗'}  置き場の検査（リンク、複製、本体の場所、カタログ）")
    for problem in problems:
        print(f"    {problem}")
    return not problems


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--example", default="write-commit-message")
    parser.add_argument("--keep", action="store_true", help="一時プロジェクトを消さずに残す")
    parser.add_argument("--build", help="検証せずに、見本をこのプロジェクトに組み立てる")
    parser.add_argument("--ready", action="store_true", help="--build のとき、probe まで済ませて status を ready にする")
    args = parser.parse_args()

    example = EXAMPLES / args.example
    if not (example / "spec.json").is_file():
        _lib.fail(f"見本がありません: {example}")
    if args.build:
        project = Path(args.build).resolve()
        project.mkdir(parents=True, exist_ok=True)
        skill = assemble(example, project)
        ok = skill is not None and (not args.ready or make_ready(skill))
        return 0 if ok else 1
    temp = Path(tempfile.mkdtemp(prefix="skill-foundation-selftest-")).resolve()
    scripts, py = SCRIPTS, sys.executable
    try:
        (temp / "proj").mkdir()
        skill = assemble(example, temp / "proj")
        results = [skill is not None]
        if skill is not None:
            results.append(step("render_skill.py --check", [py, str(scripts / "render_skill.py"), "--dir", str(skill), "--check"], temp))
            results.append(step("skill_lint.py --phase 5", [py, str(scripts / "skill_lint.py"), str(skill), "--phase", "5"], temp))
            results.append(step("probe.py", [py, str(scripts / "probe.py"), str(skill)], temp))
            results.append(check_catalog(skill, temp / "proj", temp / "catalog.html"))
            results.append(step("convergence.py prepare（全課題）",
                                [py, str(scripts / "convergence.py"), "prepare", str(skill), "--round", "1",
                                 "--include-holdout", "--agents", "1", "--runners", "claude,codex,subagent",
                                 "--workdir", str(temp / "conv"), "--agents-dir", str(temp / "agents")], temp))
            results.append(check_skip(skill, temp))
            results.append(results[-2] and check_fence(temp))
            results.append(results[-3] and check_codex_trace(temp))
            results.append(check_places(skill, temp / "proj", temp / "twins.html"))
            results.append(check_analysis(skill, temp / "proj", temp))
        failed = results.count(False)
        print(f"\n自己テスト: {len(results)} 段階中 失敗 {failed} 件")
        return 1 if failed else 0
    finally:
        if args.keep:
            print(f"一時プロジェクトを残しました: {temp}")
        else:
            shutil.rmtree(temp, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
