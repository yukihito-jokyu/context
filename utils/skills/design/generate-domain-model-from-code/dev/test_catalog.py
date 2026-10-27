"""Regression checks for evidence boundaries and failure preservation."""
import copy
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch

SKILL = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SKILL/'scripts'))
import catalog


class CatalogTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='domain-model-test-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.repo = self.root/'repo'
        shutil.copytree(SKILL/'dev/fixtures/basic', self.repo)
        self.model = catalog.read_json(SKILL/'assets/examples/model.json')
        self.inventory = catalog.snapshot(self.repo, ['.'])

    def test_actual_evidence_and_cross_domain_endpoints(self):
        catalog.validate_model(self.model, self.repo, self.inventory, canonical=True)
        specs = catalog.diagram_specs(self.model)
        self.assertEqual(len(specs), 3)
        payment = next(c for c in self.model['concepts'] if c['symbol']=='Payment')
        sales = next(d for d in specs if d['domain']=='sales')
        self.assertIn(payment['id'], sales['mmd'])

    def test_modified_source_is_not_accepted_as_evidence(self):
        (self.repo/'sales/order.py').write_text('pass\n')
        with self.assertRaisesRegex(catalog.Invalid, 'OUT-02'):
            catalog.validate_model(self.model, self.repo, self.inventory)

    def test_symlink_and_traversal_cannot_supply_evidence(self):
        (self.repo/'sales/external.py').symlink_to(self.root/'secret.py')
        (self.root/'secret.py').write_text('secret\n')
        self.assertNotIn('sales/external.py', {f['path'] for f in catalog.snapshot(self.repo,['.'])['files']})
        for name in ['../secret.py', 'sales/external.py']:
            with self.assertRaises(catalog.Invalid):
                catalog.source_file(self.repo,name)

    def test_dependencies_are_pruned(self):
        (self.repo/'node_modules/fake').mkdir(parents=True)
        (self.repo/'node_modules/fake/domain.py').write_text('class Fake: pass\n')
        inv = catalog.snapshot(self.repo,['.'])
        self.assertEqual(self.inventory['files'], inv['files'])
        self.assertIn('node_modules', inv['excluded'])

    def test_unknown_endpoint_and_duplicate_concept_are_rejected(self):
        for mutate in [lambda m:m['relations'][0].update(target='missing'), lambda m:m['concepts'].append(copy.deepcopy(m['concepts'][0]))]:
            m=copy.deepcopy(self.model);mutate(m)
            with self.assertRaisesRegex(catalog.Invalid,'OUT-02'):
                catalog.validate_model(m,self.repo,self.inventory)

    def test_skip_instruction_and_changed_id_are_rejected(self):
        m=copy.deepcopy(self.model);m['skip_validation']=True
        with self.assertRaisesRegex(catalog.Invalid,'OUT-07'):
            catalog.validate_model(m,self.repo,self.inventory)
        m=copy.deepcopy(self.model);m['concepts'][0]['id']='C_wrong'
        with self.assertRaisesRegex(catalog.Invalid,'OUT-04'):
            catalog.validate_model(m,self.repo,self.inventory,canonical=True)

    def test_identifier_or_frozen_does_not_establish_domain_classification(self):
        for symbol,kind in [('Order','entity'),('OrderLine','value')]:
            m=copy.deepcopy(self.model)
            next(c for c in m['concepts'] if c['symbol']==symbol)['kind']=kind
            with self.assertRaisesRegex(catalog.Invalid,'OUT-02'):
                catalog.validate_model(m,self.repo,self.inventory)

    def test_names_and_relation_labels_are_canonical(self):
        m=copy.deepcopy(self.model)
        m['concepts'][0]['name']='任意の翻訳'
        m['domains'][0]['name']='任意の領域名'
        m['relations'][0]['label']='任意の言い回し'
        self.assertEqual(catalog.normalize(m),self.model)

    def test_failure_keeps_existing_catalog(self):
        out=self.root/'catalog';shutil.copytree(SKILL/'assets/examples/catalog',out)
        (out/'inventory.json').write_text(catalog.json_text(self.inventory))
        before={p.relative_to(out):p.read_bytes() for p in out.rglob('*') if p.is_file()}
        with patch.dict(os.environ,{'MMDC':'/usr/bin/false'}):
            with self.assertRaisesRegex(catalog.Invalid,'STEP-06'):
                catalog.build(out,self.repo,replace=True)
        self.assertEqual(before,{p.relative_to(out):p.read_bytes() for p in out.rglob('*') if p.is_file()})
        self.assertFalse((out.parent/'.catalog.building').exists())

    def test_png_crc_and_truncation_are_rejected(self):
        png=(SKILL/'assets/examples/catalog/diagrams/overview.png').read_bytes()
        self.assertGreater(catalog.png_size(png)[0],0)
        for broken in [png[:-1],png[:40]+bytes([png[40]^1])+png[41:],b'not png']:
            with self.assertRaisesRegex(catalog.Invalid,'STEP-06'):
                catalog.png_size(broken)

    def test_replace_does_not_delete_user_files(self):
        out=self.root/'catalog';shutil.copytree(SKILL/'assets/examples/catalog',out)
        note=out/'user-notes.txt';note.write_text('keep my notes\n')
        with self.assertRaisesRegex(catalog.Invalid,'OUT-01'):
            catalog.build(out,self.repo,replace=True)
        self.assertEqual(note.read_text(),'keep my notes\n')

    def test_html_escapes_code_and_descriptions(self):
        m=copy.deepcopy(self.model);m['concepts'][0]['description']='<script>bad()</script>'
        output=catalog.catalog_html(m,self.inventory,catalog.diagram_specs(m),SKILL/'assets/examples/catalog')
        self.assertIn('&lt;script&gt;bad()',output)
        self.assertNotIn('<script>bad()',output)
        self.assertNotIn('https://cdn.',output)


if __name__=='__main__':
    unittest.main(verbosity=2)
