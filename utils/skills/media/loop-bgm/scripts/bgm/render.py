"""音符を波形にしてミックスする。

途切れないループのため、残響とEQは曲の長さを周期とする循環処理で行い、
曲末からはみ出した音は曲頭へ折り返す。リミッターは瞬時処理なので周期性を壊さない。
"""

import wave
import zlib
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from .dsp import SR, add_wrapped
from .gameboy import render_gameboy
from .instruments import AMBIENCE, INSTRUMENTS
from .score import Harmony, build_part, resolve_part

CEILING = 10 ** (-1 / 20)  # -1 dBFS
KNEE = 0.75
REVERB_IR_SECONDS = 1.6


@dataclass
class Report:
    samples: int
    seconds: float
    lufs: float
    peak_db: float
    limited_percent: float
    seam_jump: float
    seam_reference: float
    stem_levels: dict[str, tuple[float, float]]


def stable_rng(seed: int, label: str) -> np.random.Generator:
    """パート名ごとに独立した乱数。他パートを変えても影響しない。"""
    return np.random.default_rng([seed, zlib.crc32(label.encode())])


def render_part(notes, part, name, song, size) -> np.ndarray:
    instrument_name = part["instrument"]
    if instrument_name not in INSTRUMENTS:
        raise ValueError(f"パート {name}: 未知の楽器 {instrument_name!r} / 使用可能: {sorted(INSTRUMENTS)}")
    instrument = INSTRUMENTS[instrument_name]
    rng = stable_rng(song["seed"], name)
    seconds_per_beat = 60 / song["bpm"]
    humanize = song.get("humanize_ms", 0) / 1000
    buffer = np.zeros(size)
    for note in notes:
        length = note.length * seconds_per_beat
        velocity = note.velocity * rng.uniform(0.94, 1.06)
        signal = instrument(SR, note.midi, min(velocity, 1.0), length, rng)
        start = round((note.beat * seconds_per_beat + rng.normal(0, humanize)) * SR)
        add_wrapped(buffer, signal, start)
    return buffer * 10 ** (part.get("gain_db", 0) / 20)


def render_ambience(part, name, song, size) -> np.ndarray:
    """環境音は曲全体で1本の周期信号として作り、左右で別の波形にして広がりを出す。"""
    instrument_name = part["instrument"]
    if instrument_name not in AMBIENCE:
        raise ValueError(f"パート {name}: 未知の環境音 {instrument_name!r} / 使用可能: {sorted(AMBIENCE)}")
    generator = AMBIENCE[instrument_name]
    rng = stable_rng(song["seed"], name)
    return np.stack([generator(SR, size, rng), generator(SR, size, rng)]) * 10 ** (part.get("gain_db", 0) / 20)


def make_reverb_ir(seed: int, t60: float) -> np.ndarray:
    count = int(REVERB_IR_SECONDS * SR)
    predelay = int(0.018 * SR)
    t = np.arange(count) / SR
    rng = stable_rng(seed, "__reverb__")
    channels = []
    for _ in range(2):
        spectrum = np.fft.rfft(rng.standard_normal(count))
        freqs = np.fft.rfftfreq(count, 1 / SR)
        spectrum *= 1 / np.sqrt(1 + (freqs / 6000) ** 2)
        noise = np.fft.irfft(spectrum, count) * 10 ** (-3 * t / t60)
        noise = np.roll(noise, predelay)
        noise[:predelay] = 0
        channels.append(noise / np.sqrt(np.sum(noise**2)))
    return np.stack(channels)


def circular_convolve(signal: np.ndarray, ir: np.ndarray) -> np.ndarray:
    size = len(signal)
    return np.fft.irfft(np.fft.rfft(signal) * np.fft.rfft(ir[:size], size), size)


def eq_curve(size: int, highpass_hz: float, dip_db: float, dip_hz: float) -> np.ndarray:
    freqs = np.fft.rfftfreq(size, 1 / SR)
    positive = np.maximum(freqs, 1e-3)
    highpass = 1 / np.sqrt(1 + (highpass_hz / positive) ** 4)
    dip = dip_db * np.exp(-(np.log2(positive / dip_hz) ** 2) / (2 * 0.9**2))
    return highpass * 10 ** (dip / 20)


def apply_curve(stereo: np.ndarray, curve: np.ndarray) -> np.ndarray:
    return np.fft.irfft(np.fft.rfft(stereo, axis=1) * curve, stereo.shape[1], axis=1)


def k_weight_curve(size: int) -> np.ndarray:
    """ITU-R BS.1770 の 48 kHz 用 K特性の振幅応答。"""
    z = np.exp(-1j * 2 * np.pi * np.fft.rfftfreq(size, 1 / SR) / SR)
    shelf = ((1.53512485958697 - 2.69169618940638 * z + 1.19839281085285 * z**2)
             / (1 - 1.69065929318241 * z + 0.73248077421585 * z**2))
    highpass = (1 - 2 * z + z**2) / (1 - 1.99004745483398 * z + 0.99007225036621 * z**2)
    return np.abs(shelf * highpass)


