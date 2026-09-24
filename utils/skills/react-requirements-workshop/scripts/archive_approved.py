#!/usr/bin/env python3
"""Archive a fully approved TSX snapshot with source hashes."""
import argparse
import json
import os
import shutil
import tempfile
from pathlib import Path
from common import digest, load, requirements, snapshot_id
from feedback import validate_payload

parser = argparse.ArgumentParser()
parser.add_argument('--workspace', required=True, type=Path)
parser.add_argument('--snapshot', required=True)
parser.add_argument('--requirements-input', type=Path, required=True)
args = parser.parse_args()
root = args.workspace.resolve()
source = root / 'src/snapshots' / f'{args.snapshot}.tsx'
meta_path = root / 'discussion' / f'{args.snapshot}.json'
feedback_path = root / 'discussion' / f'{args.snapshot}-feedback.json'
meta, feedback = load(meta_path), load(feedback_path)
validate_payload(feedback, meta, args.snapshot)
approved_requirements = load(args.requirements_input)
requirements_path = args.requirements_input.resolve()
if not requirements_path.is_relative_to(root):
    raise SystemExit('requirements input must be inside the workspace')
if snapshot_id(meta) != args.snapshot or feedback.get('snapshot_id') != args.snapshot:
    raise SystemExit('snapshot mismatch')
expected = {point['number'] for point in meta['review_points']}
items = feedback.get('items')
if not isinstance(items, list) or not expected.issubset({item.get('number') for item in items if isinstance(item, dict)}) or any(not isinstance(item, dict) or item.get('approved') is not True for item in items):
    raise SystemExit('all review points and DOM annotations must be approved')
if len({item['number'] for item in items}) != len(items):
    raise SystemExit('duplicate feedback item')
if meta.get('screen_details') and feedback.get('screen_details_approved') is not True:
    raise SystemExit('screen details not approved')
if feedback.get('screen_detail_feedback') and feedback.get('screen_details_approved') is not True:
    raise SystemExit('screen detail feedback is not approved')
hashes = load(root / 'discussion/snapshot-hashes.json')
current = {'tsx': digest(source), 'metadata': digest(meta_path)}
if hashes.get(args.snapshot) != current:
    raise SystemExit('snapshot changed after validation')
rendered_record = root / 'discussion/rendered' / f'{args.snapshot}.json'
if not rendered_record.is_file():
    raise SystemExit('rendered snapshot must be frozen before approval')
rendered = load(rendered_record)
archive = root / 'discussion/rendered' / f'{args.snapshot}.zip'
if rendered.get('sha256') != {'archive': digest(archive), **current}:
    raise SystemExit('rendered snapshot changed')
approved_dir = root / 'src/approved'
record_dir = root / 'discussion/approved'
if record_dir.exists() and any(load(path).get('snapshot_id') == args.snapshot for path in record_dir.glob('approved-*.json')):
    raise SystemExit('snapshot already approved')
number = len(list(record_dir.glob('approved-*.json'))) + 1 if record_dir.exists() else 1
name = f'approved-{number:03d}-{args.snapshot}'
target = approved_dir / f'{name}.tsx'
record = record_dir / f'approved-{number:03d}.json'
if target.exists() or record.exists(): raise SystemExit('approval already exists')
approved_dir.mkdir(parents=True, exist_ok=True)
record_dir.mkdir(parents=True, exist_ok=True)
with tempfile.NamedTemporaryFile(dir=approved_dir, suffix='.tsx', delete=False) as file:
    staged_tsx = Path(file.name)
with tempfile.NamedTemporaryFile(dir=record_dir, suffix='.json', delete=False) as file:
    staged_record = Path(file.name)
with tempfile.NamedTemporaryFile(dir=record_dir, suffix='.md', delete=False) as file:
    staged_requirements = Path(file.name)
approved_requirements_path = record_dir / 'requirements.md'
old_requirements = approved_requirements_path.read_bytes() if approved_requirements_path.exists() else None
created_tsx = created_record = False
try:
    shutil.copyfile(source, staged_tsx)
    content = {'approved_id': name, 'snapshot_id': args.snapshot, 'source_tsx': str(source.relative_to(root)), 'metadata': str(meta_path.relative_to(root)), 'feedback': str(feedback_path.relative_to(root)), 'requirements_input': str(requirements_path.relative_to(root)), 'sha256': {**current, 'feedback': digest(feedback_path), 'requirements_input': digest(requirements_path), 'approved_tsx': digest(staged_tsx)}}
    staged_record.write_text(json.dumps(content, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    staged_requirements.write_text(requirements(approved_requirements, approved=True), encoding='utf-8')
    os.link(staged_tsx, target)
    created_tsx = True
    os.link(staged_record, record)
    created_record = True
    os.replace(staged_requirements, approved_requirements_path)
except BaseException:
    if created_record: record.unlink(missing_ok=True)
    if created_tsx: target.unlink(missing_ok=True)
    if old_requirements is None:
        approved_requirements_path.unlink(missing_ok=True)
    elif not approved_requirements_path.exists() or approved_requirements_path.read_bytes() != old_requirements:
        with tempfile.NamedTemporaryFile(dir=record_dir, delete=False) as file:
            backup = Path(file.name)
            file.write(old_requirements)
        os.replace(backup, approved_requirements_path)
    raise
finally:
    staged_tsx.unlink(missing_ok=True)
    staged_record.unlink(missing_ok=True)
    staged_requirements.unlink(missing_ok=True)
print(target)
