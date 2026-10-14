#!/usr/bin/env python3
"""Claude Code Stop adapter. Inactive projects are untouched; no global install."""
import json
from pathlib import Path
import subprocess
import sys


def main():
    try:
        event = json.load(sys.stdin)
        if event.get('hook_event_name') != 'Stop': return 0
        cwd = Path(event['cwd']).resolve()
        active = next((p/'.explain-html-active.json' for p in [cwd,*cwd.parents]
                       if (p/'.explain-html-active.json').is_file()), None)
        if active is None: return 0
        config = json.loads(active.read_text())
        manifest = (active.parent/config['manifest']).resolve()
        article = (active.parent/config['article']).resolve()
        if not manifest.is_relative_to(active.parent) or not article.is_relative_to(manifest.parent):
            raise ValueError('Activation paths must stay within project/artifact root')
        checker = Path(__file__).resolve().parents[1]/'skills/explain-html/scripts/check_diagram_delegation.py'
        if not checker.is_file(): raise ValueError('Packaged checker is missing; build plugin first')
        result = subprocess.run([sys.executable,str(checker),str(manifest),'--article',str(article)],
                                text=True,capture_output=True,timeout=120)
        if result.returncode:
            raise ValueError((result.stdout or result.stderr)[-12000:])
        return 0
    except (ValueError, OSError, KeyError, TypeError, AttributeError, subprocess.TimeoutExpired) as exc:
        print('Archify必須検査が未通過です。独自SVGや自己申告で代用せず、モデルと標準出力を修正してください。\n'+str(exc),file=sys.stderr)
        return 2

if __name__ == '__main__': sys.exit(main())
