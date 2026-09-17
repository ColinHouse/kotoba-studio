"""Cut a cue's audio and a still frame out of the video its subtitle came with.

ffmpeg is an optional external dependency, never bundled: when it is missing the
import still creates every line and says so in the response. The per-cue ffmpeg
call is injectable (`runner`) so the tests assert the arguments — times,
padding, output paths — without a real video, and the batch keeps one cue's
failure from taking the episode down with it.

Batch strategy: one short ffmpeg run per cue per stream, with the pool capped at
the CPU count. A single ffmpeg invocation producing hundreds of outputs exists
(`segment`), but it gives up per-cue isolation and per-cue naming; bounded
concurrency keeps failures countable and the code debuggable.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from collections.abc import Callable, Sequence
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import UTC, datetime
from functools import lru_cache
from pathlib import Path
from uuid import uuid4

from sqlalchemy import case, select
from sqlalchemy.orm import Session

from kotoba.core.errors import ApiError
from kotoba.models import Line
from kotoba.services.text.subtitles import Cue

# 字幕时间轴是给人看的导航提示，不是音频边界：掐在 cue 的起止点上，句头的气息
# 和句尾的语尾会被切掉。两端各留一点余量，宁可多留半拍。
HEAD_PAD_MS = 250
TAIL_PAD_MS = 500
MIN_CUT_S = 0.05
AUDIO_BITRATE = "64k"
FRAME_QUALITY = "3"
# 凝缩音频：cue 之间短于这个间隔就并成一段再切，否则一集会有几百个碎片，
# 接缝处还会爆音；段与段之间补一小段静音，听感不至于挤在一起。
GAP_MS = 500
SILENCE_MS = 200
SILENCE_SOURCE = "anullsrc=r=48000:cl=mono"

Runner = Callable[[Sequence[str]], None]


@dataclass(slots=True)
class Cut:
    """Media-relative paths, the same shape Line.audio_path/screenshot_path store."""

    audio_path: str
    screenshot_path: str


@lru_cache(maxsize=1)
def ffmpeg_path() -> str | None:
    """Resolved once per process; the batch never probes PATH per cue."""
    return shutil.which("ffmpeg")


def ffmpeg_available() -> bool:
    return ffmpeg_path() is not None


def resolve_video(raw: str, allowed_dirs: Sequence[str]) -> Path:
    """The video may only be read from a directory the user has allowed.

    The API is reachable from the LAN, so a path straight from the request body
    would otherwise turn the subtitle importer into an arbitrary-file reader.
    """
    video = Path(raw).expanduser()
    try:
        video = video.resolve(strict=True)
    except OSError as exc:
        raise ApiError("video_not_found", f"找不到视频：{raw}") from exc
    if not video.is_file():
        raise ApiError("video_not_found", f"不是文件：{raw}")
    allowed = [Path(entry).expanduser().resolve() for entry in allowed_dirs if str(entry).strip()]
    if not any(video.is_relative_to(entry) for entry in allowed):
        raise ApiError(
            "video_not_allowed",
            "视频不在允许的目录内：先把它的目录加入设置里的 video_dirs。",
        )
    return video


def audio_args(
    ffmpeg: str,
    video: Path,
    start_ms: int,
    end_ms: int,
    out: Path,
    *,
    head_pad_ms: int = HEAD_PAD_MS,
    tail_pad_ms: int = TAIL_PAD_MS,
) -> list[str]:
    start = max(0, start_ms - head_pad_ms)
    duration = max(MIN_CUT_S, (end_ms + tail_pad_ms - start) / 1000)
    return [
        ffmpeg,
        "-y",
        "-ss",
        f"{start / 1000:.3f}",
        "-i",
        str(video),
        "-t",
        f"{duration:.3f}",
        "-vn",
        "-c:a",
        "libopus",
        "-b:a",
        AUDIO_BITRATE,
        str(out),
    ]


def frame_args(ffmpeg: str, video: Path, at_ms: int, out: Path) -> list[str]:
    """The still comes from the cue's midpoint: the first frame is often a cut or black."""
    return [
        ffmpeg,
        "-y",
        "-ss",
        f"{at_ms / 1000:.3f}",
        "-i",
        str(video),
        "-frames:v",
        "1",
        "-q:v",
        FRAME_QUALITY,
        str(out),
    ]


def run_ffmpeg(args: Sequence[str]) -> None:
    """One invocation; a non-zero exit is this cue's failure, not the batch's."""
    completed = subprocess.run(args, capture_output=True, text=True, check=False)
    if completed.returncode != 0:
        detail = (completed.stderr or "").strip().splitlines()
        raise RuntimeError(detail[-1] if detail else "ffmpeg failed")


