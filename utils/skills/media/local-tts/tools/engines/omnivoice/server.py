"""local-tts engine server for OmniVoice (k2-fsa/OmniVoice, Apache-2.0).

Started by `local-tts server start --engine omnivoice` with this project's virtual environment.
Follows the official README: from_pretrained(device_map=..., dtype=float16 on GPUs),
create_voice_clone_prompt -> VoiceClonePrompt.save/load for reusable voices, generate(...).
OmniVoice returns a whole utterance per call, so /generate sends each sentence at once.

Request params (from [engines.omnivoice] in config.toml): language (e.g. "Japanese"; none =
language-agnostic), num_step (32), guidance_scale (2.0), speed, seed.
"""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "common"))

from server_base import RequestError, main, pick_device  # noqa: E402

GENERATION_KEYS = ("num_step", "guidance_scale", "t_shift", "speed", "duration",
                   "position_temperature", "class_temperature", "denoise")


class OmniVoiceAdapter:
    name = "omnivoice"
    repo = "k2-fsa/OmniVoice"

    def load(self, settings):
        import torch
        from omnivoice import OmniVoice
        self.torch = torch
        self.device = pick_device(settings.get("device"))
        dtype = settings.get("dtype") or ("float32" if self.device == "cpu" else "float16")
        if dtype not in ("float16", "bfloat16", "float32"):
            raise SystemExit(f"Unsupported dtype: {dtype}")
        self.model = OmniVoice.from_pretrained(self.repo, device_map=self.device, dtype=getattr(torch, dtype))
        self.sample_rate = int(getattr(self.model, "sampling_rate", 24000))

    def build_profile(self, wav, transcript):
        return self.model.create_voice_clone_prompt(ref_audio=str(wav), ref_text=transcript)

    def save_profile(self, profile, path):
        profile.save(str(path))

    def load_profile(self, path):
        from omnivoice import VoiceClonePrompt
        return VoiceClonePrompt.load(str(path))

    def synthesize(self, text, profile, params):
        kwargs = {k: params[k] for k in GENERATION_KEYS if k in params}
        if params.get("seed") is not None:
            self.torch.manual_seed(int(params["seed"]))
        try:
            (wav,) = self.model.generate(text=text, language=params.get("language") or None,
                                         voice_clone_prompt=profile, **kwargs)
        except (ValueError, TypeError) as exc:
            raise RequestError(str(exc)) from exc
        yield wav


if __name__ == "__main__":
    main(OmniVoiceAdapter())
