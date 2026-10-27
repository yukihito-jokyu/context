#!/usr/bin/env python3
"""Generate and verify a code-backed domain catalog (Python 3.9+ stdlib).

Rules: STEP-02, STEP-03, STEP-06, OUT-01, OUT-02, OUT-04, OUT-06, OUT-07.
Usage: catalog.py inspect|build|verify --state .skill-runs/generate-domain-model-from-code/state.json
Or: catalog.py inspect|build|verify --repo PATH --directory PATH [--scope PATH ...]
Exit: 0 success, 1 invalid output/dependency/render failure, 2 incorrect CLI use.
No network access or package installation. MMDC selects an existing Mermaid CLI;
PUPPETEER_EXECUTABLE_PATH selects an existing browser.
"""
import argparse
import base64
import copy
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
import zlib

GENERATOR = 'generate-domain-model-from-code'
EXCLUDE = {'.git', '.claude', '.agents', '.codex', '.skill-runs', '.venv', 'venv',
           'node_modules', 'vendor', 'dist', 'build', '__pycache__', 'coverage'}
SUFFIXES = {'.py', '.ts', '.tsx', '.js', '.jsx', '.mjs', '.go', '.rs', '.java', '.kt',
            '.cs', '.rb', '.php', '.swift', '.scala', '.sql', '.prisma', '.ex', '.exs',
            '.dart', '.cpp', '.cc', '.c', '.h', '.hpp', '.vue', '.svelte'}
TOP_KEYS = {'schema_version', 'title', 'domains', 'concepts', 'relations', 'questions', 'unread'}
RELATIONS = {'association': '-->', 'inheritance': '--|>', 'composition': '*--',
             'aggregation': 'o--', 'dependency': '..>'}
KINDS = {'entity', 'value', 'enum', 'concept'}
MULTIPLICITIES = {None, '1', '0..1', '0..*', '1..*', '*'}


class Invalid(Exception):
    def __init__(self, rule, message):
        super().__init__(rule + ' ' + message)


def need(condition, message, rule='OUT-02'):
    if not condition:
        raise Invalid(rule, message)


def json_text(value):
    return json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + '\n'


def digest(data):
    return hashlib.sha256(data).hexdigest()


def read_json(path):
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except (OSError, ValueError) as e:
        raise Invalid('OUT-02', f'{path.name}: {e}') from e


def git(repo, *args):
    try:
        result = subprocess.run(['git', '-C', str(repo), *args], text=True,
                                capture_output=True, timeout=15, check=False)
        return result.stdout.strip() if result.returncode == 0 else None
    except (OSError, subprocess.TimeoutExpired):
        return None


def relative_path(value):
    need(isinstance(value, str) and value != '' and '\\' not in value, '相対パスを指定する')
    p = Path(value)
    need(not p.is_absolute() and '..' not in p.parts, '範囲外のパスを参照している')
    return p


def source_file(repo, value):
    p = relative_path(value)
    candidate = repo / p
    need(not any((repo / Path(*p.parts[:i])).is_symlink() for i in range(1, len(p.parts)+1)),
         'symlinkのコードを参照している')
    need(candidate.is_file() and candidate.resolve().is_relative_to(repo), 'コードが存在しない')
    return candidate


