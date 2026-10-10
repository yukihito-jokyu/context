#!/usr/bin/env python3
"""Check metadata, target attributes and immutable snapshot history."""
import argparse
import re
from pathlib import Path
from common import KEY, digest, load, requirements, snapshot_id

parser = argparse.ArgumentParser()
parser.add_argument('--workspace', required=True, type=Path)
parser.add_argument('--snapshot', required=True)
args = parser.parse_args()
root = args.workspace.resolve()
if not re.fullmatch(r'\d{3}-[a-z0-9]+(?:-[a-z0-9]+)*', args.snapshot):
    raise SystemExit('invalid snapshot name')
source = root / 'src/snapshots' / f'{args.snapshot}.tsx'
meta = root / 'discussion' / f'{args.snapshot}.json'
data = load(meta)
if snapshot_id(data) != args.snapshot:
    raise SystemExit('snapshot id mismatch')
code = source.read_text(encoding='utf-8')
if not re.search(r'export\s+default\s+', code):
    raise SystemExit('snapshot requires a default export')
for field, attribute in [('review_points', 'data-review-target'), ('screen_details', 'data-screen-detail-target')]:
    values = data.get(field, [])
    if not isinstance(values, list):
        raise SystemExit(f'{field} must be a list')
    keys = []
    numbers = []
    for item in values:
        if not isinstance(item, dict) or type(item.get('number')) is not int or item['number'] < 1:
            raise SystemExit(f'invalid {field} item or number')
        key = item.get('target_key')
        if not isinstance(key, str) or not KEY.fullmatch(key):
            raise SystemExit(f'invalid {field} target_key')
        keys.append(key)
        numbers.append(item.get('number'))
        if not re.search(rf'{attribute}\s*=\s*[\'\"]{re.escape(key)}[\'\"]', code):
            raise SystemExit(f'missing {attribute}={key}')
        if field == 'review_points':
            status = item.get('status', 'pending')
            history = item.get('approval_history', [])
            if status not in ('pending', 'approved', 'reopened') or not isinstance(history, list):
                raise SystemExit('invalid review point status or history')
            if status in ('approved', 'reopened') and not history:
                raise SystemExit('approved or reopened point requires approval history')
            if history and status not in ('approved', 'reopened'):
                raise SystemExit('points with approval history must be approved or reopened')
            if not all(isinstance(item.get(name), str) and item[name].strip() for name in ('title', 'description')):
                raise SystemExit('review point title and description are required')
            if not all(isinstance(entry, dict) and isinstance(entry.get('approved_in_snapshot'), str) and isinstance(entry.get('title'), str) for entry in history):
                raise SystemExit('invalid approval history entry')
            for entry in history:
                prior_id = entry['approved_in_snapshot']
                if not re.fullmatch(r'\d{3}-[a-z0-9]+(?:-[a-z0-9]+)*', prior_id) or prior_id == args.snapshot:
                    raise SystemExit('invalid approval history source')
                prior_path = root / 'discussion' / f'{prior_id}.json'
                if not prior_path.is_file():
                    raise SystemExit('approval history source is missing')
                prior_points = load(prior_path).get('review_points', [])
                if not any(prior.get('number') == item['number'] and prior.get('title') == entry['title'] for prior in prior_points):
                    raise SystemExit('approval history does not match the prior point')
        else:
            if not isinstance(item.get('key'), str) or not KEY.fullmatch(item['key']):
                raise SystemExit('invalid screen detail key')
            if item.get('behavior') not in ('screen_transition', 'backend_request', 'local_state_change', 'external_navigation', 'display_only'):
                raise SystemExit('invalid screen detail behavior')
            for name in ('region', 'name', 'type', 'description', 'capability', 'trigger', 'result', 'failure'):
                if not isinstance(item.get(name), str) or not item[name].strip():
                    raise SystemExit(f'missing screen detail {name}')
    if len(keys) != len(set(keys)) or len(numbers) != len(set(numbers)):
        raise SystemExit(f'duplicate {field} key or number')
    if field == 'screen_details' and sorted(numbers) != list(range(1, len(numbers) + 1)):
        raise SystemExit('screen detail numbers must be consecutive')
    if field == 'screen_details' and len({item['key'] for item in values}) != len(values):
        raise SystemExit('duplicate screen detail key')
    found = re.findall(rf'{attribute}\s*=\s*[\'\"]([^\'\"]+)', code)
    if sorted(found) != sorted(keys):
        raise SystemExit(f'{attribute} and metadata differ')
