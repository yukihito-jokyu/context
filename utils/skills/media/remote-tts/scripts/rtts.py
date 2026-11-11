#!/usr/bin/env python3
"""Client for a local-tts (formerly presenter-tts) OpenAI-compatible speech API on another machine.

When the remote API cannot be used, `speak` falls back to the local-tts skill on this machine
(.claude/skills/local-tts next to this skill). Standard library only; FFmpeg is needed only for
non-WAV output. See ../SKILL.md.
"""
import argparse
import array
import hashlib
import http.client
import json
import os
from pathlib import Path
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
import wave
from xml.sax.saxutils import escape

CONFIG = Path(os.environ.get("RTTS_CONFIG", "~/.config/remote-tts/config.json")).expanduser()
SECONDS_PER_CHAR = 0.85  # Measured: 273 chars took 233 s; short texts are a little faster.
# Local generation seconds per character, plus model loading (about 20-30 s). Measured on an M4:
# S2 1.7 with loading (116 chars, 199 s); OmniVoice 0.3 (100 chars, 29.8 s); VoxCPM2 0.33. Rounded up.
LOCAL_SECONDS_PER_CHAR = {"s2": 2.0, "omnivoice": 0.4, "voxcpm2": 0.45}
# The API's `model` per local-tts engine; older presenter-tts servers ignore it (and use S2).
API_MODELS = {"s2": "s2-pro", "omnivoice": "omnivoice", "voxcpm2": "voxcpm2"}
LOCAL_MAX_CHARS = 300  # The local SSML compiler rejects a longer speech span.
CONNECT_TIMEOUT = 5
CONNECT_ATTEMPTS = 3  # A single 6 s Wi-Fi hiccup once caused a needless switch to the slower engine.
CONNECT_WAIT = 3
MAX_INPUT = 4096  # Server limit for one request.
TIMEOUT = 1800  # Busy servers queue requests silently, so the wait can be long.
RETRY_WAITS = (5, 15)
ENCODERS = {
    ".mp3": ["-c:a", "libmp3lame", "-b:a", "128k"],
    ".m4a": ["-c:a", "aac", "-b:a", "128k"],
    ".ogg": ["-c:a", "libopus", "-b:a", "64k"],
    ".opus": ["-c:a", "libopus", "-b:a", "64k"],
    ".flac": ["-c:a", "flac"],
}
SSML = re.compile(r"<\s*/?\s*(speak|break|prosody|emphasis|sub|mark|s|p)(\s[^>]*)?/?>", re.I)
SENTENCE = re.compile(r"[^。！？!?\n]+[。！？!?]*")
SPEAKABLE = re.compile(r"[^\W_]")
OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))  # LAN: never via a proxy.


class Fatal(Exception):
    """A failure that neither retrying nor the other engine can fix."""


class Unavailable(Exception):
    """The remote API cannot be used right now, so the local engine may take over."""


class Transient(Unavailable):
    """An Unavailable worth retrying first: connection trouble, a cut-off stream, or a 503."""


def log(message):
    print(message, file=sys.stderr, flush=True)


def load_config():
    config = {}
    if CONFIG.is_file():
        try:
            config = json.loads(CONFIG.read_text(encoding="utf-8"))
        except ValueError as error:
            raise Fatal(f"{CONFIG} is not valid JSON: {error}")
    config["base_url"] = (os.environ.get("RTTS_BASE_URL") or config.get("base_url") or "").rstrip("/")
    config["api_key"] = os.environ.get("RTTS_API_KEY") or config.get("api_key")
    return config


def require_remote(config):
    """Fail in seconds, not after the OS connect timeout, but ride out a brief network drop."""
    if not config["base_url"] or not config["api_key"]:
        raise Unavailable(f"No API settings: create {CONFIG} (base_url, api_key, voice, known_voices) "
                          "or set RTTS_BASE_URL and RTTS_API_KEY")
    url = urllib.parse.urlsplit(config["base_url"])
    port = url.port or (443 if url.scheme == "https" else 80)
    reason = None
    for attempt in range(CONNECT_ATTEMPTS):
        if attempt:
            time.sleep(CONNECT_WAIT)
        try:
            with socket.create_connection((url.hostname, port), timeout=CONNECT_TIMEOUT):
                return
        except OSError as error:
            reason = error
    raise Unavailable(f"Cannot reach {config['base_url']}: {reason}")


