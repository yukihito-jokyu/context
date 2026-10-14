#!/usr/bin/env python3
"""Reproduce Archify delivery/export and verify every article diagram image.

This detects accidental substitution. It is not an authentication boundary against
an agent that can change this script/vendor, or proof of semantic/visual quality.
"""
import argparse
import base64
import hashlib
from html.parser import HTMLParser
import json
import re
from pathlib import Path
import subprocess
import sys
import tempfile
from urllib.parse import unquote

SKILL = Path(__file__).resolve().parents[1]
TYPES = {'architecture', 'workflow', 'sequence', 'sequence-er', 'workflow-er',
         'dataflow', 'lifecycle', 'class', 'er'}

def sha(data):
    return hashlib.sha256(data).hexdigest()

def inside(root, value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError('missing artifact path')
    p = (root / value).resolve()
    if not p.is_relative_to(root) or not p.is_file():
        raise ValueError('missing/outside-root artifact: ' + value)
    return p

def command(args):
    result = subprocess.run(args, capture_output=True, text=True, timeout=60)
    if result.returncode:
        raise ValueError('Archify command failed: ' + (result.stderr or result.stdout)[-1500:])
    return json.loads(result.stdout)

class Images(HTMLParser):
    def __init__(self):
        super().__init__(); self.images = []; self.forbidden = []
    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'img': self.images.append(attrs)
        # Inline graphs/overlays require a separately implemented geometry contract.
        # Do not silently exempt an arbitrary graph with a self-declared attribute.
        if tag in ('svg', 'canvas', 'object', 'embed', 'iframe'):
            self.forbidden.append(tag)


def check(manifest, root, article):
    root = Path(root).resolve(); issues = []; allowed = {}; used = set(); checked = []
    rows = manifest.get('diagrams', []) if isinstance(manifest, dict) else []
    if not rows: issues.append('No Archify diagrams declared')
    deliveries = []
    for row in rows:
        deliveries.append(row)
        if not isinstance(row, dict): continue
        variants = row.get('archify_variants', [])
        if not isinstance(variants, list) or len(variants) > 16:
            issues.append(str(row.get('id')) + ': variants must be an array of at most 16 local projections')
            continue
        identifiers = set()
        for variant in variants:
            if (not isinstance(variant, dict)
                or not re.fullmatch(r'[a-z][a-z0-9-]*', str(variant.get('id', '')))
                or variant['id'] in identifiers
                or not isinstance(variant.get('reason'), str) or not variant['reason'].strip()):
                issues.append(str(row.get('id')) + ': variant requires unique id and specific reason')
                continue
            identifiers.add(variant['id'])
            # Ownership remains on the single logical diagram row. Every local
            # projection still undergoes the exact same delivery/export checks.
            deliveries.append({'id': str(row.get('id')) + '::' + variant['id'],
                'status': row.get('status'),
                'outputs': {'model': variant.get('model'), 'figure': variant.get('viewer')},
                'archify': variant})
    for row in deliveries:
        did = row.get('id') if isinstance(row, dict) else None
        try:
            if not isinstance(row, dict) or row.get('status') != 'complete':
                raise ValueError('diagram is not complete')
            spec = row.get('archify')
            if not isinstance(spec, dict) or spec.get('type') not in TYPES:
                raise ValueError('required archify type/viewer/svg/receipt evidence absent')
            model = inside(root, row.get('outputs', {}).get('model'))
            viewer = inside(root, spec.get('viewer')); svg = inside(root, spec.get('svg'))
            if viewer != inside(root, row.get('outputs', {}).get('figure')):
                raise ValueError('figure must be the delivered Archify viewer')
            receipt = json.loads(inside(root, spec.get('receipt')).read_text())
            candidate = json.loads(model.read_text())
            if candidate.get('meta', {}).get('visual_preset') != 'editorial':
                raise ValueError('editorial preset required')
            if not (receipt.get('ok') is True and receipt.get('command') == 'deliver'
                    and receipt.get('type') == spec['type']
                    and receipt.get('specification', {}).get('sha256') == sha(model.read_bytes())
                    and receipt.get('artifact', {}).get('sha256') == sha(viewer.read_bytes())):
                raise ValueError('delivery receipt/model/viewer mismatch')
            with tempfile.TemporaryDirectory(prefix='explain-archify-check-') as tmp:
                target = Path(tmp) / 'figure.html'; exported = Path(tmp) / 'figure.svg'
                actual = command(['node', str(SKILL/'vendor/archify-jp/bin/archify.mjs'),
                                  'deliver', spec['type'], str(model), str(target),
                                  '--quality', 'showcase', '--json'])
                if actual.get('ok') is not True or target.read_bytes() != viewer.read_bytes():
                    raise ValueError('viewer differs from actual vendored Archify delivery')
                command([sys.executable, str(SKILL/'scripts/export_standard_svg.py'),
                         str(target), str(exported), '--model', str(model)])
                if exported.read_bytes() != svg.read_bytes():
                    raise ValueError('SVG differs from unchanged standard serializer export')
            key = (sha(model.read_bytes()), sha(svg.read_bytes()))
            if key in allowed: raise ValueError('same artifact claimed by multiple diagrams')
            allowed[key] = did; checked.append(did)
        except (ValueError, OSError, TypeError, AttributeError, subprocess.TimeoutExpired) as exc:
            issues.append(str(did) + ': ' + str(exc))
    parsed = Images()
    try:
        parsed.feed(article)
        if parsed.forbidden: issues.append('Unverified inline/embedded graph elements: ' + ','.join(parsed.forbidden))
        for image in parsed.images:
            # Non-diagram photographs remain outside this gate, explicitly identified.
            if image.get('data-explain-image-role') == 'photo': continue
            try:
                src = image.get('src', '')
                if src.startswith('data:image/svg+xml;base64,'):
                    raw = base64.b64decode(src.split(',', 1)[1], validate=True)
                elif src.startswith('data:image/svg+xml,'):
                    raw = unquote(src.split(',', 1)[1]).encode()
                elif ':' not in src and not src.startswith('//'):
                    raw = inside(root, unquote(src)).read_bytes()
                else: raise ValueError('only verified standard SVG supported; PNG/browser export not yet implemented')
                key = (image.get('data-archify-model-sha256'), sha(raw))
                if key not in allowed: raise ValueError('image is not a reproduced Archify export')
                used.add(key)
            except (ValueError, OSError) as exc: issues.append(str(exc))
        for key in allowed.keys() - used: issues.append(str(allowed[key]) + ': verified diagram not embedded in article')
    except (ValueError, TypeError) as exc: issues.append('Article parse failed: ' + str(exc))
    return {'pass': not issues, 'checked_diagrams': checked, 'issues': issues,
            'scope': 'Actual vendored showcase delivery, byte-exact standard SVG and article image correspondence.',
            'limits': 'No agent/network authentication, semantic/readability proof, CSS-drawn graph detection or malicious same-user isolation. Browser PNG/inline overlays unsupported and blocked.'}

if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('manifest', type=Path); p.add_argument('--article', type=Path, required=True)
    a = p.parse_args()
    try:
        root = a.manifest.resolve().parent
        if not a.article.resolve().is_relative_to(root): raise ValueError('article must be inside manifest root')
        result = check(json.loads(a.manifest.read_text()), root, a.article.read_text())
    except (ValueError, OSError) as exc: result = {'pass':False,'issues':[str(exc)]}
    print(json.dumps(result, ensure_ascii=False, indent=2)); sys.exit(0 if result['pass'] else 1)
