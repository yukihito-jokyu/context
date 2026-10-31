#!/usr/bin/env python3
"""自己テスト: 見本（assets/example/<名前>/）から一時プロジェクトにスキルを組み立て、作成用スクリプトが通しで動くことを確かめる。

  1. 見本の spec・probes・evals・research・fixtures・Eval（eval/）・固有スクリプト・出力の見本を、一時プロジェクトの
     スキルの dev/、dev/eval/、scripts/、assets/examples/ に置く
  2. init_skill.py で骨組みを作り、見本の procedure.md を SKILL.md の「2. 手順」に入れる
  3. render_skill.py --check、skill_lint.py --phase 5、probe.py、eval_check.py を実行する
  4. 収束テストの記録の見本（report.json と traces.json）を置いて catalog.py でカタログを書き、一覧からスキルの
     ページへのリンクがあり、ページにスキルの欄、ワークフロー図、エージェントの動きの図があり、図（SVG）が XML として
     読めることを確かめる。一番左のタブが Eval 作成で、材料から事例と Eval 自体の検証までを載せることも確かめる。
     Eval に答えを待っている質問（questions）を足すと、eval_check.py が止め、カタログが削って開く質問のカードと回答シートを
     出し、貼られた回答を eval_check.py --answer が dialog に記録し、その後に直した項目にカタログが「更新」のラベルを付けることも確かめる。
     catalog.py の「見せ方の約束」（BANNED_WORDS の語を見せない、ページ内のリンクの飛び先が
     ある、「先に見るもの」が操作の行へ飛ぶ、系列を浮かび上がらせる凡例、モデルと推論エフォート）も確かめる。
     カタログに載る skill-foundation の文書と、新しいスキルに写るひな形に DOC_WORDS の語が無いことも確かめる
  5. convergence.py prepare で、全課題の fixture と setup が動くことを確かめる（エージェントは起動しない）。準備したままの
     エージェントを diff の失格の判定が失格にしないことと、spec に convergence.skip_reason があると、prepare が
     一時プロジェクトを作らずに止まることも確かめる。diff が、エージェントの出力を Eval で採点すること（code の判定、
     model の判定を分析役に頼む中身、Eval に落ちた課題を基準を満たさないとすること、holdout を採点しないこと）も確かめる
     設定（settings/）の順も確かめる。run.py start が、依頼の指定 → ユーザーの設定 → スキルの設定 → --guess の順に入力を補って
     出どころを記録し、skill_lint.py が設定の誤りを見つけること。convergence.py の動かし方が、引数 → spec の convergence →
     ユーザーの設定 → スキルの設定 の順に決まり、モデルと推論エフォートが runner の起動コマンドに入ること
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
     を動かして分析を集めること）も確かめる。分析役に model の判定を頼み、analysis-collect が判定の無い分析をはじき、
     判定を report.json に取り込んで課題の基準を決め直すことと、Eval の採点を締め込みに使う仕組み（落ちた判定が
     「## Eval の採点」の表に無いか、Eval の疑いの後に Eval を直していないと、次のラウンドの prepare が止めること。最後の
     ラウンドで終えるなら、直さずに「結論」に残せること）も確かめる

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
    if (example / "eval").is_dir():
        _lib.copy_tree(example / "eval", skill / "dev" / "eval")
    if (example / "scripts").is_dir():
        _lib.copy_tree(example / "scripts", skill / "scripts")
    if (example / "examples").is_dir():
        _lib.copy_tree(example / "examples", skill / _lib.EXAMPLES_DIR)
    return skill


READY_REPORT = """# {name} 収束テストの記録

skill-foundation の自己テストのために見本から組み立てたスキルなので、収束テストを省いた（dev/spec.json の
convergence.skip_reason）。

## 結論

