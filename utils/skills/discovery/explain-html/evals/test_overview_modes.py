import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from render_html import render
from check_overviews import Check
class OverviewModes(unittest.TestCase):
 def model(self,**extra):
  return {'title':'出典確認','scope':'原文と確認日','pages':[{'id':'sources','label':'資料','overview_html':'<div data-concern-overview="sources"><p>原文と確認範囲を確認できます。</p><a href="#references">原文へ</a></div>','body_html':'<p id="references">資料</p>',**extra}]}
 def inspect(self,model):
  check=Check();check.feed(render(model));return check.result()
 def test_justified_reference_page_can_use_text_without_inventing_a_graph(self):
  self.assertTrue(self.inspect(self.model(overview_mode='text',overview_reason='資料名と確認日の列挙。新しい関係を説明しない。'))['pass'])
 def test_text_mode_requires_an_explicit_reason(self):
  with self.assertRaises(ValueError):render(self.model(overview_mode='text'))
  with self.assertRaises(ValueError):render(self.model(overview_mode='unknown'))
 def test_diagram_pages_still_require_their_image(self):
  self.assertFalse(self.inspect(self.model())['pass'])
