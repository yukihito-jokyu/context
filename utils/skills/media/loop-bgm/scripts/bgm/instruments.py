"""全ての楽器音を数式で合成する。録音素材は使わない。

各楽器は f(sr, midi, velocity, length_seconds, rng) の形でモノラル波形を返す。
"""

from functools import partial

import numpy as np

from .dsp import add_wrapped


def midi_to_hz(midi: float) -> float:
    return 440.0 * 2.0 ** ((midi - 69) / 12)


def modal(sr, freqs, amps, decays, duration) -> np.ndarray:
    """減衰する正弦波の和。ナイキスト付近の成分は除く。"""
    t = np.arange(int(duration * sr)) / sr
    out = np.zeros_like(t)
    for freq, amp, decay in zip(freqs, amps, decays):
        if freq < sr * 0.45:
            out += amp * np.exp(-t / decay) * np.sin(2 * np.pi * freq * t)
    return out


def band_noise(sr, count, low, high, rng) -> np.ndarray:
    spectrum = np.fft.rfft(rng.standard_normal(count))
    freqs = np.fft.rfftfreq(count, 1 / sr)
    spectrum[(freqs < low) | (freqs > high)] = 0
    noise = np.fft.irfft(spectrum, count)
    return noise / (np.max(np.abs(noise)) + 1e-12)


def noise_burst(sr, duration, low, high, decay, rng) -> np.ndarray:
    count = int(duration * sr)
    return band_noise(sr, count, low, high, rng) * np.exp(-np.arange(count) / sr / decay)


def mix_at_start(body: np.ndarray, attack: np.ndarray, amount: float) -> np.ndarray:
    body[: len(attack)] += amount * attack
    return body


def finish(signal: np.ndarray, sr: int, velocity: float, fade=0.005) -> np.ndarray:
    """音量を揃え、末尾のプチノイズを防ぐ。"""
    fade_count = min(int(fade * sr), len(signal))
    signal[-fade_count:] *= np.linspace(1, 0, fade_count)
    return signal / (np.max(np.abs(signal)) + 1e-12) * velocity**1.3


def body_gain(freqs: np.ndarray, peaks: list[float], width: float) -> np.ndarray:
    gain = np.full_like(freqs, 0.35)
    for peak in peaks:
        gain += 1 / (1 + ((freqs - peak) / (peak * width)) ** 2)
    return gain


def plucked(sr, midi, velocity, rng, tau, pluck_point, rolloff, peaks, duration, top):
    f0 = midi_to_hz(midi)
    count = max(int(top / f0), 1)
    harmonics = np.arange(1, count + 1)
    freqs = f0 * harmonics * np.sqrt(1 + 1e-4 * harmonics**2)
    amps = np.abs(np.sin(np.pi * harmonics * pluck_point)) / harmonics ** (rolloff - 0.5 * velocity)
    amps = amps * body_gain(freqs, peaks, 0.35)
    decays = tau / (1 + 0.28 * (harmonics - 1))
    return modal(sr, freqs, amps, decays, duration)


def pizz_bass(sr, midi, velocity, length, rng):
    body = plucked(sr, midi, velocity, rng, tau=0.42, pluck_point=0.2, rolloff=1.5,
                   peaks=[70, 110, 190], duration=1.3, top=3500)
    thump = noise_burst(sr, 0.03, 120, 900, 0.008, rng)
    return finish(mix_at_start(body, thump, 0.18 * velocity), sr, velocity)


def pizz_violin(sr, midi, velocity, length, rng):
    body = plucked(sr, midi, velocity, rng, tau=0.2, pluck_point=0.18, rolloff=1.3,
                   peaks=[290, 460, 1000, 2600], duration=0.7, top=7000)
    tick = noise_burst(sr, 0.012, 1200, 7000, 0.003, rng)
    return finish(mix_at_start(body, tick, 0.12 * velocity), sr, velocity)


def xylophone(sr, midi, velocity, length, rng):
    f0 = midi_to_hz(midi)
    tau = 0.2 * (523.25 / f0) ** 0.4
    freqs = [f0, f0 * 3.0, f0 * 6.2, f0 * 10.1]
    amps = [1.0, 0.3 + 0.2 * velocity, 0.1 * velocity, 0.04 * velocity]
    decays = [tau, tau * 0.45, tau * 0.2, tau * 0.1]
    body = modal(sr, freqs, amps, decays, 0.8)
    tick = noise_burst(sr, 0.01, 1500, 9000, 0.0025, rng)
    return finish(mix_at_start(body, tick, 0.3 * velocity), sr, velocity)


