"""Check correspondence, not semantic correctness. Unknowns must stay unknown."""
import argparse,json
from pathlib import Path
from html.parser import HTMLParser
from collections import Counter
class Page(HTMLParser):
 def __init__(self):super().__init__();self.ids=[]
 def handle_starttag(self,tag,attrs):
  a=dict(attrs)
  if 'id' in a:self.ids.append(a['id'])
parser=argparse.ArgumentParser();parser.add_argument('html',type=Path);parser.add_argument('coverage',type=Path);args=parser.parse_args()
p=Page();p.feed(args.html.read_text());coverage=json.loads(args.coverage.read_text());items=coverage['items'];keys=[x['key'] for x in items];ids=set(p.ids)
known_states={'explained','name_only','link_only','missing','unverified','explicitly_out_of_scope'}
report={'source_count':len(coverage.get('sources',[])),'items':len(items),'states':dict(Counter(x['status'] for x in items)),'missing_targets':[x['key'] for x in items if x.get('target_id') not in ids],'duplicate_ids':[x for x,n in Counter(p.ids).items() if n>1],'duplicate_keys':[x for x,n in Counter(keys).items() if n>1],'bad_states':[x['key'] for x in items if x['status'] not in known_states],'missing_sources':[x['key'] for x in items if not x.get('source_url')],'unfinished':[x['key'] for x in items if x['status']!='explained'],'semantic_review_required':True,'note':'Matching targets and explained labels do not prove source completeness or semantic correctness. Review original headings, reference rows, defaults, conditions and exceptions.'}
report['structural_match']=not any(report[k] for k in ['missing_targets','duplicate_ids','duplicate_keys','bad_states','missing_sources'])
report['all_items_marked_explained']=not report['unfinished'];print(json.dumps(report,ensure_ascii=False,indent=2))
raise SystemExit(0 if report['structural_match'] and report['all_items_marked_explained'] else 1)
