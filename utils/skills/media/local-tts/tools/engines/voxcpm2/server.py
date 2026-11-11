"""local-tts engine server for VoxCPM2 (openbmb/VoxCPM2, Apache-2.0).

Started by `local-tts server start --engine voxcpm2` with this project's virtual environment.
Cloning follows the model card's "Ultimate Cloning": the same recording as prompt (with its
transcript, continuation mode) and as reference. The prompt cache that VoxCPM builds for that
(build_prompt_cache) is the saved voice profile; generation reuses it through
_generate_with_prompt_cache, which is what VoxCPM.generate() calls internally.

- live requests (say, playback) stream audio as it is generated; VoxCPM cannot retry bad cases there
- other requests (speak, api) return the whole sentence with bad-case retry on, as VoxCPM.generate does
- torch.compile (VoxCPM's `optimize`) is off unless set: it needs Triton, which Windows and macOS lack

Request params (from [engines.voxcpm2] in config.toml): cfg_value (2.0), inference_timesteps (10), seed.
"""

from pathlib import Path
import re
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "common"))

from server_base import main, pick_device  # noqa: E402


class VoxCPM2Adapter:
    name = "voxcpm2"
    repo = "openbmb/VoxCPM2"

    def load(self, settings):
        import torch
        from voxcpm import VoxCPM
        self.torch = torch
        device = pick_device(settings.get("device"))
        optimize = bool(settings.get("optimize", sys.platform.startswith("linux")))
        self.model = VoxCPM.from_pretrained(self.repo, load_denoiser=False, optimize=optimize, device=device)
        self.tts = self.model.tts_model
        self.device = str(next(self.tts.parameters()).device)
        self.sample_rate = int(self.tts.sample_rate)

    def build_profile(self, wav, transcript):
        return self.tts.build_prompt_cache(prompt_text=transcript, prompt_wav_path=str(wav),
                                           reference_wav_path=str(wav))

    def save_profile(self, profile, path):
        self.torch.save({k: (v.cpu() if self.torch.is_tensor(v) else v) for k, v in profile.items()}, str(path))

    def load_profile(self, path):
        # Kept on the CPU like build_prompt_cache's output; VoxCPM moves what it needs.
        return self.torch.load(str(path), map_location="cpu", weights_only=True)

    def synthesize(self, text, profile, params):
        text = re.sub(r"\s+", " ", text.replace("\n", " ")).strip()  # As VoxCPM.generate does.
        live = bool(params.get("live", False))
        seed = params.get("seed")
        results = self.tts._generate_with_prompt_cache(
            target_text=text, prompt_cache=profile, min_len=2, max_len=int(params.get("max_len", 4096)),
            inference_timesteps=int(params.get("inference_timesteps", 10)),
            cfg_value=float(params.get("cfg_value", 2.0)),
            retry_badcase=not live, retry_badcase_max_times=3, retry_badcase_ratio_threshold=6.0,
            streaming=live, seed=None if seed is None else int(seed))
        try:
            for wav, _, _ in results:
                yield wav.squeeze(0).float().cpu().numpy()
                if not live:
                    break
        finally:
            results.close()


if __name__ == "__main__":
    main(VoxCPM2Adapter())
