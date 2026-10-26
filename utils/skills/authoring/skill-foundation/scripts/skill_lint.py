#!/usr/bin/env python3
"""skill-foundation で作ったスキルを検査する。誰が作っても同じ形になっていることを、機械で確かめる。

検査はフェーズに合わせて増える。--phase を省くと、spec の status が ready なら --final、building なら 5。
  1: ディレクトリの形、ファイル名、spec の受付の項目、ランタイムが skill-foundation の版と同一
  3: 1 に加えて決定（ID・番号・軸・必須項目・あいまいな語・決定表）、軸の網羅、標準の決定、入力
  4: 3 に加えて出力の契約、検査と決定の対応、probe の書式、見本（assets/examples/ と baseline の from）、
     スクリプトの --help、生成物が最新
  5: 4 に加えて SKILL.md（frontmatter、節の並び、手順の書き方と見本の記載、行数、リンク）、doc の決定の記載
  --final: 5 に加えて TODO の目印、調査の未確認、評価課題、probe の結果、収束テストの記録、status: ready
  --gate : status が building ならフェーズ1だけ、ready なら --final（hooks から呼ぶ）

使い方:
  python3 skill_lint.py <スキルのディレクトリ> [--phase 1|3|4|5] [--final] [--gate] [--project <ルート>] [--seal]
  --project: --final のとき、そのプロジェクトに置き場所と hooks が揃っているかも調べる
  --seal   : --final でエラーが無ければ、保護ファイルのハッシュを assets/seal.json に書く（封印。CTL-02）
"""

from __future__ import annotations

import argparse
import hashlib
import json
import py_compile
import re
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _lib  # noqa: E402
import _skillrt as rt  # noqa: E402
import init_skill  # noqa: E402
import render_skill  # noqa: E402

TOP_LEVEL = {"SKILL.md", "LICENSE", "LICENSE.txt", "scripts", "references", "assets", "dev", ".DS_Store"}
INPUT_TYPES = ["string", "int", "bool", "list", "enum", "path", "slug"]
CHECK_FIELDS = {"headings": [], "require": ["pattern"], "forbid": ["pattern"], "max_lines": ["value"],
                "min_lines": ["value"], "line_length": ["max"], "json_schema": ["schema"],
                "front_matter": ["required_keys"], "command": ["run"]}
OTHERWISE = ("上のどれでもない", "otherwise")
FM_KEYS = {"name", "description", "disable-model-invocation"}
CHECKING = {"runtime", "format", "validate", "review", "doc"}  # 守ったかを確かめる段。script と template は渡すだけ
NETWORK = re.compile(r"^\s*(?:import|from)\s+(?:socket|ssl|urllib\.request|http\.client|requests|httpx|aiohttp|ftplib|smtplib)\b"
                     r"|^\s*from\s+urllib\s+import\s+request\b", re.M)
UNSTABLE = re.compile(r"\b(?:import\s+random|from\s+random\s+import|uuid\.uuid[14]|datetime\.now|datetime\.today|date\.today|time\.time\()")
DECISION_ID_IN_TEXT = re.compile(r"(?<![A-Za-z0-9-])(?:" + "|".join(_lib.PREFIXES) + r")-\d{2}(?![\d-])")


class Report:
    """errors は（決定の ID か None, 文）の組。ID は skill-foundation のどの決定を守らせる検査かを示す
    （--rule のとき行頭に出す。None は --rule の値）。"""

    def __init__(self):
        self.errors, self.warnings = [], []

    def error(self, where: str, message: str, rule: str | None = None) -> None:
        self.errors.append((rule, f"{where}: {message}"))

    def warn(self, where: str, message: str) -> None:
        self.warnings.append(f"{where}: {message}")


def probes_hash(skill_dir: Path) -> str:
    """probe の結果が最新かを判定するハッシュ。probe・契約・ランタイムのどれかが変われば変わる。"""
    digest = hashlib.sha256()
    for rel in ["dev/probes.json", "assets/contract.json", *[f"scripts/{s}" for s in _lib.RUNTIME_FILES]]:
        path = skill_dir / rel
        digest.update(rel.encode() + b"\0" + (path.read_bytes() if path.is_file() else b""))
    return digest.hexdigest()


# ---------------------------------------------------------------- フェーズ1

def check_structure(skill_dir: Path, spec: dict, r: Report) -> None:
    for error in init_skill.intake_errors(spec, skill_dir):
        rule = "OUT-05" if "use_when" in error else ("OUT-04" if error.startswith("name") else None)
        r.error("dev/spec.json", error, rule=rule)
    for entry in sorted(p.name for p in skill_dir.iterdir()):
        if entry not in TOP_LEVEL:
            r.error(entry, f"スキルの直下に置けるのは {sorted(TOP_LEVEL - {'.DS_Store'})} だけです", rule="OUT-02")
    required = ["SKILL.md", "assets/contract.json", "references/decisions.md", "dev/research.md", "dev/evals.json",
                "dev/probes.json", "dev/convergence-report.md", *[f"scripts/{s}" for s in _lib.RUNTIME_FILES]]
    for rel in required:
        if not (skill_dir / rel).is_file():
            r.error(rel, "ありません（init_skill.py と render_skill.py で作る）", rule="OUT-02")
    if spec.get("mode") == "retrofit":
        if not (skill_dir / _lib.ORIGINAL_REL).is_file():
            r.error(_lib.ORIGINAL_REL, "ありません。後付けでは元の SKILL.md をここに残す（init_skill.py が移す）", rule="OUT-06")
        research = (skill_dir / "dev/research.md").read_text(encoding="utf-8") if (skill_dir / "dev/research.md").is_file() else ""
        if not any(_lib.section(research, t).strip() for t in _lib.EXISTING_SECTIONS):
            r.error("dev/research.md", "後付けなので「## 既存のスキル」の節に、元のスキルの手順・入力・出力を書いてください", rule="OUT-06")
    for script in _lib.RUNTIME_FILES:
        mine, theirs = skill_dir / "scripts" / script, _lib.FOUNDATION_DIR / "scripts" / script
        if mine.is_file() and theirs.is_file() and mine.read_bytes() != theirs.read_bytes() and mine.resolve() != theirs.resolve():
            r.error(f"scripts/{script}", "ランタイムが skill-foundation の版と違います。スキルごとに書き換えない"
                                         "（init_skill.py --update-runtime で戻す）", rule="OUT-02")
    for rel in _lib.iter_files(skill_dir):
        parts = rel.split("/")
        if parts[0] == "scripts" and len(parts) == 2 and not re.fullmatch(r"[a-z0-9_]+\.(py|sh)|_skillrt\.py", parts[1]):
            r.error(rel, "scripts/ のファイル名は snake_case の .py か .sh にしてください", rule="OUT-02")
        if parts[0] == "references" and not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*\.md", parts[-1]):
            r.error(rel, "references/ のファイル名は kebab-case の .md にしてください", rule="OUT-02")
        if parts[0] == "references" and len(parts) > 2:
            r.error(rel, "references/ は1階層にしてください（SKILL.md から直接リンクする）", rule="OUT-02")


# ---------------------------------------------------------------- フェーズ3