def snapshot(repo, scopes):
    need(repo.is_dir(), '対象リポジトリが存在しない')
    files, excluded = {}, set()
    for scope in scopes:
        start = repo / relative_path(scope)
        need(start.exists(), f'調査範囲が存在しない: {scope}')
        need(not start.is_symlink(), 'symlinkを調査範囲に指定しない')
        def walk():
            for folder, dirs, names in os.walk(start, followlinks=False):
                here = Path(folder)
                for name in list(dirs):
                    child = here/name
                    if name in EXCLUDE or child.is_symlink():
                        excluded.add(child.relative_to(repo).as_posix())
                        dirs.remove(name)
                for name in names:
                    yield here/name
        candidates = [start] if start.is_file() else walk()
        for p in candidates:
            rel = p.relative_to(repo)
            if any(part in EXCLUDE for part in rel.parts):
                excluded.add('/'.join(rel.parts[:next(i for i, part in enumerate(rel.parts) if part in EXCLUDE)+1]))
                continue
            if any((repo / Path(*rel.parts[:i])).is_symlink() for i in range(1, len(rel.parts)+1)):
                excluded.add(rel.as_posix())
                continue
            if not p.is_file() or p.suffix.lower() not in SUFFIXES:
                continue
            try:
                raw = p.read_bytes()
                text = raw.decode('utf-8')
                need('\x00' not in text, f'バイナリのコード: {rel}')
            except (OSError, UnicodeError):
                excluded.add(rel.as_posix())
                continue
            files[rel.as_posix()] = dict(path=rel.as_posix(), sha256=digest(raw), lines=len(text.splitlines()))
    need(files, '対象コードが0件。scopeを確認する')
    status = git(repo, 'status', '--porcelain')
    remote = git(repo, 'remote', 'get-url', 'origin') or ''
    match = re.fullmatch(r'(?:https://github\.com/|git@github\.com:)([\w.-]+/[\w.-]+?)(?:\.git)?', remote)
    return dict(schema_version=1, scope=sorted(set(scopes)), commit=git(repo, 'rev-parse', 'HEAD'),
                dirty=None if status is None else bool(status),
                remote='https://github.com/' + match[1] if match else None,
                files=[files[k] for k in sorted(files)], excluded=sorted(excluded))


def text(value, label):
    need(isinstance(value, str) and value.strip() != '', label + 'が空か文字列ではない')
    need(not any(ord(c) < 32 and c not in '\n\t' for c in value), label + 'に制御文字がある')


def evidence(items, repo, inventory):
    need(isinstance(items, list) and items, '根拠がない')
    allowed = {f['path'] for f in inventory['files']}
    for e in items:
        need(isinstance(e, dict) and set(e) == {'path', 'start', 'end', 'quote'}, '根拠のキーが違う')
        need(e['path'] in allowed, '根拠が調査範囲にない')
        lines = source_file(repo, e['path']).read_text(encoding='utf-8').splitlines()
        need(type(e['start']) is int and type(e['end']) is int and 1 <= e['start'] <= e['end'] <= len(lines), '根拠の行が範囲外')
        need(e['quote'] == '\n'.join(lines[e['start']-1:e['end']]), '根拠の行と抜粋が一致しない')


def normalize(model):
    m = copy.deepcopy(model)
    if isinstance(m['questions'], list):
        m['questions'] = '\n'.join(m['questions'])
    for domain in m['domains']:
        domain['name'] = 'ルート' if domain['path'] == '.' else domain['path']
    for c in m['concepts']:
        c['name'] = c['symbol']
        c['id'] = 'C_' + digest(c['key'].encode())[:12]
    for r in m['relations']:
        r['label'] = r['member'] if r['member'] is not None else '継承'
        key = [r['source'], r['target'], r['kind'], r['label']]
        r['id'] = 'R_' + digest(json.dumps(key, ensure_ascii=False, separators=(',', ':')).encode())[:12]
    m['domains'].sort(key=lambda x: x['path'])
    m['concepts'].sort(key=lambda x: x['key'])
    m['relations'].sort(key=lambda x: x['id'])
    return m


