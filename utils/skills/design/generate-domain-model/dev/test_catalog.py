"""カタログの欠落・改ざん・更新失敗を検証する。python3 -m unittest discover -s dev。"""
import copy
import importlib.util
import json
from pathlib import Path
import shutil
import struct
import subprocess
import tempfile
import unittest
from unittest.mock import patch
import zlib

SKILL = Path(__file__).resolve().parent.parent
SPEC = importlib.util.spec_from_file_location("domain_catalog", SKILL / "scripts/catalog.py")
catalog = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(catalog)


class CatalogTests(unittest.TestCase):
    def setUp(self):
        self.workspace = tempfile.TemporaryDirectory()
        self.addCleanup(self.workspace.cleanup)
        self.root = Path(self.workspace.name) / "sample"
        shutil.copytree(SKILL / "assets/examples/sample", self.root)

    def test_real_rendered_bundle_passes(self):
        data = catalog.check(self.root)
        self.assertEqual(data["diagrams"][0]["id"], "order")

    def test_missing_png_is_rejected(self):
        (self.root / "images/order.png").unlink()
        with self.assertRaisesRegex(catalog.Finding, "ファイルがない"):
            catalog.check(self.root)

    def test_unregistered_file_is_rejected(self):
        (self.root / "diagrams/old.mmd").write_text("classDiagram\n")
        with self.assertRaisesRegex(catalog.Finding, "未登録"):
            catalog.check(self.root)

    def test_stale_source_is_rejected(self):
        source = self.root / "diagrams/order.mmd"
        source.write_text(source.read_text().replace('申し込む', '申請する'))
        with self.assertRaisesRegex(catalog.Finding, "SHA-256"):
            catalog.check(self.root)

    def test_stale_html_is_rejected(self):
        with (self.root / "index.html").open("a") as output:
            output.write("old")
        with self.assertRaisesRegex(catalog.Finding, "HTML"):
            catalog.check(self.root)

    def test_corrupt_png_is_rejected_even_with_updated_hash(self):
        path = self.root / "images/order.png"
        image = bytearray(path.read_bytes())
        image[-1] ^= 1
        path.write_bytes(image)
        record = catalog.read_json(self.root / "validation.json")
        record["files"]["images/order.png"] = catalog.digest(image)
        (self.root / "validation.json").write_text(catalog.dump(record))
        with self.assertRaisesRegex(catalog.Finding, "CRC"):
            catalog.check(self.root)

    def test_corrupt_pixel_data_with_valid_crc_is_rejected(self):
        def chunk(kind, data):
            return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data) & 0xffffffff)
        image = (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", 64, 64, 8, 6, 0, 0, 0))
                 + chunk(b"IDAT", zlib.compress(b"invalid")) + chunk(b"IEND", b""))
        with self.assertRaisesRegex(catalog.Finding, "画素"):
            catalog.png_size(image)

    def test_markup_is_escaped_in_catalog(self):
        data = catalog.load_catalog(self.root)
        data["title"] = '<img src=x onerror="alert(1)">@@CARDS@@'
        data["diagrams"][0]["sources"][0]["quote"] = '<script>alert(1)</script>'
        result = catalog.render_html(data)
        self.assertIn('&lt;img src=x onerror=', result)
        self.assertIn('@@CARDS@@', result)
        self.assertNotIn('<script>alert(1)</script>', result)
        self.assertEqual(result.count('<article '), 1)

    def test_duplicate_and_traversal_ids_are_rejected(self):
        original = catalog.load_catalog(self.root)
        for ident in ('../outside', 'Order', 'a/b'):
            data = copy.deepcopy(original)
            data["diagrams"][0]["id"] = ident
            (self.root / "catalog.json").write_text(catalog.dump(data))
            with self.assertRaises(catalog.Finding):
                catalog.load_catalog(self.root)

    def test_update_requires_explicit_flag(self):
        with self.assertRaisesRegex(catalog.Finding, '--update'):
            catalog.build(self.root)

    def test_duplicate_ids_are_rejected(self):
        data = catalog.load_catalog(self.root)
        data['diagrams'].append(copy.deepcopy(data['diagrams'][0]))
        (self.root / 'catalog.json').write_text(catalog.dump(data))
        with self.assertRaisesRegex(catalog.Finding, '重複'):
            catalog.load_catalog(self.root)

    def test_conversion_failure_preserves_published_bundle(self):
        before = {p.name: p.read_bytes() for p in [self.root / 'index.html', self.root / 'validation.json', self.root / 'images/order.png']}
        failure = subprocess.CompletedProcess([], 1, stdout='', stderr='parse error')
        with patch.object(catalog, 'renderer_command', return_value=('mmdc', 'test')):
            with patch.object(catalog.subprocess, 'run', return_value=failure):
                with self.assertRaisesRegex(catalog.Finding, '変換に失敗'):
                    catalog.build(self.root, update=True)
        after = {p.name: p.read_bytes() for p in [self.root / 'index.html', self.root / 'validation.json', self.root / 'images/order.png']}
        self.assertEqual(before, after)
        self.assertFalse(list(self.root.glob('.render-*')))
        catalog.check(self.root)

    def test_later_conversion_failure_does_not_publish_first_image(self):
        data = catalog.load_catalog(self.root)
        added = copy.deepcopy(data['diagrams'][0])
        added['id'] = 'payment'
        data['diagrams'].append(added)
        (self.root / 'catalog.json').write_text(catalog.dump(data))
        (self.root / 'diagrams/payment.mmd').write_text((self.root / 'diagrams/order.mmd').read_text())
        old_image = (self.root / 'images/order.png').read_bytes()
        payload = b'Test\0new image'
        extra = (struct.pack('>I', len(payload)) + b'tEXt' + payload
                 + struct.pack('>I', zlib.crc32(b'tEXt' + payload) & 0xffffffff))
        new_image = old_image[:-12] + extra + old_image[-12:]
        catalog.png_size(new_image)

        def render(command, **kwargs):
            if command[command.index('-i') + 1].endswith('order.mmd'):
                Path(command[command.index('-o') + 1]).write_bytes(new_image)
                return subprocess.CompletedProcess(command, 0, stdout='', stderr='')
            return subprocess.CompletedProcess(command, 1, stdout='', stderr='parse error')

        before = {name: (self.root / name).read_bytes() for name in ['index.html', 'validation.json']}
        with patch.object(catalog, 'renderer_command', return_value=('mmdc', 'test')):
            with patch.object(catalog.subprocess, 'run', side_effect=render):
                with self.assertRaisesRegex(catalog.Finding, 'payment'):
                    catalog.build(self.root, update=True)
        self.assertEqual((self.root / 'images/order.png').read_bytes(), old_image)
        self.assertFalse((self.root / 'images/payment.png').exists())
        self.assertEqual(before, {name: (self.root / name).read_bytes() for name in before})

    def test_dependency_error_does_not_install_packages(self):
        with patch.object(catalog.shutil, 'which', return_value=None):
            with self.assertRaisesRegex(catalog.Finding, 'mmdc がない'):
                catalog.renderer_command('missing-mmdc')

    def test_search_terms_come_from_concepts(self):
        self.assertEqual(catalog.concept_terms('classDiagram\n class User["利用者"]\n class User\n'),
                         ['利用者'])

    def test_quotations_from_same_file_have_one_source_entry(self):
        sources = [{'path': 'input.md:3', 'quote': '注文は顧客に属する。'},
                   {'path': 'input.md:1-2', 'quote': '顧客は注文する。'}]
        expected = [{'path': 'input.md:1-3', 'quote': '顧客は注文する。\n\n注文は顧客に属する。'}]
        self.assertEqual(catalog.canonical_sources(sources), expected)
        self.assertEqual(catalog.canonical_sources(expected), expected)

    def test_unchanged_diagram_reuses_verified_png(self):
        version = catalog.read_json(self.root / 'validation.json')['renderer']['version']
        before = (self.root / 'images/order.png').read_bytes()
        with patch.object(catalog, 'renderer_command', return_value=('mmdc', version)):
            with patch.object(catalog.subprocess, 'run') as render:
                catalog.build(self.root, update=True)
        render.assert_not_called()
        self.assertEqual((self.root / 'images/order.png').read_bytes(), before)

    def test_project_sources_use_portable_relative_paths(self):
        project = Path(self.workspace.name)
        absolute = str(project / 'library.mmd') + ':1-5'
        sources = [{'path': absolute, 'quote': '図書を貸し出す。'}]
        self.assertEqual(catalog.canonical_sources(sources, project),
                         [{'path': 'library.mmd:1-5', 'quote': '図書を貸し出す。'}])
        external = [{'path': '/external/spec.md:1', 'quote': '外部資料'}]
        self.assertEqual(catalog.canonical_sources(external, project), external)

    def test_url_ports_are_not_interpreted_as_line_numbers(self):
        sources = [{'path': 'https://example.test:8080', 'quote': '受注'},
                   {'path': 'https://example.test:9090', 'quote': '支払'}]
        self.assertEqual(catalog.canonical_sources(sources), sources)


if __name__ == '__main__':
    unittest.main()
