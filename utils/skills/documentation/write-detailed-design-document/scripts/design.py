#!/usr/bin/env python3
"""資料の一覧・引用・設計の検査・Markdown生成を行う。

ルール: IN-02 STEP-02 STEP-03 OUT-01 OUT-02 OUT-04 OUT-05 OUT-06
OUT-07 OUT-08 OUT-09。Python 3.9以上の標準ライブラリを使う。
出力: inspect/citeはJSON、render/check/reportは処理結果とルールID。
終了コード: 0=成功、1=設計への指摘、2=引数・読取の誤り、3=資料の確認が必要。
使い方: python3 scripts/design.py --help
"""

import argparse
import ast
import hashlib
import html
import json
import re
import sys
import importlib.util
from pathlib import Path

_spec = importlib.util.spec_from_file_location("design_presentation", Path(__file__).with_name("presentation.py"))
presentation = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(presentation)


FILES = ["README.md", "common.md", "features.md", "interfaces.md", "data.md",
         "ui.md", "recovery.md", "verification.md", "evidence.md", "review.html"]
GROUPS = {
    "sources": ("S", "evidence.md"), "modules": ("M", "common.md"),
    "state_sets": ("ST", "common.md"), "decisions": ("D", "common.md"),
    "requirements": ("R", "verification.md"), "features": ("F", "features.md"),
    "interfaces": ("IF", "interfaces.md"), "tables": ("T", "data.md"),
    "transitions": ("TR", "common.md"), "concurrency": ("P", "common.md"),
    "recovery": ("RC", "recovery.md"), "screens": ("UI", "ui.md"),
    "checks": ("C", "verification.md"), "issues": ("U", "evidence.md"),
    "changes": ("CH", "evidence.md"), "diagrams": ("G", "features.md"),
}
OPTIONAL = ["state_sets", "interfaces", "tables", "transitions", "concurrency",
            "recovery", "screens", "issues", "changes", "diagrams"]
LABELS = {
    "name": "名前", "meaning": "意味", "responsibility": "責務", "depends_on": "依存先",
    "entity": "対象", "values": "状態と意味", "kind": "区分", "statement": "内容",
    "source_ids": "根拠", "adoption": "採用判断", "adoption_evidence": "判断の証拠",
    "verification": "検証内容・状態", "verification_evidence": "検証の証拠",
    "external_dependency": "外部検証への依存", "issue_ids": "関連する未決",
    "text": "内容", "status": "設計の状態", "reason": "理由", "feature_ids": "対象機能",
    "check_ids": "確認条件", "module_ids": "担当する責務", "purpose": "目的",
    "preconditions": "開始条件", "input_interface_ids": "入力の境界", "steps": "処理順",
    "result": "結果", "failure": "異常・競合・中断", "state_set_ids": "共通の状態",
    "table_ids": "保存先", "screen_ids": "画面", "recovery_ids": "回復設計",
    "caller": "呼出し元", "callee": "呼出し先", "transport": "通信経路",
    "input": "入力と制約", "response": "出力", "errors": "エラーと終了値",
    "max_size": "最大サイズ", "validation_order": "検査順", "repeat": "再送・重複",
    "disconnect": "切断後の扱い", "columns": "物理列", "constraints": "制約",
    "indexes": "索引", "index_policy": "索引の採用理由", "update_unit": "更新の単位",
    "deletion": "削除の単位と順序", "migration": "移行手順", "state_set_id": "状態定義",
    "from": "現在状態", "event": "イベント", "guard": "遷移条件", "to": "次状態",
    "write": "保存の内容と原子性", "notify": "通知", "protected_data": "保護するデータ",
    "exclusion": "排他の範囲", "order": "取得順序", "acquire": "確保する時点",
    "release": "解放する時点", "limit_update": "上限の更新", "time_boundary": "時刻と等号",
    "winner": "競合の勝敗", "cut": "停止した場所", "committed": "確定済みの内容",
    "remaining": "残る情報", "restart": "再起動と再開", "retry": "再試行の条件",
    "visible_result": "呼出し元と画面の結果", "fields": "項目", "validation": "入力検査",
    "display": "表示状態", "actions": "操作と可否", "save_result": "保存結果",
    "focus": "フォーカスとキーボード操作", "updates": "更新通知",
    "interface_ids": "使う境界", "given": "開始時の条件", "when": "行う操作・発生する事象",
    "then": "観測する結果", "question": "未決の内容", "affected_ids": "影響する設計",
    "acceptance": "採用できる結果", "independent_work": "独立して進める範囲",
    "owner": "確認する担当", "target": "変更対象", "before": "変更前", "after": "変更後",
    "impact": "影響", "type": "型", "explains": "図が伝えること",
    "condition_ids": "厳密な条件を記した設計",
    "nullable": "NULL可否", "default": "既定値", "constraint": "制約", "reference": "参照先",
    "primary_key": "主キーの列構成", "unique_keys": "一意キーの列構成", "key_policy": "キーの理由",
    "request_fields": "要求の項目", "request_policy": "要求の欠落と未知項目",
    "response_variants": "応答の種類と項目", "path": "項目パス", "required": "必須",
    "description": "意味と条件", "state_effects": "応答と状態の対応", "outcome": "応答名",
    "transition_id": "遷移", "state_policy": "許可状態と権利と副作用",
    "key_role": "キーへの所属",
}
SECTIONS = {
    "common.md": ("共通仕様", "責務、用語、状態、時間条件を先に定義し、機能ごとの判断を揃える。", ["modules", "state_sets", "decisions", "transitions", "concurrency"]),
    "features.md": ("機能ごとの詳細", "開始条件から保存と結果までを追い、異常時の回復と確認方法へつなぐ。", ["features"]),
    "interfaces.md": ("境界の契約", "境界の両側が同じ意味で実装できるよう、入力、出力、失敗、切断と再送を定義する。", ["interfaces"]),
    "data.md": ("物理データ", "状態を何に保存し、どの制約と更新単位で整合性を保つかを定義する。", ["tables"]),
    "ui.md": ("画面と操作", "利用者が保存状態と操作結果を判断できるよう、項目、操作、表示とフォーカスを定義する。", ["screens"]),
    "recovery.md": ("障害と再起動", "停止した場所ごとに確定した内容と残る情報を分け、再開と再試行の条件を定義する。", ["recovery"]),
    "verification.md": ("要件との対応と確認条件", "要件を設計と観測できる結果へ対応付ける。試験条件は実施結果を意味しない。", ["requirements", "checks"]),
    "evidence.md": ("根拠と未決事項と変更", "引き継いだ記述と追加提案を分け、未決の影響と要件変更の判断を辿れるようにする。", ["sources", "issues", "changes"]),
}
REVIEW_PARTS = {
    "features": ("責務と機能", ["terms", "modules", "features"]),
    "interfaces": ("境界", ["interfaces"]),
    "tables": ("物理データ", ["tables"]),
    "screens": ("画面", ["screens"]),
    "checks": ("要件と確認条件", ["requirements", "checks"]),
    "states": ("状態と遷移", ["state_sets", "transitions"]),
    "concurrency": ("並行制御", ["concurrency"]),
    "recovery": ("障害と回復", ["recovery"]),
    "decisions": ("情報の区分と判断", ["decisions"]),
    "issues": ("未決と変更", ["issues", "changes"]),
}