def check_from(skill_dir: Path, where: str, change: dict, r: Report) -> None:
    """probe の files の from（中身をスキルの見本から写す）。"""
    if "from" not in change:
        return
    src = str(change["from"])
    if not src.startswith(_lib.EXAMPLES_DIR + "/") or not (skill_dir / src).is_file():
        r.error(where, f"from は {_lib.EXAMPLES_DIR}/ の下の実在するファイルにしてください（今: {src}）", rule="OUT-02")
    if "content" in change or change.get("mode", "create") not in ("create", "replace"):
        r.error(where, "from は mode が create か replace のときだけ使い、content と一緒に書かないでください", rule="OUT-02")


def check_changes(skill_dir: Path, where: str, changes: list, r: Report) -> None:
    """probe と reviews の files（違反を入れるファイル）。"""
    if not changes:
        r.error(where, "files（違反を入れるファイル）がありません")
    for change in changes:
        if change.get("mode", "create") not in ("create", "replace", "append", "delete", "sub"):
            r.error(where, "mode は create・replace・append・delete・sub のどれかにしてください")
        elif change.get("mode") == "sub" and not change.get("pattern"):
            r.error(where, "mode が sub なので pattern（置き換える正規表現）を書いてください")
        check_from(skill_dir, where, change, r)


def axis_info(spec: dict) -> dict:
    info = {code: {"prefix": v[0], "name": v[1], "cover": v[2]} for code, v in _lib.AXES.items()}
    for extra in spec.get("extra_axes", []):
        info[extra.get("axis", "")] = {"prefix": extra.get("prefix"), "name": extra.get("name"), "cover": "decision"}
    return info


def axis_order(spec: dict) -> list[str]:
    return list(_lib.AXES) + [e.get("axis", "") for e in spec.get("extra_axes", [])]


def retired(decision: dict) -> bool:
    return bool(str(decision.get("retired", "")).strip())


def project_backed(skill_dir: Path, rid: str) -> bool:
    """basis: project の根拠。調査の項目が、この ID を使った決定に挙げ、決まりの場所か書き方の分布（件数）を持つ。"""
    for item in _lib.research_items(skill_dir):
        used = [l for l in item.splitlines() if re.search(r"(使った決定|Used by)\s*[:：]", l)]
        if not any(rid in _lib.ID_IN_TEXT.findall(l) for l in used):
            continue
        if re.search(r"^- (決まり|Rule)\s*[:：]\s*\S", item, re.M) or re.search(r"^- (分布|Distribution)\s*[:：].*\d", item, re.M):
            return True
    return False


