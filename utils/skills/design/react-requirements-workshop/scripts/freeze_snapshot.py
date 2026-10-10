#!/usr/bin/env python3
"""Save one immutable rendered build without duplicating the React app."""
from __future__ import annotations
import argparse
import json
import os
import re
import subprocess
import tempfile
import zipfile
from pathlib import Path
from common import digest, load, snapshot_id

parser = argparse.ArgumentParser()
parser.add_argument('--workspace', required=True, type=Path)
parser.add_argument('--snapshot', required=True)
args = parser.parse_args()
root = args.workspace.resolve()
meta = root / 'discussion' / f'{args.snapshot}.json'
source = root / 'src/snapshots' / f'{args.snapshot}.tsx'
if snapshot_id(load(meta)) != args.snapshot or not source.is_file():
    raise SystemExit('snapshot source and metadata mismatch')
main = (root / 'src/main.tsx').read_text(encoding='utf-8')
if not re.search(rf"from\s+['\"]\./snapshots/{re.escape(args.snapshot)}['\"]", main) or not re.search(rf"from\s+['\"]\.\./discussion/{re.escape(args.snapshot)}\.json['\"]", main):
    raise SystemExit('main.tsx must import the selected TSX and JSON')
manifest = load(root / 'discussion/snapshot-hashes.json')
if manifest.get(args.snapshot) != {'tsx': digest(source), 'metadata': digest(meta)}:
    raise SystemExit('snapshot must pass validate_snapshot.py before freezing')
rendered = root / 'discussion/rendered'
archive = rendered / f'{args.snapshot}.zip'
record = rendered / f'{args.snapshot}.json'
if archive.exists() or record.exists():
    raise SystemExit('rendered snapshot already exists')
subprocess.run(['npm', 'run', 'build'], cwd=root, check=True)
dist = root / 'dist'
if not (dist / 'index.html').is_file():
    raise SystemExit('build did not create dist/index.html')
rendered.mkdir(parents=True, exist_ok=True)
with tempfile.NamedTemporaryFile(dir=rendered, suffix='.zip', delete=False) as handle:
    staged = Path(handle.name)
try:
    with zipfile.ZipFile(staged, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as bundle:
        for path in sorted(dist.rglob('*')):
            if path.is_file():
                bundle.write(path, path.relative_to(dist))
    data = {'snapshot_id': args.snapshot, 'archive': archive.name, 'sha256': {'archive': digest(staged), 'tsx': digest(source), 'metadata': digest(meta)}}
    with record.open('x', encoding='utf-8') as file:
        json.dump(data, file, ensure_ascii=False, indent=2)
        file.write('\n')
    os.replace(staged, archive)
except BaseException:
    staged.unlink(missing_ok=True)
    record.unlink(missing_ok=True)
    raise
print(archive)
