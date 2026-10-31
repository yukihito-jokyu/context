"""要件定義の原本からMermaid・PNG・HTMLを作り検査する。

STEP-03、STEP-04、OUT-01、OUT-02、OUT-04、OUT-05、OUT-06、OUT-07、OUT-08、OUT-09。
出力: doctorは描画経路、buildは出力一式、checkはルールID付きの指摘。
使い方: python3 document.py doctor
        python3 document.py build --source requirement-document.json --out out
        python3 document.py check --source requirement-document.json --out out
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


KINDS = ('context', 'usecase', 'workflow', 'state', 'screen', 'domain', 'sequence', 'concept', 'component')
NAMES = dict(zip(KINDS, ('システムコンテキスト図', 'ユースケース図', '業務フロー図', '状態遷移図', '画面遷移図', 'ドメインモデル図', 'シーケンス図', '概念のER・クラス図', 'コンポーネント図')))
QUALITY = ('performance', 'availability', 'security', 'privacy', 'operations', 'accessibility')
QUALITY_JA = ('性能', '可用性', 'セキュリティ', '個人情報', '運用', 'アクセシビリティ')
ROOT_KEYS = {'title', 'language', 'summary', 'background', 'purpose', 'readers', 'terms', 'scope', 'actors', 'requirements', 'quality', 'constraints', 'open_questions', 'sources', 'diagrams', 'diagram_decisions', 'design_notes'}
HEADINGS = {
    'ja': ('概要', '用語と前提', '対象範囲', '全体像と業務', '機能要件', '品質と制約', '未決事項', '根拠と補足'),
    'en': ('Overview', 'Terms and assumptions', 'Scope', 'System and workflows', 'Functional requirements', 'Quality and constraints', 'Open questions', 'Evidence and notes'),
}
SECTIONS = ('overview', 'terms', 'scope', 'diagrams', 'requirements', 'quality', 'questions', 'evidence')
RENDER_CONFIG = {'securityLevel': 'strict', 'startOnLoad': False, 'theme': 'neutral', 'fontFamily': 'Hiragino Sans, Noto Sans CJK JP, sans-serif', 'flowchart': {'htmlLabels': False, 'useMaxWidth': False, 'wrappingWidth': 420}, 'sequence': {'useMaxWidth': False}}
INTERNAL_ID = re.compile(r'(?<![A-Za-z0-9_])(?:SRC|ACT|FR|D|Q)-[0-9]{2,}(?![0-9])')


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
    """Check the data shape and references; meaning is reviewed against the evidence."""
    errors = []

    def issue(rule, text):
        errors.append(rule + ' ' + text)

    def text(v, where):
        if not isinstance(v, str) or not v.strip():
            issue('OUT-02', where + ': 空でない文字列が必要である')
            return False
        return True

    def rows(v, where, minimum=0):
        if not isinstance(v, list) or len(v) < minimum:
            issue('OUT-02', where + ': 一覧の形または件数が違う')
            return []
        return v

    def fields(v, required, where):
        if not isinstance(v, dict) or not set(required).issubset(v):
            issue('OUT-02', where + ': 必須の項目がない')
            return False
        if set(v) - set(required):
            issue('OUT-07', where + ': 未定義の項目がある ' + ', '.join(sorted(set(v) - set(required))))
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
        issue('OUT-02', 'language は ja または en にする')
    for key in ('background', 'readers'):
        for item in rows(d[key], key, 1):
            text(item, key)
    if fields(d['scope'], ('in', 'out'), 'scope'):
        for key in ('in', 'out'):
            for item in rows(d['scope'][key], 'scope.' + key, 1):
                text(item, 'scope.' + key)
    else:
        return errors
    shapes = {
        'sources': ('id', 'label', 'location', 'quote'),
        'actors': ('id', 'name', 'role', 'source_ids'),
        'requirements': ('id', 'title', 'statement', 'reason', 'acceptance', 'status', 'source_ids', 'diagram_ids'),
        'diagrams': ('id', 'kind', 'title', 'intro', 'takeaway', 'alt', 'requirement_ids', 'source_ids', 'mermaid'),
        'open_questions': ('id', 'question', 'consequence', 'source_ids'),
        'terms': ('term', 'definition', 'source_ids'),
        'quality': ('category', 'status', 'statement', 'acceptance', 'source_ids'),
        'constraints': ('statement', 'source_ids'),
        'design_notes': ('statement', 'source_ids'),
        'diagram_decisions': ('kind', 'selected', 'reason', 'source_ids'),
    }
    groups = {}
    for key, shape in shapes.items():
        minimum = 1 if key in ('sources', 'actors', 'requirements', 'diagrams') else 0
        groups[key] = rows(d[key], key, minimum)
        for index, row in enumerate(groups[key]):
            if not fields(row, shape, key + '[' + str(index) + ']'):
                return errors
            for field in shape:
                if field.endswith('_ids') or field in ('acceptance',):
                    rows(row[field], key + '.' + field)
                elif field == 'selected':
                    if not isinstance(row[field], bool):
                        issue('OUT-09', 'selected は真偽値にする')
                else:
                    text(row[field], key + '.' + field)
    if errors:
        return errors
    prefixes = {'sources': 'SRC', 'actors': 'ACT', 'requirements': 'FR', 'diagrams': 'D', 'open_questions': 'Q'}
    for key, prefix in prefixes.items():
        expected = [prefix + '-' + str(i).zfill(2) for i in range(1, len(groups[key]) + 1)]
        if [x['id'] for x in groups[key]] != expected:
            issue('OUT-04', key + ': IDを01からの出現順の連番にする')
    for path, value in reader_texts(d):
        if INTERNAL_ID.search(value):
            issue('OUT-04', path + ': 本文・図には内部IDでなく内容が分かる名前を書く')
    source_ids = {x['id'] for x in d['sources']}
    req_ids = {x['id'] for x in d['requirements']}
    diagram_ids = {x['id'] for x in d['diagrams']}
    for key, values in groups.items():
        for row in values:
            if 'source_ids' in row:
                refs = row['source_ids']
                needs_evidence = key not in ('open_questions', 'quality', 'diagram_decisions') or row.get('status') == 'stated'
                if (needs_evidence and not refs) or any(x not in source_ids for x in refs):
                    issue('OUT-08', key + ': 根拠の参照先がない')
            if key == 'requirements':
                if not row['acceptance']:
                    issue('OUT-02', row['id'] + ': 受入条件か確認すべき条件を書く')
                if not row['diagram_ids'] or any(x not in diagram_ids for x in row['diagram_ids']):
                    issue('OUT-02', row['id'] + ': 関連する図の参照がない')
            if key in ('requirements', 'quality') and row['status'] not in ('stated', 'proposal', 'open'):
                issue('OUT-02', key + ': status は stated・proposal・open にする')
    if [x['category'] for x in d['quality']] != list(QUALITY):
        issue('OUT-02', 'quality は性能・可用性・セキュリティ・個人情報・運用・アクセシビリティの順にする')
    seen = {x['kind'] for x in d['diagrams']}
    if not {'context', 'usecase', 'workflow'}.issubset(seen):
        issue('OUT-09', 'context・usecase・workflowの図を作る')
    if [x['kind'] for x in d['diagram_decisions']] != list(KINDS):
        issue('OUT-09', '9種類の図の採否を指定の順で記録する')
    for row in d['diagram_decisions']:
        if row['selected'] != (row['kind'] in seen):
            issue('OUT-09', row['kind'] + ': 採否と実際の図が違う')
    if 'component' in seen and not d['constraints']:
        issue('OUT-09', 'componentは構成の指定をconstraintsに記録してから選ぶ')
    for row in d['diagrams']:
        kind, source = row['kind'], row['mermaid']
        if kind not in KINDS:
            issue('OUT-09', row['id'] + ': 図の種別が違う')
            continue
        token = source.strip().splitlines()[0].strip()
        allowed = ('flowchart',)
        if kind == 'state':
            allowed = ('stateDiagram-v2',)
        elif kind == 'sequence':
            allowed = ('sequenceDiagram',)
        elif kind == 'domain':
            allowed = ('classDiagram', 'flowchart')
        elif kind == 'concept':
            allowed = ('classDiagram', 'erDiagram')
        if not any(token == a or token.startswith(a + ' ') for a in allowed):
            issue('OUT-09', row['id'] + ': 種別に合うMermaid構文を使う')
        if re.search(r'https?://|file:|data:|%%\{|^\s*---|^\s*(?:click|links?)\b|<\s*(?:script|img|iframe|a\b)', source, re.M | re.I):
            issue('OUT-09', row['id'] + ': 外部参照・初期化指令・埋め込みHTMLは使わない')
        if kind in ('concept', 'domain') and re.search(r'\b(?:PK|FK|varchar|timestamp|uuid)\b|^\s*[+-].*\(', source, re.M | re.I):
            issue('OUT-09', row['id'] + ': 物理DBやメソッドの詳細はdesign_notesへ分ける')
        if len(source) > 6000:
            issue('OUT-05', row['id'] + ': Mermaid原本の上限6000文字を超えている')
        if not row['requirement_ids'] or any(x not in req_ids for x in row['requirement_ids']):
            issue('OUT-02', row['id'] + ': 要件の参照先がない')
        for req in row['requirement_ids']:
            found = next((x for x in d['requirements'] if x['id'] == req), None)
            if found and row['id'] not in found['diagram_ids']:
                issue('OUT-02', row['id'] + ': 要件から図への参照がない')
    for row in d['requirements']:
        for did in row['diagram_ids']:
            found = next((x for x in d['diagrams'] if x['id'] == did), None)
            if found and row['id'] not in found['requirement_ids']:
                issue('OUT-02', row['id'] + ': 図から要件への参照がない')
    return sorted(set(errors))


def environment():
    """Resolve installed tools; cached npm packages are read, never downloaded."""
    candidates = []
    explicit = os.environ.get('REQUIREMENT_MMDC')
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
        raise ValueError('STEP-04 既存のmermaid-cliがない。REQUIREMENT_MMDCへmmdcまたはcli.jsのパスを指定する')
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
    browser = os.environ.get('REQUIREMENT_BROWSER')
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
figure{margin:20px 0 28px;padding:20px;background:#f7f9fc;border:1px solid var(--line);border-radius:8px}.diagram-image{display:block;width:100%;height:auto;object-fit:contain;background:white}figcaption{margin-top:16px}figcaption p{margin-bottom:8px}.refs{font-size:14px;color:var(--muted)}.refs a{margin-right:12px}.zoom{overflow:auto;max-height:75vh}.zoom img{max-width:none;display:block}.downloads{font-size:14px;display:flex;flex-wrap:wrap;gap:16px}
details{margin:12px 0}summary{cursor:pointer;color:var(--accent);font-size:15px}pre{white-space:pre-wrap;overflow-wrap:anywhere;font-size:13px;line-height:1.6;padding:16px;background:#edf2f7}blockquote{margin:12px 0;padding-left:16px;border-left:3px solid var(--line);max-width:44em}dl{margin:0}dt{font-weight:700}dd{margin:0 0 16px}.scope-columns{display:grid;grid-template-columns:1fr 1fr;gap:24px}.skip{display:block;padding:8px 20px}footer{font-size:14px;color:var(--muted);padding:8px 0 32px}
@media(max-width:700px){body{font-size:16px}header,main,nav,footer{width:min(100% - 24px,1040px)}header{padding-top:24px}section{padding:22px 18px}.toc{padding:14px 18px}.toc ol{display:block}figure{padding:12px;margin-inline:0}.scope-columns{display:block}h2{font-size:22px}}
@media print{body{background:white;font-size:11pt}header,main,nav,footer{width:100%;margin:0}header{padding:0 0 16px}section{padding:16px 0;border:0;border-radius:0;break-before:auto}.toc,.skip,.downloads,.zoom-control,.source-control{display:none}article,figure{break-inside:avoid}details.evidence-details{display:block}details.evidence-details>summary{display:none}details.evidence-details>*{display:block}a{color:inherit;text-decoration:none}}
'''


def render_html(d, directory, manifest):
    ja = d['language'] == 'ja'
    headings = HEADINGS[d['language']]
    parts = []
    link_labels = {x['id']: x['title'] for group in ('requirements', 'diagrams') for x in d[group]}
    link_labels.update({x['id']: x['label'] + ' · ' + x['location'] for x in d['sources']})

    def tr(a, b):
        return a if ja else b

    def para(value):
        return '<p>' + e(value) + '</p>'

    def bullets(values):
        return '<ul>' + ''.join('<li>' + e(x) + '</li>' for x in values) + '</ul>'

    def links(ids):
        return ''.join('<a href="#' + e(x) + '">' + e(link_labels[x]) + '</a>' for x in ids)

    def refs(ids):
        return '<p class="refs">' + tr('根拠：', 'Evidence: ') + links(ids) + '</p>'

    def status(value):
        labels = {'stated': tr('入力に記載', 'Stated in input'), 'proposal': tr('提案', 'Proposed'), 'open': tr('未決', 'Open')}
        return '<span class="status status-' + value + '">' + labels[value] + '</span>'

    def section(index, body):
        return '<section id="' + SECTIONS[index] + '"><h2>' + str(index + 1) + '. ' + headings[index] + '</h2>' + body + '</section>'

    parts.append('<!doctype html>\n<html lang="' + d['language'] + '"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="source-sha256" content="' + manifest['source_sha256'] + '"><title>' + e(d['title']) + '</title><style>' + CSS + '</style></head><body>')
    parts.append('<a class="skip" href="#overview">' + tr('本文へ移動', 'Skip to content') + '</a><header><p class="eyebrow">' + tr('要件定義書 · 確認用ドラフト', 'Requirements · Review draft') + '</p><h1>' + e(d['title']) + '</h1><p class="lead">' + e(d['summary']) + '</p><p class="muted">' + tr('読者：', 'Readers: ') + e(' / '.join(d['readers'])) + '</p></header>')
    parts.append('<nav class="toc" aria-label="' + tr('目次', 'Contents') + '"><ol>' + ''.join('<li><a href="#' + sid + '">' + title + '</a></li>' for sid, title in zip(SECTIONS, headings)) + '</ol></nav><main>')
    parts.append(section(0, '<h3>' + tr('解く課題', 'Problem') + '</h3>' + ''.join(para(x) for x in d['background']) + '<h3>' + tr('達成すること', 'Purpose') + '</h3>' + para(d['purpose'])))
    body = para(tr('後の章で使う用語と、業務に関わる人の役割をそろえる。', 'These terms and roles provide the context for the following sections.'))
    body += '<dl>' + ''.join('<dt>' + e(x['term']) + '</dt><dd>' + e(x['definition']) + refs(x['source_ids']) + '</dd>' for x in d['terms']) + '</dl>'
    for x in d['actors']:
        body += '<article id="' + x['id'] + '"><h3>' + e(x['name']) + '</h3>' + para(x['role']) + refs(x['source_ids']) + '</article>'
    parts.append(section(1, body))
    body = para(tr('目的を達成するために扱う範囲と、今回扱わない範囲を分ける。', 'The scope separates the work needed for the purpose from work excluded from this document.'))
    body += '<div class="scope-columns"><div><h3>' + tr('対象', 'In scope') + '</h3>' + bullets(d['scope']['in']) + '</div><div><h3>' + tr('対象外', 'Out of scope') + '</h3>' + bullets(d['scope']['out']) + '</div></div>'
    parts.append(section(2, body))
    body = para(tr('全体の境界、利用者ができること、業務の流れの順に確認する。図の下の要件名から、詳しい条件へ進める。', 'Read the system boundary, user capabilities and workflow in order. Requirement links beneath each diagram lead to the detailed conditions.'))
    for x, item in zip(d['diagrams'], manifest['diagrams']):
        encoded = base64.b64encode((directory / item['png']).read_bytes()).decode()
        src = 'data:image/png;base64,' + encoded
        mmd = base64.b64encode(x['mermaid'].encode()).decode()
        body += '<article id="' + x['id'] + '"><h3>' + e(x['title']) + '</h3>' + para(x['intro'])
        body += '<figure><img class="diagram-image" src="' + src + '" alt="' + e(x['alt']) + '" width="' + str(item['width']) + '" height="' + str(item['height']) + '"><figcaption>' + para(x['takeaway'])
        body += '<p class="refs">' + tr('関連要件：', 'Requirements: ') + links(x['requirement_ids']) + '</p>' + refs(x['source_ids']) + '</figcaption>'
        body += '<p class="downloads"><a download="' + e(Path(item['png']).name) + '" href="' + src + '">' + tr('PNGを保存', 'Save PNG') + '</a><a download="' + e(Path(item['mermaid']).name) + '" href="data:text/plain;charset=utf-8;base64,' + mmd + '">' + tr('Mermaid原本を保存', 'Save Mermaid source') + '</a></p>'
        body += '<details class="zoom-control"><summary>' + tr('図を原寸で見る', 'View at original size') + '</summary><div class="zoom" tabindex="0"><img src="' + src + '" alt="' + e(x['alt']) + '" width="' + str(item['width']) + '" height="' + str(item['height']) + '"></div></details>'
        body += '<details class="source-control"><summary>' + tr('図のMermaid原本を確認する', 'Inspect Mermaid source') + '</summary><pre><code>' + e(x['mermaid'].strip()) + '</code></pre></details></figure></article>'
    parts.append(section(3, body))
    body = para(tr('各要件は、必要な振る舞い、理由、受入条件の順に読む。「入力に記載」は資料の記述を示し、承認済みを意味しない。', 'Read each requirement as behavior, rationale and acceptance criteria. “Stated in input” indicates evidence, not approval.'))
    for x in d['requirements']:
        body += '<article class="req" id="' + x['id'] + '"><h3>' + e(x['title']) + '</h3>' + status(x['status']) + para(x['statement']) + '<h4>' + tr('理由', 'Rationale') + '</h4>' + para(x['reason']) + '<h4>' + tr('受入条件', 'Acceptance criteria') + '</h4>' + bullets(x['acceptance'])
        body += '<p class="refs">' + tr('関連図：', 'Diagrams: ') + links(x['diagram_ids']) + '</p>' + refs(x['source_ids']) + '</article>'
    parts.append(section(4, body))
    body = para(tr('品質の目標と確認方法を示す。入力に条件がない項目は未決とし、数値や合意を補って確定しない。', 'Quality goals and verification methods are listed here. Missing conditions remain open; no targets or approvals are invented.'))
    quality_groups = {}
    for x, label in zip(d['quality'], QUALITY_JA if ja else QUALITY):
        key = (x['status'], x['statement'], tuple(x['acceptance']), tuple(x['source_ids']))
        quality_groups.setdefault(key, []).append(label)
    for (state, statement, acceptance, sources), labels in quality_groups.items():
        body += '<article><h3>' + e(' / '.join(labels)) + '</h3>' + status(state) + para(statement) + bullets(acceptance) + refs(sources) + '</article>'
    body += '<h3>' + tr('指定された制約', 'Specified constraints') + '</h3>'
    body += ''.join(para(x['statement']) + refs(x['source_ids']) for x in d['constraints']) or para(tr('入力に構成や技術の指定はない。', 'No architectural or technology constraints are stated in the input.'))
    parts.append(section(5, body))
    body = para(tr('確認が必要な条件と、その条件が決まるまで確定できない範囲を示す。', 'These questions identify missing decisions and the work that cannot be confirmed until they are resolved.'))
    for x in d['open_questions']:
        body += '<article id="' + x['id'] + '"><h3>' + e(x['question']) + '</h3>' + para(x['consequence']) + refs(x['source_ids']) + '</article>'
    if not d['open_questions']:
        body += para(tr('この原本に未決事項は記録されていない。', 'No open questions are recorded in this source.'))
    parts.append(section(6, body))
    body = para(tr('要件と図の根拠を、資料の場所と実際の記述で確認する。図を省いた理由と、設計に引き継ぐ案もここに残す。', 'Check the evidence using source locations and excerpts. Diagram selection and design notes are recorded here.'))
    for x in d['sources']:
        body += '<article id="' + x['id'] + '"><h3>' + e(x['label']) + '</h3><p class="muted">' + e(x['location']) + '</p><blockquote>' + e(x['quote']) + '</blockquote></article>'
    body += '<details class="evidence-details"><summary>' + tr('図を選んだ理由・省いた理由', 'Diagram selection decisions') + '</summary><dl>'
    for x in d['diagram_decisions']:
        body += '<dt>' + e(NAMES[x['kind']] if ja else x['kind']) + ' · ' + tr('採用' if x['selected'] else '省略', 'Selected' if x['selected'] else 'Omitted') + '</dt><dd>' + e(x['reason']) + refs(x['source_ids']) + '</dd>'
    body += '</dl></details><h3>' + tr('設計へ引き継ぐ案', 'Design notes') + '</h3>'
    body += ''.join(para(x['statement']) + refs(x['source_ids']) for x in d['design_notes']) or para(tr('未決定の実装案は記録されていない。', 'No undecided implementation proposals are recorded.'))
    parts.append(section(7, body))
    parts.append('</main><footer>' + tr('図の関係と条件は、関連要件と根拠の記述を合わせて確認する。', 'Read diagram relationships and conditions together with the linked requirements and evidence.') + '</footer></body></html>\n')
    return '\n'.join(parts)


def build(source, out):
    d = read_json(source)
    errors = validate(d)
    if errors:
        return errors
    env = environment()
    out.mkdir(parents=True, exist_ok=True)
    old = read_json(out / 'manifest.json') if (out / 'manifest.json').is_file() else {}
    # Stage derived outputs. A failed conversion leaves the previous bundle intact.
    with tempfile.TemporaryDirectory(prefix='requirement-build-', dir=out.parent) as temporary:
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
        html_path = stage / 'requirement-document.html'
        html_path.write_text(render_html(d, stage, manifest), encoding='utf-8')
        manifest['html_sha256'] = sha(html_path)
        write_json(stage / 'manifest.json', manifest)
        expected = {x[k] for x in manifest['diagrams'] for k in ('mermaid', 'png')}
        (out / 'diagrams').mkdir(exist_ok=True)
        for name in sorted(expected | {'requirement-document.html', 'manifest.json'}):
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
    for name in ('requirement-document.html', 'manifest.json'):
        if not (out / name).is_file():
            return ['OUT-01 出力がない: ' + name]
    manifest = read_json(out / 'manifest.json')
    if set(manifest) != {'version', 'source_sha256', 'diagrams', 'html_sha256'} or manifest['version'] != 1:
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
    actual_html = (out / 'requirement-document.html').read_text(encoding='utf-8')
    for sid in SECTIONS:
        if ('<section id="' + sid + '">') not in actual_html:
            return ['OUT-02 HTMLの章がない: ' + sid]
    if '<script' in actual_html.lower() or re.search(r'(?:src|href)="https?://', actual_html):
        return ['OUT-02 HTMLに外部の依存またはスクリプトがある']
    if sha(out / 'requirement-document.html') != manifest['html_sha256'] or actual_html != render_html(d, out, manifest):
        return ['OUT-06 HTMLの本文・埋め込みPNGが原本と同期していない']
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
        print('原本・Mermaid・PNG・HTML・参照・同期: 指摘0件')
        return 0
    except (OSError, ValueError, KeyError, TypeError, struct.error, zlib.error, subprocess.SubprocessError) as error:
        message = str(error)
        print(message if re.match(r'^[A-Z]+-\d\d ', message) else 'STEP-03 ' + message)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
