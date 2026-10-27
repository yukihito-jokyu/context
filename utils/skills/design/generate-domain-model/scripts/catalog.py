#!/usr/bin/env python3
"""Mermaid原本からPNGとHTMLを生成し、カタログ全体を検査する。

決定: STEP-01、STEP-02、STEP-03、STEP-04、OUT-01、OUT-02、OUT-04、
OUT-05、OUT-06、OUT-07、OUT-08。Python 3.9以上の標準ライブラリを使う。
使い方: python3 catalog.py inspect|build|check|report <directory> [--update]
        python3 catalog.py deps [--mmdc /path/to/mmdc]
終了コード: 0 成功、1 出力への指摘、2 引数・依存・実行の誤り。
"""
import argparse
import hashlib
import html
import json
import os
from pathlib import Path
import re
import shutil
import struct
import subprocess
import sys
import tempfile
import zlib


SLUG = re.compile(r"[a-z][a-z0-9]*(?:-[a-z0-9]+)*\Z")
FORBIDDEN = re.compile(
    r"skip ci|ci skip|eslint-disable|noqa|type:\s*ignore|validation:\s*false",
    re.I,
)
FONT = "Hiragino Kaku Gothic ProN, Noto Sans JP, sans-serif"
CONFIG = {"securityLevel": "strict", "theme": "neutral", "fontFamily": FONT}
SKILL = Path(__file__).resolve().parent.parent


class Finding(Exception):
    def __init__(self, rule, message):
        super().__init__(message)
        self.rule = rule


def require(condition, rule, message):
    if not condition:
        raise Finding(rule, message)


