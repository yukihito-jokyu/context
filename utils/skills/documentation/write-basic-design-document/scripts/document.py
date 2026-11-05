"""基本設計の原本からMermaid・PNG・Markdown・HTMLを作り検査する。

STEP-03、STEP-04、OUT-01、OUT-02、OUT-04、OUT-05、OUT-06、OUT-07、OUT-08、OUT-09。
出力: doctorは描画経路、buildは出力一式、checkはルールID付きの指摘。
使い方: python3 document.py doctor
        python3 document.py build --source basic-design-document.json --out out
        python3 document.py check --source basic-design-document.json --out out
終了コード: 0 成功、1 指摘または描画失敗、2 引数の誤り。
Python標準ライブラリと既存のmermaid-cliを使う。パッケージを取得しない。
"""
import argparse
import base64
import hashlib
import html
import json
import os
from pathlib import Path
import re
import shutil
import struct
import subprocess
import tempfile
import zlib


AREAS = ('architecture', 'screen', 'data', 'integration')
AREA_NAMES = dict(zip(AREAS, ('全体構成', '画面と操作', 'データ設計', '外部連携')))
KINDS = ('context', 'component', 'workflow', 'screen', 'data', 'sequence', 'state', 'deployment')
NAMES = dict(zip(KINDS, ('境界と外部の関係図', '責務の分担図', '処理フロー図', '画面遷移図', '論理データの関係図', '連携のシーケンス図', '状態遷移図', '配置図')))
QUALITY = ('performance', 'availability', 'security', 'privacy', 'operations', 'accessibility')
QUALITY_JA = ('性能', '可用性', 'セキュリティ', '個人情報', '運用', 'アクセシビリティ')
ROOT_KEYS = {'title', 'language', 'summary', 'background', 'purpose', 'readers', 'terms', 'scope', 'actors', 'requirements', 'coverage', 'designs', 'quality', 'constraints', 'open_questions', 'sources', 'diagrams', 'diagram_decisions', 'handoff'}
HEADINGS = {
    'ja': ('概要', '前提と要望', '全体構成', '画面と操作', 'データ設計', '外部連携', '品質と運用', '未決事項と詳細設計への引継ぎ', '根拠と補足'),
    'en': ('Overview', 'Context and requirements', 'Architecture', 'Screens and interaction', 'Logical data design', 'External integration', 'Quality and operations', 'Open questions and detailed design', 'Evidence and notes'),
}
SECTIONS = ('overview', 'context', 'architecture', 'screens', 'data', 'integration', 'quality', 'handoff', 'evidence')
RENDER_CONFIG = {'securityLevel': 'strict', 'startOnLoad': False, 'theme': 'neutral', 'fontFamily': 'Hiragino Sans, Noto Sans CJK JP, sans-serif', 'flowchart': {'htmlLabels': False, 'useMaxWidth': False, 'wrappingWidth': 420}, 'sequence': {'useMaxWidth': False}}
INTERNAL_ID = re.compile(r'(?<![A-Za-z0-9_])(?:SRC|ACT|REQ|DES|D|Q)-[0-9]{2,}(?![0-9])')


def recipe():
    return digest(json.dumps(RENDER_CONFIG, sort_keys=True).encode())


def digest(value):
    return hashlib.sha256(value).hexdigest()


def sha(path):
    return digest(Path(path).read_bytes())


def e(value):
    return html.escape(str(value), quote=True)


