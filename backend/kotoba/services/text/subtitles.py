"""Parse .srt / .ass subtitle text into cues.

Pure functions: no database, no filesystem, no ffmpeg. The subtitle importer
turns the cues into Lines, and the parser stays testable without any of that.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from kotoba.core.errors import ApiError

_SRT_CLOCK = re.compile(r"(?P<h>\d{1,3}):(?P<m>\d{1,2}):(?P<s>\d{1,2})[,.](?P<frac>\d{1,3})")
_ASS_CLOCK = re.compile(r"(?P<h>\d+):(?P<m>\d{1,2}):(?P<s>\d{1,2})[.](?P<frac>\d{1,2})")
_ASS_OVERRIDE = re.compile(r"\{[^}]*\}")
_ASS_SECTION = re.compile(r"^\[([^\]]+)\]\s*$")
_ASS_ESCAPES = (r"\N", r"\n", r"\h")
# An [Events] header on its own line. Searching the whole text would misread an SRT
# whose dialogue happens to quote "[Events]" as an ASS file.
_ASS_EVENTS_HEADER = re.compile(r"^\s*\[events\]\s*$", re.IGNORECASE | re.MULTILINE)
# Drawing mode: \p1 and up switch the payload to vector commands, \p0 switches back.
# The commands are coordinates, not dialogue, and must not reach the tokenizer.
_ASS_DRAWING = re.compile(r"\{[^}]*\\p[1-9]\d*[^}]*\}.*?(?=\{[^}]*\\p0\b[^}]*\}|$)", re.DOTALL)
# Inline markup an SRT may carry: <i>/<b>/<font ...> and ASS-style {\an8} positioning.
_SRT_TAG = re.compile(r"</?(?:i|b|u|s|em|strong|font|ruby|rt|rp)\b[^>]*>", re.IGNORECASE)


@dataclass(slots=True)
class Cue:
    start_ms: int
    end_ms: int
    text: str
    speaker: str | None = None


def parse_subtitles(content: str, fmt: str | None = None) -> list[Cue]:
    """Parse subtitle text into cues; `fmt` is `"srt"`, `"ass"` or None to detect."""
    content = content.lstrip("\ufeff")
    cues = _parse_ass(content) if _resolve_format(content, fmt) == "ass" else _parse_srt(content)
    if not cues:
        raise ApiError("bad_subtitle", "未能在字幕中解析出任何台词")
    return cues


def _resolve_format(content: str, fmt: str | None) -> str:
    if fmt is None:
        # Only ASS/SSA has an [Events] section *header*; match the line, not the
        # substring, so dialogue quoting "[Events]" does not misdetect the file.
        return "ass" if _ASS_EVENTS_HEADER.search(content) else "srt"
    normalized = fmt.strip().lower()
    if normalized in {"srt", "ass"}:
        return normalized
    raise ApiError("bad_subtitle", f"不支持的字幕格式：{fmt}")


def _parse_srt(content: str) -> list[Cue]:
    cues: list[Cue] = []
    for block in re.split(r"\n\s*\n", content):
        lines = block.splitlines()
        timing = next((i for i, line in enumerate(lines) if "-->" in line), None)
        if timing is None:
            continue
        start, _, end = (part.strip() for part in lines[timing].partition("-->"))
        start_ms, end_ms = _srt_ms(start), _srt_ms(end)
        if start_ms is None or end_ms is None:
            continue
        text = " ".join(line.strip() for line in lines[timing + 1 :])
        text = _ASS_OVERRIDE.sub("", _SRT_TAG.sub("", text))
        text = " ".join(text.split())
        if text:
            cues.append(Cue(start_ms, end_ms, text))
    return cues


def _parse_ass(content: str) -> list[Cue]:
    cues: list[Cue] = []
    in_events = False
    fields: list[str] = []
    for raw in content.splitlines():
        line = raw.strip()
        section = _ASS_SECTION.match(line)
        if section is not None:
            in_events = section.group(1).strip().lower() == "events"
            fields = []
            continue
        if not in_events:
            continue
        if line.lower().startswith("format:"):
            fields = [field.strip().lower() for field in line[len("format:") :].split(",")]
            continue
        if fields and line.lower().startswith("dialogue:"):
            cue = _ass_cue(line[len("dialogue:") :].lstrip(), fields)
            if cue is not None:
                cues.append(cue)
    return cues


def _ass_cue(payload: str, fields: list[str]) -> Cue | None:
    # The Text field is last, so split no further than the number of fields:
    # a comma inside the line itself must stay in the text.
    parts = (part.strip() for part in payload.split(",", len(fields) - 1))
    # A malformed line can have fewer fields; the guard below skips it.
    values = dict(zip(fields, parts, strict=False))
    if not {"start", "end", "text"} <= values.keys():
        return None
    start_ms, end_ms = _ass_ms(values["start"]), _ass_ms(values["end"])
    if start_ms is None or end_ms is None:
        return None
    text = _clean_ass_text(values["text"])
    if not text:
        return None
    return Cue(start_ms, end_ms, text, values.get("name") or None)


def _clean_ass_text(text: str) -> str:
    text = _ASS_DRAWING.sub("", text)
    text = _ASS_OVERRIDE.sub("", text)
    for escape in _ASS_ESCAPES:
        text = text.replace(escape, " ")
    return " ".join(text.split())


def _srt_ms(value: str) -> int | None:
    match = _SRT_CLOCK.match(value)
    if match is None:
        return None
    # A short fraction is left-padded, so ".5" is 500 ms, not 5.
    millis = int(match.group("frac").ljust(3, "0"))
    return _clock_ms(match) + millis


def _ass_ms(value: str) -> int | None:
    match = _ASS_CLOCK.fullmatch(value)
    if match is None:
        return None
    return _clock_ms(match) + int(match.group("frac").ljust(2, "0")) * 10


def _clock_ms(match: re.Match[str]) -> int:
    hours, minutes, seconds = (int(match.group(unit)) for unit in ("h", "m", "s"))
    return ((hours * 60 + minutes) * 60 + seconds) * 1000
