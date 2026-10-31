"""skill-foundation の作成用スクリプトが共有する部品。Python 3.9 以上の標準ライブラリだけを使う。

実行時ランタイム（_skillrt.py、run.py、hook.py）とは分けてある。ランタイムは生成したスキルに写すが、
この部品は skill-foundation の中だけで使う。
"""

from __future__ import annotations

import hashlib
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
RUNTIME_FILES = ["_skillrt.py", "run.py", "hook.py", "install.py", "feedback.py", "feedback_review.py"]
FIXTURE_NAME = "basic"  # dev/fixtures/ の下に置く唯一の fixture（課題ごとの違いは setup で作る）
TODO_MARKER = "TODO(" + "skill-foundation)"  # このファイル自体が --final の検査に掛からないよう分割する
LANGS = ["ja", "en"]
TARGETS = ["claude", "codex"]
NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
ID_RE = re.compile(r"^[A-Z]{2,5}-\d{2}$")
ID_IN_TEXT = re.compile(r"(?<![A-Z0-9-])[A-Z]{2,5}-\d{2}(?![\d-])")
PROBE_ID_RE = re.compile(r"^[A-Z]{2,5}-\d{2}-[a-z0-9]+$")
ANALYSIS_FITS = ["ok", "detour", "waste", "wrong"]  # AI の分析の、操作ごとの当てはまり（convergence.py が確かめ、catalog.py が出す）
ANALYSIS_VERDICTS = ["good", "fair", "poor"]  # AI の分析の、流れ全体の評価
FINDINGS_TITLES = ["動きの指摘", "Behavior findings"]  # convergence-report.md の、AI の分析の指摘を締め込みで分類した表の節
FINDING_CLASSES = [f"V{i}" for i in range(1, 9)] + ["推定違い", "misread"]  # 動きの指摘の分類（ばらつきの分類か、記録と合わない推定）

# ばらつきの軸。記号 → (グループの接頭辞, 名前, 覆い方)。覆い方が "spec:<節>" の軸は spec のその節で答える
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
    "C3": ("CTL", "質問の時機", "standard"),
    "C4": ("CTL", "自動実行（hooks）", "standard"),
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
STANDARD_IDS = ["CTL-01", "CTL-02", "CTL-03", "CTL-04", "RPT-01"]
# 決めた根拠（variance-axes.md の2章）。上から順に当てはめ、最初に当たったものをルールの basis に書く
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
CATALOG_REL = ".skill-runs/catalog.html"  # catalog.py が書くカタログの一覧。収束テストは、ほかの出力から作る図なので数えない
CATALOG_PAGES_REL = ".skill-runs/catalog"  # 一覧の隣の、スキルごとのページ（<名前>.html）。数えないのは一覧と同じ

VAGUE_JA = ["なるべく", "できるだけ", "できる限り", "可能な限り", "可能であれば", "極力", "適切", "適宜", "必要に応じ",
            "基本的に", "原則として", "推奨", "望ましい", "場合による", "場合によって", "ケースバイケース",
            "状況に応じ", "柔軟に", "など", "等々", "その他", "いい感じ", "うまく", "よしなに"]
VAGUE_EN = [r"\bshould\b", r"\bprefer(?:ably|red)?\b", r"\brecommended\b", r"\bappropriate(?:ly)?\b",
            r"\bas needed\b", r"\bif possible\b", r"\bgenerally\b", r"\busually\b", r"\betc\b",
            r"\bwhere sensible\b", r"\bas appropriate\b"]
# 列挙が閉じていないかもしれない語。全部を列挙しているならそのままでよいので、警告にとどめる
OPEN_WORDS = [("を含む", r"を含む"), ("ほか", r"ほか(?!の)"), ("including", r"\bincluding\b"), ("such as", r"\bsuch as\b")]

