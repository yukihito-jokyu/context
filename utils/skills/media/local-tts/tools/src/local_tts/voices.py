"""Voices: a reference recording and its transcript in <home>/voices/, plus per-engine profiles.

A voice is <name>.wav (mono 44.1 kHz PCM16, peak-normalized) and <name>.json (its transcript and
notes): the only part that cannot be rebuilt, and what every engine clones from. Each engine's
profile lives in <home>/cache/voices/<engine>/ and is rebuilt from the recording when missing:
s2 keeps <name>.s2voice there (s2.cpp encodes it, about a minute on the CPU); the PyTorch
engines build theirs on first use. Before 2026-11-11 the .s2voice sat in voices/; such files move
to the cache on the next command, except for old voices that have no recording to rebuild from."""

from array import array
from datetime import datetime
import json
import math
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import wave

from .audio import AudioError
from . import home, runtime

# One home per user, shared by every project and kept across skill updates; see home.py.
HOME, HOME_WARNING = home.resolve()
RUNTIME = HOME / "cache"
VOICES = HOME / "voices"
CONFIG = HOME / "config.toml"
FILLER_CACHE = RUNTIME / "fillers"
NAME = re.compile(r"[A-Za-z0-9_-]+")
# s2.cpp recommends a 5-30 s reference; shorter clips clone poorly.
RECOMMENDED_SECONDS = (5, 30)


PROFILE_CACHE = RUNTIME / "voices"


def set_voice(config, name):
    """Select a registered voice by name (or an explicit .s2voice path); "default" drops the clone."""
    if name == "default":
        config.pop("voice", None)
        return
    if name.endswith(".s2voice"):
        path = Path(name)
        if not path.is_file():
            raise AudioError(f"Voice not found: {name}")
        config["voice"] = path.resolve().as_posix()
        return
    if name not in {p["name"] for p in profiles()}:
        names = ", ".join(["default"] + [p["name"] for p in profiles()])
        raise AudioError(f"Voice not found: {name} (available: {names})")
    config["voice"] = name


def s2_folder():
    return PROFILE_CACHE / "s2"


def s2_file(name):
    """Where the voice's S2 profile is: the cache, else an old voices/<name>.s2voice, else None."""
    for path in (s2_folder() / f"{name}.s2voice", VOICES / f"{name}.s2voice"):
        if path.is_file():
            return path
    return None


def move_legacy_s2_profiles():
    """Move voices/<name>.s2voice into cache/voices/s2/ when the recording to rebuild it exists."""
    for path in VOICES.glob("*.s2voice"):
        target = s2_folder() / path.name
        if (path.with_suffix(".wav").is_file() and path.with_suffix(".json").is_file()
                and not target.exists()):
            target.parent.mkdir(parents=True, exist_ok=True)
            os.replace(path, target)


def profiles():
    """Registered voices as dicts: name, path, s2 (has an S2 profile) and what `voice add` recorded."""
    names = {p.stem for p in VOICES.glob("*.s2voice")}  # Old voices without a recording
    names |= {p.stem for p in VOICES.glob("*.wav") if p.with_suffix(".json").is_file()}
    result = []
    for name in sorted(n for n in names if NAME.fullmatch(n)):
        meta = VOICES / f"{name}.json"
        try:
            info = json.loads(meta.read_text(encoding="utf-8")) if meta.is_file() else {}
        except (OSError, ValueError):
            info = {}  # A damaged note must not hide the voice (or block deleting it).
        if not isinstance(info, dict):
            info = {}
        s2 = s2_file(name)
        result.append({"name": name, "path": s2 or VOICES / f"{name}.wav", "s2": s2 is not None, **info})
    return result


def s2_profile(voice):
    """The .s2voice file s2.cpp loads for a voice name or path; a missing one is rebuilt from the
    recording first (the cache may have been cleared), which takes about a minute."""
    if str(voice).endswith(".s2voice"):
        path = Path(voice)
        if not path.is_file():
            raise AudioError(f"S2 profile not found: {voice}")
        return path
    found = s2_file(voice)
    if found:
        return found
    if not (VOICES / f"{voice}.wav").is_file():
        raise AudioError(f"Voice '{voice}' has no recording to build an S2 profile from")
    print(f"Encoding the S2 profile of '{voice}' from its recording (about a minute)...", file=sys.stderr)
    with tempfile.TemporaryDirectory() as folder:
        build_s2(voice, "これは確認です。", Path(folder) / "check.wav")
    return s2_folder() / f"{voice}.s2voice"


