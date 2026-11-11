"""Command line: local-tts doctor | plan | speak | say | api | server | voice | engine | home."""

import functools
import json
import platform
from pathlib import Path
import shutil
import subprocess
import sys
import tomllib
from typing import Annotated, Optional

import typer

from . import api as speech_api, engines, home as home_dir, runtime, server, voices
from .audio import AudioError, Backend, render
from .say import merge_speech, say as say_loop
from .ssml import MAX_BYTES, SSMLError, Speech, Style, compile_ssml, event_dict

app = typer.Typer(help="Local speech: OmniVoice, VoxCPM2 or Fish S2 Pro, from text or SSML 1.1.",
                  no_args_is_help=True, pretty_exceptions_enable=False)
voice_app = typer.Typer(help="Clone, list, rebuild and remove voices (voices/).", no_args_is_help=True)
app.add_typer(voice_app, name="voice")
server_app = typer.Typer(help="Run the engine servers in the background.", no_args_is_help=True)
app.add_typer(server_app, name="server")
engine_app = typer.Typer(help="Install and list the speech engines.", no_args_is_help=True)
app.add_typer(engine_app, name="engine")
home_app = typer.Typer(help="The data folder (<home>) and the move from the old presenter-tts folder.",
                       no_args_is_help=True)
app.add_typer(home_app, name="home")

VoiceOption = Annotated[Optional[str], typer.Option(
    help="Voice name from `voice list`, a .s2voice path, or default.")]
EngineOption = Annotated[Optional[str], typer.Option(
    help=f"Engine: {', '.join(engines.ENGINES)} (default: `engine` in config.toml, else {engines.DEFAULT}).")]


def handled(command):
    """Report expected failures as one ERROR line and exit 2, instead of a traceback."""
    @functools.wraps(command)
    def wrapper(*args, **kwargs):
        try:
            return command(*args, **kwargs)
        except (SSMLError, AudioError, engines.EngineError, OSError, UnicodeError,
                tomllib.TOMLDecodeError) as exc:
            typer.echo(f"ERROR: {exc}", err=True)
            raise typer.Exit(2)
        except KeyboardInterrupt:
            typer.echo("Cancelled", err=True)
            raise typer.Exit(130)
    return wrapper


def read_config(ctx):
    path = ctx.obj or voices.CONFIG
    if path.exists():
        return tomllib.loads(path.read_text(encoding="utf-8-sig"))  # Tolerate an editor's BOM.
    if ctx.obj is None:
        return {}  # No config.toml yet: defaults.
    raise AudioError(f"Config does not exist: {path}")


def load_config(ctx, voice=None, engine=None):
    """config.toml bound to one engine (--engine, `engine`, the old `backend`, or the default)."""
    config = engines.select(read_config(ctx), engine)
    # `voice` may be a name from voices/ (voice = "myvoice") or a .s2voice path.
    if voice or config.get("voice"):
        voices.set_voice(config, voice or config["voice"])
    return config


def ensure_server(config):
    if not all(server.reachable(one) for one in server.instances(config)):
        label = engines.ENGINES[config["engine"]]["label"]
        if engines.ENGINES[config["engine"]]["kind"] == "voicevox":
            raise AudioError(f"{label} is not running at {Backend(config).url}; start it first")
        typer.echo(f"Starting the {label} server in the background (stop it with: server stop)...", err=True)
    server.ensure(config)


def read_document(source):
    if source == "-":
        return sys.stdin.buffer.read(MAX_BYTES + 1).decode("utf-8-sig")
    with Path(source).open("rb") as stream:
        return stream.read(MAX_BYTES + 1).decode("utf-8-sig")


