"""local-tts engine server for Qwen3-TTS (QwenLM/Qwen3-TTS, Apache-2.0).

Started by `local-tts server start --engine qwen3-tts` with this project's virtual environment.
Follows the official README: Qwen3TTSModel.from_pretrained(device_map=..., dtype=...) on a Base
model (only Base models clone voices), create_voice_clone_prompt(ref_audio, ref_text) for a
reusable voice, generate_voice_clone(text, language, voice_clone_prompt=...).
The package returns a whole utterance per call, so /generate sends each request at once.
The voice profile is the prompt's tensors, saved with torch.save (the package has no save/load).

Process settings (from [engines.qwen3-tts] in config.toml): device, dtype.
The 1.7B Base model was chosen over the 0.6B one (2026-11-23; an M4 took 1.71x vs 1.48x the audio length).
Request params: language (e.g. "Japanese"; none = Auto), temperature, top_k, top_p,
repetition_penalty, max_new_tokens, seed.
"""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "common"))

from server_base import RequestError, main, pick_device  # noqa: E402

GENERATION_KEYS = ("temperature", "top_k", "top_p", "repetition_penalty", "max_new_tokens",
                   "subtalker_temperature", "subtalker_top_k", "subtalker_top_p")
PROMPT_FIELDS = ("ref_code", "ref_spk_embedding", "x_vector_only_mode", "icl_mode", "ref_text")


class Qwen3TTSAdapter:
    name = "qwen3-tts"
    repo = "Qwen/Qwen3-TTS-12Hz-1.7B-Base"

    def load(self, settings):
        import torch
        from qwen_tts import Qwen3TTSModel
        self.torch = torch
        self.device = pick_device(settings.get("device"))
        dtype = settings.get("dtype") or ("float32" if self.device == "cpu" else "bfloat16")
        if dtype not in ("float16", "bfloat16", "float32"):
            raise SystemExit(f"Unsupported dtype: {dtype}")
        # A local folder, not the repo id: for a repo id the tokenizer asks the Hub whether the
        # model is a Mistral one (transformers 4.57.3), which fails with HF_HUB_OFFLINE=1.
        from huggingface_hub import snapshot_download
        folder = snapshot_download(self.repo, local_files_only=True)
        self.model = Qwen3TTSModel.from_pretrained(folder, device_map=self.device,
                                                   dtype=getattr(torch, dtype), attn_implementation="sdpa")
        self.sample_rate = int(self.model.model.speech_tokenizer.get_output_sample_rate())

    def build_profile(self, wav, transcript):
        (item,) = self.model.create_voice_clone_prompt(ref_audio=str(wav), ref_text=transcript)
        return item

    def save_profile(self, profile, path):
        values = {k: getattr(profile, k) for k in PROMPT_FIELDS}
        values = {k: (v.cpu() if self.torch.is_tensor(v) else v) for k, v in values.items()}
        self.torch.save(values, str(path))

    def load_profile(self, path):
        from qwen_tts.inference.qwen3_tts_model import VoiceClonePromptItem
        values = self.torch.load(str(path), map_location="cpu", weights_only=True)
        device = self.model.device
        values = {k: (v.to(device) if self.torch.is_tensor(v) else v) for k, v in values.items()}
        return VoiceClonePromptItem(**values)

    def synthesize(self, text, profile, params):
        if profile is None:
            raise RequestError("Qwen3-TTS Base models need a registered voice (--voice <name>)")
        kwargs = {k: params[k] for k in GENERATION_KEYS if k in params}
        if params.get("seed") is not None:
            self.torch.manual_seed(int(params["seed"]))
        try:
            wavs, _ = self.model.generate_voice_clone(text=text, language=params.get("language") or "Auto",
                                                      voice_clone_prompt=[profile], **kwargs)
        except (ValueError, TypeError) as exc:
            raise RequestError(str(exc)) from exc
        yield wavs[0]


if __name__ == "__main__":
    main(Qwen3TTSAdapter())