def display_row(row):
    """キーの列への所属はキー定義から導出し、別の定義を持たない。"""
    if "columns" not in row:
        return row
    result = dict(row)
    columns = []
    for column in row["columns"]:
        name = column["name"]
        roles = []
        if name in row["primary_key"]:
            roles.append("PK " + str(row["primary_key"].index(name) + 1))
        roles += ["U" + str(i) + " " + str(key.index(name) + 1)
                  for i, key in enumerate(row["unique_keys"], 1) if name in key]
        columns.append(dict(column, key_role=", ".join(roles) or "—"))
    result["columns"] = columns
    return result


def review_document(data):
    """台帳の値を省略せず、分野別の読取り窓とする。採点の答えは作らない。"""
    english = data["language"] == "en"
    esc = lambda value: html.escape(str(value), quote=True)

    def value_html(value):
        if isinstance(value, dict):
            return "<dl>" + "".join("<dt>" + esc(k if english else LABELS.get(k, k)) + "</dt><dd>" + value_html(v) + "</dd>" for k, v in value.items()) + "</dl>"
        if isinstance(value, list):
            if value and all(isinstance(v, dict) and list(v) == list(value[0]) for v in value):
                keys = list(value[0])
                head = "<tr>" + "".join("<th>" + esc(k if english else LABELS.get(k, k)) + "</th>" for k in keys) + "</tr>"
                rows = ["<tr>" + "".join("<td>" + value_html(row[k]) + "</td>" for k in keys) + "</tr>" for row in value]
                return '<div class="matrix"><table><thead>' + head + "</thead><tbody>" + "".join(rows) + "</tbody></table></div>"
            return "<ul>" + "".join("<li>" + value_html(v) + "</li>" for v in value) + "</ul>" if value else "—"
        return esc(json.dumps(value) if value is None or isinstance(value, bool) else value)

    lines = ["<!doctype html>", '<html lang="' + data["language"] + '"><head><meta charset="utf-8">',
             '<meta name="viewport" content="width=device-width,initial-scale=1">',
             "<title>" + esc(data["title"]) + "</title>",
             "<style>body{font:16px/1.7 system-ui,sans-serif;max-width:72rem;margin:auto;padding:2rem;color:#203040}nav{display:flex;gap:1rem;flex-wrap:wrap}section{margin:3rem 0}article{border-top:1px solid #ccd5df;padding:1rem 0}dt{font-weight:600}dd{margin:0 0 .7rem 1rem;white-space:pre-wrap}dl dl{padding:.5rem;background:#f4f7fa}li{margin:.3rem 0}.matrix{overflow:auto}table{border-collapse:collapse;width:100%;font-size:.9rem}th,td{padding:.4rem;border:1px solid #ccd5df;text-align:left;vertical-align:top;overflow-wrap:anywhere}a{color:#064d99}</style></head><body>",
             "<h1>" + esc(data["title"]) + "</h1>", "<p>" + esc(data["overview"]) + "</p>",
             '<p><a href="README.md">README.md</a> · <a href="evidence.md">evidence.md</a> · <a href="design.json">design.json</a></p>',
             "<nav>" + "".join('<a href="#' + key + '">' + esc(key if english else title) + "</a>" for key, (title, _) in REVIEW_PARTS.items()) + "</nav>"]
    for key, (title, groups) in REVIEW_PARTS.items():
        lines += ['<section id="' + key + '"><h2>' + esc(key if english else title) + "</h2>",
                  "<p>" + esc(data["scope"]) + "</p>"]
        if key in ["states", "concurrency", "recovery"]:
            lines += ["<p>" + esc(data["time_policy"]) + "</p>"]
        if key in ["decisions", "issues"]:
            # 引用本文はevidence.mdに全件ある。採用・検証を主張する証拠はこの窓にも全文載せる。
            evidence = [{k: s[k] for k in ["id", "path", "line", "end_line", "kind"]} for s in data["sources"]]
            lines += [value_html({"source_ids": evidence})]
            for source in data["sources"]:
                if source["kind"] in ["decision", "verification"]:
                    lines += [value_html(source)]
        for group in groups:
            lines += ["<h3>" + esc(group) + "</h3>"]
            if not data[group]:
                lines += ["<p>" + esc(data["applicability"].get(group, "—")) + "</p>"]
            for row in data[group]:
                lines += ["<article>" + value_html(display_row(row)) + "</article>"]
        lines += ["</section>"]
    lines += ["</body></html>", ""]
    return "\n".join(lines)


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def canonical(data):
    return json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def resolve(root, value):
    return (root / value).resolve()


