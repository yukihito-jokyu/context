from pathlib import Path
import subprocess,json,datetime,sys,os
root=Path(__file__).parent
name=sys.argv[1]; command=sys.argv[2:]
started=datetime.datetime.now(datetime.timezone.utc).isoformat()
p=subprocess.run(command,cwd=root/'project',text=True,capture_output=True,env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'})
(root/f'evidence/commands/{name}.stdout.txt').write_text(p.stdout)
(root/f'evidence/commands/{name}.stderr.txt').write_text(p.stderr)
f=root/'evidence/commands.json'; records=json.loads(f.read_text()) if f.exists() else []
records.append({'name':name,'command':command,'cwd':str(root/'project'),'started_at':started,'finished_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'exit_code':p.returncode,'stdout':f'commands/{name}.stdout.txt','stderr':f'commands/{name}.stderr.txt'})
f.write_text(json.dumps(records,ensure_ascii=False,indent=2)+'\n')
print(p.stdout,end='');print(p.stderr,end='',file=sys.stderr);sys.exit(p.returncode)