def check_decisions(skill_dir: Path, spec: dict, r: Report) -> None:
    decisions = spec.get("decisions", [])
    info = axis_info(spec)
    order = axis_order(spec)
    lang = _lib.labels(spec)
    for i, extra in enumerate(spec.get("extra_axes", []), 1):
        if extra.get("axis") != f"X{i}" or not extra.get("name") or extra.get("prefix") not in _lib.PREFIXES:
            r.error("dev/spec.json extra_axes", f"{i} 番目は axis: X{i}、name、prefix（{_lib.PREFIXES} のどれか）を持たせてください")
    seen, covered = set(), set()
    by_prefix: dict[str, list[dict]] = {}
    by_first: dict[tuple, list[str]] = {}
    official = _lib.research_ids(skill_dir)
    existing = _lib.research_ids(skill_dir, existing=True)
    for d in decisions:
        rid = d.get("id", "")
        where = f"decision {rid or '(id なし)'}"
        if not _lib.ID_RE.match(rid):
            r.error(where, "id は <接頭辞>-<2桁の番号> にしてください（例: OUT-03）", rule="OUT-04")
            continue
        if rid in seen:
            r.error(where, "id が重複しています", rule="OUT-04")
        seen.add(rid)
        prefix = rid.split("-")[0]
        if prefix not in _lib.PREFIXES:
            r.error(where, f"接頭辞は {_lib.PREFIXES} のどれかにしてください", rule="OUT-04")
        by_prefix.setdefault(prefix, []).append(d)
        axes = d.get("axes", [])
        if retired(d):  # 廃止した決定は ID を残すだけ。番号の連続と順序にだけ数える
            if not str(d.get("title", "")).strip() or not axes:
                r.error(where, "廃止した決定にも title と axes を残してください（ID を辿れるようにする）")
            continue
        for field in ("title", "decision", "reason", "how", "good", "bad"):
            if not str(d.get(field, "")).strip():
                r.error(where, f"{field} がありません")
        basis = d.get("basis")
        if basis not in _lib.BASES:
            r.error(where, f"basis（答えの決め方）を {list(_lib.BASES)} のどれかにしてください（variance-axes.md の2章）")
        elif basis == "existing" and spec.get("mode", "new") != "retrofit":
            r.error(where, "basis: existing は後付け（mode: retrofit）のスキルだけで使えます")
        elif basis == "existing" and rid not in existing:
            r.error(where, "basis が existing なので、dev/research.md の「## 既存のスキル」の「使った決定」の行にこの ID を書いてください")
        elif basis == "project" and not project_backed(skill_dir, rid):
            r.error(where, "basis が project なので、dev/research.md の項目の「使った決定」にこの ID を書き、同じ項目に「- 決まり：」"
                           "（書いてある場所）か「- 分布：」（書き方ごとの件数と、数えたコマンド）を書いてください（research.md の3章）")
        elif basis == "official" and rid not in official:
            r.error(where, "basis が official なので、dev/research.md の「使った決定」の行にこの ID を書き、出典を示してください")
        elif basis == "common" and _lib.PREFERENCE_MARK[lang] not in str(d.get("reason", "")):
            r.error(where, f"basis が common なので、reason に「{_lib.PREFERENCE_MARK[lang]}」と書いてください")
        if not axes:
            r.error(where, "axes がありません")
        for axis in axes:
            if axis not in info:
                r.error(where, f"軸 {axis} はカタログにも extra_axes にもありません")
        if axes and all(a in info for a in axes) and prefix not in {info[a]["prefix"] for a in axes}:
            r.error(where, f"接頭辞 {prefix} が、軸 {axes} のグループ（{sorted({info[a]['prefix'] for a in axes})}）と合いません", rule="OUT-04")
        covered.update(axes)
        if axes:
            group = by_first.setdefault((axes[0], tuple(sorted(d.get("control", [])))), [])
            if group and not str(d.get("split_reason", "")).strip():
                r.error(where, f"{group[0]} と最初の軸（{axes[0]}）も守らせ方も同じです。1つの決定にまとめるか、"
                               "片方だけ破られうる理由を split_reason に書いてください（variance-axes.md の3章）")
            group.append(rid)
        for word in sorted(set(_lib.open_words(str(d.get("decision", ""))))):
            r.warn(where, f"「{word}」は列挙が閉じていない可能性があります。全部を列挙しているならそのままでよい")
        control = d.get("control", [])
        unknown = [c for c in control if c not in _lib.LEVELS]
        if not control or unknown:
            r.error(where, f"control は {_lib.LEVELS} から1つ以上にしてください")
        elif not set(control) & CHECKING:
            r.error(where, "script と template は値や形を渡すだけで、守ったかを確かめません。runtime・format・validate・review・doc の"
                           "どれかと一緒に書いてください（control-ladder.md の1章）")
        why = str(d.get("why_not_machine", "")).strip()
        if control and not set(control) & set(_lib.MACHINE):
            kind = _lib.why_not_kind(why)
            names = "・".join(w[0] for w in _lib.WHY_NOT.values())
            if kind is None:
                r.error(where, f"control に runtime・format・validate が無いので、why_not_machine を「<種類>：<理由>」の形で書いてください"
                               f"（種類は {names} のどれか。control-ladder.md の1章）")
            elif kind == "trace" and "review" in control:
                r.error(where, "違反が出力に痕跡を残さないなら、出力を見て確かめる review ではなく doc にしてください（control-ladder.md の1章）")
            elif kind == "meaning" and "review" not in control:
                r.error(where, "意味の判断が要る違反は出力を見れば分かるので、review を含めてください（control-ladder.md の1章）")
        texts = [d.get("decision", "")] + [c for row in d.get("table", [])[1:] for c in row]
        for word in sorted(set(w for t in texts for w in _lib.vague_words(str(t)))):
            r.error(where, f"決定にあいまいな語「{word}」があります。条件と答えで書いてください", rule="OUT-03")
        table = d.get("table")
        if table is not None:
            if not isinstance(table, list) or len(table) < 3 or len({len(row) for row in table}) != 1:
                r.error(where, "table は [見出しの行, 行, 行, ...] の形で、行を2つ以上、列の数を揃えてください")
            elif not str(table[-1][0]).startswith(OTHERWISE):
                r.error(where, f"table の最後の行の1列目は「{OTHERWISE[0]}」で始めてください（どの行にも当たらない入力を無くす）")
    # 番号の振り方: 接頭辞ごとに 01 から連番、カタログの軸の順
    standard = {d["id"]: d for d in init_skill.standard_decisions(_lib.labels(spec))}
    for prefix, items in by_prefix.items():
        numbers = sorted(int(d["id"].split("-")[1]) for d in items)
        if numbers != list(range(1, len(numbers) + 1)):
            r.error(f"decision {prefix}-*", f"番号は 01 から欠けなく振ってください（今: {numbers}）。決定を消したなら、"
                                            "消さずに retired に理由を書いて残してください（ID を再利用しない）", rule="OUT-04")
        # 廃止した決定と、ready にした後に足した決定（末尾の番号）は、軸の順を問わない。ID を変えないため
        custom = sorted((d for d in items if d["id"] not in standard and not retired(d)), key=lambda d: int(d["id"].split("-")[1]))
        firsts = [min((order.index(a) for a in d.get("axes", []) if a in order), default=0) for d in custom]
        if spec.get("status") != "ready" and firsts != sorted(firsts):
            r.error(f"decision {prefix}-*", "番号は、軸のカタログの順（最初の軸の順）に振ってください", rule="OUT-04")
    for sid, sd in standard.items():
        mine = next((d for d in decisions if d.get("id") == sid), None)
        if mine is None:
            r.error(f"decision {sid}", "標準の決定がありません（init_skill.py が足す）")
        elif mine != sd:
            r.error(f"decision {sid}", "標準の決定は変えないでください。スキル固有の決まりは別の決定として足す")
    excluded = {}
    for item in spec.get("excluded_axes", []):
        axis = item.get("axis", "")
        if axis not in info:
            r.error("dev/spec.json excluded_axes", f"軸 {axis} はカタログにありません")
        elif info[axis]["cover"] != "decision":
            r.error("dev/spec.json excluded_axes", f"軸 {axis} は spec の節か標準の決定で答えるので、対象外にできません")
        if not str(item.get("reason", "")).strip():
            r.error("dev/spec.json excluded_axes", f"軸 {axis} に reason がありません")
        excluded[axis] = item
    if not _lib.is_foundation(skill_dir) and spec.get("kind") in _lib.load_profiles():
        wanted = _lib.profile_axes(spec)
        if spec.get("extra_axes", [])[:len(wanted)] != wanted:
            r.error("dev/spec.json extra_axes", f"種類 {spec['kind']} の追加の軸 {[a['name'] for a in wanted]} を、"
                                               "X1 から順に先頭に置いてください（init_skill.py が入れる。references/skill-profiles.md）")
        for axis in _lib.load_profiles()[spec["kind"]].get("focus", []):
            if axis in excluded:
                r.error("dev/spec.json excluded_axes", f"軸 {axis} は種類 {spec['kind']} の重点軸なので、対象外にできません。決定を書いてください")
    for axis in order:
        if info.get(axis, {}).get("cover") == "decision" and axis not in covered and axis not in excluded:
            r.error("dev/spec.json", f"軸 {axis}（{info[axis]['name']}）が、どの決定にも excluded_axes にもありません")
        if axis in covered and axis in excluded:
            r.error("dev/spec.json", f"軸 {axis} は決定と excluded_axes の両方にあります")


def check_profile_inputs(skill_dir: Path, spec: dict, r: Report) -> None:
    """種類（kind）の入力の候補は、inputs に同じ key で入れるか、excluded_inputs に理由を書く。"""
    keys = {i.get("key") for i in spec.get("inputs", [])}
    profile = {} if _lib.is_foundation(skill_dir) else _lib.load_profiles().get(spec.get("kind"), {})
    candidates = {c["key"]: c for c in profile.get("inputs", [])}
    excluded = set()
    for item in spec.get("excluded_inputs", []):
        key = item.get("key", "")
        where = f"dev/spec.json excluded_inputs {key}"
        if key not in candidates:
            r.error(where, f"excluded_inputs に書けるのは、種類 {spec.get('kind')} の入力の候補（{sorted(candidates)}）だけです")
        if key in keys:
            r.error(where, "inputs と excluded_inputs の両方にあります")
        if not str(item.get("reason", "")).strip():
            r.error(where, "reason がありません")
        excluded.add(key)
    for key, cand in candidates.items():
        if key not in keys and key not in excluded:
            r.error("dev/spec.json inputs", f"種類 {spec.get('kind')} の入力の候補 `{key}`（{cand['label'][_lib.labels(spec)]}）を、"
                                            "inputs に同じ key で入れるか、excluded_inputs に key と理由を書いてください（references/skill-profiles.md）")


