"""Markdownの可搬性と、欠落・改変を拒否する出力検査を確認する。

実行: python3 -m unittest discover -s utils/skills/documentation/write-basic-design-document/dev -p 'test_*.py'
"""
import copy
import importlib.util
import json
from pathlib import Path
import re
import shutil
import tempfile
import unittest


SKILL = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('document', SKILL / 'scripts/document.py')
document = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(document)


class MarkdownOutputTest(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.out = Path(self.temporary.name) / 'out'
        shutil.copytree(SKILL / 'assets/examples', self.out)
        self.source = self.out / 'basic-design-document.json'
        self.data = document.read_json(self.source)
        self.manifest = document.read_json(self.out / 'manifest.json')

    def test_both_documents_pass_and_markdown_links_resolve(self):
        self.assertEqual(document.check(self.source, self.out), [])
        markdown = (self.out / 'basic-design-document.md').read_text()
        headings = re.findall(r'^#{2,3} (.+)$', markdown, re.M)
        self.assertNotIn('<a ', markdown)
        self.assertIn('## 3. 全体構成', markdown)
        self.assertIn('### 3.1 ', markdown)
        self.assertIn('| 用語 | 意味 | 根拠 |', markdown)
        self.assertIn('| 利用者 | 行うこと | 根拠 |', markdown)
        self.assertIn('要点：', markdown)
        self.assertIn('採用理由：', markdown)
        anchors = {re.sub(r'[^\w -]', '', heading.lower()).replace(' ', '-') for heading in headings}
        for link in re.findall(r'\]\(([^)]+)\)', markdown):
            if link.startswith('#'):
                self.assertIn(link[1:], anchors)
            else:
                self.assertTrue((self.out / link).is_file(), link)
        self.assertEqual(len(re.findall(r'^!\[', markdown, re.M)), len(self.data['diagrams']))
        for text in (self.data['designs'][0]['reason'], self.data['open_questions'][0]['consequence'], self.data['handoff'][-1]):
            self.assertIn(document.md(text), markdown)

    def test_missing_markdown_is_not_complete(self):
        (self.out / 'basic-design-document.md').unlink()
        self.assertTrue(any(x.startswith('OUT-01 ') for x in document.check(self.source, self.out)))

    def test_changed_markdown_is_rejected_even_with_matching_manifest_hash(self):
        path = self.out / 'basic-design-document.md'
        path.write_text(path.read_text() + '\n原本にない決定。\n')
        self.manifest['markdown_sha256'] = document.sha(path)
        document.write_json(self.out / 'manifest.json', self.manifest)
        self.assertTrue(any(x.startswith('OUT-06 ') for x in document.check(self.source, self.out)))

    def test_prose_stays_literal_and_multiline_quote_stays_a_quote(self):
        data = copy.deepcopy(self.data)
        data['summary'] = '[採用済み](https://example.invalid) <script>alert(1)</script> *案*'
        data['sources'][0]['quote'] = '一行目\n# 二行目 [条件]\n> 三行目'
        markdown = document.render_markdown(data, self.manifest)
        self.assertNotIn('<script>', markdown)
        self.assertNotIn('[採用済み](', markdown)
        self.assertIn('\\[採用済み\\]\\(https://example.invalid\\)', markdown)
        self.assertIn('> 一行目\n> \\# 二行目 \\[条件\\]\n> &gt; 三行目', markdown)

    def test_english_headings_and_optional_empty_lists(self):
        data = copy.deepcopy(self.data)
        data['language'] = 'en'
        data['open_questions'] = []
        for key in ('coverage', 'designs', 'quality'):
            for row in data[key]:
                row['question_ids'] = []
        markdown = document.render_markdown(data, self.manifest)
        self.assertIn('## 1. Overview', markdown)
        self.assertIn('No open questions are recorded.', markdown)
        self.assertIn('Detailed design handoff', markdown)

    def test_multiline_table_cells_do_not_add_columns_or_rows(self):
        data = copy.deepcopy(self.data)
        data['terms'][0]['definition'] = '開始 | 終了\n境界の条件'
        markdown = document.render_markdown(data, self.manifest)
        self.assertIn('開始 \\| 終了<br>境界の条件', markdown)


if __name__ == '__main__':
    unittest.main()
