from pathlib import Path
import json, subprocess
O=Path(__file__).parent;S=Path('/Users/yukihito/Documents/github_projects/context/utils/skills/discovery/explain-html');cli=S/'vendor/archify-jp/bin/archify.mjs'
def write(p,m):p.write_text(json.dumps(m,ensure_ascii=False,indent=2)+'\n')
def validate(p,tag):
 m=json.loads(p.read_text());r=subprocess.run(['node',str(cli),'validate',m['diagram_type'],str(p),'--quality','showcase','--json'],capture_output=True,text=True);(O/'records'/f'{p.stem}.{tag}.json').write_text(r.stdout);print(p.stem,tag,r.returncode,r.stdout[:3500] if r.returncode else 'PASS');return r
for name,changes in {'overview':[('e1','labelAt',[505,270])],'sources':[('e1','labelAt',[155,265]),('e2','labelAt',[505,265])],'api':[('e1','labelAt',[515,280]),('e2','labelAt',[155,280])],'states':[('success','route','straight'),('success','labelAt',[690,214])],'retry':[('again','route','up-channel')]}.items():
 p=O/'diagrams'/f'{name}.json';m=json.loads(p.read_text());coll=m.get('connections',m.get('transitions',m.get('edges')))
 for j,(eid,k,v) in enumerate(changes):
  next(e for e in coll if e['id']==eid)[k]=v;write(p,m);validate(p,'refine'+str(j+1))
p=O/'diagrams/example.json';m=json.loads(p.read_text());m['participants'].insert(2,dict(id='record',label='ジョブ記録',type='database'));m['meta']['viewBox']=[980,730]
for e in m['messages']:
 if e['id'] in ['run','finish']: e['to']='record'
write(p,m);validate(p,'refine1')
