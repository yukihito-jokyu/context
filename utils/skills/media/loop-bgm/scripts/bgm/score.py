"""設計図(TOML)を音符のリストに変換する。

メロディは音度、ベースとコードはコード基準で書くので、
key / mode / chords を変えるだけで全パートが追従する。
"""

import re
from dataclasses import dataclass

PITCH_CLASS = {
    "C": 0, "C#": 1, "Db": 1, "D": 2, "D#": 3, "Eb": 3, "E": 4, "F": 5, "F#": 6,
    "Gb": 6, "G": 7, "G#": 8, "Ab": 8, "A": 9, "A#": 10, "Bb": 10, "B": 11,
}
SCALES = {"major": [0, 2, 4, 5, 7, 9, 11], "minor": [0, 2, 3, 5, 7, 8, 10]}
DRUM_VELOCITY = {"X": 1.0, "x": 0.75, "o": 0.45}
BASS_TONE_INDEX = {"R": 0, "3": 1, "5": 2, "7": 3}
CHORD_TONE_INDEX = {"1": 0, "3": 1, "5": 2, "7": 3}

MELODY_TOKEN = re.compile(r"^([#b]?)([1-7])('*|,*)$")
CHORD_TOKEN = re.compile(r"^([1-7])(7?)$")


@dataclass
class Note:
    beat: float
    length: float  # 拍
    midi: int | None  # 打楽器は None
    velocity: float


class Harmony:
    def __init__(self, key: str, mode: str):
        if key not in PITCH_CLASS:
            raise ValueError(f"未知の key です: {key!r}")
        if mode not in SCALES:
            raise ValueError(f"mode は major か minor です: {mode!r}")
        pitch_class = PITCH_CLASS[key]
        self.tonic = pitch_class - 12 if pitch_class > 6 else pitch_class
        self.scale = SCALES[mode]

    def degree_semitones(self, degree: int) -> int:
        """音度(1始まり。7を超えると上のオクターブ)を主音からの半音数にする。"""
        octave, index = divmod(degree - 1, 7)
        return self.tonic + self.scale[index] + 12 * octave

    def chord_semitones(self, token: str) -> list[int]:
        match = CHORD_TOKEN.match(token)
        if not match:
            raise ValueError(f"コードの書式が不正です: {token!r} (例: 1, 5, 27)")
        root = int(match[1])
        count = 4 if match[2] else 3
        return [self.degree_semitones(root + 2 * i) for i in range(count)]


def parse_bars(pattern: str) -> list[list[str]]:
    """'|' か改行で小節を分け、小節内はトークンの個数で等分する。"""
    bars = [bar.split() for bar in re.split(r"[|\n]", pattern)]
    return [bar for bar in bars if bar]


def octave_marks(marks: str) -> int:
    return marks.count("'") - marks.count(",")


def midi_base(octave: int) -> int:
    return 12 * (octave + 1)


def bass_root(root: int, octave: int) -> int:
    """ベースの音域に収まるよう、ルートを G までに折り返す。"""
    base = midi_base(octave)
    midi = base + root % 12
    return midi - 12 if midi > base + 7 else midi


def voice_chord(semitones: list[int], octave: int) -> list[int]:
    """全ての音を中心の音の近くに集め、密集配置で滑らかに連結する。"""
    center = midi_base(octave) + 7
    return sorted(center - 6 + (s - (center - 6)) % 12 for s in semitones)


def metric_accent(beat: float, beats_per_bar: int) -> float:
    if beat % beats_per_bar == 0:
        return 1.0
    return 0.92 if float(beat).is_integer() else 0.82


def token_to_notes(
    part_name: str, part: dict, token: str, beat: float, step: float,
    chord: str, harmony: Harmony, song: dict,
) -> list[Note]:
    kind = part["kind"]
    octave = part.get("octave", 4)
    accent = metric_accent(beat, song["beats_per_bar"])

    def error() -> ValueError:
        return ValueError(f"パート {part_name}: 解釈できないトークン {token!r} (kind={kind})")

    if kind == "drum":
        if token not in DRUM_VELOCITY:
            raise error()
        return [Note(beat, step, None, DRUM_VELOCITY[token])]

    if kind == "melody":
        match = MELODY_TOKEN.match(token)
        if not match:
            raise error()
        accidental = {"#": 1, "b": -1, "": 0}[match[1]]
        midi = (midi_base(octave) + harmony.degree_semitones(int(match[2]))
                + accidental + 12 * octave_marks(match[3]))
        return [Note(beat, step, midi, 0.85 * accent)]

    tones = harmony.chord_semitones(chord)

    if kind == "bass":
        match = re.match(r"^(R|3|5|7|8)('*|,*)$", token)
        if not match:
            raise error()
        root = bass_root(tones[0], octave)
        if match[1] == "8":
            midi = root + 12
        else:
            index = min(BASS_TONE_INDEX[match[1]], len(tones) - 1)
            midi = root + tones[index] - tones[0]
        midi += 12 * octave_marks(match[2])
        return [Note(beat, step, midi, 0.9 * accent)]

    if kind == "chord":
        voiced = voice_chord(tones, octave)
        if token == "x":
            strum_beats = part.get("strum_ms", 0) / 1000 * song["bpm"] / 60
            return [Note(beat + i * strum_beats, step, midi, 0.8 * accent)
                    for i, midi in enumerate(voiced)]
        if token not in CHORD_TONE_INDEX:
            raise error()
        pitch_class = tones[min(CHORD_TONE_INDEX[token], len(tones) - 1)] % 12
        midi = next(m for m in voiced if m % 12 == pitch_class)
        return [Note(beat, step, midi, 0.8 * accent)]

    raise ValueError(f"パート {part_name}: 未知の kind です: {kind!r}")


def resolve_part(name: str, parts: dict) -> dict:
    """copy_of があれば元パートの設定に、自身の設定を上書きする。"""
    part = parts[name]
    if "copy_of" not in part:
        return part
    source = part["copy_of"]
    if source not in parts or "copy_of" in parts[source]:
        raise ValueError(f"パート {name}: copy_of の参照先が不正です: {source!r}")
    merged = {**parts[source], **part}
    del merged["copy_of"]
    return merged


def build_part(name: str, part: dict, song: dict, harmony: Harmony) -> list[Note]:
    bars = parse_bars(part["pattern"])
    chords = song["chords"]
    beats_per_bar = song["beats_per_bar"]
    notes: list[Note] = []
    sounding: list[Note] = []
    for bar_index in range(song["bars"]):
        tokens = bars[bar_index % len(bars)]
        chord = chords[bar_index % len(chords)]
        step = beats_per_bar / len(tokens)
        for token_index, token in enumerate(tokens):
            beat = bar_index * beats_per_bar + token_index * step
            if token == "-":
                for note in sounding:
                    note.length += step
            elif token == ".":
                sounding = []
            else:
                sounding = token_to_notes(name, part, token, beat, step, chord, harmony, song)
                notes.extend(sounding)
    return notes