def call(config, path, payload=None):
    """One HTTP exchange returning the whole body; a truncated stream raises Transient."""
    headers = {"Authorization": f"Bearer {config['api_key']}"}
    data = None
    if payload is not None:
        data = json.dumps(payload).encode()
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(config["base_url"] + path, data=data, headers=headers)
    try:
        with OPENER.open(request, timeout=TIMEOUT) as response:
            return response.read()
    except urllib.error.HTTPError as error:
        try:
            message = json.loads(error.read())["error"]["message"]
        except (ValueError, KeyError, TypeError):
            message = error.reason
        if error.code == 401:
            raise Unavailable("HTTP 401: the API key is missing or wrong (check the config file)")
        if error.code == 503:
            raise Transient(f"HTTP 503: {message}")
        if error.code == 400:
            raise Fatal(f"HTTP 400: {message}")
        raise Unavailable(f"HTTP {error.code}: {message}")
    except http.client.IncompleteRead as error:
        raise Transient(f"The audio stream was cut off after {len(error.partial)} bytes")
    except (urllib.error.URLError, socket.timeout, ConnectionError, http.client.HTTPException) as error:
        raise Transient(f"Cannot reach {config['base_url']}: {getattr(error, 'reason', error)}")


def with_retries(action):
    for wait in (*RETRY_WAITS, None):
        try:
            return action()
        except Transient as error:
            if wait is None:
                raise
            log(f"  retrying in {wait}s: {error}")
            time.sleep(wait)


def parse_wav(data):
    """(channels, sample_width, rate, pcm) from a WAV the API streamed.

    The API writes through a pipe, so its RIFF and data sizes are 0xFFFFFFFF; the real end is
    the end of the bytes."""
    if data[:4] != b"RIFF" or data[8:12] != b"WAVE":
        raise Transient("The response is not a WAV file")
    position, fmt = 12, None
    while position + 8 <= len(data):
        chunk, size = data[position:position + 4], int.from_bytes(data[position + 4:position + 8], "little")
        body = position + 8
        if chunk == b"fmt ":
            fmt = (int.from_bytes(data[body + 2:body + 4], "little"),
                   int.from_bytes(data[body + 14:body + 16], "little") // 8,
                   int.from_bytes(data[body + 4:body + 8], "little"))
        elif chunk == b"data":
            if fmt is None:
                raise Transient("The WAV has no format chunk")
            pcm = data[body:min(body + size, len(data))]
            return (*fmt, pcm[:len(pcm) - len(pcm) % (fmt[0] * fmt[1])])
        position = body + size + (size & 1)
    raise Transient("The WAV has no audio data")


def check_audible(fmt, pcm):
    channels, width, rate = fmt
    if not pcm or width != 2:
        raise Transient("The audio is empty or not 16-bit")
    if not any(array.array("h", pcm)):
        raise Transient("The audio is pure silence")
    return len(pcm) / (channels * width * rate)


def clauses(sentence, limit):
    """Cut a sentence longer than the limit at 、 or a space, else hard at the limit."""
    pieces = []
    while len(sentence) > limit:
        window = sentence[:limit]
        cut = max(window.rfind("、"), window.rfind("，"), window.rfind(" "))
        cut = cut + 1 if cut > 0 else limit
        pieces.append(sentence[:cut])
        sentence = sentence[cut:]
    return pieces + [sentence] if sentence else pieces


