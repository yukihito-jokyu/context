"""skill-foundation の作成用スクリプトが共有する部品。Python 3.9 以上の標準ライブラリだけを使う。

実行時ランタイム（_skillrt.py、run.py、hook.py）とは分けてある。ランタイムは生成したスキルに写すが、
この部品は skill-foundation の中だけで使う。
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

FOUNDATION_DIR = Path(__file__).resolve().parent.parent
TEMPLATES = FOUNDATION_DIR / "assets" / "templates"
SPEC_REL = "dev/spec.json"
ORIGINAL_REL = "dev/original/SKILL.md"  # 後付け（mode: retrofit）で、元の SKILL.md を残す場所
EXISTING_SECTIONS = ["既存のスキル", "Existing skill"]  # 後付けで、dev/research.md に元のスキルの調べを書く節
RUNTIME_FILES = ["_skillrt.py", "run.py", "hook.py", "install.py"]
FIXTURE_NAME = "basic"  # dev/fixtures/ の下に置く唯一の fixture（課題ごとの違いは setup で作る）
TODO_MARKER = "TODO(" + "skill-foundation)"  # このファイル自体が --final の検査に掛からないよう分割する
LANGS = ["ja", "en"]
TARGETS = ["claude", "codex"]
NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
ID_RE = re.compile(r"^[A-Z]{2,5}-\d{2}$")
ID_IN_TEXT = re.compile(r"(?<![A-Z0-9-])[A-Z]{2,5}-\d{2}(?![\d-])")
PROBE_ID_RE = re.compile(r"^[A-Z]{2,5}-\d{2}-[a-z0-9]+$")

# 揺れの軸。記号 → (グループの接頭辞, 名前, 覆い方)。覆い方が "spec:<節>" の軸は spec のその節で答える
AXES = {
    "T1": ("TRG", "起動する依頼", "spec:triggers.use_when"),
    "T2": ("TRG", "起動しない依頼と代わり", "spec:triggers.not_for"),
    "T3": ("TRG", "自動で起動するか", "spec:triggers.implicit"),
    "I1": ("IN", "入力の項目と受け付ける書き方", "spec:inputs"),
    "I2": ("IN", "聞くか既定値で補うか", "spec:inputs"),
    "I3": ("IN", "対象外の依頼の扱い", "decision"),
    "I4": ("IN", "作業の前に読む範囲", "decision"),
    "P1": ("STEP", "手順の順序", "decision"),
    "P2": ("STEP", "分岐の条件", "decision"),
    "P3": ("STEP", "スクリプトに任せる処理", "decision"),
    "P4": ("STEP", "使う道具とコマンド", "decision"),
    "P5": ("STEP", "失敗したときの扱い", "decision"),
    "O1": ("OUT", "出力の置き場と名前", "decision"),
    "O2": ("OUT", "出力の構造", "decision"),
    "O3": ("OUT", "文体と用語", "decision"),
    "O4": ("OUT", "値の決め方（日付・ID・順序・数値）", "decision"),
    "O5": ("OUT", "出力の量", "decision"),
    "O6": ("OUT", "既にあるものの扱い", "decision"),
    "O7": ("OUT", "一緒に変えるファイルの組", "decision"),
    "O8": ("OUT", "検査を止める記法", "decision"),
    "R1": ("RPT", "最終の返答の形", "standard"),
    "C1": ("CTL", "実行の始まりと終わり", "standard"),
    "C2": ("CTL", "スキル自身の保護", "standard"),
    "C3": ("CTL", "質問の時機", "standard"),
    "C4": ("CTL", "自動実行（hooks）", "standard"),
    "C5": ("CTL", "契約の外の変更", "standard"),
}
PREFIXES = ["TRG", "IN", "STEP", "OUT", "RPT", "CTL"]
# 守らせ方の段（control-ladder.md の1章）。MACHINE は、守ったかどうかを機械が確かめる段
LEVELS = ["runtime", "format", "validate", "script", "template", "review", "doc"]
MACHINE = ["runtime", "format", "validate"]
RUNTIME_MARKS = ["run.py", "hook.py", "install.py", "_skillrt.py", "report.sections"]
# 機械で守らせない理由の種類。why_not_machine は「<種類>：<理由>」で始める（en は「<kind>: <reason>」）
WHY_NOT = {
    "trace": ("痕跡が残らない", "leaves no trace"),
    "meaning": ("意味の判断が要る", "needs judgment of meaning"),
    "cost": ("費用が見合わない", "not worth the cost"),
}
STANDARD_IDS = ["CTL-01", "CTL-02", "CTL-03", "CTL-04", "CTL-05", "RPT-01"]
# 答えの決め方（variance-axes.md の2章）。上から順に当てはめ、最初に当たったものを決定の basis に書く
BASES = {
    "user": ("依頼の指定", "the user's request"),
    "existing": ("後付けする既存のスキルの書き方", "the existing skill being retrofitted"),
    "project": ("プロジェクトの既存の決まり", "existing conventions of the project"),
    "official": ("出力を使う道具や形式の公式の決まり", "official rules of the tool or format"),
    "machine": ("機械で守らせられる答え", "the answer that machines can enforce"),
    "fewer-tools": ("道具・スクリプト・入力を増やさない答え", "the answer that adds no tools, scripts or inputs"),
    "fewer-concepts": ("AI の判断と覚える概念が少ない答え", "the answer with fewer judgments and concepts"),
    "common": ("最も普及している答え（好みで決めた）", "the most common answer (chosen by preference)"),
}
PREFERENCE_MARK = {"ja": "好みで決めた", "en": "chosen by preference"}
# 入力が無いまま既定値で進めたときの影響（control-ladder.md の3章）。ask・default・どちらも無し、を決める
IMPACTS = {
    "external": ("外に影響する・取り消せない（送信、公開、削除、課金）", "ask"),
    "target": ("作業の対象か目的を決め、プロジェクトからも読み取れない", "ask"),
    "reversible": ("既定値で進めても、出力を作り直せば済む", "default"),
    "optional": ("無くても出力が決まる", "none"),
}
MODES = ["new", "retrofit"]
PROFILES_PATH = FOUNDATION_DIR / "assets" / "skill-profiles.json"
EXAMPLES_DIR = "assets/examples"
SEAL_REL = "assets/seal.json"  # 封印。_skillrt.SEAL_REL と同じ

VAGUE_JA = ["なるべく", "できるだけ", "できる限り", "可能な限り", "可能であれば", "極力", "適切", "適宜", "必要に応じ",
            "基本的に", "原則として", "推奨", "望ましい", "場合による", "場合によって", "ケースバイケース",
            "状況に応じ", "柔軟に", "など", "等々", "その他", "いい感じ", "うまく", "よしなに"]
VAGUE_EN = [r"\bshould\b", r"\bprefer(?:ably|red)?\b", r"\brecommended\b", r"\bappropriate(?:ly)?\b",
            r"\bas needed\b", r"\bif possible\b", r"\bgenerally\b", r"\busually\b", r"\betc\b",
            r"\bwhere sensible\b", r"\bas appropriate\b"]
# 列挙が閉じていないかもしれない語。全部を列挙しているならそのままでよいので、警告にとどめる
OPEN_WORDS = [("を含む", r"を含む"), ("ほか", r"ほか(?!の)"), ("including", r"\bincluding\b"), ("such as", r"\bsuch as\b")]

SECTIONS = {
    "ja": ["1. 使う場面", "2. 手順", "3. 入力", "4. 決定表", "5. 出力の契約", "6. 完了前チェックリスト",
           "7. 報告", "8. 制御の仕組み"],
    "en": ["1. When to use", "2. Procedure", "3. Inputs", "4. Decisions", "5. Output contract",
           "6. Pre-completion checklist", "7. Report", "8. Control"],
}
BLOCKS = ["purpose", "triggers", "inputs", "decisions", "contract", "checklist", "report", "control"]
BLOCK_RE = re.compile(r"<!-- BEGIN GENERATED:([a-z]+) -->\n(.*?)<!-- END GENERATED:\1 -->", re.S)


def fail(message: str, code: int = 2) -> None:
    print(f"ERROR {message}", file=sys.stderr)
    sys.exit(code)


def load_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        fail(f"{path} がありません")
    except json.JSONDecodeError as exc:
        fail(f"{path} の JSON が不正です（{exc.lineno} 行目）: {exc.msg}")
    return {}


def write_json(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def load_spec(skill_dir: Path) -> dict:
    return load_json(skill_dir / SPEC_REL)


def labels(spec: dict) -> str:
    return spec.get("language") if spec.get("language") in LANGS else "en"


def plain_text(text: str) -> str:
    return re.sub(r"`[^`\n]*`", " ", re.sub(r"```.*?```", " ", text, flags=re.S))


def vague_words(text: str) -> list[str]:
    """あいまいな語。`` ` `` で囲んだコード片は除いて調べる。"""
    plain = plain_text(text)
    found = [w for w in VAGUE_JA if w in plain]
    found += [p for p in VAGUE_EN if re.search(p, plain, re.I)]
    return found


def open_words(text: str) -> list[str]:
    plain = plain_text(text)
    return [word for word, pattern in OPEN_WORDS if re.search(pattern, plain, re.I)]


def load_profiles() -> dict:
    return {k: v for k, v in load_json(PROFILES_PATH).items() if not k.startswith("_")}


def profile_axes(spec: dict) -> list[dict]:
    """種類（kind）の追加の軸を、spec の extra_axes の形（X1 から）にしたもの。"""
    profile = load_profiles().get(spec.get("kind"), {})
    return [{"axis": f"X{i}", "prefix": a["prefix"], "name": a["name"][labels(spec)]}
            for i, a in enumerate(profile.get("extra_axes", []), 1)]


def is_foundation(skill_dir: Path) -> bool:
    return skill_dir.resolve() == FOUNDATION_DIR.resolve()


def why_not_kind(text: str) -> str | None:
    """why_not_machine の先頭の種類（WHY_NOT のキー）。種類で始まっていなければ None。"""
    for key, words in WHY_NOT.items():
        if any(re.match(re.escape(w) + r"\s*[:：]", str(text).strip()) for w in words):
            return key
    return None


def research_items(skill_dir: Path) -> list[str]:
    """dev/research.md の項目（## か ### の見出しから次の見出しまで）。"""
    path = skill_dir / "dev/research.md"
    text = path.read_text(encoding="utf-8") if path.is_file() else ""
    return [m.group(0) for m in re.finditer(r"^#{2,3} .*?(?=^#{2,3} |\Z)", text, re.M | re.S)]


def research_ids(skill_dir: Path, existing: bool = False) -> set[str]:
    """dev/research.md の「使った決定」の行に書かれた決定の ID。existing なら「既存のスキル」の節だけを見る。"""
    path = skill_dir / "dev/research.md"
    text = path.read_text(encoding="utf-8") if path.is_file() else ""
    if existing:
        text = "\n".join(section(text, title) for title in EXISTING_SECTIONS)
    lines = [l for l in text.splitlines() if re.search(r"(使った決定|Used by)\s*[:：]", l)]
    return {rid for l in lines for rid in ID_IN_TEXT.findall(l)}


def yaml_quote(text: str) -> str:
    return '"' + text.replace("\\", "\\\\").replace('"', '\\"').replace("\n", " ") + '"'


def parse_frontmatter(text: str) -> tuple[dict, str] | tuple[None, str]:
    """SKILL.md の frontmatter を読む（1行1キーの単純な形だけ。render_skill.py が書く形）。"""
    if not text.startswith("---\n"):
        return None, text
    end = text.find("\n---\n", 4)
    if end == -1:
        return None, text
    data = {}
    for line in text[4:end].splitlines():
        match = re.match(r"^([A-Za-z0-9_\-]+):\s*(.*)$", line)
        if not match:
            continue
        value = match.group(2).strip()
        if value.startswith('"') and value.endswith('"') and len(value) >= 2:
            value = json.loads(value) if "\\" in value or '"' in value[1:-1] else value[1:-1]
        data[match.group(1)] = value
    return data, text[end + 5:]


def blocks(text: str) -> dict:
    return {m.group(1): m.group(2) for m in BLOCK_RE.finditer(text)}


def replace_block(text: str, block_id: str, content: str) -> str:
    body = content if content.endswith("\n") else content + "\n"
    pattern = re.compile(r"(<!-- BEGIN GENERATED:" + block_id + r" -->\n).*?(<!-- END GENERATED:" + block_id + r" -->)", re.S)
    if not pattern.search(text):
        raise KeyError(block_id)
    return pattern.sub(lambda m: m.group(1) + body + m.group(2), text, count=1)


def strip_blocks(text: str) -> str:
    """生成した部分を除いた、手で書いた部分だけ。"""
    return BLOCK_RE.sub("", text)


def h2_titles(text: str) -> list[str]:
    titles, inside = [], False
    for line in text.splitlines():
        if line.lstrip().startswith("```"):
            inside = not inside
            continue
        if not inside and line.startswith("## "):
            titles.append(line[3:].strip())
    return titles


