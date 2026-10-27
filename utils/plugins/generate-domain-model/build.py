#!/usr/bin/env python3
"""Build generate-domain-model with its canonical skill and agent-specific hooks."""
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
    definition = json.loads((plugin / "bundle.json").read_text(encoding="utf-8"))
    skill = (plugin / definition["skill"]).resolve()
    output = Path(args.output).resolve()
    if output.exists():
        parser.error("Output already exists; choose a new build directory")
    if output.is_relative_to(skill) or output.is_relative_to(plugin):
        parser.error("Output must be outside the canonical sources")
    spec = json.loads((skill / "dev/spec.json").read_text(encoding="utf-8"))
    if spec["status"] != "ready" or not (skill / "assets/seal.json").is_file():
        parser.error("Build the validated, sealed skill first")
    manifest = json.loads((plugin / args.agent / "plugin.json").read_text(encoding="utf-8"))
    if manifest["name"] != definition["name"] or args.agent not in definition["targets"]:
        parser.error("Bundle and manifest do not match")
    output.mkdir(parents=True)
    manifest_dir = output / (".codex-plugin" if args.agent == "codex" else ".claude-plugin")
    manifest_dir.mkdir()
    shutil.copyfile(plugin / args.agent / "plugin.json", manifest_dir / "plugin.json")
    (output / "hooks").mkdir()
    shutil.copyfile(plugin / args.agent / "hooks.json", output / "hooks/hooks.json")
    shutil.copytree(skill, output / "skills" / definition["name"],
                    ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".DS_Store"))
    print(output)


if __name__ == "__main__":
    main()
