"""台帳から項目直下の図と参照先の抜粋を作り、既存Mermaid CLIでPNGにする。"""
import hashlib
import base64
from concurrent.futures import ThreadPoolExecutor
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


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def records(data):
    return {row['id']: row for value in data.values() if isinstance(value, list)
            for row in value if isinstance(row, dict) and 'id' in row}


def excerpt(row):
    """名前だけを要約にせず、参照先の実条件を残す。"""
    keys = ['quote', 'text', 'statement', 'purpose', 'responsibility', 'given', 'when', 'then',
            'guard', 'write', 'notify', 'input', 'response', 'errors', 'winner', 'exclusion',
            'restart', 'visible_result', 'question', 'acceptance', 'before', 'after',
            'save_result', 'display', 'update_unit', 'deletion', 'meaning', 'explains']
    values = [str(row[k]) for k in keys if row.get(k)]
    if 'request_fields' in row:
        values += ['入力: ' + ' / '.join(f['path'] + ': ' + f['type'] + (' 必須' if f['required'] else ' 任意') + (' NULL可' if f['nullable'] else ' NULL不可') + ', ' + f['constraint'] for f in row['request_fields'])]
        values += ['応答: ' + ' / '.join(v['name'] + ': ' + v['description'] + ' (' + '; '.join(f['path'] + ': ' + f['type'] + (' 必須' if f['required'] else ' 任意') + (' NULL可' if f['nullable'] else ' NULL不可') + ', ' + f['constraint'] for f in v['fields']) + ')' for v in row['response_variants'])]
        values += ['最大サイズ: ' + row['max_size']]
    if 'adoption' in row:
        values += ['採用: ' + row['adoption']]
    if isinstance(row.get('verification'), str):
        values += ['検証: ' + row['verification']]
    if row.get('values'):
        values += [v['name'] + ': ' + v['meaning'] for v in row['values']]
    return ' / '.join(values) or row.get('name', row.get('entity', row['id']))


def short(value, maximum=96):
    text = re.sub(r'\s+', ' ', str(value)).strip()
    # 図は見通しを示す。省いた部分は直下の表・引用に全文を残す。
    return text if len(text) <= maximum else text[:maximum] + '…'


def label(value):
    # Mermaidのラベル内で構文やHTMLを注入させない。
    return html.escape(short(value), quote=True).replace('`', '&#96;').replace('\n', ' ')


def flow(nodes, edges=None):
    lines = ['flowchart TD']
    lines += ['  n' + str(i) + '["' + label(v) + '"]' for i, v in enumerate(nodes)]
    lines += ['  n' + str(a) + ' --> n' + str(b) for a, b in (edges or [])]
    return '\n'.join(lines)


