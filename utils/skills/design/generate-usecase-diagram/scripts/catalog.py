"""要件から整理したMermaidをPNGとHTMLカタログにする。

STEP-03・STEP-04・STEP-05・STEP-06、OUT-01・OUT-02・OUT-04〜OUT-08を実装する。
出力: catalog.json、index.html、validation.json、diagrams/*.mmdと*.png。
使用法: python3 catalog.py preflight / build --request request.json / check --catalog catalog.json / selftest
終了コード: 0 成功、1 検査・描画失敗、2 引数の誤り。
Python標準ライブラリだけを使い、外部通信とパッケージの導入は行わない。
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
import tempfile
import zlib

from render_diagram import preview, render, resources


SKILL = Path(__file__).resolve().parent.parent
SLUG = re.compile(r'[a-z][a-z0-9]*(?:-[a-z0-9]+)*\Z')


class Problem(ValueError):
    def __init__(self, rule, message):
        self.rule = rule
        super().__init__(rule + ' ' + message)


def require(condition, rule, message):
    if not condition:
        raise Problem(rule, message)


def encoded(value):
    return (json.dumps(value, ensure_ascii=False, indent=2) + '\n').encode('utf-8')


def digest(value):
    return hashlib.sha256(value).hexdigest()


def load(path):
    try:
        return json.loads(Path(path).read_text(encoding='utf-8'))
    except (OSError, ValueError) as error:
        raise Problem('OUT-02', 'JSONを読めません: ' + str(error)) from error


def text(value, label):
    require(isinstance(value, str) and bool(value.strip()), 'OUT-02', label + 'は空でない文字列です。')
    return value


def slug(value):
    require(isinstance(value, str) and len(value) <= 64 and bool(SLUG.fullmatch(value)), 'OUT-04', '名前と図IDは64文字以下の小文字kebab-caseです。')
    return value


def source_check(source):
    require(isinstance(source, str) and len(source.encode('utf-8')) <= 100000, 'OUT-05', '原本は100KB以下です。')
    require(not re.search(r'%%\s*\{|^\s*---', source, re.M), 'OUT-08', 'initディレクティブとfrontmatterによる設定の上書きを受け付けません。原本の設定を除いて再実行してください。')
    require(bool(re.match(r'\s*(?:%%[^\n]*\n\s*)*usecase-beta\b', source)), 'OUT-02', '原本はusecase-betaで始めてください。')


def model_check(model):
    require(isinstance(model, dict), 'OUT-02', 'Mermaidの構造解析結果がありません。')
    actors, cases, systems = (model.get(k, []) for k in ('actors', 'usecases', 'systems'))
    require(all(isinstance(v, list) and v for v in (actors, cases, systems)), 'OUT-02', 'アクター・ユースケース・境界が必要です。')
    require(2 <= len(actors) + len(cases) <= 40, 'OUT-05', '1図の要素数は2〜40です。')
    nodes = actors + cases + systems
    ids = [n.get('id') for n in nodes]
    require(all(isinstance(i, str) for i in ids) and len(ids) == len(set(ids)), 'OUT-04', 'MermaidのIDが重複しています。')
    require(all(model.get('declarations', {}).get(i) == 1 for i in ids), 'OUT-04', '各IDを1回だけ明示宣言してください。')
    bounds = {b['id'] for b in systems}
    require(all(not a.get('parent') for a in actors) and all(u.get('parent') in bounds for u in cases), 'OUT-02', 'アクターは境界の外、ユースケースは境界の中に配置してください。')
    require(all(isinstance(n.get('label'), str) and n['label'] for n in nodes), 'OUT-02', '表示ラベルがありません。')
    by_id = {n['id']: kind for kind, group in (('actor', actors), ('usecase', cases)) for n in group}
    for edge in model.get('relationships', []):
        a, b, kind = edge.get('source'), edge.get('target'), edge.get('type')
        require(a in by_id and b in by_id, 'OUT-02', '関係の端点を明示宣言してください。')
        require(kind in ('association', 'include', 'extend', 'generalization'), 'OUT-02', '関係の種類が不正です。')
        if kind in ('include', 'extend'):
            require(by_id[a] == by_id[b] == 'usecase', 'OUT-02', 'includeとextendの端点はユースケースです。')
        if kind == 'generalization':
            require(by_id[a] == by_id[b], 'OUT-02', '汎化は同種の要素間に置いてください。')


def png_info(data):
    """Validate all chunk CRCs and the complete 8-bit RGB/RGBA scanline stream."""
    require(data.startswith(b'\x89PNG\r\n\x1a\n'), 'OUT-07', 'PNGのシグネチャが不正です。')
    cursor, chunks, image, header = 8, [], bytearray(), None
    while cursor < len(data):
        require(cursor + 12 <= len(data), 'OUT-07', 'PNGのチャンクが切れています。')
        size = struct.unpack('>I', data[cursor:cursor + 4])[0]
        kind = data[cursor + 4:cursor + 8]
        end = cursor + 12 + size
        require(end <= len(data), 'OUT-07', 'PNGのチャンク長が不正です。')
        value = data[cursor + 8:cursor + 8 + size]
        checksum = struct.unpack('>I', data[cursor + 8 + size:end])[0]
        require(zlib.crc32(kind + value) & 0xffffffff == checksum, 'OUT-07', 'PNGのCRCが不一致です。')
        if kind == b'IHDR':
            require(not chunks and size == 13, 'OUT-07', 'PNGのIHDRが不正です。')
            header = struct.unpack('>IIBBBBB', value)
        elif kind == b'IDAT':
            image.extend(value)
        elif kind == b'IEND':
            require(size == 0 and end == len(data), 'OUT-07', 'PNGの終端が不正です。')
        chunks.append(kind)
        cursor = end
    require(header is not None and chunks[-1:] == [b'IEND'] and image, 'OUT-07', 'PNGの必須チャンクがありません。')
    width, height, bits, color, compression, filtering, interlace = header
    require(0 < width <= 12000 and 0 < height <= 12000 and width * height <= 30000000, 'OUT-05', 'PNGの寸法または面積が上限を超えています。')
    require(bits == 8 and color in (2, 6) and (compression, filtering, interlace) == (0, 0, 0), 'OUT-07', 'PNGは8bit RGB/RGBA・非interlaceです。')
    stride = width * (3 if color == 2 else 4) + 1
    expected = height * stride
    try:
        decoder = zlib.decompressobj()
        raw = decoder.decompress(bytes(image), expected + 1)
    except zlib.error as error:
        raise Problem('OUT-07', 'PNGの画素データを展開できません。') from error
    require(len(raw) == expected and decoder.eof and not decoder.unused_data and not decoder.unconsumed_tail,
            'OUT-07', 'PNGの画素データの長さが不正です。')
    require(all(raw[n] <= 4 for n in range(0, len(raw), stride)), 'OUT-07', 'PNGの走査行フィルターが不正です。')
    return {'width': width, 'height': height}


def make_html(catalog, base, visual='pending'):
    e = lambda value: html.escape(str(value), quote=True)
    cards = []
    for diagram in catalog['diagrams']:
        source = (base / diagram['source']).read_text(encoding='utf-8')
        tags = ''.join('<span class="tag">' + e(a['label']) + '</span>' for a in diagram['actors'])
        cards.append('<article id="' + e(diagram['id']) + '"><div class="card-body"><span class="diagram-id">' +
            e(diagram['id']) + '</span><h2>' + e(diagram['title']) + '</h2><p>' + e(diagram['summary']) +
            '</p><div class="tags">' + tags + '</div></div><a class="preview" href="' + e(diagram['image']) +
            '" data-title="' + e(diagram['title']) + '"><img src="' + e(diagram['image']) + '" alt="' +
            e(diagram['title'] + '：' + diagram['summary']) + '" loading="lazy"></a><div class="card-body"><div class="actions">' +
            '<a class="button primary" href="' + e(diagram['image']) + '" download>PNGを取得</a>' +
            '<a class="button" href="' + e(diagram['source']) + '" download>Mermaid原本を取得</a></div>' +
            '<details><summary>Mermaid原本を表示</summary><pre><code>' + e(source) + '</code></pre></details></div></article>')
    template = (SKILL / 'assets/catalog.html').read_text(encoding='utf-8')
    substitutions = {'__TITLE__': e(catalog['title']), '__DESCRIPTION__': e(catalog['description']),
                     '__COUNT__': str(len(cards)), '__CARDS__': '\n'.join(cards),
                     '__VISUAL__': '確認済み（内容は検証記録を参照）' if visual == 'reviewed' else '確認待ち'}
    # One pass prevents user text containing placeholder strings from being substituted.
    return re.sub('|'.join(map(re.escape, substitutions)), lambda m: substitutions[m.group()], template)


def safe_files(base, allowed):
    require(not base.is_symlink(), 'OUT-01', 'シンボリックリンクの出力先は変更しません。')
    if not base.exists():
        return
    require(base.is_dir(), 'OUT-01', '出力先はディレクトリです。')
    for p in base.rglob('*'):
        require(not p.is_symlink(), 'OUT-01', '出力先にシンボリックリンクがあります。')
        rel = p.relative_to(base).as_posix()
        require((p.is_dir() and rel == 'diagrams') or (p.is_file() and rel in allowed), 'OUT-01', '未管理ファイルがあるため変更しません: ' + rel)


def check(catalog_path, deep=False, environment=None, workspace=None):
    base = Path(catalog_path).parent
    require(not base.is_symlink() and not any(p.is_symlink() for p in base.rglob('*')), 'OUT-01', '出力先のシンボリックリンクを拒否します。')
    catalog = load(catalog_path)
    require(isinstance(catalog, dict) and set(catalog) == {'schema_version', 'title', 'description', 'diagrams'}, 'OUT-02', 'catalog.jsonのキーが契約と一致しません。')
    require(catalog['schema_version'] == 1, 'OUT-02', 'schema_versionは1です。')
    text(catalog['title'], 'title'); text(catalog['description'], 'description')
    diagrams = catalog['diagrams']
    require(isinstance(diagrams, list) and 1 <= len(diagrams) <= 24, 'OUT-05', '図の数は1〜24です。')
    require(all(isinstance(d, dict) for d in diagrams), 'OUT-02', '図はオブジェクトです。')
    ids = [slug(d.get('id')) for d in diagrams]
    require(ids == sorted(set(ids)), 'OUT-04', '図IDは重複せず昇順です。')
    receipt = load(base / 'validation.json')
    require(isinstance(receipt, dict), 'OUT-02', 'validation.jsonはオブジェクトです。')
    require(not any(k in receipt for k in ('skip', 'ignore')), 'OUT-08', '検査を省略するキーを受け付けません。')
    require(receipt.get('status') == 'passed' and len(receipt.get('diagrams', [])) == len(diagrams), 'STEP-06', '全図の検査成功が必要です。')
    require(receipt.get('visual_review', {}).get('status') in ('pending', 'reviewed'), 'STEP-06', '目視の状態はpendingかreviewedです。')
    require(receipt.get('schema_version') == 1, 'OUT-02', '変換記録の版が不正です。')
    allowed = {'catalog.json', 'index.html', 'validation.json'}
    for d, entry in zip(diagrams, receipt['diagrams']):
        require(set(d) == {'id', 'title', 'summary', 'source', 'image', 'actors', 'systems'}, 'OUT-02', '図のキーが契約と一致しません。')
        text(d['title'], '図題名'); text(d['summary'], '図説明')
        for ext, key in (('mmd', 'source'), ('png', 'image')):
            expected = 'diagrams/' + d['id'] + '.' + ext
            require(d[key] == expected and (base / expected).is_file() and not (base / expected).is_symlink(), 'OUT-01', '原本と画像の相対パスまたは実体が不正です: ' + expected)
            allowed.add(expected)
        model_check(entry.get('model'))
        require(d['actors'] == [{'id': x['id'], 'label': x['label']} for x in entry['model']['actors']] and
                d['systems'] == [{'id': x['id'], 'label': x['label']} for x in entry['model']['systems']], 'STEP-03', 'カタログのアクター・境界と解析結果が一致しません。')
        source_bytes, png = (base / d['source']).read_bytes(), (base / d['image']).read_bytes()
        source = source_bytes.decode('utf-8')
        source_check(source)
        dimensions = png_info(png)
        require(entry.get('id') == d['id'] and dimensions == {k: entry.get(k) for k in ('width', 'height')}, 'OUT-07', 'PNGの実寸または図IDと変換記録が一致しません。')
        require(entry.get('source_sha256') == digest(source_bytes) and entry.get('png_sha256') == digest(png), 'OUT-07', '原本またはPNGが変換後に変更されています。再生成してください。')
        renderer = entry.get('renderer', {})
        require(renderer.get('network') == 'blocked' and renderer.get('layout') == 'elk' and renderer.get('mermaid', '').startswith('12.') and renderer.get('browser', '').startswith('Chrome/'), 'OUT-08', '検証済みの描画設定・環境記録が必要です。')
        if deep:
            with tempfile.TemporaryDirectory(prefix='deep-', dir=workspace) as temporary:
                observed = render(source, Path(temporary) / 'check.png', environment, temporary)
                require(observed['model'] == entry['model'], 'STEP-03', '原本の再解析結果が変換記録と一致しません。')
    safe_files(base, allowed)
    page = (base / 'index.html').read_bytes()
    require(page == make_html(catalog, base, receipt['visual_review']['status']).encode('utf-8'), 'OUT-02', 'HTMLがカタログと原本からの生成結果に一致しません。')
    require(receipt.get('catalog_sha256') == digest(Path(catalog_path).read_bytes()) and receipt.get('html_sha256') == digest(page), 'OUT-07', 'カタログまたはHTMLのSHA-256が一致しません。')
    return receipt


def request_data(request_path):
    data = load(request_path)
    require(isinstance(data, dict) and set(data) == {'title', 'description', 'diagrams'}, 'OUT-02', '入力はtitle・description・diagramsを持つJSONです。')
    text(data['title'], 'title'); text(data['description'], 'description')
    require(isinstance(data['diagrams'], list) and 1 <= len(data['diagrams']) <= 24, 'OUT-05', '図の数は1〜24です。')
    rows = []
    for d in data['diagrams']:
        require(isinstance(d, dict) and set(d) in ({'id', 'title', 'summary', 'mermaid'}, {'id', 'title', 'summary', 'source'}), 'OUT-02', '各図はid・title・summaryと、mermaidまたはsourceを持ちます。')
        row = {'id': slug(d['id']), 'title': text(d['title'], '図題名'), 'summary': text(d['summary'], '図説明')}
        if 'source' in d:
            path = Path(text(d['source'], '原本パス'))
            if not path.is_absolute():
                path = Path(request_path).parent / path
            require(path.is_file(), 'OUT-01', '指定原本がありません: ' + str(path))
            row['mermaid'] = path.read_bytes().decode('utf-8')
        else:
            row['mermaid'] = d['mermaid']
        source_check(row['mermaid'])
        rows.append(row)
    require(len(rows) == len({d['id'] for d in rows}), 'OUT-04', '図IDが重複しています。')
    return {**data, 'diagrams': sorted(rows, key=lambda d: d['id'])}


def build(request_path, root, name, replace=False, mermaid=None, browser=None):
    name = slug(name)
    root = Path(root).resolve()
    destination = root / 'artifacts/usecase' / name
    for path in (root / 'artifacts', root / 'artifacts/usecase', destination):
        require(not path.is_symlink(), 'OUT-01', 'シンボリックリンクの出力先は変更しません。')
    data = request_data(request_path)
    previous_files = None
    if destination.exists():
        previous = load(destination / 'catalog.json')
        require(isinstance(previous, dict), 'OUT-02', '既存カタログを読めません。')
        require(isinstance(previous.get('diagrams'), list), 'OUT-02', '既存カタログの図一覧が不正です。')
        allowed = {'catalog.json', 'index.html', 'validation.json'}
        for d in previous.get('diagrams', []):
            require(isinstance(d, dict), 'OUT-02', '既存カタログの図が不正です。')
            slug(d.get('id'))
            require(d.get('source') == 'diagrams/' + d['id'] + '.mmd' and d.get('image') == 'diagrams/' + d['id'] + '.png',
                    'OUT-01', '既存カタログの参照先が管理範囲の外です。')
            allowed.update({'diagrams/' + d['id'] + '.mmd', 'diagrams/' + d['id'] + '.png'})
        safe_files(destination, allowed)
        previous_files = {p.relative_to(destination).as_posix(): digest(p.read_bytes()) for p in destination.rglob('*') if p.is_file()}
        # An identical request reuses a completely checked output, without changing bytes.
        if data['title'] == previous.get('title') and data['description'] == previous.get('description') and len(data['diagrams']) == len(previous.get('diagrams', [])):
            identical = all(all(a[k] == b.get(k) for k in ('id', 'title', 'summary')) and
                            a['mermaid'].encode('utf-8') == (destination / b['source']).read_bytes()
                            for a, b in zip(data['diagrams'], previous['diagrams']))
            if identical:
                check(destination / 'catalog.json')
                return {'status': 'reused', 'catalog': str(destination / 'index.html'), 'diagrams': len(data['diagrams'])}
        require(replace, 'OUT-06', '既存出力があります。更新の依頼を確認して--replaceを指定してください。')
    environment = resources(root, mermaid, browser)
    work = root / '.skill-runs/generate-usecase-diagram/work'
    work.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='build-', dir=work) as temporary:
        stage = Path(temporary) / 'catalog'
        (stage / 'diagrams').mkdir(parents=True)
        catalog = {'schema_version': 1, 'title': data['title'], 'description': data['description'], 'diagrams': []}
        receipt = {'schema_version': 1, 'status': 'passed', 'visual_review': {'status': 'pending', 'notes': ''}, 'diagrams': []}
        for d in data['diagrams']:
            source_path, image_path = 'diagrams/' + d['id'] + '.mmd', 'diagrams/' + d['id'] + '.png'
            (stage / source_path).write_bytes(d['mermaid'].encode('utf-8'))
            try:
                observed = render(d['mermaid'], stage / image_path, environment, temporary)
            except (OSError, ValueError) as error:
                message = str(error)
                match = re.search(r'\b(?:OUT|STEP)-\d{2}\b', message)
                raise Problem(match.group() if match else 'OUT-02', '描画失敗 ' + d['id'] + ': ' + message) from error
            model_check(observed['model'])
            png_info((stage / image_path).read_bytes())
            catalog['diagrams'].append({'id': d['id'], 'title': d['title'], 'summary': d['summary'], 'source': source_path, 'image': image_path,
                'actors': [{'id': x['id'], 'label': x['label']} for x in observed['model']['actors']],
                'systems': [{'id': x['id'], 'label': x['label']} for x in observed['model']['systems']]})
            receipt['diagrams'].append({'id': d['id'], **observed, 'source_sha256': digest((stage / source_path).read_bytes()),
                                       'png_sha256': digest((stage / image_path).read_bytes())})
        (stage / 'catalog.json').write_bytes(encoded(catalog))
        (stage / 'index.html').write_text(make_html(catalog, stage), encoding='utf-8')
        receipt['catalog_sha256'] = digest((stage / 'catalog.json').read_bytes())
        receipt['html_sha256'] = digest((stage / 'index.html').read_bytes())
        (stage / 'validation.json').write_bytes(encoded(receipt))
        check(stage / 'catalog.json')
        # Detect another writer before replacing the previously inspected directory.
        require(not destination.is_symlink(), 'OUT-06', '描画中に出力先が変更されました。再確認してください。')
        if previous_files is None:
            require(not destination.exists(), 'OUT-06', '描画中に同名の出力が作られました。再確認してください。')
        else:
            safe_files(destination, set(previous_files))
            current = {p.relative_to(destination).as_posix(): digest(p.read_bytes()) for p in destination.rglob('*') if p.is_file()}
            require(current == previous_files, 'OUT-06', '描画中に既存出力が変更されました。変更を確認して再実行してください。')
        destination.parent.mkdir(parents=True, exist_ok=True)
        backup = Path(temporary) / 'previous'
        if destination.exists():
            os.replace(destination, backup)
        try:
            os.replace(stage, destination)
        except BaseException:
            if backup.exists():
                os.replace(backup, destination)
            raise
    return {'status': 'generated', 'catalog': str(destination / 'index.html'), 'diagrams': len(data['diagrams'])}


def check_preview(catalog_path, root):
    work = Path(root) / '.skill-runs/generate-usecase-diagram'
    try:
        proof = load(work / 'preview.json')
        png = (work / 'preview.png').read_bytes()
    except (OSError, Problem) as error:
        raise Problem('STEP-06', '先にcatalog.py previewで画面と操作の記録を保存してください。') from error
    require(proof.get('catalog_sha256') == digest(Path(catalog_path).read_bytes()), 'STEP-06', '画面記録が現在のカタログと一致しません。')
    require(proof.get('screenshot_sha256') == digest(png), 'STEP-06', '保存した画面が記録と一致しません。')
    png_info(png)
    checks = proof.get('checks', {})
    require(all(checks.get(k) is True for k in ('imagesValid', 'searchEmpty', 'dialogOpen', 'dialogClosed', 'sourceShown', 'localLinks', 'noOverflow')), 'STEP-06', '画面の操作検査が完了していません。')
    require(checks.get('cards') == len(load(catalog_path)['diagrams']), 'STEP-06', '画面の図数が一致しません。')
    return proof


def record_preview(catalog_path, out, root, environment):
    check(catalog_path)
    work = Path(root) / '.skill-runs/generate-usecase-diagram'
    require(Path(out).resolve() == (work / 'preview.png').resolve(), 'STEP-06', '画面は実行記録のpreview.pngへ保存してください。')
    work.mkdir(parents=True, exist_ok=True)
    result = preview(Path(catalog_path).parent / 'index.html', out, environment, work)
    proof = {'catalog_sha256': digest(Path(catalog_path).read_bytes()), 'screenshot_sha256': digest(Path(out).read_bytes()), 'checks': result}
    (work / 'preview.json').write_bytes(encoded(proof))
    check_preview(catalog_path, root)
    return result


def record_review(catalog_path, notes, root):
    check(catalog_path)
    check_preview(catalog_path, root)
    notes_path = Path(root) / '.skill-runs/generate-usecase-diagram/notes.md'
    if not notes_path.exists():
        notes_path.write_text('- なし\n', encoding='utf-8')
    base = Path(catalog_path).parent
    receipt = load(base / 'validation.json')
    receipt['visual_review'] = {'status': 'reviewed', 'notes': text(notes, '目視した内容')}
    (base / 'index.html').write_text(make_html(load(catalog_path), base, 'reviewed'), encoding='utf-8')
    receipt['html_sha256'] = digest((base / 'index.html').read_bytes())
    (base / 'validation.json').write_bytes(encoded(receipt))
    check(catalog_path)


def selftest(sample, root, mermaid=None, browser=None):
    """Exercise real rendering, input errors, synchronization and failure rollback."""
    results = []
    with tempfile.TemporaryDirectory(prefix='usecase-selftest-', dir=root) as temp:
        base = Path(temp)
        data = load(sample)
        request = base / 'request.json'
        request.write_bytes(encoded(data))
        build(request, base, 'test', mermaid=mermaid, browser=browser)
        catalog = base / 'artifacts/usecase/test/catalog.json'
        check(catalog)
        results.append('通常入力を実描画し、全PNG・HTML・SHA-256を検査')
        before = {p.relative_to(catalog.parent).as_posix(): digest(p.read_bytes()) for p in catalog.parent.rglob('*') if p.is_file()}
        require(build(request, base, 'test', mermaid=mermaid, browser=browser)['status'] == 'reused', 'STEP-06', '同じ入力を再利用できません。')
        results.append('同じ入力の再実行で既存出力を再利用')
        invalid = json.loads(json.dumps(data))
        invalid['diagrams'][-1]['mermaid'] = 'usecase-beta\nactor\n'
        request.write_bytes(encoded(invalid))
        try:
            build(request, base, 'test', True, mermaid, browser)
        except Problem:
            pass
        else:
            raise Problem('STEP-06', '不正なMermaidを成功扱いしました。')
        after = {p.relative_to(catalog.parent).as_posix(): digest(p.read_bytes()) for p in catalog.parent.rglob('*') if p.is_file()}
        require(before == after, 'STEP-06', '描画失敗で既存の正常な出力が変わりました。')
        results.append('後続図の構文エラーで以前の全出力が不変')
        invalid = json.loads(json.dumps(data))
        invalid['diagrams'].append(dict(invalid['diagrams'][0]))
        try:
            request_data_from = base / 'duplicate.json'
            request_data_from.write_bytes(encoded(invalid))
            request_data(request_data_from)
        except Problem as error:
            require(error.rule == 'OUT-04', 'STEP-06', '重複IDの判定に失敗しました。')
        else:
            raise Problem('STEP-06', '図IDの重複を受け入れました。')
        results.append('図IDの重複を拒否')
        for label, source, expected in (
            ('重複宣言', 'usecase-beta\nactor A("会員")\nactor A("会員")\nsystemBoundary S["注文"]\n U("注文する")\nend\nA -- U\n', 'OUT-04'),
            ('暗黙端点', 'usecase-beta\nactor A("会員")\nsystemBoundary S["注文"]\n U("注文する")\nend\nA -- Missing\n', 'OUT-02'),
            ('異種include', 'usecase-beta\nactor A("会員")\nsystemBoundary S["注文"]\n U("注文する")\nend\nA ..> : include U\n', 'OUT-02')):
            bad = {'title': label, 'description': label, 'diagrams': [{'id': 'd01', 'title': label, 'summary': label, 'mermaid': source}]}
            request.write_bytes(encoded(bad))
            try:
                build(request, base, 'invalid', mermaid=mermaid, browser=browser)
            except Problem as error:
                require(error.rule == expected, 'STEP-06', label + 'の判定が不一致です: ' + str(error))
            else:
                raise Problem('STEP-06', label + 'を受け入れました。')
            require(not (base / 'artifacts/usecase/invalid').exists(), 'STEP-06', '失敗した図を出力しました。')
            results.append(label + 'をnative parserと追加契約で拒否')
        different = json.loads(json.dumps(data)); different['title'] += '（更新）'
        request.write_bytes(encoded(different))
        try:
            build(request, base, 'test', mermaid=mermaid, browser=browser)
        except Problem as error:
            require(error.rule == 'OUT-06', 'STEP-06', '既存出力の保護に失敗しました。')
        else:
            raise Problem('STEP-06', '--replaceなしで既存出力を変更しました。')
        results.append('--replaceなしでの変更を拒否')
        png = catalog.parent / load(catalog)['diagrams'][0]['image']
        original_png = png.read_bytes(); png.write_bytes(original_png[:-1])
        try:
            check(catalog)
        except Problem as error:
            require(error.rule == 'OUT-07', 'STEP-06', 'PNGの破損を検出できません。')
        else:
            raise Problem('STEP-06', '破損PNGを受け入れました。')
        finally:
            png.write_bytes(original_png)
        results.append('PNGの切断を拒否')
        (catalog.parent / 'keep.txt').write_text('利用者のファイル', encoding='utf-8')
        request.write_bytes(encoded(data))
        try:
            build(request, base, 'test', True, mermaid, browser)
        except Problem as error:
            require(error.rule == 'OUT-01', 'STEP-06', '未管理ファイルの保護に失敗しました。')
        else:
            raise Problem('STEP-06', '未管理ファイルを持つ出力先を変更しました。')
        results.append('未管理ファイルを持つ出力先を保護')
    return results


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    for name in ('preflight', 'build', 'check', 'review', 'preview', 'report', 'selftest'):
        command = commands.add_parser(name)
        command.add_argument('--root', type=Path, default=Path.cwd())
        command.add_argument('--mermaid')
        command.add_argument('--browser')
        if name == 'build':
            command.add_argument('--request', type=Path, required=True)
            command.add_argument('--name', default='catalog')
            command.add_argument('--replace', action='store_true')
        if name in ('check', 'review', 'preview', 'report'):
            command.add_argument('--catalog', type=Path, required=True)
        if name == 'preview':
            command.add_argument('--out', type=Path, required=True)
        if name == 'check':
            command.add_argument('--deep', action='store_true')
        if name == 'review':
            command.add_argument('--notes', required=True)
        if name == 'selftest':
            command.add_argument('--sample', type=Path, default=SKILL / 'assets/examples/request.json')
    args = parser.parse_args()
    try:
        if args.command == 'preflight':
            result = {k: str(v) for k, v in resources(args.root, args.mermaid, args.browser).items()}
            result['platform'] = os.name
        elif args.command == 'build':
            result = build(args.request, args.root, args.name, args.replace, args.mermaid, args.browser)
        elif args.command == 'check':
            environment = resources(args.root, args.mermaid, args.browser) if args.deep else None
            work = args.root / '.skill-runs/generate-usecase-diagram/work'
            if args.deep:
                work.mkdir(parents=True, exist_ok=True)
            receipt = check(args.catalog, args.deep, environment, work)
            result = {'status': 'passed', 'diagrams': len(receipt['diagrams']), 'visual_review': receipt['visual_review']['status'], 'native_reparse': bool(args.deep)}
        elif args.command == 'review':
            record_review(args.catalog, args.notes, args.root)
            result = {'visual_review': 'reviewed'}
        elif args.command == 'preview':
            result = record_preview(args.catalog, args.out, args.root,
                                    resources(args.root, args.mermaid, args.browser))
        elif args.command == 'report':
            receipt = check(args.catalog)
            print('## カタログ\n\n- [HTMLを開く](' + str(args.catalog.resolve().parent / 'index.html') + ')')
            print('- 図: ' + str(len(receipt['diagrams'])) + '枚。原本・PNG・HTML・変換記録の対応を検査済み。')
            print('- 目視: ' + receipt['visual_review']['status'])
            return 0
        else:
            result = selftest(args.sample, args.root, args.mermaid, args.browser)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (OSError, ValueError, KeyError, TypeError) as error:
        print(str(error) if isinstance(error, Problem) else 'OUT-02 ' + str(error))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
