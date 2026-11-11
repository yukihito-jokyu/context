"""The skill's instructions must point at files and commands that exist, so a move or rename
cannot silently leave an agent following a dead path."""
import _isolated_home  # noqa: F401  (must come before local_tts)

from pathlib import Path
import re
import unittest

from typer.main import get_command

from local_tts.cli import app

SKILL = Path(__file__).resolve().parents[2]
DOCS = [SKILL / "SKILL.md", *sorted((SKILL / "references").glob("*.md"))]


def frontmatter():
    block = (SKILL / "SKILL.md").read_text(encoding="utf-8").split("---", 2)[1]
    return {k: v.strip() for k, v in re.findall(r"^([a-z-]+):(.*)$", block, re.M)}


class SkillLayoutTests(unittest.TestCase):
    def test_frontmatter_follows_the_agent_skills_spec(self):
        meta = frontmatter()
        self.assertEqual(meta["name"], SKILL.name)
        self.assertLessEqual(len(meta["description"]), 1024)
        self.assertLessEqual(len(meta["compatibility"]), 500)

    def test_referenced_files_exist(self):
        for path in DOCS:
            body = path.read_text(encoding="utf-8")
            for link in re.findall(r"\]\((?!https?:)([^)#]+)", body):
                self.assertTrue((path.parent / link).exists(), f"{path.name}: {link}")
            for rel in re.findall(r"<local-tts>/(tools/[\w./-]+)", body):
                self.assertTrue((SKILL / rel.rstrip("/.")).exists(), f"{path.name}: {rel}")

    def test_documented_commands_exist(self):
        commands = get_command(app).commands
        names = set(commands) | {f"{group} {sub}" for group, cmd in commands.items()
                                 if hasattr(cmd, "commands") for sub in cmd.commands}
        for path in DOCS:
            for used in re.findall(r"local-tts ([a-z]+(?: [a-z]+)?)", path.read_text(encoding="utf-8")):
                first = used.split()[0]
                self.assertTrue(used in names or first in names, f"{path.name}: local-tts {used}")

    def test_deck_commands_stay_out(self):
        for removed in ("narrate", "play", "video"):
            self.assertNotIn(removed, get_command(app).commands)


if __name__ == "__main__":
    unittest.main()