annotations = data.get('fixed_annotations')
if annotations is not None:
    if not isinstance(annotations, list):
        raise SystemExit('fixed_annotations must be an array')
    used = set()
    point_numbers = {item['number'] for item in data['review_points']}
    for annotation in annotations:
        if not isinstance(annotation, dict) or type(annotation.get('number')) is not int or annotation['number'] in used or annotation['number'] not in point_numbers:
            raise SystemExit('invalid fixed annotation number')
        used.add(annotation['number'])
        geometry = ('x_percent', 'y_percent', 'width_percent', 'height_percent')
        has_key = 'target_key' in annotation
        has_geometry = all(name in annotation for name in geometry)
        if has_key == has_geometry or (any(name in annotation for name in geometry) and not has_geometry):
            raise SystemExit('fixed annotation needs one target form')
        if has_key:
            key = annotation['target_key']
            if not isinstance(key, str) or not KEY.fullmatch(key) or key != next(point['target_key'] for point in data['review_points'] if point['number'] == annotation['number']):
                raise SystemExit('fixed annotation target mismatch')
            padding = annotation.get('padding_px', 8)
            if type(padding) not in (int, float) or not 0 <= padding <= 64:
                raise SystemExit('invalid annotation padding')
        else:
            if 'padding_px' in annotation or any(type(annotation[name]) not in (int, float) or not 0 <= annotation[name] <= 100 for name in geometry):
                raise SystemExit('invalid annotation geometry')
            if annotation['x_percent'] + annotation['width_percent'] > 100 or annotation['y_percent'] + annotation['height_percent'] > 100:
                raise SystemExit('annotation exceeds canvas')
requirements(data)
manifest_path = root / 'discussion/snapshot-hashes.json'
manifest = load(manifest_path) if manifest_path.exists() else {}
for recorded_id, recorded_hashes in manifest.items():
    if not re.fullmatch(r'\d{3}-[a-z0-9]+(?:-[a-z0-9]+)*', recorded_id):
        raise SystemExit('invalid historical snapshot id')
    recorded_source = root / 'src/snapshots' / f'{recorded_id}.tsx'
    recorded_meta = root / 'discussion' / f'{recorded_id}.json'
    if not recorded_source.is_file() or not recorded_meta.is_file():
        raise SystemExit(f'historical snapshot missing: {recorded_id}')
    if recorded_hashes != {'tsx': digest(recorded_source), 'metadata': digest(recorded_meta)} and (recorded_id != args.snapshot or (root / 'discussion/rendered' / f'{recorded_id}.json').exists()):
        raise SystemExit(f'historical snapshot changed: {recorded_id}')
    rendered_record = root / 'discussion/rendered' / f'{recorded_id}.json'
    if rendered_record.exists():
        rendered = load(rendered_record)
        archive = root / 'discussion/rendered' / f'{recorded_id}.zip'
        if rendered.get('snapshot_id') != recorded_id or rendered.get('archive') != archive.name or not archive.is_file():
            raise SystemExit(f'rendered snapshot missing: {recorded_id}')
        if rendered.get('sha256') != {'archive': digest(archive), 'tsx': digest(recorded_source), 'metadata': digest(recorded_meta)}:
            raise SystemExit(f'rendered snapshot changed: {recorded_id}')
entry = {'tsx': digest(source), 'metadata': digest(meta)}
if args.snapshot in manifest and manifest[args.snapshot] != entry and (root / 'discussion/rendered' / f'{args.snapshot}.json').exists():
    raise SystemExit('historical snapshot changed')
if args.snapshot not in manifest and manifest:
    previous = max(int(name[:3]) for name in manifest)
    if data['snapshot']['number'] != previous + 1:
        raise SystemExit('new snapshot number must follow the previous snapshot')
manifest[args.snapshot] = entry
manifest_path.write_text(__import__('json').dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
(root / 'discussion/requirements.md').write_text(requirements(data), encoding='utf-8')
print(f'validated {args.snapshot}')