def validate_model(m, repo, inventory, canonical=False):
    need(isinstance(m, dict), 'モデルはJSONオブジェクトである')
    need(not {'skip_validation', 'no_verify', 'ignore_errors', 'disable_checks'} & set(m), '検査の省略指定がある', 'OUT-07')
    need(set(m) == TOP_KEYS and type(m['schema_version']) is int and m['schema_version'] == 1, 'モデルのキーかschema_versionが違う')
    text(m['title'], 'title')
    for k in ['domains', 'concepts', 'relations', 'unread']:
        need(isinstance(m[k], list), k + 'は配列である')
    need(isinstance(m['questions'], (str, list)), 'questionsは文字列にする')
    need(m['domains'] and m['concepts'], '領域と概念を1件以上記録する')
    domains = set()
    for d in m['domains']:
        need(isinstance(d, dict) and set(d) == {'path', 'name', 'description'}, '領域のキーが違う')
        path = relative_path(d['path']).as_posix()
        need(path == d['path'] and path not in domains, '領域パスが重複か非正規形')
        need((repo/path).is_dir() and any(f['path'].startswith(path + '/') or path == '.' for f in inventory['files']), '領域に対象コードがない')
        domains.add(path)
        text(d['name'], '領域名'); text(d['description'], '領域の説明')
    keys, ids = set(), set()
    concept_fields = {'key', 'symbol', 'name', 'domain', 'kind', 'description', 'attributes', 'evidence'}
    for c in m['concepts']:
        need(isinstance(c, dict) and concept_fields <= set(c) <= concept_fields | {'id'}, '概念のキーが違う')
        for k in ['key', 'symbol', 'name', 'description']:
            text(c[k], k)
        need(c['key'] not in keys and c['domain'] in domains and c['kind'] in KINDS, '概念キーの重複か領域・分類の不正')
        need(c['key'] == c['evidence'][0]['path'] + '::' + c['symbol'] if isinstance(c['evidence'], list) and c['evidence'] else False, 'keyは先頭の根拠パス::symbolにする')
        keys.add(c['key'])
        evidence(c['evidence'], repo, inventory)
        need(c['domain'] == Path(c['evidence'][0]['path']).parent.as_posix(), '領域は宣言元ファイルの親ディレクトリにする')
        proof = '\n'.join(e['quote'] for e in c['evidence'])
        markers = {'entity': r'\bEntity\b|@entity\b', 'value': r'\bValueObject\b|@value_object\b', 'enum': r'\benum\b|\bEnum\b|\btype\b[^=]*=.*["\'][^\n]*\|'}
        need(c['kind'] == 'concept' or re.search(markers[c['kind']], proof), '分類を明示するコードがない。id名やfrozenだけで分類せずconceptにする')
        need(isinstance(c['attributes'], list), 'attributesは配列である')
        seen = set()
        for a in c['attributes']:
            need(isinstance(a, dict) and set(a) == {'name', 'type', 'evidence'}, '属性のキーが違う')
            text(a['name'], '属性名');text(a['type'], '属性の型')
            need(a['name'] not in seen, '属性名の重複');seen.add(a['name'])
            evidence(a['evidence'], repo, inventory)
    relation_keys = set()
    relation_fields = {'source', 'target', 'kind', 'member', 'source_multiplicity', 'target_multiplicity', 'evidence'}
    for r in m['relations']:
        need(isinstance(r, dict) and relation_fields <= set(r) <= relation_fields | {'id','label'}, '関係のキーが違う')
        need(r['source'] in keys and r['target'] in keys and r['kind'] in RELATIONS, '関係の端点か種別が不正')
        if r['kind'] == 'inheritance':
            need(r['member'] is None, '継承のmemberはnullにする')
        else:
            text(r['member'], '参照メンバー')
            need(re.fullmatch(r'[\w$!?]+', r['member']) is not None, 'memberはコード上の識別子にする')
        need(r['source_multiplicity'] in MULTIPLICITIES and r['target_multiplicity'] in MULTIPLICITIES, '多重度が不正')
        key = (r['source'], r['target'], r['kind'], r['member'])
        need(key not in relation_keys, '関係が重複している');relation_keys.add(key)
        evidence(r['evidence'], repo, inventory)
        if r['member'] is not None:
            need(any(re.search(r'(?<![\w$])'+re.escape(r['member'])+r'(?![\w$])', e['quote']) for e in r['evidence']), 'memberが関係の根拠にない')
    for q in m['questions'] if isinstance(m['questions'], list) else m['questions'].splitlines():
        text(q, '確認事項')
    paths = {f['path'] for f in inventory['files']}
    for item in m['unread']:
        need(isinstance(item, dict) and set(item) == {'path', 'reason'} and item['path'] in paths, '未読のキーかパスが不正')
        text(item['reason'], '未読の理由')
    need({c['domain'] for c in m['concepts']} == domains, '概念がない領域がある')
    if canonical:
        need(m == normalize(m), 'IDか並び順が固定規則と違う', 'OUT-04')


def label(value):
    # Mermaid labels are data, never syntax, directives, or HTML.
    return ''.join(c if (c.isalnum() or c in ' _.-/（）・') else ' ' for c in value).strip() or '名称未設定'


