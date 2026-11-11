"""The speech engines local-tts can drive, which one a command uses, and how PyTorch engines install.

Every engine is a local HTTP server speaking the same /generate contract as s2.cpp (multipart
text/params/voice in, PCM16 with X-Audio-* headers out), so the controller stays free of ML packages.
- s2: Fish Audio S2 Pro through s2.cpp (C++; built by tools/scripts/setup-s2.*)
- omnivoice, voxcpm2: PyTorch models, each in its own uv project under tools/engines/<name>
  with its own virtual environment in <home>/cache/engines/<name>/.venv
- voicevox: a VOICEVOX ENGINE the user runs; its own API, no cloned voices
"""

import os
from pathlib import Path
import shutil
import subprocess
import sys

TOOLS = Path(__file__).resolve().parents[2]
DEFAULT = "voxcpm2"
ENGINES = {
    "omnivoice": {
        "kind": "python", "label": "OmniVoice", "url": "http://127.0.0.1:3032",
        "repo": "k2-fsa/OmniVoice", "license": "Apache-2.0",
        # Measured peak on an M4 (float16 on MPS); CUDA float16 needs about the same VRAM.
        "memory_gb": 4.5, "streaming": False, "api_model": "omnivoice",
        # Each call pays for the whole reference prompt (~12 s on an M4 for a 10 s reference,
        # 2.6 s without one), so fewer, longer requests are much faster than one per sentence.
        "request_chars": 200,
    },
    "voxcpm2": {
        "kind": "python", "label": "VoxCPM2", "url": "http://127.0.0.1:3031",
        "repo": "openbmb/VoxCPM2", "license": "Apache-2.0",
        # Model card: ~8 GB VRAM in bfloat16 on CUDA; 13.8 GB peak measured on an M4 (MPS).
        "memory_gb": 8.0, "streaming": True, "api_model": "voxcpm2",
        # Live playback head start per character. An M4 generated at RTF ~2.2 (about 0.2 s of
        # audio per Japanese character), so about 55% of a sentence must be ready first; CUDA is
        # expected to run faster than real time (not yet measured here), so no head start there.
        "start_buffer_ms_per_char": 120 if sys.platform == "darwin" else 0,
    },
    "s2": {
        "kind": "s2cpp", "label": "Fish Audio S2 Pro (s2.cpp)", "url": "http://127.0.0.1:3030",
        "license": "Fish Audio Research License (non-commercial; commercial use needs a separate agreement)",
        "memory_gb": 4.6, "streaming": True, "api_model": "s2-pro",
    },
    "voicevox": {
        "kind": "voicevox", "label": "VOICEVOX ENGINE", "url": "http://127.0.0.1:50021",
        "license": "per VOICEVOX character", "streaming": False, "api_model": "voicevox",
    },
}
# Before engines existed, `backend` named the transport; keep reading it.
LEGACY_BACKENDS = {"s2cpp": "s2", "voicevox": "voicevox"}
# Settings in [engines.<name>] that configure the server process rather than one request.
PROCESS_KEYS = {"url", "device", "dtype", "optimize", "timeout", "auto_start", "wait", "request_chars"}


class EngineError(ValueError):
    pass


def check(name):
    if name not in ENGINES:
        raise EngineError(f"Unknown engine: {name} (choose from {', '.join(ENGINES)})")
    return name


def upgrade(config):
    """Rewrite an old-style config (`backend` + a root `url` for that backend) in the new form:
    `engine` set, the url moved to [engines.<engine>]. A new-style root `url` is S2's address."""
    if "backend" not in config:
        return config
    old = config["backend"]
    if old not in LEGACY_BACKENDS:
        raise EngineError(f"Unknown backend: {old}")
    owner = LEGACY_BACKENDS[old]
    config = {k: v for k, v in config.items() if k != "backend"}
    config.setdefault("engine", owner)
    if owner != "s2" and "url" in config:
        sections = {**config.get("engines", {})}
        sections[owner] = {"url": config.pop("url"), **sections.get(owner, {})}
        config["engines"] = sections
    return config


def resolve(config, override=None):
    """Engine for this command: --engine, else config `engine` (or the old `backend`), else the default."""
    if override:
        return check(override)
    config = upgrade(config)
    if config.get("engine"):
        return check(config["engine"])
    return DEFAULT


