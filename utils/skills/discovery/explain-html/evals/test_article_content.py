import sys
from pathlib import Path
import unittest
import json
import subprocess
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
from check_article_content import check


class ArticleContent(unittest.TestCase):
    def test_markup_changes_and_closed_details_retain_exact_decoded_code(self):
        before = '<pre><span class="code-line" id="line-1">  x &lt; y</span>\n</pre>'
        after = '<details><summary>コード</summary><pre><span id="line-1" class="code-line"><code>  x &#60; y</code></span>\n</pre></details><a href="#line%2D1">行へ</a>'
        self.assertTrue(check(before, after)['pass'])

    def test_plain_snippet_removal_and_code_line_whitespace_change_fail(self):
        before = '<pre>{"decision":"deny"}</pre><pre><span class="code-line" id="l">  x</span></pre>'
        after = '<pre><span class="code-line" id="l"> x</span></pre>'
        result = check(before, after)
        self.assertFalse(result['pass'])
        self.assertIn('{"decision":"deny"}', result['missing_code_blocks'])
        self.assertEqual(result['changed_or_missing_code_lines'], ['l'])

    def test_duplicate_ids_and_missing_anchor_fail(self):
        result = check('', '<p id="same"></p><input id="same"><a href="#absent">参照</a>')
        self.assertFalse(result['pass'])
        self.assertEqual(result['duplicate_ids'], ['same'])
        self.assertEqual(result['missing_anchors'], ['absent'])

    def test_baseline_failure_does_not_overwrite_an_existing_article(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root/'before.html').write_text('<pre>retained = True</pre>')
            (root/'output.html').write_text('existing reviewed output')
            (root/'manifest.json').write_text('{}')
            (root/'page.json').write_text(json.dumps({'title': '説明', 'scope': '確認',
                'pages': [{'id': 'overview', 'label': '全体像',
                           'overview_html': '<p>図</p>', 'body_html': '<p>説明</p>'}]}))
            result = subprocess.run([sys.executable,
                str(Path(__file__).resolve().parents[1]/'scripts/render_html.py'),
                str(root/'page.json'), str(root/'output.html'),
                '--manifest', str(root/'manifest.json'),
                '--baseline', str(root/'before.html')], capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('content_retention', result.stdout)
            self.assertEqual((root/'output.html').read_text(), 'existing reviewed output')