def diagram_specs(m):
    specs = [('overview', '全体像', None)]
    if len(m['domains']) > 1:
        specs += [('domain_' + digest(d['path'].encode())[:12], d['name'], d['path']) for d in m['domains']]
    result = []
    for id, title, domain in specs:
        keys = {c['key'] for c in m['concepts'] if domain is None or c['domain'] == domain}
        rels = [r for r in m['relations'] if r['source'] in keys or r['target'] in keys]
        keys |= {r[end] for r in rels for end in ('source', 'target')}
        concepts = [c for c in m['concepts'] if c['key'] in keys]
        by_key = {c['key']: c['id'] for c in concepts}
        lines = ['classDiagram', 'direction LR']
        for c in concepts:
            lines += [f'  class {c["id"]}["{label(c["name"])}"]', f'  class {c["id"]} {{', f'    <<{c["kind"]}>>']
            if id != 'overview' or len(m['domains']) == 1:
                lines += [f'    {label(a["type"])} {label(a["name"])}' for a in c['attributes']]
            lines += ['  }']
        for r in rels:
            a = f' "{r["source_multiplicity"]}"' if r['source_multiplicity'] else ''
            b = f' "{r["target_multiplicity"]}"' if r['target_multiplicity'] else ''
            lines += [f'  {by_key[r["source"]]}{a} {RELATIONS[r["kind"]]}{b} {by_key[r["target"]]} : {label(r["label"])}']
        result.append(dict(id=id, title=title, domain=domain, mmd='\n'.join(lines)+'\n'))
    return result


def png_size(data):
    need(data.startswith(b'\x89PNG\r\n\x1a\n'), 'PNG署名が違う', 'STEP-06')
    pos, compressed, dimensions, ended = 8, [], None, False
    while pos < len(data):
        need(pos+12 <= len(data), 'PNGチャンクが途中で終わる', 'STEP-06')
        n, kind = struct.unpack('>I4s', data[pos:pos+8]);chunk = data[pos+8:pos+8+n]
        need(pos+12+n <= len(data), 'PNGチャンク長が不正', 'STEP-06')
        crc = struct.unpack('>I', data[pos+8+n:pos+12+n])[0]
        need(zlib.crc32(kind+chunk)&0xffffffff == crc, 'PNGのCRCが不正', 'STEP-06')
        if kind == b'IHDR':
            need(dimensions is None and pos == 8 and n == 13, 'PNGのIHDRが不正', 'STEP-06')
            w, h, depth, color, comp, filt, interlace = struct.unpack('>IIBBBBB', chunk)
            need(0 < w <= 30000 and 0 < h <= 30000 and depth == 8 and color in (2, 6) and (comp, filt, interlace) == (0, 0, 0), 'PNGの画像形式が不正', 'STEP-06')
            dimensions = (w, h, 3 if color == 2 else 4)
        elif kind == b'IDAT':
            compressed.append(chunk)
        elif kind == b'IEND':
            need(n == 0 and pos+12 == len(data), 'PNGの終端が不正', 'STEP-06');ended = True
        pos += n+12
    need(dimensions and ended and compressed, 'PNGの必須チャンクがない', 'STEP-06')
    w, h, channels = dimensions
    expected = h*(w*channels+1)
    need(expected <= 160_000_000, 'PNGが検査可能なサイズを超えた。領域を分割する', 'STEP-06')
    try:
        decoder = zlib.decompressobj()
        raw = decoder.decompress(b''.join(compressed), expected+1)
        need(len(raw) == expected and decoder.eof and not decoder.unused_data, 'PNGの画像データ長が不正', 'STEP-06')
        need(all(raw[i] <= 4 for i in range(0, expected, w*channels+1)), 'PNGのフィルターが不正', 'STEP-06')
    except zlib.error as e:
        raise Invalid('STEP-06', 'PNGの圧縮データが不正') from e
    return w, h


