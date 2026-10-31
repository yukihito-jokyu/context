#!/usr/bin/env python3
"""Synthetic hook-event regression tests. These events are not real user approvals."""
from __future__ import annotations

import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import urllib.request
import urllib.error
import unittest

import _lib

SOURCE = Path(__file__).resolve().parents[1]


class FeedbackTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="skill-feedback-test-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "project"
        self.root.mkdir()
        self.skill = Path(self.temp.name) / "write-feedback-test"
        for name in _lib.RUNTIME_FILES:
            target = self.skill / "scripts" / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(SOURCE / "scripts" / name, target)
        (self.skill / "SKILL.md").write_text("---\nname: write-feedback-test\ndescription: Write an output\n---\nWrite an output.\n")
        self.contract = {"skill": self.skill.name, "language": "ja", "targets": ["claude", "codex"], "inputs": [],
                         "outputs": [{"id": "result", "path": "result.txt", "count": {"min": 1, "max": 1},
                                      "rule": "OUT-01", "checks": [{"type": "require", "pattern": "^Title:", "rule": "OUT-02"}]},
                                     {"id": "image", "path": "sample.png", "binary": True, "required": False,
                                      "count": {"min": 0, "max": 1}, "rule": "OUT-03", "checks": []}],
                         "control": {"hooks": True, "max_stop_blocks": 3}, "report": {}}
        self.write_json(self.skill / "assets/contract.json", self.contract)
        shutil.copyfile(SOURCE / "assets/feedback.schema.json", self.skill / "assets/feedback.schema.json")
        self.session = "synthetic-session-a"
        self.event_no = 0

    def write_json(self, path, value):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value, ensure_ascii=False))

    def cmd(self, script, *arguments, code=0, stdin=None):
        result = subprocess.run([sys.executable, str(self.skill / "scripts" / script), *map(str, arguments)],
                                cwd=self.root, input=stdin, capture_output=True, text=True)
        self.assertEqual(result.returncode, code, result.stdout + result.stderr)
        return result.stdout

    def hook(self, kind, prompt=None, session=None, platform="codex", **extra):
        self.event_no += 1
        event = {"cwd": str(self.root), "session_id": session or self.session, "turn_id": str(self.event_no), **extra}
        if prompt is not None:
            event["prompt"] = prompt
        return self.cmd("hook.py", "--platform", platform, kind, stdin=json.dumps(event))

    def data(self):
        return json.loads((self.root / ".skill-feedback" / self.skill.name / "feedback.json").read_text())

    def start_output(self):
        self.cmd("run.py", "start", "Write a concise result")
        self.hook("pre-tool", tool_name="apply_patch", tool_input={"patch": "*** Update File: result.txt\n"})
        (self.root / "input.txt").write_text("original input\n")
        self.cmd("feedback.py", "context", "--file", "input.txt")
        (self.root / "input.txt").write_text("changed after it was read\n")
        (self.root / "result.txt").write_text("Title: Original\nThe answer is hard to scan.\n")
        (self.root / "sample.png").write_bytes(b"\x89PNG\r\n\x1a\noriginal\xff")
        self.cmd("run.py", "finish")
        self.hook("stop")

    def feedback(self, text="結論を先頭に置き、理由を続けてください。", platform="codex"):
        output = self.hook("prompt", text, platform=platform)
        self.assertIn("UserPromptSubmit", output)
        event = self.data()["messages"][-1]["id"]
        self.cmd("feedback.py", "feedback", "--event", event)
        return self.data()["cases"][-1]

    def revision(self, restart=True):
        if restart:
            self.cmd("run.py", "start", "Put the conclusion first")
        (self.root / "result.txt").write_text("Title: Conclusion first\nThe reason follows.\n")
        (self.root / "sample.png").write_bytes(b"\x89PNG\r\n\x1a\nrevised\xfe")
        if restart:
            self.cmd("run.py", "finish")
            self.hook("stop")
        else:
            self.hook("stop")

    def review_server(self):
        process = subprocess.Popen([sys.executable, str(self.skill / "scripts/feedback.py"), "review"],
                                   cwd=self.root, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        self.addCleanup(lambda: process.stdout.close())
        self.addCleanup(lambda: process.stderr.close())
        def close():
            process.terminate()
            process.wait(timeout=5)
        self.addCleanup(close)
        url = process.stdout.readline().strip()
        self.assertTrue(url.startswith("http://127.0.0.1:"), process.stderr.read() if not url else url)
        return url

    def review_post(self, url, case, *, origin=True, code=200):
        payload = {"case_id": case["id"], "delivery": case["after"], "revision": case["revision"], "token": case["token"]}
        headers = {"Content-Type": "application/json"}
        if origin:
            headers["Origin"] = url.rstrip("/")
        request = urllib.request.Request(url + "api/approve", data=json.dumps(payload).encode(), headers=headers)
        try:
            response = urllib.request.urlopen(request)
        except urllib.error.HTTPError as error:
            response = error
        with response:
            self.assertEqual(response.status, code, response.read().decode() if response.status != code else "")

    def approve(self, platform="codex"):
        url = self.review_server()
        data = json.load(urllib.request.urlopen(url + "api/state"))
        for case in data["cases"]:
            if case["status"] == "pending":
                self.review_post(url, case)

    def test_collect_before_after_after_finish_and_explicit_approval(self):
        self.start_output()
        before = self.data()["deliveries"][0]
        case = self.feedback()
        self.revision()
        self.approve()
        data = self.data()
        case = data["cases"][0]
        self.assertEqual(case["status"], "approved")
        self.assertEqual(case["before"], before["id"])
        self.assertNotEqual(case["after"], case["before"])
        self.assertEqual(case["approval"]["text"], "この修正版を承認する")
        self.assertEqual(case["approval"]["source"], "review-ui")
        objects = self.root / ".skill-feedback" / self.skill.name
        self.assertEqual((objects / before["context"][0]["object"]).read_text(), "original input\n")
        image = next(a for a in before["artifacts"] if a["output"] == "image")
        self.assertEqual((objects / image["object"]).read_bytes(), b"\x89PNG\r\n\x1a\noriginal\xff")
        self.cmd("feedback.py", "validate")
        import convergence
        self.assertFalse(any(p.startswith(".skill-feedback/") for p in convergence.snapshot(self.root)))

    def test_pending_and_ambiguous_messages_do_not_become_success_examples(self):
        self.start_output()
        self.feedback()
        self.revision()
        self.hook("prompt", "OK")
        event = self.data()["messages"][-1]["id"]
        self.cmd("feedback.py", "approve", "--event", event, code=2)
        self.assertEqual(self.data()["cases"][0]["status"], "pending")
        self.cmd("feedback.py", "export", "--out", Path(self.temp.name) / "export", code=1)

    def test_approval_cannot_approve_bytes_changed_since_presentation(self):
        self.start_output()
        self.feedback()
        self.revision()
        (self.root / "result.txt").write_text("Title: not shown to the user\n")
        url = self.review_server()
        page = json.load(urllib.request.urlopen(url + "api/state"))
        self.review_post(url, page["cases"][0], code=400)
        self.assertEqual(self.data()["cases"][0]["status"], "pending")

    def test_output_check_still_rejects_invalid_revisions(self):
        self.start_output()
        self.feedback()
        self.revision(restart=False)
        (self.root / "result.txt").write_text("invalid output")
        self.hook("stop")
        url = self.review_server()
        page = json.load(urllib.request.urlopen(url + "api/state"))
        self.review_post(url, page["cases"][0], code=400)
        self.assertEqual(self.data()["cases"][0]["status"], "pending")

    def test_other_session_and_duplicate_events_do_not_mix_feedback(self):
        self.start_output()
        self.assertEqual(self.hook("prompt", "この修正版でOK", session="other-session"), "")
        event = {"cwd": str(self.root), "session_id": self.session, "turn_id": "same-event", "prompt": "Add an example"}
        for _ in range(2):
            self.cmd("hook.py", "--platform", "codex", "prompt", stdin=json.dumps(event))
        self.assertEqual(len(self.data()["messages"]), 1)

    def test_cli_only_finish_binds_session_on_stop(self):
        self.cmd("run.py", "start", "Write a concise result")
        (self.root / "result.txt").write_text("Title: CLI-only output\n")
        self.cmd("run.py", "finish")
        self.assertFalse((self.root / ".skill-feedback").exists())
        self.hook("stop")
        self.assertEqual(self.data()["deliveries"][-1]["session_id"], self.session)
        self.assertEqual(self.hook("prompt", "Unrelated feedback", session="other-session"), "")
        self.assertEqual(self.data()["messages"], [])
        case = self.feedback()
        self.assertEqual(case["session_id"], self.session)
        self.cmd("feedback.py", "validate")

    def test_chained_feedback_and_claude_hooks(self):
        self.start_output()
        self.feedback(platform="claude")
        self.revision()
        self.feedback("理由に具体例も加えてください。", platform="claude")
        self.cmd("run.py", "start", "Add a concrete example")
        (self.root / "result.txt").write_text("Title: Conclusion first\nReason and a concrete example.\n")
        self.cmd("run.py", "finish")
        self.hook("stop")
        self.approve(platform="claude")
        self.assertEqual([c["status"] for c in self.data()["cases"]], ["approved", "approved"])
        self.assertEqual(self.data()["cases"][1]["request"], "Write a concise result")
        self.cmd("feedback.py", "validate")

    def test_history_cannot_be_edited_through_edit_hook(self):
        self.start_output()
        output = self.hook("pre-tool", tool_name="apply_patch", tool_input={
            "patch": "*** Update File: .skill-feedback/write-feedback-test/feedback.json\n"})
        self.assertEqual(json.loads(output)["hookSpecificOutput"]["permissionDecision"], "deny")
        output = self.hook("pre-tool", tool_name="apply_patch", tool_input={
            "patch": "*** Update File: " + str(self.skill / "SKILL.md") + "\n"})
        self.assertEqual(output, "")

    def test_export_integrity_and_eval_preparation_do_not_leak_answers(self):
        self.start_output()
        self.feedback()
        self.revision()
        self.approve()
        export = Path(self.temp.name) / "export"
        self.cmd("feedback.py", "export", "--out", export)
        spec = json.loads((SOURCE / "assets/example/write-commit-message/spec.json").read_text())
        spec["name"] = self.skill.name
        self.write_json(self.skill / "dev/spec.json", spec)
        output = Path(self.temp.name) / "improve"
        command = [sys.executable, str(SOURCE / "scripts/feedback_eval.py"), "--dataset", str(export),
                   "--skill", str(self.skill), "--out", str(output)]
        result = subprocess.run(command, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        candidate = output / "skills" / self.skill.name
        eval_cli = [sys.executable, str(SOURCE / "scripts/eval_check.py"), str(candidate)]
        result = subprocess.run(eval_cli, capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("答えを待っている", result.stdout)
        conv = [sys.executable, str(SOURCE / "scripts/convergence.py"), "prepare", str(candidate), "--round", "1",
                "--runners", "subagent", "--agents", "1", "--workdir", str(output / "runs"),
                "--agents-dir", str(output / "agents")]
        self.assertNotEqual(subprocess.run(conv, capture_output=True).returncode, 0)
        result = subprocess.run(eval_cli + ["--answer", f"Eval 作成の回答（{candidate.name}、talk-1）\nQ1 指摘 1 を評価条件にする: 評価基準と事例・入力条件を確認しました（合成テストの回答）"], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        result = subprocess.run(conv, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        plan = json.loads((output / "runs/round-1/plan.json").read_text())
        producer = Path(plan["runs"][0]["dir"])
        self.assertEqual((producer / "input.txt").read_text(), "original input\n")
        self.assertIn("Write a concise result", plan["runs"][0]["prompt"])
        self.assertNotIn("結論を先頭", plan["runs"][0]["prompt"])
        self.assertFalse(list(producer.rglob("eval.json")))
        obj = next((export / "objects").iterdir())
        obj.write_bytes(b"changed")
        other = Path(self.temp.name) / "tampered"
        command[-1] = str(other)
        self.assertNotEqual(subprocess.run(command, capture_output=True).returncode, 0)

    def test_review_requires_same_origin_and_rejects_stale_page(self):
        self.start_output()
        self.feedback()
        self.revision()
        url = self.review_server()
        page = json.load(urllib.request.urlopen(url + "api/state"))
        case = page["cases"][0]
        self.review_post(url, case, origin=False, code=403)
        with urllib.request.urlopen(url + "api/state") as response:
            refreshed = json.load(response)
        self.review_post(url, case, code=400)
        self.review_post(url, refreshed["cases"][0])
        self.review_post(url, refreshed["cases"][0], code=400)
        self.assertEqual(self.data()["cases"][0]["status"], "approved")

    def test_chat_approval_does_not_replace_review_approval(self):
        self.start_output()
        self.feedback()
        self.revision()
        self.hook("prompt", "この修正版を承認します")
        self.assertEqual(self.data()["cases"][0]["status"], "pending")

    def test_collection_is_bundled_but_hooks_can_be_disabled(self):
        self.cmd("install.py", "--project", self.root, "--no-hooks")
        for rel in (".claude/settings.json", ".codex/hooks.json"):
            path = self.root / rel
            self.assertFalse(path.exists() and json.loads(path.read_text()).get("hooks"))
        self.cmd("install.py", "--project", self.root)
        for rel in (".claude/settings.json", ".codex/hooks.json"):
            hooks = json.loads((self.root / rel).read_text())["hooks"]
            self.assertEqual(set(hooks), {"PreToolUse", "PostToolUse", "Stop", "UserPromptSubmit"})

    def test_core_works_without_collection_modules_or_hooks(self):
        for name in ("hook.py", "feedback.py", "feedback_review.py"):
            (self.skill / "scripts" / name).unlink()
        blocked = self.root / ".skill-feedback"
        blocked.write_text("collector cannot create its store here")
        self.cmd("run.py", "start", "Write a concise result")
        (self.root / "result.txt").write_text("Title: Works without hooks\n")
        self.cmd("run.py", "check")
        report = self.cmd("run.py", "finish")
        self.assertIn("完了", report)
        self.assertNotIn("feedback.py", report)
        self.assertNotIn("指摘収集", report)
        state = json.loads((self.root / ".skill-runs" / self.skill.name / "state.json").read_text())
        self.assertEqual(state["status"], "done")
        self.assertFalse(any(key.startswith("feedback") for key in state))

    def test_collection_instructions_come_only_from_hooks(self):
        self.cmd("run.py", "start", "Write a concise result")
        result = self.hook("post-tool", tool_name="exec_command", tool_input={})
        context = json.loads(result)["hookSpecificOutput"]["additionalContext"]
        self.assertIn("context --file", context)
        self.assertIn("指摘収集hooks", context)
        self.assertEqual(self.hook("post-tool", tool_name="exec_command", tool_input={}), "")
        state = json.loads((self.root / ".skill-runs" / self.skill.name / "state.json").read_text())
        self.assertFalse(any(key.startswith("feedback") for key in state))

    def test_broken_collector_does_not_block_finish_or_wait_resume(self):
        self.cmd("run.py", "start", "Write a concise result")
        (self.root / "result.txt").write_text("Title: Valid output\n")
        base = self.root / ".skill-feedback" / self.skill.name
        base.mkdir(parents=True)
        (base / "feedback.json").write_text("invalid json")
        self.cmd("run.py", "wait", "--question", "Continue?")
        self.assertEqual(self.hook("prompt", "Yes"), "")
        self.assertEqual(self.hook("stop")[:1], "{")  # Existing finish gate still runs.
        self.cmd("run.py", "check")
        self.cmd("run.py", "finish")
        self.assertEqual(self.hook("stop"), "")

    def test_generated_prompts_have_no_collection_duties_in_either_language(self):
        import init_skill
        import render_skill
        original = json.loads((SOURCE / "assets/example/write-commit-message/spec.json").read_text())
        for language in ("ja", "en"):
            spec = json.loads(json.dumps(original))
            spec["language"] = language
            (self.skill / "SKILL.md").write_text(init_skill.fill((SOURCE / f"assets/templates/SKILL.{language}.md.tmpl").read_text(), spec))
            spec.setdefault("decisions", []).append({"id": "FBK-01", "axes": ["F1"], "decision": "Collect feedback"})
            init_skill.merge_standard(spec)
            rendered = render_skill.render_all(self.skill, spec)
            for rel in ("SKILL.md", "references/decisions.md"):
                for marker in ("FBK-01", "feedback.py", ".skill-feedback", "references/feedback.md", "指摘収集", "collect feedback"):
                    self.assertNotIn(marker, rendered[rel], rel)
            self.assertNotIn("feedback", json.loads(rendered["assets/contract.json"]))


if __name__ == "__main__":
    unittest.main(verbosity=2)