@app.callback()
def main(ctx: typer.Context,
         config: Annotated[Optional[Path], typer.Option(
             help="TOML settings file (default: <home>/config.toml).")] = None):
    ctx.obj = config
    if voices.HOME_WARNING:
        typer.echo("WARNING: " + voices.HOME_WARNING, err=True)
    # Before the rename the data lived in presenter-tts; do not silently start an empty home.
    if (ctx.invoked_subcommand not in {"home", "plan", "doctor"} and not home_dir.explicit()
            and home_dir.needs_migration(voices.HOME, home_dir.legacy())):
        typer.echo(f"ERROR: Voices and settings are still in the old folder {home_dir.legacy()}. "
                   "Move them with: local-tts home migrate --dry-run, then local-tts home migrate", err=True)
        raise typer.Exit(2)
    voices.move_legacy_s2_profiles()  # Before 2026-11-11 S2 profiles sat in voices/.


@app.command()
@handled
def doctor(ctx: typer.Context):
    """Check GPU, toolchain, engines, voices, network and the local TTS ports (JSON).

    references/setup.md reads `engine.ready`, `engines` and `prerequisites` to decide what still needs doing."""
    import socket
    import re
    config = load_config(ctx)
    try:
        profile = runtime.current()
    except ValueError:
        profile = {"platform": sys.platform, "accelerator": None}
    result = {"python": sys.version.split()[0], "ffmpeg": shutil.which("ffmpeg"),
              "ffplay": shutil.which("ffplay"), "selected_engine": config["engine"]}
    if sys.platform == "darwin":
        result["swiftc"] = shutil.which("swiftc")  # --play/say use a Core Audio helper built with it
    try:
        engine_ok, engine_note = bool(voices.engine()), None
    except AudioError as exc:
        engine_ok, engine_note = False, str(exc)
    cuda_file = voices.RUNTIME / "s2-cuda-root.txt"
    cuda_root = cuda_file.read_text(encoding="utf-8-sig").strip() if cuda_file.is_file() else None
    old = home_dir.legacy()
    result["home"] = {"path": str(voices.HOME), "config": voices.CONFIG.is_file(),
                      "voices": [p["name"] for p in voices.profiles()],
                      "legacy": str(old) if old.is_dir() else None,
                      "needs_migration": home_dir.needs_migration(voices.HOME, old)}
    # `engine` is S2 (s2.cpp), kept under this key for the setup steps that read it.
    result["engine"] = {"ready": engine_ok, "missing": engine_note, "cuda_root": cuda_root,
                        "accelerator": profile["accelerator"],
                        "cache": str(voices.RUNTIME)}
    result["engines"] = engines.status(config)
    for info in result["engines"]:
        if info["engine"] == "s2":
            info["installed"] = engine_ok
        bound = engines.select(config, info["engine"])
        info["listening"] = server.reachable(bound)
    nvcc = str(Path(cuda_root) / "bin" / "nvcc.exe") if cuda_root else shutil.which("nvcc")
    cuda_version = None
    if nvcc and Path(nvcc).is_file():
        found = re.search(r"release (\d+\.\d+)", subprocess.run(
            [nvcc, "--version"], capture_output=True, text=True, timeout=30).stdout)
        cuda_version = found and found[1]
    vswhere = Path(r"C:\Program Files (x86)\Microsoft Visual Studio\Installer\vswhere.exe")
    visual_studio = None
    if vswhere.is_file():
        visual_studio = subprocess.run(
            [str(vswhere), "-latest", "-products", "*", "-requires",
             "Microsoft.VisualStudio.Component.VC.Tools.x86.x64", "-property", "installationPath"],
            capture_output=True, text=True, timeout=30).stdout.strip() or None
    xcrun = shutil.which("xcrun")
    metal = subprocess.run([xcrun, "--find", "metal"], capture_output=True, text=True).stdout.strip() \
        if xcrun and sys.platform == "darwin" else None
    cmake = shutil.which("cmake") or (visual_studio and "bundled with Visual Studio") \
        or (shutil.which("uv") and "uvx --from cmake cmake")
    result["prerequisites"] = {"platform": profile["platform"],
                               "architecture": platform.machine(),
                               "windows": sys.platform == "win32", "macos": sys.platform == "darwin",
                               "uv": shutil.which("uv"),
                               "git": shutil.which("git"), "nvcc": nvcc, "cuda_version": cuda_version,
                               "visual_studio_cpp": visual_studio,
                               "metal": metal,
                               "cmake": cmake}
    command = shutil.which("nvidia-smi")
    if command:
        proc = subprocess.run([command, "--query-gpu=name,memory.total,memory.free",
                               "--format=csv,noheader,nounits"], capture_output=True,
                              text=True, timeout=10)
        result["gpu"] = proc.stdout.strip() if not proc.returncode else proc.stderr.strip()
    for host in ("huggingface.co", "github.com"):
        try:
            socket.getaddrinfo(host, 443)
            result[host] = "DNS available"
        except OSError as exc:
            result[host] = f"DNS unavailable: {exc}"
    result["tts_port"] = ("reachable (TCP only; synthesis not verified)" if server.reachable(config)
                          else f"unavailable: {Backend(config).url}")
    typer.echo(json.dumps(result, ensure_ascii=False, indent=2))