def section(text: str, title: str) -> str:
    """見出し `## title` から次の `## ` までの本文。"""
    match = re.search(r"^## " + re.escape(title) + r"\s*\n(.*?)(?=^## |\Z)", text, re.M | re.S)
    return match.group(1) if match else ""


def iter_files(root: Path, skip: tuple = (".git", "__pycache__", ".skill-runs", "node_modules")) -> list[str]:
    found = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames if d not in skip)
        for f in filenames:
            found.append((Path(dirpath) / f).relative_to(root).as_posix())
    return sorted(found)


def copy_tree(src: Path, dst: Path, exclude: tuple = ("__pycache__", ".skill-runs", ".DS_Store")) -> None:
    shutil.copytree(src, dst, symlinks=False, ignore=shutil.ignore_patterns(*exclude))


def run(command, cwd: Path, timeout: int = 60, env: dict | None = None, stdin: str | None = None) -> tuple[int, str]:
    try:
        proc = subprocess.run(command, cwd=cwd, shell=isinstance(command, str), capture_output=True, text=True,
                              timeout=timeout, env=env, input=stdin)
        return proc.returncode, (proc.stdout or "") + (proc.stderr or "")
    except subprocess.TimeoutExpired:
        return 124, f"[timeout] {timeout} 秒で打ち切りました"
    except FileNotFoundError as exc:
        return 127, str(exc)


def git_init(directory: Path, message: str = "base") -> bool:
    if shutil.which("git") is None:
        return False
    git = ["git", "-c", "user.name=skill-foundation", "-c", "user.email=skill-foundation@localhost",
           "-c", "commit.gpgsign=false", "-c", "core.hooksPath=/dev/null"]
    for args in (["init", "-q"], ["add", "-A"], ["commit", "-q", "--allow-empty", "-m", message]):
        code, _ = run(git + args, directory)
        if code != 0:
            return False
    return True


def tail(text: str, lines: int = 20) -> str:
    return "\n".join(text.rstrip().splitlines()[-lines:])
