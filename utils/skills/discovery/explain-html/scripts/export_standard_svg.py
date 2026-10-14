"""Export a delivered supported Archify viewer through its unchanged SVG serializer.
This bounded offline DOM adapter is not a browser export or PNG screenshot.
"""
from pathlib import Path
import argparse, hashlib, json, re, subprocess
import xml.etree.ElementTree as etree
ROOT=Path(__file__).resolve().parents[1]
def css_rules(text):
 text=re.sub(r'/\*[\s\S]*?\*/','',text);rules=[];i=0
 while i<len(text):
  a=text.find('{',i)
  if a<0:break
  selector=text[i:a].strip();depth=1;j=a+1;quote=None
  while j<len(text) and depth:
   c=text[j]
   if quote:
    if c==quote and text[j-1]!='\\':quote=None
   elif c in ['"',"'"]:quote=c
   elif c=='{':depth+=1
   elif c=='}':depth-=1
   j+=1
  if not selector.startswith('@'):rules.append({'type':1,'selectorText':selector,'cssText':selector+' {'+text[a+1:j-1]+'}'})
  elif selector.startswith('@keyframes'):rules.append({'type':7,'name':selector.split()[1],'cssText':selector+' {'+text[a+1:j-1]+'}'})
  i=j
 return rules

def variables(rules,theme):
 vals={};priority={}
 for order,r in enumerate(rules):
  if r['type']!=1:continue
  eligible=[]
  for sel in r['selectorText'].split(','):
   sel=sel.strip()
   # Only root/probe selectors determine inherited theme variables.
   if not (sel==':root' or re.fullmatch(r'(?:svg)?(?:\[data-(?:theme|preset)="[^"]+"\])+',sel)):continue
   attrs=re.findall(r'\[data-(theme|preset)="([^"]+)"\]',sel)
   if any((k=='theme' and v!=theme) or (k=='preset' and v!='editorial') for k,v in attrs):continue
   eligible.append(len(attrs) or 1)
  if not eligible:continue
  specificity=max(eligible)
  for key,val in re.findall(r'(--[a-zA-Z0-9_-]+)\s*:\s*([^;{}]+);',r['cssText']):
   if (specificity,order)>=priority.get(key,(-1,-1)):vals[key]=val.strip();priority[key]=(specificity,order)
 return vals

def tree(e):
 children=[]
 if e.text:children.append(e.text)
 for c in e:
  if isinstance(c.tag,str):children.append(tree(c))
  if c.tail:children.append(c.tail)
 return {'tag':e.tag.rsplit('}',1)[-1],'attrs':dict(e.attrib),'children':children}

def main():
 parser=argparse.ArgumentParser(description=__doc__)
 parser.add_argument('viewer',type=Path);parser.add_argument('output',type=Path)
 parser.add_argument('--model',type=Path,required=True)
 args=parser.parse_args()
 package=json.loads((ROOT/'vendor/archify-jp/package.json').read_text())
 supported_versions={'2.16.0'}
 if package['version'] not in supported_versions:
  raise SystemExit('Unsupported Archify version. Review serializer compatibility before exporting.')
 template=(ROOT/'vendor/archify-jp/assets/template.html').read_text()
 start=template.find('      function serializeSvg(scale, opts) {');end=template.find('      function download(blob, filename)',start)
 if start<0 or end<start or hashlib.sha256(template[start:end].encode()).hexdigest()!='b2eeb9cc9aff53294f9fce5c37783dc401404f8acd003cbf8f2b036f951a9dfd':
  raise SystemExit('Archify standard serializer changed. Review adapter compatibility; do not simplify output.')
 model=json.loads(args.model.read_text())
 if model.get('meta',{}).get('visual_preset')!='editorial':raise SystemExit('Set meta.visual_preset to editorial and deliver again')
 doc=args.viewer.read_text();match=re.search(r'<svg\b[\s\S]*?</svg>',doc)
 if not match:raise SystemExit('No delivered SVG found')
 raw=match.group();svg=etree.fromstring(raw);rules=css_rules(re.search(r'<style>([\s\S]*?)</style>',doc).group(1))
 payload={'svg':tree(svg),'rules':rules,'variables':{t:variables(rules,t) for t in ['light','dark']}}
 result=subprocess.run(['node',str(ROOT/'scripts/standard_svg_export.mjs')],input=json.dumps(payload,ensure_ascii=False),capture_output=True,text=True,check=True)
 exported=json.loads(result.stdout);out=etree.fromstring(exported['svgString'])
 if svg.attrib['viewBox']!=out.attrib['viewBox']:raise SystemExit('Exporter changed viewBox')
 old_ids={n.attrib['data-node-id'] for n in svg.iter() if 'data-node-id' in n.attrib}
 new_ids={n.attrib['data-node-id'] for n in out.iter() if 'data-node-id' in n.attrib}
 if old_ids!=new_ids:raise SystemExit('Exporter lost nodes')
 args.output.parent.mkdir(parents=True,exist_ok=True)
 args.output.write_text(exported['svgString'])
 receipt={'method':'canonical-svg-offline-adapter','preset':'editorial','theme':'light','archify_version':package['version'],
          'model_sha256':hashlib.sha256(args.model.read_bytes()).hexdigest(),'svg_sha256':hashlib.sha256(args.output.read_bytes()).hexdigest(),
          'viewer_sha256':hashlib.sha256(args.viewer.read_bytes()).hexdigest(),'viewBox':out.attrib['viewBox'],
          'browser_export_verified':False,'pixel_equivalence_verified':False,'browser_canvas_png':False}
 args.output.with_suffix('.export.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n')
 print(json.dumps(receipt,ensure_ascii=False))
if __name__=='__main__':main()
