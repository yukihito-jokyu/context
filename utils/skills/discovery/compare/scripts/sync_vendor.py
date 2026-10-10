#!/usr/bin/env python3
"""Install dependencies through npx skills add; never mutate global skills."""
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]

def digest(directory):
    value = hashlib.sha256()
    for path in sorted(directory.rglob('*')):
        if path.is_symlink():
            raise ValueError(f'Symlink is not portable: {path}')
        if path.is_file():
            value.update(path.relative_to(directory).as_posix().encode() + b'\0')
            value.update(path.read_bytes() + b'\0')
    return value.hexdigest()

def read_json(path):
    return json.loads(path.read_text(encoding='utf-8'))

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dependency', default='archify-jp')
    parser.add_argument('--source', help='Explicit source override, including a local skill directory')
    parser.add_argument('--skill', help='Skill name for the explicit source override')
    parser.add_argument('--cli-prefix', help='Existing npm project containing the pinned skills CLI (offline use)')
    parser.add_argument('--check', action='store_true', help='Verify local contents against the lock; no network')
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--timeout', type=int, default=180)
    args = parser.parse_args()
    manifest = read_json(ROOT / 'dependencies.json')
    dep = manifest['dependencies'][args.dependency]
    target = ROOT / dep['target']
    if not target.resolve().is_relative_to((ROOT / 'vendor').resolve()) or target == ROOT / 'vendor':
        raise ValueError('Dependency target must be a directory inside vendor')
    lock_path = ROOT / 'dependencies.lock.json'
    if args.check:
        lock = read_json(lock_path)['dependencies'][args.dependency]
        if digest(target) != lock['tree_sha256']:
            raise ValueError('Vendor differs from recorded dependency; review before syncing')
        for file in dep['required_files']:
            if not (target / file).is_file():
                raise ValueError(f'Missing dependency file: {file}')
        print(json.dumps({'ok': True, 'dependency': args.dependency, 'installed_version': lock['package_version'],
                          'source_type': lock['source_type'], 'configured_source_sync_verified': lock['configured_source_sync_verified']}))
        return
    source = args.source or dep['source']
    expanded_source = Path(source).expanduser()
    if source.startswith('~') or expanded_source.exists():
        source = str(expanded_source.resolve())
    skill = args.skill or dep['skill']
    version = manifest['skills_cli_version']
    if args.cli_prefix:
        prefix = Path(args.cli_prefix).resolve()
        found = read_json(prefix / 'node_modules/skills/package.json')['version']
        if found != version:
            raise ValueError(f'Expected skills CLI {version}, found {found}')
        command = ['npx', '--offline', '--prefix', str(prefix), '--no-install', 'skills']
    else:
        command = ['npx', '--yes', f'skills@{version}']
    command += ['add', source, '--skill', skill, '--agent', 'codex', '--copy', '--yes']
    if args.dry_run:
        print(json.dumps({'argv': command, 'target': str(target), 'staged': True}, ensure_ascii=False, indent=2))
        return
    vendor = ROOT / 'vendor'
    vendor.mkdir(exist_ok=True)
    guard = vendor / '.sync.lock'
    # Exclusive directory is also supported on Windows; no third-party Python deps.
    guard.mkdir()
    backup = vendor / f'.{args.dependency}.previous'
    try:
        if backup.exists():
            raise ValueError(f'Previous interrupted sync requires review: {backup}')
        with tempfile.TemporaryDirectory(prefix='.sync-', dir=vendor) as stage_string:
            stage = Path(stage_string)
            env = dict(os.environ, DISABLE_TELEMETRY='1', npm_config_cache=str(stage / 'npm-cache'))
            print('Running: ' + ' '.join(command), flush=True)
            subprocess.run(command, cwd=stage, env=env, check=True, timeout=args.timeout)
            installed = stage / '.agents/skills' / skill
            if not installed.is_dir():
                raise ValueError('skills CLI did not create the requested skill; vendor was preserved')
            for file in dep['required_files']:
                if not (installed / file).is_file():
                    raise ValueError(f'Incomplete dependency: {file}; vendor was preserved')
            tree_hash = digest(installed)
            package_version = read_json(installed / 'package.json')['version']
            # Keep the upstream package byte-for-byte; receipt is outside the vendor tree.
            receipt = {
                'requested_source': dep['source'], 'installed_source': source,
                'source_type': 'local' if Path(source).is_dir() else 'remote',
                'skill_name': skill, 'package_version': package_version,
                'skills_cli_version': version, 'tree_sha256': tree_hash,
                'configured_source_sync_verified': source == str(Path(dep['source']).expanduser().resolve()) and skill == dep['skill'],
                'synced_at_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
                'installer_argv': command,
                'skills_lock': read_json(stage / 'skills-lock.json') if (stage / 'skills-lock.json').exists() else None
            }
            lock = read_json(lock_path) if lock_path.exists() else {'schema_version': 1, 'dependencies': {}}
            lock['dependencies'][args.dependency] = receipt
            pending_lock = stage / 'dependencies.lock.json'
            pending_lock.write_text(json.dumps(lock, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
            if target.exists():
                target.rename(backup)
            try:
                installed.rename(target)
                pending_lock.replace(lock_path)
            except BaseException:
                if target.exists():
                    shutil.rmtree(target)
                if backup.exists():
                    backup.rename(target)
                raise
            if backup.exists():
                shutil.rmtree(backup)
            print(json.dumps({'ok': True, 'version': package_version, 'target': str(target),
                              'configured_source_sync_verified': receipt['configured_source_sync_verified']}))
    finally:
        guard.rmdir()

if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError, KeyError, subprocess.SubprocessError) as error:
        print(f'Sync failed: {error}', file=sys.stderr)
        sys.exit(1)