def path_label(root, path):
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)


def source_args(items):
    result = []
    for item in items or []:
        try:
            val = json.loads(item)
        except (ValueError, TypeError):
            try:
                val = ast.literal_eval(item) if item.startswith("[") else item
            except (ValueError, SyntaxError):
                val = item
        if isinstance(val, list):
            result.extend(str(v) for v in val)
        else:
            result.extend(v.strip() for v in re.split(r"[,、\n]", str(val)) if v.strip())
    return result


def inspect(args):
    root = Path(args.root).resolve()
    selected = []
    candidates = source_args(args.source) or ["docs"]
    for value in candidates:
        path = resolve(root, value)
        if path.is_file():
            selected.append(path)
            continue
        if not path.is_dir():
            print("IN-01 資料が見つからない: " + value)
            return 3
        files = sorted(path.glob("*.md"))
        req = [p for p in files if re.search(r"requirement|要件", p.stem, re.I)]
        basic = [p for p in files if re.search(r"basic[-_]design|基本設計", p.stem, re.I)]
        if len(req) != 1 or len(basic) != 1 or req[0] == basic[0]:
            print("IN-01 要件と基本設計を一組に決められない。対象ファイルを指定する: " + value)
            return 3
        selected.extend([req[0], basic[0]])
    selected = list(dict.fromkeys(selected))
    inventory = []
    for path in selected:
        raw = path.read_bytes()
        lines = raw.decode("utf-8").splitlines()
        inventory.append({"path": path_label(root, path), "sha256": digest(raw),
                          "lines": len(lines), "headings": [
                              {"line": i, "text": line} for i, line in enumerate(lines, 1)
                              if re.match(r"^#{1,3} ", line)]})
    print(json.dumps({"sources": [r["path"] for r in inventory], "inventory": inventory},
                     ensure_ascii=False, indent=2))
    return 0


def cite(args):
    root = Path(args.root).resolve()
    path = resolve(root, args.path)
    raw = path.read_bytes()
    lines = raw.decode("utf-8").splitlines()
    end = args.end_line or args.line
    if not 1 <= args.line <= end <= len(lines):
        print("OUT-09 引用の行範囲が資料の範囲外である")
        return 2
    print(json.dumps({"id": args.id, "path": path_label(root, path), "line": args.line,
                      "end_line": end, "quote": "\n".join(lines[args.line - 1:end]),
                      "sha256": digest(raw), "kind": args.kind}, ensure_ascii=False, indent=2))
    return 0