収束テストは実施していないので、出力を Eval で採点してもいない。
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
    return (step("eval_check.py", [sys.executable, str(SCRIPTS / "eval_check.py"), str(skill)], skill)
            and step("render_skill.py", [sys.executable, str(SCRIPTS / "render_skill.py"), "--dir", str(skill)], skill)
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
    import eval_check
    pending = {"type": "model", "target": out, "result": "pending", "detail": ""}  # behavior-3 は model の判定（分析役が判定する）
    _lib.write_json(rdir / "report.json", {"round": 1, "runners": ["subagent"], "thresholds": {"files": 1.0, "structure": 1.0, "names": 0.8},
                                           "eval": {"hash": eval_check.eval_hash(skill), "dialog": len(eval_check.load(skill)[0]["dialog"])}, "tasks": [
        {"id": "T1-typical", "agents": ["subagent-1", "subagent-2"], "expect_status": "done", "status": {"subagent-1": "done", "subagent-2": "done"},
         "files": 1.0, "structure": 1.0, "names": 1.0, "content": 0.9, "by_runner": {}, "check": {}, "fence_changed": {}, "excerpts": [],
         "check_failures": {}, "converged": False, "variance_ok": True, "eval_ok": None,
         "eval": {f"subagent-{i}": {"behavior-3": dict(pending)} for i in (1, 2)},
         "changed_files": {"subagent-1": [out], "subagent-2": [out]}, "partial_files": [], "messages": {}}]})
    for i in (1, 2):
        _lib.write_json(rdir / f"T1-typical/subagent-{i}.eval.json",
                        {"behavior-3": {"target": out, "text": (skill / "dev/eval/cases/good.txt").read_text(encoding="utf-8")}})
    (rdir / "T1-typical/subagent-1.patch").write_text(f"=== {out}\nfeat: 見本\n=== .api-flow/chart.png\n(削除・バイナリ)\n", encoding="utf-8")
    image = rdir / "records/outputs/T1-typical__subagent-1/.api-flow/chart.png"  # convergence.py diff が置く写し
    image.parent.mkdir(parents=True, exist_ok=True)
    image.write_bytes(b"\x89PNG\r\n\x1a\n")
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
    tabs = re.findall(r'data-show="skill-' + re.escape(skill.name) + r'-([a-z]+)"', text)
    if not tabs or tabs[0] != "eval":
        problems.append(f"一番左のタブが Eval 作成ではない（今: {tabs[:1]}）")
    for want in ("価値を見つけた材料", "Eval ができるまで", "talk-3", "case-7", "Eval 自体の検証", "確定した価値と、収束テストでの採点",
                 "判定のしかた", "収束テストでの採点</b>"):
        if want not in text:
            problems.append(f"Eval 作成のタブに「{want}」が無い")
    if "<h3>収束テストの題材</h3>" not in text or f'id="{skill.name}-ev-T1-typical"' not in text:
        problems.append("Eval 作成のタブに、収束テストの題材の表が無い")
    if "成果物 2 件" not in text or "契約の出力" not in text or \
            not re.search(r'<img src="[^"]*records/outputs/T1-typical__subagent-1/\.api-flow/chart\.png"', text):
        problems.append("エージェントの動きのタブに、成果物（契約の出力と、records/outputs の写しの画像）が無い")
    if not re.search(r'class="[^"]*hkd-ev used"[^>]*data-hk="PreToolUse"', text):
        problems.append("hooks 設計のタブに、このスキルが hooks を置くイベント（PreToolUse と matcher）が無い")
    if set(re.findall(r' data-hk="(\w+)"', text)) != set(re.findall(r'data-hk-pane="(\w+)"', text)):
        problems.append("hooks 設計の図の箱と、押したときに出す詳しい欄が揃っていない")
    if "<h3>Eval の採点</h3>" not in text or "判定待ち" not in text:
        problems.append("収束テストのタブに、Eval の採点（model の判定待ち）が無い")
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



QUESTIONS = {"talk": "talk-4", "items": [
    {"title": "見本の選ぶ質問", "ask": "見本の質問の文", "refs": ["value-1"],
     "options": [{"key": "A", "text": "見本の答え"}, {"key": "B", "text": "その他", "free": True}]},
    {"title": "見本の書く質問", "ask": "見本の質問の文"}]}
ANSWER = "Eval 作成の回答（{name}、{talk}）\nQ1 見本の選ぶ質問: A. 見本の答え\nQ2 見本の書く質問:\n  見本の書いた答え\n"


def check_eval_questions(skill: Path, project: Path, out: Path) -> bool:
    """Eval 作成の聞き方（references/eval.md の2章）: 答えを待っている質問があると eval_check.py が止め、カタログが質問のカードと
    回答シートを出し、貼られた回答を --answer が dialog に記録し、回答の後に直した項目にカタログがラベルを付けるか。"""
    import eval_check
    py, problems = sys.executable, []
    eval_path, result_path = skill / eval_check.EVAL_REL, skill / eval_check.RESULT_REL
    saved = {path: path.read_text(encoding="utf-8") for path in (eval_path, result_path)}
    page = out.with_suffix("") / f"{skill.name}.html"
    check, catalog = [py, str(SCRIPTS / "eval_check.py"), str(skill)], [py, str(SCRIPTS / "catalog.py"), "--project", str(project), "--out", str(out)]
    try:
        doc = json.loads(saved[eval_path])
        talks = len(doc["dialog"])
        doc["questions"] = QUESTIONS
        _lib.write_json(eval_path, doc)
        code, text = _lib.run(check, project)
        if code == 0 or "ユーザーの答えを待っている質問が 2 件" not in text:
            problems.append(f"答えを待っている質問があるのに、eval_check.py が止めない（終了コード {code}）")
        _lib.run(catalog, project)
        html = page.read_text(encoding="utf-8") if page.is_file() else ""
        if html.count('class="evq-q covered"') != 2 or "data-evq-copy" not in html or "data-evq-tab" not in html:
            problems.append("カタログの Eval 作成のタブに、削って開く質問のカード2枚と回答シート、タブの質問の数が無い")
        code, text = _lib.run(check + ["--answer", ANSWER.format(name=skill.name, talk="talk-9")], project)
        if code == 0 or "今の質問は" not in text:
            problems.append("ほかの対話への回答を、eval_check.py --answer が受け付けた")
        code, text = _lib.run(check + ["--answer", ANSWER.format(name=skill.name, talk="talk-4")], project)
        doc = json.loads(eval_path.read_text(encoding="utf-8"))
        before = json.loads(result_path.read_text(encoding="utf-8")).get("before") or {}
        if code != 0 or "questions" in doc or len(doc["dialog"]) != talks + 1 or "見本の書いた答え" not in doc["dialog"][-1]["answer"] \
                or before.get("talk") != "talk-4":
            problems.append(f"貼られた回答を、eval_check.py --answer が dialog に記録していない（終了コード {code}）\n" + _lib.tail(text, 5))
        doc["values"][0]["text"] += "（見本の直し）"
        _lib.write_json(eval_path, doc)
        _lib.run(check, project)
        _lib.run(catalog, project)
        html = page.read_text(encoding="utf-8") if page.is_file() else ""
        if '<span class="ev-tag upd"' not in html or "前: <del>" not in html or '<span class="ev-tag keep"' not in html:
            problems.append("回答の後に直した項目に、カタログが「更新」のラベルと前の文を付けていない")
    finally:
        for path, text in saved.items():
            path.write_text(text, encoding="utf-8")
    print(f"{'成功' if not problems else '失敗'}  Eval 作成の質問をカタログで答え、回答を記録する")
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
        if run.get("eval") != ["behavior-3"] or "## Eval の判定" not in text or "### behavior-3" not in text:
            problems.append(f"{run['id']} の record.md に、model の判定を頼む「Eval の判定」の節が無い")
        ops = [{"n": n, "fit": "ok" if n != 5 else "detour", "why": f"#{n} の理由の見本"} for n in range(1, run["ops"] + 1)]
        bad = run["id"].endswith("-2")
        _lib.write_json(Path(run["dir"]) / "analysis.json", {"ops": ops[:-1] if bad else ops, "compare": "", "eval": JUDGED,
                        "flow": {"verdict": "poor", "summary": "#2 で始めて #4 で失敗した見本", "issues": ["#4 の失敗"], "suggestions": []}})
    collect = [py, conv, "analysis-collect", "--workdir", str(work), "--round", "1"]
    code, out = _lib.run(collect, temp)
    saved = _lib.load_json(skill / "dev/results/convergence/round-1/analysis.json").get("runs", {})
    if code != 1 or "T1-typical/subagent-2" not in out or sorted(saved) != ["T1-typical/subagent-1"]:
        problems.append(f"analysis-collect が、決まりに合わない分析をはじいて、合うものだけを残していない（終了コード {code}）")
    run2 = next(r for r in plan["runs"] if r["id"].endswith("-2"))
    fixed = {"ops": [{"n": n, "fit": "ok", "why": "見本"} for n in range(1, run2["ops"] + 1)],
             "compare": "", "flow": {"verdict": "good", "summary": "見本", "issues": [], "suggestions": []}}
    _lib.write_json(Path(run2["dir"]) / "analysis.json", fixed)
    code, out = _lib.run(collect, temp)
    if code != 1 or "behavior-3" not in out:
        problems.append(f"analysis-collect が、頼んだ model の判定（eval）の無い分析をはじかない（終了コード {code}）")
    _lib.write_json(Path(run2["dir"]) / "analysis.json", {**fixed, "eval": JUDGED})
    if _lib.run(collect, temp)[0] != 0:
        problems.append("analysis-collect が、決まりどおりの分析を受け入れない")
    task = _lib.load_json(skill / "dev/results/convergence/round-1/report.json")["tasks"][0]
    if {a: s["behavior-3"]["result"] for a, s in task["eval"].items()} != {"subagent-1": "pass", "subagent-2": "pass"} \
            or task.get("eval_ok") is not True or not task.get("converged"):
        problems.append("analysis-collect が、分析役の model の判定を report.json に取り込んで課題の基準を決め直さない")
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
    problems += eval_gate_problems(skill, temp)
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
JUDGED = [{"behavior": "behavior-3", "result": "pass", "reason": "各行の要約が、そのファイルの差分の内容と合っている見本"}]  # 分析役の model の判定


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
                                     "issues": [], "suggestions": []},
                                     "eval": [{"behavior": b, "result": "pass", "reason": "Codex の分析役の見本"} for b in run["eval"]]},
                                    ensure_ascii=False), encoding="utf-8")
