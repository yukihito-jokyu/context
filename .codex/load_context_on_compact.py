import json
from pathlib import Path

context_path = Path(".codex/memory/context.md")

if not context_path.exists():
    print(json.dumps({"continue": True}))
    raise SystemExit(0)

content = context_path.read_text(encoding="utf-8").strip()

if not content:
    print(json.dumps({"continue": True}))
    raise SystemExit(0)

print(
    json.dumps(
        {
            "continue": True,
            "hookSpecificOutput": {
                "hookEventName": "SessionStart",
                "additionalContext": content,
            },
        },
        ensure_ascii=False,
    )
)