def validate_schema(value, schema, where, errors):
    types = schema.get("type", [])
    types = [types] if isinstance(types, str) else types
    matches = {"object": isinstance(value, dict), "array": isinstance(value, list),
               "string": isinstance(value, str), "integer": isinstance(value, int) and not isinstance(value, bool),
               "boolean": isinstance(value, bool), "null": value is None}
    if types and not any(matches.get(t, False) for t in types):
        errors.append(("OUT-02", where + " の型が違う"))
        return
    if "enum" in schema and value not in schema["enum"]:
        errors.append(("OUT-02", where + " の値が定義された選択肢にない"))
    if isinstance(value, str):
        if schema.get("minLength", 0) and not value.strip():
            errors.append(("OUT-08", where + " が空欄である"))
        if not (where.startswith("design.sources[") and where.endswith(".quote")) and re.search(r"\b(?:TODO|TBD|FIXME)\b", value):
            errors.append(("OUT-08", where + " に仮置きが残っている"))
        if "pattern" in schema and not re.fullmatch(schema["pattern"], value):
            errors.append(("OUT-02", where + " の形式が違う"))
    if isinstance(value, int) and "minimum" in schema and value < schema["minimum"]:
        errors.append(("OUT-02", where + " が下限より小さい"))
    if isinstance(value, dict):
        props = schema.get("properties", {})
        for key in schema.get("required", []):
            if key not in value:
                errors.append(("OUT-02", where + "." + key + " がない"))
        for key, val in value.items():
            if key not in props:
                if schema.get("additionalProperties") is False:
                    errors.append(("OUT-02", where + "." + key + " は契約にない項目である"))
            else:
                validate_schema(val, props[key], where + "." + key, errors)
    if isinstance(value, list):
        if len(value) < schema.get("minItems", 0):
            errors.append(("OUT-02", where + " の件数が足りない"))
        for i, val in enumerate(value):
            validate_schema(val, schema.get("items", {}), where + "[" + str(i) + "]", errors)


def load_design(directory):
    return json.loads((directory / "design.json").read_text(encoding="utf-8"))


def validate(data, root, selected):
    errors = []
    schema = json.loads((Path(__file__).resolve().parent.parent / "assets/design.schema.json").read_text())
    validate_schema(data, schema, "design", errors)
    if errors:
        return errors
    ids = {}
    for group, (prefix, filename) in GROUPS.items():
        for row in data[group]:
            rid = row["id"]
            if not re.fullmatch(prefix + r"\d{3}", rid) or rid.endswith("000") or rid in ids:
                errors.append(("OUT-04", "IDの形または一意性が違う: " + rid))
            ids[rid] = (group, filename)
    reference_groups = {
        "source_ids": "sources", "adoption_evidence": "sources", "verification_evidence": "sources",
        "depends_on": "modules", "feature_ids": "features", "check_ids": "checks",
        "module_ids": "modules", "input_interface_ids": "interfaces", "interface_ids": "interfaces",
        "state_set_ids": "state_sets", "state_set_id": "state_sets", "table_ids": "tables",
        "screen_ids": "screens", "recovery_ids": "recovery", "issue_ids": "issues",
        "affected_ids": None, "condition_ids": None,
        "transition_id": "transitions",
    }
    def refs(obj, where):
        if isinstance(obj, dict):
            for key, val in obj.items():
                if key in reference_groups:
                    values = val if isinstance(val, list) else ([] if val is None else [val])
                    expected = reference_groups[key]
                    for rid in values:
                        if rid not in ids or (expected and ids[rid][0] != expected):
                            errors.append(("OUT-04", where + "." + key + " の参照先が違う: " + rid))
                else:
                    refs(val, where + "." + key)
        elif isinstance(obj, list):
            for i, val in enumerate(obj):
                refs(val, where + "[" + str(i) + "]")
    refs(data, "design")
    for group in OPTIONAL:
        if not data[group] and not data["applicability"].get(group, "").strip():
            errors.append(("OUT-02", group + " が非該当である理由がない"))
    state_sets = {r["id"]: [v["name"] for v in r["values"]] for r in data["state_sets"]}
    for row in data["state_sets"]:
        names = state_sets[row["id"]]
        if len(names) != len(set(names)):
            errors.append(("OUT-04", row["id"] + " に同じ状態名がある"))
    for row in data["transitions"]:
        allowed = state_sets.get(row["state_set_id"], [])
        if row["from"] not in allowed or row["to"] not in allowed:
            errors.append(("OUT-04", row["id"] + " が共通定義にない状態を使っている"))
    validate_contracts(data, state_sets, errors)
    for row in data["requirements"]:
        if row["status"] == "designed" and (not row["feature_ids"] or not row["check_ids"]):
            errors.append(("OUT-04", row["id"] + " の機能または確認条件がない"))
        if row["status"] == "blocked" and (not row["issue_ids"] or not row["check_ids"]):
            errors.append(("OUT-04", row["id"] + " の未決または確認条件がない"))
    checks = {r["id"]: r for r in data["checks"]}
    for row in data["features"]:
        for cid in row["check_ids"]:
            if cid in checks and row["id"] not in checks[cid]["feature_ids"]:
                errors.append(("OUT-04", row["id"] + " と " + cid + " の対応が片方向である"))
    source_map = {r["id"]: r for r in data["sources"]}
    for row in data["decisions"]:
        if row["kind"] == "inherited" and not row["source_ids"]:
            errors.append(("STEP-02", row["id"] + " の引継ぎ元がない"))
        if row["kind"] == "observed" and row["verification"] == "unverified":
            errors.append(("STEP-02", row["id"] + " は未検証の観測事実になっている"))
        if row["external_dependency"] and not row["issue_ids"] and row["verification"] != "passed":
            errors.append(("STEP-02", row["id"] + " の未検証の依存先に未決がない"))
        for field, wanted, active in [
            ("adoption_evidence", "decision", row["adoption"] == "accepted"),
            ("verification_evidence", "verification", row["verification"] in ["passed", "failed"]),
        ]:
            evidence = row[field]
            if active and (not evidence or any(source_map.get(k, {}).get("kind") != wanted for k in evidence)):
                errors.append(("STEP-02", row["id"] + " の採用判断または検証結果を支える証拠がない"))
    for row in data["changes"]:
        if row["adoption"] == "accepted" and not any(source_map.get(k, {}).get("kind") == "decision" for k in row["source_ids"]):
            errors.append(("STEP-02", row["id"] + " の変更判断の証拠がない"))
    source_paths = set()
    for row in data["sources"]:
        path = resolve(root, row["path"])
        source_paths.add(path)
        try:
            raw = path.read_bytes()
            lines = raw.decode("utf-8").splitlines()
            start, end = row["line"], row["end_line"]
            if digest(raw) != row["sha256"]:
                errors.append(("OUT-09", row["id"] + " の資料が引用時から変わっている"))
            if not 1 <= start <= end <= len(lines) or not row["quote"].strip() or row["quote"] not in "\n".join(lines[start - 1:end]):
                errors.append(("OUT-09", row["id"] + " の引用が指定した行にない"))
        except (OSError, UnicodeError) as exc:
            errors.append(("OUT-09", row["id"] + " の資料を読めない: " + str(exc)))
    for path in source_args(selected):
        if resolve(root, path) not in source_paths:
            errors.append(("OUT-09", "対象資料を根拠に含めていない: " + path))
    prefixes = {"sequence": "sequenceDiagram", "state": "stateDiagram-v2", "er": "erDiagram", "flowchart": "flowchart"}
    for row in data["diagrams"]:
        if not row["mermaid"].lstrip().startswith(prefixes[row["type"]]) or "```" in row["mermaid"]:
            errors.append(("OUT-02", row["id"] + " の図の種類かフェンスの書き方が違う"))
        if not row["condition_ids"] or not all(rid in ids and ids[rid][0] != "diagrams" for rid in row["condition_ids"]):
            errors.append(("OUT-16", row["id"] + " に配置できる説明対象がない"))
    return errors


