#!/usr/bin/env python3
"""Build and compare the explain-html plugin; no installation or activation."""
import argparse, datetime, hashlib, json, os, shutil, subprocess, zipfile
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--repo-root',type=Path,required=True);p.add_argument('--workdir',type=Path,required=True);a=p.parse_args();repo=a.repo_root.resolve();work=a.workdir.resolve();work.mkdir();plugin=repo/'utils/plugins/explain-html';skill=repo/'utils/skills/discovery/explain-html';out=work/'built/plugin';out.parent.mkdir();results=work/'results';results.mkdir()
def files(root):return {str(x.relative_to(root)):x.read_bytes() for x in root.rglob('*') if x.is_file() and '__pycache__' not in x.parts and x.suffix!='.pyc'}
before_plugin=files(plugin);before_skill=files(skill)
p=subprocess.run(['python3',str(plugin/'build.py'),'--output',str(out)],capture_output=True,text=True,env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'});assert p.returncode==0,(p.stdout,p.stderr)
expected={'.claude-plugin/plugin.json':(plugin/'claude-code/plugin.json').read_bytes(),'hooks/hooks.json':(plugin/'claude-code/hooks.json').read_bytes()};expected.update({'scripts/'+k:v for k,v in files(plugin/'scripts').items()});expected.update({'skills/explain-html/'+k:v for k,v in before_skill.items()});assert files(out)==expected
archive=results/'explain-html-claude-code.zip'
with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
 for name,data in sorted(files(out).items()):z.writestr('explain-html/'+name,data)
with zipfile.ZipFile(archive) as z:z.extractall(work/'extracted')
assert files(work/'extracted/explain-html')==expected
for rel in ['.claude-plugin/plugin.json','hooks/hooks.json']:json.loads((work/'extracted/explain-html'/rel).read_text())
assert files(plugin)==before_plugin and files(skill)==before_skill
verification={'executed_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'status':'passed','checks':['Canonical build completed','Extracted ZIP inventory and bytes match canonical sources','Manifest and hooks are valid JSON','Canonical sources unchanged'],'distribution_files':len(expected),'plugin_files':len(before_plugin),'skill_files':len(before_skill),'unverified':['Installation','Activation','Hooks in real Agent clients'],'command':['python3','<repository>/utils/plugins/explain-html/build.py','--output','<workdir>/built/plugin'],'exit_code':p.returncode,'stdout':p.stdout.replace(str(work),'<workdir>'),'stderr':p.stderr.replace(str(work),'<workdir>'),'archive_sha256':hashlib.sha256(archive.read_bytes()).hexdigest()}
(results/'validation.json').write_text(json.dumps(verification,ensure_ascii=False,indent=2)+'\n')
(results/'verification.txt').write_text('Executed at: '+verification['executed_at']+'\nRunner: /root/refresh_foundation_examples (actual delegated subagent)\nScope: build + extracted ZIP byte comparison; no installation, activation or real-client hook execution.\n$ '+' '.join(verification['command'])+'\n'+verification['stdout']+'Build exit: 0\nPASS: explain-html-claude-code.zip: '+str(len(expected))+' files; exact inventory and byte equality against canonical sources.\nPASS: manifest and hooks parse as JSON.\nPASS: canonical sources unchanged.\n')
print(json.dumps({'status':'passed','files':len(expected),'results':str(results)}))