def sentences(paragraph, limit):
    found = []
    for match in SENTENCE.finditer(paragraph):
        text = match.group().strip()
        if not SPEAKABLE.search(text):
            continue  # Punctuation alone makes the server answer 503.
        if text[-1] not in "。！？!?.…":
            text += "。" if not text.isascii() else ". "  # Keep a heading from running into the next line.
        found.extend(clauses(text, limit))
    return found


def plan(text, limit):
    """Requests to make, as (text, starts_new_paragraph)."""
    parts = []
    for paragraph in re.split(r"\n\s*\n", text):
        current, fresh = "", True
        for sentence in sentences(paragraph, limit):
            if current and len(current) + len(sentence) > limit:
                parts.append((current, fresh))
                current, fresh = "", False
            current += sentence
        if current:
            parts.append((current, fresh))
    return parts


def fmt_time(seconds):
    return f"{int(seconds // 60)}m{int(seconds % 60):02d}s" if seconds >= 60 else f"{seconds:.0f}s"


def read_input(args):
    if args.file:
        return Path(args.file).read_text(encoding="utf-8")
    if args.text == "-":
        return sys.stdin.read()
    if args.text:
        return args.text
    raise Fatal("Give the text as an argument, as - for stdin, or with --file")


def synthesize(config, text, voice, speed, engine=None):
    def attempt():
        data = call(config, "/audio/speech", {"model": API_MODELS.get(engine, "tts-1"), "voice": voice,
                                              "input": text, "response_format": "wav", "speed": speed})
        channels, width, rate, pcm = parse_wav(data)
        check_audible((channels, width, rate), pcm)
        return (channels, width, rate), pcm
    return with_retries(attempt)


def write_wav(path, fmt, frames):
    with wave.open(str(path), "wb") as out:
        out.setnchannels(fmt[0])
        out.setsampwidth(fmt[1])
        out.setframerate(fmt[2])
        for chunk in frames:
            out.writeframes(chunk)


def read_wav(path):
    with wave.open(str(path), "rb") as source:
        return (source.getnchannels(), source.getsampwidth(), source.getframerate()), \
            source.readframes(source.getnframes())


def local_project():
    """The local-tts skill's tools (RTTS_LOCAL_TTS overrides the skill folder)."""
    skill = Path(os.environ.get("RTTS_LOCAL_TTS") or Path(__file__).resolve().parents[2] / "local-tts")
    project = skill / "tools"
    if not (project / "pyproject.toml").is_file():
        raise Fatal(f"The local-tts skill is missing at {skill}; the local fallback needs it")
    if not shutil.which("uv"):
        raise Fatal("uv is required to run the local engine")
    return project


def local_cli(project, *arguments, **options):
    return subprocess.run(["uv", "run", "--quiet", "--project", str(project), "local-tts", *arguments],
                          text=True, encoding="utf-8", **options)


def local_status(project, engine=None):
    """{ready, voices, engine} for local-tts's engine (`engine`, else its configured default)."""
    done = local_cli(project, "doctor", capture_output=True)
    try:
        info = json.loads(done.stdout)
        engine = engine or info["selected_engine"]
        if engine == "s2":
            ready = bool(info["engine"]["ready"])
        else:
            found = [e for e in info["engines"] if e["engine"] == engine]
            ready = bool(found and found[0].get("installed") and found[0].get("model"))
        return {"ready": ready, "voices": list(info["home"]["voices"]), "engine": engine,
                "needs_migration": bool(info["home"].get("needs_migration"))}
    except (ValueError, KeyError, TypeError, IndexError):
        raise Fatal(f"The local engine could not be checked: {done.stderr.strip()[:300]}")


