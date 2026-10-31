#!/usr/bin/env python3
"""Route plugin-owned hook events to the unchanged requirements runtime."""
import argparse
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
CORE = ROOT / "runtime/write-requirement-document"
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
    for file in ["scripts/hook.py", "scripts/_skillrt.py", "assets/contract.json"]:
        if not (CORE / file).is_file():
            raise ValueError("Missing bundled runtime: " + file)
    result = subprocess.run([sys.executable, str(CORE / "scripts/hook.py"), "--platform", args.platform, args.event],
                            input=raw, text=True, capture_output=True)
    if result.returncode:
        raise ValueError("The bundled hook failed: " + result.stderr[-1000:])
    sys.stdout.write(result.stdout)
    sys.stderr.write(result.stderr)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (OSError, ValueError) as exc:
        if sys.argv[-1] == "pre-tool":
            print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny",
                              "permissionDecisionReason": f"write-requirement-document plugin: {exc}"}}, ensure_ascii=False))
        else:
            print(f"write-requirement-document plugin: {exc}", file=sys.stderr)
            sys.exit(2)
