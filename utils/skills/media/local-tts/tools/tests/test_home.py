import _isolated_home  # noqa: F401  (must come before local_tts)
import os
from pathlib import Path
import re
import tempfile
import unittest
from unittest.mock import patch

from typer.testing import CliRunner

from local_tts import home
from local_tts.cli import app

SKILL = Path(__file__).resolve().parents[2]


def legacy_folder(root):
    old = root / "presenter-tts"
    (old / "voices").mkdir(parents=True)
    (old / "voices" / "me.wav").write_bytes(b"RIFF")
    (old / "voices" / "me.json").write_text('{"transcript": "hi"}', encoding="utf-8")
    (old / "config.toml").write_text('voice = "me"\n', encoding="utf-8")
    (old / "config.before-x.toml").write_text("", encoding="utf-8")
    (old / "api-key.txt").write_text("secret", encoding="ascii")
    build = old / "cache" / "s2-build"
    (build / "CMakeFiles").mkdir(parents=True)
    (build / "CMakeCache.txt").write_text("cache", encoding="utf-8")
    (build / "s2").write_bytes(b"bin")
    (old / "cache" / "models").mkdir()
    (old / "cache" / "models" / "s2.gguf").write_bytes(b"x" * 10)
    (old / "cache" / "s2-server.pid").write_text("123", encoding="ascii")
    return old


class HomeTests(unittest.TestCase):
    def test_resolve_prefers_the_new_variable_and_warns_on_the_old(self):
        self.assertEqual(home.resolve({"LOCAL_TTS_HOME": "/a", "PRESENTER_TTS_HOME": "/b"}), (Path("/a"), None))
        path, warning = home.resolve({"PRESENTER_TTS_HOME": "/b"})
        self.assertEqual(path, Path("/b"))
        self.assertIn("LOCAL_TTS_HOME", warning)
        self.assertEqual(home.resolve({"LOCALAPPDATA": r"C:\Users\me\AppData\Local"})[0],
                         Path(r"C:\Users\me\AppData\Local") / "local-tts")

    def test_needs_migration_only_when_the_new_folder_is_empty(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            old = legacy_folder(root)
            new = root / "local-tts"
            self.assertTrue(home.needs_migration(new, old))
            (new / "voices").mkdir(parents=True)
            self.assertFalse(home.needs_migration(new, old))

    def test_macos_keeps_s2_build_and_skips_pid_files(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            old, new, hub = legacy_folder(root), root / "local-tts", root / "hub"
            actions = {a["what"]: a for a in home.plan(new, old, hub, platform="darwin")}
            self.assertEqual(actions["voices"]["action"], "copy")
            self.assertEqual(actions["config.before-x.toml"]["action"], "copy")
            self.assertEqual(actions["cache/s2-build"]["action"], "skip")
            self.assertEqual(actions["cache/s2-server.pid"]["action"], "skip")
            self.assertEqual(actions["cache/models"]["action"], "move")
            self.assertFalse(new.exists(), "plan() must not touch the disk")

    def test_migrate_copies_keepsakes_moves_caches_and_models(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            old, new, hub = legacy_folder(root), root / "local-tts", root / "hub"
            model = hub / "models--k2-fsa--OmniVoice" / "snapshots" / "abc"
            model.mkdir(parents=True)
            (model / "config.json").write_text("{}", encoding="utf-8")
            home.migrate(new, old, hub, platform="win32")
            # Copied and still in the old folder.
            self.assertEqual((new / "voices" / "me.json").read_text(encoding="utf-8"), '{"transcript": "hi"}')
            self.assertTrue((old / "voices" / "me.json").is_file())
            self.assertEqual((new / "api-key.txt").read_text(encoding="ascii"), "secret")
            # Moved; on Windows s2-build moves too, without CMake's absolute-path cache.
            self.assertTrue((new / "cache" / "models" / "s2.gguf").is_file())
            self.assertFalse((old / "cache" / "models").exists())
            self.assertTrue((new / "cache" / "s2-build" / "s2").is_file())
            self.assertFalse((new / "cache" / "s2-build" / "CMakeCache.txt").exists())
            self.assertFalse((new / "cache" / "s2-build" / "CMakeFiles").exists())
            self.assertFalse((new / "cache" / "s2-server.pid").exists())
            self.assertTrue((new / "cache" / "huggingface" / "hub" / "models--k2-fsa--OmniVoice").is_dir())
            self.assertFalse((hub / "models--k2-fsa--OmniVoice").exists())
            self.assertTrue((old / home.MARKER).is_file())
            self.assertTrue((new / "cache" / "migrated-from.json").is_file())

    def test_migrate_never_overwrites_the_new_folder(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            old, new = legacy_folder(root), root / "local-tts"
            new.mkdir()
            (new / "config.toml").write_text('voice = "kept"\n', encoding="utf-8")
            home.migrate(new, old, root / "hub", platform="darwin")
            self.assertEqual((new / "config.toml").read_text(encoding="utf-8"), 'voice = "kept"\n')

    def test_commands_stop_while_only_the_old_folder_has_voices(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            legacy_folder(root)
            with patch.dict(os.environ, {"LOCALAPPDATA": str(root)}), \
                    patch("local_tts.voices.HOME", root / "local-tts"), \
                    patch("local_tts.home.explicit", return_value=False):
                result = CliRunner().invoke(app, ["voice", "list"])
                self.assertEqual(result.exit_code, 2)
                self.assertIn("home migrate", result.output)
                self.assertEqual(CliRunner().invoke(app, ["home", "show"]).exit_code, 0)


class RenameTests(unittest.TestCase):
    def test_old_names_stay_only_where_they_describe_the_history(self):
        allowed = {"upstream.md", "home.py", "test_home.py", "_isolated_home.py", "setup-s2.sh", "setup-s2.ps1", "cli.py"}
        pattern = re.compile(r"presenter[_-]tts|PRESENTER_TTS|presenter\.example")
        for path in SKILL.rglob("*"):
            if not path.is_file() or ".venv" in path.parts or "__pycache__" in path.parts \
                    or path.suffix not in {".py", ".md", ".toml", ".sh", ".ps1", ".swift"}:
                continue
            for line in path.read_text(encoding="utf-8").splitlines():
                if pattern.search(line) and path.name not in allowed and not any(word in line for word in ("旧", "presenterスキル", "presenter-ttsを使っていた")):
                    self.fail(f"{path.relative_to(SKILL)}: {line.strip()}")


if __name__ == "__main__":
    unittest.main()