def reference(name):
    """(wav path, transcript) every engine clones from."""
    wav, meta = VOICES / f"{name}.wav", VOICES / f"{name}.json"
    if not wav.is_file() or not meta.is_file():
        raise AudioError(f"Voice '{name}' has no reference recording in {VOICES}")
    transcript = json.loads(meta.read_text(encoding="utf-8")).get("transcript", "").strip()
    if not transcript:
        raise AudioError(f"Voice '{name}' has no transcript in {meta}")
    return wav, transcript


def drop_derived(name, keep=()):
    """Forget everything built from a voice's recording: engine profiles and cached fillers.
    `keep` names engines whose profile was just made from the new recording."""
    for folder in PROFILE_CACHE.glob("*"):
        if folder.name in keep:
            continue
        for path in folder.glob(f"{name}.*"):
            path.unlink(missing_ok=True)
    (VOICES / f"{name}.s2voice").unlink(missing_ok=True)  # An old-layout S2 profile
    shutil.rmtree(FILLER_CACHE / name, ignore_errors=True)  # Before engines: fillers/<voice>
    for folder in FILLER_CACHE.glob("*"):
        shutil.rmtree(folder / name, ignore_errors=True)


def normalize(path, peak_db=-3.0, max_gain_db=20.0):
    """Scale a PCM16 WAV so its peak sits at peak_db; a quiet reference clones a quiet voice."""
    with wave.open(str(path), "rb") as clip:
        params = clip.getparams()
        samples = array("h", clip.readframes(clip.getnframes()))
    peak = max(map(abs, samples), default=0)
    if not peak:
        raise AudioError(f"Reference audio is silent: {path}")
    gain = min(10 ** (peak_db / 20) * 32767 / peak, 10 ** (max_gain_db / 20))
    scaled = array("h", (max(-32768, min(32767, round(s * gain))) for s in samples))
    with wave.open(str(path), "wb") as clip:
        clip.setparams(params)
        clip.writeframes(scaled.tobytes())
    return 20 * math.log10(gain)


def engine():
    """s2.cpp executable, model, tokenizer and its platform-specific environment."""
    try:
        profile = runtime.current()
    except ValueError as exc:
        raise AudioError(str(exc)) from exc
    executable = RUNTIME / profile["executable"]
    model = RUNTIME / "models" / "s2-pro-q4_k_m.gguf"
    for path in (executable, model, model.with_name("tokenizer.json")):
        if not path.is_file():
            raise AudioError(f"Missing {path}. Run tools/scripts/{profile['setup']} first.")
    env = dict(os.environ)
    cuda = RUNTIME / "s2-cuda-root.txt"
    if cuda.is_file():
        # utf-8-sig: Windows PowerShell 5.1 writes a BOM, which strip() would leave in the path.
        root = Path(cuda.read_text(encoding="utf-8-sig").strip())
        env["PATH"] = os.pathsep.join([str(root / "bin"), str(root / "bin" / "x64"), env["PATH"]])
    return executable, model, model.with_name("tokenizer.json"), env


def s2_ready():
    try:
        engine()
        return True
    except AudioError:
        return False


def s2_encode(staging, reference_wav, transcript, name, sample_text, sample_output, gpu):
    """Run s2.cpp to save staging/<name>.s2voice and speak sample_text into sample_output."""
    executable, model, tokenizer, env = engine()
    command = [str(executable), "--model", str(model), "--tokenizer", str(tokenizer),
               "--prompt-audio", str(reference_wav), "--prompt-text", transcript, "--voice", name,
               "--save-voice", "--voice-dir", str(staging), "--text", sample_text,
               "--output", str(sample_output)]
    if gpu:
        command += runtime.accelerator_args({}) + [runtime.codec_arg({})]
    Path(sample_output).parent.mkdir(parents=True, exist_ok=True)
    proc = subprocess.run(command, capture_output=True, text=True, encoding="utf-8",
                          errors="replace", env=env)
    if proc.returncode or not (staging / f"{name}.s2voice").is_file():
        tail = "\n".join((proc.stdout + proc.stderr).strip().splitlines()[-5:])
        raise AudioError(f"s2.cpp could not save the voice:\n{tail}")