def plan(data, groups, labels=None):
    """各台帳項目に図を置く。矢印の意味は種類別に固定し、未定義の動作を補わない。"""
    result = []
    labels = labels or {}
    all_rows = records(data)
    def add(owner, filename, title, source, explains):
        result.append(dict(id='local-' + owner, owner=owner, file=filename, name=title,
                           mermaid=source + '\n', explains=explains))
    add('overview', 'README.md', '読む順序', flow(
        ['共通仕様', '機能', '境界', '物理データ・画面', '障害と回復', '確認条件・根拠'],
        [(i, i+1) for i in range(5)]), '矢印は文書を読む順序を示す。実行順序ではない。')
    for group, (_, filename) in groups.items():
        if group == 'diagrams':
            continue
        for row in data[group]:
            rid = row['id']
            name = row.get('name', row.get('entity', row.get('question', rid)))
            source, explains = None, '矢印は項目と条件の対応を示す。実行順序ではない。厳密な全文は同じ項目の表にある。'
            if group == 'features':
                nodes = [rid + ' 開始: ' + ' / '.join(row['preconditions'])] + row['steps'] + ['結果: ' + row['result']]
                source = flow(nodes, [(i, i+1) for i in range(len(nodes)-1)])
                explains = '矢印はこの機能の処理順を示す。異常・競合の条件は直下の本文で確認する。'
            elif group == 'interfaces':
                lines = ['sequenceDiagram', '  participant A as ' + label(row['caller']), '  participant B as ' + label(row['callee']),
                         '  A->>B: ' + label(rid + ' ' + row['input'])]
                for i, variant in enumerate(row['response_variants']):
                    lines += [('  alt ' if i == 0 else '  else ') + label(variant['name'] + ' ' + variant['description']),
                              '    B-->>A: ' + label(variant['name'])]
                if row['response_variants']:
                    lines += ['  end']
                source = '\n'.join(lines)
                explains = '要求と応答候補を示す。altは応答の選択肢であり、全候補を順次返す意味ではない。入力検査・エラー・状態条件は同じ項目の表にある。'
            elif group in ['state_sets', 'transitions']:
                sid = rid if group == 'state_sets' else row['state_set_id']
                transitions = [r for r in data['transitions'] if r['state_set_id'] == sid and (group == 'state_sets' or r['id'] == rid)]
                states = all_rows.get(sid, {}).get('values', [])
                if group == 'transitions':
                    states = [v for v in states if v['name'] in {row['from'], row['to']}]
                names = {v['name']: rid + '_s' + str(i) for i, v in enumerate(states)}
                lines = ['stateDiagram-v2', '  direction LR'] + ['  state "' + label(v['name']) + '" as ' + names[v['name']] for v in states]
                for t in transitions:
                    lines.append('  ' + names[t['from']] + ' --> ' + names[t['to']] + ': ' + t['id'])
                source = '\n'.join(lines)
                explains = '共通定義の状態名と実在する遷移だけを示す。競合の勝敗、保存の原子性、等号条件は同じ項目の表にある。'
            elif group == 'tables':
                lines = ['erDiagram', '  ' + rid + ' {']
                for i, column in enumerate(row['columns']):
                    # 型と列名は引用コメントに保存し、ER構文の識別子は固定する。
                    field = column['name'] if re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*',column['name']) else 'c'+str(i)
                    kind = re.match(r'[A-Za-z_][A-Za-z0-9_]*',column['type'])
                    kind = kind.group() if kind else 'field'
                    description = label(column['name'] + ': ' + column['type'])
                    lines.append('    ' + kind + ' ' + field + ' "' + description + '"')
                lines += ['  }']
                source = '\n'.join(lines)
                explains = '表の物理列を示す。列名・型の全文、キー構成、参照先、更新・削除単位は直下の表を正本とする。'
            else:
                fields = {
                    'modules': ['responsibility', 'depends_on'], 'decisions': ['statement', 'kind', 'verification', 'adoption'],
                    'requirements': ['text', 'feature_ids', 'check_ids', 'issue_ids'],
                    'concurrency': ['protected_data', 'exclusion', 'order', 'acquire', 'winner', 'release'],
                    'recovery': ['cut', 'committed', 'remaining', 'restart', 'retry', 'visible_result'],
                    'screens': ['fields', 'validation', 'actions', 'save_result', 'focus', 'updates'],
                    'checks': ['given', 'when', 'then'], 'sources': ['path', 'kind', 'quote'],
                    'issues': ['question', 'verification', 'acceptance', 'affected_ids', 'independent_work'],
                    'changes': ['before', 'after', 'reason', 'impact', 'adoption'],
                }[group]
                def text(value):
                    if isinstance(value, list):
                        return ' / '.join(text(v) for v in value) or 'なし'
                    if isinstance(value, dict):
                        return ' / '.join(str(k) + ': ' + text(v) for k, v in value.items())
                    if isinstance(value, str) and value in all_rows:
                        return value + ' ' + short(excerpt(all_rows[value]))
                    return str(value)
                captions = dict(labels)
                captions.update({'quote':'引用','path':'資料のパス'} if group == 'sources' else {})
                nodes = [rid + (' ' + name if name != rid else '')] + [(captions.get(key,key) if data['language']=='ja' else key) + ': ' + text(row[key]) for key in fields if key in row]
                edges = [(0, i) for i in range(1, len(nodes))]
                if group in ['checks', 'recovery']:
                    edges = [(i, i+1) for i in range(len(nodes)-1)]
                    explains = '矢印は確認の順序または停止後の回復判断を示す。省略した全文は同じ項目の表にある。'
                source = flow(nodes, edges)
            add(rid, filename, rid + ' ' + name, source, explains)
            if group in ['state_sets', 'transitions']:
                result[-1]['legend'] = [t['id'] + ': ' + t['from'] + ' → ' + t['to'] + ' / ' + t['event'] + ' / ' + t['guard'] for t in transitions]
    # 手書きの横断図は、厳密な条件の各項目の直後に置く。
    destinations = {row['id']: fn for group, (_, fn) in groups.items() for row in data[group] if group != 'diagrams'}
    for row in data['diagrams']:
        for owner in row['condition_ids']:
            if owner in destinations:
                add(row['id'] + '-' + owner, destinations[owner], row['name'], row['mermaid'], row['explains'])
                result[-1]['owner'] = owner
                result[-1]['author_id'] = row['id']
                result[-1]['legend'] = [rid + ' — ' + excerpt(all_rows[rid]) for rid in row['condition_ids']]
                break
    return result