def settings(config, name):
    return dict(upgrade(config).get("engines", {}).get(name, {}))


def url(config, name):
    """[engines.<name>] url, else the root `url` for S2, else the engine's default address."""
    config = upgrade(config)
    own = settings(config, name).get("url")
    if own:
        return own
    if name == "s2" and config.get("url"):
        return config["url"]
    return ENGINES[name]["url"]


def select(config, override=None):
    """A copy of config in the new form, bound to one engine (`engine` set). Callers ask url()
    for the bound engine's address; the root `url` remains S2's."""
    config = upgrade(config)
    return {**config, "engine": resolve(config, override)}


def request_chars(config, name=None):
    """Characters to send per request for engines that prefer long requests (0 = one per sentence)."""
    name = name or resolve(config)
    value = settings(config, name).get("request_chars", ENGINES[name].get("request_chars", 0))
    if not isinstance(value, int) or value < 0:
        raise EngineError(f"engines.{name}.request_chars must be 0 or a positive whole number")
    return value


def by_api_model(model):
    """Engine for an OpenAI `model` field; OpenAI's own names (tts-1, ...) mean the default."""
    for name, spec in ENGINES.items():
        if model in (name, spec["api_model"]):
            return name
    return None


# --- PyTorch engines: project, environment, model ---------------------------------------------

def project(name):
    return TOOLS / "engines" / name


def venv(name):
    from . import voices
    return voices.RUNTIME / "engines" / name / ".venv"


def python(name):
    folder = venv(name)
    return folder / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")


def hf_home():
    from . import voices
    return voices.RUNTIME / "huggingface"


def model_folder(name):
    repo = ENGINES[name]["repo"]
    return hf_home() / "hub" / ("models--" + repo.replace("/", "--"))


def model_ready(name):
    """A finished download leaves refs/main and a snapshot; an interrupted one may not."""
    folder = model_folder(name)
    return (folder / "refs" / "main").is_file() and any((folder / "snapshots").glob("*/*"))


def installed(name):
    return python(name).is_file()


def process_env(name, offline=True):
    """Environment for an engine process: its own HF cache inside <home>, no network at runtime."""
    from . import voices
    env = {**os.environ, "LOCAL_TTS_HOME": str(voices.HOME), "HF_HOME": str(hf_home()),
           "PYTHONUNBUFFERED": "1", "PYTHONIOENCODING": "utf-8",
           "TQDM_DISABLE": "1"}  # Progress bars would flood the server log.
    env.pop("HF_HUB_CACHE", None)
    if offline:
        env["HF_HUB_OFFLINE"] = "1"
    return env


def install(name, echo=print):
    """uv sync the engine's locked project into <home>/cache/engines/<name>/.venv, then fetch the model."""
    spec = ENGINES[check(name)]
    if spec["kind"] != "python":
        raise EngineError(f"{name} is not installed with this command (see references/setup.md)")
    uv = shutil.which("uv")
    if not uv:
        raise EngineError("uv is required to install an engine")
    env = {**os.environ, "UV_PROJECT_ENVIRONMENT": str(venv(name))}
    venv(name).parent.mkdir(parents=True, exist_ok=True)
    echo(f"Installing the {spec['label']} environment into {venv(name)} ...")
    done = subprocess.run([uv, "sync", "--project", str(project(name)), "--frozen", "--no-dev"], env=env)
    if done.returncode:
        raise EngineError(f"uv sync failed for {name} (exit {done.returncode})")
    echo(f"Downloading {spec['repo']} into {hf_home()} (skipped when already there) ...")
    done = subprocess.run([str(python(name)), str(project(name) / "server.py"), "--download"],
                          env=process_env(name, offline=False))
    if done.returncode or not model_ready(name):
        raise EngineError(f"The {spec['repo']} download did not finish (exit {done.returncode})")


def status(config):
    """One dict per engine for `engine list` and `doctor`."""
    result = []
    for name, spec in ENGINES.items():
        info = {"engine": name, "label": spec["label"], "url": url(config, name), "license": spec["license"]}
        if spec["kind"] == "python":
            info.update(installed=installed(name), model=model_ready(name), environment=str(venv(name)))
        result.append(info)
    return result
