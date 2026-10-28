#!/usr/bin/env python3
"""Build skill-foundation without changing its sealed canonical source."""
import argparse
import json
from pathlib import Path
import shutil
import sys


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--agent", choices=["codex", "claude-code"], required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    plugin = Path(__file__).resolve().parent
    definition = json.loads((plugin / "bundle.json").read_text(encoding="utf-8"))
    skill = (plugin / definition["skill"]).resolve()
    output = args.output.resolve()
    if output.exists() or output.is_relative_to(plugin) or output.is_relative_to(skill):
        parser.error("Choose a new output directory outside the canonical sources")
    sys.path.insert(0, str(skill / "scripts"))
    import _skillrt as rt
    if rt.seal_findings(skill, rt.load_contract(skill)):
        parser.error("The canonical skill does not match assets/seal.json")
    manifest = json.loads((plugin / args.agent / "plugin.json").read_text(encoding="utf-8"))
    if (manifest["name"], manifest["version"]) != (definition["name"], definition["version"]):
        parser.error("Bundle and manifest identity do not match")
    ignore = shutil.ignore_patterns("__pycache__", "*.pyc", ".DS_Store")
    output.mkdir(parents=True)
    folder = ".codex-plugin" if args.agent == "codex" else ".claude-plugin"
    (output / folder).mkdir()
    shutil.copyfile(plugin / args.agent / "plugin.json", output / folder / "plugin.json")
    (output / "hooks").mkdir()
    shutil.copyfile(plugin / args.agent / "hooks.json", output / "hooks/hooks.json")
    shutil.copytree(plugin / "scripts", output / "scripts", ignore=ignore)
    shutil.copytree(skill, output / "runtime/skill-foundation", ignore=ignore)
    # The entry owns only plugin integration. The complete sealed skill stays byte-identical.
    entry = output / "skills/skill-foundation/SKILL.md"
    entry.parent.mkdir(parents=True)
    frontmatter = (skill / "SKILL.md").read_text(encoding="utf-8").split("---", 2)[1]
    entry.write_text("---" + frontmatter + "---\n\n" + (plugin / "entry.md").read_text(encoding="utf-8"), encoding="utf-8")
    if args.agent == "claude-code":
        shutil.copytree(plugin / "agents", output / "agents", ignore=ignore)
    shutil.copyfile(plugin / "README.md", output / "README.md")
    print(output)


if __name__ == "__main__":
    main()