def environment():
    candidates = [Path(os.environ['DETAILED_DESIGN_MMDC'])] if os.environ.get('DETAILED_DESIGN_MMDC') else []
    if shutil.which('mmdc'):
        candidates.append(Path(shutil.which('mmdc')))
    candidates += [p / 'node_modules/.bin/mmdc' for p in [Path.cwd(), *Path.cwd().parents]]
    candidates += sorted((Path.home() / '.npm/_npx').glob('*/node_modules/@mermaid-js/mermaid-cli/src/cli.js'))
    cli = next((p.resolve() for p in candidates if p.is_file()), None)
    if not cli:
        raise ValueError('OUT-16 Mermaid CLIがない。DETAILED_DESIGN_MMDCで既存のmmdcまたはcli.jsを指定する。')
    command = [shutil.which('node'), str(cli)] if cli.suffix == '.js' else [str(cli)]
    version = subprocess.run(command + ['--version'], capture_output=True, text=True, timeout=15)
    if version.returncode:
        raise ValueError('OUT-16 Mermaid CLIを起動できない')
    browser = os.environ.get('DETAILED_DESIGN_BROWSER')
    default = Path('/Applications/Google Chrome.app/Contents/MacOS/Google Chrome')
    if not browser and default.is_file():
        browser = str(default)
    return command, version.stdout.strip(), browser


def png_info(raw):
    if not raw.startswith(b'\x89PNG\r\n\x1a\n'):
        raise ValueError('OUT-16 PNG署名が違う')
    pos, size, compressed, end = 8, None, b'', False
    while pos + 12 <= len(raw):
        length = struct.unpack('>I', raw[pos:pos+4])[0]
        kind, payload = raw[pos+4:pos+8], raw[pos+8:pos+8+length]
        stop = pos + 12 + length
        if stop > len(raw) or zlib.crc32(kind + payload) & 0xffffffff != struct.unpack('>I', raw[stop-4:stop])[0]:
            raise ValueError('OUT-16 PNGのCRCが違う')
        if kind == b'IHDR':
            size = struct.unpack('>II', payload[:8])
        if kind == b'IDAT':
            compressed += payload
        if kind == b'IEND':
            end = stop == len(raw)
        pos = stop
    if not size or min(size) < 1 or not end or not zlib.decompress(compressed):
        raise ValueError('OUT-16 PNGの画像データがない')
    return size


CONFIG = {'theme': 'neutral', 'securityLevel': 'strict', 'fontFamily': 'sans-serif', 'flowchart': {'htmlLabels': False, 'wrappingWidth': 280}}


