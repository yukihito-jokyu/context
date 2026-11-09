"""ゲームボーイ風の鳴らし方。設計図は通常版と共通で、4チャンネルの制約で演奏する。

ch1 矩形波: メロディ
ch2 矩形波: コード(アルペジオ)。飾りのメロディが鳴る間はそちらを優先
ch3 波形メモリ: ベース
ch4 ノイズ: 打楽器を1音ずつ
"""

from dataclasses import dataclass
from functools import lru_cache

import numpy as np

from .dsp import SR, add_wrapped
from .score import Note, build_part, resolve_part

OVERSAMPLE = 4
OVERSAMPLED_SR = SR * OVERSAMPLE
PULSE_CLOCK = 131072
WAVE_CLOCK = 65536
NOISE_CLOCK = 524288
ENVELOPE_RATE = 64
DRIVER_RATE = 60
ARPEGGIO_SECONDS = 3 / DRIVER_RATE
WAVE_TABLE = np.array([15] * 11 + [12, 9, 6, 3] + [0] * 13 + [3, 6, 9, 12], dtype=float)
WAVE_TABLE -= WAVE_TABLE.mean()
WAVE_VOLUME = 0.5  # 実機の波形メモリの音量は 100 / 50 / 25%


@dataclass(frozen=True)
class PulseVoice:
    duty: float
    peak: int
    pace: int
    vibrato: bool = False


@dataclass(frozen=True)
class WaveVoice:
    pass


@dataclass(frozen=True)
class NoiseVoice:
    divisor: int
    shift: int
    short: bool
    peak: int
    pace: int
    priority: int


LEAD = PulseVoice(duty=0.25, peak=14, pace=4, vibrato=True)
HARMONY = PulseVoice(duty=0.5, peak=11, pace=2)
ORNAMENT = PulseVoice(duty=0.125, peak=11, pace=2)
BASS = WaveVoice()
NOISE_VOICES = {
    "bongo_lo": NoiseVoice(divisor=1, shift=5, short=False, peak=13, pace=2, priority=0),
    "bongo_hi": NoiseVoice(divisor=1, shift=3, short=False, peak=9, pace=1, priority=1),
    "woodblock": NoiseVoice(divisor=2, shift=3, short=True, peak=6, pace=1, priority=2),
    "tambourine": NoiseVoice(divisor=1, shift=1, short=False, peak=6, pace=1, priority=3),
}


@dataclass
class ChipNote:
    beat: float
    length: float
    midis: tuple[int, ...]  # 2音以上ならアルペジオ
    velocity: float
    voice: PulseVoice | WaveVoice | NoiseVoice


def to_chip(notes: list[Note], voice) -> list[ChipNote]:
    return [ChipNote(n.beat, n.length, (n.midi,), n.velocity, voice) for n in notes]


def group_chords(notes: list[Note], voice) -> list[ChipNote]:
    """同時に鳴る和音を1音のアルペジオにまとめる。"""
    grouped: list[ChipNote] = []
    for note in sorted(notes, key=lambda n: n.beat):
        if grouped and note.beat - grouped[-1].beat < 0.1:
            grouped[-1].midis += (note.midi,)
        else:
            grouped.append(ChipNote(note.beat, note.length, (note.midi,), note.velocity, voice))
    return grouped


def merge_layers(layers: list[list[ChipNote]], hold_claim: bool) -> list[ChipNote]:
    """前の層を優先して1本にする。hold_claim なら優先音の発音中は下位の発音を捨てる。"""
    merged: list[ChipNote] = []
    for layer in layers:
        for note in layer:
            taken = any(
                claim.beat - 1e-6 <= note.beat < claim.beat + (claim.length if hold_claim else 1e-6)
                for claim in merged
            )
            if not taken:
                merged.append(note)
    return merged


def fit_monophonic(notes, total_beats, fraction=1.0, ring_beats=0.0) -> list[ChipNote]:
    """次の音で必ず切る。1チャンネル1音の制約はここで保証する(曲末は曲頭の音で切る)。"""
    ordered = sorted(notes, key=lambda n: n.beat)
    for index, note in enumerate(ordered):
        following = ordered[(index + 1) % len(ordered)].beat
        if index == len(ordered) - 1:
            following += total_beats
        note.length = min((following - note.beat) * fraction, max(note.length, ring_beats))
    return ordered


def envelope(count: int, velocity: float, peak: int, pace: int) -> np.ndarray:
    """4bit の音量を 64 Hz の階段で減衰させる。"""
    start = np.clip(round(peak * velocity), 1, 15)
    steps = np.floor(np.arange(count) / OVERSAMPLED_SR * ENVELOPE_RATE / pace)
    return np.maximum(start - steps, 0) / 15


def register_hz(midi: np.ndarray, clock: int) -> np.ndarray:
    """周波数を 11bit レジスタの刻みに丸める。"""
    hz = 440.0 * 2.0 ** ((midi - 69) / 12)
    register = np.clip(np.round(2048 - clock / hz), 0, 2047)
    return clock / (2048 - register)


def midi_track(note: ChipNote, count: int, vibrato: bool) -> np.ndarray:
    t = np.arange(count) / OVERSAMPLED_SR
    tones = np.array(note.midis, dtype=float)
    track = tones[(np.floor(t / ARPEGGIO_SECONDS).astype(int)) % len(tones)]
    if vibrato:
        frame_time = np.floor(t * DRIVER_RATE) / DRIVER_RATE
        track = track + 0.22 * np.sin(2 * np.pi * 5.5 * frame_time) * (frame_time > 0.25)
    return track


