#!/usr/bin/env python3
"""Build the requirements plugin without installing it or modifying its source."""
import argparse
import json
from pathlib import Path
import shutil


def ignore(directory, names):
    skipped = {n for n in names if n in {".git", "node_modules", "__pycache__", ".DS_Store"} or n.endswith(".pyc")}
    if Path(directory).name == "dev":
        skipped.update({"results", "convergence-report.md"} & set(names))
    return skipped


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--agent", choices=["codex", "claude-code"], required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    plugin = Path(__file__).resolve().parent
    repo = plugin.parents[2]
    definition = json.loads((plugin / "bundle.json").read_text(encoding="utf-8"))
    skill = (plugin / definition["skill"]).resolve()
    output = args.output.resolve()
    if output.exists() or args.output.is_symlink() or output.is_relative_to(repo):
        parser.error("Choose a new output directory outside the repository")
    manifest = json.loads((plugin / args.agent / "plugin.json").read_text(encoding="utf-8"))
    if (manifest["name"], manifest["version"]) != (definition["name"], definition["version"]) or args.agent not in definition["targets"]:
        parser.error("Bundle and manifest identity do not match")
    if json.loads((skill / "dev/spec.json").read_text(encoding="utf-8"))["status"] != "ready":
        parser.error("The canonical skill must be ready")
    output.mkdir(parents=True)
    folder = ".codex-plugin" if args.agent == "codex" else ".claude-plugin"
    (output / folder).mkdir()
    shutil.copyfile(plugin / args.agent / "plugin.json", output / folder / "plugin.json")
    (output / "hooks").mkdir()
    shutil.copyfile(plugin / args.agent / "hooks.json", output / "hooks/hooks.json")
    shutil.copytree(plugin / "scripts", output / "scripts", ignore=ignore)
    shutil.copytree(skill, output / "runtime" / definition["name"], ignore=ignore)
    entry = output / "skills" / definition["name"] / "SKILL.md"
    entry.parent.mkdir(parents=True)
    frontmatter = (skill / "SKILL.md").read_text(encoding="utf-8").split("---", 2)[1]
    entry.write_text("---" + frontmatter + "---\n\n" + (plugin / "entry.md").read_text(encoding="utf-8"), encoding="utf-8")
    shutil.copyfile(plugin / "README.md", output / "README.md")
    print(output)


if __name__ == "__main__":
    main()
