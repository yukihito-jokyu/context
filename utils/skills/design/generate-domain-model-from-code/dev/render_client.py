#!/usr/bin/env python3
"""Evaluation-only mmdc adapter. Send bounded render jobs through local files."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

if '--version' in sys.argv or '-V' in sys.argv or '--help' in sys.argv or '-h' in sys.argv:
    raise SystemExit(subprocess.run([os.environ['RENDER_MMDC'], *sys.argv[1:]]).returncode)
queue=Path.cwd()/'.skill-runs/png-requests'
queue.mkdir(parents=True,exist_ok=True)
key=hashlib.sha256(json.dumps(sys.argv[1:]).encode()).hexdigest()[:20]
request=queue/(key+'.render-request.json')
response=queue/(key+'.render-response.json')
response.unlink(missing_ok=True)
temp=queue/(key+'.tmp')
temp.write_text(json.dumps(dict(args=sys.argv[1:]),ensure_ascii=False))
temp.replace(request)
try:
    deadline=time.monotonic()+110
    while time.monotonic()<deadline:
        if response.exists():
            result=json.loads(response.read_text())
            print(result.get('stdout',''))
            print(result.get('stderr',''),file=sys.stderr)
            raise SystemExit(result['exit'])
        time.sleep(.1)
    print('Render worker did not respond',file=sys.stderr)
    raise SystemExit(1)
finally:
    request.unlink(missing_ok=True)
    response.unlink(missing_ok=True)
