import base64
import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SKILL=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(SKILL/'scripts'))
from check_archify import check, command

class ArchifyGateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp=tempfile.TemporaryDirectory();cls.root=Path(cls.tmp.name)
        model=json.loads((SKILL/'vendor/archify-jp/examples/cache-miss-request.sequence.json').read_text())
        model['meta']['visual_preset']='editorial';model['meta'].pop('output',None);model['meta'].pop('animation',None)
        (cls.root/'model.json').write_text(json.dumps(model,ensure_ascii=False,indent=2))
        receipt=command(['node',str(SKILL/'vendor/archify-jp/bin/archify.mjs'),'deliver','sequence',str(cls.root/'model.json'),str(cls.root/'figure.html'),'--quality','showcase','--json'])
        (cls.root/'receipt.json').write_text(json.dumps(receipt))
        command([sys.executable,str(SKILL/'scripts/export_standard_svg.py'),str(cls.root/'figure.html'),str(cls.root/'figure.svg'),'--model',str(cls.root/'model.json')])
        cls.original={n:(cls.root/n).read_bytes() for n in ['model.json','figure.html','figure.svg','receipt.json']}
        cls.row={'id':'cache','status':'complete','outputs':{'model':'model.json','figure':'figure.html'},'archify':{'type':'sequence','viewer':'figure.html','svg':'figure.svg','receipt':'receipt.json'}}
        cls.article='<img data-archify-model-sha256="'+receipt['specification']['sha256']+'" src="data:image/svg+xml;base64,'+base64.b64encode(cls.original['figure.svg']).decode()+'">'
        alternate=copy.deepcopy(model);alternate['meta']['title']='別の局所投影（検査fixture）'
        (cls.root/'variant.json').write_text(json.dumps(alternate,ensure_ascii=False,indent=2))
        alternate_receipt=command(['node',str(SKILL/'vendor/archify-jp/bin/archify.mjs'),'deliver','sequence',str(cls.root/'variant.json'),str(cls.root/'variant.html'),'--quality','showcase','--json'])
        (cls.root/'variant-receipt.json').write_text(json.dumps(alternate_receipt))
        command([sys.executable,str(SKILL/'scripts/export_standard_svg.py'),str(cls.root/'variant.html'),str(cls.root/'variant.svg'),'--model',str(cls.root/'variant.json')])
        cls.variant={'id':'detail','reason':'独立した局所投影の検査fixture','type':'sequence','model':'variant.json','viewer':'variant.html','svg':'variant.svg','receipt':'variant-receipt.json'}
        cls.variant_article='<img data-archify-model-sha256="'+alternate_receipt['specification']['sha256']+'" src="data:image/svg+xml;base64,'+base64.b64encode((cls.root/'variant.svg').read_bytes()).decode()+'">'
        cls.original.update({n:(cls.root/n).read_bytes()for n in ['variant.json','variant.html','variant.svg','variant-receipt.json']})
    @classmethod
    def tearDownClass(cls):cls.tmp.cleanup()
    def setUp(self):
        for n,b in self.original.items():(self.root/n).write_bytes(b)
    def verify(self,row=None,article=None):return check({'diagrams':[row or self.row]},self.root,self.article if article is None else article)
    def test_real_delivery_and_standard_export_pass(self):self.assertTrue(self.verify()['pass'])
    def test_native_svg_and_self_declared_renderer_are_rejected(self):
        row=copy.deepcopy(self.row);row.pop('archify');row['renderer']='archify'
        self.assertFalse(self.verify(row)['pass'])
    def test_viewer_tamper_with_forged_hash_is_rejected_by_reproduction(self):
        from check_archify import sha
        raw=self.original['figure.html'].replace('キャッシュ'.encode(),'変更後'.encode(),1)
        (self.root/'figure.html').write_bytes(raw)
        r=json.loads(self.original['receipt.json']);r['artifact']['sha256']=sha(raw);(self.root/'receipt.json').write_text(json.dumps(r))
        self.assertFalse(self.verify()['pass'])
    def test_model_svg_and_receipt_drift_rejected(self):
        for name in ['model.json','figure.svg','receipt.json']:
            with self.subTest(name=name):
                self.setUp();(self.root/name).write_bytes(self.original[name]+b' ')
                # Whitespace in receipt alone is harmless; alter its actual hash.
                if name=='receipt.json':
                    r=json.loads(self.original[name]);r['specification']['sha256']='0'*64;(self.root/name).write_text(json.dumps(r))
                self.assertFalse(self.verify()['pass'])
    def test_article_substitution_missing_and_inline_graph_rejected(self):
        for article in ['', '<img src="data:image/svg+xml;base64,PHN2Zy8+">', self.article+'<svg></svg>',self.article+'<canvas></canvas>']:
            with self.subTest(article=article[:40]):self.assertFalse(self.verify(article=article)['pass'])
    def test_relative_local_standard_svg_accepted_and_escape_rejected(self):
        import re
        local=re.sub(r'src="[^"]+"','src="figure.svg"',self.article)
        self.assertTrue(self.verify(article=local)['pass'])
        row=copy.deepcopy(self.row);row['archify']['svg']='../figure.svg';self.assertFalse(self.verify(row)['pass'])
    def test_local_projection_is_reproduced_and_must_be_embedded(self):
        row=copy.deepcopy(self.row);row['archify_variants']=[self.variant]
        self.assertTrue(self.verify(row,self.article+self.variant_article)['pass'])
        self.assertFalse(self.verify(row,self.article)['pass'])
        (self.root/'variant.svg').write_bytes(self.original['variant.svg']+b' ')
        self.assertFalse(self.verify(row,self.article+self.variant_article)['pass'])
    def test_projection_cannot_reuse_a_primary_artifact_or_escape_paths(self):
        row=copy.deepcopy(self.row);variant=copy.deepcopy(self.variant);variant.update(model='model.json',viewer='figure.html',svg='figure.svg',receipt='receipt.json');row['archify_variants']=[variant]
        self.assertFalse(self.verify(row,self.article)['pass'])
        variant=copy.deepcopy(self.variant);variant['model']='../variant.json';row['archify_variants']=[variant]
        self.assertFalse(self.verify(row,self.article+self.variant_article)['pass'])
        variant=copy.deepcopy(self.variant);variant['reason']='';row['archify_variants']=[variant]
        self.assertFalse(self.verify(row,self.article+self.variant_article)['pass'])
    def full_bundle(self,root):
        row=copy.deepcopy(self.row);row.update(agent_id='/root/cache',assigned_diagram_ids=['cache'])
        for key in ['research','design','explanation','review']:row['outputs'][key]=key+'.txt'
        (root/'research.txt').write_text(json.dumps({'sources':[{'url':'https://example.org/spec','checked_at':'2026-10-14','finding':'Test fixture only','location':'fixture'}]}))
        for key in ['design','review']:(root/(key+'.txt')).write_text('Test fixture')
        (root/'explanation.txt').write_text('<p data-diagram-intro data-diagram-reading data-diagram-explanation data-diagram-conditions>Test fixture</p>')
        (root/'manifest.json').write_text(json.dumps({'diagrams':[row]}))
        return row
    def run_render(self,markup):
        self.full_bundle(self.root)
        model={'title':'T','scope':'S','pages':[{'id':'start','label':'Start','overview_html':markup,'body_html':''}]}
        (self.root/'page.json').write_text(json.dumps(model))
        return subprocess.run([sys.executable,str(SKILL/'scripts/render_html.py'),str(self.root/'page.json'),str(self.root/'old-output.html'),'--manifest',str(self.root/'manifest.json')],capture_output=True,text=True)
    def test_failed_render_does_not_replace_previous_output(self):
        p=self.root/'old-output.html';p.write_text('previous accepted output')
        run=self.run_render('<svg>independent renderer</svg>')
        self.assertNotEqual(run.returncode,0);self.assertEqual(p.read_text(),'previous accepted output')
        report=json.loads(run.stdout);self.assertTrue(report['delegation']['pass']);self.assertFalse(report['archify']['pass'])
    def test_real_diagram_passes_mandatory_render_cli(self):
        run=self.run_render(self.article);self.assertEqual(run.returncode,0,run.stdout+run.stderr)
        self.assertIn(self.article,(self.root/'old-output.html').read_text())

    def test_stop_hook_inactive_real_and_failed_projects(self):
        with tempfile.TemporaryDirectory() as d:
            project=Path(d);bundle=project/'plugin'
            repo=SKILL.parents[3]
            subprocess.run([sys.executable,str(repo/'utils/plugins/explain-html/build.py'),'--output',str(bundle)],check=True,capture_output=True)
            adapter=bundle/'scripts/archify_gate.py'
            def invoke(**extra):
                return subprocess.run([sys.executable,str(adapter)],input=json.dumps({'hook_event_name':'Stop','cwd':str(project),**extra}),text=True,capture_output=True)
            self.assertEqual(invoke().returncode,0)
            (project/'.explain-html-active.json').write_text(json.dumps({'manifest':'diagram-agent-manifest.json','article':'output.html'}))
            self.assertEqual(invoke().returncode,2)
            # A continuation must not silently bypass the rule.
            self.assertEqual(invoke(stop_hook_active=True).returncode,2)
            for n,b in self.original.items():(project/n).write_bytes(b)
            row=copy.deepcopy(self.row);row.update(agent_id='/root/cache',assigned_diagram_ids=['cache'])
            for key in ['research','design','explanation','review']:row['outputs'][key]=key+'.txt'
            (project/'research.txt').write_text(json.dumps({'sources':[{'url':'https://example.org/spec','checked_at':'2026-10-14','finding':'Test fixture only','location':'fixture'}]}))
            for key in ['design','review']:(project/(key+'.txt')).write_text('Test fixture')
            (project/'explanation.txt').write_text('<p data-diagram-intro data-diagram-reading data-diagram-explanation data-diagram-conditions>Test fixture</p>')
            (project/'diagram-agent-manifest.json').write_text(json.dumps({'diagrams':[row]}));(project/'output.html').write_text(self.article)
            self.assertEqual(invoke().returncode,0)
            (project/'output.html').write_text('<svg>independent renderer</svg>')
            self.assertEqual(invoke().returncode,2)

if __name__=='__main__':unittest.main()
