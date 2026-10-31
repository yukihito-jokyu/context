"""Exercise relocated plugin builds, active runtime hooks, and the packaged tester."""
import hashlib
import json
import os
import shutil
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

PLUGIN = Path(__file__).resolve().parents[1]
SOURCE = (PLUGIN / json.loads((PLUGIN / "bundle.json").read_text(encoding="utf-8"))["skill"]).resolve()


def files(folder):
    return {p.relative_to(folder).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in folder.rglob("*") if p.is_file() and "__pycache__" not in p.parts and p.suffix != ".pyc"}


class PluginTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix="foundation-plugin-")
        cls.root = Path(cls.temp.name).resolve()
        cls.before = files(SOURCE)
        cls.builds = {}
        for agent in ["codex", "claude-code"]:
            build = cls.root / (agent + " relocated path")
            subprocess.run([sys.executable, str(PLUGIN / "build.py"), "--agent", agent, "--output", str(build)],
                           check=True, capture_output=True)
            cls.builds[agent] = build

    @classmethod
    def tearDownClass(cls):
        assert files(SOURCE) == cls.before
        cls.temp.cleanup()

    def workspace(self, name):
        project = self.root / name
        project.mkdir()
        subprocess.run(["git", "init", "-q", str(project)], check=True)
        return project

    def run_core(self, build, project, *args):
        return subprocess.run([sys.executable, str(build / "runtime/skill-foundation/scripts/run.py"), *args],
                              cwd=project, capture_output=True, text=True)

    def hook(self, build, platform, action, event, project):
        env = {**os.environ, "CLAUDE_PLUGIN_ROOT": str(build), "PLUGIN_ROOT": str(build)}
        return subprocess.run([sys.executable, str(build / "scripts/hook.py"), "--platform", platform, action],
                              input=json.dumps({"cwd": str(project), **event}), text=True, cwd=project,
                              capture_output=True, env=env)

    def test_complete_core_is_byte_identical_and_usable(self):
        for build in self.builds.values():
            self.assertEqual(files(build / "runtime/skill-foundation"), self.before)
            self.assertFalse(any(p.is_symlink() for p in build.rglob("*")))
            runtime = build / "runtime/skill-foundation"
            self.assertFalse((runtime / "assets/seal.json").exists())
            # The distributed creator has no dev/spec.json. Exercise its packaged
            # example instead, including Eval, settings, probes and final checks.
            result = subprocess.run([sys.executable, str(runtime / "scripts/selftest.py")],
                                    capture_output=True, text=True, timeout=180)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_existing_output_is_not_overwritten(self):
        build = self.builds["codex"]
        before = files(build)
        result = subprocess.run([sys.executable, str(PLUGIN / "build.py"), "--agent", "codex", "--output", str(build)],
                                capture_output=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(files(build), before)

    def test_inactive_events_are_transparent(self):
        project = self.workspace("inactive")
        for agent, platform in [("codex", "codex"), ("claude-code", "claude")]:
            for action in ["pre-tool", "post-tool", "stop", "prompt"]:
                event = {"tool_name": "apply_patch" if platform == "codex" else "Write"}
                result = self.hook(self.builds[agent], platform, action, event, project)
                self.assertEqual((result.returncode, result.stdout), (0, ""), result.stderr)

    def test_edits_are_allowed_while_output_checks_and_resume_work(self):
        for agent, platform in [("codex", "codex"), ("claude-code", "claude")]:
            project = self.workspace("active-" + agent)
            build = self.root / ("editable-" + agent)
            shutil.copytree(self.builds[agent], build)
            skill = build / "runtime/skill-foundation"
            (skill / "assets/seal.json").write_text('{"files":{"SKILL.md":"legacy"}}')
            entry = skill / "SKILL.md"
            entry.write_text(entry.read_text() + "\n")
            start = self.run_core(build, project, "start", "--set", "name=write-sample", "--set", "measure=skip", "文章を書くスキルを作る")
            self.assertEqual(start.returncode, 0, start.stdout + start.stderr)
            path = str(build / "runtime/skill-foundation/SKILL.md")
            event = {"tool_name": "apply_patch", "tool_input": {"input": "*** Begin Patch\n*** Update File: " + path + "\n*** End Patch"}} if platform == "codex" else {"tool_name": "Write", "tool_input": {"file_path": path, "content": "changed"}}
            result = self.hook(build, platform, "pre-tool", event, project)
            self.assertEqual((result.returncode, result.stdout), (0, ""), result.stderr)
            entry.write_text(entry.read_text() + "\n")
            restarted = self.run_core(build, project, "start", "--restart", "--set", "name=write-sample", "--set", "measure=skip", "文章を書くスキルを作る")
            self.assertEqual(restarted.returncode, 0, restarted.stdout + restarted.stderr)
            blocked = self.hook(build, platform, "stop", {}, project)
            self.assertEqual(json.loads(blocked.stdout).get("decision"), "block")
            waiting = self.run_core(build, project, "wait", "--question", "確認してください")
            self.assertEqual(waiting.returncode, 0, waiting.stderr)
            self.assertEqual(self.hook(build, platform, "stop", {}, project).stdout, "")
            self.assertEqual(self.hook(build, platform, "prompt", {}, project).returncode, 0)
            state = json.loads((project / ".skill-runs/skill-foundation/state.json").read_text())
            self.assertEqual(state["status"], "active")

    def test_tester_is_fenced_but_other_agents_are_not(self):
        project = self.workspace("fence")
        build = self.builds["claude-code"]
        lab = project / "lab"
        fence = lab / ".skill-runs/_fence"
        fence.mkdir(parents=True)
        (fence / "lab.json").write_text(json.dumps({"round": str(project / "round"), "language": "ja"}))
        (lab / "input.txt").write_text("sample")
        base = {"agent_type": "skill-foundation:skill-foundation-tester", "agent_id": "test-agent", "tool_name": "Read"}
        allowed = self.hook(build, "claude", "pre-tool", {**base, "tool_input": {"file_path": str(lab / "input.txt")}}, project)
        self.assertEqual(allowed.stdout, "")
        denied = self.hook(build, "claude", "pre-tool", {**base, "tool_input": {"file_path": str(project / "outside.txt")}}, project)
        self.assertEqual(json.loads(denied.stdout)["hookSpecificOutput"]["permissionDecision"], "deny")
        other = self.hook(build, "claude", "pre-tool", {**base, "agent_type": "other", "tool_input": {"file_path": str(project / "outside.txt")}}, project)
        self.assertEqual(other.stdout, "")

    def test_missing_runtime_fails_closed(self):
        build = self.root / "broken-plugin"
        (build / "scripts").mkdir(parents=True)
        (build / "scripts/hook.py").write_bytes((PLUGIN / "scripts/hook.py").read_bytes())
        result = self.hook(build, "codex", "pre-tool", {"tool_name": "apply_patch"}, self.root)
        self.assertEqual(json.loads(result.stdout)["hookSpecificOutput"]["permissionDecision"], "deny")

    def test_subagent_prepare_uses_packaged_agent(self):
        project = self.workspace("prepare")
        build = self.builds["claude-code"]
        core = build / "runtime/skill-foundation/scripts"
        assembled = subprocess.run([sys.executable, str(core / "selftest.py"), "--build", str(project)], capture_output=True, text=True)
        self.assertEqual(assembled.returncode, 0, assembled.stdout + assembled.stderr)
        skill = project / ".claude/skills/write-commit-message"
        evaluated = subprocess.run([sys.executable, str(core / "eval_check.py"), str(skill)],
                                   cwd=project, capture_output=True, text=True)
        self.assertEqual(evaluated.returncode, 0, evaluated.stdout + evaluated.stderr)
        result = subprocess.run([sys.executable, str(build / "scripts/convergence.py"), "prepare", str(skill), "--round", "1",
                                 "--runners", "subagent", "--agents", "1", "--workdir", str(project / "work")],
                                cwd=project, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("skill-foundation:skill-foundation-tester", result.stdout)
        self.assertFalse((project / ".claude/agents").exists())
        prompts = subprocess.run([sys.executable, str(build / "scripts/convergence.py"), "prompts",
                                  "--workdir", str(project / "work"), "--round", "1"],
                                 cwd=project, capture_output=True, text=True)
        self.assertEqual(prompts.returncode, 0, prompts.stdout + prompts.stderr)
        self.assertIn("subagent_type は skill-foundation:skill-foundation-tester", prompts.stdout)


if __name__ == "__main__":
    unittest.main()