@app.command()
@handled
def plan(source: Annotated[str, typer.Argument(metavar="INPUT", help="SSML file, or - for stdin.")]):
    """Show the speech and timing events an SSML document compiles to."""
    events, warnings = compile_ssml(read_document(source))
    typer.echo(json.dumps({"profile": "local-tts-ssml-1.1-subset", "warnings": warnings,
                           "events": [event_dict(e) for e in events]}, ensure_ascii=False, indent=2))


@app.command()
@handled
def speak(ctx: typer.Context,
          source: Annotated[str, typer.Argument(metavar="INPUT", help="SSML file, or - for stdin.")],
          output: Annotated[Path, typer.Option(help="WAV to write.")] = Path("outputs/presentation.wav"),
          play: Annotated[bool, typer.Option(help="Play PCM as it arrives.")] = False,
          force: Annotated[bool, typer.Option(help="Overwrite an existing output.")] = False,
          voice: VoiceOption = None,
          engine: EngineOption = None):
    """Render an SSML presentation to WAV."""
    config = load_config(ctx, voice, engine)
    events, warnings = compile_ssml(read_document(source))
    for warning in warnings:
        typer.echo("WARNING: " + warning, err=True)
    limit = engines.request_chars(config)
    if limit:
        events = merge_speech(events, limit)  # Fewer, longer requests for engines that prefer them.
    ensure_server(config)
    report = render(events, Backend(config), output, play=play, force=force)
    typer.echo(json.dumps({"output": str(output), "timing": str(output.with_suffix(".json")),
                           "engine": config["engine"],
                           "first_speech_pcm_seconds": report["first_speech_pcm_seconds"],
                           "rtf_speech": report["rtf_speech"]}, ensure_ascii=False, indent=2))


@app.command()
@handled
def say(ctx: typer.Context,
        text: Annotated[Optional[list[str]], typer.Argument(
            help="Text to speak once; omit to type lines interactively (/voice NAME switches).")] = None,
        output: Annotated[Path, typer.Option(help="WAV of the last line.")] = Path("outputs/say.wav"),
        voice: VoiceOption = None,
        engine: EngineOption = None):
    """Speak typed text while it is generated."""
    config = load_config(ctx, voice, engine)
    ensure_server(config)
    say_loop(Backend(config), " ".join(text or []), output)


