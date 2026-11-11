"""Run the engine servers as background processes: start, stop and status.

s2 runs s2.cpp; omnivoice and voxcpm2 run tools/engines/<name>/server.py in their own virtual
environment. Each keeps a PID file and a log in <home>/cache/ (s2-server.pid, omnivoice-server.pid, ...).
VOICEVOX is started by the user and only reported here."""

import json
import os
from pathlib import Path
import shutil
import signal
import socket
import subprocess
import sys
import time
from urllib.parse import urlsplit

from .audio import AudioError, Backend
from . import engines, runtime
from .voices import RUNTIME, engine

PID_FILE = RUNTIME / "s2-server.pid"
LOG_FILE = RUNTIME / "s2-server.log"


def endpoint(config):
    url = urlsplit(Backend(config).url)
    return url.hostname, url.port or 80


def instances(config):
    """One config per server. Only s2 supports [server] parallel (consecutive ports from `url`)."""
    config = engines.select(config)
    if config["engine"] != "s2":
        return [config]
    count = config.get("server", {}).get("parallel", 1)
    if not isinstance(count, int) or not 1 <= count <= 8:
        raise AudioError("server.parallel must be a whole number from 1 to 8")
    host, port = endpoint(config)
    host = f"[{host}]" if ":" in host else host
    return [{**config, "url": f"http://{host}:{port + i}"} for i in range(count)]


def files(index, port, name="s2"):
    """PID and log files; the first s2 server keeps the original names."""
    if name != "s2":
        return RUNTIME / f"{name}-server.pid", RUNTIME / f"{name}-server.log"
    if index == 0:
        return PID_FILE, LOG_FILE
    return PID_FILE.with_name(f"s2-server-{port}.pid"), LOG_FILE.with_name(f"s2-server-{port}.log")


def reachable(config, timeout=.5):
    try:
        with socket.create_connection(endpoint(config), timeout=timeout):
            return True
    except OSError:
        return False


def command_line(pid):
    """The command line of a process, or "" when it cannot be read."""
    if sys.platform == "win32":
        query = f"(Get-CimInstance Win32_Process -Filter 'ProcessId={int(pid)}').CommandLine"
        found = subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command", query],
                               capture_output=True, text=True, errors="replace")
        return found.stdout.strip()
    found = subprocess.run(["ps", "-p", str(int(pid)), "-o", "command="], capture_output=True,
                           text=True, errors="replace")
    return found.stdout.strip()


def marker(name):
    """Text only this engine's server process has on its command line."""
    return str(engines.project(name) / "server.py")


def recorded_pid(pid_file=None, name="s2"):
    """PID of the server this tool started, if that process is still that server."""
    pid_file = pid_file or PID_FILE
    try:
        pid = int(pid_file.read_text(encoding="ascii").strip())
    except (OSError, ValueError):
        return None
    # A stale PID may belong to another program by now; verify it before stopping it.
    if name != "s2":
        line = command_line(pid).replace("\\", "/")
        return pid if marker(name).replace("\\", "/") in line else None
    if sys.platform == "win32":
        found = subprocess.run(["tasklist", "/FI", f"PID eq {pid}", "/FO", "CSV", "/NH"],
                               capture_output=True, text=True, errors="replace").stdout
        return pid if '"s2.exe"' in found.lower() else None
    found = subprocess.run(["ps", "-p", str(pid), "-o", "comm="], capture_output=True,
                           text=True, errors="replace").stdout.strip()
    return pid if Path(found).name == "s2" else None


def log_tail(lines=8, log_file=None):
    try:
        return "\n".join((log_file or LOG_FILE).read_text(encoding="utf-8", errors="replace").splitlines()[-lines:])
    except OSError:
        return ""


def start(config, wait=None):
    """Start the configured engine's server in the background and wait until it listens.

    s2 takes [server] gpu_layers (36), codec_gpu (true), threads (0 = automatic) and parallel (1);
    a PyTorch engine takes [engines.<name>] device (auto), dtype and wait (seconds, default 600).
    Returns True if a server was started."""
    config = engines.select(config)
    name = config["engine"]
    kind = engines.ENGINES[name]["kind"]
    if kind == "voicevox":
        raise AudioError("Start the VOICEVOX ENGINE yourself; local-tts only connects to it")
    if kind == "python":
        settings = engines.settings(config, name)
        return start_python(config, name, *files(0, 0, name), float(wait or settings.get("wait", 600)))
    started = False
    for index, one in enumerate(instances(config)):
        started = start_one(one, *files(index, endpoint(one)[1]), wait or 120.) or started
    return started


def launch(command, env, pid_file, log_file):
    log_file.parent.mkdir(parents=True, exist_ok=True)
    with log_file.open("ab") as log:
        detach = ({"creationflags": subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP}
                  if sys.platform == "win32" else {"start_new_session": True})
        process = subprocess.Popen(
            command, stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT, env=env,
            **detach)
    pid_file.write_text(str(process.pid), encoding="ascii")
    return process


def wait_until_listening(config, process, pid_file, log_file, wait):
    host, port = endpoint(config)
    deadline = time.monotonic() + wait
    while not reachable(config):
        if process.poll() is not None:
            pid_file.unlink(missing_ok=True)
            raise AudioError(f"The TTS server exited during startup (see {log_file}):\n"
                             f"{log_tail(log_file=log_file)}")
        if time.monotonic() > deadline:
            raise AudioError(f"The TTS server did not open {host}:{port} within {wait:.0f} s "
                             f"(see {log_file})")
        time.sleep(.5)


