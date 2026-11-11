"""HTTP server shared by the PyTorch engines, speaking the same /generate contract as s2.cpp.

POST /generate   multipart: text, params (JSON), voice (a name in <home>/voices, optional)
                 -> 200, PCM16 mono, X-Audio-Encoding: pcm_s16le, X-Audio-Sample-Rate, X-Audio-Channels,
                    Transfer-Encoding: chunked (streaming engines send audio while it is generated)
POST /profile    multipart: voice -> rebuild that voice's profile now (JSON)
GET  /health     -> {"engine", "device", "sample_rate", "ready"} (JSON)

An engine supplies an Adapter (see the methods used below). Voice profiles are built from
<home>/voices/<name>.wav and its transcript on first use and cached in
<home>/cache/voices/<engine>/<name>.pt with a fingerprint of the recording and transcript, so a
re-recorded voice is rebuilt instead of reusing a stale profile.
Only one request is generated at a time; others wait for the lock."""

import argparse
from email.parser import BytesParser
from email.policy import HTTP
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import re
import sys
import threading
import time
import traceback

NAME = re.compile(r"[A-Za-z0-9_-]+")


class RequestError(ValueError):
    pass


def home():
    value = os.environ.get("LOCAL_TTS_HOME")
    if not value:
        raise SystemExit("LOCAL_TTS_HOME is not set; start engines through local-tts")
    return Path(value)


def parse_multipart(content_type, body):
    """{field: text} of a multipart/form-data body (the controller sends text fields only)."""
    if "multipart/form-data" not in (content_type or ""):
        raise RequestError("Expected multipart/form-data")
    message = BytesParser(policy=HTTP).parsebytes(
        b"Content-Type: " + content_type.encode("latin-1") + b"\r\nMIME-Version: 1.0\r\n\r\n" + body)
    fields = {}
    for part in message.iter_parts():
        name = part.get_param("name", header="content-disposition")
        if name:
            fields[name] = part.get_payload(decode=True).decode("utf-8")
    return fields


def pick_device(setting):
    """auto: CUDA, else Apple's MPS, else the CPU."""
    import torch
    setting = (setting or "auto").lower()
    if setting != "auto":
        return setting
    if torch.cuda.is_available():
        return "cuda"
    if getattr(torch.backends, "mps", None) and torch.backends.mps.is_available():
        return "mps"
    return "cpu"


def pcm16(samples):
    """float waveform in [-1, 1] -> PCM16 little-endian bytes (numpy when the engine has it)."""
    try:
        import numpy as np
    except ImportError:  # The controller's tests run the server without numpy.
        from array import array
        values = array("h", (round(max(-1.0, min(1.0, float(x))) * 32767) for x in samples))
        if sys.byteorder != "little":
            values.byteswap()
        return values.tobytes()
    clipped = np.clip(np.asarray(samples, dtype=np.float32).reshape(-1), -1.0, 1.0)
    return (clipped * 32767.0).astype("<i2").tobytes()