@app.command()
@handled
def api(ctx: typer.Context,
        voice: Annotated[Optional[str], typer.Option(
            help="Voice when a request names none or an OpenAI voice (alloy, nova, ...).")] = None,
        engine: Annotated[Optional[str], typer.Option(
            help="Engine when a request's model names none (tts-1, ...); see `engine list`.")] = None,
        host: Annotated[str, typer.Option(
            help="Address to listen on; 0.0.0.0 accepts other devices (API key required).")]
        = "0.0.0.0",
        port: Annotated[int, typer.Option(help="Port to listen on.")] = 8000,
        api_key: Annotated[Optional[str], typer.Option(
            envvar=["LOCAL_TTS_API_KEY", "PRESENTER_TTS_API_KEY"],  # The second is the old name.
            help="Bearer key clients must send; default: generated once into <home>/api-key.txt.")]
        = None):
    """Serve an OpenAI-compatible speech API: POST /v1/audio/speech.

    Point an OpenAI client at http://<this PC>:8000/v1 with the printed API key. A request's
    "voice" picks a registered voice by name and "model" an engine (omnivoice, voxcpm2, s2-pro).
    With --host 127.0.0.1 no key is needed."""
    config = load_config(ctx, voice, engine)
    ensure_server(config)
    speech_api.serve(config, host, port, api_key)


@server_app.command("start")
@handled
def server_start(ctx: typer.Context, engine: EngineOption = None):
    """Start an engine's server in the background and wait until it accepts requests.

    S2 reads [server] in the config; a PyTorch engine reads [engines.<name>] (device, dtype)."""
    config = load_config(ctx, engine=engine)
    typer.echo(f"Starting the {engines.ENGINES[config['engine']]['label']} server (loading the model)...")
    if server.start(config):
        for info in server.status(config):
            typer.echo(f"Running: {info['url']} (log: {info['log']})")
    else:
        typer.echo("Already running")


@server_app.command("status")
@handled
def server_status(ctx: typer.Context, engine: Annotated[Optional[str], typer.Option(
        help="One engine, or all (default: every engine).")] = "all"):
    """Show which engine servers are listening and which process this tool started."""
    for info in server.status(load_config(ctx), engine):
        state = "listening" if info["listening"] else "not running"
        owner = f", pid {info['pid']} (started here)" if info["pid"] else (
            ", started elsewhere" if info["listening"] else "")
        typer.echo(f"{info['engine']}: {info['url']}: {state}{owner}")
        if info["log"]:
            typer.echo(f"  log: {info['log']}")


@server_app.command("stop")
@handled
def server_stop(engine: Annotated[Optional[str], typer.Option(
        help="Stop only this engine's server (default: all of them).")] = None):
    """Stop the servers started by this tool (frees their GPU memory)."""
    if engine:
        engines.check(engine)
    typer.echo("Stopped" if server.stop(engine) else "No server started by this tool is running")


@engine_app.command("list")
@handled
def engine_list(ctx: typer.Context):
    """Show each engine: installed, model downloaded, address and license; * marks the default."""
    config = load_config(ctx)
    try:
        s2_ok = bool(voices.engine())
    except AudioError:
        s2_ok = False
    for info in engines.status(config):
        mark = "*" if info["engine"] == config["engine"] else " "
        if info["engine"] == "s2":
            state = "ready" if s2_ok else "not set up (references/setup.md)"
        elif "installed" in info:
            state = ("ready" if info["installed"] and info["model"] else
                     f"not installed (local-tts engine install {info['engine']})")
        else:
            state = "external (start it yourself)"
        typer.echo(f"{mark} {info['engine']:<10} {state:<40} {info['url']}  {info['license']}")


@engine_app.command("install")
@handled
def engine_install(name: Annotated[str, typer.Argument(help="omnivoice or voxcpm2.")]):
    """Install a PyTorch engine into <home>/cache/engines/<name> and download its model.

    Uses the engine's locked dependencies (CUDA PyTorch on Windows, MPS-capable PyTorch on macOS)."""
    engines.install(engines.check(name), echo=typer.echo)
    typer.echo(f"Installed {name}. Try: local-tts say --engine {name} こんにちは。")


def speak_sample(config, text, output):
    """Speak one check sentence into `output` with the configured engine."""
    ensure_server(config)
    render([Speech(text, Style())], Backend(config), Path(output), force=True)


def play_file(path):
    if sys.platform == "darwin" and shutil.which("afplay"):
        subprocess.run([shutil.which("afplay"), str(path)])
    elif shutil.which("ffplay"):
        subprocess.run([shutil.which("ffplay"), "-loglevel", "error", "-nodisp", "-autoexit", str(path)])


