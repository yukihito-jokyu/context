"""新しいレンダラーでreviewの見本を再生成する。検査は変更しない。"""
import argparse
import importlib.util
import json
from pathlib import Path
import shutil
import tempfile

parser=argparse.ArgumentParser();parser.add_argument('skill');args=parser.parse_args()
s=Path(args.skill).resolve()
spec=importlib.util.spec_from_file_location('detailed_design',s/'scripts/design.py')
design=importlib.util.module_from_spec(spec);spec.loader.exec_module(design)
probes=json.loads((s/'dev/probes.json').read_text())
baseline=json.loads((s/'assets/examples/design.json').read_text())
shutil.rmtree(s/'assets/examples/review_fixtures',ignore_errors=True)
with tempfile.TemporaryDirectory(prefix='detailed-review-build-') as temp:
 root=Path(temp);shutil.copytree(s/'assets/sample-input',root/'docs');out=root/'docs/detailed-design';out.mkdir()
 (out/'design.json').write_text(json.dumps(baseline,ensure_ascii=False,indent=2)+'\n')
 request=argparse.Namespace(root=str(root),directory=str(out),source=[])
 assert design.render(request)==0
 baseline_images={p.relative_to(out).as_posix():p.read_bytes() for p in (out/'diagrams').iterdir()}
 baseline_docs=design.render_documents(baseline,root)
 for row in probes['reviews']:
  data=json.loads(next(f['content'] for f in row['files'] if f['path'].endswith('/design.json')))
  (out/'design.json').write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
  assert design.render(request)==0
  docs=design.render_documents(data,root)
  files=[{'path':'{in:output_dir}/design.json','content':json.dumps(data,ensure_ascii=False,indent=2)+'\n'}]
  files += [{'path':'{in:output_dir}/'+name,'content':body} for name,body in docs.items() if body != baseline_docs[name]]
  present={p.relative_to(out).as_posix() for p in (out/'diagrams').iterdir()}
  files += [{'path':'{in:output_dir}/'+rel,'mode':'delete'} for rel in baseline_images if rel not in present]
  # PNGは環境によってサブピクセル描画が変わる。差分だけでなく一つの生成の全組を保存する。
  import hashlib
  for path in sorted((out/'diagrams').iterdir()):
   rel=path.relative_to(out).as_posix();raw=path.read_bytes()
   artifact=s/'assets/examples/review_fixtures'/(hashlib.sha256(raw).hexdigest()+path.suffix)
   artifact.parent.mkdir(parents=True,exist_ok=True);artifact.write_bytes(raw)
   files.append({'path':'{in:output_dir}/'+rel,'from':artifact.relative_to(s).as_posix()})
  row['files']=files
  # 次の違反例の基準は常に正常な見本へ戻す。
  for path in (out/'diagrams').iterdir():
   if path.relative_to(out).as_posix() not in baseline_images:path.unlink()
  for rel,raw in baseline_images.items():(out/rel).write_bytes(raw)
  for name,body in baseline_docs.items():(out/name).write_text(body)
  print(row['id'],len(files),'files')
(s/'dev/probes.json').write_text(json.dumps(probes,ensure_ascii=False,indent=2)+'\n')

spec_path=s/'dev/spec.json'
spec_data=json.loads(spec_path.read_text())
spec_data['examples']=[x for x in spec_data['examples'] if not x['path'].startswith('review_fixtures/')]+[{'path':str(f.relative_to(s/'assets/examples')),'shows':['OUT-16']} for f in sorted((s/'assets/examples/review_fixtures').iterdir())]
spec_path.write_text(json.dumps(spec_data,ensure_ascii=False,indent=2)+'\n')

# 正常な見本のPNG組も配置し、反復検査では一致する実変換済みPNGを再利用する。
# OUT-03は入口の文章だけの違反であり図の内容を変えない。
normal_images=[x for x in probes['reviews'][0]['files'] if x.get('from') and '/diagrams/' in x['path']]
probes['baseline']['files']=[x for x in probes['baseline']['files'] if '/diagrams/' not in x['path']]+normal_images
(s/'dev/probes.json').write_text(json.dumps(probes,ensure_ascii=False,indent=2)+'\n')