def start_one(config, pid_file, log_file, wait):
    if reachable(config):
        return False
    settings = config.get("server", {})
    host, port = endpoint(config)
    executable, model, tokenizer, env = engine()
    threads = settings.get("threads", 0)
    if not isinstance(threads, int) or threads < 0:
        raise AudioError("server.threads must be 0 (automatic) or a positive whole number")
    threads = threads or runtime.auto_threads()
    try:
        accelerator = runtime.accelerator_args(settings)
        codec = runtime.codec_arg(settings)
    except ValueError as exc:
        raise AudioError(str(exc)) from exc
    command = [str(executable), "--model", str(model), "--tokenizer", str(tokenizer),
               *accelerator, *(["--threads", str(threads)] if threads else []),
               "--server", "--host", host, "--port", str(port), codec]
    process = launch(command, env, pid_file, log_file)
    wait_until_listening(config, process, pid_file, log_file, wait)
    return True


def free_vram_gb():
    """Free memory of the first NVIDIA GPU in GB, or None without nvidia-smi."""
    command = shutil.which("nvidia-smi")
    if not command:
        return None
    try:
        done = subprocess.run([command, "--query-gpu=memory.free", "--format=csv,noheader,nounits"],
                              capture_output=True, text=True, timeout=10)
        return int(done.stdout.split()[0]) / 1024 if not done.returncode else None
    except (OSError, ValueError, IndexError, subprocess.TimeoutExpired):
        return None


def start_python(config, name, pid_file, log_file, wait):
    if reachable(config):
        return False
    spec = engines.ENGINES[name]
    if not engines.installed(name) or not engines.model_ready(name):
        raise AudioError(f"{spec['label']} is not installed; run: local-tts engine install {name}")
    settings = engines.settings(config, name)
    if settings.get("device", "auto") in ("auto", "cuda"):
        free = free_vram_gb()
        if free is not None and free < spec["memory_gb"]:
            running = [s["engine"] for s in status(config) if s["listening"]]
            raise AudioError(f"{spec['label']} needs about {spec['memory_gb']:.0f} GB of GPU memory but "
                             f"{free:.1f} GB is free (running: {', '.join(running) or 'none'}); "
                             "stop other servers with: local-tts server stop")
    host, port = endpoint(config)
    process_settings = {k: v for k, v in settings.items() if k in {"device", "dtype", "optimize"}}
    command = [str(engines.python(name)), marker(name), "--host", host, "--port", str(port),
               "--settings", json.dumps(process_settings)]
    process = launch(command, engines.process_env(name), pid_file, log_file)
    wait_until_listening(config, process, pid_file, log_file, wait)
    return True


def pid_files():
    """(engine, pid file) for every server this tool may have started."""
    found = [("s2", PID_FILE), *(("s2", p) for p in sorted(PID_FILE.parent.glob("s2-server-*.pid")))]
    found += [(name, files(0, 0, name)[0]) for name, spec in engines.ENGINES.items()
              if spec["kind"] == "python"]
    return found


def stop(name=None):
    """Stop every server this tool started (or only one engine's). Returns False if none was running."""
    stopped = False
    for engine_name, pid_file in pid_files():
        if name and engine_name != name:
            continue
        pid = recorded_pid(pid_file, engine_name)
        pid_file.unlink(missing_ok=True)
        if pid is None:
            continue
        stopped = True
        if sys.platform == "win32":
            subprocess.run(["taskkill", "/PID", str(pid), "/T", "/F"], capture_output=True)
        else:
            try:
                os.kill(pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
        wait_for_exit(pid)
    return stopped


def alive(pid):
    if sys.platform == "win32":
        found = subprocess.run(["tasklist", "/FI", f"PID eq {pid}", "/FO", "CSV", "/NH"],
                               capture_output=True, text=True, errors="replace").stdout
        return f'"{pid}"' in found
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def wait_for_exit(pid, timeout=15.):
    """Wait until a stopped server is gone, so a following start does not find its port still open."""
    deadline = time.monotonic() + timeout
    while alive(pid) and time.monotonic() < deadline:
        time.sleep(.2)


def status(config, name=None):
    """One entry per server: the configured engine's (or `name`'s), or every engine with name="all"."""
    names = list(engines.ENGINES) if name == "all" else [engines.resolve(config, name)]
    result = []
    for engine_name in names:
        bound = engines.select(config, engine_name)
        for index, one in enumerate(instances(bound)):
            pid_file, log_file = files(index, endpoint(one)[1], engine_name)
            result.append({"engine": engine_name, "url": Backend(one).url, "listening": reachable(one),
                           "pid": None if engine_name == "voicevox" else recorded_pid(pid_file, engine_name),
                           "log": None if engine_name == "voicevox" else str(log_file)})
    return result


def ensure(config):
    """Start the engine's server for say/speak if it is down, unless auto_start = false."""
    config = engines.select(config)
    name = config["engine"]
    kind = engines.ENGINES[name]["kind"]
    auto = (engines.settings(config, name).get("auto_start", True) if kind == "python"
            else config.get("server", {}).get("auto_start", True))
    if kind != "voicevox" and auto and not all(reachable(one) for one in instances(config)):
        return start(config)
    return False