def check_inputs(spec: dict, r: Report) -> None:
    keys = set()
    for item in spec.get("inputs", []):
        key = item.get("key", "")
        where = f"input {key or '(key なし)'}"
        if not re.fullmatch(r"[a-z][a-z0-9_]*", key):
            r.error(where, "key は snake_case にしてください")
        if key in keys:
            r.error(where, "key が重複しています")
        keys.add(key)
        if not item.get("label"):
            r.error(where, "label がありません")
        kind = item.get("type", "string")
        if kind not in INPUT_TYPES:
            r.error(where, f"type は {INPUT_TYPES} のどれかにしてください")
        if item.get("case") not in (None, "upper", "lower"):
            r.error(where, "case は upper か lower にしてください")
        if kind == "enum" and not item.get("enum"):
            r.error(where, "type が enum なので enum（選択肢）を書いてください")
        if item.get("default") is not None:
            try:
                rt.convert(item["default"], item)
            except ValueError as exc:
                r.error(where, f"default が type に合いません: {exc}")
        if item.get("ask") and item.get("default") is not None:
            r.error(where, "ask と default の両方があります。聞くなら default を消し、既定値で補うなら ask を消してください")
        if item.get("ask") and not item.get("question"):
            r.error(where, "ask が true なので question（聞く文）を書いてください")
        impact = item.get("impact")
        if impact not in _lib.IMPACTS:
            r.error(where, f"impact（無いまま既定値で進めたときの影響）を {list(_lib.IMPACTS)} のどれかにしてください（control-ladder.md の3章）")
        else:
            actual = "ask" if item.get("ask") else ("default" if item.get("default") is not None else "none")
            wanted = _lib.IMPACTS[impact][1]
            if actual != wanted:
                r.error(where, f"impact が {impact} なので、{ {'ask': 'ask と question を書く', 'default': 'default を書く', 'none': 'ask も default も書かない'}[wanted] }（今: {actual}）")


# ---------------------------------------------------------------- フェーズ4

def contract_rules(spec: dict) -> set[str]:
    rules = set()
    for out in spec.get("outputs", []):
        rules.add(out.get("rule"))
        for c in out.get("checks", []):
            rules.add(c.get("rule"))
            rules.update(c.get("rules", []))  # command 検査が出しうるルールID
    rules.update(g.get("rule") for g in spec.get("together", []))
    return {x for x in rules if x}


