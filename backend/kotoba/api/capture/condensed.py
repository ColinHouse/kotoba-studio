"""Condensed audio: every dialogue segment of a source joined into one track.

The build runs as a background job with observable progress (the JMdict install
pattern), because cutting a whole episode takes far longer than a request should.
One job at a time, like the dictionary installer.
"""

from __future__ import annotations

import threading
from collections.abc import Callable

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from kotoba.api.capture.sources import get_source_or_404
from kotoba.core.config import Paths
from kotoba.core.db import get_db
from kotoba.core.errors import ApiError
from kotoba.services import settings_store
from kotoba.services.capture import media
from kotoba.services.capture.gate import gate

router = APIRouter(prefix="/sources", tags=["capture"])

CONDENSED_SUBDIR = "condensed"
LONG_WRITE = "condensed-audio"


class CondensedIn(BaseModel):
    video_path: str
    gap_ms: int = Field(default=media.GAP_MS, ge=0, le=5000)
    silence_ms: int = Field(default=media.SILENCE_MS, ge=0, le=5000)


class CondenseJob:
    """Background condensed-audio build with observable state."""

    def __init__(self) -> None:
        self.state = "idle"
        self.message = ""
        self.done = 0
        self.total = 0
        self.source_id: int | None = None
        self.output: str | None = None
        self.lines_used = 0
        self.segments = 0
        self._thread: threading.Thread | None = None

    def snapshot(self) -> dict:
        return {
            "state": self.state,
            "message": self.message,
            "done": self.done,
            "total": self.total,
            "source_id": self.source_id,
            "output": self.output,
            "lines_used": self.lines_used,
            "segments": self.segments,
        }

    def start(
        self,
        session_factory: Callable[[], Session],
        paths: Paths,
        source_id: int,
        video_path,
        *,
        gap_ms: int,
        silence_ms: int,
    ) -> bool:
        if self._thread and self._thread.is_alive():
            return False
        # 和另外四个长作业一样在**请求线程**登记闸门：恢复备份期间直接拿到
        # restoring，而不是留一个跑到一半、正在写 media_dir 的线程。
        gate.begin_long_write(LONG_WRITE)
        self.state, self.message = "running", "正在收集台词…"
        self.done = self.total = 0
        self.source_id, self.output = source_id, None
        self.lines_used = self.segments = 0

        def run() -> None:
            db = session_factory()
            try:
                spans = media.timeline(db, source_id)
                if not spans:
                    self.state, self.message = "error", "这部作品还没有带时间轴的台词"
                    return
                self.lines_used = len(spans)

                def progress(done: int, total: int) -> None:
                    self.done, self.total = done, total
                    self.message = f"正在切台词… {done}/{total} 段"

                self.message = "正在切台词…"
                report = media.condense(
                    video_path,
                    spans,
                    paths.media_dir,
                    f"{CONDENSED_SUBDIR}/{source_id}.opus",
                    gap_ms=gap_ms,
                    silence_ms=silence_ms,
                    progress=progress,
                )
                self.output, self.segments = report.output, report.segments
                self.state, self.message = "done", f"凝缩音频已生成（{report.segments} 段）"
            except Exception as exc:  # noqa: BLE001 - report through state; a silent thread would say "running" for ever
                self.state, self.message = "error", str(exc)
            finally:
                db.close()
                gate.end_long_write(LONG_WRITE)

        try:
            self._thread = threading.Thread(target=run, name="condensed-audio", daemon=True)
            self._thread.start()
        except BaseException:
            # 线程起不来时闸门必须放开，否则之后每一次恢复备份都会被拒。
            gate.end_long_write(LONG_WRITE)
            self.state, self.message = "error", "无法启动后台任务"
            raise
        return True


condense_job = CondenseJob()


@router.post("/{source_id}/condensed", status_code=202)
def start_condensed(
    source_id: int, body: CondensedIn, request: Request, db: Session = Depends(get_db)
) -> dict:
    get_source_or_404(db, source_id)
    if not media.ffmpeg_available():
        raise ApiError("ffmpeg_unavailable", "未找到 ffmpeg：凝缩音频需要它。", 503)
    video = media.resolve_video(body.video_path, settings_store.get(db, "video_dirs") or [])
    started = condense_job.start(
        request.app.state.db.session,
        request.app.state.paths,
        source_id,
        video,
        gap_ms=body.gap_ms,
        silence_ms=body.silence_ms,
    )
    return {"started": started, **condense_job.snapshot()}


@router.get("/{source_id}/condensed")
def condensed_status(source_id: int, db: Session = Depends(get_db)) -> dict:
    get_source_or_404(db, source_id)
    return condense_job.snapshot()
