"""Rolling in-memory media buffer, so a line can be completed after it passed.

The learner notices they missed a word after the line already left the screen;
this keeps the last minute of frames (and, once an audio source exists, audio
chunks) around to backfill it. The buffer is pure memory: it never writes to
the data directory. Only when a backfill is requested does the chosen blob go
through the normal media path.
"""

from __future__ import annotations

import threading
from collections import deque
from dataclasses import dataclass
from datetime import datetime, timedelta

from kotoba.models import utcnow


@dataclass(frozen=True, slots=True)
class Buffered:
    at: datetime
    data: bytes


class MediaBuffer:
    """Keep the last ``seconds`` of media, bounded by ``max_bytes`` of memory.

    Both caps evict the oldest entry first; the byte cap is the one that
    matters, because frame size and cadence vary with the display.
    """

    def __init__(self, seconds: float = 60.0, max_bytes: int = 200 * 1024 * 1024) -> None:
        self.seconds = seconds
        self.max_bytes = max_bytes
        self._frames: deque[Buffered] = deque()
        self._audio: deque[Buffered] = deque()
        self._size = 0
        self._lock = threading.Lock()

    def add_frame(self, png: bytes, at: datetime | None = None) -> None:
        with self._lock:
            self._frames.append(Buffered(at or utcnow(), png))
            self._size += len(png)
            self._evict()

    def add_audio(self, data: bytes, at: datetime | None = None) -> None:
        with self._lock:
            self._audio.append(Buffered(at or utcnow(), data))
            self._size += len(data)
            self._evict()

    def frame_at(self, at: datetime, tolerance_s: float) -> Buffered | None:
        return self._nearest(self._frames, at, tolerance_s)

    def audio_at(self, at: datetime, tolerance_s: float) -> Buffered | None:
        return self._nearest(self._audio, at, tolerance_s)

    def clear(self) -> None:
        with self._lock:
            self._frames.clear()
            self._audio.clear()
            self._size = 0

    def stats(self) -> dict:
        with self._lock:
            return {
                "frames": len(self._frames),
                "audio_chunks": len(self._audio),
                "bytes": self._size,
            }

    @staticmethod
    def _nearest(entries: deque[Buffered], at: datetime, tolerance_s: float) -> Buffered | None:
        cutoff = at - timedelta(seconds=tolerance_s)
        best: Buffered | None = None
        for entry in entries:
            if cutoff <= entry.at <= at and (best is None or entry.at > best.at):
                best = entry
        return best

    def _evict(self) -> None:
        cutoff = utcnow() - timedelta(seconds=self.seconds)
        for entries in (self._frames, self._audio):
            while entries and entries[0].at < cutoff:
                self._size -= len(entries.popleft().data)
        while self._size > self.max_bytes:
            frame = self._frames[0] if self._frames else None
            audio = self._audio[0] if self._audio else None
            if frame is None and audio is None:
                return
            if audio is None or (frame is not None and frame.at <= audio.at):
                self._size -= len(self._frames.popleft().data)
            else:
                self._size -= len(self._audio.popleft().data)