SECTIONS = {
    "ja": ["1. 使う場面", "2. 手順", "3. 入力", "4. ルール", "5. 出力の契約", "6. 完了前チェックリスト",
           "7. 報告", "8. 制御の仕組み"],
    "en": ["1. When to use", "2. Procedure", "3. Inputs", "4. Rules", "5. Output contract",
           "6. Pre-completion checklist", "7. Report", "8. Control"],
}
OLD_SECTIONS = {"4. 決定表": "4. ルール", "4. Decisions": "4. Rules"}  # 改めた見出し。古いスキルに直し方を示す
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


HOOK_EVENTS = ["PreToolUse", "PostToolUse", "Stop", "UserPromptSubmit"]  # install.py が登録するイベント。プラグインで配るときも同じ
PLUGIN_MANIFESTS = {"claude": ".claude-plugin/plugin.json", "codex": ".codex-plugin/plugin.json"}


def plugin_root(skill_dir: Path) -> Path | None:
    """本体が <プラグイン>/skills/<name> にあり、そのプラグインにマニフェストがあれば、プラグインのディレクトリ。"""
    body = skill_dir.resolve()
    root = body.parent.parent
    if body.parent.name == "skills" and any((root / m).is_file() for m in PLUGIN_MANIFESTS.values()):
        return root
    return None


