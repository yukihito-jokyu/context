"""Refresh genuine positive outputs and prose-only review counterexamples."""
import copy
import json
from pathlib import Path
import sys

r=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(r/'scripts'))
import catalog
base=r/'assets/examples/catalog'
doc=catalog.read_json(r/'dev/probes.json')
doc['baseline']['files']=[dict(path='{run}/out/{in:name}/'+p.relative_to(base).as_posix(),**{'from':'assets/examples/catalog/'+p.relative_to(base).as_posix()}) for p in sorted(base.rglob('*')) if p.is_file()]
m=catalog.read_json(base/'model.json');inv=catalog.read_json(base/'inventory.json')
for review in doc['reviews']:
    model=copy.deepcopy(m)
    next(c for c in model['concepts'] if c['symbol']=='Payment')['description']='Stores the target order and amount.' if review['rule']=='OUT-03' else '支払いは対象注文を削除する。'
    texts={'model.json':catalog.json_text(model),'index.html':catalog.catalog_html(model,inv,catalog.diagram_specs(model),base)}
    manifest=catalog.read_json(base/'manifest.json')
    for name,value in texts.items():manifest['files'][name]=catalog.digest(value.encode())
    texts['manifest.json']=catalog.json_text(manifest)
    review['files']=[dict(path='{run}/out/{in:name}/'+name,content=value) for name,value in sorted(texts.items())]
(r/'dev/probes.json').write_text(json.dumps(doc,ensure_ascii=False,indent=2)+'\n')