Path(args[args.index("-o") + 1]).write_text("書きました", encoding="utf-8")
print(json.dumps({"type": "thread.started"}))
'''  # codex exec の代わり。プロンプトに record.md と analysis.json の場所があれば、決まりどおりの分析（頼まれた model の判定を含む）を書く


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


def eval_gate_problems(skill: Path, temp: Path) -> list[str]:
    """Eval の採点を締め込みに使う仕組み（STEP-07）: 落ちた判定が「## Eval の採点」の表に無いか、Eval の疑いの後に
    ユーザーと話して Eval を直していないと次のラウンドの prepare が止め、直した後は止めないか。最後のラウンドで終えるなら、
    skill_lint.py --final が、Eval を直さずに疑いを「結論」に残すことを認め、残していなければ求めるか（prepare は止めたまま）。
    skill_lint.py --final が、最後のラウンドを今の Eval で採点していないことを止めるか。"""
    import eval_check
    py, problems = sys.executable, []
    report, notes, eval_path = (skill / "dev/results/convergence/round-1/report.json", skill / "dev/convergence-report.md",
                                skill / eval_check.EVAL_REL)
    saved = {path: path.read_text(encoding="utf-8") for path in (report, notes, eval_path, skill / eval_check.RESULT_REL)}
    data = json.loads(saved[report])
    data["tasks"][0]["eval"]["subagent-2"]["behavior-3"].update(result="fail", detail="見本の落ちた判定")
    _lib.write_json(report, data)
    base = re.sub(r"(^## 動きの指摘\n.*?^\|---\|---\|---\|---\|---\|\n)", lambda m: m.group(1) + FINDINGS_ROW.replace("{cls}", "V3"),
                  re.sub(r"^## Eval の採点\n.*?(?=^## )", "", saved[notes], flags=re.M | re.S), count=1, flags=re.M | re.S)
    prepare = [py, str(SCRIPTS / "convergence.py"), "prepare", str(skill), "--round", "2", "--only-tasks", "T1-typical",
               "--agents", "1", "--runners", "claude", "--workdir", str(temp / "conv-eval"), "--force"]

    def table(cls: str) -> str:  # 「## Eval の採点」の表を、その分類の行1つ（分類が空なら行なし）にする
        rows = f"| 1 | T1-typical/subagent-2 | behavior-3 | {cls} | 見本の対処 |\n" if cls else ""
        return base.replace("## 結論", "## Eval の採点\n\n| ラウンド | 課題/エージェント | 振る舞い | 分類 | 対処 |\n"
                                        f"|---|---|---|---|---|\n{rows}\n## 結論", 1)
    cases = [("", "Eval に落ちた判定が、「Eval の採点」の表にありません", "落ちた判定が表に無い"),
             ("出力の誤り", "", "出力の誤りと分類した"),
             ("Eval の疑い", "対話（dialog）が増えていません", "Eval の疑いの後に Eval を直していない")]
    try:
        for cls, message, what in cases:
            notes.write_text(table(cls), encoding="utf-8")
            code, out = _lib.run(prepare, temp)
            if (code == 0 or message not in out) if message else code != 0:
                problems.append(f"{what}のに、次のラウンドの prepare が{'止めない' if message else '止める'}（終了コード {code}）"
                                + ("" if message else "\n" + _lib.tail(out, 5)))
        lint = [py, str(SCRIPTS / "skill_lint.py"), str(skill), "--final"]
        if "「結論」に behavior-3 の分類と残した理由" not in _lib.run(lint, temp)[1]:
            problems.append("最後のラウンドの Eval の疑いを直さず「結論」にも残していないのに、skill_lint.py --final が求めない")
        notes.write_text(table("Eval の疑い").replace("## 結論\n", "## 結論\n\n- behavior-3: Eval の疑い。最後のラウンドなので直さない（見本）\n", 1),
                         encoding="utf-8")
        out = _lib.run(lint, temp)[1]
        if "Eval を直さずに「結論」に残しています" not in out or "対話（dialog）が増えていません" in out:
            problems.append("最後のラウンドで終えて Eval の疑いを「結論」に残したのに、skill_lint.py --final が認めない\n" + _lib.tail(out, 5))
        code, out = _lib.run(prepare, temp)
        if code == 0 or "対話（dialog）が増えていません" not in out:
            problems.append(f"Eval の疑いを「結論」に残しただけで、次のラウンドの prepare が止めない（終了コード {code}）")
        doc = json.loads(saved[eval_path])
        doc["dialog"].append({"id": f"talk-{len(doc['dialog']) + 1}", "asked": "見本の質問", "answer": "見本の答え"})
        eval_path.write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")
        _lib.run([py, str(SCRIPTS / "eval_check.py"), str(skill)], temp)
        code, out = _lib.run(prepare, temp)
        if code != 0:
            problems.append(f"Eval の疑いの後にユーザーと話して Eval を直したのに、次のラウンドの prepare が止める（終了コード {code}）\n"
                            + _lib.tail(out, 5))
        if "最後のラウンドを今の Eval で採点していません" not in _lib.run([py, str(SCRIPTS / "skill_lint.py"), str(skill), "--final"], temp)[1]:
            problems.append("Eval を直した後のラウンドが無いのに、skill_lint.py --final が止めない")
    finally:
        for path, text in saved.items():
            path.write_text(text, encoding="utf-8")
    return problems


def check_eval_scoring(skill: Path, temp: Path) -> bool:
    """diff が各エージェントの出力を Eval で採点するか（STEP-07）。準備したままのエージェントの2人に、Eval の事例の
    成功と失敗の出力を置き、code の判定、model の判定を頼む中身、課題の基準、holdout を採点しないことを確かめる。"""
    import eval_check
    plan_path = temp / "conv/round-1/plan.json"
    plan = _lib.load_json(plan_path)
    labs = {r["id"]: Path(r["dir"]) for r in plan["runs"]}
    for rid, sample in (("T1-typical/claude-1", "good.txt"), ("T1-typical/codex-1", "prefixed.txt")):
        place = labs[rid] / ".skill-runs" / skill.name
        (place / "out").mkdir(parents=True, exist_ok=True)
        shutil.copy(skill / "dev/eval/cases" / sample, place / "out/commit-message.txt")
        _lib.write_json(place / "state.json", {"status": "active", "input": {"ticket": "ABC-12"}, "history": []})
    out, original = temp / "diff-eval", plan_path.read_text(encoding="utf-8")
    plan.setdefault("expect", {})["H1-holdout"] = "unused"  # スキルを使わないのが正解の課題として扱う
    _lib.write_json(plan_path, plan)
    try:
        _lib.run([sys.executable, str(SCRIPTS / "convergence.py"), "diff", "--workdir", str(temp / "conv"), "--round", "1", "--out", str(out)], temp)
    finally:
        plan_path.write_text(original, encoding="utf-8")
    report = _lib.load_json(out / "report.json") if (out / "report.json").is_file() else {}
    tasks = {t["id"]: t for t in report.get("tasks", [])}
    t1 = tasks.get("T1-typical", {})
    got = {agent: {b: x.get("result") for b, x in scores.items()} for agent, scores in t1.get("eval", {}).items()}
    want = {"claude-1": {"behavior-1": "pass", "behavior-2": "pass", "behavior-3": "pending"},
            "codex-1": {"behavior-1": "fail", "behavior-2": "pass", "behavior-3": "pending"},
            "subagent-1": {"behavior-1": "na", "behavior-2": "na", "behavior-3": "na"}}
    problems = [] if got == want else [f"T1-typical の採点が期待と違う: {got}"]
    if (report.get("eval") or {}).get("hash") != eval_check.eval_hash(skill):
        problems.append("report.json に、採点に使った Eval のハッシュが無い")
    if t1.get("eval_ok") is not False or t1.get("converged"):
        problems.append("Eval に落ちた出力がある課題を、基準を満たさないとしていない")
    if "H1-holdout" not in tasks or tasks["H1-holdout"].get("eval"):
        problems.append("スキルを使わないのが正解の課題（expect_status が unused）を採点した")
    asks_path = out / "T1-typical/claude-1.eval.json"
    asks = _lib.load_json(asks_path) if asks_path.is_file() else {}
    if list(asks) != ["behavior-3"] or "ABC-12" not in asks["behavior-3"].get("text", ""):
        problems.append("model の判定を分析役に頼む中身（<課題>/<エージェント>.eval.json）が無い")
    print(f"{'成功' if not problems else '失敗'}  diff が各エージェントの出力を Eval で採点する")
    for problem in problems:
        print(f"    {problem}")
    return not problems


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


def check_settings(skill: Path, project: Path) -> bool:
    """設定（settings/）: YAML の読み方、run.py start の入力の補い方と出どころ、skill_lint.py の設定の検査、
    収束テストの動かし方の決め方。"""
    import _skillrt as rt
    import convergence
    py, problems = sys.executable, []
    folder, run = skill / "settings", [sys.executable, str(skill / "scripts/run.py")]

    def start(user, mine, *extra) -> dict:
        folder.mkdir(exist_ok=True)
        (folder / "skill-setting.yaml").write_text(f"inputs:\n  ticket: {json.dumps(mine)}\n", encoding="utf-8")
        (folder / "user-setting.yaml").write_text(f"inputs: # 入力\n  ticket: {json.dumps(user)} # 書き方の説明\n", encoding="utf-8")
        code, text = _lib.run(run + ["start", "--json", *extra, "見本の依頼"], project)
        _lib.run(run + ["abort", "--reason", "自己テスト"], project)
        try:
            data = json.loads(text[text.index("{"):]) if code == 0 else {}
        except ValueError:
            data = {}
        return {"ticket": data.get("input", {}).get("ticket"), "from": data.get("default_from", {}).get("ticket", "given")}

    sample = folder / "sample.yaml"  # 設定に使う書き方を一通り
    folder.mkdir(exist_ok=True)
    sample.write_text("# 見出し\na: # c\n  b: [x, \"y # z\"] # c\n  c:\n    - 1\n    - 0.5\n  d: null\ne: 'p # q' # c\nf: true\n",
                      encoding="utf-8")
    wanted_yaml = {"a": {"b": ["x", "y # z"], "c": [1, 0.5], "d": None}, "e": "p # q", "f": True}
    try:
        got_yaml = rt.load_yaml(sample)
    except ValueError as exc:
        got_yaml = str(exc)
    sample.unlink()
    if got_yaml != wanted_yaml:
        problems.append(f"設定の YAML を {got_yaml} と読んだ（期待 {wanted_yaml}）")
    try:
        cases = [(("abc-1", "zzz-9"), [], {"ticket": "ABC-1", "from": "user"}),
                 ((None, "zzz-9"), ["--guess", "ticket=g-1"], {"ticket": "ZZZ-9", "from": "skill"}),
                 ((None, None), ["--guess", "ticket=g-1"], {"ticket": "G-1", "from": "guess"}),
                 (("abc-1", "zzz-9"), ["--set", "ticket=x-2"], {"ticket": "X-2", "from": "given"})]
        for (user, mine), extra, wanted in cases:
            got = start(user, mine, *extra)
            if got != wanted:
                problems.append(f"ユーザーの設定 {user}、スキルの設定 {mine}、{extra} で、run.py start が {got} にした（期待 {wanted}）")
        (folder / "user-setting.yaml").write_text(
            "inputs:\n  tiket: abc-1 # 書き方の説明\nconvergence:\n  agents: 0\n", encoding="utf-8")
        code, text = _lib.run([py, str(SCRIPTS / "skill_lint.py"), str(skill), "--phase", "3"], project)
        if code == 0 or "`tiket`" not in text or "convergence.agents" not in text:
            problems.append(f"設定の知らない入力と、種類に合わない収束テストの値を、skill_lint.py が見つけない（終了コード {code}）")
    finally:
        shutil.rmtree(folder, ignore_errors=True)
    saved = _lib.setting_files
    mine = rt.load_yaml(_lib.FOUNDATION_DIR / "settings/skill-setting.yaml")
    _lib.setting_files = lambda: ([("user", {"convergence": {"agents": 4, "max_rounds": 5, "model": {"codex": "gpt-x"}}}),
                                   ("skill", mine)], [])
    try:
        cfg, sources, _ = _lib.convergence_settings({"convergence": {"agents": 3}}, {"runners": ["codex"]})
    finally:
        _lib.setting_files = saved
    picked = {k: (_lib.setting_value(cfg, k), sources.get(k)) for k in ("runners", "agents", "max_rounds", "model.codex", "parallel")}
    if picked != {"runners": (["codex"], "args"), "agents": (3, "spec"), "max_rounds": (5, "user"), "model.codex": ("gpt-x", "user"),
                  "parallel": (mine["convergence"]["parallel"], "skill")}:
        problems.append(f"収束テストの動かし方が、引数 → spec → ユーザーの設定 → スキルの設定 の順に決まらない: {picked}")
    codex = convergence.with_model(convergence.default_runner("codex"), "codex", "gpt-x", "high")
    claude = convergence.with_model(convergence.default_runner("claude"), "claude", "opus", "low")
    if {k: v for k, v in convergence.codex_settings(codex).items() if k in ("model", "effort")} != {"model": "gpt-x", "effort": "high"} \
            or claude[claude.index("--model"):claude.index("--allowedTools")] != ["--model", "opus", "--effort", "low"]:
        problems.append("設定のモデルと推論エフォートが、runner の起動コマンドに入らない")
    print(f"{'成功' if not problems else '失敗'}  設定（settings/）の YAML、順と出どころ、設定の検査、モデルと推論エフォートの受け渡し")
    for problem in problems:
        print(f"    {problem}")
    return not problems


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


def check_untouched(temp: Path) -> bool:
    """スキルにも hooks にも手を付けていないエージェントを、diff が失格にしないか（作業ディレクトリの複製で確かめる）。"""
    import convergence  # noqa: E402
    plan = _lib.load_json(temp / "conv/round-1/plan.json")
    spec = _lib.load_spec(Path(plan["skill"]))
    problems = [f"{run['id']}: {e}" for run in plan["runs"]
                for e in convergence.fence_changes(run, plan)]
    print(f"{'成功' if not problems else '失敗'}  手を付けていないエージェントを失格にしない")
    for problem in problems[:3]:
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
    stream = [{"type": "system", "subtype": "init"}, {"type": "assistant", "message": {"content": [call]}},
              {"type": "user", "message": {"content": [{"type": "tool_result", "tool_use_id": "t1", "content": "a"}]}},
              {"type": "result", "result": "本文", "modelUsage": {"claude-x": {"outputTokens": 1}}}]
    (temp / "claude.events.jsonl").write_text("".join(json.dumps({"at": f"2026-01-01T09:00:0{i}+09:00", "line": json.dumps(e)}) + "\n"
                                                      for i, e in enumerate(stream)), encoding="utf-8")
    got_claude = [(a["at"], a["tool"], a["input"], a["ok"]) for a in convergence.transcript_actions(temp / "claude.events.jsonl", str(temp))]
    if got_claude != [("2026-01-01T09:00:01+09:00", "Bash", "ls", True)]:
        problems.append(f"claude -p の stream-json の出力から操作の列を作れない: {got_claude}")
    if convergence.last_message("claude", "\n".join(json.dumps(e) for e in stream), temp / "none") != "本文":
        problems.append("claude -p の stream-json の出力から最終の返答を読めない")
    history = [{"at": "2026-01-01T09:00:01+09:00", "event": "start", "detail": ""},
               {"at": "2026-01-01T09:00:05+09:00", "event": "check", "detail": "2 件"},
               {"at": "2026-01-01T09:00:06+09:00", "event": "stop-blocked", "detail": "2 件"},
               {"at": "2026-01-01T10:00:00+09:00", "event": "check", "detail": "0 件"}]
    outcome = {"seconds": 7, "output_tail": json.dumps({"result": "本文", "permission_denials": [
        {"tool_name": "Bash", "tool_use_id": "t2", "tool_input": {"command": f"cd {temp} && glab ci lint"}}]})}
    state = {"input": {"style": "new"}, "text": "作って", "history": history}
    acts, denied = convergence.claude_result_actions(outcome, state, 1767225608, "python3 run.py", str(temp))  # 09:00:08+09:00 に終わった
    got_old = ([(a["input"], a["ok"]) for a in acts], [(d["tool"], d["input"]) for d in denied])
    if got_old != ([("python3 run.py start --set style=new '作って'", True), ("python3 run.py check", False)], [("Bash", "glab ci lint")]):
        problems.append(f"stream-json の無い claude -p の実行記録と許可されなかった操作から、操作の一部を作れない: {got_old}")
    kept = {p.name for p in (temp / "trace" / convergence.RECORDS).glob("*.gz")}
    want = {f"{convergence.safe(cdx['id'])}.events.jsonl.gz", f"{convergence.safe(sub['id'])}.rollout.jsonl.gz", "plan.json.gz"}
    if not want <= kept:
        problems.append(f"trace が元の記録の写しを records/ に残さない: {sorted(want - kept)}")
    else:  # 一時ディレクトリの記録と製品の記録が消えた後も、写しから同じ動きを作る
        (rdir / "_results" / convergence.EVENTS.format(id=convergence.safe(cdx["id"]))).unlink()
        convergence.write_traces(plan, rdir, temp / "trace", temp / "no-transcripts", temp / "no-sessions")
        again = _lib.load_json(temp / "trace/traces.json")["runs"]
        if any(again[r["id"]]["actions"] != runs[r["id"]]["actions"] for r in (sub, cdx)):
            problems.append("元の記録が消えた後に、records/ の写しから動きを作り直せない")
    print(f"{'成功' if not problems else '失敗'}  Codex と Claude Code の記録から操作の列を作る（subagent {len(got_sub)} 件、codex {len(got_cdx)} 件）")
    for problem in problems:
        print(f"    {problem}")
    return not problems


def check_places(skill: Path, project: Path, out: Path) -> bool:
    """もう一方の置き場の複製を、install.py --check が問題にし、skill_lint.py が本体の場所を見分け、カタログが要確認に出すか。"""
    import skill_lint  # noqa: E402
    install = [sys.executable, str(skill / "scripts/install.py"), "--project", str(project)]
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
    # 置き場自体がリンク（.claude/skills → .agents/skills）のプロジェクト
    import _skillrt as rt  # noqa: E402
    linked = project.parent / "linked"
    (linked / ".agents/skills").mkdir(parents=True, exist_ok=True)
    (linked / ".claude").mkdir(exist_ok=True)
    (linked / ".claude/skills").symlink_to("../.agents/skills", target_is_directory=True)
    body = linked / ".agents/skills" / skill.name
    shutil.copytree(skill, body, symlinks=True)
    if skill_lint.place_problem(body, _lib.load_spec(body), linked.resolve()):
        problems.append("置き場自体がリンクのとき、skill_lint.py が本体の場所を見分けない")
    if f".agents/skills/{skill.name}/**" not in rt.path_aliases(linked.resolve(), f".claude/skills/{skill.name}/**"):
        problems.append("置き場自体がリンクのとき、出力の照合が実体のパスを許さない")
    # Context Repository の共有正本は動かさず、対象製品の置き場からリンクする
    places = {"claude": ".claude/skills", "codex": ".agents/skills"}
    for targets in (["codex"], ["claude"], ["claude", "codex"], ["codex", "claude"]):
        label = ",".join(targets)
        shared = project.parent / ("shared-" + "-".join(targets))
        body = shared / "utils/skills/documentation" / skill.name
        shutil.copytree(skill, body, symlinks=True)
        spec = {**_lib.load_spec(body), "targets": targets}
        setup = [sys.executable, str(body / "scripts/install.py"), "--project", str(shared), "--targets", label]
        if _lib.run(setup, shared)[0] or skill_lint.place_problem(body, spec, shared):
            problems.append(f"共有正本への正しいリンクを skill_lint.py が通さない（{label}）")
        report = skill_lint.Report()
        skill_lint.check_final(body, spec, report, shared)
        if any(rule == "OUT-01" for rule, _ in report.errors):
            problems.append(f"共有正本のリンクと hooks が揃っても最終の配置検査が通らない（{label}）")
        for target in targets:
            link = shared / places[target] / skill.name
            saved = link.readlink()
            link.unlink()
            if not skill_lint.place_problem(body, spec, shared):
                problems.append(f"共有正本へのリンクが無くても通る（{label}: {target}）")
            wrong = shared / "other" / skill.name
            wrong.mkdir(parents=True, exist_ok=True)
            (wrong / "SKILL.md").write_text("別のスキル", encoding="utf-8")
            link.symlink_to(wrong, target_is_directory=True)
            if not skill_lint.place_problem(body, spec, shared):
                problems.append(f"共有正本と異なるリンクでも通る（{label}: {target}）")
            link.unlink()
            shutil.copytree(body, link, symlinks=True)
            if not skill_lint.place_problem(body, spec, shared):
                problems.append(f"共有正本へのリンクを複製に変えても通る（{label}: {target}）")
            shutil.rmtree(link)
            link.symlink_to(saved, target_is_directory=True)
        config = shared / (".codex/hooks.json" if targets[0] == "codex" else ".claude/settings.json")
        saved_config = config.read_text(encoding="utf-8")
        data = json.loads(saved_config)
        data["hooks"].pop("Stop")
        _lib.write_json(config, data)
        report = skill_lint.Report()
        skill_lint.check_final(body, spec, report, shared)
        if not any(rule == "OUT-01" and "hook がありません" in message for rule, message in report.errors):
            problems.append(f"共有正本の hooks の欠落を最終検査が問題にしない（{label}）")
        config.write_text(saved_config, encoding="utf-8")
        arbitrary = shared / "arbitrary" / skill.name
        arbitrary.parent.mkdir()
        body.rename(arbitrary)
        for target in targets:
            link = shared / places[target] / skill.name
            link.unlink()
            link.symlink_to(arbitrary, target_is_directory=True)
        if not skill_lint.place_problem(arbitrary, spec, shared):
            problems.append(f"utils/skills 以外の任意の本体をリンクだけで通す（{label}）")
        external = project.parent / ("external-" + "-".join(targets)) / skill.name
        external.parent.mkdir()
        arbitrary.rename(external)
        body.symlink_to(external, target_is_directory=True)
        for target in targets:
            link = shared / places[target] / skill.name
            link.unlink()
            link.symlink_to(body, target_is_directory=True)
        if not skill_lint.place_problem(body, spec, shared):
            problems.append(f"utils/skills 内のリンクからプロジェクト外の本体まで通す（{label}）")
    # 本体をプラグイン（plugins/<プラグイン>/skills/<name>）に置き、置き場には置かないプロジェクト
    shipped = project.parent / "shipped"
    plugin = shipped / "plugins/kit"
    body = plugin / "skills" / skill.name
    shutil.copytree(skill, body, symlinks=True)
    _lib.write_json(plugin / ".claude-plugin/plugin.json", {"name": "kit"})
    _lib.write_json(shipped / ".claude-plugin/marketplace.json", {"plugins": [{"name": "kit", "source": "./plugins/kit"}]})
    command = f'python3 "${{CLAUDE_PLUGIN_ROOT}}/skills/{skill.name}/scripts/hook.py" --platform claude'
    _lib.write_json(plugin / "hooks/hooks.json", {"hooks": {e: [{"hooks": [{"type": "command", "command": command}]}] for e in _lib.HOOK_EVENTS}})
    spec = _lib.load_spec(body)
    if skill_lint.place_problem(body, spec, shipped.resolve()) or _lib.plugin_skill_dirs(shipped) != [body]:
        problems.append("本体がプラグインにあり置き場に無いとき、skill_lint.py かカタログが本体を見分けない")
    if _lib.plugin_hook_events(plugin, "claude", skill.name) != sorted(_lib.HOOK_EVENTS) or _lib.plugin_hook_events(plugin, "codex", skill.name):
        problems.append("プラグインが配る hooks を、製品ごとに読み分けない")
    nested = project.parent / "shared-plugin"
    nested_plugin = nested / "utils/skills/kit"
    shutil.copytree(plugin, nested_plugin, symlinks=True)
    if skill_lint.place_problem(nested_plugin / "skills" / skill.name, spec, nested):
        problems.append("utils/skills 配下のプラグインの既存配置を、共有正本へのリンク欠落として拒否する")
    shutil.copytree(body, shipped / ".agents/skills" / skill.name)
    if not skill_lint.place_problem(body, spec, shipped.resolve()):
        problems.append("プラグインの本体と別に置き場に複製があるとき、skill_lint.py が問題にしない")
    print(f"{'成功' if not problems else '失敗'}  置き場の検査（リンク、複製、本体の場所、置き場自体のリンク、共有正本と hooks、プラグイン、カタログ）")
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
            results.append(step("eval_check.py", [py, str(scripts / "eval_check.py"), str(skill)], temp))
            results.append(check_catalog(skill, temp / "proj", temp / "catalog.html"))
            results.append(check_eval_questions(skill, temp / "proj", temp / "catalog.html"))
            results.append(check_settings(skill, temp / "proj"))
            results.append(step("convergence.py prepare（全課題）",
                                [py, str(scripts / "convergence.py"), "prepare", str(skill), "--round", "1",
                                 "--include-holdout", "--agents", "1", "--runners", "claude,codex,subagent",
                                 "--workdir", str(temp / "conv"), "--agents-dir", str(temp / "agents")], temp))
            results.append(results[-1] and check_untouched(temp))
            results.append(check_skip(skill, temp))
            results.append(results[-3] and check_fence(temp))
            results.append(results[-4] and check_codex_trace(temp))
            results.append(results[-5] and check_eval_scoring(skill, temp))
            results.append(check_places(skill, temp / "proj", temp / "twins.html"))
            results.append(check_analysis(skill, temp / "proj", temp))
            results.append(step("feedback_selftest.py（合成イベントによる収集・承認・Eval 接続）",
                                [py, str(scripts / "feedback_selftest.py")], temp))
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
