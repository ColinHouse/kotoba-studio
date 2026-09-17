"""Subtitle import: one uploaded file becomes one import session full of lines.

With a `video_path` form field, every cue also gets its original audio and a
still from the cue's midpoint; the path is checked against the user's allowed
`video_dirs` first (see services/capture/media.py). ffmpeg is optional: when it
is missing the import still succeeds and the response says only text was taken.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, Request, UploadFile
from sqlalchemy.orm import Session

from kotoba.api.capture.sources import get_source_or_404
from kotoba.core.db import get_db
from kotoba.models import CaptureSession, Line
from kotoba.schemas import LineCreate
from kotoba.services import settings_store
from kotoba.services.capture import media
from kotoba.services.text.encoding import decode_text
from kotoba.services.text.ingest import create_line
from kotoba.services.text.subtitles import Cue, parse_subtitles

router = APIRouter(prefix="/sources", tags=["capture"])

NO_FFMPEG_NOTE = "未找到 ffmpeg，本次只导入文本"


@router.post("/{source_id}/subtitles")
async def import_subtitles(
    source_id: int,
    request: Request,
    file: UploadFile = File(...),
    video_path: str | None = Form(None),
    head_pad_ms: int = Form(media.HEAD_PAD_MS, ge=0, le=5000),
    tail_pad_ms: int = Form(media.TAIL_PAD_MS, ge=0, le=5000),
    db: Session = Depends(get_db),
) -> dict:
    get_source_or_404(db, source_id)
    cues = parse_subtitles(decode_text(await file.read()))
    session = CaptureSession(source_id=source_id, mode="import", text_source="subtitle")
    db.add(session)
    db.commit()

    created = skipped = 0
    pairs: list[tuple[Line, Cue]] = []
    for position, cue in enumerate(cues, start=1):
        line, duplicate = create_line(
            db,
            LineCreate(
                session_id=session.id,
                source_id=source_id,
                text=cue.text,
                origin="subtitle",
                speaker=cue.speaker,
                start_ms=cue.start_ms,
                end_ms=cue.end_ms,
                locator={"kind": "time", "start_ms": cue.start_ms, "end_ms": cue.end_ms},
                ord=position,
            ),
        )
        if duplicate:
            skipped += 1
        else:
            created += 1
        pairs.append((line, cue))

    media_cut = media_failed = 0
    note: str | None = None
    if video_path:
        if not media.ffmpeg_available():
            note = NO_FFMPEG_NOTE
        else:
            video = media.resolve_video(video_path, settings_store.get(db, "video_dirs") or [])
            cuts = media.cut_cues(
                video,
                [cue for _, cue in pairs],
                request.app.state.paths.media_dir,
                head_pad_ms=head_pad_ms,
                tail_pad_ms=tail_pad_ms,
            )
            for (line, _), cut in zip(pairs, cuts, strict=True):
                if cut is None:
                    media_failed += 1
                    continue
                if not line.audio_path:
                    line.audio_path = cut.audio_path
                if not line.screenshot_path:
                    line.screenshot_path = cut.screenshot_path
                media_cut += 1
            db.commit()

    return {
        "session_id": session.id,
        "created": created,
        "skipped": skipped,
        "media_cut": media_cut,
        "media_failed": media_failed,
        "media_note": note,
    }
