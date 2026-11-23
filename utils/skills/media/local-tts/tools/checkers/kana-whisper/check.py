"""Kana Whisper reading check for local-tts: what each sentence of a WAV sounds like, in katakana.

sbintuitions/kana-whisper (MIT) is Whisper large-v3-turbo fine-tuned to write Japanese speech as
katakana, made to score kanji readings of TTS. It reports only what was heard; whether a reading
is right is decided against the script by whoever reads the result (local-tts SKILL.md).

    check.py --download                      fetch the model into HF_HOME and exit
    check.py WAV TIMING_JSON [N ...]         JSON list of {segment, text, heard}; N are 1-based
                                             segment numbers (default: all)
"""
import argparse
import json
import sys

REPO = "sbintuitions/kana-whisper"
RATE = 16000


def pick_device():
    import torch
    if torch.cuda.is_available():
        return "cuda", torch.float16
    if getattr(torch.backends, "mps", None) and torch.backends.mps.is_available():
        return "mps", torch.float32  # float16 on MPS was not tried; float32 is what was measured.
    return "cpu", torch.float32


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--download", action="store_true", help="Fetch the model into HF_HOME and exit")
    parser.add_argument("wav", nargs="?")
    parser.add_argument("timing", nargs="?")
    parser.add_argument("segments", nargs="*", type=int)
    args = parser.parse_args()
    if args.download:
        from huggingface_hub import snapshot_download
        print(snapshot_download(REPO), flush=True)
        return 0
    if not args.wav or not args.timing:
        parser.error("WAV and TIMING_JSON are required")

    import numpy as np
    import soundfile as sf
    import torch
    import torchaudio.functional as F
    from transformers import pipeline

    timing = json.loads(open(args.timing, encoding="utf-8").read())
    segments = timing["segments"]
    wanted = args.segments or range(1, len(segments) + 1)
    for number in wanted:
        if not 1 <= number <= len(segments):
            parser.error(f"segment {number} is out of range 1-{len(segments)}")
    audio, rate = sf.read(args.wav, dtype="float32", always_2d=True)
    audio = audio.mean(axis=1)
    device, dtype = pick_device()
    recognize = pipeline("automatic-speech-recognition", model=REPO, device=device, torch_dtype=dtype,
                         chunk_length_s=30, generate_kwargs={"language": "ja", "task": "transcribe"})
    result = []
    for number in wanted:
        segment = segments[number - 1]
        clip = torch.from_numpy(np.ascontiguousarray(audio[segment["start_frame"]:segment["end_frame"]]))
        if rate != RATE:
            clip = F.resample(clip, rate, RATE)
        heard = recognize({"raw": clip.numpy(), "sampling_rate": RATE})["text"].strip()
        result.append({"segment": number, "text": segment["text"], "heard": heard})
    json.dump(result, sys.stdout, ensure_ascii=False)
    return 0


if __name__ == "__main__":
    sys.exit(main())