def synth_pulse(note: ChipNote, count: int) -> np.ndarray:
    voice = note.voice
    hz = register_hz(midi_track(note, count, voice.vibrato), PULSE_CLOCK)
    phase = np.cumsum(hz) / OVERSAMPLED_SR
    return ((phase % 1 < voice.duty) - voice.duty) * envelope(count, note.velocity, voice.peak, voice.pace)


def synth_wave(note: ChipNote, count: int) -> np.ndarray:
    hz = register_hz(midi_track(note, count, False), WAVE_CLOCK)
    phase = np.cumsum(hz) / OVERSAMPLED_SR
    return WAVE_TABLE[(np.floor(phase * len(WAVE_TABLE)).astype(int)) % len(WAVE_TABLE)] / 15 * WAVE_VOLUME


@lru_cache(maxsize=2)
def lfsr_sequence(short: bool) -> np.ndarray:
    state = 0x7FFF
    output = []
    for _ in range(127 if short else 32767):
        bit = (state ^ (state >> 1)) & 1
        state = (state >> 1) | (bit << 14)
        if short:
            state = (state & ~(1 << 6)) | (bit << 6)
        output.append((~state) & 1)
    return np.array(output, dtype=float) - 0.5


def synth_noise(note: ChipNote, count: int) -> np.ndarray:
    voice = note.voice
    sequence = lfsr_sequence(voice.short)
    clock = NOISE_CLOCK / voice.divisor / 2 ** (voice.shift + 1)
    index = np.floor(np.arange(count) / OVERSAMPLED_SR * clock).astype(int) % len(sequence)
    return sequence[index] * envelope(count, note.velocity, voice.peak, voice.pace)


SYNTH = {PulseVoice: synth_pulse, WaveVoice: synth_wave, NoiseVoice: synth_noise}


def render_channel(notes: list[ChipNote], size: int, seconds_per_beat: float) -> np.ndarray:
    buffer = np.zeros(size * OVERSAMPLE)
    samples_per_beat = seconds_per_beat * OVERSAMPLED_SR
    for note in notes:
        start = round(note.beat * samples_per_beat)
        end = round((note.beat + note.length) * samples_per_beat)
        if end > start:
            add_wrapped(buffer, SYNTH[type(note.voice)](note, end - start), start)
    return downsample(buffer, size)


def downsample(signal: np.ndarray, size: int) -> np.ndarray:
    """周期信号のまま帯域制限して間引く。折り返しノイズを防ぐ。"""
    spectrum = np.fft.rfft(signal)[: size // 2 + 1]
    taper = np.clip((23000 - np.fft.rfftfreq(size, 1 / SR)) / 3000, 0, 1)
    return np.fft.irfft(spectrum * taper, size) / OVERSAMPLE


def arrange(spec: dict, harmony) -> dict[str, list[ChipNote]]:
    """設計図の全パートを4チャンネルへ割り振る。"""
    song, parts = spec["song"], spec["parts"]
    total_beats = song["bars"] * song["beats_per_bar"]
    resolved = {name: resolve_part(name, parts) for name in parts
                if parts[name].get("kind") != "ambience"}
    notes = {name: build_part(name, part, song, harmony) for name, part in resolved.items()}

    def of_kind(kind: str) -> list[str]:
        return [name for name, part in resolved.items()
                if part["kind"] == kind and "copy_of" not in parts[name]]

    melodies = sorted(of_kind("melody"), key=lambda name: len(notes[name]), reverse=True)
    lead = to_chip(notes[melodies[0]], LEAD) if melodies else []
    ornaments = [chip for name in melodies[1:] for chip in to_chip(notes[name], ORNAMENT)]
    ornaments = fit_monophonic(ornaments, total_beats, ring_beats=1.0)
    chords = [chip for name in of_kind("chord")[:1] for chip in group_chords(notes[name], HARMONY)]
    bass = [chip for name in of_kind("bass")[:1] for chip in to_chip(notes[name], BASS)]

    # 鳥の声のようにノイズで代用できない音は鳴らさない
    drum_names = sorted(
        (name for name in of_kind("drum") if resolved[name]["instrument"] in NOISE_VOICES),
        key=lambda name: NOISE_VOICES[resolved[name]["instrument"]].priority,
    )
    drums = [[ChipNote(n.beat, 1.0, (0,), n.velocity, NOISE_VOICES[resolved[name]["instrument"]])
              for n in notes[name]] for name in drum_names]

    return {
        "ch1_pulse_melody": fit_monophonic(lead, total_beats, ring_beats=1.0),
        "ch2_pulse_harmony": fit_monophonic(merge_layers([ornaments, chords], hold_claim=True),
                                            total_beats, ring_beats=0.5),
        "ch3_wave_bass": fit_monophonic(bass, total_beats, fraction=0.85, ring_beats=1.0),
        "ch4_noise_drums": fit_monophonic(merge_layers(drums, hold_claim=False), total_beats),
    }


def render_gameboy(spec: dict, harmony, size: int) -> dict[str, np.ndarray]:
    seconds_per_beat = 60 / spec["song"]["bpm"]
    stems = {}
    for channel, notes in arrange(spec, harmony).items():
        mono = render_channel(notes, size, seconds_per_beat) * 0.25
        stems[channel] = np.stack([mono, mono])
    return stems
