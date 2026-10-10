#!/usr/bin/env python3
"""Copy the shared app once. Install dependencies explicitly after initialization."""
import argparse
import shutil
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument('--workspace', required=True, type=Path)
args = parser.parse_args()
source = Path(__file__).resolve().parents[1] / 'assets/app'
target = args.workspace.resolve()
if target.exists() and any(target.iterdir()):
    raise SystemExit(f'refusing to overwrite existing workspace: {target}')
shutil.copytree(source, target, dirs_exist_ok=True)
print(target)
print('Next: create src/snapshots/001-initial.tsx and discussion/001-initial.json, then npm install and select Registry items using vendor/design-system/SKILL.md')