def read_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def write_json(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def reader_texts(value, path=''):
    """Read authored prose and diagram source, excluding internal references and verbatim quotes."""
    if isinstance(value, dict):
        for key, item in value.items():
            if key != 'id' and not key.endswith('_ids') and key != 'quote':
                yield from reader_texts(item, path + '.' + key)
    elif isinstance(value, list):
        for index, item in enumerate(value):
            yield from reader_texts(item, path + '[' + str(index) + ']')
    elif isinstance(value, str):
        yield path, value


def validate(d):
    """Validate the authored structure and links; review meaning against the input."""
    errors = []

    def issue(rule, message):
        errors.append(rule + ' ' + message)

    def text(value, where):
        if not isinstance(value, str) or not value.strip():
            issue('OUT-02', where + ': 空でない文字列が必要である')

    def strings(value, where, minimum=0):
        if not isinstance(value, list) or len(value) < minimum or any(not isinstance(x, str) or not x.strip() for x in value):
            issue('OUT-02', where + ': 文字列の一覧と指定件数が必要である')

    def fields(value, required, where):
        if not isinstance(value, dict) or not set(required).issubset(value):
            issue('OUT-02', where + ': 必須の項目がない')
            return False
        if set(value) - set(required):
            issue('OUT-07', where + ': 未定義の項目がある ' + ', '.join(sorted(set(value) - set(required))))
        return True

    if not isinstance(d, dict):
        return ['OUT-02 原本はJSONオブジェクトにする']
    if set(d) - ROOT_KEYS:
        issue('OUT-07', '未定義の項目がある: ' + ', '.join(sorted(set(d) - ROOT_KEYS)))
    if ROOT_KEYS - set(d):
        return errors + ['OUT-02 原本にない項目: ' + ', '.join(sorted(ROOT_KEYS - set(d)))]
    for key in ('title', 'summary', 'purpose'):
        text(d[key], key)
    if d['language'] not in HEADINGS:
        issue('OUT-02', 'languageはjaまたはenにする')
    for key in ('background', 'readers', 'handoff'):
        strings(d[key], key, 1)
    if not fields(d['scope'], ('in', 'out'), 'scope'):
        return errors
    for key in ('in', 'out'):
        strings(d['scope'][key], 'scope.' + key, 1)
    shapes = {
        'sources': ('id', 'label', 'location', 'quote'),
        'actors': ('id', 'name', 'role', 'source_ids'),
        'requirements': ('id', 'title', 'statement', 'source_ids'),
        'coverage': ('area', 'applicable', 'reason', 'source_ids', 'question_ids'),
        'designs': ('id', 'area', 'title', 'statement', 'reason', 'details', 'status', 'requirement_ids', 'source_ids', 'diagram_ids', 'question_ids'),
        'diagrams': ('id', 'kind', 'area', 'title', 'intro', 'takeaway', 'alt', 'design_ids', 'source_ids', 'mermaid'),
        'open_questions': ('id', 'question', 'consequence', 'source_ids'),
        'terms': ('term', 'definition', 'source_ids'),
        'quality': ('category', 'status', 'statement', 'acceptance', 'source_ids', 'question_ids'),
        'constraints': ('statement', 'source_ids'),
        'diagram_decisions': ('kind', 'selected', 'reason', 'source_ids'),
    }
    for key, shape in shapes.items():
        minimum = 1 if key in ('sources', 'requirements', 'designs', 'diagrams') else 0
        if not isinstance(d[key], list) or len(d[key]) < minimum:
            issue('OUT-02', key + ': 一覧の形または件数が違う')
            return errors
        for index, row in enumerate(d[key]):
            where = key + '[' + str(index) + ']'
            if not fields(row, shape, where):
                return errors
            for field in shape:
                if field.endswith('_ids') or field in ('acceptance', 'details'):
                    strings(row[field], where + '.' + field)
                elif field in ('selected', 'applicable'):
                    if not isinstance(row[field], bool):
                        issue('OUT-09', where + '.' + field + ': 真偽値が必要である')
                else:
                    text(row[field], where + '.' + field)
    if errors:
        return sorted(set(errors))
    for key, prefix in {'sources': 'SRC', 'actors': 'ACT', 'requirements': 'REQ', 'designs': 'DES', 'diagrams': 'D', 'open_questions': 'Q'}.items():
        if [x['id'] for x in d[key]] != [prefix + '-' + str(i).zfill(2) for i in range(1, len(d[key]) + 1)]:
            issue('OUT-04', key + ': IDを01から出現順の連番にする')
    for path, value in reader_texts(d):
        if INTERNAL_ID.search(value):
            issue('OUT-04', path + ': 内部IDでなく内容の分かる名前を書く')
    indices = {key: {x['id']: x for x in d[key]} for key in ('sources', 'requirements', 'designs', 'diagrams', 'open_questions')}
    for key in shapes:
        for row in d[key]:
            if 'source_ids' in row:
                refs = row['source_ids']
                if (key not in ('coverage', 'quality', 'open_questions', 'diagram_decisions') and not refs) or any(x not in indices['sources'] for x in refs):
                    issue('OUT-08', key + ': 根拠の参照先がない')
            for field, target in (('requirement_ids', 'requirements'), ('question_ids', 'open_questions'), ('design_ids', 'designs')):
                if field in row and any(x not in indices[target] for x in row[field]):
                    issue('OUT-08', key + ': ' + field + 'の参照先がない')
            if key in ('designs', 'quality'):
                if row['status'] not in ('stated', 'proposal', 'open'):
                    issue('OUT-02', key + ': statusはstated・proposal・openにする')
                if row['status'] == 'open' and not row['question_ids']:
                    issue('OUT-08', key + ': 未決の内容を確認質問へ結び付ける')
                if row['status'] == 'stated' and not row['source_ids']:
                    issue('OUT-08', key + ': 入力の事実には根拠が必要である')
    if [x['area'] for x in d['coverage']] != list(AREAS):
        issue('OUT-09', 'coverageはarchitecture・screen・data・integrationの順にする')
        return sorted(set(errors))
    coverage = {x['area']: x for x in d['coverage']}
    for area in ('architecture', 'data'):
        if not coverage[area]['applicable']:
            issue('OUT-09', area + ': 設計の観点を採用する')
    for area in AREAS:
        found = [x for x in d['designs'] if x['area'] == area]
        if coverage[area]['applicable'] != bool(found):
            issue('OUT-09', area + ': 観点の採否と設計の有無が違う')
    for row in d['designs']:
        if row['area'] not in AREAS:
            issue('OUT-02', row['id'] + ': areaの値が違う')
        if not row['requirement_ids']:
            issue('OUT-08', row['id'] + ': 元の要望へ参照を付ける')
        if not row['diagram_ids'] or any(x not in indices['diagrams'] for x in row['diagram_ids']):
            issue('OUT-02', row['id'] + ': 関連する図がない')
        for did in row['diagram_ids']:
            if did in indices['diagrams'] and row['id'] not in indices['diagrams'][did]['design_ids']:
                issue('OUT-08', row['id'] + ': 図から設計への参照がない')
    for row in d['requirements']:
        if not any(row['id'] in x['requirement_ids'] for x in d['designs']):
            issue('OUT-08', row['id'] + ': 設計へ結び付いていない要望がある')
    if [x['category'] for x in d['quality']] != list(QUALITY):
        issue('OUT-02', 'qualityは性能・可用性・セキュリティ・個人情報・運用・アクセシビリティの順にする')
    seen = {x['kind'] for x in d['diagrams']}
    required = {'context', 'component', 'workflow', 'data'}
    if coverage['screen']['applicable']:
        required.add('screen')
    if coverage['integration']['applicable']:
        required.add('sequence')
    if not required.issubset(seen):
        issue('OUT-09', '必要な図がない: ' + '・'.join(sorted(required - seen)))
    if [x['kind'] for x in d['diagram_decisions']] != list(KINDS):
        issue('OUT-09', '8種類の図の採否を指定順で記録する')
    for row in d['diagram_decisions']:
        if row['selected'] != (row['kind'] in seen):
            issue('OUT-09', row['kind'] + ': 採否と実際の図が違う')
    fixed_areas = {'context': 'architecture', 'component': 'architecture', 'screen': 'screen', 'data': 'data', 'sequence': 'integration', 'deployment': 'architecture'}
    syntax = {'state': ('stateDiagram-v2',), 'sequence': ('sequenceDiagram',), 'data': ('erDiagram', 'classDiagram', 'flowchart')}
    for row in d['diagrams']:
        kind, source, area = row['kind'], row['mermaid'], row['area']
        if kind not in KINDS or area not in AREAS:
            issue('OUT-09', row['id'] + ': 図の種別または観点が違う')
            continue
        if not coverage[area]['applicable'] or (kind in fixed_areas and fixed_areas[kind] != area):
            issue('OUT-09', row['id'] + ': 図を置く観点が採否または種別と違う')
        token = source.strip().splitlines()[0].strip()
        if not any(token == a or token.startswith(a + ' ') for a in syntax.get(kind, ('flowchart',))):
            issue('OUT-09', row['id'] + ': 種別に合うMermaid構文を使う')
        if re.search(r'https?://|file:|data:|%%\{|^\s*---|^\s*(?:click|links?)\b|<\s*(?:script|img|iframe|a\b)', source, re.M | re.I):
            issue('OUT-09', row['id'] + ': 外部参照・初期化指令・埋め込みHTMLは使わない')
        if kind == 'data' and re.search(r'\b(?:PK|FK|varchar|timestamp|uuid)\b|^\s*[+-].*\(', source, re.M | re.I):
            issue('OUT-09', row['id'] + ': 物理列とメソッドはhandoffへ分ける')
        if len(source) > 6000:
            issue('OUT-05', row['id'] + ': Mermaid原本の上限6000文字を超えている')
        if not row['design_ids']:
            issue('OUT-08', row['id'] + ': 対応する設計の参照がない')
        for design_id in row['design_ids']:
            found = indices['designs'].get(design_id)
            if found and row['id'] not in found['diagram_ids']:
                issue('OUT-08', row['id'] + ': 設計から図への参照がない')
    return sorted(set(errors))


def environment():
    """Resolve installed tools; cached npm packages are read, never downloaded."""
    candidates = []
    explicit = os.environ.get('BASIC_DESIGN_MMDC')
    if explicit:
        candidates.append(Path(explicit))
    command = shutil.which('mmdc')
    if command:
        candidates.append(Path(command))
    for p in [Path.cwd(), *Path.cwd().parents]:
        candidates.append(p / 'node_modules/.bin/mmdc')
    cached = sorted((Path.home() / '.npm/_npx').glob('*/node_modules/@mermaid-js/mermaid-cli/src/cli.js'))
    candidates.extend(cached)
    cli = next((x.resolve() for x in candidates if x.is_file()), None)
    if not cli:
        raise ValueError('STEP-04 既存のmermaid-cliがない。BASIC_DESIGN_MMDCへmmdcまたはcli.jsのパスを指定する')
    command = [str(cli)]
    if cli.suffix == '.js':
        node = shutil.which('node')
        if not node:
            raise ValueError('STEP-04 Node.jsが見つからない')
        command = [node, str(cli)]
    result = subprocess.run(command + ['--version'], capture_output=True, text=True, timeout=15)
    version = result.stdout.strip()
    match = re.search(r'(\d+)\.\d+\.\d+', version)
    if result.returncode or not match or int(match.group(1)) < 11:
        raise ValueError('STEP-04 mermaid-cli 11以降が必要である: ' + version)
    browser = os.environ.get('BASIC_DESIGN_BROWSER')
    if not browser:
        browser = next((str(p) for p in [Path('/Applications/Google Chrome.app/Contents/MacOS/Google Chrome')]
                        if p.is_file()), None)
    return {'command': command, 'version': version, 'browser': browser}


def png_info(path):
    data = Path(path).read_bytes()
    if not data.startswith(b'\x89PNG\r\n\x1a\n'):
        raise ValueError('STEP-03 PNGの署名が違う: ' + Path(path).name)
    pos, image, compressed, ended = 8, None, b'', False
    while pos + 12 <= len(data):
        size = struct.unpack('>I', data[pos:pos + 4])[0]
        kind = data[pos + 4:pos + 8]
        payload = data[pos + 8:pos + 8 + size]
        end = pos + 12 + size
        if end > len(data) or zlib.crc32(kind + payload) & 0xffffffff != struct.unpack('>I', data[end - 4:end])[0]:
            raise ValueError('STEP-03 PNGのデータまたはCRCが壊れている: ' + Path(path).name)
        if kind == b'IHDR':
            image = struct.unpack('>IIBBBBB', payload)
        if kind == b'IDAT':
            compressed += payload
        if kind == b'IEND':
            ended = end == len(data)
            break
        pos = end
    if not ended or not image or not compressed:
        raise ValueError('STEP-03 PNGが完結していない: ' + Path(path).name)
    width, height = image[:2]
    if min(width, height) < 32:
        raise ValueError('STEP-03 PNGの図が小さすぎる: ' + Path(path).name)
    if width > 6000 or height > 6000 or width * height > 25000000:
        raise ValueError('OUT-05 PNGの寸法の上限を超えている: ' + Path(path).name)
    if len(zlib.decompress(compressed)) < height:
        raise ValueError('STEP-03 PNGの画素がない: ' + Path(path).name)
    return width, height


CSS = '''
:root{color-scheme:light;--ink:#172738;--muted:#506174;--line:#cbd5e1;--accent:#24578d;--paper:#fff;--back:#f4f6f9}
*{box-sizing:border-box}html{scroll-behavior:auto;scroll-padding-top:24px}body{margin:0;background:var(--back);color:var(--ink);font:17px/1.85 -apple-system,BlinkMacSystemFont,"Hiragino Sans","Noto Sans CJK JP",sans-serif}
a{color:var(--accent);text-underline-offset:.2em}a:focus-visible,summary:focus-visible{outline:3px solid #a45200;outline-offset:4px}header,main,nav,footer{width:min(100% - 40px,1040px);margin-inline:auto}
header{padding:48px 0 24px}h1{font-size:clamp(26px,4vw,38px);line-height:1.45;margin:8px 0 16px}h2{font-size:25px;line-height:1.5;margin:0 0 16px}h3{font-size:20px;line-height:1.6;margin:20px 0 8px}p{max-width:44em;margin:0 0 16px;overflow-wrap:anywhere}ul,ol{padding-left:1.5em;margin:8px 0 20px}li{margin:6px 0}
.eyebrow,.muted{color:var(--muted);font-size:14px}.lead{font-size:19px;max-width:40em}.toc{padding:16px 24px;background:#eaf0f7;border:1px solid var(--line);border-radius:10px;margin-bottom:24px}.toc ol{display:flex;flex-wrap:wrap;gap:8px 28px;margin:0;padding-left:1.2em}.toc li{font-size:15px}
section{background:var(--paper);border:1px solid var(--line);border-radius:10px;padding:32px;margin-bottom:24px}article{border-top:1px solid var(--line);padding:20px 0 4px;scroll-margin-top:24px}.req{border-left:4px solid var(--accent);padding-left:20px}.status{display:inline-block;border:1px solid #b8c8d8;border-radius:4px;font-size:13px;line-height:1.7;padding:1px 8px;margin-bottom:10px}.status-open{border-color:#b77814;background:#fff5df;color:#664200}
figure{margin:20px 0 28px;padding:20px;background:#f7f9fc;border:1px solid var(--line);border-radius:8px}.diagram-image{display:block;width:auto;max-width:100%;height:auto;margin-inline:auto;object-fit:contain;background:white}figcaption{margin-top:16px}figcaption p{margin-bottom:8px}.refs{font-size:14px;color:var(--muted)}.refs a{margin-right:12px}.zoom{overflow:auto;max-height:75vh}.zoom img{max-width:none;display:block}.downloads{font-size:14px;display:flex;flex-wrap:wrap;gap:16px}
details{margin:12px 0}summary{cursor:pointer;color:var(--accent);font-size:15px}pre{white-space:pre-wrap;overflow-wrap:anywhere;font-size:13px;line-height:1.6;padding:16px;background:#edf2f7}blockquote{margin:12px 0;padding-left:16px;border-left:3px solid var(--line);max-width:44em}dl{margin:0}dt{font-weight:700}dd{margin:0 0 16px}.scope-columns{display:grid;grid-template-columns:1fr 1fr;gap:24px}.skip{display:block;padding:8px 20px}footer{font-size:14px;color:var(--muted);padding:8px 0 32px}
@media(max-width:700px){body{font-size:16px}header,main,nav,footer{width:min(100% - 24px,1040px)}header{padding-top:24px}section{padding:22px 18px}.toc{padding:14px 18px}.toc ol{display:block}figure{padding:12px;margin-inline:0}.scope-columns{display:block}h2{font-size:22px}}
@media print{body{background:white;font-size:11pt}header,main,nav,footer{width:100%;margin:0}header{padding:0 0 16px}section{padding:16px 0;border:0;border-radius:0;break-before:auto}.toc,.skip,.downloads,.zoom-control,.source-control{display:none}article,figure{break-inside:avoid}details.evidence-details{display:block}details.evidence-details>summary{display:none}details.evidence-details>*{display:block}a{color:inherit;text-decoration:none}}
'''


def render_html(d, directory, manifest):
    ja = d['language'] == 'ja'
    headings = HEADINGS[d['language']]
    labels = {x['id']: x['title'] for key in ('requirements', 'designs', 'diagrams') for x in d[key]}
    labels.update({x['id']: x['label'] + ' · ' + x['location'] for x in d['sources']})
    labels.update({x['id']: x['question'] for x in d['open_questions']})

    def tr(a, b):
        return a if ja else b

    def para(value):
        return '<p>' + e(value) + '</p>'

    def bullets(values):
        return '<ul>' + ''.join('<li>' + e(x) + '</li>' for x in values) + '</ul>'

    def links(ids):
        return ''.join('<a href="#' + e(x) + '">' + e(labels[x]) + '</a> ' for x in ids)

    def refs(ids):
        return '<p class="refs">' + tr('根拠：', 'Evidence: ') + links(ids) + '</p>' if ids else ''

    def status(value):
        text = {'stated': tr('入力に記載', 'Stated in input'), 'proposal': tr('設計案', 'Design proposal'), 'open': tr('未決', 'Open')}[value]
        return '<span class="status status-' + value + '">' + text + '</span>'

    def section(index, body):
        return '<section id="' + SECTIONS[index] + '"><h2>' + str(index + 1) + '. ' + headings[index] + '</h2>' + body + '</section>'

    def figure(x):
        item = next(v for v in manifest['diagrams'] if v['id'] == x['id'])
        src = 'data:image/png;base64,' + base64.b64encode((directory / item['png']).read_bytes()).decode()
        mmd = base64.b64encode(x['mermaid'].encode()).decode()
        size = ' width="' + str(item['width']) + '" height="' + str(item['height']) + '"'
        display_size = ' width="' + str(max(1, item['width'] // 2)) + '" height="' + str(max(1, item['height'] // 2)) + '"'
        body = '<article id="' + e(x['id']) + '"><h3>' + e(x['title']) + '</h3>' + para(x['intro'])
        body += '<figure><img class="diagram-image" src="' + src + '" alt="' + e(x['alt']) + '"' + display_size + '><figcaption>' + para(x['takeaway'])
        body += '<p class="refs">' + tr('関連する設計：', 'Design: ') + links(x['design_ids']) + '</p>' + refs(x['source_ids']) + '</figcaption>'
        body += '<p class="downloads"><a download="' + e(Path(item['png']).name) + '" href="' + src + '">' + tr('図の画像を保存', 'Save diagram image') + '</a><a download="' + e(Path(item['mermaid']).name) + '" href="data:text/plain;charset=utf-8;base64,' + mmd + '">' + tr('図の記述を保存', 'Save diagram source') + '</a></p>'
        body += '<details class="zoom-control"><summary>' + tr('図を原寸で見る', 'View at original size') + '</summary><div class="zoom" tabindex="0"><img src="' + src + '" alt="' + e(x['alt']) + '"' + size + '></div></details>'
        body += '<details class="source-control"><summary>' + tr('図の記述を確認する', 'Inspect diagram source') + '</summary><pre><code>' + e(x['mermaid'].strip()) + '</code></pre></details></figure></article>'
        return body

    parts = ['<!doctype html>\n<html lang="' + d['language'] + '"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="source-sha256" content="' + manifest['source_sha256'] + '"><title>' + e(d['title']) + '</title><style>' + CSS + '</style></head><body>']
    parts.append('<a class="skip" href="#overview">' + tr('本文へ移動', 'Skip to content') + '</a><header><p class="eyebrow">' + tr('基本設計書 · 確認用ドラフト', 'Basic design · Review draft') + '</p><h1>' + e(d['title']) + '</h1><p class="lead">' + e(d['summary']) + '</p><p class="muted">' + tr('読者：', 'Readers: ') + e(' / '.join(d['readers'])) + '</p></header>')
    parts.append('<nav class="toc" aria-label="' + tr('目次', 'Contents') + '"><ol>' + ''.join('<li><a href="#' + sid + '">' + title + '</a></li>' for sid, title in zip(SECTIONS, headings)) + '</ol></nav><main>')
    body = '<h3>' + tr('解く課題', 'Problem') + '</h3>' + ''.join(para(x) for x in d['background']) + '<h3>' + tr('設計の目的', 'Purpose') + '</h3>' + para(d['purpose'])
    body += '<div class="scope-columns"><div><h3>' + tr('対象', 'In scope') + '</h3>' + bullets(d['scope']['in']) + '</div><div><h3>' + tr('対象外', 'Out of scope') + '</h3>' + bullets(d['scope']['out']) + '</div></div>'
    parts.append(section(0, body))
    body = para(tr('用語と役割を確認してから、会話で求められた振る舞いを読む。設計案は後の章で分けて示す。', 'Read the terms, roles and requested behavior before the design proposals.'))
    body += '<dl>' + ''.join('<dt>' + e(x['term']) + '</dt><dd>' + e(x['definition']) + refs(x['source_ids']) + '</dd>' for x in d['terms']) + '</dl>'
    for x in d['actors']:
        body += '<article id="' + e(x['id']) + '"><h3>' + e(x['name']) + '</h3>' + para(x['role']) + refs(x['source_ids']) + '</article>'
    for x in d['requirements']:
        design_ids = [v['id'] for v in d['designs'] if x['id'] in v['requirement_ids']]
        body += '<article id="' + e(x['id']) + '"><h3>' + e(x['title']) + '</h3>' + para(x['statement']) + '<p class="refs">' + tr('対応する設計：', 'Design: ') + links(design_ids) + '</p>' + refs(x['source_ids']) + '</article>'
    parts.append(section(1, body))
    for index, area in enumerate(AREAS, 2):
        coverage = next(x for x in d['coverage'] if x['area'] == area)
        body = para(coverage['reason']) + refs(coverage['source_ids'])
        if coverage['question_ids']:
            body += '<p class="refs">' + tr('確認する条件：', 'Questions: ') + links(coverage['question_ids']) + '</p>'
        if not coverage['applicable']:
            body += para(tr('この観点の設計は今回の対象に含めていない。理由と確認する条件は上記に示す。', 'This area is outside this draft; the reason and questions are stated above.'))
        for x in [v for v in d['designs'] if v['area'] == area]:
            body += '<article class="req" id="' + e(x['id']) + '"><h3>' + e(x['title']) + '</h3>' + status(x['status']) + para(x['statement']) + bullets(x['details'])
            body += '<h4>' + tr('採用理由', 'Rationale') + '</h4>' + para(x['reason'])
            body += '<p class="refs">' + tr('元の要望：', 'Requirements: ') + links(x['requirement_ids']) + '</p><p class="refs">' + tr('関連する図：', 'Diagrams: ') + links(x['diagram_ids']) + '</p>'
            if x['question_ids']:
                body += '<p class="refs">' + tr('確認する条件：', 'Questions: ') + links(x['question_ids']) + '</p>'
            body += refs(x['source_ids']) + '</article>'
        body += ''.join(figure(x) for x in d['diagrams'] if x['area'] == area)
        parts.append(section(index, body))
    body = para(tr('品質と運用の条件を確認する。入力の事実・設計案・未決を分け、未指定の目標値は確定しない。', 'Separate stated constraints, proposals and open questions; do not invent quality targets.'))
    grouped = {}
    for x, label in zip(d['quality'], QUALITY_JA if ja else QUALITY):
        key = (x['status'], x['statement'], tuple(x['acceptance']), tuple(x['source_ids']), tuple(x['question_ids']))
        grouped.setdefault(key, []).append(label)
    for (state, statement, acceptance, source_ids, question_ids), names in grouped.items():
        body += '<article><h3>' + e(' / '.join(names)) + '</h3>' + status(state) + para(statement) + bullets(acceptance) + refs(source_ids)
        if question_ids:
            body += '<p class="refs">' + tr('確認する条件：', 'Questions: ') + links(question_ids) + '</p>'
        body += '</article>'
    body += '<h3>' + tr('指定された制約', 'Specified constraints') + '</h3>'
    body += ''.join(para(x['statement']) + refs(x['source_ids']) for x in d['constraints']) or para(tr('入力に技術・配置の制約の指定はない。', 'No technology or deployment constraint is stated.'))
    parts.append(section(6, body))
    body = para(tr('次の質問に、決まるまで確定できない範囲を添える。その後で、詳細設計で具体化する作業を示す。', 'Each question states its design impact, followed by detailed design work.'))
    for x in d['open_questions']:
        body += '<article id="' + e(x['id']) + '"><h3>' + e(x['question']) + '</h3>' + para(x['consequence']) + refs(x['source_ids']) + '</article>'
    if not d['open_questions']:
        body += para(tr('この原本に未決事項は記録されていない。', 'No open questions are recorded.'))
    body += '<h3>' + tr('詳細設計へ引き継ぐ作業', 'Detailed design handoff') + '</h3>' + bullets(d['handoff'])
    parts.append(section(7, body))
    body = para(tr('設計の根拠を、資料の場所と実際の記述で確かめる。「入力に記載」は資料にあるという意味であり、承認済みを意味しない。', 'Check source locations and excerpts; stated input does not imply approval.'))
    for x in d['sources']:
        body += '<article id="' + e(x['id']) + '"><h3>' + e(x['label']) + '</h3><p class="muted">' + e(x['location']) + '</p><blockquote>' + e(x['quote']) + '</blockquote></article>'
    body += '<details class="evidence-details"><summary>' + tr('図を選んだ理由・省いた理由', 'Diagram selection decisions') + '</summary><dl>'
    for x in d['diagram_decisions']:
        body += '<dt>' + e(NAMES[x['kind']] if ja else x['kind']) + ' · ' + tr('採用' if x['selected'] else '省略', 'Selected' if x['selected'] else 'Omitted') + '</dt><dd>' + e(x['reason']) + refs(x['source_ids']) + '</dd>'
    body += '</dl></details>'
    parts.append(section(8, body))
    parts.append('</main><footer>' + tr('図・設計・採用理由・根拠を合わせて確認する。', 'Read diagrams, designs, rationale and evidence together.') + '</footer></body></html>\n')
    return '\n'.join(parts)


def md(value):
    """Keep authored text literal rather than interpreting it as Markdown or HTML."""
    return re.sub(r'([\\`*_{}\[\]()#+\-.!|])', r'\\\1', html.escape(str(value), quote=False))


def render_markdown(d, manifest):
    """Render the same design content with portable local image and source links."""
    ja = d['language'] == 'ja'
    headings = HEADINGS[d['language']]
    labels = {x['id']: x['title'] for key in ('requirements', 'designs', 'diagrams') for x in d[key]}
    labels.update({x['id']: x['label'] + ' · ' + x['location'] for x in d['sources']})
    labels.update({x['id']: x['question'] for x in d['open_questions']})
    parts = []

    def tr(a, b):
        return a if ja else b

    def paragraph(value):
        parts.append(md(value).replace('\n', '  \n'))

    def heading(level, value, anchor=None):
        if anchor:
            parts.append('<a id="' + e(anchor) + '"></a>')
        parts.append('#' * level + ' ' + md(value).replace('\n', ' '))

    def bullets(values):
        if values:
            parts.append('\n'.join('- ' + md(x).replace('\n', '  \n  ') for x in values))

    def links(prefix, ids):
        if ids:
            parts.append(prefix + ' '.join('[' + md(labels[x]).replace('\n', ' ') + '](#' + x + ')' for x in ids))

    def refs(ids):
        links(tr('根拠：', 'Evidence: '), ids)

    def status(value):
        paragraph({'stated': tr('入力に記載', 'Stated in input'), 'proposal': tr('設計案', 'Design proposal'), 'open': tr('未決', 'Open')}[value])

    def section(index):
        heading(2, str(index + 1) + '. ' + headings[index], SECTIONS[index])

    paragraph(tr('基本設計書 · 確認用ドラフト', 'Basic design · Review draft'))
    heading(1, d['title'])
    paragraph(d['summary'])
    paragraph(tr('読者：', 'Readers: ') + ' / '.join(d['readers']))
    heading(2, tr('目次', 'Contents'))
    parts.append('\n'.join('- [' + md(title) + '](#' + sid + ')' for sid, title in zip(SECTIONS, headings)))
    section(0)
    heading(3, tr('解く課題', 'Problem'))
    for value in d['background']:
        paragraph(value)
    heading(3, tr('設計の目的', 'Purpose'))
    paragraph(d['purpose'])
    for key, title in (('in', tr('対象', 'In scope')), ('out', tr('対象外', 'Out of scope'))):
        heading(3, title)
        bullets(d['scope'][key])
    section(1)
    paragraph(tr('用語と役割を確認してから、会話で求められた振る舞いを読む。設計案は後の章で分けて示す。', 'Read the terms, roles and requested behavior before the design proposals.'))
    for x in d['terms']:
        heading(3, x['term'])
        paragraph(x['definition'])
        refs(x['source_ids'])
    for x in d['actors']:
        heading(3, x['name'], x['id'])
        paragraph(x['role'])
        refs(x['source_ids'])
    for x in d['requirements']:
        heading(3, x['title'], x['id'])
        paragraph(x['statement'])
        links(tr('対応する設計：', 'Design: '), [v['id'] for v in d['designs'] if x['id'] in v['requirement_ids']])
        refs(x['source_ids'])
    for index, area in enumerate(AREAS, 2):
        section(index)
        coverage = next(x for x in d['coverage'] if x['area'] == area)
        paragraph(coverage['reason'])
        refs(coverage['source_ids'])
        links(tr('確認する条件：', 'Questions: '), coverage['question_ids'])
        if not coverage['applicable']:
            paragraph(tr('この観点の設計は今回の対象に含めていない。理由と確認する条件は上記に示す。', 'This area is outside this draft; the reason and questions are stated above.'))
        for x in (v for v in d['designs'] if v['area'] == area):
            heading(3, x['title'], x['id'])
            status(x['status'])
            paragraph(x['statement'])
            bullets(x['details'])
            heading(4, tr('採用理由', 'Rationale'))
            paragraph(x['reason'])
            links(tr('元の要望：', 'Requirements: '), x['requirement_ids'])
            links(tr('関連する図：', 'Diagrams: '), x['diagram_ids'])
            links(tr('確認する条件：', 'Questions: '), x['question_ids'])
            refs(x['source_ids'])
        for x in (v for v in d['diagrams'] if v['area'] == area):
            item = next(v for v in manifest['diagrams'] if v['id'] == x['id'])
            heading(3, x['title'], x['id'])
            paragraph(x['intro'])
            parts.append('![' + md(x['alt']).replace('\n', ' ') + '](' + item['png'] + ')')
            paragraph(x['takeaway'])
            links(tr('関連する設計：', 'Design: '), x['design_ids'])
            refs(x['source_ids'])
            parts.append('[' + tr('図の画像を開く', 'Open diagram image') + '](' + item['png'] + ') · [' + tr('Mermaid原本', 'Mermaid source') + '](' + item['mermaid'] + ')')
    section(6)
    paragraph(tr('品質と運用の条件を確認する。入力の事実・設計案・未決を分け、未指定の目標値は確定しない。', 'Separate stated constraints, proposals and open questions; do not invent quality targets.'))
    grouped = {}
    for x, label in zip(d['quality'], QUALITY_JA if ja else QUALITY):
        key = (x['status'], x['statement'], tuple(x['acceptance']), tuple(x['source_ids']), tuple(x['question_ids']))
        grouped.setdefault(key, []).append(label)
    for (state, statement, acceptance, source_ids, question_ids), names in grouped.items():
        heading(3, ' / '.join(names))
        status(state)
        paragraph(statement)
        bullets(acceptance)
        refs(source_ids)
        links(tr('確認する条件：', 'Questions: '), question_ids)
    heading(3, tr('指定された制約', 'Specified constraints'))
    for x in d['constraints']:
        paragraph(x['statement'])
        refs(x['source_ids'])
    if not d['constraints']:
        paragraph(tr('入力に技術・配置の制約の指定はない。', 'No technology or deployment constraint is stated.'))
    section(7)
    paragraph(tr('次の質問に、決まるまで確定できない範囲を添える。その後で、詳細設計で具体化する作業を示す。', 'Each question states its design impact, followed by detailed design work.'))
    for x in d['open_questions']:
        heading(3, x['question'], x['id'])
        paragraph(x['consequence'])
        refs(x['source_ids'])
    if not d['open_questions']:
        paragraph(tr('この原本に未決事項は記録されていない。', 'No open questions are recorded.'))
    heading(3, tr('詳細設計へ引き継ぐ作業', 'Detailed design handoff'))
    bullets(d['handoff'])
    section(8)
    paragraph(tr('設計の根拠を、資料の場所と実際の記述で確かめる。「入力に記載」は資料にあるという意味であり、承認済みを意味しない。', 'Check source locations and excerpts; stated input does not imply approval.'))
    for x in d['sources']:
        heading(3, x['label'], x['id'])
        paragraph(x['location'])
        parts.append('\n'.join('> ' + md(line) for line in x['quote'].splitlines()))
    heading(3, tr('図を選んだ理由・省いた理由', 'Diagram selection decisions'))
    for x in d['diagram_decisions']:
        heading(4, (NAMES[x['kind']] if ja else x['kind']) + ' · ' + tr('採用' if x['selected'] else '省略', 'Selected' if x['selected'] else 'Omitted'))
        paragraph(x['reason'])
        refs(x['source_ids'])
    paragraph(tr('図・設計・採用理由・根拠を合わせて確認する。', 'Read diagrams, designs, rationale and evidence together.'))
    return '\n\n'.join(parts) + '\n'


def build(source, out):
    d = read_json(source)
    errors = validate(d)
    if errors:
        return errors
    env = environment()
    out.mkdir(parents=True, exist_ok=True)
    old = read_json(out / 'manifest.json') if (out / 'manifest.json').is_file() else {}
    # Stage derived outputs. A failed conversion leaves the previous bundle intact.
    with tempfile.TemporaryDirectory(prefix='basic-design-build-', dir=out.parent) as temporary:
        stage = Path(temporary)
        (stage / 'diagrams').mkdir()
        puppet = {'args': ['--disable-background-networking', '--disable-extensions', '--no-first-run', '--host-resolver-rules=MAP * ~NOTFOUND, EXCLUDE localhost']}
        if env['browser']:
            puppet['executablePath'] = env['browser']
        write_json(stage / 'mermaid-config.json', RENDER_CONFIG)
        write_json(stage / 'puppeteer-config.json', puppet)
        manifest = {'version': 1, 'source_sha256': sha(source), 'diagrams': []}
        for x in d['diagrams']:
            stem = x['id'].lower() + '-' + x['kind']
            mmd, png = 'diagrams/' + stem + '.mmd', 'diagrams/' + stem + '.png'
            (stage / mmd).write_text(x['mermaid'].strip() + '\n', encoding='utf-8')
            prior = next((v for v in old.get('diagrams', []) if v.get('id') == x['id']), {})
            same = prior.get('mermaid_sha256') == sha(stage / mmd) and prior.get('renderer') == env['version'] and prior.get('recipe_sha256') == recipe()
            if same and (out / png).is_file() and sha(out / png) == prior.get('png_sha256'):
                shutil.copyfile(out / png, stage / png)
            else:
                args = env['command'] + ['-i', str(stage / mmd), '-o', str(stage / png), '-c', str(stage / 'mermaid-config.json'), '-p', str(stage / 'puppeteer-config.json'), '-w', '1400', '-H', '900', '-s', '2', '-b', 'white', '-q']
                result = subprocess.run(args, capture_output=True, text=True, timeout=60)
                if result.returncode:
                    raise ValueError('STEP-03 ' + x['id'] + ' の描画失敗: ' + (result.stderr or result.stdout)[-3000:])
            width, height = png_info(stage / png)
            manifest['diagrams'].append({'id': x['id'], 'kind': x['kind'], 'mermaid': mmd, 'png': png, 'mermaid_sha256': sha(stage / mmd), 'png_sha256': sha(stage / png), 'width': width, 'height': height, 'renderer': env['version'], 'recipe_sha256': recipe()})
        html_path = stage / 'basic-design-document.html'
        html_path.write_text(render_html(d, stage, manifest), encoding='utf-8')
        manifest['html_sha256'] = sha(html_path)
        markdown_path = stage / 'basic-design-document.md'
        markdown_path.write_text(render_markdown(d, manifest), encoding='utf-8')
        manifest['markdown_sha256'] = sha(markdown_path)
        write_json(stage / 'manifest.json', manifest)
        expected = {x[k] for x in manifest['diagrams'] for k in ('mermaid', 'png')}
        (out / 'diagrams').mkdir(exist_ok=True)
        for name in sorted(expected | {'basic-design-document.html', 'basic-design-document.md', 'manifest.json'}):
            os.replace(stage / name, out / name)
        for p in (out / 'diagrams').iterdir():
            if p.suffix in ('.mmd', '.png') and p.relative_to(out).as_posix() not in expected:
                p.unlink()
    return check(source, out)


def check(source, out):
    d = read_json(source)
    errors = validate(d)
    if errors:
        return errors
    for name in ('basic-design-document.html', 'basic-design-document.md', 'manifest.json'):
        if not (out / name).is_file():
            return ['OUT-01 出力がない: ' + name]
    manifest = read_json(out / 'manifest.json')
    if set(manifest) != {'version', 'source_sha256', 'diagrams', 'html_sha256', 'markdown_sha256'} or manifest['version'] != 1:
        return ['OUT-07 manifestの形が違う。buildで生成し直す']
    if manifest['source_sha256'] != sha(source):
        return ['OUT-06 原本のハッシュが違う。buildで生成し直す']
    if not isinstance(manifest['diagrams'], list) or len(manifest['diagrams']) != len(d['diagrams']):
        return ['OUT-06 manifestの図の件数が違う']
    expected = set()
    for x, item in zip(d['diagrams'], manifest['diagrams']):
        stem = x['id'].lower() + '-' + x['kind']
        mmd, png = 'diagrams/' + stem + '.mmd', 'diagrams/' + stem + '.png'
        expected.update((mmd, png))
        if item.get('id') != x['id'] or item.get('kind') != x['kind'] or item.get('mermaid') != mmd or item.get('png') != png:
            return ['OUT-06 manifestの図・原本・PNGの対応が違う']
        if item.get('recipe_sha256') != recipe():
            return ['OUT-06 描画設定が変わっている。buildで生成し直す']
        for name in (mmd, png):
            if not (out / name).is_file():
                return ['OUT-01 図の出力がない: ' + name]
        if (out / mmd).read_text(encoding='utf-8') != x['mermaid'].strip() + '\n' or sha(out / mmd) != item.get('mermaid_sha256'):
            return ['OUT-06 Mermaid原本が同期していない: ' + mmd]
        width, height = png_info(out / png)
        if sha(out / png) != item.get('png_sha256') or (width, height) != (item.get('width'), item.get('height')):
            return ['STEP-03 PNGの実体がmanifestと違う: ' + png]
    actual = {p.relative_to(out).as_posix() for p in (out / 'diagrams').iterdir() if p.is_file()}
    if actual != expected:
        return ['OUT-01 diagramsのファイルがmanifestと一致しない']
    actual_html = (out / 'basic-design-document.html').read_text(encoding='utf-8')
    for sid in SECTIONS:
        if ('<section id="' + sid + '">') not in actual_html:
            return ['OUT-02 HTMLの章がない: ' + sid]
    if '<script' in actual_html.lower() or re.search(r'(?:src|href)="https?://', actual_html):
        return ['OUT-02 HTMLに外部の依存またはスクリプトがある']
    if sha(out / 'basic-design-document.html') != manifest['html_sha256'] or actual_html != render_html(d, out, manifest):
        return ['OUT-06 HTMLの本文・埋め込みPNGが原本と同期していない']
    actual_markdown = (out / 'basic-design-document.md').read_text(encoding='utf-8')
    if sha(out / 'basic-design-document.md') != manifest['markdown_sha256'] or actual_markdown != render_markdown(d, manifest):
        return ['OUT-06 Markdownの本文・図への参照が原本と同期していない']
    return []


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    sub.add_parser('doctor')
    for command in ('build', 'check'):
        child = sub.add_parser(command)
        child.add_argument('--source', type=Path, required=True)
        child.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    try:
        if args.command == 'doctor':
            env = environment()
            print('描画: mermaid-cli ' + env['version'])
            print('実行経路: ' + ' '.join(env['command']))
            print('実描画とブラウザー起動: buildで確認する')
            print('図の構文: flowchart / stateDiagram-v2 / sequenceDiagram / classDiagram / erDiagram')
            print('追加取得: しない')
            return 0
        errors = (build if args.command == 'build' else check)(args.source.resolve(), args.out.resolve())
        for error in errors:
            print(error)
        if errors:
            return 1
        print('原本・Mermaid・PNG・Markdown・HTML・参照・同期: 指摘0件')
        return 0
    except (OSError, ValueError, KeyError, TypeError, struct.error, zlib.error, subprocess.SubprocessError) as error:
        message = str(error)
        print(message if re.match(r'^[A-Z]+-\d\d ', message) else 'STEP-03 ' + message)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