@voice_app.command("add")
@handled
def voice_add(
        ctx: typer.Context,
        name: Annotated[str, typer.Argument(help="New voice name (letters, digits, - and _).")],
        audio: Annotated[Path, typer.Argument(exists=True, dir_okay=False,
                                              help="Reference recording (wav, mp3, m4a, ...).")],
        text: Annotated[Optional[str], typer.Option("--text", "-t",
                                                    help="Exactly what the recording says.")] = None,
        text_file: Annotated[Optional[Path], typer.Option(exists=True, dir_okay=False,
                                                          help="UTF-8 file holding the transcript.")] = None,
        sample: Annotated[str, typer.Option(help="Sentence spoken in the new voice as a check.")]
        = "これは、新しく登録した声のテストです。",
        boost: Annotated[bool, typer.Option(help="Raise the reference to a -3 dB peak first.")] = True,
        gpu: Annotated[bool, typer.Option(help="S2: encode on the GPU (stop the TTS server first).")] = False,
        preview: Annotated[bool, typer.Option(help="Play the check sentence when done.")] = True,
        force: Annotated[bool, typer.Option(help="Replace an existing voice of this name.")] = False,
        engine: EngineOption = None):
    """Save a voice from a recording and its transcript, and speak a check sentence with it.

    With S2 installed an S2 profile is encoded too; OmniVoice and VoxCPM2 build theirs on first use.
    Only clone voices you have permission to use."""
    if (text is None) == (text_file is None):
        raise AudioError("Give the transcript with exactly one of --text or --text-file")
    transcript = text if text is not None else text_file.read_text(encoding="utf-8-sig").strip()
    config = load_config(ctx, engine=engine)
    sample_output = Path("outputs") / f"voice-{name}.wav"
    with_s2 = True if config["engine"] == "s2" else None
    if with_s2 or voices.s2_ready():
        typer.echo(f"Encoding '{name}' for S2 on the {'GPU' if gpu else 'CPU'}; this takes about a minute...")
    meta = voices.clone(name, audio, transcript, sample_text=sample, sample_output=sample_output,
                        force=force, gpu=gpu, boost=boost, s2=with_s2)
    for warning in meta["warnings"]:
        typer.echo("WARNING: " + warning, err=True)
    typer.echo(f"Saved voice '{name}': {meta['seconds']} s reference, gain {meta['gain_db']:+} dB"
               + ("" if meta["s2"] else " (no S2 profile: S2 is not installed)"))
    if config["engine"] != "s2" or not meta["s2"]:
        # The S2 sample came from s2.cpp; other engines speak it through their server.
        typer.echo(f"Speaking the check sentence with {engines.ENGINES[config['engine']]['label']}...")
        speak_sample({**config, "voice": name}, sample, sample_output)
    typer.echo(f"Check sentence: {sample_output}")
    typer.echo(f"Use it with: local-tts say --voice {name}")
    if preview:
        play_file(sample_output)


@voice_app.command("build")
@handled
def voice_build(
        ctx: typer.Context,
        name: Annotated[str, typer.Argument(help="Registered voice to rebuild.")],
        engine: EngineOption = None,
        sample: Annotated[str, typer.Option(help="Sentence spoken in the voice as a check.")]
        = "これは、作り直した声のテストです。",
        gpu: Annotated[bool, typer.Option(help="S2: encode on the GPU (stop the TTS server first).")] = False):
    """(Re)create one engine's profile of a voice from its saved recording and transcript."""
    config = load_config(ctx, engine=engine)
    voices.reference(name)  # Fails early for unknown voices or ones without a recording.
    sample_output = Path("outputs") / f"voice-{name}-{config['engine']}.wav"
    if config["engine"] == "s2":
        voices.build_s2(name, sample, sample_output, gpu=gpu)
    elif engines.ENGINES[config["engine"]]["kind"] == "python":
        for path in (voices.PROFILE_CACHE / config["engine"]).glob(f"{name}.*"):
            path.unlink()
        speak_sample({**config, "voice": name}, sample, sample_output)  # The server rebuilds it on use.
    else:
        raise AudioError(f"{config['engine']} does not use cloned voices")
    typer.echo(f"Rebuilt '{name}' for {config['engine']}; check sentence: {sample_output}")


