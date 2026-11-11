import _isolated_home  # noqa: F401  (must come before local_tts)
from http.server import ThreadingHTTPServer
import json
import os
from pathlib import Path
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch

from local_tts import engines, server
from local_tts.audio import AudioError, Backend, Format, multipart
from local_tts.say import group, joined, merge_speech
from local_tts.ssml import Mark, Pause, Speech, Style

sys.path.insert(0, str(engines.TOOLS / "engines" / "common"))
import server_base  # noqa: E402


class SelectionTests(unittest.TestCase):
    def test_default_engine_and_overrides(self):
        self.assertEqual(engines.resolve({}), "voxcpm2")
        self.assertEqual(engines.resolve({"engine": "voxcpm2"}), "voxcpm2")
        self.assertEqual(engines.resolve({"engine": "voxcpm2"}, "s2"), "s2")
        with self.assertRaises(engines.EngineError):
            engines.resolve({"engine": "nope"})

    def test_old_backend_configs_still_work(self):
        self.assertEqual(engines.resolve({"backend": "s2cpp"}), "s2")
        old = {"backend": "voicevox", "url": "http://127.0.0.1:50099", "speaker": 3}
        bound = engines.select(old)
        self.assertEqual(bound["engine"], "voicevox")
        self.assertNotIn("backend", bound)
        self.assertEqual(engines.url(bound, "voicevox"), "http://127.0.0.1:50099")
        self.assertEqual(engines.url(bound, "s2"), "http://127.0.0.1:3030")  # Not VOICEVOX's address
        with self.assertRaises(engines.EngineError):
            engines.resolve({"backend": "other"})

    def test_each_engine_has_its_own_address(self):
        config = {"url": "http://127.0.0.1:3999", "engines": {"voxcpm2": {"url": "http://127.0.0.1:4001"}}}
        self.assertEqual(engines.url(config, "s2"), "http://127.0.0.1:3999")
        self.assertEqual(engines.url(config, "voxcpm2"), "http://127.0.0.1:4001")
        self.assertEqual(engines.url(config, "omnivoice"), "http://127.0.0.1:3032")
        self.assertEqual(Backend(engines.select(config, "omnivoice")).url, "http://127.0.0.1:3032")

    def test_api_models_map_to_engines(self):
        self.assertEqual(engines.by_api_model("s2-pro"), "s2")
        self.assertEqual(engines.by_api_model("omnivoice"), "omnivoice")
        self.assertIsNone(engines.by_api_model("tts-1"))

    def test_windows_virtual_environment_layout(self):
        with patch.object(engines.sys, "platform", "win32"):
            self.assertEqual(engines.python("voxcpm2").parts[-2:], ("Scripts", "python.exe"))
        with patch.object(engines.sys, "platform", "darwin"):
            self.assertEqual(engines.python("voxcpm2").parts[-2:], ("bin", "python"))
        self.assertIn("LOCAL_TTS_HOME", engines.process_env("omnivoice"))
        self.assertEqual(engines.process_env("omnivoice")["HF_HUB_OFFLINE"], "1")
        self.assertNotIn("HF_HUB_OFFLINE", engines.process_env("omnivoice", offline=False))


class LayoutTests(unittest.TestCase):
    def test_each_pytorch_engine_ships_a_locked_project(self):
        for name, spec in engines.ENGINES.items():
            if spec["kind"] != "python":
                continue
            folder = engines.project(name)
            for file in ("pyproject.toml", "uv.lock", "server.py", ".python-version"):
                self.assertTrue((folder / file).is_file(), f"{name}: {file}")
            text = (folder / "pyproject.toml").read_text(encoding="utf-8")
            self.assertIn("download.pytorch.org/whl/cu128", text)  # CUDA PyTorch on Windows
            self.assertIn(f'repo = "{spec["repo"]}"', (folder / "server.py").read_text(encoding="utf-8"))


