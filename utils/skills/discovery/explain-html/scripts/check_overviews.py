"""Check that every concern page has its own visible overview and reading context.
Presence checks do not replace review of coverage or diagram semantics.
"""
import argparse,json
from html.parser import HTMLParser
from pathlib import Path
class Check(HTMLParser):
 def __init__(self):super().__init__();self.stack=[];self.pages={};self.maps=[];self.issues=[]
 def handle_starttag(self,tag,attrs):
  a=dict(attrs);n={'tag':tag,'attrs':a};self.stack.append(n)
  if 'data-page' in a:self.pages[a['id']]=[]
  if 'data-concern-overview' in a:
   pages=[x for x in self.stack if 'data-page' in x['attrs']];pid=pages[-1]['attrs']['id'] if pages else None
   page=pages[-1]['attrs'] if pages else {}
   n.update({'overview':True,'page':pid,'text':'','figure':False,'image':False,'links':0,
    'text_mode':page.get('data-overview-mode')=='text','reason':page.get('data-overview-reason','').strip()})
   self.maps.append(n)
   if pid in self.pages:self.pages[pid].append(n)
   if a['data-concern-overview']!=pid:self.issues.append('Overview does not match containing page: '+str(pid))
   if any(x['tag']=='details' for x in self.stack[:-1]) or 'hidden' in a:self.issues.append('Overview is hidden or folded: '+str(pid))
  for x in self.stack:
   if x.get('overview'):
    if tag=='figure':x['figure']=True
    if tag=='img' and a.get('src','').startswith('data:image/'):
     import re
     if re.fullmatch(r'[a-f0-9]{64}',a.get('data-archify-model-sha256','')) and a.get('data-archify-preset')=='editorial' and a.get('data-archify-export'):x['image']=True
     else:self.issues.append(str(x['page'])+': missing editorial/export/hash attributes')
    if tag=='a' and a.get('href','').startswith('#'):x['links']+=1
  if tag in ['img','br','hr','meta','link','input']:self.stack.pop()
 def handle_data(self,data):
  for x in self.stack:
   if x.get('overview'):x['text']+=data
 def handle_endtag(self,tag):
  for i in range(len(self.stack)-1,-1,-1):
   if self.stack[i]['tag']==tag:del self.stack[i:];break
 def result(self):
  for pid,maps in self.pages.items():
   if len(maps)!=1:self.issues.append(pid+': expected one whole overview, got '+str(len(maps)))
   for m in maps:
    if m['text_mode']:
     if not m['reason'] or not m['text'].strip() or m['links']==0:self.issues.append(pid+': text overview requires reason, context and detail entry')
    elif not m['figure'] or not m['image'] or m['links']==0 or not m['text'].strip():self.issues.append(pid+': missing diagram, context, or detail entry')
  return {'pages':len(self.pages),'whole_overviews':len(self.maps),'issues':self.issues,'pass':bool(self.pages) and not self.issues,'semantic_review':'Review whether each diagram covers the concern and represents true relations; not established by this presence check.'}
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('html');a=p.parse_args();c=Check();c.feed(Path(a.html).read_text());r=c.result();print(json.dumps(r,ensure_ascii=False,indent=2));raise SystemExit(0 if r['pass'] else 1)