def cut_cues(
    video: Path,
    cues: Sequence[Cue],
    media_dir: Path,
    *,
    runner: Runner | None = None,
    head_pad_ms: int = HEAD_PAD_MS,
    tail_pad_ms: int = TAIL_PAD_MS,
    max_workers: int | None = None,
) -> list[Cut | None]:
    """One entry per cue (None = that cue failed); bounded concurrency, failures counted."""
    ffmpeg = ffmpeg_path()
    if ffmpeg is None:
        return [None] * len(cues)
    run = runner or run_ffmpeg
    token = uuid4().hex[:8]
    workers = max_workers or max(1, min(os.cpu_count() or 1, len(cues) or 1))

    def one(index: int, cue: Cue) -> Cut | None:
        prefix = f"{token}-{index:05d}"
        audio_file, audio_rel = _target(media_dir, "audio", f"{prefix}.opus")
        frame_file, frame_rel = _target(media_dir, "screens", f"{prefix}.jpg")
        try:
            run(
                audio_args(
                    ffmpeg,
                    video,
                    cue.start_ms,
                    cue.end_ms,
                    audio_file,
                    head_pad_ms=head_pad_ms,
                    tail_pad_ms=tail_pad_ms,
                )
            )
            run(frame_args(ffmpeg, video, (cue.start_ms + cue.end_ms) // 2, frame_file))
        except Exception:  # noqa: BLE001 - one cue's failure must not abort the episode
            audio_file.unlink(missing_ok=True)
            frame_file.unlink(missing_ok=True)
            return None
        return Cut(audio_path=audio_rel, screenshot_path=frame_rel)

    with ThreadPoolExecutor(max_workers=workers) as pool:
        return list(pool.map(lambda item: one(*item), enumerate(cues)))


def _target(media_dir: Path, subdir: str, name: str) -> tuple[Path, str]:
    """Same layout as screen.py: media/<subdir>/YYYYMMDD/<name>."""
    day = datetime.now(UTC).strftime("%Y%m%d")
    folder = media_dir / subdir / day
    folder.mkdir(parents=True, exist_ok=True)
    return folder / name, f"{subdir}/{day}/{name}"


@dataclass(slots=True)
class Span:
    start_ms: int
    end_ms: int


@dataclass(slots=True)
class CondenseReport:
    segments: int
    lines_used: int
    output: str  # media-relative path, downloadable through /media


def merge_spans(spans: Sequence[Span], gap_ms: int = GAP_MS) -> list[Span]:
    """Cues closer than `gap_ms` become one segment, overlaps included.

    Cutting every cue separately would leave hundreds of fragments and a click
    at each seam; keeping only the short gaps also makes the pauses that survive
    meaningful (a scene change, not every breath).
    """
    if not spans:
        return []
    merged = [Span(spans[0].start_ms, spans[0].end_ms)]
    for span in spans[1:]:
        last = merged[-1]
        if span.start_ms - last.end_ms < gap_ms:
            last.end_ms = max(last.end_ms, span.end_ms)
        else:
            merged.append(Span(span.start_ms, span.end_ms))
    return merged


def timeline(db: Session, source_id: int) -> list[Span]:
    """Every line of the source that has a usable timeline, in `ord` order."""
    rows = db.scalars(
        select(Line)
        .where(
            Line.source_id == source_id,
            Line.start_ms.is_not(None),
            Line.end_ms.is_not(None),
            Line.end_ms > Line.start_ms,
        )
        .order_by(case((Line.ord.is_(None), 1), else_=0), Line.ord.asc(), Line.id.asc())
    ).all()
    return [Span(span.start_ms, span.end_ms) for span in rows]


def silence_args(ffmpeg: str, duration_ms: int, out: Path) -> list[str]:
    return [
        ffmpeg,
        "-y",
        "-f",
        "lavfi",
        "-i",
        SILENCE_SOURCE,
        "-t",
        f"{duration_ms / 1000:.3f}",
        "-c:a",
        "libopus",
        "-b:a",
        AUDIO_BITRATE,
        str(out),
    ]


def concat_args(ffmpeg: str, list_file: Path, out: Path) -> list[str]:
    return [
        ffmpeg,
        "-y",
        "-f",
        "concat",
        "-safe",
        "0",
        "-i",
        str(list_file),
        "-c:a",
        "libopus",
        "-b:a",
        AUDIO_BITRATE,
        str(out),
    ]


def condense(
    video: Path,
    spans: Sequence[Span],
    media_dir: Path,
    out_name: str,
    *,
    gap_ms: int = GAP_MS,
    silence_ms: int = SILENCE_MS,
    runner: Runner | None = None,
    progress: Callable[[int, int], None] | None = None,
) -> CondenseReport:
    """Cut every merged segment and join them with silence into one track.

    The finished file replaces the previous one only after it is complete, so a
    failed regeneration does not destroy the track the user already has.
    """
    ffmpeg = ffmpeg_path()
    if ffmpeg is None:
        raise ApiError("ffmpeg_unavailable", "未找到 ffmpeg：凝缩音频需要它。", 503)
    run = runner or run_ffmpeg
    segments = merge_spans(spans, gap_ms)
    if not segments:
        raise ApiError("no_timeline", "这部作品还没有带时间轴的台词", 400)

    target = media_dir / out_name
    target.parent.mkdir(parents=True, exist_ok=True)
    # Keep the .opus extension: ffmpeg infers the muxer from it.
    staged = target.with_name(f"{target.stem}.part{target.suffix}")
    try:
        with tempfile.TemporaryDirectory(prefix="kotoba-condensed-") as tmp:
            work = Path(tmp)
            silence = work / "silence.opus"
            if silence_ms > 0:
                run(silence_args(ffmpeg, silence_ms, silence))
            parts: list[Path] = []
            for index, segment in enumerate(segments, start=1):
                part = work / f"part-{index:05d}.opus"
                run(
                    audio_args(
                        ffmpeg,
                        video,
                        segment.start_ms,
                        segment.end_ms,
                        part,
                        head_pad_ms=0,
                        tail_pad_ms=0,
                    )
                )
                parts.append(part)
                if progress is not None:
                    progress(index, len(segments))
            sequence: list[Path] = []
            for index, part in enumerate(parts):
                if index and silence_ms > 0:
                    sequence.append(silence)
                sequence.append(part)
            list_file = work / "concat.txt"
            list_file.write_text(
                "".join(f"file '{path.as_posix()}'\n" for path in sequence), encoding="utf-8"
            )
            run(concat_args(ffmpeg, list_file, staged))
        staged.replace(target)
    except BaseException:
        staged.unlink(missing_ok=True)
        raise
    return CondenseReport(segments=len(segments), lines_used=len(spans), output=out_name)
