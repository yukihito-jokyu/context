"""Compare code-backed concepts and relationships across independent runs."""
import argparse
import itertools
import hashlib
import json
from pathlib import Path


def score(a,b):
    return 1.0 if not a and not b else round(len(a&b)/len(a|b),3)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--lab',type=Path,required=True)
    p.add_argument('--round',type=int,required=True)
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args()
    plan=json.loads((a.lab/f'round-{a.round}/plan.json').read_text())
    tasks=[]
    for task in plan['tasks']:
        runs=[]
        for run in plan['runs']:
            if run['task']!=task:continue
            state_path=Path(run['dir'])/'.skill-runs/generate-domain-model/state.json'
            if not state_path.exists():
                runs.append(dict(id=run['id'],status='unused'));continue
            state=json.loads(state_path.read_text())
            model_path=state_path.parent/'out'/state['input']['name']/'model.json'
            if not model_path.exists():
                runs.append(dict(id=run['id'],status=state['status']));continue
            m=json.loads(model_path.read_text())
            diagram_dir=model_path.parent/'diagrams'
            diagram_hashes={suffix:{f.name:hashlib.sha256(f.read_bytes()).hexdigest() for f in sorted(diagram_dir.glob('*'+suffix))} for suffix in ['.mmd','.png']}
            runs.append(dict(id=run['id'],status=state['status'],
                concepts=sorted([(c['key'],c['kind'],tuple(sorted((v['name'],v['type']) for v in c['attributes']))) for c in m['concepts']]),
                relations=sorted([(r['source'],r['target'],r['kind'],r['source_multiplicity'],r['target_multiplicity']) for r in m['relations']],key=repr),
                labels=sorted([(r['source'],r['target'],r['label']) for r in m['relations']]),
                classifications={c['key']:c['kind'] for c in m['concepts']},diagram_hashes=diagram_hashes,catalog_complete=(model_path.parent/'manifest.json').is_file()))
        pairs=[]
        for x,y in itertools.combinations([r for r in runs if 'concepts' in r],2):
            pairs.append(dict(a=x['id'],b=y['id'],concepts=score(set(x['concepts']),set(y['concepts'])),relations=score(set(x['relations']),set(y['relations'])),classification_difference={key:[x['classifications'].get(key),y['classifications'].get(key)] for key in set(x['classifications'])|set(y['classifications']) if x['classifications'].get(key)!=y['classifications'].get(key)},label_text_equal=x['labels']==y['labels'],mermaid_equal=(x['diagram_hashes']['.mmd']==y['diagram_hashes']['.mmd']) if x['catalog_complete'] and y['catalog_complete'] else None,png_equal=(x['diagram_hashes']['.png']==y['diagram_hashes']['.png']) if x['catalog_complete'] and y['catalog_complete'] else None))
        tasks.append(dict(id=task,runs=runs,pairs=pairs))
    result=dict(round=a.round,tasks=tasks,limits='説明文の意味同一性と画像の可読性は自動採点しない。processの終了コードとSkillのdoneを区別する。')
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps([dict(id=t['id'],runs=len(t['runs']),all_done=all(r['status']=='done' for r in t['runs']),min_concepts=min((v['concepts'] for v in t['pairs']),default=None),min_relations=min((v['relations'] for v in t['pairs']),default=None),all_mermaid_equal=all(v['mermaid_equal'] for v in t['pairs'] if v['mermaid_equal'] is not None) if any(v['mermaid_equal'] is not None for v in t['pairs']) else None,all_png_equal=all(v['png_equal'] for v in t['pairs'] if v['png_equal'] is not None) if any(v['png_equal'] is not None for v in t['pairs']) else None) for t in tasks],ensure_ascii=False))


if __name__=='__main__':main()