def command_check(args):
    config = load_config()
    try:
        require_remote(config)
        started = time.perf_counter()
        try:
            models = [m["id"] for m in json.loads(with_retries(lambda: call(config, "/models")))["data"]]
        except (ValueError, KeyError, TypeError):
            raise Unavailable(f"{config['base_url']} did not answer like the speech API")
        result = {"backend": "remote", "base_url": config["base_url"], "models": models,
                  "latency_ms": round((time.perf_counter() - started) * 1000),
                  "voice": config.get("voice")}
        if args.synth:
            started = time.perf_counter()
            fmt, pcm = synthesize(config, "接続を確認しています。", config.get("voice") or "default", 1.0,
                                  args.engine or config.get("engine"))
            result["synth_seconds"] = round(time.perf_counter() - started, 1)
            result["audio_seconds"] = round(check_audible(fmt, pcm), 2)
    except Unavailable as error:
        result = {"backend": None, "remote_error": str(error), "local_ready": False}
        try:
            status = local_status(local_project(), args.engine or config.get("engine"))
            result.update(local_ready=status["ready"], local_voices=status["voices"],
                          local_engine=status["engine"], backend="local" if status["ready"] else None)
        except Fatal as local_error:
            result["local_error"] = str(local_error)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["backend"] else 1


def deliver(joined, output):
    """Move a finished WAV into place, encoding it first when the output is not WAV."""
    suffix = output.suffix.lower()
    if suffix == ".wav":
        os.replace(joined, output)
        return
    encoded = output.with_name(f".{output.stem}.encoding{suffix}")
    done = subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(joined),
                           *ENCODERS[suffix], str(encoded)], stderr=subprocess.PIPE, text=True)
    if done.returncode:
        encoded.unlink(missing_ok=True)
        raise Fatal(f"FFmpeg failed: {done.stderr.strip()[:300]}")
    os.replace(encoded, output)


def generate_remote(config, parts, voice, args, output):
    """Generate through the API, keeping finished parts so a rerun can resume."""
    require_remote(config)
    if not voice:
        raise Unavailable("No voice is configured for the remote API")
    cache = output.with_name(output.name + ".parts")
    cache.mkdir(exist_ok=True)
    fmt, frames, generated = None, [], 0
    for index, (part, fresh) in enumerate(parts):
        key = hashlib.sha256(f"{args.engine}\0{voice}\0{args.speed}\0{part}".encode()).hexdigest()[:16]
        path = cache / f"{index:04d}-{key}.wav"
        if path.is_file():
            part_fmt, pcm = read_wav(path)
            log(f"[{index + 1}/{len(parts)}] reused from an earlier run")
        else:
            t0 = time.perf_counter()
            part_fmt, pcm = synthesize(config, part, voice, args.speed, args.engine)
            temporary = path.with_suffix(".tmp")
            write_wav(temporary, part_fmt, [pcm])
            os.replace(temporary, path)
            generated += 1
            log(f"[{index + 1}/{len(parts)}] {len(part)} chars in {fmt_time(time.perf_counter() - t0)}")
        if fmt and part_fmt != fmt:
            raise Fatal("The audio format changed between requests")
        fmt = part_fmt
        if fresh and index and args.gap > 0:
            frames.append(bytes(int(args.gap * fmt[2]) * fmt[0] * fmt[1]))
        frames.append(pcm)
    joined = output.with_name(f".{output.stem}.joining.wav")
    write_wav(joined, fmt, frames)
    try:
        deliver(joined, output)
    finally:
        joined.unlink(missing_ok=True)
    shutil.rmtree(cache)
    return {"backend": "remote", "audio_seconds": sum(len(f) for f in frames) / (fmt[0] * fmt[1] * fmt[2]),
            "requests": len(parts), "generated": generated, "voice": voice,
            "engine_requested": args.engine or "(server default)"}


def to_ssml(parts, speed, gap):
    """The plain-text plan as the SSML the local engine takes."""
    body = []
    for index, (part, fresh) in enumerate(parts):
        if fresh and index and gap > 0:
            body.append(f'<break time="{round(gap * 1000)}ms"/>')
        body.append(f"<s>{escape(part.strip())}</s>")
    content = "".join(body)
    if speed != 1:
        content = f'<prosody rate="{speed * 100:g}%">{content}</prosody>'
    return ('<?xml version="1.0" encoding="UTF-8"?>\n'
            '<speak xmlns="http://www.w3.org/2001/10/synthesis" version="1.1" xml:lang="ja-JP">'
            f"{content}</speak>")