def catalog_html(m, inventory, diagrams, directory):
    h = lambda value: html.escape(str(value), quote=True)
    b64 = lambda value: base64.b64encode(value).decode('ascii')
    options = ''.join(f'<option value="{h(d["path"])}">{h(d["name"])}</option>' for d in m['domains'])
    cards = []
    for d in diagrams:
        png = (directory/'diagrams'/f'{d["id"]}.png').read_bytes()
        data = 'data:image/png;base64,'+b64(png)
        cards.append(f'<article class="diagram" data-domain="{h(d["domain"] or "")}" data-search="{h(d["title"])}"><h2>{h(d["title"])}</h2><button class="preview" data-image="{data}" data-title="{h(d["title"])}" aria-label="{h(d["title"])}を拡大"><img src="{data}" alt="{h(d["title"])}のドメインモデル図"></button><a download="{d["id"]}.mmd" href="data:text/plain;charset=utf-8;base64,{b64(d["mmd"].encode())}">Mermaid原本を取得</a></article>')
    def proof(items):
        parts = []
        for e in items:
            title = f'{e["path"]}:{e["start"]}–{e["end"]}'
            link = h(title)
            if inventory.get('remote') and inventory.get('commit') and inventory.get('dirty') is False:
                encoded = ''.join(chr(b) if chr(b).isascii() and (chr(b).isalnum() or chr(b) in '/._-') else f'%{b:02X}' for b in e['path'].encode())
                url = inventory['remote']+'/blob/'+inventory['commit']+'/'+encoded+f'#L{e["start"]}-L{e["end"]}'
                link = f'<a href="{h(url)}" target="_blank" rel="noopener">{h(title)}</a>'
            parts.append(f'<details><summary>{link}</summary><pre><code>{h(e["quote"])}</code></pre></details>')
        return ''.join(parts)
    concepts = []
    for c in m['concepts']:
        attrs = ''.join(f'<li><code>{h(a["name"])}: {h(a["type"])}</code>{proof(a["evidence"])}</li>' for a in c['attributes']) or '<li>記載なし</li>'
        concepts.append(f'<article class="concept" id="{c["id"]}" data-domain="{h(c["domain"])}" data-search="{h(c["name"]+" "+c["symbol"]+" "+c["description"])}"><span class="tag">{h(c["kind"])} · {h(c["domain"])}</span><h3>{h(c["name"])}</h3><code>{h(c["symbol"])}</code><p>{h(c["description"])}</p><ul>{attrs}</ul><h4>コードの根拠</h4>{proof(c["evidence"])}</article>')
    by_key = {c['key']: c for c in m['concepts']}
    relationships = ''.join(f'<li><a href="#{by_key[r["source"]]["id"]}">{h(by_key[r["source"]]["name"])}</a> → <a href="#{by_key[r["target"]]["id"]}">{h(by_key[r["target"]]["name"])}</a>：{h(r["label"])} <small>{h(r["kind"])} / {h(r["source_multiplicity"] or "不明")} → {h(r["target_multiplicity"] or "不明")}</small>{proof(r["evidence"])}</li>' for r in m['relations']) or '<li>確認できた関係なし</li>'
    questions = ''.join(f'<li>{h(q)}</li>' for q in (m['questions'].splitlines() if isinstance(m['questions'],str) else m['questions'])) or '<li>記録された確認事項なし</li>'
    unread = ''.join(f'<li><code>{h(i["path"])}</code>：{h(i["reason"])}</li>' for i in m['unread']) or '<li>未読のコードなし</li>'
    css = '''*{box-sizing:border-box}body{margin:0;background:#f5f3ee;color:#18352f;font:16px/1.7 system-ui,sans-serif}main{max-width:1320px;margin:auto;padding:40px 28px}header{border-bottom:1px solid #ccd7d1;padding-bottom:28px}h1{font-size:clamp(28px,4vw,46px);line-height:1.25;margin:12px 0}h2{font-size:23px}h3{font-size:22px;margin:12px 0}h4{margin-bottom:8px}.eyebrow,.tag{color:#49756a;font-size:13px;letter-spacing:.04em}.meta{color:#52645d;overflow-wrap:anywhere}.filters{display:flex;flex-wrap:wrap;gap:16px;margin:28px 0;align-items:end}.filters label{display:grid;gap:6px}input,select,button{font:inherit}input,select{background:white;border:1px solid #a8bdb2;border-radius:8px;padding:10px 14px;max-width:100%}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(350px,100%),1fr));gap:22px}.diagram,.concept,.notes{background:white;border:1px solid #d4ded8;border-radius:14px;padding:24px;min-width:0}.diagram:first-child{grid-column:1/-1}.preview{display:block;width:100%;cursor:zoom-in;background:#fff;border:0;padding:12px 0}.preview img{display:block;max-width:100%;max-height:440px;width:auto;height:auto;margin:auto}a{color:#126e58;text-underline-offset:3px}pre{white-space:pre-wrap;overflow-wrap:anywhere;background:#f0f5f2;padding:12px;border-radius:8px;color:#244038;font-size:13px}code{overflow-wrap:anywhere;font-size:.88em}summary{cursor:pointer;font-size:13px}section{margin-top:36px}.notes{margin-top:24px}li{margin-bottom:10px}dialog{width:94vw;max-width:1500px;max-height:94vh;border:0;border-radius:12px;padding:20px;background:#fff}dialog::backdrop{background:#132b25cc}.zoom{overflow:auto;max-height:78vh}dialog img{display:block;max-width:none}dialog button{float:right;padding:8px 18px}.empty{padding:16px;border:1px dashed #8ba99b}[hidden]{display:none!important}footer{margin-top:32px;font-size:13px;color:#52645d}'''
    js = '''const search=document.querySelector('#search'),domain=document.querySelector('#domain');function filter(){const q=search.value.toLocaleLowerCase();let n=0;document.querySelectorAll('.concept,.diagram').forEach(e=>{const show=(!domain.value||!e.dataset.domain||domain.value===e.dataset.domain)&&(!q||(e.dataset.search||'').toLocaleLowerCase().includes(q)||e.classList.contains('diagram'));e.hidden=!show;if(show&&e.classList.contains('concept'))n++});document.querySelector('#count').textContent=n+'件の概念';document.querySelector('#empty').hidden=n>0}search.addEventListener('input',filter);domain.addEventListener('change',filter);const modal=document.querySelector('dialog');document.querySelectorAll('.preview').forEach(b=>b.addEventListener('click',()=>{modal.querySelector('img').src=b.dataset.image;modal.querySelector('img').alt=b.dataset.title;modal.querySelector('h2').textContent=b.dataset.title;modal.showModal()}));document.querySelector('#close').addEventListener('click',()=>modal.close());filter();'''
    commit = inventory['commit'] or 'コミットなし'
    status = '変更あり' if inventory['dirty'] else ('変更なし' if inventory['dirty'] is False else 'Git管理外')
    return f'<!doctype html>\n<html lang="ja"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{h(m["title"])}</title><style>{css}</style><body><main><header><div class="eyebrow">DOMAIN MODEL · CODE EVIDENCE</div><h1>{h(m["title"])}</h1><p>実装から読み取った業務上の概念と関係。図から全体を掴み、概念カードからコードの根拠を確認できます。</p><p class="meta">{len(m["concepts"])}概念 · {len(m["relations"])}関係 · {len(m["domains"])}領域<br>調査範囲：{h(", ".join(inventory["scope"]))}<br>コミット：{h(commit)}（{status}）</p></header><div class="filters"><label>概念を検索<input id="search" type="search" placeholder="名前・コード識別子"></label><label>領域<select id="domain"><option value="">すべての領域</option>{options}</select></label><span id="count"></span></div><div class="grid">{"".join(cards)}</div><section><h2>概念とコードの根拠</h2><p id="empty" class="empty" hidden>条件に一致する概念がありません。</p><div class="grid">{"".join(concepts)}</div></section><section class="notes"><h2>関係と根拠</h2><ul>{relationships}</ul></section><section class="notes"><h2>確認事項</h2><ul>{questions}</ul><h3>未読のコード</h3><ul>{unread}</ul><details><summary>走査時の除外対象</summary><pre>{h(chr(10).join(inventory["excluded"]) or "なし")}</pre></details></section><footer>分類と関係の意味はコードの読解に基づく整理です。抜粋の一致と画像の構造を機械検査し、意味の正しさは別途レビューします。</footer></main><dialog aria-label="図の拡大"><button id="close">閉じる</button><h2></h2><div class="zoom"><img alt=""></div></dialog><script>{js}</script></body></html>\n'