class PackingTests(unittest.TestCase):
    def test_join_without_space_in_japanese(self):
        self.assertEqual(joined("こんにちは。", "元気？"), "こんにちは。元気？")
        self.assertEqual(joined("Hello.", "Bye."), "Hello. Bye.")
        self.assertEqual(group(["あ" * 5, "い" * 5, "う" * 5], 10), ["あ" * 5 + "い" * 5, "う" * 5])

    def test_merge_keeps_real_pauses_marks_and_style_changes(self):
        style, fast = Style(), Style(rate=1.2)
        events = [Speech("一。", style), Pause(0.0), Speech("二。", style), Pause(.5), Speech("三。", style),
                  Mark("m"), Speech("四。", style), Speech("五。", fast)]
        merged = merge_speech(events, 200)
        self.assertEqual(merged, [Speech("一。二。", style), Pause(.5), Speech("三。", style), Mark("m"),
                                  Speech("四。", style), Speech("五。", fast)])
        self.assertEqual(len(merge_speech([Speech("あ" * 150, style), Speech("い" * 100, style)], 200)), 2)

    def test_say_packs_sentences_for_omnivoice_but_not_for_s2(self):
        from local_tts.say import say
        line = "一つ目の文です。二つ目の文です、続きです。"
        for engine, expected in (("omnivoice", [line]), ("s2", ["一つ目の文です。", "二つ目の文です、", "続きです。"])):
            backend = Backend({"engine": engine, "say": {"split_first_clause": True, "max_chars": 8}})
            with patch("local_tts.say.render", return_value={}) as render:
                say(backend, line, Path("x.wav"))
            self.assertEqual([e.text for e in render.call_args.args[0]], expected, engine)

    def test_request_chars_only_for_engines_that_want_it(self):
        self.assertEqual(engines.request_chars({}, "omnivoice"), 200)
        self.assertEqual(engines.request_chars({"engines": {"omnivoice": {"request_chars": 0}}}, "omnivoice"), 0)
        self.assertEqual(engines.request_chars({}, "voxcpm2"), 0)
        self.assertEqual(engines.request_chars({}, "s2"), 0)


class PythonBackendTests(unittest.TestCase):
    def synthesize(self, config, text="こんにちは。", live=True):
        import io
        response = io.BytesIO(b"\0\0" * 10)
        response.headers = {"X-Audio-Encoding": "pcm_s16le", "X-Audio-Sample-Rate": "24000",
                            "X-Audio-Channels": "1"}
        with patch("local_tts.audio.urllib.request.build_opener") as build:
            build.return_value.open.return_value = response
            with Backend(config).synthesize(text, live=live) as (fmt, chunks):
                self.assertEqual(fmt, Format(24000))
                b"".join(chunks)
            request = build.return_value.open.call_args.args[0]
        return request

    def test_sends_generation_settings_and_the_voice_name(self):
        config = {"engine": "omnivoice", "voice": "myvoice",
                  "engines": {"omnivoice": {"language": "Japanese", "device": "mps", "request_chars": 100}}}
        request = self.synthesize(config)
        self.assertEqual(request.full_url, "http://127.0.0.1:3032/generate")
        self.assertIn(b'"language": "Japanese"', request.data)
        self.assertIn(b'"live": true', request.data)
        self.assertNotIn(b"device", request.data)  # A process setting, not a request setting
        self.assertNotIn(b"request_chars", request.data)
        self.assertIn(b"myvoice", request.data)
        self.assertNotIn(b"start_buffer_ms", request.data)  # OmniVoice does not stream

    def test_streaming_engine_gets_a_head_start_only_when_live(self):
        config = {"engine": "voxcpm2", "engines": {"voxcpm2": {"stream_start_buffer_ms_per_char": 100}}}
        self.assertIn(b'"start_buffer_ms": 600', self.synthesize(config, "あ" * 6, live=True).data)
        self.assertNotIn(b"start_buffer_ms", self.synthesize(config, "あ" * 6, live=False).data)


class FakeAdapter:
    name = "fake"
    repo = "nobody/fake"
    device = "cpu"
    sample_rate = 8000

    def __init__(self):
        self.built = 0
        self.seen = []

    def build_profile(self, wav, transcript):
        self.built += 1
        return {"transcript": transcript}

    def save_profile(self, profile, path):
        Path(path).write_text(json.dumps(profile), encoding="utf-8")

    def load_profile(self, path):
        return json.loads(Path(path).read_text(encoding="utf-8"))

    def synthesize(self, text, profile, params):
        self.seen.append((text, profile, params))
        if text == "boom":
            raise RuntimeError("model failed")
        yield [0.5] * 80
        yield [-2.0] * 80  # Clipped to -1