def plugin_hook_events(plugin: Path, platform: str, name: str) -> list[str]:
    """プラグインが配る hooks のうち、このスキルの hook.py を platform 向けに呼ぶイベント。
    Claude Code は .claude-plugin/plugin.json の hooks（無ければ hooks/hooks.json）、Codex は .codex-plugin/plugin.json の hooks を読む。"""
    try:
        manifest = json.loads((plugin / PLUGIN_MANIFESTS[platform]).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        manifest = {}
    hooks = manifest.get("hooks", "hooks/hooks.json" if platform == "claude" else {}) if isinstance(manifest, dict) else {}
    if isinstance(hooks, str):  # プラグインのルートからの相対パス
        try:
            hooks = json.loads((plugin / hooks).read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return []
    events = hooks.get("hooks", {}) if isinstance(hooks, dict) else {}
    script, flag = f"/{name}/scripts/hook.py", f"--platform {platform}"
    return sorted(event for event, groups in (events.items() if isinstance(events, dict) else []) if isinstance(groups, list)
                  and any(script in str(h.get("command", "")) and flag in str(h.get("command", ""))
                          for g in groups if isinstance(g, dict) for h in g.get("hooks", []) if isinstance(h, dict)))


MARKETPLACES = [".claude-plugin/marketplace.json", ".agents/plugins/marketplace.json"]  # source（Codex は source.path）はルートからの相対パス


def plugin_skill_dirs(project: Path) -> list[Path]:
    """プロジェクトのマーケットプレイスに載る、プロジェクトの中のプラグインの skills/ の下のスキル。"""
    found = []
    for rel in MARKETPLACES:
        try:
            plugins = json.loads((project / rel).read_text(encoding="utf-8")).get("plugins", [])
        except (OSError, ValueError, AttributeError):
            continue
        for entry in plugins if isinstance(plugins, list) else []:
            source = entry.get("source") if isinstance(entry, dict) else None
            path = source.get("path") if isinstance(source, dict) else source
            if isinstance(path, str) and path.startswith("./"):
                found += [d for d in sorted((project / path / "skills").glob("*")) if (d / "SKILL.md").is_file() and d not in found]
    return found


def actions_hash(actions: list) -> str:
    """traces.json の1人分の操作（道具・入力・成否）のハッシュ。AI の分析が、今の記録を読んだものかを確かめる。"""
    keep = [[a.get("tool"), a.get("input"), a.get("ok")] for a in actions if isinstance(a, dict)]
    return hashlib.sha256(json.dumps(keep, ensure_ascii=False).encode("utf-8")).hexdigest()[:16]


def stale_analyses(skill_dir: Path, rnd: int) -> list[str]:
    """ラウンド rnd の、操作の記録があるのに AI の分析が無いか、記録（traces.json）を取り直す前の分析のエージェント。"""
    rdir = skill_dir / f"dev/results/convergence/round-{rnd}"
    if not (rdir / "traces.json").is_file():
        return []
    runs = {rid: run for rid, run in load_json(rdir / "traces.json").get("runs", {}).items() if run.get("actions")}
    done = load_json(rdir / "analysis.json").get("runs", {}) if (rdir / "analysis.json").is_file() else {}
    return sorted(rid for rid, run in runs.items() if done.get(rid, {}).get("based_on") != actions_hash(run["actions"]))


def finding_rows(report: str, rnd: int) -> list[list[str]]:
    """convergence-report.md の「動きの指摘」の表のうち、ラウンドの列が rnd の行（セルの列）。"""
    body = "".join(section(report, title) for title in FINDINGS_TITLES)
    rows = [[c.strip() for c in line.strip().strip("|").split("|")] for line in body.splitlines() if line.strip().startswith("|")]
    return [row for row in rows if row[0] == str(rnd)]


def uncited_findings(skill_dir: Path, rnd: int, report: str) -> list[str]:
    """ラウンド rnd の AI の分析を、締め込みで分類した記録（convergence-report.md の「動きの指摘」の表）が足りないところ。
    指摘があるのに表のどの行にも出ないエージェントと、分類か対処の列が埋まっていない行。"""
    path = skill_dir / f"dev/results/convergence/round-{rnd}/analysis.json"
    if not path.is_file():
        return []
    rows, problems = finding_rows(report, rnd), []
    for row in rows:
        classes = [c for c in re.split(r"[・、,/\s]+", row[3]) if c] if len(row) >= 5 else []
        if not classes or any(c not in FINDING_CLASSES for c in classes) or not row[4]:
            problems.append(f"ラウンド {rnd} の行「{row[1][:40] if len(row) > 1 else ''}」の分類（V1〜V8 か推定違い）か対処が埋まっていません")
    cited = " ".join(row[1] for row in rows if len(row) > 1)
    missing = sorted(rid for rid, a in load_json(path).get("runs", {}).items()
                     if a.get("flow", {}).get("issues") and not re.search(re.escape(rid) + r"(?![\w-])", cited))
    if missing:
        problems.append(f"ラウンド {rnd} の AI の分析に指摘があるのに、「動きの指摘」の表のどの行にも無いエージェントがいます（"
                        + ", ".join(missing[:4]) + (f" ほか {len(missing) - 4} 件" if len(missing) > 4 else "") + "）")
    return problems


def load_spec(skill_dir: Path) -> dict:
    return load_json(skill_dir / SPEC_REL)


# 収束テストの動かし方（skill-foundation の settings/ の convergence）。項目 → 値の種類。入れ子は項目の組
CONVERGENCE_SETTINGS = {
    "runners": "runners", "agents": "count", "max_rounds": "count",
    "thresholds": {"files": "rate", "structure": "rate", "names": "rate"},
    "model": {"claude": "text", "codex": "text", "subagent": "text"},
    "effort": {"claude": "text", "codex": "text", "subagent": "text"},
    "analysis": {"runner": "runner", "model": "text", "effort": "text"},
    "parallel": "count", "timeout": "count",
}
CONVERGENCE_REQUIRED = ["runners", "agents", "max_rounds", "thresholds.files", "thresholds.structure", "thresholds.names",
                        "parallel", "timeout"]  # どの層にも無いと収束テストを動かせない項目
CONVERGENCE_RUNNERS = ["claude", "codex", "subagent"]
SETTING_SOURCES = {"args": "引数", "spec": "dev/spec.json の convergence", "user": "ユーザーの設定 settings/user-setting.yaml",
                   "skill": "スキルの設定 settings/skill-setting.yaml"}


def setting_problem(kind: str, value) -> str | None:
    """設定の値が種類に合わないときの説明。null は「値なし」なので合う。"""
    if value is None:
        return None
    number = isinstance(value, (int, float)) and not isinstance(value, bool)
    if kind == "runners":
        ok = isinstance(value, list) and bool(value) and all(v in CONVERGENCE_RUNNERS for v in value)
        return None if ok else f"{CONVERGENCE_RUNNERS} から選んだ一覧にしてください"
    if kind == "runner":
        return None if value in CONVERGENCE_RUNNERS else f"{CONVERGENCE_RUNNERS} のどれかにしてください"
    if kind == "count":
        return None if number and value == int(value) and value >= 1 else "1 以上の整数にしてください"
    if kind == "rate":
        return None if number and 0 <= value <= 1 else "0 から 1 の数にしてください"
    return None if isinstance(value, str) and value.strip() else "空でない文字列にしてください"


def convergence_problems(data, shape: dict = CONVERGENCE_SETTINGS, prefix: str = "convergence") -> list[str]:
    """設定の convergence の誤り（設定に無い項目、種類に合わない値）。"""
    if not isinstance(data, dict):
        return [f"{prefix} はオブジェクトにしてください"]
    problems = []
    for key, value in data.items():
        where = f"{prefix}.{key}"
        if key not in shape:
            problems.append(f"{where} は設定の項目にありません（{', '.join(shape)}）")
        elif isinstance(shape[key], dict):
            problems += convergence_problems(value, shape[key], where) if value is not None else []
        elif setting_problem(shape[key], value):
            problems.append(f"{where}: {setting_problem(shape[key], value)}")
    return problems


def setting_files() -> tuple[list[tuple[str, dict]], list[str]]:
    """skill-foundation の settings/ の設定を強い順に（ユーザーの設定 → スキルの設定）と、convergence の誤り。"""
    import _skillrt
    layers, warnings = _skillrt.load_settings(FOUNDATION_DIR)
    rels = dict(_skillrt.SETTINGS_FILES)
    for source, data in layers:
        warnings += [f"{rels[source]}: {p}（この値は使わない）" for p in convergence_problems(data.get("convergence") or {})]
    return layers, warnings


def convergence_settings(spec: dict, args: dict | None = None) -> tuple[dict, dict, list[str]]:
    """収束テストの動かし方、項目ごとの出どころ（SETTING_SOURCES のキー）、設定の誤り。
    引数 → 作るスキルの spec の convergence → ユーザーの設定 → スキルの設定 の順に、null でなく種類に合う最初の値を使う。"""
    files, warnings = setting_files()
    layers = [("args", args or {}), ("spec", spec.get("convergence") or {})]
    layers += [(source, data.get("convergence") or {}) for source, data in files]
    sources: dict = {}

    def pick(shape: dict, layers: list, prefix: str) -> dict:
        values = {}
        for key, kind in shape.items():
            here = [(source, data.get(key)) for source, data in layers if isinstance(data, dict)]
            if isinstance(kind, dict):
                values[key] = pick(kind, here, f"{prefix}{key}.")
                continue
            values[key] = None
            for source, value in here:
                if value is not None and not setting_problem(kind, value):
                    values[key], sources[prefix + key] = value, source
                    break
        return values

    return pick(CONVERGENCE_SETTINGS, layers, ""), sources, warnings


def setting_value(values: dict, path: str):
    for key in path.split("."):
        values = values.get(key) if isinstance(values, dict) else None
    return values


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
    """dev/research.md の「使ったルール」の行に書かれたルールID。existing なら「既存のスキル」の節だけを見る。"""
    path = skill_dir / "dev/research.md"
    text = path.read_text(encoding="utf-8") if path.is_file() else ""
    if existing:
        text = "\n".join(section(text, title) for title in EXISTING_SECTIONS)
    lines = [l for l in text.splitlines() if re.search(r"(使ったルール|使った決定|Used by)\s*[:：]", l)]
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
