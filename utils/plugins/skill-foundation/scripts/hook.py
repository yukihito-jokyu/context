#!/usr/bin/env python3
"""Connect plugin events to the unmodified skill runtime and tester fence."""
import argparse
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "runtime/skill-foundation/scripts"
TESTER = "skill-foundation:skill-foundation-tester"
EDIT_TOOLS = {"claude": {"Edit", "Write", "MultiEdit", "NotebookEdit"}, "codex": {"apply_patch"}}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--platform", choices=["claude", "codex"], required=True)
    parser.add_argument("event", choices=["pre-tool", "post-tool", "stop", "prompt"])
    args = parser.parse_args()
    raw = sys.stdin.read()
    event = json.loads(raw or "{}")
    if not isinstance(event, dict):
        raise ValueError("Expected a hook event object")
    # Plugin agent frontmatter cannot register hooks. Fence its calls here instead.
    if args.platform == "claude" and event.get("agent_type") == TESTER:
        if args.event != "pre-tool":
            return 0
        command = [sys.executable, str(SCRIPTS / "fence.py"), "--platform", "claude", "--agent"]
    else:
        if args.event in {"pre-tool", "post-tool"} and event.get("tool_name") not in EDIT_TOOLS[args.platform]:
            return 0
        command = [sys.executable, str(SCRIPTS / "hook.py"), "--platform", args.platform, args.event]
    result = subprocess.run(command, input=raw, text=True, capture_output=True)
    if args.event == "pre-tool" and result.returncode:
        raise ValueError("The bundled hook could not evaluate this operation: " + result.stderr[-1000:])
    sys.stdout.write(result.stdout)
    sys.stderr.write(result.stderr)
    return result.returncode


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (OSError, ValueError) as exc:
        if sys.argv[-1] == "pre-tool":
            print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny",
                              "permissionDecisionReason": f"skill-foundation plugin: {exc}"}}, ensure_ascii=False))
        else:
            print(f"skill-foundation plugin: {exc}", file=sys.stderr)
            sys.exit(2)