def render_pngs(plans, directory):
    command, version, browser = environment()
    old_path = directory / 'diagrams/manifest.json'
    old = json.loads(old_path.read_text()) if old_path.is_file() else {'diagrams': []}
    prior = {r['id']: r for r in old.get('diagrams', [])}
    if (directory/'diagrams').exists():
        known = {'manifest.json'} if old_path.is_file() else set()
        for row in old.get('diagrams', []):
            for key in ['mermaid', 'png']:
                name = Path(row[key]).name
                known.add(name)
                path = directory/'diagrams'/name
                if path.is_file() and sha(path.read_bytes()) != row[key+'_sha256']:
                    raise ValueError('OUT-06 変更済みの図を上書きしない: ' + name)
        if {p.name for p in (directory/'diagrams').iterdir()} - known:
            raise ValueError('OUT-06 手書きの図を上書き・削除しない')
    recipe = sha(json.dumps(CONFIG, sort_keys=True).encode() + b'width1600-scale1.5-isolated-v2')
    with tempfile.TemporaryDirectory(prefix='detailed-diagrams-', dir=directory.parent) as temporary:
        stage = Path(temporary)
        pending, output = [], {}
        for p in plans:
            mmd, png = 'diagrams/' + p['id'] + '.mmd', 'diagrams/' + p['id'] + '.png'
            raw = p['mermaid'].encode()
            output[mmd] = raw
            last = prior.get(p['id'], {})
            path = directory / png
            if last.get('mermaid_sha256') == sha(raw) and last.get('renderer') == version and last.get('recipe') == recipe and path.is_file() and last.get('png_sha256') == sha(path.read_bytes()):
                output[png] = path.read_bytes()
            else:
                pending.append(p)
        if pending:
            puppet = {'args': ['--disable-background-networking', '--disable-extensions', '--no-first-run', '--host-resolver-rules=MAP * ~NOTFOUND, EXCLUDE localhost']}
            if browser:
                puppet['executablePath'] = browser
            (stage/'puppet.json').write_text(json.dumps(puppet))
            (stage/'config.json').write_text(json.dumps(CONFIG))
            def draw(p):
                source, target = stage/(p['id']+'.mmd'), stage/(p['id']+'.png')
                source.write_text(p['mermaid'])
                args = command + ['-i', str(source), '-o', str(target), '-c', str(stage/'config.json'), '-p', str(stage/'puppet.json'), '-w', '1600', '-s', '1.5', '-b', 'white', '-q']
                result = subprocess.run(args, capture_output=True, text=True, timeout=90)
                if result.returncode:
                    raise ValueError('OUT-16 ' + p['id'] + ' のPNG変換に失敗: ' + (result.stderr or result.stdout)[-2000:])
                return 'diagrams/' + p['id'] + '.png', target.read_bytes()
            with ThreadPoolExecutor(max_workers=3) as pool:
                output.update(pool.map(draw, pending))
        entries = []
        for p in plans:
            mmd, png = 'diagrams/' + p['id'] + '.mmd', 'diagrams/' + p['id'] + '.png'
            width, height = png_info(output[png])
            entries.append(dict(id=p['id'], owner=p['owner'], document=p['file'], mermaid=mmd, png=png,
                                mermaid_sha256=sha(output[mmd]), png_sha256=sha(output[png]), width=width, height=height,
                                renderer=version, recipe=recipe))
        output['diagrams/manifest.json'] = (json.dumps({'version': 1, 'diagrams': entries}, ensure_ascii=False, indent=2)+'\n').encode()
        return output