def glockenspiel(sr, midi, velocity, length, rng):
    f0 = midi_to_hz(midi)
    freqs = [f0, f0 * 2.76, f0 * 5.40, f0 * 8.93]
    amps = [1.0, 0.4, 0.16 * velocity, 0.06 * velocity]
    decays = [0.85, 0.42, 0.16, 0.07]
    body = modal(sr, freqs, amps, decays, 2.8)
    tick = noise_burst(sr, 0.006, 3000, 12000, 0.0015, rng)
    return finish(mix_at_start(body, tick, 0.2 * velocity), sr, velocity)


def ocarina(sr, midi, velocity, length, rng):
    f0 = midi_to_hz(midi)
    duration = max(length * 0.95, 0.08) + 0.06
    count = int(duration * sr)
    t = np.arange(count) / sr
    vibrato_depth = np.clip((t - 0.18) / 0.2, 0, 1) * 0.006
    phase = 2 * np.pi * f0 * (t + vibrato_depth * np.sin(2 * np.pi * 5.2 * t) / (2 * np.pi * 5.2))
    tone = np.sin(phase) + 0.1 * np.sin(2 * phase) + 0.05 * np.sin(3 * phase)
    breath = band_noise(sr, count, f0 * 0.8, f0 * 4, rng) * 0.05
    envelope = np.minimum(1, t / 0.025) * np.minimum(1, (duration - t) / 0.05)
    return finish((tone + breath) * envelope, sr, velocity, fade=0.002)


def bongo(sr, midi, velocity, length, rng, f0):
    t = np.arange(int(0.3 * sr)) / sr
    out = np.zeros_like(t)
    for ratio, amp, decay in [(1.0, 1.0, 0.1), (1.59, 0.5, 0.05), (2.14, 0.28, 0.03)]:
        freq = f0 * ratio
        phase = 2 * np.pi * freq * (t + 0.12 * 0.012 * (1 - np.exp(-t / 0.012)))
        out += amp * np.exp(-t / decay) * np.sin(phase)
    slap = noise_burst(sr, 0.03, 800, 4500, 0.005, rng)
    return finish(mix_at_start(out, slap, 0.3 * velocity), sr, velocity)


def tambourine(sr, midi, velocity, length, rng):
    duration = 0.28
    decay = 0.04 + 0.05 * velocity
    t = np.arange(int(duration * sr)) / sr
    freqs = rng.uniform(5200, 11500, 14)
    jingle = sum(np.sin(2 * np.pi * freq * t + phase)
                 for freq, phase in zip(freqs, rng.uniform(0, 2 * np.pi, 14))) / 14
    shimmer = band_noise(sr, len(t), 6500, 15000, rng)
    attack = np.minimum(1, t / 0.0015)
    return finish((jingle + 0.7 * shimmer) * attack * np.exp(-t / decay), sr, velocity)


def woodblock(sr, midi, velocity, length, rng):
    body = modal(sr, [980, 1370, 2620], [1.0, 0.45, 0.2], [0.03, 0.018, 0.01], 0.16)
    tick = noise_burst(sr, 0.005, 2000, 9000, 0.001, rng)
    return finish(mix_at_start(body, tick, 0.2 * velocity), sr, velocity)


def harp(sr, midi, velocity, length, rng):
    body = plucked(sr, midi, velocity, rng, tau=0.75, pluck_point=0.3, rolloff=1.9,
                   peaks=[200, 420, 900], duration=2.4, top=6000)
    tick = noise_burst(sr, 0.008, 800, 5000, 0.002, rng)
    return finish(mix_at_start(body, tick, 0.05 * velocity), sr, velocity)


def syllable(sr, start_hz, end_hz, duration, vibrato_hz=0.0, vibrato_depth=0.0):
    """鳥の声の一節。周波数が滑らかに動く短い音。"""
    t = np.arange(int(duration * sr)) / sr
    progress = t / duration
    hz = start_hz + (end_hz - start_hz) * progress + vibrato_depth * np.sin(2 * np.pi * vibrato_hz * t)
    phase = 2 * np.pi * np.cumsum(hz) / sr
    return (np.sin(phase) + 0.08 * np.sin(2 * phase)) * np.sin(np.pi * progress) ** 2