def check_contract(skill_dir: Path, spec: dict, r: Report) -> None:
    decisions = {d.get("id"): d for d in spec.get("decisions", []) if not retired(d)}
    keys = {i.get("key") for i in spec.get("inputs", [])}
    outputs = spec.get("outputs", [])
    if not outputs:
        r.error("dev/spec.json outputs", "出力が1つもありません。返答だけのスキルでも、返答の本文を `{run}/out/` のファイルに書かせて検査する")
    allow = spec.get("control", {}).get("allow_changes", [])
    if not isinstance(allow, list) or not all(isinstance(g, str) and g and not g.startswith("/") for g in allow):
        r.error("dev/spec.json control.allow_changes", "プロジェクトのルートからの相対の glob の配列にしてください")
    elif "**" in allow or "**/*" in allow:
        r.error("dev/spec.json control.allow_changes", "すべてを許す glob は CTL-05 を無効にします。変えてよいファイルを絞ってください")
    ids = set()
    obj = spec.get("name", "").split("-", 1)[1] if "-" in spec.get("name", "") else ""
    for out in outputs:
        oid = out.get("id", "")
        where = f"output {oid or '(id なし)'}"
        if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", oid):
            r.error(where, "id は kebab-case にしてください")
        if len(outputs) == 1 and obj and not _lib.is_foundation(skill_dir):
            if oid != obj:
                r.error(where, f"出力が1つなので、id は名前の目的語 `{obj}` にしてください（control-ladder.md の4章）", rule="OUT-04")
            stem = Path(out.get("path", "")).name.split(".", 1)[0]
            if out.get("path", "").startswith("{run}/out/") and stem != obj:
                r.error(where, f"{{run}}/out/ に書く出力のファイル名は `{obj}.<拡張子>` にしてください（control-ladder.md の4章）", rule="OUT-04")
        if oid in ids:
            r.error(where, "id が重複しています")
        ids.add(oid)
        for field in ("label", "path", "rule"):
            if not out.get(field):
                r.error(where, f"{field} がありません")
        for key in rt.IN_PLACEHOLDER.findall(out.get("path", "")):
            if key not in keys:
                r.error(where, f"path の {{in:{key}}} が inputs にありません")
        if out.get("path", "").startswith("/") or ".." in out.get("path", "").split("/"):
            r.error(where, "path はプロジェクトのルートからの相対パスにしてください（`..` を使わない）")
        if out.get("rule") and out["rule"] not in decisions:
            r.error(where, f"rule {out['rule']} が decisions にありません")
        if out.get("name_pattern"):
            try:
                re.compile(out["name_pattern"])
            except re.error as exc:
                r.error(where, f"name_pattern が正規表現として不正です: {exc}")
        count = out.get("count", {})
        if any(not isinstance(v, int) for v in count.values()):
            r.error(where, "count の min・max は整数にしてください")
        if count.get("max") == 1 and re.search(r"[*?\[]", rt.IN_PLACEHOLDER.sub("", out.get("path", ""))):
            r.error(where, "count の max が 1 なので、path は glob にせず、ファイル名まで書いてください（control-ladder.md の4章）")
        for i, check in enumerate(out.get("checks", []), 1):
            cw = f"{where} checks[{i}]"
            kind = check.get("type")
            if kind not in CHECK_FIELDS:
                r.error(cw, f"type は {list(CHECK_FIELDS)} のどれかにしてください")
                continue
            for field in CHECK_FIELDS[kind]:
                if field not in check:
                    r.error(cw, f"type {kind} には {field} が必要です")
            if check.get("stage") not in (None, "finish"):
                r.error(cw, "stage は省くか finish にしてください")
            if kind == "headings" and not ("equals" in check or "includes" in check):
                r.error(cw, "headings には equals か includes が必要です")
            if not check.get("rule") or check["rule"] not in decisions:
                r.error(cw, f"rule {check.get('rule')} が decisions にありません")
            elif "validate" not in decisions[check["rule"]].get("control", []):
                r.error(cw, f"rule {check['rule']} の control に validate がありません")
            for extra in check.get("rules", []):
                if kind != "command":
                    r.error(cw, "rules は type が command の検査にだけ書けます")
                elif extra not in decisions or "validate" not in decisions[extra].get("control", []):
                    r.error(cw, f"rules の {extra} が、control に validate を持つ決定ではありません")
            if "pattern" in check:
                try:
                    re.compile(check["pattern"])
                except re.error as exc:
                    r.error(cw, f"pattern が正規表現として不正です: {exc}")
        for i, fix in enumerate(out.get("format", []), 1):
            fw = f"{where} format[{i}]"
            kind = fix.get("type")
            if kind not in rt.FORMAT_TYPES:
                r.error(fw, f"type は {rt.FORMAT_TYPES} のどれかにしてください")
                continue
            for field in {"replace": ["pattern"], "command": ["run"]}.get(kind, []):
                if field not in fix:
                    r.error(fw, f"type {kind} には {field} が必要です")
            if not fix.get("rule") or fix["rule"] not in decisions:
                r.error(fw, f"rule {fix.get('rule')} が decisions にありません")
            elif "format" not in decisions[fix["rule"]].get("control", []):
                r.error(fw, f"rule {fix['rule']} の control に format がありません")
            if "pattern" in fix:
                try:
                    re.compile(fix["pattern"])
                except re.error as exc:
                    r.error(fw, f"pattern が正規表現として不正です: {exc}")
    for i, group in enumerate(spec.get("together", []), 1):
        gw = f"dev/spec.json together[{i}]"
        members = group.get("outputs", [])
        if len(members) < 2 or any(m not in ids for m in members):
            r.error(gw, "outputs に、一緒に変える出力の id を2つ以上書いてください")
        if group.get("rule") not in decisions or "validate" not in decisions[group["rule"]].get("control", []):
            r.error(gw, f"rule {group.get('rule')} が、control に validate を持つ決定ではありません")
    include = spec.get("report", {}).get("include_output")
    if include is not None and include not in ids:
        r.error("dev/spec.json report", f"include_output {include} が outputs にありません")
    for i, section in enumerate(spec.get("report", {}).get("sections", []), 1):
        if not isinstance(section, dict) or not str(section.get("run", "")).strip():
            r.error(f"dev/spec.json report.sections[{i}]", "run（報告の節を標準出力に出すコマンド）を書いてください")
        elif not isinstance(section.get("timeout", 120), int):
            r.error(f"dev/spec.json report.sections[{i}]", "timeout は秒の整数にしてください")
        elif section.get("stage") not in (None, "finish"):
            r.error(f"dev/spec.json report.sections[{i}]", "stage は省くか finish にしてください")
        else:
            for key in rt.IN_PLACEHOLDER.findall(section["run"]):
                if key not in keys:
                    r.error(f"dev/spec.json report.sections[{i}]", f"run の {{in:{key}}} が inputs にありません")
    used = contract_rules(spec)
    format_rules = {fix.get("rule") for out in outputs for fix in out.get("format", [])}
    probes_doc = _lib.load_json(skill_dir / "dev/probes.json") if (skill_dir / "dev/probes.json").is_file() else {}
    probes = {p.get("id"): p for p in probes_doc.get("probes", [])}
    for d in decisions.values():
        rid, control = d.get("id"), d.get("control", [])
        where = f"decision {rid}"
        if "runtime" in control and not any(m in d.get("how", "") for m in _lib.RUNTIME_MARKS):
            r.error(where, f"control に runtime があるので、how に共通ランタイムの仕組み（{'、'.join(_lib.RUNTIME_MARKS)} のどれか）を書いてください")
        if d.get("probes") == ["builtin"]:
            continue
        if "format" in control:
            if rid not in format_rules:
                r.error(where, "control に format があるのに、outputs の format で使われていません")
            if not any(probes.get(pid, {}).get("fixed") for pid in d.get("probes", [])):
                r.error(where, "control に format があるので、probes に、自動で直ることを確かめる違反例（fixed を持つ probe）を書いてください")
        if "validate" in control or "format" in control:
            if "validate" in control and rid not in used:
                r.error(where, "control に validate があるのに、契約（outputs の rule か checks の rule）で使われていません")
            listed = d.get("probes", [])
            if not listed:
                r.error(where, "control に validate か format があるので、probes に違反例の ID を書いてください")
            for pid in listed:
                if pid not in probes:
                    r.error(where, f"probe {pid} が dev/probes.json にありません")
                elif probes[pid].get("rule") != rid:
                    r.error(where, f"probe {pid} の rule が {probes[pid].get('rule')} になっています")
        if "script" in control:
            paths = re.findall(r"scripts/[A-Za-z0-9_./-]+", d.get("how", ""))
            if not paths:
                r.error(where, "control に script があるので、how にスクリプトのパス（scripts/...）を書いてください")
            for path in paths:
                if not (skill_dir / path.rstrip(".。,、")).is_file():
                    r.error(where, f"how の {path} がありません")
        if "template" in control:
            paths = re.findall(r"assets/[A-Za-z0-9_./-]+", d.get("how", ""))
            if not paths or not all((skill_dir / p.rstrip(".。,、")).exists() for p in paths):
                r.error(where, "control に template があるので、how に実在するひな形のパス（assets/...）を書いてください")
    for pid, probe in probes.items():
        where = f"dev/probes.json {pid}"
        if not _lib.PROBE_ID_RE.match(pid or "") or not str(pid).startswith(f"{probe.get('rule')}-"):
            r.error(where, "id は <ルールID>-<英小文字か数字>（例: OUT-02-a）にしてください", rule="OUT-04")
        if probe.get("rule") not in decisions:
            r.error(where, f"rule {probe.get('rule')} が decisions にありません")
        check_changes(skill_dir, where, probe.get("files", []), r)
        if probe.get("fixed") is not None:
            try:
                re.compile(probe["fixed"])
            except re.error as exc:
                r.error(where, f"fixed が正規表現として不正です: {exc}")
            if "format" not in decisions.get(probe.get("rule"), {}).get("control", []):
                r.error(where, f"fixed は、control に format を持つ決定の probe にだけ書けます（rule {probe.get('rule')}）")
        try:
            re.compile(probe.get("expect") or "")
            if not probe.get("expect"):
                r.error(where, "expect（出力に現れるべき文字列の正規表現。ふつうはルールID）がありません")
        except re.error as exc:
            r.error(where, f"expect が正規表現として不正です: {exc}")
    reviewed = {}
    for sample in probes_doc.get("reviews", []):
        sid, rule = sample.get("id", ""), sample.get("rule")
        where = f"dev/probes.json reviews {sid or '(id なし)'}"
        if not re.fullmatch(r"[A-Z]{2,5}-\d{2}-r\d+", sid) or not sid.startswith(f"{rule}-"):
            r.error(where, "id は <ルールID>-r<番号>（例: OUT-03-r1）にしてください", rule="OUT-04")
        if sid in probes or sid in {x for v in reviewed.values() for x in v}:
            r.error(where, "id が重複しています")
        if rule not in decisions or "review" not in decisions[rule].get("control", []):
            r.error(where, f"rule {rule} が、control に review を持つ決定ではありません")
        if not str(sample.get("description", "")).strip():
            r.error(where, "description（どんな違反を入れるか）がありません")
        check_changes(skill_dir, where, sample.get("files", []), r)
        reviewed.setdefault(rule, []).append(sid)
    for rid, d in decisions.items():
        if "review" in d.get("control", []) and rid not in _lib.STANDARD_IDS and rid not in reviewed:
            r.error(f"decision {rid}", "control に review があるので、dev/probes.json の reviews に、機械の検査を通ってしまう違反の見本を"
                                       "1つ以上書いてください（レビューの検出率を測る。control-ladder.md の7章）")
    baseline = probes_doc.get("baseline", {})
    if not baseline.get("files") and not baseline.get("commands"):
        r.error("dev/probes.json baseline", "files か commands で、検査に通る出力の見本を作ってください（probe はこれを壊して作る）")
    for change in baseline.get("files", []):
        check_from(skill_dir, "dev/probes.json baseline", change, r)
    if not _lib.is_foundation(skill_dir):
        examples = [p for p in (skill_dir / _lib.EXAMPLES_DIR).rglob("*") if p.is_file() and p.name != ".DS_Store"] \
            if (skill_dir / _lib.EXAMPLES_DIR).is_dir() else []
        if not examples:
            r.error(_lib.EXAMPLES_DIR, "検査に通る出力の見本を1つ以上置いてください（AI が形を写す元になる）", rule="OUT-02")
        if not any(str(c.get("from", "")).startswith(_lib.EXAMPLES_DIR + "/") for c in baseline.get("files", [])):
            r.error("dev/probes.json baseline", f"files の1つ以上を from: {_lib.EXAMPLES_DIR}/<ファイル> にしてください"
                                                "（見本が検査に通ることを probe.py で確かめる）", rule="OUT-02")
        check_examples(skill_dir, spec, decisions, examples, r)
        check_scripts(skill_dir, decisions, r)
    for path in sorted((skill_dir / "scripts").glob("*.py")):
        try:
            py_compile.compile(str(path), cfile=str(Path(tempfile.gettempdir()) / "skill-lint.pyc"), doraise=True)
        except py_compile.PyCompileError as exc:
            r.error(f"scripts/{path.name}", f"Python として読めません: {exc.msg}")
            continue
        if path.name.startswith("_"):
            continue
        code, output = _lib.run([sys.executable, str(path), "--help"], skill_dir, timeout=20)
        if code != 0:
            r.error(f"scripts/{path.name}", f"--help が終了コード {code} で終わりました: {_lib.tail(output, 3)}")
    for rel, content in render_skill.render_all(skill_dir, spec).items():
        target = skill_dir / rel
        if not target.is_file() or target.read_text(encoding="utf-8") != content:
            r.error(rel, "dev/spec.json から生成した内容と違います（手で編集しない。render_skill.py を実行する）")


