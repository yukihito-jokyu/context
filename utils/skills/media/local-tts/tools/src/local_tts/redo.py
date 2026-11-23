"""Regenerate chosen segments of a `speak` WAV in place and shift the timing JSON to match.

The rest of the audio is kept as it was. A new segment is first brought to the loudness of the one
it replaces, so the finished file is only touched up by the usual normalization afterwards.
"""

import json
import os
from pathlib import Path
import shutil
import tempfile
import time
import wave

from . import loudness
from .audio import AudioError, transform
from .ssml import Speech


def synthesize(backend, event, rate, channels):
    with backend.synthesize(event.text, live=False) as (fmt, chunks):
        if (fmt.rate, fmt.channels) != (rate, channels):
            raise AudioError(f"The engine now returns {fmt.rate} Hz/{fmt.channels} ch, the WAV has "
                             f"{rate} Hz/{channels} ch; use the engine speak used (--engine)")
        data = b"".join(transform(chunks, fmt, event.style))
    if not data or len(data) % fmt.frame_bytes:
        raise AudioError("TTS returned no audio or an incomplete PCM frame")
    return data


def match_level(old, new, params, folder):
    """new raised or lowered to old's integrated loudness (unchanged when either is too quiet)."""
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise AudioError("FFmpeg is required to match loudness (or set loudness = 0)")
    paths = []
    try:
        for data in (old, new, b""):
            handle, path = tempfile.mkstemp(prefix=".local-tts-", suffix=".wav", dir=folder)
            os.close(handle)
            paths.append(path)
            with wave.open(path, "wb") as wav:
                wav.setparams(params)
                wav.writeframes(data)
        before, after = loudness.measure(ffmpeg, paths[0]), loudness.measure(ffmpeg, paths[1])
        if before is None or after is None:
            return new
        loudness.apply(ffmpeg, paths[1], paths[2], before - after)
        with wave.open(paths[2], "rb") as wav:
            return wav.readframes(wav.getnframes())
    finally:
        for path in paths:
            Path(path).unlink(missing_ok=True)


def redo(events, backend, output, numbers):
    """Replace the 1-based segments `numbers`; return [{segment, text, seconds}] of what was redone."""
    output = Path(output)
    metadata = output.with_suffix(".json")
    if not output.is_file() or not metadata.is_file():
        raise AudioError(f"{output} and {metadata.name} are needed (make them with speak first)")
    report = json.loads(metadata.read_text(encoding="utf-8"))
    segments = report["segments"]
    speech = [e for e in events if isinstance(e, Speech)]
    if [e.text for e in speech] != [s["text"] for s in segments]:
        raise AudioError(f"The script no longer matches {metadata.name}; run speak again instead")
    if not numbers:
        raise AudioError("Give the segments to redo, e.g. --segments 6,9")
    for number in numbers:
        if not 1 <= number <= len(segments):
            raise AudioError(f"Segment {number} is out of range 1-{len(segments)}")
    goal = loudness.target(backend.config)
    with wave.open(str(output), "rb") as wav:
        params = wav.getparams()
        audio = wav.readframes(wav.getnframes())
    frame_bytes = params.nchannels * params.sampwidth

    replaced = {}
    for number in sorted(set(numbers)):
        segment = segments[number - 1]
        started = time.perf_counter()
        new = synthesize(backend, speech[number - 1], params.framerate, params.nchannels)
        if goal is not None:
            old = audio[segment["start_frame"] * frame_bytes:segment["end_frame"] * frame_bytes]
            new = match_level(old, new, params, output.parent)
        replaced[number] = (new, time.perf_counter() - started)

    # Rebuild the audio and move every later frame position by the change in length so far.
    pieces, cursor, moves = [], 0, []
    for number, segment in enumerate(segments, 1):
        if number not in replaced:
            continue
        start, end = segment["start_frame"], segment["end_frame"]
        new, seconds = replaced[number]
        pieces += [audio[cursor * frame_bytes:start * frame_bytes], new]
        cursor = end
        moves.append((end, len(new) // frame_bytes - (end - start)))
    pieces.append(audio[cursor * frame_bytes:])

    def shifted(frame):
        return frame + sum(delta for end, delta in moves if end <= frame)

    for number, segment in enumerate(segments, 1):
        start = shifted(segment["start_frame"])
        if number in replaced:
            new, seconds = replaced[number]
            segment.update(start_frame=start, end_frame=start + len(new) // frame_bytes,
                           generation_seconds=seconds)
        else:
            segment.update(start_frame=start, end_frame=shifted(segment["end_frame"]))
    for mark in report["marks"]:
        mark["frame"] = shifted(mark["frame"])
        mark["audio_seconds"] = mark["frame"] / params.framerate
    total = sum(delta for _, delta in moves)
    report["audio_seconds"] += total / params.framerate
    report["speech_seconds"] += total / params.framerate

    handle, temporary = tempfile.mkstemp(prefix=".local-tts-", suffix=".wav", dir=output.parent)
    os.close(handle)
    try:
        with wave.open(temporary, "wb") as wav:
            wav.setparams(params)
            wav.writeframes(b"".join(pieces))
        if goal is not None:
            loudness.normalize(temporary, goal)
        os.replace(temporary, output)
    finally:
        Path(temporary).unlink(missing_ok=True)
    metadata.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return [{"segment": n, "text": segments[n - 1]["text"], "seconds": round(replaced[n][1], 1)}
            for n in sorted(replaced)]