def validate_contracts(data, state_sets, errors):
    """キー・境界項目・結果と遷移の対応を一つの定義から検査する。"""
    for table in data["tables"]:
        columns = {c["name"]: c for c in table["columns"]}
        if len(columns) != len(table["columns"]):
            errors.append(("OUT-13", table["id"] + " の列名が重複している"))
        keys = ([table["primary_key"]] if table["primary_key"] else []) + table["unique_keys"]
        signatures = []
        for key in keys:
            if len(key) != len(set(key)) or any(c not in columns for c in key):
                errors.append(("OUT-13", table["id"] + " のキー列が重複または未定義である"))
            signatures.append(tuple(sorted(key)))
        if len(signatures) != len(set(signatures)):
            errors.append(("OUT-13", table["id"] + " のキー構成が重複している"))
        if any(columns.get(c, {}).get("nullable", False) for c in table["primary_key"]):
            errors.append(("OUT-13", table["id"] + " の主キー列がNULL可である"))
        prose = [c["constraint"] for c in table["columns"]] + table["constraints"] + table["indexes"]
        if any(re.search(r"\bPRIMARY\s+KEY\b|\bUNIQUE\b|主キー|一意", s, re.I) for s in prose):
            errors.append(("OUT-13", table["id"] + " のキーはprimary_key・unique_keysだけで定義する"))
    transitions = {t["id"]: t for t in data["transitions"]}
    for interface in data["interfaces"]:
        rid = interface["id"]
        variants = [v["name"] for v in interface["response_variants"]]
        if len(variants) != len(set(variants)):
            errors.append(("OUT-14", rid + " の応答名が重複している"))
        for fields in [interface["request_fields"]] + [v["fields"] for v in interface["response_variants"]]:
            names = [f["path"] for f in fields]
            if len(names) != len(set(names)):
                errors.append(("OUT-14", rid + " の項目パスが重複している"))
        covered = set()
        signatures = []
        for effect in interface["state_effects"]:
            sid = effect["state_set_id"]
            covered.add(sid)
            signatures.append((sid, effect["from"], effect["outcome"]))
            states = state_sets.get(sid, [])
            if sid not in interface["state_set_ids"] or effect["from"] not in states or effect["to"] not in states or effect["outcome"] not in variants:
                errors.append(("OUT-15", rid + " の状態または応答名が定義と対応していない"))
            tid = effect["transition_id"]
            if tid is None:
                if effect["from"] != effect["to"]:
                    errors.append(("OUT-15", rid + " の状態変更に遷移の参照がない"))
            else:
                t = transitions.get(tid, {})
                if (t.get("state_set_id"), t.get("from"), t.get("to")) != (sid, effect["from"], effect["to"]):
                    errors.append(("OUT-15", rid + " の結果と " + tid + " の遷移が違う"))
        if len(signatures) != len(set(signatures)) or covered != set(interface["state_set_ids"]):
            errors.append(("OUT-15", rid + " の状態の対応が重複または不足している"))


def marker(body):
    return "<!-- generated-by: write-detailed-design-document; body-sha256: " + digest(body.encode()) + " -->\n" + body


