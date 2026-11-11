"""Interactive speech: sentence splitting and the `say` loop."""

import re
import sys

from . import voices
from .audio import AudioError, render
from .fillers import Fillers
from .ssml import Pause, Speech, Style

SENTENCE = re.compile(r"[^。！？!?]+[。！？!?]*")


def clauses(sentence, max_chars):
    """Split a sentence longer than max_chars at 、 outside 「」/（）, or between 」「 in a list of
    titles, regrouping clauses so each piece stays near max_chars. Long requests run slower and
    need a long head start."""
    if not max_chars or len(sentence) <= max_chars:
        return [sentence]
    found, depth, current = [], 0, ""
    for i, ch in enumerate(sentence):
        current += ch
        depth += (ch in "「『（(【") - (ch in "」』）)】")
        between_titles = ch in "」』" and sentence[i + 1:i + 2] in ("「", "『")
        if (ch == "、" or between_titles) and depth <= 0:
            found.append(current)
            current = ""
    if current:
        found.append(current)
    pieces = []
    for clause in found:
        if pieces and len(pieces[-1]) + len(clause) <= max_chars:
            pieces[-1] += clause
        else:
            pieces.append(clause)
    return pieces


def segments(line, split_first_clause, max_chars=0):
    """The line's sentences, long ones cut into clauses; optionally the first clause (up to 、)
    alone, so its audio comes sooner."""
    parts = [p for s in SENTENCE.findall(line) if s.strip() for p in clauses(s.strip(), max_chars)]
    if split_first_clause and parts:
        head, comma, rest = parts[0].partition("、")
        if comma and rest:
            parts[:1] = [head + comma, rest]
    return parts


def joined(left, right):
    """Two pieces of text as one request: no space after Japanese, a space between other words."""
    if not left:
        return right
    return left + ("" if not left[-1].isascii() or left[-1] in "、。" else " ") + right


def group(parts, limit):
    """Consecutive parts packed into requests of up to `limit` characters (a longer part stays whole)."""
    packed = []
    for part in parts:
        if packed and len(packed[-1]) + len(part) <= limit:
            packed[-1] = joined(packed[-1], part)
        else:
            packed.append(part)
    return packed


def merge_speech(events, limit):
    """SSML events with runs of same-style speech (no real pause or mark between) packed up to `limit`
    characters per request. The timing JSON then has one segment per packed request."""
    merged = []
    for event in events:
        if isinstance(event, Pause) and not event.seconds:
            continue  # The zero-length break SSML puts between sentences does not separate requests.
        last = merged[-1] if merged else None
        if (isinstance(event, Speech) and isinstance(last, Speech) and last.style == event.style
                and len(last.text) + len(event.text) <= limit):
            merged[-1] = Speech(joined(last.text, event.text), event.style)
        else:
            merged.append(event)
    return merged


def say(backend, text, output):
    """Speak the given text once, or each typed line until Ctrl+Z/Ctrl+D; "/voice NAME" switches."""
    settings = backend.config.get("say", {})
    fillers = Fillers(backend, settings) if settings.get("filler", False) else None
    while True:
        try:
            line = text or input("> ").strip()
        except EOFError:
            return 0
        if not text and line.startswith("/voice"):
            try:
                voices.set_voice(backend.config, line[len("/voice"):].strip())
                print(f"voice: {backend.config.get('voice', 'default')}")
                if fillers:
                    fillers.prepare()
            except AudioError as exc:
                print(f"ERROR: {exc}", file=sys.stderr)
            continue
        # One request per sentence: long requests run slower (RTF 1.65 vs ~1.5 measured).
        # Each sentence gets its own server head start, so pauses fall between sentences,
        # never inside one. An optional filler plays only if the first audio is late.
        # Punctuation-only input ("！？") yields no sentences and is skipped.
        from . import engines
        limit = engines.request_chars(backend.config, backend.engine)
        if limit:
            # This engine pays a fixed cost per request, so short first clauses would only add waits.
            sentences = group(segments(line, False, 0), limit)
        else:
            sentences = segments(line, settings.get("split_first_clause", False),
                                 int(settings.get("max_chars", 40)))
        if sentences:
            try:
                report = render([Speech(s, Style()) for s in sentences], backend, output, play=True,
                                force=True, filler=fillers and fillers.choose(sentences[0]),
                                filler_after=fillers.after if fillers else 0)
                if fillers and not text:
                    fillers.heard(report)
            except AudioError as exc:
                if text:
                    raise
                print(f"ERROR: {exc}", file=sys.stderr)
        if text:
            return 0