class EngineServerTests(unittest.TestCase):
    def setUp(self):
        self.home = Path(tempfile.mkdtemp())
        (self.home / "voices").mkdir()
        (self.home / "voices" / "me.wav").write_bytes(b"RIFF1")
        (self.home / "voices" / "me.json").write_text('{"transcript": "やあ。"}', encoding="utf-8")
        patcher = patch.dict(os.environ, {"LOCAL_TTS_HOME": str(self.home)})
        patcher.start()
        self.addCleanup(patcher.stop)
        self.adapter = FakeAdapter()
        self.profiles = server_base.Profiles(self.adapter)
        self.httpd = ThreadingHTTPServer(("127.0.0.1", 0),
                                         server_base.handler(self.adapter, self.profiles, threading.Lock()))
        threading.Thread(target=self.httpd.serve_forever, daemon=True).start()
        self.addCleanup(self.httpd.server_close)
        self.addCleanup(self.httpd.shutdown)
        self.config = {"engine": "omnivoice", "engines": {"omnivoice": {
            "url": f"http://127.0.0.1:{self.httpd.server_address[1]}"}}}

    def test_contract_matches_what_the_controller_reads(self):
        with Backend({**self.config, "voice": "me"}).synthesize("こんにちは。") as (fmt, chunks):
            pcm = b"".join(chunks)
        self.assertEqual(fmt, Format(8000))
        self.assertEqual(len(pcm), 2 * 160)
        self.assertEqual(pcm[:2], (16384).to_bytes(2, "little", signed=True))
        self.assertEqual(pcm[-2:], (-32767).to_bytes(2, "little", signed=True))
        text, profile, params = self.adapter.seen[-1]
        self.assertEqual((text, profile, params["live"]), ("こんにちは。", {"transcript": "やあ。"}, True))

    def test_profiles_are_cached_and_rebuilt_when_the_recording_changes(self):
        self.profiles.get("me")
        self.profiles.get("me")
        self.assertEqual(self.adapter.built, 1)
        self.assertTrue((self.home / "cache" / "voices" / "fake" / "me.pt").is_file())
        fresh = server_base.Profiles(self.adapter)  # A restarted server reuses the saved profile.
        fresh.get("me")
        self.assertEqual(self.adapter.built, 1)
        (self.home / "voices" / "me.wav").write_bytes(b"RIFF2")
        fresh.get("me")
        self.assertEqual(self.adapter.built, 2)

    def test_errors_are_reported_before_any_audio(self):
        with self.assertRaisesRegex(AudioError, "HTTP 400.*no recording"):
            with Backend({**self.config, "voice": "ghost"}).synthesize("hi"):
                pass
        with self.assertRaisesRegex(AudioError, "HTTP 500.*model failed"):
            with Backend(self.config).synthesize("boom"):
                pass

    def test_multipart_round_trip(self):
        body, content_type = multipart({"text": "日本語", "params": "{}"})
        self.assertEqual(server_base.parse_multipart(content_type, body), {"text": "日本語", "params": "{}"})


class ProcessTests(unittest.TestCase):
    def test_python_engine_pid_is_verified_by_command_line(self):
        with tempfile.TemporaryDirectory() as folder:
            pid_file = Path(folder, "omnivoice-server.pid")
            pid_file.write_text("77", encoding="ascii")
            mine = f"/venv/bin/python {server.marker('omnivoice')} --port 3032"
            with patch("local_tts.server.command_line", return_value=mine):
                self.assertEqual(server.recorded_pid(pid_file, "omnivoice"), 77)
            with patch("local_tts.server.command_line", return_value="/usr/bin/python other.py"):
                self.assertIsNone(server.recorded_pid(pid_file, "omnivoice"))

    def test_uninstalled_engine_says_how_to_install(self):
        with patch("local_tts.server.reachable", return_value=False):
            with self.assertRaisesRegex(AudioError, "engine install voxcpm2"):
                server.start({"engine": "voxcpm2"})

    def test_cuda_memory_check_blocks_a_start_that_cannot_fit(self):
        with patch("local_tts.server.reachable", return_value=False), \
                patch("local_tts.engines.installed", return_value=True), \
                patch("local_tts.engines.model_ready", return_value=True), \
                patch("local_tts.server.free_vram_gb", return_value=3.0):
            with self.assertRaisesRegex(AudioError, "needs about 8 GB"):
                server.start({"engine": "voxcpm2"})


if __name__ == "__main__":
    unittest.main()