def render_png(mmd, png, work):
    cli = os.environ.get('MMDC') or shutil.which('mmdc')
    need(cli and Path(cli).is_file(), '既存のMermaid CLIをMMDCで指定する。PNGは未生成', 'STEP-06')
    config = work/'mermaid-config.json'
    config.write_text(json_text(dict(theme='neutral', securityLevel='strict', fontFamily='sans-serif', deterministicIds=True, deterministicIDSeed='domain-model')))
    command = [cli, '-i', str(mmd), '-o', str(png), '-c', str(config), '-b', 'white', '-s', '2']
    browser = os.environ.get('PUPPETEER_EXECUTABLE_PATH')
    browser_config = work/'puppeteer.json'
    # Use a fresh profile in the build workspace; keep user profiles untouched.
    cfg = dict(userDataDir=str(work/'browser-profile'))
    if browser:
        cfg['executablePath'] = browser
    browser_config.write_text(json_text(cfg));command += ['-p', str(browser_config)]
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=90, check=False)
        need(result.returncode == 0 and png.is_file(), 'Mermaid変換失敗: '+result.stderr[-1200:], 'STEP-06')
        png_size(png.read_bytes())
    except (OSError, subprocess.TimeoutExpired) as e:
        raise Invalid('STEP-06', 'Mermaid実行失敗: '+str(e)) from e


