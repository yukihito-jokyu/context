#!/usr/bin/env python3
"""Rebuild the published, newly authored source with current skill scripts.
No hooks, installation, package fetching or model sessions are started.
"""
import argparse, hashlib, json, shutil, subprocess, sys
from pathlib import Path

def main():
 p=argparse.ArgumentParser(description=__doc__)
 p.add_argument('--repo-root',type=Path,required=True)
 p.add_argument('--workdir',type=Path,required=True)
 p.add_argument('--artifacts',type=Path,default=Path(__file__).resolve().parent)
 p.add_argument('--finish',action='store_true',help='Finish with an explicit note that replay visual QA is unverified')
 a=p.parse_args();repo=a.repo_root.resolve();work=a.workdir.resolve();artifacts=a.artifacts.resolve()
 if work.exists() or work.is_relative_to(repo):p.error('Choose a new workdir outside the repository')
 work.mkdir(parents=True);project=work/'project';project.mkdir();origin=repo/'utils/skills/documentation/write-requirement-document';skill=work/'skill/write-requirement-document'
 code='const {sourceManifest}=require("./scripts/example-skill-source.cjs");process.stdout.write(JSON.stringify(sourceManifest(process.argv[1])))'
 before=json.loads(subprocess.check_output(['node','-e',code,str(origin)],cwd=repo,text=True))
 for row in before['source_files']:
  dest=skill/row['file'];dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(origin/row['file'],dest)
 def run(*args):subprocess.run([sys.executable,str(skill/'scripts'/args[0]),*args[1:]],cwd=project,check=True)
 subprocess.run(['git','init','-q',str(project)],check=True)
 run('run.py','start','--guess','language=ja',(artifacts/'input.md').read_text())
 run('document.py','doctor');out=project/'.skill-runs/write-requirement-document/out';out.mkdir(parents=True,exist_ok=True)
 shutil.copyfile(artifacts/'out/requirement-document.json',out/'requirement-document.json')
 run('document.py','build','--source',str(out/'requirement-document.json'),'--out',str(out));run('run.py','check')
 print('Open each PNG and compare its labels and conditions with the source:',*sorted((out/'diagrams').glob('*.png')),sep='\n')
 if a.finish:
  (out.parent/'notes.md').write_text('- 再現用スクリプトは公開済みの構造化原本を再描画した。新規のAI執筆実行ではない。\n- この再現実行のPNG・ブラウザ目視は未実施であり、公開サンプルの初回実行の確認を引き継がない。\n')
  run('run.py','finish')
 assert not (project/'.skill-feedback').exists()
 after=json.loads(subprocess.check_output(['node','-e',code,str(origin)],cwd=repo,text=True));assert before==after
 print('Source unchanged; collection directory was not created.')

if __name__=='__main__':main()