def generate_local(config, text, voice, args, output):
    """Generate everything with the local engine, so one file never mixes two machines' audio."""
    if not .5 <= args.speed <= 2:
        raise Fatal("The local engine supports --speed from 0.5 to 2.0 only")
    project = local_project()
    status = local_status(project, args.engine)
    if status["needs_migration"]:
        raise Fatal("local-tts still has its voices in the old presenter-tts folder; run local-tts home migrate "
                    "(needs the user's approval)")
    if not status["ready"]:
        raise Fatal(f"The local {status['engine']} engine is not set up; follow references/local-setup.md "
                    "(needs the user's approval)")
    engine = ["--engine", status["engine"]]
    if voice and voice != "default" and voice not in status["voices"]:
        raise Fatal(f"Voice {voice!r} is not registered locally (available: {', '.join(status['voices'])})")
    state = local_cli(project, "server", "status", *engine, capture_output=True)
    was_running = "not running" not in state.stdout
    workspace = Path(tempfile.mkdtemp(prefix=".rtts-local-", dir=output.parent))
    try:
        wav = workspace / "local.wav"
        ssml = to_ssml(plan(text, min(args.max_chars, LOCAL_MAX_CHARS)), args.speed, args.gap)
        done = local_cli(project, "speak", "-", "--output", str(wav), *(["--voice", voice] if voice else []),
                         *engine, input=ssml, stdout=subprocess.PIPE)
        if done.returncode or not wav.is_file():
            raise Fatal(f"The local engine failed (exit {done.returncode})")
        fmt, pcm = read_wav(wav)
        duration = check_audible(fmt, pcm)
        deliver(wav, output)
    finally:
        shutil.rmtree(workspace, ignore_errors=True)
        if not was_running and not args.keep_local_server:
            local_cli(project, "server", "stop", *engine, capture_output=True)
    return {"backend": "local", "audio_seconds": duration, "voice": voice or "(local default)",
            "engine": status["engine"]}


def local_rate(args):
    """Seconds per character on this machine for the engine the fallback would use."""
    return LOCAL_SECONDS_PER_CHAR.get(args.engine or "", max(LOCAL_SECONDS_PER_CHAR.values()))


