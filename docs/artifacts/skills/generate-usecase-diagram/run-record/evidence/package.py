from pathlib import Path
import datetime,hashlib,json,os,shutil,subprocess,zipfile
work=Path('/private/tmp/context-85-public-example')
run=work/'.skill-runs/generate-usecase-diagram'
repo=Path('<user-home>/Documents/github_projects/context')
out=repo/'docs/artifacts/skills/generate-usecase-diagram'
if any(out.iterdir()):
    raise SystemExit('Public destination must be empty for a fresh execution')
def digest(b): return hashlib.sha256(b).hexdigest()
shutil.copytree(work/'artifacts/usecase/library',out/'catalog')
shutil.copyfile(run/'evidence/input.md',out/'input.md')
shutil.copyfile(run/'evidence/commands/finish.stdout.txt',out/'output.md')
shutil.copyfile(run/'preview.png',out/'preview.png')
shutil.copytree(run,out/'run-record')
with zipfile.ZipFile(out/'catalog.zip','w',compression=zipfile.ZIP_DEFLATED) as z:
    for f in sorted((out/'catalog').rglob('*')):
        if f.is_file(): z.write(f,f.relative_to(out/'catalog').as_posix())
zip_files=[]
with zipfile.ZipFile(out/'catalog.zip') as z:
    actual=sorted(f.relative_to(out/'catalog').as_posix() for f in (out/'catalog').rglob('*') if f.is_file())
    assert sorted(z.namelist())==actual
    assert 'index.html' in z.namelist()
    for name in actual:
        b=(out/'catalog'/name).read_bytes()
        assert z.read(name)==b
        zip_files.append({'file':name,'sha256':digest(b),'bytes':len(b)})
assert (out/'output.md').read_bytes()==(run/'evidence/commands/finish.stdout.txt').read_bytes()
assert (out/'preview.png').read_bytes()==(run/'preview.png').read_bytes()
env=os.environ.copy()
env['PYTHONDONTWRITEBYTECODE']='1'
env['USECASE_MERMAID_JS']=str(repo/'node_modules/mermaid/dist/mermaid.min.js')
publication=[]
def command(argv,label):
    started=datetime.datetime.now(datetime.timezone.utc).isoformat()
    p=subprocess.run(argv,cwd=work,env=env,capture_output=True,text=True)
    publication.append({'label':label,'argv':argv,'cwd':str(work),'started_at':started,'exit_code':p.returncode,'stdout':p.stdout,'stderr':p.stderr})
    print(p.stdout,end='')
    if p.returncode: raise SystemExit(p.returncode)
command(['python3',str(repo/'utils/skills/design/generate-usecase-diagram/scripts/catalog.py'),'check','--catalog',str(out/'catalog/catalog.json')],'published-catalog-check')
validation={
 'schema_version':1,'recorded_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),
 'execution_directory':str(work),'publication_directory':str(out),
 'fresh_execution':True,'runner':{'kind':'subagent','agent_id':'/root/usecase_public_example'},
 'commands':json.loads((run/'evidence/commands.json').read_text()),
 'publication_checks':publication,
 'status':'passed','catalog':'catalog/catalog.json','render_validation':'catalog/validation.json',
 'html_operations':json.loads((run/'preview.json').read_text()),
 'visual_observations':json.loads((run/'evidence/visual-observations.json').read_text()),
 'user_final_confirmation':{'status':'not_performed','reason':'利用者の最終確認は未実施。目視と自動操作検査は利用者の合意を代行しない。'},
 'manual_browser_interaction':{'status':'not_performed','reason':'追加のCUAによるfile://表示がURLポリシーで拒否された。迂回していない。catalog.py previewでChromeの実画面を保存し、view_imageで確認した。'},
 'source_integrity':{'helper':'scripts/example-skill-source.cjs: sourceManifest','before':'run-record/evidence/source-before.json','after':'run-record/evidence/source-after.json','unchanged':json.loads((run/'evidence/source-before.json').read_text())==json.loads((run/'evidence/source-after.json').read_text())},
 'archive':{'file':'catalog.zip','root_entry':'index.html','file_count':len(zip_files),'status':'passed','comparison':'ZIP内の各ファイルをcatalog/の実ファイルとバイト単位で比較し一致','files':zip_files},
 'output_integrity':{'finish_stdout_exact':True,'preview_after_review_exact':True},
 'not_performed':['利用者の最終確認','対話ブラウザでの手動操作','追加のパッケージ導入','インストールとhooks登録','グローバル設定の変更','GitHub投稿とPR作成','リポジトリ本体へのコミット']
}
def save_validation():
    (out/'validation.json').write_text(json.dumps(validation,ensure_ascii=False,indent=2)+'\n')
save_validation()
command(['node',str(run/'evidence/metadata.cjs')],'source-and-artifacts-verification')
# The preceding helper invocation has completed; persist its real argv, exit code and output.
validation['publication_checks']=publication
save_validation()
# Refresh artifact hashes for the updated real command record, and verify the final package.
command(['node',str(run/'evidence/metadata.cjs')],'final-source-and-artifacts-recheck')
# Keep the final verification stdout under the execution record without changing the published package.
(run/'evidence/publication-commands.json').write_text(json.dumps(publication,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'publication_directory':str(out),'catalog_files':len(zip_files),'zip_matches':True,'finish_stdout_exact':True,'user_final_confirmation':'not_performed'},ensure_ascii=False,indent=2))