def bird_warbler(sr, midi, velocity, length, rng):
    """高く細かいさえずり。呼び出すたびに節回しが変わる。"""
    base = rng.uniform(3400, 4600)
    pieces = []
    for _ in range(rng.integers(3, 7)):
        start = base * rng.uniform(0.85, 1.25)
        pieces.append(syllable(sr, start, start * rng.uniform(0.75, 1.3), rng.uniform(0.05, 0.11)))
        pieces.append(np.zeros(int(rng.uniform(0.02, 0.06) * sr)))
    return finish(np.concatenate(pieces), sr, velocity)


def bird_whistle(sr, midi, velocity, length, rng):
    """澄んだ2音の口笛のような鳴き声。"""
    base = rng.uniform(2300, 2800)
    pieces = [syllable(sr, base * 1.06, base, 0.32, 6, 12), np.zeros(int(0.1 * sr)),
              syllable(sr, base * 0.86, base * 0.8, 0.45, 6, 14)]
    return finish(np.concatenate(pieces), sr, velocity)


def shaped_noise(sr, size, rng, low, high, tilt) -> np.ndarray:
    """曲の長さを周期とするノイズ。RMS は 1。"""
    freqs = np.fft.rfftfreq(size, 1 / sr)
    gain = ((freqs >= low) & (freqs <= high)) / np.maximum(freqs, 1.0) ** tilt
    noise = np.fft.irfft(np.fft.rfft(rng.standard_normal(size)) * gain, size)
    return noise / (np.sqrt(np.mean(noise**2)) + 1e-12)


def periodic_swell(size, rng, cycles, depth) -> np.ndarray:
    """曲の長さの整数分の1の周期だけを使う、ゆっくりした音量の揺れ。"""
    position = 2 * np.pi * np.arange(size) / size
    cycles = list(cycles)
    swell = 1 + sum(np.cos(k * position + rng.uniform(0, 2 * np.pi)) for k in cycles) * depth / np.sqrt(len(cycles))
    return np.maximum(swell, 0.15)


def normalized(signal: np.ndarray, rms=0.1) -> np.ndarray:
    return signal * rms / (np.sqrt(np.mean(signal**2)) + 1e-12)


def stream(sr, size, rng):
    water = shaped_noise(sr, size, rng, 300, 7000, 0.5) * periodic_swell(size, rng, range(4, 24), 0.25)
    bubbles = np.zeros(size)
    for _ in range(int(size / sr * 60)):
        t = np.arange(int(rng.uniform(0.015, 0.06) * sr)) / sr
        duration = t[-1]
        phase = 2 * np.pi * rng.uniform(450, 1900) * (t + rng.uniform(0.2, 0.6) * t**2 / (2 * duration))
        add_wrapped(bubbles, np.sin(phase) * np.exp(-3 * t / duration) * rng.uniform(0.3, 1.0),
                    int(rng.integers(size)))
    return normalized(water + 0.7 * normalized(bubbles, 1.0))


def forest_air(sr, size, rng):
    low = shaped_noise(sr, size, rng, 80, 500, 1.0) * periodic_swell(size, rng, range(2, 7), 0.5)
    middle = shaped_noise(sr, size, rng, 500, 2200, 0.5) * periodic_swell(size, rng, range(3, 10), 0.5)
    leaves = shaped_noise(sr, size, rng, 2500, 9000, 0.2) * periodic_swell(size, rng, range(3, 14), 0.7)
    return normalized(0.5 * low + 0.6 * middle + 0.5 * leaves)


AMBIENCE = {"stream": stream, "forest_air": forest_air}

INSTRUMENTS = {
    "harp": harp,
    "bird_warbler": bird_warbler,
    "bird_whistle": bird_whistle,
    "pizz_bass": pizz_bass,
    "pizz_violin": pizz_violin,
    "xylophone": xylophone,
    "glockenspiel": glockenspiel,
    "ocarina": ocarina,
    "bongo_hi": partial(bongo, f0=420.0),
    "bongo_lo": partial(bongo, f0=290.0),
    "tambourine": tambourine,
    "woodblock": woodblock,
}
