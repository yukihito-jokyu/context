from pathlib import Path
from html.parser import HTMLParser
import json,base64,hashlib,re,subprocess,xml.etree.ElementTree as E
O=Path(__file__).parent;S=Path('<user-home>/Documents/github_projects/context/utils/skills/discovery/explain-html')
p=O/'index.html';s=p.read_text()
s=s.replace("[{opacity:1,strokeDashoffset:0},{opacity:1,strokeDashoffset:-1},{opacity:0,strokeDashoffset:-1}]", "[{opacity:0,strokeDashoffset:0,offset:0},{opacity:1,strokeDashoffset:0,offset:.04},{opacity:1,strokeDashoffset:-1,offset:.96},{opacity:0,strokeDashoffset:-1,offset:1}]")
p.write_text(s)
class Read(HTMLParser):
 def __init__(self):super().__init__();self.ids=[];self.links=[];self.imgs=[];self.scripts=[];self.inscript=False
 def handle_starttag(self,t,a):
  a=dict(a)
  if 'id'in a:self.ids.append(a['id'])
  if t=='a':self.links.append(a.get('href',''))
  if t=='img':self.imgs.append(a)
  if t=='script':self.inscript=True;self.scripts.append('')
 def handle_endtag(self,t):
  if t=='script':self.inscript=False
 def handle_data(self,d):
  if self.inscript:self.scripts[-1]+=d
r=Read();r.feed(s)
results={}
for name,args in [('overviews',['check_overviews.py',str(p)]),('coverage',['check_coverage.py',str(p),str(O/'coverage.json')]),('vendor-lock',['sync_vendor.py','--check'])]:
 proc=subprocess.run(['python3',str(S/'scripts'/args[0]),*args[1:]],capture_output=True,text=True);(O/'records'/f'{name}.json').write_text(proc.stdout);results[name]=dict(exit_code=proc.returncode,result=json.loads(proc.stdout))
checks={}
checks['unique_ids']=len(r.ids)==len(set(r.ids))
checks['hash_targets']=all(h[1:] in r.ids for h in r.links if h.startswith('#'))
checks['relative_files']=all((O/h).is_file() for h in r.links if h and not h.startswith(('#','http')))
checks['self_contained_media']=all(a['src'].startswith('data:image/') for a in r.imgs) and not re.search(r'<(?:script|link)[^>]+(?:src|href)=',s)
checks['all_six_images_match_standard_svg']=all(base64.b64decode(a['src'].split(',',1)[1])==(O/'diagrams'/f'{n}.svg').read_bytes() for a,n in zip(r.imgs,['overview','example','api','states','retry','sources']))
checks['all_model_hashes_match']=all(a['data-archify-model-sha256']==hashlib.sha256((O/'diagrams'/f'{n}.json').read_bytes()).hexdigest() for a,n in zip(r.imgs,['overview','example','api','states','retry','sources']))
checks['source_embedded']=__import__('html').escape((O/'source.txt').read_text()) in s
checks['no_placeholder']=not re.search(r'\{\{[A-Z_]+\}\}',s)
checks['no_initial_diagram_scroll']=not re.search(r'class="diagram-scroll"',s)
syntax=[]
for j,js in enumerate(r.scripts):
 f=O/'records'/f'inline-script-{j}.js';f.write_text(js);proc=subprocess.run(['node','--check',str(f)],capture_output=True,text=True);syntax.append(dict(index=j,exit_code=proc.returncode,output=proc.stdout+proc.stderr))
checks['javascript_syntax']=all(x['exit_code']==0 for x in syntax)
checks['flow_scope_wraps_code']=s.index('<div data-flow-diagram>')<s.index('id="post-request-l1"')<s.index('id="api"')
checks['flow_paths_match']=all(d in (O/'diagrams/example.svg').read_text() for d in re.findall(r'class="trace-signal"[^>]+ d="([^"]+)"',s))
for n in ['overview','example','api','states','retry','sources']:
 m=O/'diagrams'/f'{n}.json';typ=json.loads(m.read_text())['diagram_type'];proc=subprocess.run(['node',str(S/'vendor/archify-jp/bin/archify.mjs'),'validate',typ,str(m),'--quality','showcase','--json'],capture_output=True,text=True);(O/'records'/f'{n}.final-validation.json').write_text(proc.stdout);checks[n+'-showcase']=proc.returncode==0
v=dict(checked_on='2026-10-11',method='static HTML parser, source/hash correspondence, JavaScript syntax, Archify validators; no browser',checks=checks,script_syntax=syntax,check_commands=results,browser_tested=False,browser_export_verified=False,pixel_equivalence_verified=False,unperformed=['browser rendering at wide/narrow viewport','interactive navigation/history/focus','real animation/pause/restart/visibility/reduced-motion','print and JavaScript-disabled rendering'],raster_review=dict(method='rsvg-convert at width 1120; review-only CSS variable resolution',standard_svg_unchanged=True,embedded_images_are_original_standard_svg=True,browser_equivalence=False))
(O/'records/verification.json').write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n')
plans=json.loads((O/'diagram-plan.json').read_text())
for d in plans['diagrams']:
 m=json.loads((O/d['model_path']).read_text());d['entities']=m.get('components',m.get('participants',m.get('states',m.get('nodes'))));d['relations']=m.get('connections',m.get('messages',m.get('transitions',m.get('edges'))));d['model_sha256']=hashlib.sha256((O/d['model_path']).read_bytes()).hexdigest()
(O/'diagram-plan.json').write_text(json.dumps(plans,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(checks,ensure_ascii=False,indent=2));assert all(checks.values())
