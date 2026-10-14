#!/usr/bin/env python3
"""Agent hook adapter. No evaluator context is injected into generation agents."""
import json
import os
from pathlib import Path
import sys

PLUGIN = Path(__file__).resolve().parents[1]
CORE = PLUGIN / "skills" / "skill-refiner" / "scripts"
if not CORE.is_dir():
    CORE = PLUGIN.parents[1] / "skills" / "authoring" / "skill-refiner" / "scripts"
sys.path.insert(0, str(CORE))
from refine import RefineError, integrity, locked, log, read_json, register, require


def workspace_for(event):
    configured = os.environ.get("SKILL_REFINER_WORKSPACE")
    if configured:
        return Path(configured).resolve()
    root = Path(event.get("cwd", ".")).resolve()
    for folder in (root, *root.parents):
        marker = folder / ".skill-refiner-active.json"
        if marker.is_file():
            return Path(read_json(marker)["workspace"]).resolve()
    return None


def is_spawn(name):
    return name in ("Agent", "Task", "spawn_agent", "collaboration.spawn_agent") or name.endswith("__spawn_agent")


def pending_ticket(state, event):
    args = event.get("tool_input") or {}
    prompt = args.get("prompt", args.get("message"))
    found = [r for r in state["runs"] if r["status"] == "pending" and r["prompt"] == prompt]
    require(len(found) == 1, "generate a ticket and pass its exact prompt")
    require(not args.get("resume") and not args.get("resume_id"), "use a fresh agent")
    if "spawn_agent" in event.get("tool_name", ""):
        require(args.get("fork_turns") == "none", "spawn with fork_turns=none")
    run = found[0]
    require(not run.get("hook_authorized"), "ticket has already authorized a launch")
    require(run["iteration"] == state["iteration"], "ticket belongs to an old iteration")
    require((run["role"] == "generate" and state["stage"] == "generating") or
            (run["role"] == "evaluate" and state["stage"] == "evaluating"), "stage does not permit this ticket")
    require(not any(not r["processed"] for r in state["responses"]), "handle submitted HTML responses first")
    return run


def edit_paths(event):
    args = event.get("tool_input") or {}
    result = []
    for key in ("file_path", "path"):
        if isinstance(args.get(key), str):
            result.append(args[key])
    patch = args.get("patch", args.get("input", args.get("command", "")))
    if isinstance(patch, str):
        for line in patch.splitlines():
            for prefix in ("*** Add File: ", "*** Update File: ", "*** Delete File: ", "*** Move to: "):
                if line.startswith(prefix):
                    result.append(line[len(prefix):])
    return [Path(event.get("cwd", "."), path).resolve() for path in result]


def check_edit(state, event):
    for path in edit_paths(event):
        workspace = Path(state["workspace"])
        target = Path(state["target"])
        candidate = Path(state["skill"])
        if path.is_relative_to(target):
            raise RefineError("only the approved promote command can change the target")
        if path.is_relative_to(candidate):
            raise RefineError("candidate changes are applied by the approved analysis only")
        elif path.is_relative_to(workspace):
            outputs = [Path(r["output"]) for r in state["runs"] if r["status"] == "running"]
            require(any(path.is_relative_to(out) for out in outputs), "use the controller for workflow records")


def extract_id(response):
    if isinstance(response, str):
        try:
            return extract_id(json.loads(response))
        except ValueError:
            return None
    if isinstance(response, dict):
        for key in ("agent_id", "agentId"):
            if isinstance(response.get(key), str):
                return response[key]
        for key in ("structuredContent", "result", "content", "output", "text"):
            value = extract_id(response.get(key))
            if value:
                return value
    if isinstance(response, list):
        for item in response:
            value = extract_id(item)
            if value:
                return value
    return None


def handle(event):
    workspace = workspace_for(event)
    if workspace is None:
        return {}
    with locked(workspace) as state:
        kind = event.get("hook_event_name")
        tool = event.get("tool_name", "")
        if kind == "PreToolUse":
            if is_spawn(tool):
                run = pending_ticket(state, event)
                run["authorized_session"] = event.get("session_id")
                run["hook_authorized"] = True
            elif any(word in tool for word in ("resume_agent", "send_message", "followup_task")):
                raise RefineError("do not reuse a generation or evaluation agent")
            elif tool in ("Write", "Edit", "apply_patch"):
                check_edit(state, event)
        elif kind == "PostToolUse" and is_spawn(tool):
            args = event.get("tool_input") or {}
            prompt = args.get("prompt", args.get("message"))
            runs = [r for r in state["runs"] if r["prompt"] == prompt and r.get("hook_authorized")]
            require(len(runs) == 1, "spawn was not authorized by a ticket")
            agent_id = extract_id(event.get("tool_response", event.get("tool_result")))
            if agent_id:
                register(state, runs[0]["id"], agent_id)
            else:
                log(state, "hook_id_unavailable", run_id=runs[0]["id"])
        elif kind == "SubagentStart":
            agent_id = event.get("agent_id")
            already = [r for r in state["runs"] if r["agent_id"] == agent_id]
            if not already:
                pending = [r for r in state["runs"] if r["status"] == "pending" and
                           r.get("hook_authorized") and r.get("authorized_session") == event.get("session_id")]
                if len(pending) == 1 and agent_id:
                    register(state, pending[0]["id"], agent_id)
                else:
                    log(state, "hook_id_unavailable", agent_id=agent_id)
        state["hook_checks"].append({"event": kind, "tool": tool, "result": "observed"})
    return {}


def main():
    event = json.load(sys.stdin)
    try:
        print(json.dumps(handle(event)))
    except (RefineError, OSError, ValueError, KeyError) as exc:
        kind = event.get("hook_event_name")
        if kind == "PreToolUse":
            print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse",
                  "permissionDecision": "deny", "permissionDecisionReason": str(exc)}}))
        else:
            # This reports a failure; SubagentStart cannot prevent the launch.
            print(str(exc), file=sys.stderr)
            sys.exit(2)


if __name__ == "__main__":
    main()