def intact(text):
    first, sep, body = text.partition("\n")
    m = re.fullmatch(r"<!-- generated-by: write-detailed-design-document; body-sha256: ([a-f0-9]{64}) -->", first)
    return bool(sep and m and m.group(1) == digest(body.encode()))


def render_documents(data, root):
    english = data["language"] == "en"
    def tr(ja, en):
        return en if english else ja
    destinations = {r["id"]: filename for group, (_, filename) in GROUPS.items() for r in data[group]}
    rows_by_id = presentation.records(data)
    plans = presentation.plan(data, GROUPS, LABELS)
    for row in data["diagrams"]:
        destinations[row["id"]] = destinations.get(row["condition_ids"][0], "features.md") if row["condition_ids"] else "features.md"
    def figures(owner):
        lines = []
        for diagram in plans:
            if diagram["owner"] != owner:
                continue
            if diagram.get("author_id"):
                lines += ['<a id="' + diagram['author_id'] + '"></a>', '']
            lines += ["#### " + diagram["name"], "", diagram["explains"], "",
                      "<details><summary>Mermaidの記述を確認する</summary>", "", "```mermaid", diagram["mermaid"].rstrip(), "```", "", "</details>", "",
                      "![" + diagram["name"].replace("]", "") + "](diagrams/" + diagram["id"] + ".png)", "",
                      "Mermaid: [" + diagram["id"] + ".mmd](diagrams/" + diagram["id"] + ".mmd) — " + diagram["explains"], ""]
            for item in diagram.get("legend", []):
                lines += ["> " + item, ""]
        return lines
    def inline(value):
        if value is None:
            return tr("非該当", "Not applicable")
        if isinstance(value, bool):
            return str(value).lower()
        if isinstance(value, list):
            return "<br>".join(inline(v) for v in value) or tr("なし", "None")
        if isinstance(value, dict):
            return "<br>".join((str(k) if english else LABELS.get(k, str(k))) + ": " + inline(v) for k, v in value.items())
        value = str(value)
        if value in destinations:
            return "[" + value + "](" + destinations[value] + "#" + value + ") — " + presentation.excerpt(rows_by_id[value]).replace("|", "\\|").replace("\n", "<br>")
        return value.replace("|", "\\|").replace("\n", "<br>")
    def contextual_refs(row):
        ids = []
        def visit(value):
            if isinstance(value, dict):
                for key, item in value.items():
                    if key != "id":
                        visit(item)
            elif isinstance(value, list):
                for item in value:
                    visit(item)
            elif isinstance(value, str):
                candidates = [value] if value in rows_by_id and "quote" in rows_by_id[value] else (re.findall(r"\b[A-Z]+[0-9]+\b", value) if value not in rows_by_id else [])
                for rid in candidates:
                    if rid in rows_by_id and rid != row["id"] and rid not in ids:
                        ids.append(rid)
        visit(row)
        lines = []
        for rid in ids:
            target = rows_by_id[rid]
            lines += ["[" + rid + "](" + destinations[rid] + "#" + rid + ")", ""]
            lines += ["> " + line for line in presentation.excerpt(target).splitlines()]
            if "quote" in target:
                path = resolve(root, target["path"])
                lines += ["", "出典: [" + target["path"] + " " + str(target["line"]) + "行目](" + str(path).replace(" ", "%20") + ":" + str(target["line"]) + ":1)", ""]
            else:
                lines += [""]
        return lines
    def record(row):
        row = display_row(row)
        rid = row["id"]
        title = row.get("name", row.get("entity", row.get("target", row.get("question", rid))))
        lines = ['<a id="' + rid + '"></a>', "### " + rid + (" " + title if title != rid else ""), ""]
        if rid.startswith("S") and "quote" in row:
            path = resolve(root, row["path"])
            lines += ["[" + path.name + " " + str(row["line"]) + tr("行目", " line") + "](" + str(path).replace(" ", "%20") + ":" + str(row["line"]) + ":1)", ""]
            lines += ["> " + line for line in row["quote"].splitlines()]
            lines += ["", "SHA-256: `" + row["sha256"] + "` / " + row["kind"], ""]
            return lines + figures(rid)
        lines += ["| " + tr("項目", "Field") + " | " + tr("内容", "Detail") + " |", "| --- | --- |"]
        for key, val in row.items():
            if key not in ["id", "name", "columns"]:
                lines.append("| " + (key if english else LABELS.get(key, key)) + " | " + inline(val) + " |")
        if "columns" in row:
            keys = ["name", "type", "nullable", "default", "constraint", "reference", "state_set_id", "key_role"]
            lines += ["", "#### " + tr("物理列", "Physical columns"), "",
                      "| " + " | ".join(k if english else LABELS[k] for k in keys) + " |",
                      "| " + " | ".join("---" for _ in keys) + " |"]
            for col in row["columns"]:
                lines.append("| " + " | ".join(inline(col[k]) for k in keys) + " |")
        return lines + [""] + contextual_refs(row) + figures(rid)
    def feature(row):
        lines = ['<a id="' + row["id"] + '"></a>', "## " + row["id"] + " " + row["name"], ""]
        parts = [
            ("目的と根拠", "Purpose and evidence", [row["purpose"], inline(row["source_ids"]), inline(row["module_ids"])]),
            ("開始条件と入力", "Start conditions and input", row["preconditions"] + [inline(row["input_interface_ids"])]),
            ("処理の流れ", "Processing", [str(i) + ". " + v for i, v in enumerate(row["steps"], 1)] + [inline(row["table_ids"]), inline(row["state_set_ids"])]),
            ("結果", "Result", [row["result"], inline(row["screen_ids"])]),
            ("異常・競合・中断", "Errors, races and interruption", [row["failure"], inline(row["recovery_ids"]), inline(row["issue_ids"])]),
            ("確認方法", "Verification", [inline(row["check_ids"])])]
        for ja, en, content in parts:
            lines += ["### " + tr(ja, en), ""] + content + [""]
            if ja == "目的と根拠":
                lines += contextual_refs(row)
            if ja == "処理の流れ":
                lines += figures(row["id"])
        return lines
    bodies = {}
    index = ["# " + data["title"], "", data["overview"], "",
             tr("本書は設計書である。文書検査の通過は、採用承認・実装・結合試験の完了を意味しない。", "This is a design document. Passing document checks does not establish approval, implementation or integration test results."), "",
             "## " + tr("対象と状態", "Scope and status"), "", data["scope"], "",
             tr("対象外: ", "Excluded: ") + inline(data["scope_exclusions"]), "",
             tr("機能 / 要件 / 未決: ", "Features / requirements / open issues: ") + " / ".join(str(len(data[k])) for k in ["features", "requirements", "issues"]), "",
             "## " + tr("読む順序", "Reading order"), ""]
    for name, (ja, intro, _) in SECTIONS.items():
        index.append("- [" + (name if english else ja) + "](" + name + ") — " + intro)
    index += ["", "- [" + tr("分野別の閲覧と確認", "Review by area") + "](review.html)", "",
              tr("設計の正本: ", "Design source: ") + "[design.json](design.json)", "",
              "Design SHA-256: `" + digest(canonical(data)) + "`", ""]
    index += ["## " + tr("図の読み方", "Reading the diagrams"), "", data["diagram_notes"], ""]
    index += figures("overview")
    bodies["README.md"] = "\n".join(index)
    for filename, (title, intro, groups) in SECTIONS.items():
        lines = ["# " + (filename[:-3] if english else title), "", "[" + tr("入口に戻る", "Back to index") + "](README.md)", "",
                 tr(intro, "This section expands the shared design into implementable contracts and observable verification conditions."), ""]
        if filename == "common.md":
            lines += ["## " + tr("用語と時刻", "Terms and time"), "", data["time_policy"], ""]
            for term in data["terms"]:
                lines += ["- **" + term["name"] + "**: " + term["meaning"]]
            lines += [""]
        for group in groups:
            lines += ["## " + group, ""]
            if not data[group]:
                lines += [data["applicability"][group], ""]
            for row in data[group]:
                lines += feature(row) if group == "features" else record(row)
        bodies[filename] = "\n".join(lines)
    bodies["review.html"] = review_document(data)
    return {name: marker(body.rstrip() + "\n") for name, body in bodies.items()}


