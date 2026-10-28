#!/usr/bin/env python3
"""Rebuild and verify the plugin using its current repository sources.

This script requires the complete Context Repository, Python 3, Node.js, git,
and the Claude Code CLI (manifest validation only). It does not launch a model.
Use a new --workdir; results are written to its results/ directory.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import zipfile


def inventory(root):
    return {p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(root.rglob("*")) if p.is_file()
            and "__pycache__" not in p.parts and p.suffix != ".pyc"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--workdir", type=Path, required=True)
    args = parser.parse_args()
    repo, work = args.repo_root.resolve(), args.workdir.resolve()
    if work.exists():
        parser.error("--workdir must not exist")
    plugin = repo / "utils/plugins/skill-foundation"
    skill = repo / "utils/skills/authoring/skill-foundation"
    before_plugin, before_skill = inventory(plugin), inventory(skill)
    assert len(before_plugin) == 12 and len(before_skill) == 97
    work.mkdir(parents=True)
    results = work / "results"
    results.mkdir()
    (work / "unit-test-temp").mkdir()
    env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1", "TMPDIR": str(work / "unit-test-temp"),
           "CLAUDE_CONFIG_DIR": str(work / "isolated-claude-config")}
    commands, checks, bundles = [], [], {}
    aliases = [(str(repo), "<repository>"), (str(work), "<workdir>"),
               (str(Path.home()), "<user-home>"),
               (str(Path(tempfile.gettempdir()).resolve()), "<system-temp>"),
               (tempfile.gettempdir(), "<system-temp>")]

    def redact(value):
        for old, new in sorted(aliases, key=lambda item: len(item[0]), reverse=True):
            value = value.replace(old, new)
        return value

    def run(label, command, *, cwd=repo, stdin=None, extra_env=None, expected=0, shell=False):
        result = subprocess.run(command, cwd=cwd, input=stdin, text=True, capture_output=True,
                                env={**env, **(extra_env or {})}, shell=shell, timeout=180)
        commands.append({"label": label, "command": command, "shell": shell,
                         "cwd": str(cwd), "stdin": stdin, "exit_code": result.returncode,
                         "stdout": result.stdout, "stderr": result.stderr})
        assert result.returncode == expected, label + "\n" + result.stdout + result.stderr
        return result

    def check(label, **details):
        checks.append({"check": label, "status": "passed", **details})

    for agent, platform in [("codex", "codex"), ("claude-code", "claude")]:
        built = work / "build" / agent
        run(agent + ": build", ["python3", str(plugin / "build.py"), "--agent", agent,
                                "--output", str(built)])
        relocated = work / "relocated path with spaces" / agent
        relocated.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(built), relocated)
        assert not built.exists()
        archive = results / ("skill-foundation-" + agent + ".zip")
        with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as output:
            for file in sorted(relocated.rglob("*")):
                if file.is_file():
                    output.write(file, file.relative_to(relocated).as_posix())
        unpacked = work / "unpacked path with spaces" / agent
        with zipfile.ZipFile(archive) as source:
            assert source.testzip() is None
            source.extractall(unpacked)
        assert inventory(unpacked) == inventory(relocated)
        assert not any(p.is_symlink() for p in unpacked.rglob("*"))
        runtime = unpacked / "runtime/skill-foundation"
        assert inventory(runtime) == before_skill
        seal = json.loads((runtime / "assets/seal.json").read_text())
        assert len(seal["files"]) == 49
        assert all(inventory(runtime)[name] == digest for name, digest in seal["files"].items())
        run(agent + ": final runtime lint and seal", ["python3", str(runtime / "scripts/skill_lint.py"),
                                                    str(runtime), "--final"])
        metadata = ".codex-plugin" if agent == "codex" else ".claude-plugin"
        assert (unpacked / metadata / "plugin.json").read_bytes() == (plugin / agent / "plugin.json").read_bytes()
        manifest = json.loads((unpacked / metadata / "plugin.json").read_text())
        assert (manifest["name"], manifest["version"]) == ("skill-foundation", "0.1.0")
        frontmatter = (skill / "SKILL.md").read_text().split("---", 2)[1]
        assert (unpacked / "skills/skill-foundation/SKILL.md").read_text() == (
            "---" + frontmatter + "---\n\n" + (plugin / "entry.md").read_text())
        hooks = json.loads((unpacked / "hooks/hooks.json").read_text())["hooks"]
        assert set(hooks) == {"PreToolUse", "PostToolUse", "Stop", "UserPromptSubmit"}
        assert (unpacked / "hooks/hooks.json").read_bytes() == (plugin / agent / "hooks.json").read_bytes()
        if agent == "claude-code":
            tester = (unpacked / "agents/skill-foundation-tester.md").read_text()
            assert "hooks:" not in tester.split("---", 2)[1]
            assert hooks["PreToolUse"][0]["matcher"] == "*"
        else:
            assert not (unpacked / "agents").exists()
            assert manifest["skills"] == "./skills/" and manifest["hooks"] == "./hooks/hooks.json"
        check(agent + ": relocation, zip, extraction, runtime, seal, manifest, thin entry, hooks",
              distribution_files=len(inventory(unpacked)), runtime_files=97, sealed_files=49,
              archive_sha256=hashlib.sha256(archive.read_bytes()).hexdigest())
        project = work / ("project-" + agent)
        project.mkdir()
        run(agent + ": project init", ["git", "init", "-q", str(project)])

        def hook(event_name, payload, label):
            command = hooks[event_name][0]["hooks"][0]["command"]
            return run(agent + ": " + label, command, shell=True, cwd=project,
                       stdin=json.dumps({"cwd": str(project), **payload}, ensure_ascii=False),
                       extra_env={"CLAUDE_PLUGIN_ROOT": str(unpacked), "PLUGIN_ROOT": str(unpacked)})

        tool = "apply_patch" if platform == "codex" else "Write"
        for event in hooks:
            result = hook(event, {"tool_name": tool}, "inactive " + event)
            assert result.stdout == ""
        run(agent + ": start", ["python3", str(runtime / "scripts/run.py"), "start", "--set",
                                "name=write-sample", "--set", "measure=skip", "文章を書くスキルを作る"], cwd=project)

        def edit(path):
            if platform == "codex":
                return {"tool_name": "apply_patch", "tool_input": {
                    "input": "*** Begin Patch\n*** Update File: " + str(path) + "\n*** End Patch"}}
            return {"tool_name": "Write", "tool_input": {"file_path": str(path), "content": "changed"}}

        protected = hook("PreToolUse", edit(runtime / "SKILL.md"), "protected runtime edit")
        decision = json.loads(protected.stdout)["hookSpecificOutput"]["permissionDecision"]
        assert decision == ("deny" if platform == "codex" else "ask")
        malformed = project / ".claude/skills/write-sample/SKILL.md"
        malformed.parent.mkdir(parents=True)
        malformed.write_text("# Broken output\n")
        post = hook("PostToolUse", edit(malformed), "malformed output feedback")
        assert json.loads(post.stdout)["decision"] == "block"
        stopped = hook("Stop", {}, "unfinished output stop")
        assert json.loads(stopped.stdout)["decision"] == "block"
        run(agent + ": wait", ["python3", str(runtime / "scripts/run.py"), "wait", "--question", "検証用の質問"], cwd=project)
        assert hook("Stop", {}, "waiting stop").stdout == ""
        assert hook("UserPromptSubmit", {}, "waiting resume").stdout == ""
        assert json.loads((project / ".skill-runs/skill-foundation/state.json").read_text())["status"] == "active"
        check(agent + ": configured hook commands directly executed", events=list(hooks),
              protected_edit_decision=decision, post_tool_decision="block", stop_decision="block",
              wait_stop_output="", resumed_status="active")

        if agent == "claude-code":
            lab = project / "lab"
            fence = lab / ".skill-runs/_fence"
            fence.mkdir(parents=True)
            (fence / "lab.json").write_text(json.dumps({"round": str(project / "round"), "language": "ja"}))
            (lab / "input.txt").write_text("sample")
            base = {"agent_type": "skill-foundation:skill-foundation-tester", "agent_id": "validation-agent", "tool_name": "Read"}
            assert hook("PreToolUse", {**base, "tool_input": {"file_path": str(lab / "input.txt")}}, "tester allowed read").stdout == ""
            denied = hook("PreToolUse", {**base, "tool_input": {"file_path": str(project / "outside.txt")}}, "tester denied outside read")
            assert json.loads(denied.stdout)["hookSpecificOutput"]["permissionDecision"] == "deny"
            assert hook("PreToolUse", {**base, "agent_type": "other", "tool_input": {"file_path": str(project / "outside.txt")}}, "unrelated agent read").stdout == ""
            check("Claude namespaced tester fence", allowed_inside=True, denied_outside=True, unrelated_agent_transparent=True)

        preparation = work / ("preparation-" + agent)
        preparation.mkdir()
        run(agent + ": build convergence fixture", ["python3", str(runtime / "scripts/selftest.py"), "--build", str(preparation)])
        generated = preparation / ".claude/skills/write-commit-message"
        prepared = run(agent + ": convergence prepare", ["python3", str(unpacked / "scripts/convergence.py"), "prepare",
                       str(generated), "--round", "1", "--runners", "subagent", "--agents", "1",
                       "--workdir", str(preparation / "work")], cwd=preparation)
        assert "skill-foundation:skill-foundation-tester" in prepared.stdout
        prompts = run(agent + ": convergence prompts", ["python3", str(unpacked / "scripts/convergence.py"), "prompts",
                      "--workdir", str(preparation / "work"), "--round", "1"], cwd=preparation)
        assert "subagent_type は skill-foundation:skill-foundation-tester" in prompts.stdout
        assert not list(preparation.rglob(".claude/agents"))
        assert not list(preparation.rglob(".agents/agents"))
        check(agent + ": convergence prepare/prompts", project_agent_directories=0,
              tester_type="skill-foundation:skill-foundation-tester", independent_ai_sessions=0)
        bundles[agent] = {"distribution_files": len(inventory(unpacked)), "runtime_files": 97,
                          "sealed_files": 49, "runtime_inventory": inventory(runtime)}
    tests = run("plugin-owned tests", ["python3", "-m", "unittest", "discover", "-s",
                "utils/plugins/skill-foundation/tests", "-p", "test_*.py", "-v"])
    assert re.search(r"Ran 7 tests", tests.stdout + tests.stderr)
    (results / "unit-tests.log").write_text(redact(tests.stdout + tests.stderr))
    check("plugin-owned unit tests", count=7)
    assert shutil.which("claude"), "Claude Code CLI is required only for local manifest validation"
    validation = run("Claude manifest validation", ["claude", "plugin", "validate",
                    str(work / "unpacked path with spaces/claude-code")])
    (results / "manifest-validation.log").write_text(redact(validation.stdout + validation.stderr))
    check("Claude Code CLI manifest validation", model_sessions=0, isolated_config_directory=True)
    assert inventory(plugin) == before_plugin and inventory(skill) == before_skill
    check("canonical sources unchanged", plugin_files=12, skill_files=97)
    record = {"checked_at": datetime.now(timezone.utc).isoformat(), "status": "passed",
              "purpose": "Rebuild plugin artifacts after moving plugin-only tests under their owner",
              "checks": checks, "bundles": bundles, "commands": commands,
              "source_unchanged": {"plugin": True, "skill": True},
              "unit_test_command": "python3 -m unittest discover -s utils/plugins/skill-foundation/tests -p 'test_*.py' -v",
              "not_verified": ["Automatic hooks from a real product session", "Codex hooks trust UI",
                               "Independent AI convergence execution", "Project installation (recorded separately by parent)"],
              "redactions": ["repository absolute path → <repository>", "temporary workdir → <workdir>",
                             "user home absolute path → <user-home>", "system temporary path → <system-temp>"],
              "reproduction": "Run this script with --repo-root pointing to the complete current repository and a new --workdir. The plugin-owned tests are imported from that repository; copying a test file alone is insufficient."}
    (results / "validation.json").write_text(redact(json.dumps(record, ensure_ascii=False, indent=2)) + "\n")
    lines = ["skill-foundation plugin: PASS", "", "Checks:"]
    lines.extend("PASS " + json.dumps(item, ensure_ascii=False) for item in checks)
    lines.extend(["", "Commands executed:"])
    for command in commands:
        lines.extend(["", command["label"], "command: " + json.dumps(command["command"], ensure_ascii=False),
                      "cwd: " + command["cwd"], "exit: " + str(command["exit_code"]),
                      "stdout:\n" + command["stdout"], "stderr:\n" + command["stderr"]])
    lines.extend(["", "Not verified:", *record["not_verified"], "", "Redactions:", *record["redactions"],
                  "", "Reproduction:", record["reproduction"]])
    (results / "verification.txt").write_text(redact("\n".join(lines)) + "\n")
    print(json.dumps({"status": "passed", "results": str(results), "checks": len(checks),
                      "commands": len(commands), "bundle_files": {k: v["distribution_files"] for k, v in bundles.items()}}))


if __name__ == "__main__":
    main()
