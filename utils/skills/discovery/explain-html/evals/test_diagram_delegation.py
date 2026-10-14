import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from check_diagram_delegation import check

class DelegationContractTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
        for name in ('design','model','figure','review'):(self.root/(name+'.txt')).write_text('Authored content')
        (self.root/'research.json').write_text(json.dumps({'sources':[{'url':'https://example.org/spec','checked_at':'2026-10-13','finding':'A change cleans the old connection before starting the new one','location':'Re-synchronization section'}]}))
        (self.root/'explanation.html').write_text('<p data-diagram-intro>Input</p><p data-diagram-reading>Read</p><p data-diagram-explanation>Change</p><p data-diagram-conditions>Condition</p>')
        self.row={'id':'room-change','agent_id':'/root/figure1','assigned_diagram_ids':['room-change'],'status':'complete',
                  'outputs':{'research':'research.json','explanation':'explanation.html',**{name:name+'.txt' for name in ('design','model','figure','review')}}}
    def tearDown(self):self.temp.cleanup()
    def inspect(self,rows,observed=None):return check({'diagrams':rows},self.root,observed)
    def test_one_diagram_owner_with_a_complete_bundle(self):
        self.assertTrue(self.inspect([self.row],['/root/figure1'])['pass'])
        self.assertFalse(self.inspect([self.row],['/root/someone-else'])['pass'])
    def test_one_agent_cannot_claim_a_second_diagram(self):
        second=copy.deepcopy(self.row);second.update(id='other',assigned_diagram_ids=['other'])
        self.assertFalse(self.inspect([self.row,second])['pass'])
        self.row['assigned_diagram_ids'].append('other')
        self.assertFalse(self.inspect([self.row])['pass'])
    def test_starting_an_agent_is_not_a_completed_diagram(self):
        self.row['status']='running';self.assertFalse(self.inspect([self.row])['pass'])
    def test_network_source_without_concrete_findings_is_rejected(self):
        (self.root/'research.json').write_text('{"sources":[{"url":"https://example.org/spec"}]}')
        self.assertFalse(self.inspect([self.row])['pass'])
    def test_explanation_and_inside_root_outputs_are_required(self):
        (self.root/'explanation.html').write_text('A generic caption')
        self.assertFalse(self.inspect([self.row])['pass'])
        self.row['outputs']['figure']='../outside.html';self.assertFalse(self.inspect([self.row])['pass'])

if __name__=='__main__':unittest.main()
