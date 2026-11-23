"""Bring a finished WAV to a target integrated loudness (EBU R128 / BS.1770) with FFmpeg.

The default -14 LUFS with peaks under -1.5 dBFS is YouTube's recommendation. Raising the gain
alone would clip, since synthesized speech already peaks near 0 dBFS, so a limiter holds the
peaks; it costs some loudness, which re-measured corrections make up. Duration and
sample positions are unchanged, so the timing JSON (marks, segments) stays valid.
"""

import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile

from .audio import AudioError

DEFAULT_TARGET = -14.0
# Sample-peak ceiling (0.79 = -2.0 dBFS): under -1.5 dBFS with room for AAC encoding overshoot.
LIMIT = 0.79
TOLERANCE = 0.3  # LU
PASSES = 4  # Gain tries at most; each is a quick FFmpeg run over the finished file.


def target(config):
    """The configured target in LUFS, or None when `loudness = 0` turns it off."""
    value = float(config.get("loudness", DEFAULT_TARGET))
    return value if value else None


def measure(ffmpeg, path):
    """Integrated loudness in LUFS, or None when there is nothing above the gate (silence)."""
    proc = subprocess.run([ffmpeg, "-hide_banner", "-nostats", "-i", str(path),
                           "-af", "ebur128", "-f", "null", "-"], capture_output=True, text=True)
    found = re.findall(r"I:\s+(-?[\d.]+|-inf) LUFS", proc.stderr)
    if proc.returncode or not found:
        raise AudioError("FFmpeg could not measure loudness")
    value = float(found[-1])  # The last one is the summary.
    return value if value > -70 else None


def apply(ffmpeg, source, output, gain_db):
    proc = subprocess.run([ffmpeg, "-hide_banner", "-loglevel", "error", "-y", "-i", str(source),
                           "-af", f"volume={gain_db:.3f}dB,alimiter=limit={LIMIT}:level=false:latency=true",
                           "-c:a", "pcm_s16le", str(output)], capture_output=True, text=True)
    if proc.returncode:
        raise AudioError("FFmpeg could not adjust loudness: " + proc.stderr.strip())


def normalize(path, goal):
    """Rewrite the WAV at path to goal LUFS; return the measured result (None if silent)."""
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise AudioError("FFmpeg is required to normalize loudness (or set loudness = 0)")
    path = Path(path)
    before = measure(ffmpeg, path)
    if before is None:
        return None
    handle, adjusted = tempfile.mkstemp(prefix=".local-tts-", suffix=".wav", dir=path.parent)
    os.close(handle)
    try:
        # Past the limit 1 dB more gain yields only ~0.5 LU more (measured), so correct by the
        # slope seen between tries (secant) rather than by the shortfall itself.
        gain, previous = goal - before, (0.0, before)
        for _ in range(PASSES):
            apply(ffmpeg, path, adjusted, gain)
            after = measure(ffmpeg, adjusted)
            if after is None or abs(goal - after) <= TOLERANCE:
                break
            slope = (after - previous[1]) / (gain - previous[0]) if gain != previous[0] else 1.0
            previous = (gain, after)
            gain += (goal - after) / max(slope, 0.1)
        os.replace(adjusted, path)
        return after
    finally:
        Path(adjusted).unlink(missing_ok=True)
