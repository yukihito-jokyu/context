"""Test relocated packages through their configured commands, without installation."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

PLUGIN = Path(__file__).resolve().parents[1]
NAME = "write-requirement-document"
SOURCE = (PLUGIN / json.loads((PLUGIN / "bundle.json").read_text())["skill"]).resolve()


def files(root):
    return {p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in root.rglob("*") if p.is_file() and not any(n in p.parts for n in ["__pycache__", "results"])
            and p.name != "convergence-report.md" and p.suffix != ".pyc"}


class PluginTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix="requirements-plugin-")
        cls.root = Path(cls.temp.name).resolve()
        cls.before = files(SOURCE)
        cls.builds = {}
        for agent in ["codex", "claude-code"]:
            initial = cls.root / (agent + " original")
            subprocess.run([sys.executable, str(PLUGIN / "build.py"), "--agent", agent, "--output", str(initial)],
                           check=True, capture_output=True)
            relocated = cls.root / (agent + " relocated path")
            initial.rename(relocated)
            cls.builds[agent] = relocated

    @classmethod
    def tearDownClass(cls):
        assert files(SOURCE) == cls.before
        cls.temp.cleanup()

    def workspace(self, name):
        root = self.root / name
        root.mkdir()
        subprocess.run(["git", "init", "-q", str(root)], check=True)
        return root

    def run_core(self, build, project, *args):
        return subprocess.run([sys.executable, str(build / "runtime" / NAME / "scripts/run.py"), *args],
                              cwd=project, capture_output=True, text=True)

    def hook(self, build, project, event_name, payload):
        settings = json.loads((build / "hooks/hooks.json").read_text())
        command = settings["hooks"][event_name][0]["hooks"][0]["command"]
        env = {**os.environ, "PLUGIN_ROOT": str(build), "CLAUDE_PLUGIN_ROOT": str(build)}
        return subprocess.run(command, shell=True, input=json.dumps({"cwd": str(project), **payload}),
                              cwd=project, env=env, text=True, capture_output=True)

    def edit(self, platform, path):
        if platform == "codex":
            return {"tool_name": "apply_patch", "tool_input": {"input": "*** Begin Patch\n*** Update File: " + str(path) + "\n*** End Patch"}}
        return {"tool_name": "Write", "tool_input": {"file_path": str(path)}}

    def test_runtime_matches_and_private_records_are_excluded(self):
        for build in self.builds.values():
            runtime = build / "runtime" / NAME
            self.assertEqual(files(runtime), self.before)
            self.assertFalse((runtime / "dev/results").exists())
            self.assertFalse((runtime / "dev/convergence-report.md").exists())
            self.assertFalse(any(p.is_symlink() for p in build.rglob("*")))
            entry = (build / "skills" / NAME / "SKILL.md").read_text()
            self.assertIn("`scripts/install.py` は実行しない", entry)
            self.assertIn("../../runtime/write-requirement-document/SKILL.md", entry)

    def test_build_rejects_existing_output_and_source_paths(self):
        for target in [self.builds["codex"], SOURCE / "overwrite", PLUGIN / "overwrite"]:
            result = subprocess.run([sys.executable, str(PLUGIN / "build.py"), "--agent", "codex", "--output", str(target)],
                                    capture_output=True)
            self.assertNotEqual(result.returncode, 0)

    def test_inactive_events_and_unrelated_tools_are_transparent(self):
        project = self.workspace("inactive")
        for agent, platform in [("codex", "codex"), ("claude-code", "claude")]:
            for event in ["PreToolUse", "PostToolUse", "Stop", "UserPromptSubmit"]:
                result = self.hook(self.builds[agent], project, event, self.edit(platform, project / "unrelated.txt"))
                self.assertEqual((result.returncode, result.stdout), (0, ""), result.stderr)
            result = self.hook(self.builds[agent], project, "PreToolUse", {"tool_name": "Read"})
            self.assertEqual((result.returncode, result.stdout), (0, ""), result.stderr)

    def test_active_hooks_check_finish_and_no_standalone_installation(self):
        for agent, platform in [("codex", "codex"), ("claude-code", "claude")]:
            project = self.workspace("active-" + agent)
            build = self.builds[agent]
            start = self.run_core(build, project, "start", "備品予約の要件定義書を作成する")
            self.assertEqual(start.returncode, 0, start.stdout + start.stderr)
            run = project / ".skill-runs" / NAME
            denied = self.hook(build, project, "PreToolUse", self.edit(platform, run / "state.json"))
            self.assertEqual(json.loads(denied.stdout)["hookSpecificOutput"]["permissionDecision"], "deny")
            out = run / "out"
            shutil.copytree(build / "runtime" / NAME / "assets/examples", out)
            source = out / "requirement-document.json"
            good = source.read_bytes()
            source.write_text("{}")
            post = self.hook(build, project, "PostToolUse", self.edit(platform, source))
            self.assertEqual(json.loads(post.stdout)["decision"], "block", post.stderr)
            source.write_bytes(good)
            html = out / "requirement-document.html"
            good_html = html.read_bytes()
            html.write_text("<html>broken</html>")
            invalid = self.run_core(build, project, "check")
            self.assertNotEqual(invalid.returncode, 0, invalid.stdout + invalid.stderr)
            html.write_bytes(good_html)
            checked = self.run_core(build, project, "check")
            self.assertEqual(checked.returncode, 0, checked.stdout + checked.stderr)
            stopped = self.hook(build, project, "Stop", {})
            self.assertEqual(json.loads(stopped.stdout)["decision"], "block")
            waiting = self.run_core(build, project, "wait", "--question", "予約条件を確認してください")
            self.assertEqual(waiting.returncode, 0, waiting.stderr)
            self.assertEqual(self.hook(build, project, "Stop", {}).stdout, "")
            self.assertEqual(self.hook(build, project, "UserPromptSubmit", {}).returncode, 0)
            self.assertEqual(json.loads((run / "state.json").read_text())["status"], "active")
            finished = self.run_core(build, project, "finish")
            self.assertEqual(finished.returncode, 0, finished.stdout + finished.stderr)
            self.assertEqual(self.hook(build, project, "Stop", {}).stdout, "")
            for directory in [".agents", ".codex", ".claude"]:
                self.assertFalse((project / directory).exists(), directory)

    def test_broken_runtime_is_reported_instead_of_silent_success(self):
        project = self.workspace("broken")
        build = self.root / "broken package"
        shutil.copytree(self.builds["codex"], build)
        (build / "runtime" / NAME / "scripts/hook.py").unlink()
        pre = self.hook(build, project, "PreToolUse", self.edit("codex", project / "file.txt"))
        self.assertEqual(json.loads(pre.stdout)["hookSpecificOutput"]["permissionDecision"], "deny")
        self.assertEqual(self.hook(build, project, "Stop", {}).returncode, 2)

    def test_core_skill_completes_without_hooks_or_collector(self):
        project = self.workspace("standalone")
        build = self.root / "standalone package"
        shutil.copytree(self.builds["codex"], build)
        runtime = build / "runtime" / NAME
        for name in ("hook.py", "feedback.py", "feedback_review.py"):
            (runtime / "scripts" / name).unlink()
        (project / ".skill-feedback").write_text("Collection is unavailable")
        self.assertEqual(self.run_core(build, project, "start", "備品予約の要件を整理する").returncode, 0)
        shutil.copytree(runtime / "assets/examples", project / ".skill-runs" / NAME / "out")
        for command in ("check", "finish"):
            result = self.run_core(build, project, command)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertNotIn("feedback.py", result.stdout)
        prompt = (runtime / "SKILL.md").read_text()
        for marker in ("feedback.py", "FBK-01", "指摘収集", ".skill-feedback"):
            self.assertNotIn(marker, prompt)

    def test_feedback_extension_collects_only_through_hooks(self):
        # Synthetic feedback, without creating any real user approval.
        for agent in ("codex", "claude-code"):
            build = self.builds[agent]
            runtime = build / "runtime" / NAME
            project = self.workspace("feedback-" + agent)
            session = "synthetic-" + agent
            core = self.run_core(build, project, "start", "備品予約の要件を整理する")
            self.assertEqual(core.returncode, 0, core.stdout + core.stderr)
            run = project / ".skill-runs" / NAME
            original_state = (run / "state.json").read_bytes()
            injected = self.hook(build, project, "PostToolUse", {"session_id": session, "tool_name": "exec_command"})
            self.assertIn("context --file", json.loads(injected.stdout)["hookSpecificOutput"]["additionalContext"])
            self.assertEqual((run / "state.json").read_bytes(), original_state)
            shutil.copytree(runtime / "assets/examples", run / "out")
            finished = self.run_core(build, project, "finish")
            self.assertEqual(finished.returncode, 0, finished.stdout + finished.stderr)
            store = project / ".skill-feedback" / NAME / "feedback.json"
            self.assertEqual(json.loads(store.read_text())["deliveries"], [])
            self.assertEqual(self.hook(build, project, "Stop", {"session_id": session}).returncode, 0)
            before = json.loads(store.read_text())["deliveries"][0]["id"]
            prompt = self.hook(build, project, "UserPromptSubmit", {"session_id": session, "turn_id": "feedback-1",
                               "prompt": "タイトルに業務名が分かるようにしてください。"})
            self.assertIn("feedback --event", json.loads(prompt.stdout)["hookSpecificOutput"]["additionalContext"])
            event_id = json.loads(store.read_text())["messages"][-1]["id"]
            classified = subprocess.run([sys.executable, str(runtime / "scripts/feedback.py"), "feedback", "--event", event_id],
                                        cwd=project, capture_output=True, text=True)
            self.assertEqual(classified.returncode, 0, classified.stderr)
            source = run / "out/requirement-document.json"
            data = json.loads(source.read_text())
            data["title"] = "備品予約業務の要件定義書"
            source.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")
            rebuilt = subprocess.run([sys.executable, str(runtime / "scripts/document.py"), "build", "--source", str(source),
                                      "--out", str(run / "out")], cwd=project, capture_output=True, text=True)
            self.assertEqual(rebuilt.returncode, 0, rebuilt.stdout + rebuilt.stderr)
            # A correction to a presented document can be checked and shown by
            # Stop without finishing the already-completed core run twice.
            revised = self.run_core(build, project, "check")
            self.assertEqual(revised.returncode, 0, revised.stdout + revised.stderr)
            self.hook(build, project, "Stop", {"session_id": session})
            corpus = json.loads(store.read_text())
            case = corpus["cases"][0]
            self.assertEqual(case["before"], before)
            self.assertTrue(case["revisions"])
            self.assertEqual(case["status"], "pending")
            self.assertIsNone(case["approval"])
            checked = subprocess.run([sys.executable, str(runtime / "scripts/feedback.py"), "validate"],
                                     cwd=project, capture_output=True, text=True)
            self.assertEqual(checked.returncode, 0, checked.stderr)


if __name__ == "__main__":
    unittest.main()
