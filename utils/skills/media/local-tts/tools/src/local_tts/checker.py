"""Reading check: what each sentence of a `speak` WAV sounds like, in katakana (Kana Whisper).

The recognizer is a PyTorch model, so like the engines it lives in its own uv project
(tools/checkers/kana-whisper) with its own environment in <home>/cache/checkers/kana-whisper/.venv,
installed on first use; the controller only starts it and reads its JSON.
"""

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

from .audio import AudioError
from .engines import TOOLS, hf_home

NAME = "kana-whisper"
REPO = "sbintuitions/kana-whisper"


def project():
    return TOOLS / "checkers" / NAME


def venv():
    from . import voices
    return voices.RUNTIME / "checkers" / NAME / ".venv"


def python():
    return venv() / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")


def model_ready():
    folder = hf_home() / "hub" / ("models--" + REPO.replace("/", "--"))
    return (folder / "refs" / "main").is_file() and any((folder / "snapshots").glob("*/*"))


def env(offline=True):
    from . import voices
    result = {**os.environ, "LOCAL_TTS_HOME": str(voices.HOME), "HF_HOME": str(hf_home()),
              "PYTHONIOENCODING": "utf-8", "TQDM_DISABLE": "1"}
    result.pop("HF_HUB_CACHE", None)
    if offline:
        result["HF_HUB_OFFLINE"] = "1"
    return result


def install(echo=print):
    """uv sync the locked checker project, then download the model (both skipped when present)."""
    if python().is_file() and model_ready():
        return
    uv = shutil.which("uv")
    if not uv:
        raise AudioError("uv is required to install the reading check")
    venv().parent.mkdir(parents=True, exist_ok=True)
    echo(f"Installing the reading check (Kana Whisper) into {venv()} ...")
    done = subprocess.run([uv, "sync", "--project", str(project()), "--frozen", "--no-dev"],
                          env={**os.environ, "UV_PROJECT_ENVIRONMENT": str(venv())})
    if done.returncode:
        raise AudioError(f"uv sync failed for the reading check (exit {done.returncode})")
    echo(f"Downloading {REPO} into {hf_home()} (skipped when already there) ...")
    done = subprocess.run([str(python()), str(project() / "check.py"), "--download"], env=env(offline=False))
    if done.returncode or not model_ready():
        raise AudioError(f"The {REPO} download did not finish (exit {done.returncode})")


def check(wav, timing, segments=(), echo=print):
    """[{segment, text, heard}] for the 1-based segment numbers given (all when empty)."""
    wav, timing = Path(wav), Path(timing)
    for path in (wav, timing):
        if not path.is_file():
            raise AudioError(f"Not found: {path} (make it with speak first)")
    install(echo)
    done = subprocess.run([str(python()), str(project() / "check.py"), str(wav), str(timing),
                           *map(str, segments)], env=env(), capture_output=True, text=True,
                          encoding="utf-8")
    if done.returncode:
        raise AudioError("The reading check failed: " + done.stderr.strip()[-2000:])
    return json.loads(done.stdout)
