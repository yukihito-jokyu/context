"""skill-foundation の実行時ランタイム。run.py と hook.py が使う。

Python 3.9 以上の標準ライブラリだけで動く。skill-foundation が作ったすべてのスキルに、同じ内容のまま
写される。スキルごとに書き換えない（skill_lint.py がハッシュで確かめる）。スキル固有の決まりは
assets/contract.json に書く。

方針: 入力（ユーザーの依頼・既存のファイル）には寛容に、出力（AI が書いたもの）には厳格にする。
  - 入力: キーの表記ゆれ・全角・大文字小文字・未知のキーを受け入れ、既定値で補い、補ったことを記録する
  - 出力: 契約（contract.json）に合わないものは、ルールID付きのエラーにする
"""

from __future__ import annotations

import datetime
import hashlib
import json
import os
import re
import subprocess
import sys
import unicodedata
from pathlib import Path

RUNTIME_VERSION = "1.0.0"
SKILL_DIR = Path(__file__).resolve().parent.parent
CONTRACT_REL = "assets/contract.json"
# 依頼に指定の無い入力の既定値。前の方が強く、null の項目は次へ進む（ユーザーの設定 → スキルの設定）
SETTINGS_FILES = [("user", "settings/user-setting.yaml"), ("skill", "settings/skill-setting.yaml")]
RUNS_DIRNAME = ".skill-runs"
# 出力の探索で入らないディレクトリ（パターンの固定部分に含まれる場合は入る）
SKIP_DIRS = {".git", ".hg", ".svn", "node_modules", ".venv", "venv", "__pycache__", ".pytest_cache",
             ".mypy_cache", ".ruff_cache", ".tox", ".next", ".turbo", ".cache", RUNS_DIRNAME}
CHECK_TYPES = ["headings", "require", "forbid", "max_lines", "min_lines", "line_length", "json_schema",
               "front_matter", "command"]
FORMAT_TYPES = ["trailing_space", "final_newline", "replace", "command"]
STATUSES = ["active", "waiting", "done", "failed", "aborted"]
ENFORCING = ("active",)
MAX_NOTES = 10


# ---------------------------------------------------------------- 基本

def now() -> str:
    return datetime.datetime.now().astimezone().isoformat(timespec="seconds")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def load_yaml(path: Path) -> object:
    """settings/ の設定（YAML）。標準ライブラリに YAML が無いので、設定に使う形だけを読む: 字下げの入れ子のマップ
    （`キー: 値`）、`- 値` と `[a, b]` の一覧、null・真偽・数・文字列（引用符の有無どちらも）、`#` から行末のコメント。
    中身が無ければ空のマップ。読めない形は行番号付きの ValueError にする。"""
    lines = []
    for no, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        text = _yaml_uncomment(raw).rstrip()
        if text.strip() in ("", "---", "..."):
            continue
        indent = len(text) - len(text.lstrip(" "))
        if text[indent] == "\t":
            raise ValueError(f"{no} 行目: 字下げにタブは使えません。空白で字下げしてください")
        lines.append((no, indent, text.strip()))
    if not lines:
        return {}
    value, end = _yaml_block(lines, 0, lines[0][1])
    if end < len(lines):
        raise ValueError(f"{lines[end][0]} 行目: 字下げが前の行と合いません")
    return value


def _yaml_uncomment(line: str) -> str:
    """`#` から行末のコメントを消す。引用符の中と、語の途中の `#` は残す。"""
    quote, i = None, 0
    while i < len(line):
        ch = line[i]
        if quote:
            if quote == '"' and ch == "\\":
                i += 1
            elif ch == quote:
                quote = None
        elif ch in "\"'" and (i == 0 or line[i - 1] in " \t[,:-"):
            quote = ch
        elif ch == "#" and (i == 0 or line[i - 1] in " \t"):
            return line[:i]
        i += 1
    return line


def _yaml_is_item(text: str) -> bool:
    return text == "-" or text.startswith("- ")