def checked(args, compare=True):
    root, directory = Path(args.root).resolve(), Path(args.directory).resolve()
    if not (directory / "design.json").is_file():
        return None, {}, [("OUT-01", "design.json がない")]
    try:
        data = load_design(directory)
    except (ValueError, UnicodeError) as exc:
        return None, {}, [("OUT-02", "design.json を読めない: " + str(exc))]
    errors = validate(data, root, args.source)
    if errors:
        return data, {}, errors
    docs = render_documents(data, root)
    for name, text in docs.items():
        maximum = 120 if name == "README.md" else 3000
        if len(text.splitlines()) > maximum:
            errors.append(("OUT-05", name + " が行数の上限を超える。対象範囲を分ける"))
        if compare:
            path = directory / name
            if not path.is_file():
                errors.append(("OUT-01", name + " がない"))
                continue
            actual = path.read_text(encoding="utf-8")
            if len(actual.splitlines()) > maximum:
                errors.append(("OUT-05", name + " が行数の上限を超える"))
                continue
            if any(line.startswith("> ") for line in text.splitlines()) and not any(line.startswith("> ") for line in actual.splitlines()):
                errors.append(("OUT-17", name + " に必要な参照先の引用がない"))
            if "```mermaid" in text and "```mermaid" not in actual:
                errors.append(("OUT-16", name + " に項目の図がない"))
            if not intact(actual):
                errors.append(("OUT-06", name + " は手書きか、生成後に編集されている"))
            elif actual != text:
                errors.append(("OUT-07", name + " がdesign.jsonの現在の内容と一致しない"))
    if compare:
        errors += presentation.check_pngs(presentation.plan(data, GROUPS, LABELS), directory)
    return data, docs, list(dict.fromkeys(errors))


def print_errors(errors):
    for rule, message in errors:
        print(rule + " " + message)


