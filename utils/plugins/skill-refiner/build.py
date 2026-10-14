#!/usr/bin/env python3
"""Build the skill-refiner plugin from its canonical skill and agent-specific config."""
import argparse
import json
from pathlib import Path
import shutil


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--agent", choices=["codex", "claude-code"], required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    plugin = Path(__file__).resolve().parent
    definition = json.loads((plugin / "bundle.json").read_text())
    output = Path(args.output).resolve()
    if output.exists():
        raise SystemExit("Output already exists; choose a new build directory")
    skill = (plugin / definition["skill"]).resolve()
    if output.is_relative_to(skill) or output.is_relative_to(plugin):
        raise SystemExit("Output must be outside the canonical sources")
    output.mkdir(parents=True)
    manifest_dir = output / (".codex-plugin" if args.agent == "codex" else ".claude-plugin")
    manifest_dir.mkdir()
    shutil.copyfile(plugin / args.agent / "plugin.json", manifest_dir / "plugin.json")
    (output / "hooks").mkdir()
    shutil.copyfile(plugin / args.agent / "hooks.json", output / "hooks/hooks.json")
    shutil.copytree(plugin / "scripts", output / "scripts", ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    shutil.copytree(skill, output / "skills/skill-refiner", ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    print(output)


if __name__ == "__main__":
    main()