def _yaml_block(lines: list[tuple[int, int, str]], i: int, indent: int) -> tuple[object, int]:
    """字下げ indent の塊（マップか `- ` の一覧）を読み、値と、塊の次の行の位置を返す。"""
    if _yaml_is_item(lines[i][2]):
        items = []
        while i < len(lines) and lines[i][1] == indent and _yaml_is_item(lines[i][2]):
            no, rest = lines[i][0], lines[i][2][1:].strip()
            i += 1
            if rest:
                items.append(_yaml_scalar(rest, no))
            elif i < len(lines) and lines[i][1] > indent:
                value, i = _yaml_block(lines, i, lines[i][1])
                items.append(value)
            else:
                items.append(None)
        return items, i
    mapping: dict = {}
    while i < len(lines) and lines[i][1] == indent:
        no, _, text = lines[i]
        match = re.match(r'("(?:[^"\\]|\\.)*"|\'[^\']*\'|[^\s"\'\-][^:]*?)\s*:(?:\s+(.*))?$', text)
        if not match:
            raise ValueError(f"{no} 行目: `キー: 値` の形にしてください: {text}")
        key = _yaml_scalar(match.group(1), no) if match.group(1)[0] in "\"'" else match.group(1)
        if key in mapping:
            raise ValueError(f"{no} 行目: キー `{key}` が同じ塊に2回あります")
        rest, i = (match.group(2) or "").strip(), i + 1
        if rest:
            mapping[key] = _yaml_scalar(rest, no)
        elif i < len(lines) and (lines[i][1] > indent or (lines[i][1] == indent and _yaml_is_item(lines[i][2]))):
            mapping[key], i = _yaml_block(lines, i, lines[i][1])
        else:
            mapping[key] = None
    if i < len(lines) and lines[i][1] > indent:
        raise ValueError(f"{lines[i][0]} 行目: 字下げが前の行と合いません")
    return mapping, i


def _yaml_split(text: str) -> list[str]:
    """`[a, b]` の中身を、引用符の外の `,` で分ける。"""
    parts, quote, start, i = [], None, 0, 0
    while i < len(text):
        ch = text[i]
        if quote:
            if quote == '"' and ch == "\\":
                i += 1
            elif ch == quote:
                quote = None
        elif ch in "\"'":
            quote = ch
        elif ch == ",":
            parts.append(text[start:i])
            start = i + 1
        i += 1
    return parts + [text[start:]]


def _yaml_scalar(text: str, no: int) -> object:
    """1行の値: null・真偽・数・引用符の文字列・`[a, b]` の一覧。ほかは文字列のまま。"""
    text = text.strip()
    if text in ("", "~", "null", "Null", "NULL"):
        return None
    if text in ("true", "True", "TRUE", "false", "False", "FALSE"):
        return text.lower() == "true"
    if text.startswith("["):
        if not text.endswith("]"):
            raise ValueError(f"{no} 行目: `[` を同じ行の `]` で閉じてください: {text}")
        inner = text[1:-1].strip()
        return [_yaml_scalar(part, no) for part in _yaml_split(inner)] if inner else []
    if text.startswith("{"):
        if text.replace(" ", "") == "{}":
            return {}
        raise ValueError(f"{no} 行目: `{{...}}` の書き方は読めません。字下げで書いてください: {text}")
    if text.startswith('"'):
        try:
            return json.loads(text)
        except ValueError:
            raise ValueError(f"{no} 行目: 引用符の文字列が閉じていないか、読めない `\\` があります: {text}") from None
    if text.startswith("'"):
        if len(text) < 2 or not text.endswith("'"):
            raise ValueError(f"{no} 行目: 引用符の文字列が閉じていません: {text}")
        return text[1:-1].replace("''", "'")
    if re.fullmatch(r"[-+]?\d+", text):
        return int(text)
    if re.fullmatch(r"[-+]?(\d+\.\d*|\.\d+|\d+)([eE][-+]?\d+)?", text):
        return float(text)
    return text


