import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import unittest
from urllib.error import HTTPError
from urllib.request import Request, urlopen

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
REPO = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(SCRIPTS))
import refine as r
import review


class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.skill = self.root / "brief"
        self.skill.mkdir()
        (self.skill / "SKILL.md").write_text('---\nname: brief\ndescription: Write a note\n---\nWrite a note.\n')
        self.workspace = self.root / "workspace"
        self.state = r.init(self.workspace, {"skill": str(self.skill), "cases": [
            {"id": "one", "task": "Write a short note"}]})

    def respond(self, action, notes=""):
        result = r.human_response(self.state, {"revision": self.state["revision"],
                                  "stage": self.state["stage"], "action": action, "notes": notes})
        r.acknowledge(self.state, result["id"], "Test fixture processed the simulated response")

    def generate(self):
        ticket = r.ticket(self.state, "one", "generate")
        r.register(self.state, ticket["run_id"], "agent-" + ticket["run_id"])
        (Path(ticket["output"]) / "note.txt").write_text("A short note")
        r.finish(self.state, ticket["run_id"])
        return ticket

    def rubric(self):
        r.publish_rubric(self.state, {"threshold": .8, "criteria": [{"id": "quality", "label": "Clarity",
                        "method": "1 for a clear note; 0 for an unclear note", "weight": 1,
                        "feedback": "The simulated reader asked for clear text"}]})

    def evaluate(self, score):
        ticket = r.ticket(self.state, "one", "evaluate")
        r.register(self.state, ticket["run_id"], "agent-" + ticket["run_id"])
        (Path(ticket["output"]) / "evidence.txt").write_text("Checked note")
        r.finish(self.state, ticket["run_id"], {"status": "ok", "grades": [
            {"id": "quality", "score": score, "evidence": "Observed clarity in the test fixture"}]})

    def baseline(self):
        self.respond("approve")
        self.generate()
        self.respond("feedback", "The reader wants clear text")
        self.rubric()
        self.respond("approve")
        self.evaluate(.2)

    def analysis(self, file="SKILL.md"):
        src = Path(self.state["skill"]) / file
        value = src.read_text() if src.exists() else None
        r.publish_analysis(self.state, {"summary": "Make the note clearer", "changes": [
            {"path": file, "before": value, "after": (value or "") + "\nUse clear text.\n",
             "reason": "Match simulated feedback"}]})

    def test_required_inputs_and_unique_cases(self):
        for spec in ({"skill": []}, {"skill": str(self.skill), "cases": []},
                     {"skill": str(self.skill), "cases": [{"id": "x", "task": ""}]}):
            with self.assertRaises(r.RefineError):
                r.init(self.root / "invalid", spec)
        self.assertFalse((self.root / "invalid").exists())

    def test_input_can_be_saved_inside_workspace_before_initialization(self):
        workspace = self.root / "prepared"
        workspace.mkdir()
        source = workspace / "input.json"
        spec = {"skill": str(self.skill), "cases": [{"id": "one", "task": "A note"}]}
        r.atomic_json(source, spec)
        r.init(workspace, r.read_json(source))
        self.assertEqual(r.read_json(source), spec)
        with self.assertRaises(r.RefineError):
            r.init(workspace, spec)

    def test_fresh_agents_and_no_meta_in_generation_prompt(self):
        with self.assertRaises(r.RefineError):
            r.ticket(self.state, "one", "generate")
        self.respond("approve")
        ticket = r.ticket(self.state, "one", "generate")
        self.assertEqual(ticket["fork_turns"], "none")
        self.assertNotIn("rubric", ticket["prompt"])
        self.assertNotIn("analysis", ticket["prompt"])
        self.assertNotIn("skill-refiner", ticket["prompt"])
        with self.assertRaises(r.RefineError):
            r.finish(self.state, ticket["run_id"])
        r.register(self.state, ticket["run_id"], "used-agent")
        (Path(ticket["output"]) / "result.txt").write_text("note")
        r.finish(self.state, ticket["run_id"])
        self.respond("feedback", "clearer please")
        self.rubric()
        with self.assertRaises(r.RefineError):
            r.ticket(self.state, "one", "evaluate")
        self.respond("approve")
        grade = r.ticket(self.state, "one", "evaluate")
        with self.assertRaises(r.RefineError):
            r.register(self.state, grade["run_id"], "used-agent")

    def test_stale_response_and_changed_frozen_artifact(self):
        with self.assertRaises(r.RefineError):
            r.human_response(self.state, {"revision": 0, "stage": "input_review", "action": "approve"})
        self.respond("approve")
        ticket = self.generate()
        (Path(ticket["output"]) / "note.txt").write_text("changed after completion")
        with self.assertRaisesRegex(r.RefineError, "artifact changed"):
            r.integrity(self.state)

    def test_pending_feedback_is_handled_before_execution(self):
        r.human_response(self.state, {"revision": 1, "stage": "input_review", "action": "approve"})
        with self.assertRaisesRegex(r.RefineError, "responses first"):
            r.ticket(self.state, "one", "generate")

    def test_candidate_success_and_promotion(self):
        before = r.digest(self.skill)
        self.baseline()
        self.analysis()
        with self.assertRaises(r.RefineError):
            r.ticket(self.state, "one", "generate")
        self.respond("approve")
        self.assertEqual(before, r.digest(self.skill))
        self.assertEqual(self.state["iteration"], 1)
        self.generate()
        self.evaluate(1)
        self.assertEqual(self.state["stage"], "final_review")
        with self.assertRaises(r.RefineError):
            r.promote(self.state)
        self.respond("approve")
        r.promote(self.state)
        self.assertEqual(self.state["stage"], "complete")
        self.assertIn("Use clear text.", (self.skill / "SKILL.md").read_text())
        self.assertEqual(len({x["agent_id"] for x in self.state["runs"]}), 4)

    def test_manual_retry_and_three_loop_iterations(self):
        self.baseline()
        self.analysis()
        self.respond("approve")
        self.generate()
        self.evaluate(.1)
        self.assertEqual(self.state["stage"], "results_review")
        self.respond("loop")
        for iteration in (2, 3, 4):
            self.analysis()
            self.assertEqual(self.state["iteration"], iteration)
            self.generate()
            self.evaluate(.1)
        self.assertEqual(self.state["stage"], "results_review")
        self.assertIsNone(self.state["loop"])

    def test_loop_stops_at_unapproved_file_scope(self):
        self.baseline()
        self.analysis()
        self.respond("approve")
        self.generate()
        self.evaluate(0)
        self.respond("loop")
        with self.assertRaisesRegex(r.RefineError, "approved file scope"):
            self.analysis("new-file.txt")
        self.assertEqual(self.state["stage"], "analysis_needed")

    def test_errors_are_not_quality_zero_and_retry_uses_fresh_ticket(self):
        self.respond("approve")
        ticket = r.ticket(self.state, "one", "generate")
        r.register(self.state, ticket["run_id"], "failed-agent")
        r.finish(self.state, ticket["run_id"], {"status": "error", "reason": "Tool unavailable"})
        run = r.run_by_id(self.state, ticket["run_id"])
        self.assertNotIn("score", run)
        self.assertEqual(self.state["stage"], "error_review")
        self.respond("retry")
        retry = r.ticket(self.state, "one", "generate")
        with self.assertRaises(r.RefineError):
            r.register(self.state, retry["run_id"], "failed-agent")

    def test_path_escape_and_target_concurrent_change(self):
        self.baseline()
        with self.assertRaises(r.RefineError):
            r.publish_analysis(self.state, {"summary": "escape", "changes": [
                {"path": "../escape", "before": None, "after": "bad", "reason": "bad"}]})
        (self.skill / "SKILL.md").write_text("someone else's edit")
        with self.assertRaisesRegex(r.RefineError, "target changed"):
            r.integrity(self.state)

    def test_resume_atomic_record_and_old_rubric_approval(self):
        self.respond("approve")
        self.generate()
        self.respond("feedback", "clear text")
        self.rubric()
        r.atomic_json(self.workspace / "state.json", self.state)
        old = self.state["revision"]
        with r.locked(self.workspace) as state:
            r.publish_rubric(state, {"threshold": .9, "criteria": [{"id": "new", "label": "New",
                            "method": "new scale", "weight": 1, "feedback": "reader feedback"}]})
        loaded = r.read_json(self.workspace / "state.json")
        self.assertGreater(loaded["revision"], old)
        with self.assertRaises(r.RefineError):
            r.human_response(loaded, {"revision": old, "stage": "rubric_review", "action": "approve"})

    def test_html_server_submission_and_csrf_staleness(self):
        server = review.make_server(self.workspace)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        base = f"http://127.0.0.1:{server.server_port}"
        with urlopen(base + "/review.html") as response:
            page = response.read().decode()
        payload = page.split('<script id="review-data" type="application/json">')[1].split('</script>')[0]
        token = json.loads(payload)["token"]
        body = json.dumps({"revision": 1, "stage": "input_review", "action": "approve", "notes": ""}).encode()
        with self.assertRaises(HTTPError):
            urlopen(Request(base + "/api/respond", data=body, method="POST"))
        request = Request(base + "/api/respond", data=body, method="POST",
                          headers={"Origin": base, "X-Review-Token": token, "Content-Type": "application/json"})
        with urlopen(request) as response:
            self.assertTrue(json.load(response)["saved"])
        self.assertEqual(r.read_json(self.workspace / "state.json")["stage"], "generating")
        with self.assertRaises(HTTPError):
            urlopen(request)
        with self.assertRaises(HTTPError):
            urlopen(base + "/artifact/state.json")

    def test_html_escapes_script_injection(self):
        self.state["cases"][0]["task"] = '</script><script>alert("bad")</script>'
        rendered = review.render(self.state)
        self.assertNotIn('</script><script>alert', rendered)
        self.assertIn('\\u003c/script>', rendered)

    def test_plugin_gate_denies_wrong_prompt_and_reuse(self):
        gate = REPO / "utils/plugins/skill-refiner/scripts/gate.py"
        self.respond("approve")
        ticket = r.ticket(self.state, "one", "generate")
        r.atomic_json(self.workspace / "state.json", self.state)
        env = {**os.environ, "SKILL_REFINER_WORKSPACE": str(self.workspace)}
        def call(event):
            process = subprocess.run([sys.executable, str(gate)], input=json.dumps(event),
                                     text=True, capture_output=True, env=env)
            self.assertEqual(process.returncode, 0, process.stderr)
            return json.loads(process.stdout)
        event = {"hook_event_name": "PreToolUse", "tool_name": "spawn_agent", "session_id": "parent",
                 "cwd": str(self.root), "tool_input": {"message": ticket["prompt"], "fork_turns": "all"}}
        self.assertEqual(call(event)["hookSpecificOutput"]["permissionDecision"], "deny")
        event["tool_input"]["fork_turns"] = "none"
        self.assertEqual(call(event), {})
        start = {"hook_event_name": "SubagentStart", "session_id": "parent", "agent_id": "hook-agent"}
        self.assertEqual(call(start), {})
        self.assertEqual(r.read_json(self.workspace / "state.json")["runs"][0]["agent_id"], "hook-agent")
        self.assertEqual(call(event)["hookSpecificOutput"]["permissionDecision"], "deny")

    def test_multiple_cases_finish_only_when_all_done(self):
        self.state["cases"].append({"id": "two", "task": "Another note", "files": []})
        self.respond("approve")
        self.generate()
        self.assertEqual(self.state["stage"], "generating")
        ticket = r.ticket(self.state, "two", "generate")
        r.register(self.state, ticket["run_id"], "agent-two")
        (Path(ticket["output"]) / "result").write_text("Another note")
        r.finish(self.state, ticket["run_id"])
        self.assertEqual(self.state["stage"], "feedback_review")

    def test_empty_directories_do_not_count_as_artifacts(self):
        self.respond("approve")
        ticket = r.ticket(self.state, "one", "generate")
        r.register(self.state, ticket["run_id"], "empty-agent")
        (Path(ticket["output"]) / "empty").mkdir()
        with self.assertRaisesRegex(r.RefineError, "no artifacts"):
            r.finish(self.state, ticket["run_id"])

    def test_grades_require_all_criteria_and_valid_evidence(self):
        self.respond("approve")
        self.generate()
        self.respond("feedback", "clear text")
        self.rubric()
        self.respond("approve")
        ticket = r.ticket(self.state, "one", "evaluate")
        r.register(self.state, ticket["run_id"], "grader")
        (Path(ticket["output"]) / "raw.txt").write_text("checked")
        for grades in ([], [{"id": "quality", "score": float("nan"), "evidence": "checked"}],
                       [{"id": "quality", "score": 1, "evidence": ""}]):
            with self.assertRaises(r.RefineError):
                r.finish(self.state, ticket["run_id"], {"status": "ok", "grades": grades})

    def test_invalid_candidate_does_not_leave_a_half_applied_directory(self):
        self.baseline()
        src = Path(self.state["skill"]) / "SKILL.md"
        r.publish_analysis(self.state, {"summary": "bad candidate", "changes": [{"path": "SKILL.md",
                           "before": src.read_text(), "after": "no frontmatter", "reason": "test"}]})
        with self.assertRaises(r.RefineError):
            self.respond("approve")
        self.assertFalse((self.workspace / "candidate-skill/iteration-1/brief").exists())

    def test_bundles_execute_their_own_hook_without_source_links(self):
        for agent in ("codex", "claude-code"):
            output = self.root / agent
            result = subprocess.run([sys.executable, str(REPO / "utils/plugins/skill-refiner/build.py"),
                                     "--agent", agent, "--output", str(output)], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue((output / "skills/skill-refiner/scripts/refine.py").is_file())
            event = {"hook_event_name": "PreToolUse", "cwd": str(self.root), "tool_name": "spawn_agent",
                     "tool_input": {"message": "unplanned", "fork_turns": "none"}}
            run = subprocess.run([sys.executable, str(output / "scripts/gate.py")], input=json.dumps(event),
                                 text=True, capture_output=True,
                                 env={**os.environ, "SKILL_REFINER_WORKSPACE": str(self.workspace)})
            self.assertEqual(run.returncode, 0, run.stderr)
            self.assertEqual(json.loads(run.stdout)["hookSpecificOutput"]["permissionDecision"], "deny")


if __name__ == "__main__":
    unittest.main()
