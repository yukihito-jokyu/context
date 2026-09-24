from __future__ import annotations
import hashlib
import json
import re
from pathlib import Path

NAME = re.compile(r'^\d{3}-[a-z0-9]+(?:-[a-z0-9]+)*$')
KEY = re.compile(r'^[a-z0-9]+(?:-[a-z0-9]+)*$')

def load(path: Path) -> dict:
    value = json.loads(path.read_text(encoding='utf-8'))
    if not isinstance(value, dict):
        raise ValueError(f'object required: {path}')
    return value

def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

def snapshot_id(data: dict) -> str:
    snapshot = data['snapshot']
    result = f"{snapshot['number']:03d}-{snapshot['slug']}"
    if not NAME.fullmatch(result):
        raise ValueError('invalid snapshot id')
    return result

def requirements(data: dict, approved: bool = False) -> str:
    requirements = data['requirements']
    groups = [('目的', 'purpose'), ('対象ユーザー', 'target_users'), ('確定した要件' if not approved else '承認済み要件', 'confirmed')]
    if not approved:
        groups += [('仮説', 'hypotheses'), ('未決事項', 'open_questions'), ('見送った案', 'deferred'), ('次に確認すること', 'next')]
    result = [f"# {data['project']['title']} {'承認済み要件' if approved else '要件'}", '']
    for title, key in groups:
        values = requirements.get(key, [])
        if not isinstance(values, list) or not all(isinstance(item, str) for item in values):
            raise ValueError(f'invalid requirements.{key}')
        result += [f'## {title}', '', *[f'- {item}' for item in values], '']
    return '\n'.join(result)
