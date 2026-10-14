#!/usr/bin/env python3
"""Completion CLI: ownership contract plus mandatory Archify reproduction.
The check() helper checks declarations only, not completion or agent identity.
"""
import argparse
import json
from pathlib import Path
from urllib.parse import urlparse

REQUIRED = ('research', 'design', 'model', 'figure', 'explanation', 'review')

def check(manifest, root, observed=None):
    issues=[];ids=set();agents=set();root=Path(root).resolve()
    rows=manifest.get('diagrams',[]) if isinstance(manifest,dict) else []
    if not rows:issues.append('No diagram owners declared')
    for row in rows:
        if not isinstance(row,dict):issues.append('Invalid diagram row');continue
        did,aid=row.get('id'),row.get('agent_id')
        if not isinstance(did,str) or not did.strip() or did in ids:
            issues.append('Missing or duplicate diagram ID: '+str(did))
        if not isinstance(aid,str) or not aid.strip() or aid in agents:
            issues.append('Missing or reused agent ID: '+str(aid))
        if isinstance(did,str):ids.add(did)
        if isinstance(aid,str):agents.add(aid)
        if observed is not None and aid not in observed:
            issues.append('Agent not present in supplied observed list: '+str(aid))
        if row.get('assigned_diagram_ids') != [did]:
            issues.append(str(did)+': agent must own exactly this one logical diagram')
        if row.get('status')!='complete':issues.append(str(did)+': diagram is not complete')
        outputs=row.get('outputs',{});paths={}
        for key in REQUIRED:
            value=outputs.get(key) if isinstance(outputs,dict) else None
            if not isinstance(value,str) or not value.strip():
                issues.append(str(did)+': missing '+key);continue
            path=(root/value).resolve()
            if not path.is_relative_to(root) or not path.is_file() or not path.read_bytes().strip():
                issues.append(str(did)+': missing/empty/outside-root '+key);continue
            paths[key]=path
        if 'research' in paths:
            try:
                sources=json.loads(paths['research'].read_text()).get('sources',[])
                if not sources:raise ValueError('No sources')
                for source in sources:
                    if (urlparse(source.get('url','')).scheme not in ('http','https')
                            or not urlparse(source.get('url','')).netloc
                            or any(not isinstance(source.get(k),str) or not source[k].strip()
                                   for k in ('checked_at','finding','location'))):
                        raise ValueError('Missing researched findings')
            except (ValueError,TypeError,AttributeError):
                issues.append(str(did)+': research needs visited URLs/date/findings/locations')
        if 'explanation' in paths:
            prose=paths['explanation'].read_text()
            if not all(token in prose for token in ('data-diagram-intro','data-diagram-reading','data-diagram-explanation','data-diagram-conditions')):
                issues.append(str(did)+': explanation needs intro/reading/explanation/conditions sections')
    return {'pass':not issues,'diagrams':len(ids),'agents':len(agents),'issues':issues,
            'limit':'Checks declarations and files. Verify actual spawn/network tool records and content separately.'}

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('manifest',type=Path)
    p.add_argument('--article',type=Path,required=True,help='Final HTML; Archify reproduction is mandatory')
    p.add_argument('--observed-agents',type=Path,help='JSON list of agent IDs from actual orchestration records')
    a=p.parse_args();observed=json.loads(a.observed_agents.read_text()) if a.observed_agents else None
    result=check(json.loads(a.manifest.read_text()),a.manifest.parent,observed)
    from check_archify import check as check_archify
    try:
        root=a.manifest.resolve().parent
        if not a.article.resolve().is_relative_to(root):raise ValueError('Article must be inside manifest root')
        result['archify']=check_archify(json.loads(a.manifest.read_text()),root,a.article.read_text())
    except (ValueError,OSError) as exc:result['archify']={'pass':False,'issues':[str(exc)]}
    result['pass']=result['pass'] and result['archify']['pass']
    print(json.dumps(result,ensure_ascii=False,indent=2));raise SystemExit(0 if result['pass'] else 1)
