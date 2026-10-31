#!/usr/bin/env python3
"""Reproduce package relocation and direct hook checks without installing the plugin."""
import argparse
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import zipfile

NAME = 'write-requirement-document'
TASK = 'AGENTS.mdとskill-authoringの公開成果物再作成手順に従い、資料末尾の空行除去後の要件定義Skill/pluginを新規実行して公開成果物を全再生成する。正本とpluginソースは変更しない。両製品向けbuild・移動・ZIP展開・正本byte照合・4hooks直接接続・coreと収集機能の分離・合成指摘収集・専用7tests・Claude manifest検査を実行し、実際のコマンド・結果・未実施事項と実subagent識別子を記録する。実ユーザー承認・導入・外部投稿・実モデル収束を行わない。'
REQUEST = '備品予約の同梱見本を検証する。社員は空き時間を確認して備品を予約し、自分の予約を取り消す。重複予約を防止する。今回は新しい要件を作成せず、配布物に含む完成見本を配置して出力検査とhooksの接続を確認する。'


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--repo-root', type=Path, required=True)
    p.add_argument('--workdir', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    repo, work, output = a.repo_root.resolve(), a.workdir.resolve(), a.output.resolve()
    if work.exists() or work.is_relative_to(repo):
        p.error('Choose a new workdir outside the repository')
    work.mkdir(parents=True)
    output.mkdir(parents=True, exist_ok=True)
    plugin = repo / 'utils/plugins' / NAME
    skill = repo / 'utils/skills/documentation' / NAME
    records, checks = [], []
    def clean(value):
        if isinstance(value, str):
            for old, new in [(str(repo), '<repository>'), (str(work), '<workdir>'), (str(Path.home()), '<user-home>'), (sys.executable, 'python3')]:
                value = value.replace(old, new)
            return value
        if isinstance(value, list): return [clean(x) for x in value]
        if isinstance(value, dict): return {k:clean(v) for k,v in value.items()}
        return value
    def run(label, command, cwd=repo, data=None, env=None, expected=0, shell=False):
        result = subprocess.run(command, cwd=cwd, input=data, env=env, shell=shell, capture_output=True, text=True)
        records.append(clean({'label':label, 'command':command, 'cwd':str(cwd), 'stdin':data,
                              'exit_code':result.returncode, 'stdout':result.stdout, 'stderr':result.stderr}))
        assert result.returncode == expected, (label, result.returncode, result.stdout, result.stderr)
        return result
    def manifest(folder):
        code = 'const {sourceManifest}=require("./scripts/example-skill-source.cjs");process.stdout.write(JSON.stringify(sourceManifest(process.argv[1])))'
        return json.loads(run('source inventory', ['node','-e',code,str(folder)]).stdout)
    def inventory(folder):
        return {p.relative_to(folder).as_posix():hashlib.sha256(p.read_bytes()).hexdigest()
                for p in folder.rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix != '.pyc'}
    plugin_before, skill_before = manifest(plugin), manifest(skill)
    (output/'input.md').write_text('# Pluginの公開検証入力\n\n'+REQUEST+'\n\nCodex・Claude Code向けに新規ビルドし、移動・ZIP展開後の全ファイルを照合する。設定に記載された4イベントのcommandを直接実行する。実製品への導入、自動hooksの起動、信頼設定、新規要件定義書のAI作成、PNGの再描画、ブラウザ目視は行わない。\n',encoding='utf-8')
    builds = {}
    for agent, platform in [('codex','codex'),('claude-code','claude')]:
        original = work / 'build' / agent
        run(agent+': build',[sys.executable,str(plugin/'build.py'),'--agent',agent,'--output',str(original)])
        relocated = work / 'relocated path with spaces' / agent
        relocated.parent.mkdir(exist_ok=True)
        original.rename(relocated)
        archive = output / (NAME+'-'+agent+'.zip')
        with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
            for file in sorted(relocated.rglob('*')):
                assert not file.is_symlink(), file
                if file.is_file():
                    z.write(file,file.relative_to(relocated).as_posix())
        unpacked = work / 'unpacked path with spaces' / agent
        with zipfile.ZipFile(archive) as z:
            assert z.testzip() is None
            assert all(not Path(n).is_absolute() and '..' not in Path(n).parts for n in z.namelist())
            z.extractall(unpacked)
        assert inventory(unpacked)==inventory(relocated)
        runtime = unpacked / 'runtime' / NAME
        expected = {row['file']:row['sha256'] for row in skill_before['source_files']}
        assert inventory(runtime) == expected
        assert not (runtime/'dev/results').exists()
        assert not (runtime/'dev/convergence-report.md').exists()
        manifest_dir = '.codex-plugin' if agent=='codex' else '.claude-plugin'
        declared = json.loads((unpacked/manifest_dir/'plugin.json').read_text())
        assert declared['name']==NAME and declared['version']=='0.1.1'
        for key in ['skills','hooks']:
            if key in declared: assert (unpacked/declared[key]).exists()
        settings = json.loads((unpacked/'hooks/hooks.json').read_text())
        assert set(settings['hooks'])=={'PreToolUse','PostToolUse','Stop','UserPromptSubmit'}
        assert (unpacked/'skills'/NAME/'SKILL.md').is_file()
        checks.append({'check':agent+': relocated ZIP, manifest and complete runtime', 'status':'passed',
                       'distribution_files':len(inventory(unpacked)), 'runtime_files':len(expected), 'archive_sha256':hashlib.sha256(archive.read_bytes()).hexdigest()})
        project = work / ('project-'+agent)
        project.mkdir()
        run(agent+': init temporary project',['git','init','-q',str(project)])
        env = {**os.environ,'PLUGIN_ROOT':str(unpacked),'CLAUDE_PLUGIN_ROOT':str(unpacked)}
        def hook(label,event,payload):
            command=settings['hooks'][event][0]['hooks'][0]['command']
            return run(agent+': '+label,command,cwd=project,data=json.dumps({'cwd':str(project),**payload}),env=env,shell=True)
        def edit(path):
            return ({'tool_name':'apply_patch','tool_input':{'input':'*** Begin Patch\n*** Update File: '+str(path)+'\n*** End Patch'}}
                    if platform=='codex' else {'tool_name':'Write','tool_input':{'file_path':str(path)}})
        for event in settings['hooks']:
            assert hook('inactive '+event,event,edit(project/'unrelated.txt')).stdout == ''
        core = runtime/'scripts/run.py'
        run(agent+': start fixture validation',[sys.executable,str(core),'start',REQUEST],cwd=project)
        run_dir=project/'.skill-runs'/NAME
        original_state=(run_dir/'state.json').read_bytes()
        injected=hook('nonedit startup injects collection guidance','PostToolUse',{'session_id':'synthetic-start-'+agent,'tool_name':'exec_command'})
        assert 'context --file' in json.loads(injected.stdout)['hookSpecificOutput']['additionalContext']
        assert (run_dir/'state.json').read_bytes()==original_state
        store=project/'.skill-feedback'/NAME/'feedback.json'
        assert json.loads(store.read_text())['deliveries']==[]
        pre=hook('deny direct state edit','PreToolUse',edit(run_dir/'state.json'))
        assert json.loads(pre.stdout)['hookSpecificOutput']['permissionDecision']=='deny'
        out=run_dir/'out'
        shutil.copytree(runtime/'assets/examples',out)
        source=out/'requirement-document.json'
        good=source.read_bytes()
        source.write_text('{}')
        post=hook('reject malformed source','PostToolUse',edit(source))
        assert json.loads(post.stdout)['decision']=='block'
        source.write_bytes(good)
        html=out/'requirement-document.html'
        good_html=html.read_bytes()
        html.write_text('<html>broken</html>')
        run(agent+': reject broken HTML',[sys.executable,str(core),'check'],cwd=project,expected=1)
        html.write_bytes(good_html)
        run(agent+': check complete fixture',[sys.executable,str(core),'check'],cwd=project)
        assert json.loads(hook('unfinished Stop','Stop',{}).stdout)['decision']=='block'
        run(agent+': wait',[sys.executable,str(core),'wait','--question','予約条件を確認してください'],cwd=project)
        assert hook('waiting Stop','Stop',{}).stdout==''
        assert hook('resume prompt','UserPromptSubmit',{}).returncode==0
        assert json.loads((run_dir/'state.json').read_text())['status']=='active'
        run(agent+': finish fixture validation',[sys.executable,str(core),'finish'],cwd=project)
        assert hook('done Stop','Stop',{}).stdout==''
        assert all(not (project/d).exists() for d in ['.agents','.codex','.claude'])
        checks.append({'check':agent+': configured hooks and fixture check/finish without standalone placement','status':'passed',
                       'events':list(settings['hooks']), 'state_edit':'deny','malformed_source':'block','broken_html':'check rejected',
                       'fixture':'bundled completed example; no newly authored requirements','standalone_directories_created':0})
        # Core remains useful when all extension entrypoints are absent and the
        # collection path is deliberately unwritable as a directory.
        bare=work/('bare-'+agent)
        bare.mkdir()
        run(agent+': init hook-disabled project',['git','init','-q',str(bare)])
        bare_runtime=work/('bare-runtime-'+agent)
        shutil.copytree(runtime,bare_runtime)
        for filename in ('hook.py','feedback.py','feedback_review.py'):
            (bare_runtime/'scripts'/filename).unlink()
        (bare/'.skill-feedback').write_text('Collection is unavailable')
        bare_core=bare_runtime/'scripts/run.py'
        run(agent+': no hooks start',[sys.executable,str(bare_core),'start',REQUEST],cwd=bare)
        shutil.copytree(bare_runtime/'assets/examples',bare/'.skill-runs'/NAME/'out')
        for command in ('check','finish'):
            result=run(agent+': no hooks '+command,[sys.executable,str(bare_core),command],cwd=bare)
            assert 'feedback.py' not in result.stdout
        assert (bare/'.skill-feedback').read_text()=='Collection is unavailable'
        checks.append({'check':agent+': core check/finish without hooks or collector scripts','status':'passed','collection_available':False})
        # A distinct synthetic project exercises the extra feature only through
        # guidance emitted by configured hooks. No real user approval is made.
        synthetic=work/('synthetic-feedback-'+agent)
        synthetic.mkdir()
        run(agent+': init synthetic feedback project',['git','init','-q',str(synthetic)])
        def synthetic_hook(label,event,payload):
            command=settings['hooks'][event][0]['hooks'][0]['command']
            return run(agent+': '+label,command,cwd=synthetic,data=json.dumps({'cwd':str(synthetic),**payload}),env=env,shell=True)
        run(agent+': synthetic core start',[sys.executable,str(core),'start',REQUEST],cwd=synthetic)
        synthetic_run=synthetic/'.skill-runs'/NAME
        original_state=(synthetic_run/'state.json').read_bytes()
        event={'session_id':'synthetic-'+agent,'tool_name':'exec_command'}
        response=synthetic_hook('hook-only capture guidance','PostToolUse',event)
        assert 'context --file' in json.loads(response.stdout)['hookSpecificOutput']['additionalContext']
        assert (synthetic_run/'state.json').read_bytes()==original_state
        synthetic_store=synthetic/'.skill-feedback'/NAME/'feedback.json'
        assert json.loads(synthetic_store.read_text())['deliveries']==[]
        shutil.copytree(runtime/'assets/examples',synthetic_run/'out')
        run(agent+': synthetic finish before Stop',[sys.executable,str(core),'finish'],cwd=synthetic)
        assert json.loads(synthetic_store.read_text())['deliveries']==[]
        synthetic_hook('Stop records first delivery','Stop',event)
        before_id=json.loads(synthetic_store.read_text())['deliveries'][0]['id']
        response=synthetic_hook('synthetic correction prompt','UserPromptSubmit',{**event,'turn_id':'synthetic-feedback-1','prompt':'タイトルに業務名が分かるようにしてください。'})
        assert 'feedback --event' in json.loads(response.stdout)['hookSpecificOutput']['additionalContext']
        event_id=json.loads(synthetic_store.read_text())['messages'][-1]['id']
        run(agent+': classify synthetic correction from hook guidance',[sys.executable,str(runtime/'scripts/feedback.py'),'feedback','--event',event_id],cwd=synthetic)
        revised_source=synthetic_run/'out/requirement-document.json'
        revised=json.loads(revised_source.read_text());revised['title']='備品予約業務の要件定義書'
        revised_source.write_text(json.dumps(revised,ensure_ascii=False,indent=2)+'\n')
        run(agent+': rebuild synthetic revision',[sys.executable,str(runtime/'scripts/document.py'),'build','--source',str(revised_source),'--out',str(synthetic_run/'out')],cwd=synthetic)
        run(agent+': check synthetic revision',[sys.executable,str(core),'check'],cwd=synthetic)
        synthetic_hook('Stop records synthetic revision','Stop',event)
        corpus=json.loads(synthetic_store.read_text()); case=corpus['cases'][0]
        assert case['before']==before_id and case['revisions'] and case['status']=='pending' and case['approval'] is None
        run(agent+': validate synthetic corpus',[sys.executable,str(runtime/'scripts/feedback.py'),'validate'],cwd=synthetic)
        result=run(agent+': export refuses unapproved synthetic corpus',[sys.executable,str(runtime/'scripts/feedback.py'),'export','--out',str(work/('synthetic-export-'+agent))],cwd=synthetic,expected=1)
        assert 'No user-approved corrections' in result.stderr
        checks.append({'check':agent+': hook-only capture, first delivery and synthetic revision','status':'passed','core_state_changed_by_capture':False,'before_retained':True,'revision_saved':True,'real_approvals':0,'case_status':'pending','unapproved_export':'rejected','scope':'synthetic; no real user approval or model convergence'})
        builds[agent]=unpacked
    unit=run('plugin-owned unit tests',[sys.executable,'-m','unittest','discover','-s',str(plugin/'tests'),'-p','test_*.py','-v'])
    (output/'unit-tests.log').write_text(clean(unit.stdout+unit.stderr),encoding='utf-8')
    checks.append({'check':'plugin-owned unit tests','status':'passed','count':7})
    if shutil.which('claude'):
        isolated=work/'isolated-claude-config'
        isolated.mkdir()
        result=run('Claude manifest validation',['claude','plugin','validate',str(builds['claude-code'])],env={**os.environ,'CLAUDE_CONFIG_DIR':str(isolated)})
        (output/'manifest-validation.log').write_text(clean(result.stdout+result.stderr),encoding='utf-8')
        checks.append({'check':'Claude CLI manifest validation','status':'passed','model_sessions':0})
    assert manifest(plugin)==plugin_before
    assert manifest(skill)==skill_before
    checks.append({'check':'canonical sources unchanged','status':'passed','plugin_files':len(plugin_before['source_files']),'skill_files':len(skill_before['source_files'])})
    limitations=['Real user approval through the review UI','Independent model Eval and convergence runs','Automatic hooks from real product sessions','Codex trust UI','Installation and activation','New AI-authored requirements','PNG rendering and browser visual inspection']
    validation={'status':'passed','checks':checks,'commands':records,'command_count':len(records),
                'not_verified':limitations,'redactions':['repository absolute path -> <repository>','temporary workdir -> <workdir>','user home -> <user-home>','local Python executable path -> python3']}
    (output/'validation.json').write_text(json.dumps(validation,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    lines=[NAME+' plugin: PASS','','同梱見本の実行検証。新しい要件定義書をAIで作成した結果ではありません。','', 'Checks:']
    lines += ['PASS '+json.dumps(c,ensure_ascii=False) for c in checks]
    lines += ['',f'Commands recorded: {len(records)}','', 'Not verified:']+limitations
    lines += ['', 'Redactions:']+validation['redactions']
    lines += ['', 'Reproduction:', 'Run verify_plugin.py with --repo-root, a new --workdir outside the repository, and --output.', 'The complete repository and its plugin-owned tests are required. No installation or model session is started.']
    (output/'verification.txt').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    downloads=[{'label':'Codex用plugin ZIP','file':NAME+'-codex.zip'}, {'label':'Claude Code用plugin ZIP','file':NAME+'-claude-code.zip'},
               {'label':'検証結果','file':'verification.txt'},{'label':'実コマンドと結果','file':'validation.json'}, {'label':'専用テスト結果','file':'unit-tests.log'},
               {'label':'再現用スクリプト','file':'verify_plugin.py'}]
    if (output/'manifest-validation.log').exists(): downloads.append({'label':'manifest検査','file':'manifest-validation.log'})
    execution={'name':NAME,'kind':'plugin','executed_at':datetime.now(timezone.utc).isoformat(),
               'runner':{'kind':'subagent','agent_id':'/root/refresh_requirements_precommit','task':TASK},
               'stage':'0.1.1の両製品向け配布物を生成・移動・展開。hooks無効時のcore完了と、hooks由来の案内・提示版・合成指摘・修正版保存を検証。実承認・実製品への導入・モデル収束は未実施',
               'input':'input.md','text_output':'verification.txt','checks':[c['check'] for c in checks], 'downloads':downloads,
               **plugin_before,'skill_sources':[{'file':'utils/skills/documentation/'+NAME,**skill_before}]}
    if Path(__file__).resolve() != (output/'verify_plugin.py').resolve(): shutil.copyfile(__file__,output/'verify_plugin.py')
    execution['artifacts']=[{'file':p.relative_to(output).as_posix(),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
                            for p in sorted(output.rglob('*')) if p.is_file() and p.name!='execution.json']
    (output/'execution.json').write_text(json.dumps(execution,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    helper='const fs=require("fs");const {verifyArtifacts,sourceManifest}=require("./scripts/example-skill-source.cjs");const p=process.argv[1];const r=JSON.parse(fs.readFileSync(p+"/execution.json"));verifyArtifacts({record:r,exampleDir:p});if(JSON.stringify(sourceManifest(process.argv[2]))!==JSON.stringify({source_files:r.source_files,source_sha256:r.source_sha256}))throw Error("plugin source mismatch");console.log("sourceManifest and verifyArtifacts: PASS")'
    result=subprocess.run(['node','-e',helper,str(output),str(plugin)],cwd=repo,capture_output=True,text=True,check=True)
    print(result.stdout,end='')
    spec=importlib.util.spec_from_file_location('privacy',repo/'scripts/check-public-environment.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    failures=[]
    for file in output.rglob('*'):
        if file.is_file(): module.scan(file.read_bytes(),file.relative_to(output).as_posix(),failures)
    assert not failures,failures
    print(json.dumps({'checks':len(checks),'commands':len(records),'files':len(execution['artifacts'])+1,'privacy_findings':len(failures),'distributions':[c for c in checks if 'distribution_files' in c]},ensure_ascii=False))


if __name__=='__main__':
    main()
