#!/usr/bin/env python3
"""Build, but never install or activate, the Claude Code explain-html plugin."""
import argparse
import json
from pathlib import Path
import shutil

p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True)
a=p.parse_args();plugin=Path(__file__).resolve().parent;repo=plugin.parents[2]
skill=(plugin/json.loads((plugin/'bundle.json').read_text())['skill']).resolve();out=a.output.resolve()
if out.exists() or out.is_relative_to(repo):raise SystemExit('Choose a new build directory outside repository')
out.mkdir(parents=True);(out/'.claude-plugin').mkdir();(out/'hooks').mkdir()
shutil.copyfile(plugin/'claude-code/plugin.json',out/'.claude-plugin/plugin.json')
shutil.copyfile(plugin/'claude-code/hooks.json',out/'hooks/hooks.json')
ignore=shutil.ignore_patterns('__pycache__','*.pyc')
shutil.copytree(plugin/'scripts',out/'scripts',ignore=ignore)
shutil.copytree(skill,out/'skills/explain-html',ignore=ignore)
print(out)
