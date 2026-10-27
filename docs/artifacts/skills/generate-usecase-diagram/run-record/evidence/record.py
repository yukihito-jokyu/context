from pathlib import Path
import datetime,json,os,subprocess,sys
base=Path(__file__).resolve().parent
label=sys.argv[1]
cmd=sys.argv[2:]
env=os.environ.copy()
env['PYTHONDONTWRITEBYTECODE']='1'
env['USECASE_MERMAID_JS']='<user-home>/Documents/github_projects/context/node_modules/mermaid/dist/mermaid.min.js'
started=datetime.datetime.now(datetime.timezone.utc).isoformat()
p=subprocess.run(cmd,cwd=base.parents[2],env=env,capture_output=True)
commands=base/'commands'
commands.mkdir(exist_ok=True)
(commands/(label+'.stdout.txt')).write_bytes(p.stdout)
(commands/(label+'.stderr.txt')).write_bytes(p.stderr)
log=base/'commands.json'
rows=json.loads(log.read_text()) if log.exists() else []
rows.append({'label':label,'argv':cmd,'cwd':str(base.parents[2]),'environment':{'PYTHONDONTWRITEBYTECODE':'1','USECASE_MERMAID_JS':env['USECASE_MERMAID_JS']},'started_at':started,'completed_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'exit_code':p.returncode,'stdout':'commands/'+label+'.stdout.txt','stderr':'commands/'+label+'.stderr.txt'})
log.write_text(json.dumps(rows,ensure_ascii=False,indent=2)+'\n')
sys.stdout.buffer.write(p.stdout)
sys.stderr.buffer.write(p.stderr)
raise SystemExit(p.returncode)