@voice_app.command("list")
@handled
def voice_list(ctx: typer.Context):
    """Show registered voices; * marks the one config.toml uses. Flags: s2 = has an S2 profile."""
    current = Path(load_config(ctx).get("voice", "default")).stem
    typer.echo(f"{'*' if current == 'default' else ' '} default  (model's own voice)")
    for profile in voices.profiles():
        mark = "*" if profile["name"] == current else " "
        built = [e for e in engines.ENGINES if e != "s2" and
                 any((voices.PROFILE_CACHE / e).glob(f"{profile['name']}.*"))]
        flags = ",".join((["s2"] if profile["s2"] else []) + built) or "-"
        details = f"{profile['seconds']} s  {profile['transcript']}" if "transcript" in profile else ""
        typer.echo(f"{mark} {profile['name']}  [{flags}]  {details}".rstrip())


@voice_app.command("remove")
@handled
def voice_remove(name: Annotated[str, typer.Argument(help="Voice to delete.")],
                 yes: Annotated[bool, typer.Option("--yes", "-y", help="Do not ask.")] = False):
    """Delete a voice: its recording, S2 profile, engine profiles and cached fillers."""
    if not yes:
        typer.confirm(f"Delete voice '{name}'?", abort=True)
    voices.remove(name)
    typer.echo(f"Removed voice '{name}'")


@home_app.command("show")
@handled
def home_show():
    """Print the data folder, the old presenter-tts folder and whether a move is pending (JSON)."""
    old = home_dir.legacy()
    typer.echo(json.dumps({"home": str(voices.HOME), "exists": voices.HOME.is_dir(),
                           "legacy": str(old), "legacy_exists": old.is_dir(),
                           "needs_migration": home_dir.needs_migration(voices.HOME, old),
                           "hf_hub_cache": str(home_dir.hf_hub_cache())}, ensure_ascii=False, indent=2))


@home_app.command("migrate")
@handled
def home_migrate(dry_run: Annotated[bool, typer.Option(help="Only list what would be copied or moved.")] = False):
    """Copy voices, config.toml and api-key.txt from the old presenter-tts folder; move the caches.

    The originals of what cannot be rebuilt stay in the old folder. Stop TTS servers first."""
    old = home_dir.legacy()
    if not old.is_dir():
        raise AudioError(f"No old folder to move from: {old}")
    if not dry_run and server.reachable(old_server(old)):
        raise AudioError("A TTS server is running; stop it first (local-tts server stop, or the old presenter-tts)")
    hub = home_dir.hf_hub_cache()
    actions = (home_dir.plan if dry_run else home_dir.migrate)(voices.HOME, old, hub)
    total = sum(a["bytes"] for a in actions if a["action"] != "skip")
    typer.echo(json.dumps({"dry_run": dry_run, "from": str(old), "to": str(voices.HOME),
                           "bytes": total, "actions": actions}, ensure_ascii=False, indent=2))
    if not dry_run and sys.platform == "darwin" and not (voices.RUNTIME / "s2-build" / "s2").is_file() \
            and (old / "cache" / "s2-build").is_dir():
        typer.echo("NEXT: rebuild s2.cpp in the new folder: bash <local-tts>/tools/scripts/setup-s2.sh", err=True)


def old_server(old):
    """The old folder's server address, to refuse moving files under a running server."""
    path = old / "config.toml"
    config = tomllib.loads(path.read_text(encoding="utf-8-sig")) if path.is_file() else {}
    return {"engine": "s2", "url": config.get("url", "http://127.0.0.1:3030")}