def command_speak(args):
    text = read_input(args)
    if SSML.search(text):
        raise Fatal("The API does not interpret SSML: tags go to the model as text and <break> is "
                    "ignored. Use plain text (--gap for pauses between paragraphs).")
    if not 20 <= args.max_chars <= MAX_INPUT:
        raise Fatal(f"--max-chars must be from 20 to {MAX_INPUT}")
    if not .25 <= args.speed <= 4:
        raise Fatal("--speed must be from 0.25 to 4.0")
    parts = plan(text, args.max_chars)
    if not parts:
        raise Fatal("Nothing to speak: the text has no letters")
    total_chars = sum(len(t) for t, _ in parts)
    estimate = total_chars * SECONDS_PER_CHAR
    if args.dry_run:
        print(json.dumps({"requests": len(parts), "chars": total_chars,
                          "estimated_seconds": round(estimate),
                          "estimated": fmt_time(estimate),
                          "estimated_if_local": fmt_time(total_chars * local_rate(args)),
                          "parts": [t for t, _ in parts]}, ensure_ascii=False, indent=2))
        return 0

    if not args.output:
        raise Fatal("--output is required")
    output = Path(args.output).expanduser().resolve()
    suffix = output.suffix.lower()
    if suffix != ".wav" and suffix not in ENCODERS:
        raise Fatal(f"Unsupported output type {suffix or '(none)'}: use .wav, " + ", ".join(ENCODERS))
    if suffix != ".wav" and not shutil.which("ffmpeg"):
        raise Fatal(f"FFmpeg is required for {suffix} output")
    if output.exists() and not args.force:
        raise Fatal(f"{output} already exists (use --force to replace it)")

    config = load_config()
    args.engine = args.engine or config.get("engine")
    voice = args.voice or config.get("voice")
    known = config.get("known_voices") or ([config["voice"]] if config.get("voice") else [])
    if voice and known and voice not in known and not args.unverified_voice:
        raise Fatal(f"Voice {voice!r} is not in known_voices {known}. The API answers an unknown name "
                    "with a different voice instead of an error. Add it to the config once it is "
                    "registered on the server, or pass --unverified-voice.")

    output.parent.mkdir(parents=True, exist_ok=True)
    log(f"{len(parts)} request(s), {total_chars} chars, about {fmt_time(estimate)}, voice {voice}")
    started = time.perf_counter()
    try:
        result = generate_remote(config, parts, voice, args, output)
    except Unavailable as error:
        if args.no_fallback:
            raise
        log(f"Remote API unavailable: {error}")
        log(f"Switching to the local engine, about {fmt_time(total_chars * local_rate(args))} "
            "plus model loading.")
        try:
            result = generate_local(config, text, voice, args, output)
        except Fatal as local_error:
            raise Fatal(f"Remote: {error} / Local: {local_error}")
        result["fallback_reason"] = str(error)
        shutil.rmtree(output.with_name(output.name + ".parts"), ignore_errors=True)

    result["audio_seconds"] = round(result["audio_seconds"], 2)
    print(json.dumps({"output": str(output), **result, "speed": args.speed,
                      "elapsed_seconds": round(time.perf_counter() - started, 1)},
                     ensure_ascii=False, indent=2))
    if args.play:
        player = shutil.which("afplay") or shutil.which("ffplay")
        if not player:
            raise Fatal("No audio player found (afplay or ffplay)")
        extra = ["-nodisp", "-autoexit", "-loglevel", "error"] if player.endswith("ffplay") else []
        subprocess.run([player, *extra, str(output)], check=False)
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    check = commands.add_parser("check", help="confirm the API answers and the key works")
    check.add_argument("--synth", action="store_true", help="also generate a short test sentence (about 10 s)")
    check.add_argument("--engine", choices=sorted(API_MODELS), help="engine to check (default: config or server)")
    check.set_defaults(run=command_check)
    speak = commands.add_parser("speak", help="turn text into an audio file")
    speak.add_argument("text", nargs="?", help="the text, or - to read stdin")
    speak.add_argument("--file", help="read the text from a UTF-8 file")
    speak.add_argument("-o", "--output", help="output path: .wav .mp3 .m4a .ogg .opus .flac")
    speak.add_argument("--voice", help="registered voice name (default: voice in the config)")
    speak.add_argument("--engine", choices=sorted(API_MODELS),
                       help="local-tts engine, remote and local (default: config, else each side's default)")
    speak.add_argument("--unverified-voice", action="store_true", help="allow a name not in known_voices")
    speak.add_argument("--speed", type=float, default=1.0, help="0.25 to 4.0 (default 1.0)")
    speak.add_argument("--gap", type=float, default=0.0, help="seconds of silence between paragraphs")
    speak.add_argument("--max-chars", type=int, default=300, help="characters per request (default 300)")
    speak.add_argument("--force", action="store_true", help="replace an existing output")
    speak.add_argument("--play", action="store_true", help="play the result when finished")
    speak.add_argument("--no-fallback", action="store_true", help="fail instead of using the local engine")
    speak.add_argument("--keep-local-server", action="store_true",
                       help="leave the local TTS server running after a fallback")
    speak.add_argument("--dry-run", action="store_true", help="show the split and time estimate only")
    speak.set_defaults(run=command_speak)
    args = parser.parse_args()
    try:
        return args.run(args)
    except (Fatal, Unavailable) as error:
        log(f"ERROR: {error}")
        return 1
    except KeyboardInterrupt:
        log("Interrupted; rerun the same command to continue from the finished parts.")
        return 130


if __name__ == "__main__":
    sys.exit(main())