class Profiles:
    """Voice name -> engine profile, built from the saved recording on first use."""

    def __init__(self, adapter):
        self.adapter = adapter
        self.folder = home() / "cache" / "voices" / adapter.name
        self.loaded = {}

    def source(self, name):
        if not NAME.fullmatch(name):
            raise RequestError(f"Invalid voice name: {name}")
        voices = home() / "voices"
        wav, meta = voices / f"{name}.wav", voices / f"{name}.json"
        if not wav.is_file() or not meta.is_file():
            raise RequestError(f"Voice '{name}' has no recording in {voices}; register it with local-tts voice add")
        transcript = json.loads(meta.read_text(encoding="utf-8")).get("transcript", "").strip()
        if not transcript:
            raise RequestError(f"Voice '{name}' has no transcript in {meta}")
        digest = hashlib.sha256(wav.read_bytes() + b"\0" + transcript.encode("utf-8")).hexdigest()
        return wav, transcript, digest

    def get(self, name, rebuild=False):
        wav, transcript, digest = self.source(name)
        cached = self.loaded.get(name)
        if cached and cached[0] == digest and not rebuild:
            return cached[1]
        path, note = self.folder / f"{name}.pt", self.folder / f"{name}.json"
        fresh = (not rebuild and path.is_file() and note.is_file()
                 and json.loads(note.read_text(encoding="utf-8")).get("sha256") == digest)
        started = time.perf_counter()
        if fresh:
            profile = self.adapter.load_profile(path)
            print(f"voice {name}: loaded profile {path}", flush=True)
        else:
            profile = self.adapter.build_profile(wav, transcript)
            self.folder.mkdir(parents=True, exist_ok=True)
            temporary = path.with_suffix(".tmp")
            self.adapter.save_profile(profile, temporary)
            os.replace(temporary, path)
            note.write_text(json.dumps({"sha256": digest, "source": str(wav), "engine": self.adapter.name},
                                       ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            # Use exactly what was saved, so the first request already runs on the cached profile.
            profile = self.adapter.load_profile(path)
            print(f"voice {name}: built profile {path} in {time.perf_counter() - started:.1f} s", flush=True)
        self.loaded[name] = (digest, profile)
        return profile


def handler(adapter, profiles, lock):
    class Handler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"
        server_version = f"local-tts-{adapter.name}/1"

        def log_message(self, fmt, *args):
            pass

        def send_json(self, status, payload):
            body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def read_fields(self):
            length = int(self.headers.get("Content-Length", 0))
            if not 0 < length <= 1_000_000:
                raise RequestError("The request body is missing or too large")
            return parse_multipart(self.headers.get("Content-Type"), self.rfile.read(length))

        def do_GET(self):
            if self.path.rstrip("/") == "/health":
                self.send_json(200, {"engine": adapter.name, "device": adapter.device,
                                     "sample_rate": adapter.sample_rate, "ready": True})
            else:
                self.send_json(404, {"error": f"Unknown path: {self.path}"})

        def do_POST(self):
            path = self.path.rstrip("/")
            try:
                fields = self.read_fields()
                if path == "/profile":
                    with lock:
                        profiles.get(fields.get("voice", ""), rebuild=True)
                    self.send_json(200, {"voice": fields.get("voice"), "rebuilt": True})
                    return
                if path != "/generate":
                    self.send_json(404, {"error": f"Unknown path: {self.path}"})
                    return
                text = fields.get("text", "").strip()
                if not text:
                    raise RequestError("'text' must not be empty")
                params = json.loads(fields.get("params") or "{}")
                if not isinstance(params, dict):
                    raise RequestError("'params' must be a JSON object")
                voice = fields.get("voice") or None
            except (RequestError, ValueError) as exc:
                self.send_json(400, {"error": str(exc)})
                return
            with lock:
                started = time.perf_counter()
                try:
                    profile = profiles.get(voice) if voice else None
                    chunks = adapter.synthesize(text, profile, params)
                    # Hold the headers until the first audio exists, so a failure can still be reported.
                    first = next(chunks, None)
                except RequestError as exc:
                    self.send_json(400, {"error": str(exc)})
                    return
                except Exception as exc:  # A model error: report it and keep serving.
                    traceback.print_exc()
                    self.send_json(500, {"error": f"{type(exc).__name__}: {exc}"})
                    return
                self.send_response(200)
                self.send_header("X-Audio-Encoding", "pcm_s16le")
                self.send_header("X-Audio-Sample-Rate", str(adapter.sample_rate))
                self.send_header("X-Audio-Channels", "1")
                self.send_header("Content-Type", "application/octet-stream")
                self.send_header("Transfer-Encoding", "chunked")
                self.end_headers()
                samples = 0
                # Live playback on a slower-than-real-time device: send nothing until this much
                # audio is ready (or the sentence is done), so the stream then keeps ahead.
                hold = int(float(params.get("start_buffer_ms", 0)) * adapter.sample_rate / 1000)
                held = []
                try:
                    for chunk in _chain(first, chunks):
                        data = pcm16(chunk)
                        samples += len(data) // 2
                        if held is not None:
                            held.append(data)
                            if samples < hold:
                                continue
                            data, held = b"".join(held), None
                        if data:
                            self.wfile.write(b"%X\r\n%s\r\n" % (len(data), data))
                            self.wfile.flush()
                    if held:
                        data = b"".join(held)
                        self.wfile.write(b"%X\r\n%s\r\n" % (len(data), data))
                    self.wfile.write(b"0\r\n\r\n")
                    outcome = "ok"
                except Exception as exc:  # Headers are out; closing early is the only signal left.
                    traceback.print_exc()
                    self.close_connection = True
                    outcome = f"failed: {exc}"
                finally:
                    close = getattr(chunks, "close", None)
                    if close:
                        close()
                seconds = samples / adapter.sample_rate
                elapsed = time.perf_counter() - started
                print(f"{time.strftime('%H:%M:%S')} voice={voice or 'default'} chars={len(text)} "
                      f"audio={seconds:.2f}s took={elapsed:.2f}s rtf={elapsed / seconds if seconds else 0:.2f} "
                      f"{outcome}", flush=True)

    return Handler


def _chain(first, rest):
    if first is not None:
        yield first
    yield from rest


def main(adapter):
    parser = argparse.ArgumentParser(description=f"local-tts {adapter.name} engine server")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=0)
    parser.add_argument("--settings", default="{}", help="JSON: device, dtype, optimize")
    parser.add_argument("--download", action="store_true", help="Fetch the model into HF_HOME and exit")
    args = parser.parse_args()
    if args.download:
        from huggingface_hub import snapshot_download
        print(snapshot_download(adapter.repo), flush=True)
        return
    if args.host not in ("127.0.0.1", "localhost", "::1"):
        raise SystemExit("Engine servers listen on loopback only; local-tts api serves other devices")
    settings = json.loads(args.settings)
    started = time.perf_counter()
    adapter.load(settings)
    print(f"{adapter.name}: loaded on {adapter.device} in {time.perf_counter() - started:.1f} s "
          f"(python {sys.version.split()[0]})", flush=True)
    profiles = Profiles(adapter)
    httpd = ThreadingHTTPServer((args.host, args.port), handler(adapter, profiles, threading.Lock()))
    httpd.daemon_threads = True
    print(f"{adapter.name}: listening on http://{args.host}:{httpd.server_address[1]}", flush=True)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()