def check_pngs(plans, directory):
    try:
        manifest = json.loads((directory/'diagrams/manifest.json').read_text())
        if type(manifest.get('version')) is not int or manifest['version'] != 1:
            raise ValueError('図のmanifestの版が違う')
        rows = manifest['diagrams']
        if [p['id'] for p in plans] != [r['id'] for r in rows]:
            raise ValueError('図の集合が台帳と違う')
        expected = {'manifest.json'}
        for p, row in zip(plans, rows):
            mmd, png = p['id'] + '.mmd', p['id'] + '.png'
            if row['mermaid'] != 'diagrams/' + mmd or row['png'] != 'diagrams/' + png:
                raise ValueError('図のmanifestのパスが違う: ' + p['id'])
            expected.update([mmd, png])
            source, image = (directory/'diagrams'/mmd).read_bytes(), (directory/'diagrams'/png).read_bytes()
            if source != p['mermaid'].encode() or row['mermaid_sha256'] != sha(source) or row['png_sha256'] != sha(image):
                raise ValueError('MermaidまたはPNGの内容・ハッシュが違う: ' + p['id'])
            if (row['width'], row['height']) != png_info(image) or row['owner'] != p['owner'] or row['document'] != p['file']:
                raise ValueError('図の寸法か配置先が違う: ' + p['id'])
        if {p.name for p in (directory/'diagrams').iterdir()} != expected:
            raise ValueError('図フォルダのファイル集合が違う')
        return []
    except (OSError, ValueError, KeyError, zlib.error, struct.error) as exc:
        return [('OUT-16', 'Mermaid・PNGの一致検査: ' + str(exc))]


def sheets(directory):
    """全図の一覧と原画像の対応を作る。画像の確認済みという判定は作らない。"""
    command, _, browser = environment()
    target = directory/'qa'
    old = json.loads((target/'manifest.json').read_text()) if (target/'manifest.json').is_file() else {'files': []}
    if target.exists():
        expected = {'manifest.json'}
        for row in old['files']:
            expected.add(row['file'])
            if sha((target/row['file']).read_bytes()) != row['sha256']:
                raise ValueError('OUT-06 編集済みの確認画像を上書きしない')
        if {p.name for p in target.iterdir()} != expected:
            raise ValueError('OUT-06 手書きの確認資料を上書きしない')
    rows = json.loads((directory/'diagrams/manifest.json').read_text())['diagrams']
    with tempfile.TemporaryDirectory(prefix='diagram-sheets-',dir=directory.parent) as temporary:
        stage = Path(temporary)
        config = {'args': ['--disable-background-networking','--disable-extensions','--no-first-run','--host-resolver-rules=MAP * ~NOTFOUND, EXCLUDE localhost']}
        if browser:
            config['executablePath'] = browser
        pages = []
        for i in range(0,len(rows),4):
            name = 'sheet-' + str(i//4+1).zfill(3) + '.png'
            items = [dict(id=row['id'],width=row['width'],height=row['height'],base64=base64.b64encode((directory/row['png']).read_bytes()).decode()) for row in rows[i:i+4]]
            pages.append(dict(output=str(stage/name),items=items))
        (stage/'input.json').write_text(json.dumps({'browser':config,'sheets':pages}))
        result = subprocess.run(['/bin/sh',str(Path(__file__).with_name('contact_sheet.sh')),command[-1],str(stage/'input.json')],capture_output=True,text=True,timeout=max(120,len(pages)*15))
        if result.returncode:
            raise ValueError('OUT-16 確認用一覧を生成できない。各PNGを直接開く: ' + result.stderr[-1500:])
        target.mkdir(exist_ok=True)
        inventory = []
        for i,page in enumerate(pages):
            path = Path(page['output']);raw=path.read_bytes();png_info(raw)
            (target/path.name).write_bytes(raw)
            inventory.append(dict(file=path.name,sha256=sha(raw),diagram_ids=[r['id'] for r in rows[i*4:i*4+4]]))
        for path in target.iterdir():
            if path.name not in {r['file'] for r in inventory} | {'manifest.json'}:
                path.unlink()
        (target/'manifest.json').write_text(json.dumps({'kind':'visual-review-sheets','source_sha256':sha((directory/'diagrams/manifest.json').read_bytes()),'files':inventory},ensure_ascii=False,indent=2)+'\n')
    return [str(target/r['file']) for r in inventory]