def dump(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n"


def digest(data):
    return hashlib.sha256(data).hexdigest()


def keys(value, expected, label):
    require(isinstance(value, dict) and set(value) == set(expected),
            "OUT-02", label + " のキーは " + ", ".join(expected) + " にする")


def text_value(value):
    return isinstance(value, str) and bool(value.strip())


def read_json(path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, UnicodeError) as exc:
        raise Finding("OUT-02", path.name + " をJSONとして読めない: " + str(exc)) from exc


def checked_root(directory):
    root = Path(directory).absolute()
    require(not root.is_symlink(), "OUT-01", "カタログのディレクトリにシンボリックリンクを使わない")
    if root.exists():
        for path in root.rglob("*"):
            require(not path.is_symlink(), "OUT-01", "出力にシンボリックリンクを使わない: " + path.name)
    return root


def load_catalog(root, canonical=False):
    path = root / "catalog.json"
    require(path.is_file(), "OUT-01", "catalog.json がない")
    data = read_json(path)
    keys(data, ["schema_version", "name", "title", "diagrams"], "catalog.json")
    require(data["schema_version"] == 1 and type(data["schema_version"]) is int,
            "OUT-02", "schema_version は 1 にする")
    require(text_value(data["name"]) and SLUG.fullmatch(data["name"]) and len(data["name"]) <= 64,
            "OUT-04", "name は64文字以下の英小文字から始まるslugにする")
    require(data["name"] == root.name, "OUT-04", "name とディレクトリ名を一致させる")
    require(text_value(data["title"]), "OUT-05", "カタログの題名が空である")
    require(isinstance(data["diagrams"], list), "OUT-02", "diagrams は配列にする")
    require(1 <= len(data["diagrams"]) <= 1000, "OUT-05", "図は1〜1000件にする")
    ids = []
    for item in data["diagrams"]:
        keys(item, ["id", "title", "description", "terms", "sources", "unresolved"], "diagrams の図")
        ident = item["id"]
        require(text_value(ident) and SLUG.fullmatch(ident) and len(ident) <= 64,
                "OUT-04", "図のidは64文字以下のslugにする")
        ids.append(ident)
        require(text_value(item["title"]) and text_value(item["description"]),
                "OUT-05", ident + " の題名と説明を空にしない")
        for field in ("terms", "unresolved"):
            require(isinstance(item[field], list) and all(text_value(v) for v in item[field]),
                    "OUT-02", ident + "." + field + " は空でない文字列の配列にする")
        require(isinstance(item["sources"], list), "OUT-02", ident + ".sources は配列にする")
        require(bool(item["sources"]), "OUT-05", ident + " に根拠を1件以上書く")
        for source in item["sources"]:
            keys(source, ["path", "quote"], "sources")
            require(text_value(source["path"]) and text_value(source["quote"]),
                    "OUT-05", ident + " の参照先と実際の記述を空にしない")
    require(len(ids) == len(set(ids)), "OUT-04", "図のidが重複している")
    require(not FORBIDDEN.search(json.dumps(data, ensure_ascii=False)),
            "OUT-08", "検査を止める記法がある")
    if canonical:
        require(ids == sorted(ids), "OUT-04", "図をidの昇順にする")
        for item in data["diagrams"]:
            require(item["terms"] == sorted(set(item["terms"])), "OUT-04", "terms を重複なしの昇順にする")
        require(path.read_text(encoding="utf-8") == dump(data), "OUT-04", "JSONはキーの昇順・2空白・末尾改行で書く")
    return data


def bundle_paths(data):
    files = {"catalog.json", "index.html", "validation.json"}
    for item in data["diagrams"]:
        files.update({"diagrams/" + item["id"] + ".mmd", "images/" + item["id"] + ".png"})
    return files


def check_files(root, data, complete):
    wanted = bundle_paths(data)
    actual = {p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file()}
    require(not actual - wanted, "OUT-01", "未登録のファイルがある: " + ", ".join(sorted(actual - wanted)))
    if complete:
        require(actual == wanted, "OUT-01", "対応するファイルがない: " + ", ".join(sorted(wanted - actual)))


def read_mermaid(root, ident):
    path = root / "diagrams" / (ident + ".mmd")
    require(path.is_file(), "OUT-01", "Mermaid原本がない: " + ident)
    try:
        source = path.read_text(encoding="utf-8")
    except UnicodeError as exc:
        raise Finding("OUT-02", "Mermaid原本はUTF-8で書く: " + ident) from exc
    require(source.splitlines() and source.splitlines()[0].strip() == "classDiagram",
            "OUT-02", ident + " の先頭行を classDiagram にする")
    require(not FORBIDDEN.search(source) and "%%{" not in source
            and not re.search(r"^\s*(click|link)\s", source, re.M),
            "OUT-08", ident + " に初期化・リンク・検査を止める記法がある")
    require(bool(re.search(r"^\s*class\s+\S+", source, re.M)), "OUT-02", ident + " に概念のclass定義がない")
    return source


def concept_terms(source):
    """Derive search terms from declarations instead of an author's choice of aliases."""
    terms = {}
    pattern = r'^\s*class\s+([^\s\[{]+)(?:\[\s*"([^"\n]+)"\s*\])?'
    for match in re.finditer(pattern, source, re.M):
        ident = match.group(1).split(':::')[0]
        if match.group(2):
            terms[ident] = match.group(2)
        else:
            terms.setdefault(ident, ident)
    return sorted(set(terms.values()))


def canonical_sources(sources, project=None):
    """Group quotations from one file, retaining the quoted text and line references."""
    groups = {}
    for index, source in enumerate(sources):
        is_url = re.match(r'[a-z][a-z0-9+.-]*://', source['path'], re.I)
        match = None if is_url else re.fullmatch(r'(.*?):L?(\d+)(?:-L?(\d+))?(?::\d+)?', source['path'])
        path = match.group(1) if match else source['path']
        if project is not None and not is_url and Path(path).is_absolute():
            try:
                path = Path(path).resolve().relative_to(Path(project).resolve()).as_posix()
            except ValueError:
                pass  # A supplied reference outside the project retains its absolute path.
        start = int(match.group(2)) if match else None
        end = int(match.group(3) or match.group(2)) if match else None
        groups.setdefault(path, []).append((start, end, index, source['quote']))
    result = []
    for path, entries in sorted(groups.items()):
        entries.sort(key=lambda item: (item[0] if item[0] is not None else -1, item[2]))
        quotes = list(dict.fromkeys(item[3] for item in entries))
        if all(item[0] is not None for item in entries):
            first, last = min(item[0] for item in entries), max(item[1] for item in entries)
            path += ':' + str(first) + ('-' + str(last) if first != last else '')
        result.append({'path': path, 'quote': '\n\n'.join(quotes)})
    return result


def png_size(data):
    require(data.startswith(b"\x89PNG\r\n\x1a\n"), "OUT-02", "PNGの署名が壊れている")
    offset, kinds, payloads, size = 8, [], [], None
    while offset < len(data):
        require(offset + 12 <= len(data), "OUT-02", "PNGのチャンクが欠けている")
        length = struct.unpack(">I", data[offset:offset + 4])[0]
        kind = data[offset + 4:offset + 8]
        end = offset + 12 + length
        require(end <= len(data), "OUT-02", "PNGのチャンク長が壊れている")
        chunk = data[offset + 8:offset + 8 + length]
        crc = struct.unpack(">I", data[end - 4:end])[0]
        require(zlib.crc32(kind + chunk) & 0xffffffff == crc, "OUT-02", "PNGのCRCが一致しない")
        kinds.append(kind)
        if kind == b"IHDR":
            require(len(kinds) == 1 and len(chunk) == 13, "OUT-02", "PNGのIHDRが壊れている")
            width, height, depth, color, compression, filtering, interlace = struct.unpack(">IIBBBBB", chunk)
            require(32 <= width <= 16000 and 32 <= height <= 16000 and width * height <= 50000000,
                    "OUT-02", "PNGの寸法が範囲外である")
            require(depth == 8 and color in (2, 6) and (compression, filtering, interlace) == (0, 0, 0),
                    "OUT-02", "ブラウザの8bit RGB/RGBA PNGを使う")
            size = (width, height, 3 if color == 2 else 4)
        if kind == b"IDAT":
            payloads.append(chunk)
        offset = end
        if kind == b"IEND":
            require(not chunk and offset == len(data), "OUT-02", "PNGの終端が壊れている")
            break
    require(size and kinds[-1:] == [b"IEND"] and payloads, "OUT-02", "PNGの画像データまたは終端がない")
    width, height, channels = size
    expected = height * (1 + width * channels)
    try:
        decoder = zlib.decompressobj()
        pixels = decoder.decompress(b"".join(payloads), expected + 1)
        require(decoder.eof and not decoder.unused_data and len(pixels) == expected,
                "OUT-02", "PNGの画素データが壊れている")
    except zlib.error as exc:
        raise Finding("OUT-02", "PNGの画素を展開できない") from exc
    require(all(pixels[i] <= 4 for i in range(0, expected, 1 + width * channels)),
            "OUT-02", "PNGの走査行フィルタが壊れている")
    return {"width": width, "height": height}


def render_html(data):
    def esc(value, quote=True):
        return html.escape(value, quote=quote).replace('\r', '&#13;').replace('\n', '&#10;')
    cards = []
    for item in data["diagrams"]:
        ident = item["id"]
        search = " ".join([item["title"], item["description"]] + item["terms"])
        tags = "".join('<span class="tag">' + esc(t) + '</span>' for t in item["terms"])
        sources = "".join('<li><code>' + esc(s["path"]) + '</code><blockquote>' + esc(s["quote"]) + '</blockquote></li>'
                          for s in item["sources"])
        unresolved = "".join('<li>' + esc(t) + '</li>' for t in item["unresolved"])
        unknown = '<div class="unknown"><strong>確認したいこと</strong><ul>' + unresolved + '</ul></div>' if unresolved else '<p class="confirmed">未確認事項なし</p>'
        cards.append('''<article class="card" id="{id}" data-search="{search}">
<div class="preview"><button class="open-diagram" data-id="{id}" data-title="{title}" aria-label="{title}の図を拡大"><img src="images/{id}.png" alt="{title}のドメインモデル図"></button></div>
<div class="card-body"><div class="diagram-id">{id}</div><h2>{title}</h2><p>{description}</p><div class="tags">{tags}</div>{unknown}
<details><summary>根拠となる資料（{count}件）</summary><ul class="sources">{sources}</ul></details>
<div class="actions"><button class="open-diagram primary" data-id="{id}" data-title="{title}">図を拡大</button><a href="diagrams/{id}.mmd" download>Mermaid原本</a><a href="images/{id}.png" download>PNG</a></div></div></article>'''.format(
            id=ident, search=esc(search, quote=True), title=esc(item["title"], quote=True),
            description=esc(item["description"]), tags=tags, unknown=unknown, count=len(item["sources"]), sources=sources))
    template = (SKILL / "assets/catalog.html").read_text(encoding="utf-8")
    # Replace each placeholder once so user text cannot become another template instruction.
    values = {"TITLE": esc(data["title"]), "COUNT": str(len(cards)), "CARDS": "\n".join(cards)}
    return re.sub(r"@@(TITLE|COUNT|CARDS)@@", lambda m: values[m.group(1)], template)


def receipt(data, files, version):
    return {"schema_version": 1, "status": "passed", "diagram_ids": [d["id"] for d in data["diagrams"]],
            "renderer": {"name": "mermaid-cli", "version": version, "scale": 2, "background": "white", "font_family": FONT, "config": CONFIG},
            "files": {path: digest(content) for path, content in sorted(files.items())},
            "images": {d["id"]: png_size(files["images/" + d["id"] + ".png"]) for d in data["diagrams"]}}


def check(root):
    data = load_catalog(root, canonical=True)
    check_files(root, data, complete=True)
    for item in data["diagrams"]:
        source = read_mermaid(root, item["id"])
        require(item['terms'] == concept_terms(source), 'OUT-04', 'termsを原本の概念の表示名から生成する')
        require(item['sources'] == canonical_sources(item['sources'], root.parent.parent), 'OUT-04', '同じ資料の引用をまとめ、参照先の昇順にする')
    record = read_json(root / "validation.json")
    keys(record, ["schema_version", "status", "diagram_ids", "renderer", "files", "images"], "validation.json")
    require(record["schema_version"] == 1 and record["status"] == "passed", "STEP-04", "変換検証に合格していない")
    renderer = record["renderer"]
    keys(renderer, ["name", "version", "scale", "background", "font_family", "config"], "renderer")
    require(renderer["name"] == "mermaid-cli" and text_value(renderer["version"]), "STEP-04", "変換に使ったMermaid CLIの版がない")
    require(renderer["scale"] == 2 and renderer["background"] == "white" and renderer["font_family"] == FONT,
            "STEP-04", "固定した変換設定と一致しない")
    files = {p: (root / p).read_bytes() for p in bundle_paths(data) - {"validation.json"}}
    for item in data["diagrams"]:
        png_size(files["images/" + item["id"] + ".png"])
    require(files["index.html"].decode("utf-8") == render_html(data), "OUT-02", "HTMLがカタログ情報と一致しない")
    expected = receipt(data, files, renderer["version"])
    require(record == expected, "OUT-07", "原本・PNG・HTML・カタログの対応またはSHA-256が一致しない。buildを再実行する")
    return data


def renderer_command(explicit):
    command = explicit or os.environ.get("DOMAIN_MODEL_MMDC") or "mmdc"
    resolved = shutil.which(command)
    if not resolved:
        raise Finding("STEP-02", "mmdc がない。references/setup.md の導入方法を確認する")
    try:
        proc = subprocess.run([resolved, "--version"], capture_output=True, text=True, timeout=15)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise Finding("STEP-02", "mmdc の版を確認できない: " + str(exc)) from exc
    require(proc.returncode == 0 and bool(proc.stdout.strip()), "STEP-02", "mmdc --version が失敗した")
    return resolved, proc.stdout.strip()


def build(root, explicit=None, update=False):
    data = load_catalog(root)
    check_files(root, data, complete=False)
    exists = (root / "index.html").exists() or (root / "validation.json").exists()
    require(not exists or update, "OUT-06", "既存カタログの更新は --update を指定する")
    previous = None
    if exists:
        require((root / "validation.json").is_file(), "OUT-06", "検証記録のない既存HTMLを上書きしない")
        previous = read_json(root / "validation.json")
        old_ids = previous.get("diagram_ids")
        require(isinstance(old_ids, list) and all(text_value(i) for i in old_ids), "OUT-06", "既存IDの記録を読めない")
        require(set(old_ids) <= {d["id"] for d in data["diagrams"]}, "OUT-06", "依頼のない既存図の削除・ID変更を行わない")
    data["diagrams"].sort(key=lambda item: item["id"])
    sources = {}
    for item in data["diagrams"]:
        sources["diagrams/" + item["id"] + ".mmd"] = read_mermaid(root, item["id"]).rstrip() + "\n"
        item['terms'] = concept_terms(sources['diagrams/' + item['id'] + '.mmd'])
        item['sources'] = canonical_sources(item['sources'], root.parent.parent)
    command, version = renderer_command(explicit)
    # Stage every conversion before replacing any published image or HTML.
    with tempfile.TemporaryDirectory(prefix=".render-", dir=root) as work:
        stage = Path(work)
        config = stage / "mermaid.json"
        config.write_text(dump(CONFIG), encoding="utf-8")
        files = {p: source.encode("utf-8") for p, source in sources.items()}
        for item in data["diagrams"]:
            ident = item["id"]
            # Reuse only a verified PNG with unchanged source and renderer settings.
            # This also avoids changing unrelated diagrams when adding a new one.
            source_key, image_key = "diagrams/" + ident + ".mmd", "images/" + ident + ".png"
            prior_files = previous.get("files", {}) if previous else {}
            prior_renderer = previous.get("renderer", {}) if previous else {}
            existing_image = root / image_key
            if (prior_renderer == {"name": "mermaid-cli", "version": version, "scale": 2, "background": "white", "font_family": FONT, "config": CONFIG}
                    and prior_files.get(source_key) == digest(files[source_key])
                    and existing_image.is_file()):
                image = existing_image.read_bytes()
                if prior_files.get(image_key) == digest(image):
                    png_size(image)
                    files[image_key] = image
                    continue
            source_path = stage / (ident + ".mmd")
            source_path.write_bytes(files["diagrams/" + ident + ".mmd"])
            target = stage / (ident + ".png")
            try:
                result = subprocess.run([command, "-i", str(source_path), "-o", str(target),
                                         "-c", str(config), "-b", "white", "-s", "2", "-q"],
                                        capture_output=True, text=True, timeout=120)
            except (OSError, subprocess.TimeoutExpired) as exc:
                raise Finding("STEP-03", ident + " の変換を実行できない: " + str(exc)) from exc
            require(result.returncode == 0 and target.is_file(), "STEP-03",
                    ident + " の変換に失敗した: " + (result.stderr or result.stdout)[-1800:])
            image = target.read_bytes()
            png_size(image)
            files["images/" + ident + ".png"] = image
        files["catalog.json"] = dump(data).encode("utf-8")
        files["index.html"] = render_html(data).encode("utf-8")
        files["validation.json"] = dump(receipt(data, files, version)).encode("utf-8")
        before = {p: (root / p).read_bytes() if (root / p).exists() else None for p in files}
        changed = []
        try:
            for i, (path, content) in enumerate(files.items()):
                target = root / path
                target.parent.mkdir(parents=True, exist_ok=True)
                prepared = stage / (str(i) + ".out")
                prepared.write_bytes(content)
                os.replace(prepared, target)
                changed.append(path)
        except OSError:
            for path in reversed(changed):
                if before[path] is None:
                    (root / path).unlink(missing_ok=True)
                else:
                    (root / path).write_bytes(before[path])
            raise
    return check(root)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("action", choices=["inspect", "deps", "build", "check", "report"])
    parser.add_argument("directory", nargs="?")
    parser.add_argument("--mmdc", help="既に導入されたMermaid CLIの実行ファイル")
    parser.add_argument("--update", action="store_true", help="依頼された既存カタログの更新")
    args = parser.parse_args()
    try:
        if args.action == "deps":
            command, version = renderer_command(args.mmdc)
            print("Mermaid CLI: " + version + "\n実行ファイル: " + command)
            return 0
        if not args.directory:
            parser.error("directory が必要である")
        root = checked_root(args.directory)
        if args.action == "inspect":
            if not root.exists():
                print("カタログ: 新規\n出力先: " + str(root))
            else:
                data = load_catalog(root)
                print("既存の図: " + ", ".join(d["id"] for d in data["diagrams"]))
                print("画像生成済み: " + str((root / "index.html").is_file()))
            return 0
        data = build(root, args.mmdc, args.update) if args.action == "build" else check(root)
        print("図: " + str(len(data["diagrams"])) + "件")
        if args.action == "report":
            notes = root.parent.parent / ".skill-runs/generate-domain-model/notes.md"
            if notes.is_file():
                lines = notes.read_text(encoding="utf-8").splitlines()
                labels = ["資料照合", "PNG表示", "HTML操作"]
                require(len(lines) == 3 and all(re.fullmatch(
                    r"- " + label + r": (?:確認済み|未実施（[^\n]+）)", line)
                    for label, line in zip(labels, lines)) and not any(re.search(r"[A-Za-z]", line.split(": ", 1)[-1]) for line in lines), "STEP-04",
                    "notes.mdは資料照合・PNG表示・HTML操作の順で3行にし、値は確認済みか未実施（英字を含まない日本語の理由）にする")
            print("カタログ: [開く](" + str(root / "index.html") + ")")
            print("検証: 原本・画像・HTML・全ファイルの対応に合格")
        else:
            print(args.action + ": 指摘 0 件")
        return 0
    except Finding as exc:
        print(exc.rule + " " + str(exc), file=sys.stderr)
        return 2 if exc.rule == "STEP-02" else 1
    except (OSError, UnicodeError, ValueError, TypeError, KeyError) as exc:
        print("OUT-02 カタログを処理できない: " + str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