def verify(directory, repo):
    need(directory.is_dir(), '出力ディレクトリがない', 'OUT-01')
    for name in ['model.json', 'inventory.json', 'manifest.json']:
        need((directory/name).is_file(), name+'がない', 'OUT-01')
    m, inv, manifest = [read_json(directory/name) for name in ['model.json', 'inventory.json', 'manifest.json']]
    validate_model(m, repo, inv, canonical=True)
    need(snapshot(repo, inv['scope']) == inv, 'コード・Git状態・調査範囲が走査時から変わった', 'OUT-06')
    specs = diagram_specs(m)
    need(isinstance(manifest, dict) and manifest.get('generator') == GENERATOR and manifest.get('diagrams') == [{k:d[k] for k in ('id','title','domain')} for d in specs], '図の集合がモデルと違う', 'STEP-02')
    expected = {'model.json','inventory.json','manifest.json','index.html'} | {f'diagrams/{d["id"]}.{ext}' for d in specs for ext in ('mmd','png')}
    actual = {p.relative_to(directory).as_posix() for p in directory.rglob('*') if p.is_file()}
    need(actual == expected and not any(p.is_symlink() for p in directory.rglob('*')), '出力のファイル集合が違う', 'OUT-01')
    for d in specs:
        need((directory/'diagrams'/f'{d["id"]}.mmd').read_text() == d['mmd'], 'Mermaidがモデルと違う', 'STEP-03')
        png_size((directory/'diagrams'/f'{d["id"]}.png').read_bytes())
    need((directory/'index.html').read_text() == catalog_html(m, inv, specs, directory), 'HTMLがモデルとPNGからの生成結果と違う', 'STEP-03')
    hashes = {name:digest((directory/name).read_bytes()) for name in sorted(expected-{'manifest.json'})}
    need(manifest.get('files') == hashes, 'manifestのハッシュが一致しない', 'OUT-06')
    return dict(concepts=len(m['concepts']), relations=len(m['relations']), diagrams=len(specs), checks='passed')