def lufs_of(stereo: np.ndarray) -> float:
    weighted = apply_curve(stereo, k_weight_curve(stereo.shape[1]))
    return -0.691 + 10 * np.log10(np.sum(np.mean(weighted**2, axis=1)) + 1e-20)


def soft_limit(stereo: np.ndarray) -> tuple[np.ndarray, float]:
    magnitude = np.abs(stereo)
    over = magnitude > KNEE
    span = CEILING - KNEE
    limited = magnitude.copy()
    limited[over] = KNEE + span * np.tanh((magnitude[over] - KNEE) / span)
    return np.sign(stereo) * limited, 100 * float(np.mean(over))


def level_db(stereo: np.ndarray) -> tuple[float, float]:
    """平均(RMS)とピークを dBFS で返す。"""
    floor = 1e-10
    return (float(10 * np.log10(np.mean(stereo**2) + floor)),
            float(20 * np.log10(np.max(np.abs(stereo)) + floor)))


def boundary_jumps(stereo: np.ndarray, bars: int) -> tuple[float, float]:
    """曲末→曲頭と、曲中の各小節境界での最大の段差を返す。

    窓が狭いと、演奏の揺らぎで発音が窓の内外に振れて比較にならないので ±20ms とする。
    """
    size = stereo.shape[1]
    window = int(0.02 * SR)

    def jump(center: int) -> float:
        indices = np.arange(center - window, center + window) % size
        return float(np.max(np.abs(np.diff(stereo[:, indices], axis=1))))

    return jump(0), max(jump(round(size * bar / bars)) for bar in range(1, bars))


def write_wav(path: Path, stereo: np.ndarray) -> None:
    pcm = np.clip(np.round(stereo.T * 32767), -32768, 32767).astype("<i2")
    with wave.open(str(path), "wb") as output:
        output.setnchannels(2)
        output.setsampwidth(2)
        output.setframerate(SR)
        output.writeframes(pcm.tobytes())


def render_standard(spec: dict, harmony: Harmony, size: int) -> dict[str, np.ndarray]:
    song, mix, parts = spec["song"], spec.get("mix", {}), spec["parts"]
    ir = make_reverb_ir(song["seed"], mix.get("reverb_t60", 1.1))
    stems: dict[str, np.ndarray] = {}
    for part_name in parts:
        part = resolve_part(part_name, parts)
        if part["kind"] == "ambience":
            stems[part_name] = render_ambience(part, part_name, song, size)
            continue
        notes = build_part(part_name, part, song, harmony)
        mono = render_part(notes, part, part_name, song, size)
        angle = (part.get("pan", 0.0) + 1) * np.pi / 4
        dry = np.stack([mono * np.cos(angle), mono * np.sin(angle)])
        send = part.get("reverb", 0.0)
        wet = np.stack([circular_convolve(mono, ir[0]), circular_convolve(mono, ir[1])]) * send
        stems[part_name] = dry + wet
    return stems


STYLES = {"standard": render_standard, "gameboy": render_gameboy}


def render_song(spec: dict, out_dir: Path, name: str, style: str = "standard") -> Report:
    song, mix = spec["song"], spec.get("mix", {})
    harmony = Harmony(song["key"], song["mode"])
    beats = song["bars"] * song["beats_per_bar"]
    size = round(beats * 60 / song["bpm"] * SR)

    curve = eq_curve(size, mix.get("highpass_hz", 35.0),
                     mix.get("voice_dip_db", 0.0), mix.get("voice_dip_hz", 2000.0))
    stems = {part: apply_curve(stem, curve) for part, stem in STYLES[style](spec, harmony, size).items()}

    mixed = sum(stems.values())
    gain = 10 ** ((mix.get("target_lufs", -16.0) - lufs_of(mixed)) / 20)
    master, limited_percent = soft_limit(mixed * gain)

    stems_dir = out_dir / "stems"
    stems_dir.mkdir(parents=True, exist_ok=True)
    write_wav(out_dir / f"{name}.wav", master)
    for part_name, stem in stems.items():
        write_wav(stems_dir / f"{part_name}.wav", stem * gain)

    seam_jump, seam_reference = boundary_jumps(master, song["bars"])
    return Report(
        samples=size,
        seconds=size / SR,
        lufs=lufs_of(master),
        peak_db=20 * np.log10(np.max(np.abs(master))),
        limited_percent=limited_percent,
        seam_jump=seam_jump,
        seam_reference=seam_reference,
        stem_levels={part: level_db(stem * gain) for part, stem in stems.items()},
    )