def clone(name, audio, transcript, *, sample_text, sample_output, force=False, gpu=False,
          boost=True, s2=None):
    """Save `audio` (any format FFmpeg reads) and its exact transcript as a voice.

    s2: True requires an S2 profile, False skips it, None makes one when S2 is installed (then
    s2.cpp also speaks sample_text into sample_output; the CPU by default, so it does not compete
    with a TTS server holding the GPU). Returns the saved metadata, including warnings and
    whether the S2 profile was made."""
    if not NAME.fullmatch(name) or name == "default":
        raise AudioError("Voice names use letters, digits, - and _ only, and cannot be 'default'")
    if not transcript.strip():
        raise AudioError("The transcript is required: write exactly what the recording says")
    if (VOICES / f"{name}.wav").exists() or s2_file(name):
        if not force:
            raise AudioError(f"Voice already exists: {name} (use --force to replace it)")
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise AudioError("FFmpeg is required to read the reference audio")
    with_s2 = s2_ready() if s2 is None else s2
    if with_s2:
        engine()  # Fail before touching anything when S2 was required but is missing.
    VOICES.mkdir(parents=True, exist_ok=True)
    # Build everything in a staging folder and swap it in only after encoding succeeded, so a
    # failed `--force` re-clone (OOM, bad audio) leaves the existing voice untouched.
    staging = Path(tempfile.mkdtemp(prefix=f".{name}-", dir=VOICES))
    try:
        reference_wav = staging / f"{name}.wav"
        proc = subprocess.run([ffmpeg, "-v", "error", "-y", "-i", str(audio), "-ac", "1",
                               "-ar", "44100", "-sample_fmt", "s16", str(reference_wav)],
                              capture_output=True, text=True, encoding="utf-8", errors="replace")
        if proc.returncode:
            raise AudioError(f"FFmpeg could not read {audio}: {proc.stderr.strip()[-300:]}")
        gain_db = normalize(reference_wav) if boost else 0.0
        with wave.open(str(reference_wav), "rb") as clip:
            seconds = clip.getnframes() / clip.getframerate()
        if with_s2:
            s2_encode(staging, reference_wav, transcript, name, sample_text, sample_output, gpu)
        meta = {"transcript": transcript, "source": str(audio), "seconds": round(seconds, 2),
                "gain_db": round(gain_db, 1),
                "created": datetime.now().isoformat(timespec="seconds")}
        (staging / f"{name}.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n",
                                              encoding="utf-8")
        # The recording last: it marks the voice usable. The new S2 profile replaces the old one.
        for suffix in (".json", ".wav"):
            os.replace(staging / f"{name}{suffix}", VOICES / f"{name}{suffix}")
        if with_s2:
            s2_folder().mkdir(parents=True, exist_ok=True)
            os.replace(staging / f"{name}.s2voice", s2_folder() / f"{name}.s2voice")
    finally:
        shutil.rmtree(staging, ignore_errors=True)
    # Profiles and fillers are made per voice; a replaced voice must not reuse the old ones.
    drop_derived(name, keep=("s2",) if with_s2 else ())
    low, high = RECOMMENDED_SECONDS
    warnings = []
    if not low <= seconds <= high:
        warnings.append(f"Reference is {seconds:.1f} s; {low}-{high} s clones more reliably")
    return {**meta, "warnings": warnings, "s2": with_s2}


def build_s2(name, sample_text, sample_output, gpu=False):
    """(Re)create cache/voices/s2/<name>.s2voice from the saved recording and transcript."""
    reference_wav, transcript = reference(name)
    s2_folder().mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=f".{name}-", dir=s2_folder()))
    try:
        s2_encode(staging, reference_wav, transcript, name, sample_text, sample_output, gpu)
        os.replace(staging / f"{name}.s2voice", s2_folder() / f"{name}.s2voice")
        (VOICES / f"{name}.s2voice").unlink(missing_ok=True)  # The old-layout copy, if any
    finally:
        shutil.rmtree(staging, ignore_errors=True)
    shutil.rmtree(FILLER_CACHE / "s2" / name, ignore_errors=True)


def remove(name):
    """Delete a voice: its recording, metadata, S2 profile, engine profiles and cached fillers."""
    if not NAME.fullmatch(name) or name not in {p["name"] for p in profiles()}:
        raise AudioError(f"Voice not found: {name}")
    for suffix in (".s2voice", ".wav", ".json"):
        (VOICES / f"{name}{suffix}").unlink(missing_ok=True)
    drop_derived(name)