def check_examples(skill_dir: Path, spec: dict, decisions: dict, files: list[Path], r: Report) -> None:
    """見本はすべて spec の examples に載せ、出力の決定（OUT-*）をどれかの見本の shows で体現させる。"""
    listed, shown = set(), set()
    for i, example in enumerate(spec.get("examples", []), 1):
        where = f"dev/spec.json examples[{i}]"
        rel = f"{_lib.EXAMPLES_DIR}/{example.get('path', '')}"
        if not example.get("path") or not (skill_dir / rel).is_file():
            r.error(where, f"path は {_lib.EXAMPLES_DIR}/ の下の実在するファイル（{_lib.EXAMPLES_DIR}/ からの相対パス）にしてください", rule="OUT-02")
        listed.add(rel)
        for rid in example.get("shows", []):
            if rid not in decisions:
                r.error(where, f"shows の {rid} が decisions にありません")
        shown.update(example.get("shows", []))
    outputs = spec.get("outputs", [])
    single = Path(outputs[0].get("path", "")).name if len(outputs) == 1 else ""
    if single and not re.search(r"[*?\[{]", single) and files and single not in {f.name for f in files}:
        r.error(_lib.EXAMPLES_DIR, f"見本のファイル名は、出力のファイル名 `{single}` と同じにしてください（control-ladder.md の7章）", rule="OUT-02")
    for path in files:
        rel = path.relative_to(skill_dir).as_posix()
        if rel not in listed:
            r.error(rel, "dev/spec.json の examples に、この見本の path と shows（体現する決定の ID）を書いてください", rule="OUT-02")
    for rid in decisions:
        if rid.startswith("OUT-") and rid not in shown:
            r.error(f"decision {rid}", "どの見本もこの決定を体現していません。見本を直し、dev/spec.json の examples の shows にこの ID を"
                                       "足してください（AI は規則より、一番近い見本を写す）", rule="OUT-02")


def check_scripts(skill_dir: Path, decisions: dict, r: Report) -> None:
    """スキル固有のスクリプトの決定性と、決定との対応（control-ladder.md の5章）。"""
    folder = skill_dir / "scripts"
    for path in sorted(folder.iterdir()) if folder.is_dir() else []:
        if not path.is_file() or path.name in _lib.RUNTIME_FILES or path.suffix not in (".py", ".sh"):
            continue
        rel = f"scripts/{path.name}"
        text = path.read_text(encoding="utf-8", errors="replace")
        if NETWORK.search(text):
            r.error(rel, "ネットワークに触れるモジュールを使っています。同じ入力なら同じ結果を出すよう、スキルのスクリプトは"
                         "ネットワークに触れない（control-ladder.md の5章）")
        if UNSTABLE.search(text):
            r.warn(rel, "乱数・UUID・現在時刻を使っています。出力に入れる値なら、入力か git から取ってください（同じ入力なら同じ結果にする）")
        if path.name.startswith("_"):
            r.error(rel, "部品のファイル（`_` で始まる）は作りません。同じ処理が2つのスクリプトに要るなら、"
                         "1つのスクリプトのサブコマンドにしてください（control-ladder.md の5章）")
            continue
        owners = [rid for rid, d in decisions.items() if rel in d.get("how", "")]
        if not owners:
            r.error(rel, "どの決定の how にも挙がっていません。スクリプトは決定を守らせるためだけに置き、その決定の how に書いてください")
        elif not any(re.search(r"(?<![A-Z])" + re.escape(o) + r"(?![\d-])", text) for o in owners):
            r.error(rel, f"先頭の docstring に、このスクリプトを how に挙げた決定の ID（{'、'.join(owners)}）を書いてください")


# ---------------------------------------------------------------- フェーズ5

