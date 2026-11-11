"""Where local-tts keeps voices, settings and caches, and the move from the old presenter-tts folder.

One home per user, shared by every project and kept across skill updates (like uv's cache):
%LOCALAPPDATA%\\local-tts on Windows, ~/.local/share/local-tts elsewhere; LOCAL_TTS_HOME overrides it.
cache/ holds what can be rebuilt (engines, models, fillers) and may be deleted any time; voices/,
config.toml and api-key.txt cannot be rebuilt.

Until 2026-11 the folder was called presenter-tts and shared with the presenter skill.
`migrate()` copies what cannot be rebuilt and moves the large caches into the new folder.
"""

import json
import os
from pathlib import Path
import shutil
import sys

NAME = "local-tts"
LEGACY_NAME = "presenter-tts"
LEGACY_ENV = "PRESENTER_TTS_HOME"
# Hugging Face model folders of the PyTorch engines, moved out of the user's shared HF cache.
HF_MODEL_FOLDERS = ("models--k2-fsa--OmniVoice", "models--openbmb--VoxCPM2")
MARKER = "MOVED-TO-local-tts.txt"


def base(environ=None):
    environ = os.environ if environ is None else environ
    return Path(environ.get("LOCALAPPDATA") or Path.home() / ".local" / "share")


def resolve(environ=None):
    """(home, warning): LOCAL_TTS_HOME, else the old PRESENTER_TTS_HOME (with a warning), else default."""
    environ = os.environ if environ is None else environ
    if environ.get("LOCAL_TTS_HOME"):
        return Path(environ["LOCAL_TTS_HOME"]), None
    if environ.get(LEGACY_ENV):
        return Path(environ[LEGACY_ENV]), f"{LEGACY_ENV} is deprecated; rename it to LOCAL_TTS_HOME"
    return base(environ) / NAME, None


def legacy(environ=None):
    return base(environ) / LEGACY_NAME


def explicit(environ=None):
    environ = os.environ if environ is None else environ
    return bool(environ.get("LOCAL_TTS_HOME") or environ.get(LEGACY_ENV))


def needs_migration(home, old):
    """True when only the old folder holds voices or settings, so commands should stop and say so."""
    keep = ("voices", "config.toml", "api-key.txt")
    return (not any((home / name).exists() for name in keep)
            and any((old / name).exists() for name in keep))


def hf_hub_cache(environ=None):
    """The user's Hugging Face hub cache, the way huggingface_hub resolves it."""
    environ = os.environ if environ is None else environ
    if environ.get("HF_HUB_CACHE"):
        return Path(environ["HF_HUB_CACHE"])
    if environ.get("HF_HOME"):
        return Path(environ["HF_HOME"]) / "hub"
    cache = environ.get("XDG_CACHE_HOME")
    return (Path(cache) if cache else Path.home() / ".cache") / "huggingface" / "hub"


def size(path):
    if path.is_file() or path.is_symlink():
        return path.lstat().st_size
    return sum(p.lstat().st_size for p in path.rglob("*") if p.is_file() and not p.is_symlink())


def plan(home, old, hub, platform=None):
    """Actions as dicts {action: copy|move|skip, what, source, target, bytes, note}."""
    platform = platform or sys.platform
    actions = []

    def add(action, what, source, target, note=""):
        actions.append({"action": action, "what": what, "source": str(source), "target": str(target),
                        "bytes": size(source) if source.exists() else 0, "note": note})

    # Cannot be rebuilt: copy, and leave the originals for tools that still read the old folder.
    for name in ("voices", "api-key.txt", "config.toml", *sorted(p.name for p in old.glob("config.*.toml"))):
        source, target = old / name, home / name
        if not source.exists():
            continue
        if target.exists():
            add("skip", name, source, target, "already in the new folder; left unchanged")
        else:
            add("copy", name, source, target)
    # Can be rebuilt but large or slow to rebuild: move.
    cache = old / "cache"
    if cache.is_dir():
        for source in sorted(cache.iterdir()):
            target = home / "cache" / source.name
            if source.suffix == ".pid":
                add("skip", f"cache/{source.name}", source, target, "process id of an old server")
            elif source.name == "s2-build" and platform == "darwin":
                add("skip", "cache/s2-build", source, target,
                    "macOS binaries link their libraries by absolute path; rebuild with setup-s2.sh")
            elif target.exists():
                add("skip", f"cache/{source.name}", source, target, "already in the new folder")
            else:
                note = "CMake's cache is dropped so a later rebuild configures afresh" \
                    if source.name == "s2-build" else ""
                add("move", f"cache/{source.name}", source, target, note)
    for folder in HF_MODEL_FOLDERS:
        source, target = hub / folder, home / "cache" / "huggingface" / "hub" / folder
        if not source.is_dir():
            continue
        if target.exists():
            add("skip", f"model {folder}", source, target, "already in the new folder")
        else:
            add("move", f"model {folder}", source, target, "Hugging Face cache (relative links inside)")
    return actions


def migrate(home, old, hub, platform=None):
    """Carry out plan(); returns the actions done. Copies never overwrite, moves never replace."""
    actions = plan(home, old, hub, platform)
    home.mkdir(parents=True, exist_ok=True)
    for item in actions:
        source, target = Path(item["source"]), Path(item["target"])
        if item["action"] == "copy":
            if source.is_dir():
                shutil.copytree(source, target, copy_function=shutil.copy2)
            else:
                shutil.copy2(source, target)
        elif item["action"] == "move":
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(source), str(target))
            if target.name == "s2-build":
                (target / "CMakeCache.txt").unlink(missing_ok=True)
                shutil.rmtree(target / "CMakeFiles", ignore_errors=True)
    if old.is_dir():
        (old / MARKER).write_text(
            f"local-tts now keeps its data in {home}\n"
            "Voices, config.toml and api-key.txt were copied there and are still here; "
            "the caches were moved.\n", encoding="utf-8")
    (home / "cache").mkdir(exist_ok=True)
    (home / "cache" / "migrated-from.json").write_text(
        json.dumps({"from": str(old), "actions": actions}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8")
    return actions
