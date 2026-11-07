#!/usr/bin/env python3
"""採点前に、原本を変えず境界の全項目を字数内の判定窓へ写す。"""
import argparse
import hashlib
import html
import importlib.util
import json
import re
from pathlib import Path

SKILL = Path(__file__).resolve().parents[2]
CONFIG = Path(__file__).with_name('input-pages.json')
FIELDS = {'request_fields', 'request_policy', 'response_variants'}
STATES = {'state_effects', 'state_policy'}
TITLES = {'contract': '操作の契約', 'fields': '要求・応答の項目', 'states': '操作と状態'}
LIMIT = 11000
spec = importlib.util.spec_from_file_location('detailed_design', SKILL / 'scripts/design.py')
design = importlib.util.module_from_spec(spec)
spec.loader.exec_module(design)


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def visible_text(text):
    # 評価器と同じHTMLの表示文字の数え方。上限そのものは変更しない。
    text = re.sub(r'<(script|style|svg)\b.*?</\1>', ' ', text, flags=re.S)
    text = re.sub(r'</(tr|p|h[1-6]|li|div|summary|details|table|section)>|<br\s*/?>', '\n', text)
    lines = (re.sub(r'\s+', ' ', line).strip() for line in html.unescape(re.sub(r'<[^>]+>', ' ', text)).split('\n'))
    return '\n'.join(line for line in lines if line)


def source(project):
    state = json.loads((project / '.skill-runs/write-detailed-design-document/state.json').read_text())
    path = project / state['input']['output_dir'] / 'design.json'
    raw = path.read_bytes()
    return path, raw, json.loads(raw)


def split_rows(data):
    groups = {key: [] for key in TITLES}
    restored = {}
    for row in sorted(data['interfaces'], key=lambda r: r['id']):
        parts = {
            'contract': {k: v for k, v in row.items() if k not in FIELDS | STATES},
            'fields': {k: v for k, v in row.items() if k in {'id', 'name'} | FIELDS},
            'states': {k: v for k, v in row.items() if k in {'id', 'name', 'state_set_ids'} | STATES},
        }
        combined = {}
        for key, part in parts.items():
            groups[key].append(part)
            for field, value in part.items():
                if field in combined and combined[field] != value:
                    raise ValueError('窓の間で値が違う: ' + row['id'] + '.' + field)
                combined[field] = value
        if combined != row:
            raise ValueError('境界の項目を網羅していない: ' + row['id'])
        restored[row['id']] = combined
    if restored != {r['id']: r for r in data['interfaces']}:
        raise ValueError('境界の集合が元データと違う')
    return groups


def render(data, kind, rows, number):
    values = dict(data)
    values['_eval_records'] = rows
    values['applicability'] = dict(data['applicability'])
    values['applicability']['_eval_records'] = (
        'このページに割り当てる境界はない。項目がある場合は同じ分類の別ページに記載する。'
        if data['interfaces'] else data['applicability']['interfaces'])
    old = design.REVIEW_PARTS
    design.REVIEW_PARTS = {'window': (TITLES[kind] + ' / ' + str(number), ['_eval_records'])}
    try:
        return design.review_document(values)
    finally:
        design.REVIEW_PARTS = old


def window_text(body):
    # review_documentが生成した唯一のsectionだけを数える。ナビやCSSは判定対象外。
    return visible_text(body[body.index('<section id="window">'):body.index('</section>') + len('</section>')])


def paginate(data):
    result = {}
    for kind, rows in split_rows(data).items():
        pages = [[]]
        for row in rows:
            candidate = pages[-1] + [row]
            if len(window_text(render(data, kind, candidate, len(pages)))) > LIMIT:
                if not pages[-1]:
                    raise ValueError('一つの境界が上限を超える: ' + kind + '/' + row['id'])
                pages.append([row])
                if len(window_text(render(data, kind, pages[-1], len(pages)))) > LIMIT:
                    raise ValueError('一つの境界が上限を超える: ' + kind + '/' + row['id'])
            else:
                pages[-1] = candidate
        result[kind] = pages
    return result


def expected(project, config):
    path, raw, data = source(project)
    groups = paginate(data)
    files = {}
    inventory = []
    for kind, capacity in config['pages'].items():
        pages = groups[kind]
        if len(pages) > capacity:
            raise ValueError('未登録の判定ページが必要: ' + kind + ' ' + str(len(pages)))
        for i in range(capacity):
            rows = pages[i] if i < len(pages) else []
            name = 'interfaces-' + kind + '-' + str(i + 1) + '.html'
            body = render(data, kind, rows, i + 1)
            count = len(window_text(body))
            if count > config['limit']:
                raise ValueError('判定窓が字数上限を超える: ' + name)
            files[name] = body
            inventory.append({'file': name, 'characters': count, 'interface_ids': [r['id'] for r in rows], 'sha256': digest(body.encode())})
    # 同じ分類の各境界はちょうど一つのページに載せる。
    wanted = sorted(r['id'] for r in data['interfaces'])
    for kind in TITLES:
        ids = [rid for row in inventory if row['file'].startswith('interfaces-' + kind + '-') for rid in row['interface_ids']]
        if sorted(ids) != wanted:
            raise ValueError('判定ページが境界を網羅していない: ' + kind)
    manifest = {'schema_version': 1, 'source': str(path.relative_to(project)), 'source_sha256': digest(raw), 'limit': config['limit'], 'pages': inventory}
    files['manifest.json'] = json.dumps(manifest, ensure_ascii=False, indent=2) + '\n'
    if path.read_bytes() != raw:
        raise ValueError('処理中に原本が変更された')
    return files, inventory


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=['plan', 'stage', 'check'])
    parser.add_argument('--project', action='append', required=True)
    args = parser.parse_args()
    projects = [Path(p).resolve() for p in args.project]
    if args.mode == 'plan':
        counts = {k: 1 for k in TITLES}
        for project in projects:
            _, _, data = source(project)
            for kind, pages in paginate(data).items():
                counts[kind] = max(counts[kind], len(pages))
        config = {'schema_version': 1, 'limit': LIMIT, 'pages': counts}
        CONFIG.write_text(json.dumps(config, ensure_ascii=False, indent=2) + '\n')
        print(json.dumps(config, ensure_ascii=False))
        return
    config = json.loads(CONFIG.read_text())
    largest = 0
    for project in projects:
        files, inventory = expected(project, config)
        directory = project / '.skill-runs/_fence/eval-inputs'
        if args.mode == 'stage':
            directory.mkdir(parents=True, exist_ok=True)
            for old in directory.iterdir():
                if old.name not in files:
                    raise ValueError('判定用でない既存ファイルがある: ' + str(old))
            for name, body in files.items():
                (directory / name).write_text(body)
        if not directory.is_dir() or {p.name for p in directory.iterdir()} != set(files):
            raise ValueError('判定入力のファイル集合が違う')
        for name, body in files.items():
            if (directory / name).read_text() != body:
                raise ValueError('判定入力が原本と一致しない: ' + name)
        largest = max(largest, *(row['characters'] for row in inventory))
    print('判定入力: ' + str(len(projects)) + '件、全境界・全項目を網羅、原本ハッシュ一致、最大' + str(largest) + '文字')


if __name__ == '__main__':
    main()