def check_entry(skill_dir: Path, spec: dict, r: Report) -> None:
    path = skill_dir / "SKILL.md"
    text = path.read_text(encoding="utf-8")
    fm, body = _lib.parse_frontmatter(text)
    if fm is None:
        r.error("SKILL.md", "先頭に --- で囲んだ frontmatter がありません", rule="OUT-02")
        return
    for key in fm:
        if key not in FM_KEYS:
            r.error("SKILL.md", f"frontmatter のキー {key} は使わない（Claude Code・Codex・claude.ai で共通に読めるのは name と description）", rule="OUT-02")
    desc = render_skill.description(spec)
    if len(desc) > 1024:
        r.error("SKILL.md", f"description が {len(desc)} 文字です。1024 文字以下にする（Codex は一覧で 1024 文字に切り詰める）", rule="OUT-05")
    elif len(desc) > 600:
        r.warn("SKILL.md", f"description が {len(desc)} 文字です。先頭の 250 文字に目的と主な依頼が入っているか確かめてください")
    lines = text.splitlines()
    if len(lines) > 500:
        r.error("SKILL.md", f"{len(lines)} 行あります。500 行以下にし、詳細は references/ に移してください", rule="OUT-05")
    titles = _lib.h2_titles(body)
    expected = _lib.SECTIONS[_lib.labels(spec)]
    if titles != expected:
        r.error("SKILL.md", f"## の見出しは {expected} の順で過不足なく並べてください（今: {titles}）", rule="OUT-02")
    found = _lib.blocks(text)
    for block_id in _lib.BLOCKS:
        if block_id not in found:
            r.error("SKILL.md", f"生成部分 {block_id} の目印がありません", rule="OUT-02")
    decisions = {d.get("id"): d for d in spec.get("decisions", []) if not retired(d)}
    retired_ids = {d.get("id") for d in spec.get("decisions", []) if retired(d)}
    procedure = _lib.section(body, expected[1])
    steps = re.findall(r"^(\d+)\. (.+)$", procedure, re.M)
    numbers = [int(n) for n, _ in steps]
    if numbers != list(range(1, len(numbers) + 1)) or len(numbers) < 5:
        r.error("SKILL.md 手順", f"手順は 1 から連番の番号付きの行で、5つ以上にしてください（今: {numbers}）", rule="OUT-05")
    joined = [s for _, s in steps]
    positions = {}
    for word in ("run.py start", "run.py check", "run.py finish"):
        hit = [i for i, s in enumerate(joined) if word in s]
        if not hit:
            r.error("SKILL.md 手順", f"`{word}` を実行する手順がありません（CTL-01）", rule="OUT-02")
        else:
            positions[word] = hit[0]
    if len(positions) == 3 and not positions["run.py start"] < positions["run.py check"] < positions["run.py finish"]:
        r.error("SKILL.md 手順", "start → check → finish の順に並べてください", rule="OUT-02")
    if joined and "run.py finish" not in joined[-1]:
        r.error("SKILL.md 手順", "最後の手順は `run.py finish` にしてください", rule="OUT-02")
    if joined and "CTL-03" not in joined[0]:
        r.error("SKILL.md 手順", "最初の手順は、start の前に質問を済ませる手順（CTL-03）にしてください", rule="OUT-02")
    if joined and not _lib.is_foundation(skill_dir) and not any(_lib.EXAMPLES_DIR + "/" in s for s in joined):
        r.error("SKILL.md 手順", f"出力を書く手順で、写す元になる見本（`{_lib.EXAMPLES_DIR}/<ファイル>`）を示してください", rule="OUT-02")
    for i, step in enumerate(joined, 1):
        ids = _lib.ID_IN_TEXT.findall(step)
        if not ids and "`" not in step:
            r.error(f"SKILL.md 手順 {i}", "各手順に、決定のIDか `` ` `` で囲んだコマンドを入れてください（何に従うかを一意にする）", rule="OUT-02")
        for rid in ids:
            if rid in retired_ids:
                r.error(f"SKILL.md 手順 {i}", f"{rid} は廃止した決定です。手順から外してください")
            elif rid not in decisions:
                r.error(f"SKILL.md 手順 {i}", f"{rid} が decisions にありません")
        for word in _lib.vague_words(step):
            r.error(f"SKILL.md 手順 {i}", f"あいまいな語「{word}」があります", rule="OUT-03")
    handwritten = _lib.strip_blocks(body)
    refs = "\n".join(p.read_text(encoding="utf-8") for p in sorted((skill_dir / "references").glob("*.md"))
                     if p.name != "decisions.md")
    for rid, d in decisions.items():
        if "doc" in d.get("control", []) and not re.search(r"(?<![A-Z])" + re.escape(rid) + r"(?![\d-])", handwritten + refs):
            r.error(f"decision {rid}", "control に doc があるので、SKILL.md の手順か references/ の本文にこの ID を書いてください")
    for target in re.findall(r"\]\(([^)#\s]+)(?:#[^)]*)?\)", text):
        if re.match(r"[a-z]+://", target):
            continue
        if not (skill_dir / target).exists():
            r.error("SKILL.md", f"リンク先 {target} がありません", rule="OUT-02")
        elif target.startswith("references/") and target.count("/") > 1:
            r.error("SKILL.md", f"リンク先 {target} は references/ の直下に置いてください", rule="OUT-02")
    for ref in sorted((skill_dir / "references").glob("*.md")):
        if f"references/{ref.name}" not in text:
            r.warn(f"references/{ref.name}", "SKILL.md からリンクされていません（読まれない）")


# ---------------------------------------------------------------- 仕上げ