def build(directory, repo, replace):
    need(directory.is_dir(), 'inspectで出力を準備してからmodel.jsonを書く', 'OUT-01')
    existing = directory/'manifest.json'
    need(not existing.exists() or (replace and read_json(existing).get('generator') == GENERATOR), '同名の生成結果が存在する。別名にするか同じ実行内の修正で--replaceを指定する', 'OUT-01')
    if existing.exists():
        declared = read_json(existing).get('files')
        need(isinstance(declared, dict), '既存のmanifestのファイル一覧が不正', 'OUT-01')
        actual = {p.relative_to(directory).as_posix() for p in directory.rglob('*') if p.is_file()}
        need(actual == set(declared) | {'manifest.json'} and not any(p.is_symlink() for p in directory.rglob('*')), '生成元が管理していないファイルがある。既存の出力を保持する', 'OUT-01')
    allowed = {'model.json','inventory.json'}
    if not existing.exists():
        need({p.name for p in directory.iterdir()} <= allowed, '既存のファイルを保持して別の出力を選ぶ', 'OUT-01')
    m, inv = read_json(directory/'model.json'), read_json(directory/'inventory.json')
    validate_model(m, repo, inv)
    need(snapshot(repo, inv['scope']) == inv, '調査したコードが変わった。inspectからやり直す', 'OUT-06')
    m = normalize(m)
    staging = directory.parent/('.'+directory.name+'.building')
    backup = directory.parent/('.'+directory.name+'.previous')
    need(not staging.exists() and not backup.exists(), '前の一時出力が残っている。内容を確認して別名にする', 'OUT-01')
    staging.mkdir();(staging/'diagrams').mkdir()
    try:
        (staging/'model.json').write_text(json_text(m));(staging/'inventory.json').write_text(json_text(inv))
        specs = diagram_specs(m)
        for d in specs:
            mmd = staging/'diagrams'/f'{d["id"]}.mmd';png = mmd.with_suffix('.png')
            mmd.write_text(d['mmd']);render_png(mmd,png,staging)
        # Browser and renderer configuration are working files, never catalog outputs.
        for p in ['mermaid-config.json','puppeteer.json']:
            (staging/p).unlink(missing_ok=True)
        shutil.rmtree(staging/'browser-profile', ignore_errors=True)
        (staging/'index.html').write_text(catalog_html(m, inv, specs, staging))
        files = {p.relative_to(staging).as_posix():digest(p.read_bytes()) for p in sorted(staging.rglob('*')) if p.is_file()}
        manifest = dict(generator=GENERATOR, diagrams=[{k:d[k] for k in ('id','title','domain')} for d in specs], files=files)
        (staging/'manifest.json').write_text(json_text(manifest))
        result = verify(staging, repo)
        directory.rename(backup)
        try:
            staging.rename(directory)
        except OSError:
            backup.rename(directory)
            raise
        shutil.rmtree(backup)
        return result
    finally:
        if staging.exists():
            shutil.rmtree(staging)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('action', choices=['inspect','build','verify'])
    p.add_argument('--state', type=Path)
    p.add_argument('--repo', type=Path, default=Path('.'))
    p.add_argument('--directory', type=Path)
    p.add_argument('--scope', nargs='+', default=['.'])
    p.add_argument('--replace', action='store_true')
    p.add_argument('--only-rule', help='契約内の個別検査に使うルールID')
    a = p.parse_args()
    try:
        if a.state:
            state = read_json(a.state)
            inputs = state['input']
            # run.py records normalized inputs as {value, source} entries.
            inputs = {k:(v.get('value') if isinstance(v,dict) and 'value' in v else v) for k,v in inputs.items()}
            project = a.state.resolve().parents[2]
            a.repo = project/inputs['repo']
            a.scope = inputs['scope']
            a.directory = a.state.parent/'out'/inputs['name']
        if a.directory is None:
            p.error('--state または --directory を指定する')
        repo, directory = a.repo.resolve(), a.directory.resolve()
        need(not a.directory.is_symlink(), '出力にsymlinkを使わない', 'OUT-01')
        if a.action == 'inspect':
            need(not directory.exists(), '同名の出力が存在する。別のnameを指定する', 'OUT-01')
            inv = snapshot(repo, a.scope)
            directory.mkdir(parents=True)
            (directory/'inventory.json').write_text(json_text(inv))
            result = dict(files=inv['files'], excluded=inv['excluded'], commit=inv['commit'], dirty=inv['dirty'])
        elif a.action == 'build':
            result = build(directory,repo,a.replace)
        else:
            result = verify(directory,repo)
        print(json.dumps(result,ensure_ascii=False,sort_keys=True))
        return 0
    except Invalid as e:
        if a.only_rule and not str(e).startswith(a.only_rule+' '):
            return 0
        print(str(e));return 1
    except (OSError, ValueError, KeyError, TypeError, IndexError) as e:
        print('OUT-02 入力か出力を読み取れない: '+str(e));return 1


if __name__ == '__main__':
    sys.exit(main())
