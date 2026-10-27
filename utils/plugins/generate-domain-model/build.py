#!/usr/bin/env python3
"""Build a local domain-model plugin; does not install or enable it."""
import argparse
import json
from pathlib import Path
import shutil


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--agent',choices=['codex','claude-code'],required=True)
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args()
    plugin=Path(__file__).resolve().parent
    definition=json.loads((plugin/'bundle.json').read_text())
    source=(plugin/definition['skill']).resolve()
    out=a.output.resolve()
    if out.exists() or out.is_relative_to(source) or out.is_relative_to(plugin):
        p.error('既存の出力と正本を保持し、別の出力先を指定してください')
    if not (source/'assets/seal.json').is_file():
        p.error('検査して封印したSkill正本が必要です')
    if any(file.is_symlink() for file in source.rglob('*')):
        p.error('Skill正本にsymlinkがあるため配布できません')
    out.mkdir(parents=True)
    manifest=out/('.codex-plugin' if a.agent=='codex' else '.claude-plugin')
    manifest.mkdir()
    shutil.copyfile(plugin/a.agent/'plugin.json',manifest/'plugin.json')
    (out/'hooks').mkdir()
    shutil.copyfile(plugin/a.agent/'hooks.json',out/'hooks/hooks.json')
    shutil.copytree(plugin/'scripts',out/'scripts',ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
    shutil.copytree(source,out/'skills/generate-domain-model',ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
    print(out)


if __name__=='__main__':
    main()
