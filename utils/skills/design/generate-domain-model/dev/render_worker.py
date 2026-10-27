#!/usr/bin/env python3
"""Evaluation-only PNG worker. No shell or arbitrary job commands are accepted."""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import time

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--lab',type=Path,required=True)
p.add_argument('--cli',type=Path,required=True)
p.add_argument('--browser',type=Path,required=True)
p.add_argument('--seconds',type=int,default=7200)
a=p.parse_args();lab=a.lab.resolve();deadline=time.monotonic()+a.seconds
while time.monotonic()<deadline:
    for request in sorted(lab.glob('round-*/**/.skill-runs/png-requests/*.render-request.json')):
        response=request.with_name(request.name.replace('.render-request.json','.render-response.json'))
        if response.exists():continue
        project=request.parents[2].resolve()
        temporary=[]
        try:
            if not project.is_relative_to(lab) or not (project/'.git').exists():raise ValueError('Unknown evaluation project')
            args=json.loads(request.read_text())['args']
            if len(args)%2 or len(args)!=12:raise ValueError('Unexpected Mermaid CLI arguments')
            flags=dict(zip(args[::2],args[1::2]))
            if set(flags)!={'-i','-o','-c','-b','-s','-p'} or flags['-b']!='white' or flags['-s']!='2':raise ValueError('Only the catalog PNG render is allowed')
            paths={key:Path(flags[key]).resolve() for key in ['-i','-o','-c','-p']}
            allowed=project/'.skill-runs/generate-domain-model/out'
            if not all(path.is_relative_to(allowed) for path in paths.values()):raise ValueError('Render path is outside the catalog workspace')
            if paths['-i'].suffix!='.mmd' or paths['-o'].suffix!='.png':raise ValueError('Only Mermaid to PNG is allowed')
            source=paths['-i'].read_text()
            if not source.startswith('classDiagram\n') or any(value in source for value in ['http://','https://','%%{','<script']):raise ValueError('Expected a local classDiagram')
            config=json.loads(paths['-c'].read_text())
            if config.get('securityLevel')!='strict':raise ValueError('Expected strict Mermaid rendering')
            profile=request.parent/(request.stem+'.profile')
            browser_config=request.parent/(request.stem+'.puppeteer.json')
            browser_config.write_text(json.dumps(dict(executablePath=str(a.browser.resolve()),userDataDir=str(profile))))
            temporary=[profile,browser_config]
            command=[str(a.cli.resolve()),'-i',str(paths['-i']),'-o',str(paths['-o']),'-c',str(paths['-c']),'-b','white','-s','2','-p',str(browser_config)]
            result=subprocess.run(command,text=True,capture_output=True,timeout=80)
            value=dict(exit=result.returncode,stdout=result.stdout,stderr=result.stderr)
        except Exception as e:
            value=dict(exit=1,stdout='',stderr=str(e))
        finally:
            for item in temporary:
                if item.is_dir():shutil.rmtree(item,ignore_errors=True)
                else:item.unlink(missing_ok=True)
        temp=response.with_suffix('.tmp');temp.write_text(json.dumps(value,ensure_ascii=False));temp.replace(response)
    time.sleep(.2)
