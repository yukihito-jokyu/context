#!/usr/bin/env python3
"""Verify every archived approval against its source and stored hashes."""
from __future__ import annotations

import argparse
import re
from pathlib import Path
from common import digest, load, requirements
from feedback import validate_payload

parser = argparse.ArgumentParser()
parser.add_argument('--workspace', required=True, type=Path)
args = parser.parse_args()
root = args.workspace.resolve()
record_dir = root / 'discussion/approved'
records = sorted(record_dir.glob('approved-*.json'))
if not records:
    raise SystemExit('no approved records')
for index, path in enumerate(records, 1):
    if path.name != f'approved-{index:03d}.json':
        raise SystemExit(f'approval numbering is inconsistent: {path.name}')
    record = load(path)
    approved_id = record.get('approved_id')
    if not isinstance(approved_id, str) or not re.fullmatch(r'approved-\d{3}-\d{3}-[a-z0-9]+(?:-[a-z0-9]+)*', approved_id):
        raise SystemExit(f'invalid approved id: {path}')
    if not approved_id.startswith(f'approved-{index:03d}-'):
        raise SystemExit(f'approved id and record number differ: {path}')
    snapshot_id = record.get('snapshot_id')
    if approved_id != f'approved-{index:03d}-{snapshot_id}':
        raise SystemExit(f'approved id and snapshot differ: {path}')
    paths = {
        'tsx': record.get('source_tsx'),
        'metadata': record.get('metadata'),
        'feedback': record.get('feedback'),
        'requirements_input': record.get('requirements_input'),
        'approved_tsx': f'src/approved/{approved_id}.tsx',
    }
    expected = record.get('sha256')
    if not isinstance(expected, dict):
        raise SystemExit(f'missing hashes: {path}')
    for key, relative in paths.items():
        if not isinstance(relative, str):
            raise SystemExit(f'invalid {key} path: {path}')
        file_path = (root / relative).resolve()
        if not file_path.is_relative_to(root) or not file_path.is_file():
            raise SystemExit(f'missing or external {key} file: {relative}')
        if digest(file_path) != expected.get(key):
            raise SystemExit(f'{key} hash differs: {relative}')
    meta = load(root / paths['metadata'])
    feedback = load(root / paths['feedback'])
    validate_payload(feedback, meta, snapshot_id)
    rendered = load(root / 'discussion/rendered' / f'{snapshot_id}.json')
    archive = root / 'discussion/rendered' / f'{snapshot_id}.zip'
    if rendered.get('sha256') != {'archive': digest(archive), 'tsx': digest(root / paths['tsx']), 'metadata': digest(root / paths['metadata'])}:
        raise SystemExit(f'rendered approval source changed: {path}')
    if not all(item['approved'] is True for item in feedback['items']) or meta.get('screen_details') and feedback.get('screen_details_approved') is not True:
        raise SystemExit(f'approval conditions changed: {path}')
    if feedback.get('snapshot_id') != snapshot_id or meta.get('snapshot', {}).get('number') != int(snapshot_id[:3]):
        raise SystemExit(f'approval source mismatch: {path}')
latest = load(root / records[-1].relative_to(root))
latest_requirements = load(root / latest['requirements_input'])
expected_requirements = requirements(latest_requirements, approved=True)
actual_requirements = (record_dir / 'requirements.md').read_text(encoding='utf-8')
if actual_requirements != expected_requirements:
    raise SystemExit('approved requirements changed')
print(f'validated {len(records)} approval(s)')