def check_final(skill_dir: Path, spec: dict, r: Report, project: Path | None) -> None:
    if spec.get("status") != "ready":
        r.error("dev/spec.json", "status が ready ではありません（フェーズ7で ready にする）")
    # skill-foundation 自身のひな形と見本は、埋める前の形を配るものなので除く
    exempt = ("assets/templates/", "assets/example/") if skill_dir.resolve() == _lib.FOUNDATION_DIR.resolve() else ()
    for rel in _lib.iter_files(skill_dir):
        if rel.startswith("dev/results/") or rel.startswith(exempt):
            continue
        path = skill_dir / rel
        try:
            content = re.sub(r"`[^`\n]*`", "", path.read_text(encoding="utf-8"))  # コード片の中の記載は数えない
        except (UnicodeDecodeError, OSError):
            continue
        if _lib.TODO_MARKER in content:
            r.error(rel, f"{_lib.TODO_MARKER} が {content.count(_lib.TODO_MARKER)} 件残っています")
    research = (skill_dir / "dev/research.md").read_text(encoding="utf-8") if (skill_dir / "dev/research.md").is_file() else ""
    pending = [l for l in research.splitlines() if re.search(r"(確認の状態|Status)\s*[:：].*(未確認|unverified)", l, re.I)]
    if pending:
        r.error("dev/research.md", f"確認の状態が未確認の項目が {len(pending)} 件あります")
    evals = _lib.load_json(skill_dir / "dev/evals.json").get("tasks", []) if (skill_dir / "dev/evals.json").is_file() else []
    kinds = [t.get("kind") for t in evals]
    if sum(k != "holdout" for k in kinds) < 3 or "holdout" not in kinds:
        r.error("dev/evals.json", "課題は holdout 以外を3つ以上と、holdout を1つ以上にしてください", rule="OUT-05")
    implicit = spec.get("triggers", {}).get("implicit") is not False
    fixtures = skill_dir / "dev/fixtures"
    extra = sorted(p.name for p in fixtures.iterdir() if p.name not in (_lib.FIXTURE_NAME, ".DS_Store")) if fixtures.is_dir() else []
    if extra:
        r.error("dev/fixtures", f"fixture は dev/fixtures/{_lib.FIXTURE_NAME} の1つだけにし、課題ごとの違いは setup のコマンドで作ってください"
                                f"（余分: {'、'.join(extra)}。convergence-test.md の1章）")
    for task in evals:
        tid = task.get("id")
        if task.get("fixture") and task["fixture"] != f"dev/fixtures/{_lib.FIXTURE_NAME}":
            r.error("dev/evals.json", f"{tid} の fixture は dev/fixtures/{_lib.FIXTURE_NAME} にしてください")
        elif task.get("fixture") and not (skill_dir / task["fixture"]).is_dir():
            r.error("dev/evals.json", f"{tid} の fixture {task['fixture']} がありません")
        prompt = str(task.get("prompt", ""))
        hints = [w for w in (spec.get("name"), "scripts/", "run.py", "SKILL.md") if w and w in prompt]
        hints += DECISION_ID_IN_TEXT.findall(prompt)
        if hints:
            r.error("dev/evals.json", f"{tid} の prompt に {'、'.join(hints)} があります。ユーザーが知らない手掛かりを課題に書かないでください")
        if task.get("invoke") == "explicit" and implicit:
            r.error("dev/evals.json", f"{tid} は invoke: explicit ですが、triggers.implicit が false ではありません。"
                                      "自動で起動するかを測るため、invoke を外してください")
        if not implicit and task.get("invoke") != "explicit" and task.get("expect_status", "done") == "done":
            r.error("dev/evals.json", f"{tid} に invoke: explicit を付けてください（triggers.implicit が false なので、付けないと Claude Code で起動しない）")
    results_path = skill_dir / "dev/results/probe-results.json"
    if not results_path.is_file():
        r.error("dev/results/probe-results.json", "ありません。probe.py を実行してください")
    else:
        results = _lib.load_json(results_path)
        if results.get("hash") != probes_hash(skill_dir):
            r.error("dev/results/probe-results.json", "probe・契約・ランタイムが変わった後の結果ではありません。probe.py をやり直してください")
        failed = [x["id"] for x in results.get("results", []) if not x.get("passed")]
        if failed:
            r.error("dev/results/probe-results.json", f"成功していない probe: {', '.join(failed)}")
        for x in results.get("results", []):
            if x.get("others"):
                r.warn(f"dev/results/probe-results.json {x['id']}", f"別のルール {', '.join(x['others'])} の指摘も出ています。"
                                                                   "1つの違反例は1つの決定だけを破るようにしてください（control-ladder.md の7章）")
        platforms = {w.get("platform") for w in results.get("wiring", []) if w.get("passed")}
        for target in spec.get("targets", []):
            if spec.get("control", {}).get("hooks", True) and target not in platforms:
                r.error("dev/results/probe-results.json", f"{target} の hooks の配線の確認が成功していません")
        if any(not w.get("passed") for w in results.get("wiring", [])):
            r.error("dev/results/probe-results.json", "失敗した配線の確認があります")
    rounds = sorted((skill_dir / "dev/results/convergence").glob("round-*/report.json"))
    skip = str(spec.get("convergence", {}).get("skip_reason") or "").strip()
    if skip:
        r.warn("dev/spec.json convergence.skip_reason", f"収束テストを省いています（{skip}）")
    elif not rounds:
        r.error("dev/results/convergence", "収束テストの結果がありません。convergence.py を実行するか、"
                                           "利用者が省くと指定したときか、runner が無いときだけ convergence.skip_reason に理由を書いてください", rule="STEP-02")
    else:
        latest = max(rounds, key=lambda p: int(p.parent.name.split("-")[1]))
        report = _lib.load_json(latest)
        rel = latest.relative_to(skill_dir).as_posix()
        missing = sorted({t.get("id") for t in evals} - {t["id"] for t in report.get("tasks", [])})
        if missing:
            r.error(rel, f"最後のラウンドに holdout を含む全課題を入れてください（足りない課題: {', '.join(missing)}）", rule="STEP-04")
        text = (skill_dir / "dev/convergence-report.md").read_text(encoding="utf-8") \
            if (skill_dir / "dev/convergence-report.md").is_file() else ""
        conclusion = _lib.section(text, "結論") + _lib.section(text, "Conclusion")
        for task in report.get("tasks", []):
            if not task.get("converged") and task["id"] not in conclusion:
                r.error(rel, f"{task['id']} が基準を満たしていません。締め込んで再実行するか、"
                             "上限のラウンドなら続けるかをユーザーに聞き、続けないなら dev/convergence-report.md の「結論」に課題の ID・分類・残した理由を書いてください", rule="STEP-04")
        doc = _lib.load_json(skill_dir / "dev/probes.json") if (skill_dir / "dev/probes.json").is_file() else {}
        if doc.get("reviews"):
            review_path = latest.parent / "review.json"
            if not review_path.is_file():
                r.error(rel, "最後のラウンドに、レビューの検出率の結果（review.json）がありません。convergence.py の review-prepare・"
                             "run・review-score を実行してください（convergence-test.md の3章）", rule="STEP-04")
            else:
                for sample in _lib.load_json(review_path).get("samples", []):
                    if sample.get("rate", 0) < 1 and sample["id"] not in conclusion:
                        r.error(review_path.relative_to(skill_dir).as_posix(),
                                f"{sample['id']}（{sample.get('rule')}）を見逃したエージェントがいます。完了前チェックリストの項目を直して"
                                "測り直すか、続けないなら dev/convergence-report.md の「結論」に見本の ID と残した理由を書いてください", rule="STEP-04")
    if project is not None:
        code, output = _lib.run([sys.executable, str(skill_dir / "scripts/install.py"), "--project", str(project),
                                 "--targets", ",".join(spec.get("targets", [])), "--check"]
                                + ([] if spec.get("control", {}).get("hooks", True) else ["--no-hooks"]), skill_dir)
        if code != 0:
            r.error("install", _lib.tail(output, 10), rule="OUT-01")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("dir", help="スキルのディレクトリ")
    parser.add_argument("--phase", type=int, choices=[1, 3, 4, 5])
    parser.add_argument("--final", action="store_true")
    parser.add_argument("--gate", action="store_true", help="status が building ならフェーズ1、ready なら --final")
    parser.add_argument("--project", help="--final のとき、置き場所と hooks も調べるプロジェクトのルート")
    parser.add_argument("--rule", help="エラーの行頭を ERROR でなくこのルールIDにする（契約の command 検査から呼ぶとき）")
    parser.add_argument("--seal", action="store_true", help="--final でエラーが無ければ assets/seal.json を書く（封印）")
    args = parser.parse_args()

    skill_dir = Path(args.dir).resolve()
    if not (skill_dir / _lib.SPEC_REL).is_file():
        _lib.fail(f"{skill_dir / _lib.SPEC_REL} がありません")
    spec = _lib.load_spec(skill_dir)
    final = args.final or (args.gate and spec.get("status") == "ready") or (
        args.phase is None and not args.gate and spec.get("status") == "ready")
    phase = 5 if final else (1 if args.gate else (args.phase or 5))
    r = Report()
    check_structure(skill_dir, spec, r)
    if args.seal and not final:
        _lib.fail("--seal は --final と一緒に使います（全部の検査に通った状態だけを封印する）")
    if phase >= 3:
        check_decisions(skill_dir, spec, r)
        check_inputs(spec, r)
        check_profile_inputs(skill_dir, spec, r)
    if phase >= 4 and not r.errors:
        check_contract(skill_dir, spec, r)
    elif phase >= 4:
        r.warn("skill_lint", "前のフェーズのエラーがあるため、フェーズ4以降の検査を飛ばしました")
    if phase >= 5 and (skill_dir / "SKILL.md").is_file():
        check_entry(skill_dir, spec, r)
    if final:
        check_final(skill_dir, spec, r, Path(args.project).resolve() if args.project else None)
    for warning in r.warnings:
        print(f"WARN {warning}")
    for rule, error in r.errors:
        print(f"{(rule or args.rule) if args.rule else 'ERROR'} {error}")
    label = "final" if final else f"phase {phase}"
    print(f"[{label}] {spec.get('name')}: 決定 {len(spec.get('decisions', []))} 件、出力 {len(spec.get('outputs', []))} 件、"
          f"エラー {len(r.errors)} 件、警告 {len(r.warnings)} 件")
    if args.seal and not r.errors:
        count = rt.write_seal(skill_dir, rt.load_contract(skill_dir))
        print(f"封印しました: {rt.SEAL_REL}（保護ファイル {count} 件）。変えると、封印し直すまで start が止まります")
    return 1 if r.errors else 0


if __name__ == "__main__":
    sys.exit(main())