def write_json(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def load_contract(skill_dir: Path = SKILL_DIR) -> dict:
    return load_json(skill_dir / CONTRACT_REL)


def project_root(start: Path) -> Path:
    """プロジェクトのルート。start から親へ辿って最初に .git がある場所、無ければ start 自身。"""
    current = start.resolve()
    if current.is_file():
        current = current.parent
    for candidate in [current, *current.parents]:
        if (candidate / ".git").exists():
            return candidate
    return current


def run_rel(name: str) -> str:
    return f"{RUNS_DIRNAME}/{name}"


def state_path(root: Path, name: str) -> Path:
    return root / RUNS_DIRNAME / name / "state.json"


def load_state(root: Path, name: str) -> dict | None:
    path = state_path(root, name)
    if not path.is_file():
        return None
    try:
        return load_json(path)
    except (json.JSONDecodeError, OSError):
        return None


def save_state(root: Path, state: dict) -> None:
    runs = root / RUNS_DIRNAME
    runs.mkdir(parents=True, exist_ok=True)
    ignore = runs / ".gitignore"
    if not ignore.exists():
        ignore.write_text("*\n", encoding="utf-8")  # 利用者の .gitignore を変えずに、実行記録を git から外す
    write_json(state_path(root, state["skill"]), state)


def log_event(state: dict, event: str, detail: str = "") -> None:
    state.setdefault("history", []).append({"at": now(), "event": event, "detail": detail[:500]})


# ---------------------------------------------------------------- パスと glob

def glob_to_regex(pattern: str) -> re.Pattern:
    """`**`、`*`、`?`、`{a,b}` に対応する glob を、ルートからの相対パス全体に一致する正規表現にする。"""
    out, i = [], 0
    while i < len(pattern):
        c = pattern[i]
        if c == "*":
            if pattern.startswith("**/", i):
                out.append("(?:.*/)?")
                i += 3
                continue
            if pattern.startswith("**", i):
                out.append(".*")
                i += 2
                continue
            out.append("[^/]*")
        elif c == "?":
            out.append("[^/]")
        elif c == "{" and "}" in pattern[i:]:
            end = pattern.index("}", i)
            out.append("(?:" + "|".join(re.escape(a) for a in pattern[i + 1:end].split(",")) + ")")
            i = end + 1
            continue
        else:
            out.append(re.escape(c))
        i += 1
    return re.compile("^" + "".join(out) + "$")


def matches_any(rel: str, patterns: list[str]) -> str | None:
    for pattern in patterns:
        if glob_to_regex(pattern).match(rel):
            return pattern
    return None


IN_PLACEHOLDER = re.compile(r"\{in:([A-Za-z0-9_]+)\}")


def expand(pattern: str, name: str, values: dict | None = None) -> str:
    """契約のパスの {run} を実行記録の置き場（.skill-runs/<name>）に、{in:キー} を入力の値に置き換える。"""
    expanded = pattern.replace("{run}", run_rel(name))
    expanded = IN_PLACEHOLDER.sub(lambda m: str((values or {}).get(m.group(1)) or m.group(0)), expanded)
    return expanded[2:] if expanded.startswith("./") else expanded


def static_prefix(pattern: str) -> str:
    parts = []
    for part in pattern.split("/")[:-1]:
        if any(ch in part for ch in "*?{["):
            break
        parts.append(part)
    return "/".join(parts)


def path_aliases(root: Path, pattern: str) -> list[str]:
    """pattern と、その固定の部分のシンボリックリンクを解決した書き方（例：.claude/skills → .agents/skills）。
    git と hooks は実体のパスで知らせるので、リンクを通した置き場の出力も照合できるようにする。"""
    prefix = static_prefix(pattern)
    if not prefix:
        return [pattern]
    try:
        real = (root / prefix).resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return [pattern]  # リンクの先がプロジェクトの外
    return [pattern] if real == prefix else [pattern, real + pattern[len(prefix):]]


def iter_glob(root: Path, pattern: str) -> list[str]:
    """pattern に一致するファイルの相対パス（POSIX 形式、昇順）。シンボリックリンクは辿らない。"""
    regex = glob_to_regex(pattern)
    prefix = static_prefix(pattern)
    base = root / prefix if prefix else root
    if not base.is_dir():
        return []
    found = []
    for dirpath, dirnames, filenames in os.walk(base, followlinks=False):
        rel_dir = Path(dirpath).relative_to(root).as_posix()
        rel_dir = "" if rel_dir == "." else rel_dir
        dirnames[:] = sorted(d for d in dirnames
                             if d not in SKIP_DIRS and d != ".skill-feedback" and not (Path(dirpath) / d).is_symlink())
        for f in filenames:
            rel = f"{rel_dir}/{f}" if rel_dir else f
            if regex.match(rel) and not (Path(dirpath) / f).is_symlink():
                found.append(rel)
    return sorted(found)


def snapshot(root: Path, contract: dict, name: str, values: dict | None = None) -> dict:
    files = {}
    for out in contract.get("outputs", []):
        for rel in iter_glob(root, expand(out["path"], name, values)):
            files[rel] = sha256(root / rel)
    return files


# ---------------------------------------------------------------- 入力の正規化（寛容）

def canon(text: str) -> str:
    """キーや選択肢を比べるための形。全角→半角、小文字、空白・-・_ を除く。"""
    return re.sub(r"[\s\-_]+", "", unicodedata.normalize("NFKC", str(text)).strip().lower())


TRUE_WORDS = {canon(w) for w in ["true", "yes", "y", "on", "1", "はい", "する", "あり", "有効"]}
FALSE_WORDS = {canon(w) for w in ["false", "no", "n", "off", "0", "いいえ", "しない", "なし", "無効"]}
KV_LINE = re.compile(r"^\s*([^:=：＝\s][^:=：＝]{0,40}?)\s*[:=：＝]\s*(.+?)\s*$")


def convert(value, spec: dict):
    """値を型に合わせて変換し、case（upper / lower）があれば文字列の大文字・小文字を揃える。変換できなければ ValueError。"""
    result = convert_type(value, spec)
    if isinstance(result, str) and spec.get("case") in ("upper", "lower"):
        result = result.upper() if spec["case"] == "upper" else result.lower()
    return result


def convert_type(value, spec: dict):
    kind = spec.get("type", "string")
    if isinstance(value, str):
        value = value.strip()
    if kind == "string":
        return str(value)
    if kind == "int":
        return int(unicodedata.normalize("NFKC", str(value)).replace(",", ""))
    if kind == "bool":
        if isinstance(value, bool):
            return value
        word = canon(value)
        if word in TRUE_WORDS:
            return True
        if word in FALSE_WORDS:
            return False
        raise ValueError(f"真偽値として読めません: {value!r}")
    if kind == "list":
        if isinstance(value, list):
            return [str(v).strip() for v in value if str(v).strip()]
        return [v.strip() for v in re.split(r"[,、，\n]+", str(value)) if v.strip()]
    if kind == "enum":
        choices = spec.get("enum", [])
        aliases = {canon(k): v for k, v in spec.get("enum_aliases", {}).items()}
        for choice in choices:
            if canon(choice) == canon(value):
                return choice
        if canon(value) in aliases:
            return aliases[canon(value)]
        raise ValueError(f"{choices} のどれでもありません: {value!r}")
    if kind == "path":
        return Path(str(value)).as_posix()
    if kind == "slug":
        slug = re.sub(r"[^a-z0-9]+", "-", unicodedata.normalize("NFKC", str(value)).lower()).strip("-")
        if not slug:
            raise ValueError(f"英数字を含まないので slug にできません: {value!r}")
        return slug
    raise ValueError(f"未知の type: {kind}")


def load_settings(skill_dir: Path = SKILL_DIR) -> tuple[list[tuple[str, dict]], list[str]]:
    """settings/ の設定（YAML）を強い順に返す。無いファイルは飛ばし、読めないファイルは注意にして飛ばす。"""
    layers, warnings = [], []
    for source, rel in SETTINGS_FILES:
        path = skill_dir / rel
        if not path.is_file():
            continue
        try:
            data = load_yaml(path)
        except (OSError, ValueError) as exc:
            warnings.append(f"{rel}: YAML として読めないので使いません（{exc}）")
            continue
        if isinstance(data, dict):
            layers.append((source, data))
        else:
            warnings.append(f"{rel}: オブジェクトでないので使いません")
    return layers, warnings


def normalize_input(raw: dict, text: str, contract: dict, settings: list[tuple[str, dict]] | None = None,
                    guessed: dict | None = None) -> dict:
    """依頼から受け取った値を契約の inputs に合わせる。エラーにせず、補ったこと・読めなかったことを記録する。
    依頼に無い値は、設定（settings の強い順）→ 依頼文からの推定（guessed）→ default_by（前の入力から決まる値）→ default の順に補い、
    補った元を default_from に残す。"""
    specs = contract.get("inputs", [])
    by_canon = {}
    for spec in specs:
        for word in [spec["key"], spec.get("label", ""), *spec.get("aliases", [])]:
            if word:
                by_canon[canon(word)] = spec["key"]
    given, extra = {}, {}
    # 自由記述の中の「キー: 値」の行も拾う（明示の指定が優先）
    for line in text.splitlines():
        match = KV_LINE.match(line)
        if match and canon(match.group(1)) in by_canon:
            given.setdefault(by_canon[canon(match.group(1))], match.group(2))
    for key, value in raw.items():
        target = by_canon.get(canon(key))
        if target:
            given[target] = value
        else:
            extra[key] = value
    guesses = {by_canon[canon(k)]: v for k, v in (guessed or {}).items() if canon(k) in by_canon}
    where = {**dict(SETTINGS_FILES), "guess": "--guess", "derived": "default_by", "default": "default"}
    values, defaulted, default_from, questions, warnings = {}, [], {}, [], []
    for spec in specs:
        key = spec["key"]
        unread = None
        if key in given and str(given[key]).strip() != "":
            try:
                values[key] = convert(given[key], spec)
                continue
            except ValueError as exc:
                unread = given[key]
                warnings.append(f"{key}: {exc}。設定か既定値があれば補い、無ければそのまま使います")
        candidates = [(source, data["inputs"].get(key)) for source, data in settings or []
                      if isinstance(data.get("inputs"), dict)]
        candidates.append(("guess", guesses.get(key)))
        by = spec.get("default_by") or {}
        if by.get("input") in values:
            ref = values[by["input"]]
            candidates.append(("derived", by.get("values", {}).get(",".join(sorted(ref)) if isinstance(ref, list) else str(ref))))
        candidates.append(("default", spec.get("default")))
        for source, value in candidates:
            if value is None or value == [] or str(value).strip() == "":
                continue
            try:
                values[key] = convert(value, spec)
            except ValueError as exc:
                warnings.append(f"{key}: {where[source]} の値が使えません（{exc}）。次の候補で補います")
                continue
            defaulted.append(key)
            default_from[key] = source
            break
        else:
            if unread is not None:
                values[key] = unread
            elif spec.get("ask"):
                questions.append(f"{spec.get('label', key)}（{key}）: {spec.get('question', '値を確かめる')}")
            else:
                values[key] = None
    return {"values": values, "defaulted": defaulted, "default_from": default_from, "questions": questions,
            "warnings": warnings, "extra": extra, "text": text}


# ---------------------------------------------------------------- 出力の検査（厳格）

HEADING = re.compile(r"^(#{1,6})\s+(.*?)\s*#*\s*$")
FENCE = re.compile(r"^\s*(```|~~~)")


def finding(rule: str, path: str, line: int, message: str) -> dict:
    return {"rule": rule, "path": path, "line": line, "message": message}


def format_finding(f: dict) -> str:
    where = f"{f['path']}:{f['line']}" if f["line"] else f["path"]
    return f"{f['rule']} {where} {f['message']}"


def code_mask(lines: list[str]) -> list[bool]:
    """各行がコードフェンスの中（フェンス行を含む）かどうか。"""
    mask, inside = [], False
    for line in lines:
        if FENCE.match(line):
            mask.append(True)
            inside = not inside
            continue
        mask.append(inside)
    return mask


def headings(lines: list[str]) -> list[tuple[int, int, str]]:
    mask = code_mask(lines)
    result = []
    for i, line in enumerate(lines):
        if mask[i]:
            continue
        match = HEADING.match(line)
        if match:
            result.append((i + 1, len(match.group(1)), match.group(2)))
    return result


def front_matter(lines: list[str]) -> dict | None:
    if not lines or lines[0].strip() != "---":
        return None
    keys = {}
    for line in lines[1:]:
        if line.strip() == "---":
            return keys
        match = re.match(r"^([A-Za-z0-9_\-]+)\s*:\s*(.*)$", line)
        if match:
            keys[match.group(1)] = match.group(2).strip()
    return None


def schema_errors(value, schema: dict, where: str = "$") -> list[str]:
    """JSON Schema の部分集合（type, enum, const, required, properties, additionalProperties, items,
    pattern, minLength, maxLength, minimum, maximum, minItems, maxItems）で検査する。"""
    errors = []
    types = schema.get("type")
    if types:
        names = types if isinstance(types, list) else [types]
        checks = {"object": lambda v: isinstance(v, dict), "array": lambda v: isinstance(v, list),
                  "string": lambda v: isinstance(v, str), "boolean": lambda v: isinstance(v, bool),
                  "integer": lambda v: isinstance(v, int) and not isinstance(v, bool),
                  "number": lambda v: isinstance(v, (int, float)) and not isinstance(v, bool),
                  "null": lambda v: v is None}
        if not any(checks.get(n, lambda v: False)(value) for n in names):
            return [f"{where}: 型が {names} ではありません"]
    if "enum" in schema and value not in schema["enum"]:
        errors.append(f"{where}: {schema['enum']} のどれでもありません")
    if "const" in schema and value != schema["const"]:
        errors.append(f"{where}: {schema['const']!r} ではありません")
    if isinstance(value, str):
        if "pattern" in schema and not re.search(schema["pattern"], value):
            errors.append(f"{where}: /{schema['pattern']}/ に一致しません")
        if len(value) < schema.get("minLength", 0):
            errors.append(f"{where}: {schema['minLength']} 文字以上必要です")
        if "maxLength" in schema and len(value) > schema["maxLength"]:
            errors.append(f"{where}: {schema['maxLength']} 文字以下にしてください")
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if "minimum" in schema and value < schema["minimum"]:
            errors.append(f"{where}: {schema['minimum']} 以上にしてください")
        if "maximum" in schema and value > schema["maximum"]:
            errors.append(f"{where}: {schema['maximum']} 以下にしてください")
    if isinstance(value, dict):
        for key in schema.get("required", []):
            if key not in value:
                errors.append(f"{where}: キー {key} がありません")
        props = schema.get("properties", {})
        for key, item in value.items():
            if key in props:
                errors += schema_errors(item, props[key], f"{where}.{key}")
            elif schema.get("additionalProperties") is False:
                errors.append(f"{where}: 決められていないキー {key} があります")
    if isinstance(value, list):
        if len(value) < schema.get("minItems", 0):
            errors.append(f"{where}: {schema['minItems']} 件以上必要です")
        if "maxItems" in schema and len(value) > schema["maxItems"]:
            errors.append(f"{where}: {schema['maxItems']} 件以下にしてください")
        if "items" in schema:
            for i, item in enumerate(value):
                errors += schema_errors(item, schema["items"], f"{where}[{i}]")
    return errors


def format_file(root: Path, rel: str, out: dict, name: str, skill_dir: Path,
                values: dict | None = None) -> tuple[list[dict], list[dict]]:
    """契約の format で出力ファイル1つを自動で直す（段 format）。戻り値は（直したもの, 直せなかった指摘）。"""
    path, fixes, problems = root / rel, [], []
    for fix in out.get("format", []):
        rule, kind = fix["rule"], fix["type"]
        if kind == "command":
            before = sha256(path)
            code, output = run_shell(fill_command(fix["run"], root, name, skill_dir, values, rel), root, int(fix.get("timeout", 60)))
            if code != 0:
                problems.append(finding(rule, rel, 0, f"整形のコマンドが失敗しました: {tail(output, 5)}"))
            elif path.is_file() and sha256(path) != before:
                fixes.append(finding(rule, rel, 0, fix.get("message") or f"`{fix['run']}` で整えました"))
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            return fixes, problems
        if kind == "trailing_space":
            new, what = re.sub(r"[ \t]+$", "", text, flags=re.M), "行末の空白を消しました"
        elif kind == "final_newline":
            new, what = (text.rstrip("\n") + "\n") if text.strip() else text, "末尾の改行を1つにしました"
        else:
            source = IN_PLACEHOLDER.sub(lambda m: re.escape(str((values or {}).get(m.group(1), ""))), fix["pattern"])
            new, what = re.sub(source, fix.get("with", ""), text, flags=re.M), f"/{fix['pattern']}/ を「{fix.get('with', '')}」に置き換えました"
        if new != text:
            path.write_text(new, encoding="utf-8")
            fixes.append(finding(rule, rel, 0, fix.get("message") or what))
    return fixes, problems


def format_fix(f: dict) -> str:
    """自動で直したことの1行。指摘（ルールIDで始まる行）と見分けられるよう「整形」で始める。"""
    return f"整形 {f['rule']} {f['path']} {f['message']}"


def record_fixes(state: dict, fixes: list[dict]) -> None:
    done = state.setdefault("formatted", [])
    for f in fixes:
        item = f"{f['rule']} {f['path']}"
        if item not in done:
            done.append(item)


def selected_lines(spec, count: int) -> list[int]:
    if spec in (None, "all"):
        return list(range(1, count + 1))
    if spec == "first":
        return [1] if count else []
    return [n for n in spec if 1 <= n <= count]


def check_file(root: Path, rel: str, out: dict, name: str, skill_dir: Path, values: dict | None = None,
               edit: bool = False) -> list[dict]:
    """出力ファイル1つを、契約の checks で検査する。edit（編集の直後の検査）では stage: finish の検査を飛ばす。"""
    path = root / rel
    try:
        text = "" if out.get("binary") else path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return [finding(out.get("rule", "OUT"), rel, 0, "UTF-8 のテキストとして読めません")]
    lines = text.splitlines()
    findings = []
    pattern = out.get("name_pattern")
    if pattern and not re.search(pattern, Path(rel).name):
        findings.append(finding(out.get("rule", "OUT"), rel, 0, f"ファイル名が /{pattern}/ に一致しません"))
    for check in out.get("checks", []):
        if edit and check.get("stage") == "finish":
            continue
        rule, kind = check["rule"], check["type"]
        if out.get("binary") and kind != "command":
            findings.append(finding(rule, rel, 0, "binary の出力には command の検査を指定してください"))
            continue
        message = check.get("message", "")
        suffix = f"（{message}）" if message else ""
        if kind == "headings":
            level = check.get("level")
            found = [(n, t) for n, lv, t in headings(lines) if level is None or lv == level]
            titles = [t for _, t in found]
            if "equals" in check and titles != check["equals"]:
                findings.append(finding(rule, rel, found[0][0] if found else 0,
                                        f"見出し（レベル {level}）が {check['equals']} と一致しません。今: {titles}{suffix}"))
            if "includes" in check:
                it = iter(titles)
                if not all(any(t == want for t in it) for want in check["includes"]):
                    findings.append(finding(rule, rel, 0, f"見出し {check['includes']} がこの順で揃っていません。今: {titles}{suffix}"))
        elif kind in ("require", "forbid"):
            source = IN_PLACEHOLDER.sub(lambda m: re.escape(str((values or {}).get(m.group(1), ""))), check["pattern"])
            regex = re.compile(source, re.M)
            mask = code_mask(lines) if check.get("ignore_code") else [False] * len(lines)
            scope = set(selected_lines(check.get("lines"), len(lines)))
            hits = [i + 1 for i, line in enumerate(lines) if i + 1 in scope and not mask[i] and regex.search(line)]
            if check.get("multiline"):
                body = "\n".join("" if mask[i] else line for i, line in enumerate(lines))
                hits = [body[:m.start()].count("\n") + 1 for m in regex.finditer(body)]
            if kind == "forbid":
                for n in hits:
                    findings.append(finding(rule, rel, n, f"/{check['pattern']}/ は使えません{suffix}: {lines[n - 1].strip()[:80]}"))
            else:
                low, high = check.get("min", 1), check.get("max")
                if len(hits) < low or (high is not None and len(hits) > high):
                    span = f"{low} 回以上" + (f" {high} 回以下" if high is not None else "")
                    findings.append(finding(rule, rel, 0, f"/{check['pattern']}/ が {span} 必要です（今 {len(hits)} 回）{suffix}"))
        elif kind == "max_lines" and len(lines) > check["value"]:
            findings.append(finding(rule, rel, check["value"] + 1, f"{check['value']} 行以下にしてください（今 {len(lines)} 行）{suffix}"))
        elif kind == "min_lines" and len(lines) < check["value"]:
            findings.append(finding(rule, rel, 0, f"{check['value']} 行以上必要です（今 {len(lines)} 行）{suffix}"))
        elif kind == "line_length":
            for n in selected_lines(check.get("lines"), len(lines)):
                width = len(lines[n - 1])
                if width > check["max"]:
                    findings.append(finding(rule, rel, n, f"1行は {check['max']} 文字以下にしてください（今 {width} 文字）{suffix}"))
        elif kind == "json_schema":
            try:
                data = json.loads(text)
            except json.JSONDecodeError as exc:
                findings.append(finding(rule, rel, exc.lineno, f"JSON として読めません: {exc.msg}"))
                continue
            for error in schema_errors(data, check["schema"]):
                findings.append(finding(rule, rel, 0, error + suffix))
        elif kind == "front_matter":
            keys = front_matter(lines)
            if keys is None:
                findings.append(finding(rule, rel, 1, f"先頭に --- で囲んだ front matter が必要です{suffix}"))
            else:
                for key in check.get("required_keys", []):
                    if not keys.get(key):
                        findings.append(finding(rule, rel, 1, f"front matter に {key} がありません{suffix}"))
        elif kind == "command":
            command = fill_command(check["run"], root, name, skill_dir, values, rel)
            code, output = run_shell(command, root, int(check.get("timeout", 60)))
            if code != 0:
                passed = [l for l in output.splitlines() if re.match(r"^[A-Z]{2,6}-\d{2,3}\s", l)]
                if passed:
                    findings += [{"rule": l.split()[0], "path": rel, "line": 0, "message": l, "raw": True} for l in passed]
                else:
                    findings.append(finding(rule, rel, 0, f"検査コマンドが失敗しました{suffix}: {tail(output, 5)}"))
    return findings


def check_outputs(root: Path, state: dict, contract: dict, skill_dir: Path = SKILL_DIR,
                  only: str | None = None, fixes: list | None = None) -> tuple[list[dict], dict]:
    """契約の出力を、format で直してから検査する。only を渡すとそのファイルだけを検査し、件数は見ない。
    戻り値は（指摘の一覧, 出力ID → 変わったファイルの一覧）。直したものは fixes に足す。"""
    fixes = [] if fixes is None else fixes
    name = state["skill"]
    values = state.get("input", {})
    baseline = state.get("baseline", {})
    findings, changed_by_output = [], {}
    for out in contract.get("outputs", []):
        pattern = expand(out["path"], name, values)
        rule = out.get("rule", "OUT")
        if only is not None:
            if any(glob_to_regex(p).match(only) for p in path_aliases(root, pattern)) and (root / only).is_file():
                fixed, problems = format_file(root, only, out, name, skill_dir, values)
                fixes += fixed
                findings += problems + check_file(root, only, out, name, skill_dir, values, edit=True)
            continue
        changed = [rel for rel in iter_glob(root, pattern) if baseline.get(rel) != sha256(root / rel)]
        changed_by_output[out["id"]] = changed
        count = out.get("count", {})
        low = count.get("min", 1 if out.get("required", True) else 0)
        high = count.get("max")
        if len(changed) < low:
            findings.append(finding(rule, pattern, 0, f"出力 {out['id']}（{out.get('label', '')}）を {low} 件以上作ってください（今 {len(changed)} 件）"))
        if high is not None and len(changed) > high:
            findings.append(finding(rule, pattern, 0, f"出力 {out['id']} は {high} 件以下です（今 {len(changed)} 件: {', '.join(changed[:5])}）"))
        for rel in changed:
            fixed, problems = format_file(root, rel, out, name, skill_dir, values)
            fixes += fixed
            findings += problems + check_file(root, rel, out, name, skill_dir, values)
    if only is None:
        for group in contract.get("together", []):
            ids = group.get("outputs", [])
            touched = [i for i in ids if changed_by_output.get(i)]
            if touched and len(touched) < len(ids):
                missing = [i for i in ids if i not in touched]
                note = f"（{group['message']}）" if group.get("message") else ""
                findings.append(finding(group.get("rule", "OUT"), ", ".join(missing), 0,
                                        f"出力 {', '.join(touched)} を変えたので、{', '.join(missing)} も一緒に変えてください{note}"))
        findings += notes_findings(root, name, contract)
    elif only == notes_rel(name):
        findings += notes_findings(root, name, contract)
    return findings, changed_by_output


def notes_rel(name: str) -> str:
    """決めきれなかったことを AI が書くファイル。finish が報告の「## 補足」に入れる（RPT-01）。"""
    return f"{run_rel(name)}/notes.md"


def read_notes(root: Path, name: str) -> list[str]:
    path = root / notes_rel(name)
    if not path.is_file():
        return []
    return [line.rstrip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def notes_findings(root: Path, name: str, contract: dict) -> list[dict]:
    """notes.md は「- 」で始まる箇条書きだけで、MAX_NOTES 項目まで。自由な文や見出しを報告に混ぜない。"""
    rule = contract.get("report", {}).get("rule", "RPT")
    rel = notes_rel(name)
    if not (root / rel).is_file():
        return []
    try:
        lines = (root / rel).read_text(encoding="utf-8").splitlines()
    except UnicodeDecodeError:
        return [finding(rule, rel, 0, "UTF-8 のテキストとして読めません")]
    result = [finding(rule, rel, n, f"補足は「- 」で始まる箇条書きの行だけにしてください: {line.strip()[:60]}")
              for n, line in enumerate(lines, 1) if line.strip() and not re.match(r"^- \S", line)]
    items = sum(1 for line in lines if line.strip())
    if items > MAX_NOTES:
        result.append(finding(rule, rel, 0, f"補足は {MAX_NOTES} 項目以下にしてください（今 {items} 項目）"))
    return result


def fill_command(template: str, root: Path, name: str, skill_dir: Path, values: dict | None, rel: str | None = None) -> str:
    """契約のコマンドの {file}・{skill}・{root}・{run}・{in:キー} を、シェルで安全な形に置き換える。"""
    command = (template.replace("{skill}", shell_quote(str(skill_dir))).replace("{root}", shell_quote(str(root)))
               .replace("{run}", shell_quote(run_rel(name))))
    if rel is not None:
        command = command.replace("{file}", shell_quote(rel))
    return IN_PLACEHOLDER.sub(lambda m: shell_quote(str((values or {}).get(m.group(1), ""))), command)


def report_sections(root: Path, state: dict, contract: dict, skill_dir: Path = SKILL_DIR,
                    stage: str = "finish") -> tuple[list[str], list[dict]]:
    """契約の report.sections のコマンドを実行し、その出力（Markdown の節）を返す。失敗は指摘にする。
    stage: finish の節（終えるときだけ行うもの）は、check からは実行しない。"""
    rule = contract.get("report", {}).get("rule", "RPT")
    texts, findings = [], []
    for i, section in enumerate(contract.get("report", {}).get("sections", []), 1):
        if section.get("stage") == "finish" and stage != "finish":
            continue
        command = fill_command(section["run"], root, state["skill"], skill_dir, state.get("input", {}))
        code, output = run_shell(command, root, int(section.get("timeout", 120)))
        if code != 0:
            findings.append(finding(rule, f"report.sections[{i}]", 0, f"報告の節を作るコマンドが失敗しました: {tail(output, 5)}"))
        else:
            texts.append(output.strip())
    return texts, findings


# ---------------------------------------------------------------- 外部コマンド

def shell_quote(text: str) -> str:
    if os.name == "nt":
        return '"' + text.replace('"', '\\"') + '"'
    return "'" + text.replace("'", "'\"'\"'") + "'"


def run_shell(command: str, cwd: Path, timeout: int) -> tuple[int, str]:
    try:
        proc = subprocess.run(command, cwd=cwd, shell=True, capture_output=True, text=True, timeout=timeout)
        return proc.returncode, (proc.stdout or "") + (proc.stderr or "")
    except subprocess.TimeoutExpired:
        return 124, f"[timeout] {timeout} 秒で打ち切りました"


def tail(text: str, lines: int = 20) -> str:
    return "\n".join(text.rstrip().splitlines()[-lines:])


def emit(text: str, stream=None) -> None:
    (stream or sys.stdout).write(text if text.endswith("\n") else text + "\n")
