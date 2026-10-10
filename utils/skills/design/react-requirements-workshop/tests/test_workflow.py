"""Exercise a resumed review and approval using separate script processes."""
from __future__ import annotations
import json
import hashlib
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SKILL = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SKILL / 'scripts'))
from feedback import validate_payload  # noqa: E402


def fixture() -> dict:
    return {
        'snapshot': {'number': 1, 'slug': 'initial', 'label': '初期案'},
        'project': {'title': '依頼管理', 'subtitle': '確認'},
        'review_points': [{'number': 1, 'title': '主操作', 'description': '位置を確認する', 'target_key': 'action', 'status': 'pending', 'approval_history': []}],
        'fixed_annotations': [{'number': 1, 'target_key': 'action', 'padding_px': 8}],
        'screen_details': [{'number': 1, 'key': 'action', 'target_key': 'action', 'region': '上部', 'name': '登録', 'type': 'ボタン', 'description': '依頼の登録', 'capability': '登録を始める', 'behavior': 'screen_transition', 'trigger': 'クリック', 'result': '登録画面へ移動', 'failure': '失敗を表示'}],
        'requirements': {'purpose': ['依頼を管理する'], 'target_users': ['担当者'], 'confirmed': [], 'hypotheses': [], 'open_questions': [], 'deferred': [], 'next': []},
    }


def run(script: str, *arguments: str, success: bool = True):
    completed = subprocess.run([sys.executable, str(SKILL / 'scripts' / script), *arguments], text=True, capture_output=True)
    if success and completed.returncode:
        raise AssertionError(completed.stderr + completed.stdout)
    return completed


class WorkflowTest(unittest.TestCase):
    def test_resumed_feedback_and_immutable_approval(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'src/snapshots').mkdir(parents=True)
            (root / 'discussion').mkdir()
            source = root / 'src/snapshots/001-initial.tsx'
            source.write_text('export default function Snapshot() { return <button data-review-target="action" data-screen-detail-target="action">登録</button> }\n')
            metadata = fixture()
            (root / 'discussion/001-initial.json').write_text(json.dumps(metadata, ensure_ascii=False))
            run('validate_snapshot.py', '--workspace', str(root), '--snapshot', '001-initial')
            rendered = root / 'discussion/rendered'
            rendered.mkdir()
            archive = rendered / '001-initial.zip'
            archive.write_bytes(b'fixture rendered build')
            checksum = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
            (rendered / '001-initial.json').write_text(json.dumps({'snapshot_id': '001-initial', 'archive': archive.name, 'sha256': {'archive': checksum(archive), 'tsx': checksum(source), 'metadata': checksum(root / 'discussion/001-initial.json')}}))
            feedback = {
                'schema_version': 1, 'snapshot_id': '001-initial', 'submitted_at': '2026-09-24T00:00:00.000Z',
                'items': [
                    {'number': 1, 'kind': 'review_point', 'status_at_render': 'pending', 'previously_approved': False, 'reopened': False, 'title': '主操作', 'approved': True, 'comment': '', 'target': None, 'position': None},
                    {'number': 2, 'kind': 'dom_annotation', 'status_at_render': 'pending', 'previously_approved': False, 'reopened': False, 'title': '選択要素への指摘', 'approved': True, 'comment': 'この位置でよい', 'target': {'selector': '[data-review-target="action"]', 'target_key': 'action', 'tag': 'button', 'text': '登録'}, 'position': {'x_percent': 10, 'y_percent': 10, 'width_percent': 20, 'height_percent': 5}},
                ],
                'screen_detail_feedback': [], 'screen_details_approved': True, 'general_comment': '',
            }
            self.assertEqual(validate_payload(feedback, metadata, '001-initial'), feedback)
            (root / 'discussion/001-initial-feedback.json').write_text(json.dumps(feedback, ensure_ascii=False))
            applied = fixture()
            applied['snapshot'] = {'number': 2, 'slug': 'feedback-applied', 'label': '承認結果'}
            applied['requirements']['confirmed'] = ['主操作と位置を承認した']
            applied_path = root / 'discussion/002-feedback-applied.json'
            applied_path.write_text(json.dumps(applied, ensure_ascii=False))
            run('archive_approved.py', '--workspace', str(root), '--snapshot', '001-initial', '--requirements-input', str(applied_path))
            run('validate_approved.py', '--workspace', str(root))
            self.assertNotEqual(run('archive_approved.py', '--workspace', str(root), '--snapshot', '001-initial', '--requirements-input', str(applied_path), success=False).returncode, 0)
            archived = root / 'src/approved/approved-001-001-initial.tsx'
            original = archived.read_text()
            archived.write_text(archived.read_text() + '// tampered\n')
            self.assertNotEqual(run('validate_approved.py', '--workspace', str(root), success=False).returncode, 0)
            archived.write_text(original)
            archive.write_bytes(archive.read_bytes() + b'tampered')
            self.assertNotEqual(run('validate_snapshot.py', '--workspace', str(root), '--snapshot', '001-initial', success=False).returncode, 0)

    def test_prior_approval_remains_valid_feedback(self):
        metadata = fixture()
        point = metadata['review_points'][0]
        point['status'] = 'approved'
        point['approval_history'] = [{'approved_in_snapshot': '001-initial', 'title': '主操作'}]
        payload = {
            'schema_version': 1, 'snapshot_id': '001-initial', 'submitted_at': '2026-09-24T00:00:00.000Z',
            'items': [{'number': 1, 'kind': 'review_point', 'status_at_render': 'approved', 'previously_approved': True, 'reopened': False, 'title': '主操作', 'approved': True, 'comment': '', 'target': None, 'position': None}],
            'screen_detail_feedback': [], 'screen_details_approved': True, 'general_comment': '',
        }
        self.assertEqual(validate_payload(payload, metadata, '001-initial'), payload)


if __name__ == '__main__':
    unittest.main()