def render(args):
    data, docs, errors = checked(args, compare=False)
    directory = Path(args.directory).resolve()
    for name in docs:
        path = directory / name
        if path.exists() and not intact(path.read_text(encoding="utf-8")):
            errors.append(("OUT-06", name + " の手書き内容を上書きしない"))
    if errors:
        print_errors(errors)
        return 1
    images = presentation.render_pngs(presentation.plan(data, GROUPS, LABELS), directory)
    (directory / "diagrams").mkdir(exist_ok=True)
    for name, raw in images.items():
        (directory / name).write_bytes(raw)
    for path in (directory / "diagrams").iterdir():
        if "diagrams/" + path.name not in images:
            path.unlink()
    # 全ファイルの事前検査後に書く。途中のIO失敗後もcheckで欠落・不一致を検出できる。
    for name, text in docs.items():
        (directory / name).write_text(text, encoding="utf-8")
    print("生成した文書: " + str(len(docs)) + " 件 / Mermaid・PNG: " + str(len(images)//2) + " 組")
    print("保存先: " + str(directory) + " / 入口: " + str(directory / "README.md"))
    return 0


def check(args):
    data, _, errors = checked(args)
    if errors:
        print_errors(errors)
        return 1
    print("文書検査: 指摘0件 / 機能 " + str(len(data["features"])) + " / 要件 " + str(len(data["requirements"])) + " / 未決 " + str(len(data["issues"])))
    return 0


def report(args):
    data, _, errors = checked(args)
    if errors:
        print_errors(errors)
        return 1
    p = Path(args.directory).resolve() / "README.md"
    print("## 詳細設計書\n\n- [入口文書](" + str(p) + ")")
    print("- 機能 " + str(len(data["features"])) + " 件、要件 " + str(len(data["requirements"])) + " 件、確認条件 " + str(len(data["checks"])) + " 件")
    print("- 図 " + str(len(presentation.plan(data, GROUPS, LABELS))) + " 件をMermaidとPNGで保存している。")
    print("- 未決 " + str(len(data["issues"])) + " 件、要件変更 " + str(len(data["changes"])) + " 件")
    print("- 文書検査の通過と、採用判断・実装・実機検証の結果は別に記録している。")
    return 0


def read(args):
    """値を削らず、範囲を決めて意味の照合に使う。各ページは6,000文字以内。"""
    data = load_design(Path(args.directory).resolve())
    errors = validate(data, Path(args.root).resolve(), args.source)
    if errors:
        print_errors(errors)
        return 1
    areas = {key: {group: data[group] for group in groups} for key, (_, groups) in REVIEW_PARTS.items()}
    areas['overview'] = {key: data[key] for key in ['title', 'overview', 'scope', 'scope_exclusions', 'time_policy', 'diagram_notes', 'applicability']}
    areas['sources'] = data['sources']
    pages = {}
    for key, value in areas.items():
        body = json.dumps(value, ensure_ascii=False, indent=2)
        pieces, current = [], ''
        for line in body.splitlines(keepends=True):
            while len(line) > 6000:
                if current:
                    pieces.append(current)
                    current = ''
                pieces.append(line[:6000])
                line = line[6000:]
            if len(current) + len(line) > 6000:
                pieces.append(current)
                current = ''
            current += line
        if current:
            pieces.append(current)
        assert ''.join(pieces) == body
        pages[key] = pieces
    if args.area == 'list':
        print('分野別ページ数（全ページに元の値を省略せず収録）')
        for key, values in pages.items():
            print(key + ': ' + str(len(values)) + ' ページ')
        return 0
    values = pages[args.area]
    if not 1 <= args.page <= len(values):
        print('OUT-02 ページが範囲外である')
        return 2
    print(args.area + ' / page ' + str(args.page) + ' of ' + str(len(values)) + '（続くページも読む）\n')
    print(values[args.page-1])
    return 0


def sheets(args):
    _, _, errors = checked(args)
    if errors:
        print_errors(errors)
        return 1
    for path in presentation.sheets(Path(args.directory).resolve()):
        print(path)
    print('一覧の各図を確認し、文字が小さい図・多数の遷移・長いラベルは元PNGを開いて読む。台帳変更後は再生成して一覧も作り直す。')
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ["inspect", "cite", "render", "check", "report", "read", "sheets"]:
        p = commands.add_parser(name)
        p.add_argument("--root", default=".")
        if name == "cite":
            p.add_argument("--path", required=True)
            p.add_argument("--line", type=int, required=True)
            p.add_argument("--end-line", type=int)
            p.add_argument("--kind", choices=["requirement", "basic_design", "decision", "verification"], required=True)
            p.add_argument("--id", default="S001")
        else:
            p.add_argument("--source", action="append", default=[])
        if name in ["render", "check", "report", "read", "sheets"]:
            p.add_argument("--dir", dest="directory", required=True)
        if name == "read":
            p.add_argument("--area", choices=['list', 'overview', 'sources', *REVIEW_PARTS], default='list')
            p.add_argument("--page", type=int, default=1)
    args = parser.parse_args()
    try:
        return globals()[args.command](args)
    except (OSError, UnicodeError, ValueError) as exc:
        print("OUT-02 入出力を処理できない: " + str(exc))
        return 2


if __name__ == "__main__":
    sys.exit(main())
