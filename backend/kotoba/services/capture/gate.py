"""One master switch for capture ingestion.

Restoring a backup disposes the database, replaces the file and builds a new
engine. Anything written in that window goes into the database that is about
to be overwritten (or keeps a connection open and makes the swap fail on
Windows). Every capture source runs its write through this gate: `pause()`
closes it and waits for the write already in flight, and while it is closed a
new ingest is skipped rather than blocking the source thread.
"""

from __future__ import annotations

import threading
from collections.abc import Iterator
from contextlib import contextmanager

from kotoba.core.errors import ApiError


class CaptureGate:
    """Pause capture writes and wait for the in-flight one, without killing sources."""

    def __init__(self) -> None:
        self._idle = threading.Condition()
        self._paused = False
        self._active = 0
        self._maintenance = False
        self._long_writers: set[str] = set()

    def pause(self) -> None:
        """Close the gate; returns once no ingest is in flight."""
        with self._idle:
            self._paused = True
            while self._active:
                self._idle.wait()

    def resume(self) -> None:
        with self._idle:
            self._paused = False
            self._idle.notify_all()

    @contextmanager
    def hold(self) -> Iterator[None]:
        """Hold the gate closed for destructive maintenance.

        Refuses outright while a long write is running rather than waiting for it:
        a JMdict import takes minutes, and blocking a restore for that long is not a
        better outcome than telling the user to try again.
        """
        with self._idle:
            if self._long_writers:
                busy = "、".join(sorted(self._long_writers))
                raise ApiError("busy", f"{busy} 正在写入数据库，请等它结束后再试")
            self._maintenance = True
        try:
            self.pause()
            yield
        finally:
            self.resume()
            with self._idle:
                self._maintenance = False

    def begin_long_write(self, name: str) -> None:
        """Claim the database for a job that writes for minutes; refuse during maintenance.

        This is the other half of `hold()`: the two must not overlap, and whichever
        starts second is the one that loses. It is a pair of plain calls rather than a
        context manager because the claim is made on the request thread — so the caller
        gets a real error — while the release happens on the worker thread that ends it.
        """
        with self._idle:
            if self._maintenance:
                raise ApiError("restoring", "正在恢复备份，请等它结束后再试")
            self._long_writers.add(name)

    def end_long_write(self, name: str) -> None:
        with self._idle:
            self._long_writers.discard(name)
            self._idle.notify_all()

    @contextmanager
    def long_write(self, name: str) -> Iterator[None]:
        """`begin_long_write` / `end_long_write` for callers that stay on one thread."""
        self.begin_long_write(name)
        try:
            yield
        finally:
            self.end_long_write(name)

    @contextmanager
    def ingest(self) -> Iterator[bool]:
        """One write: yields False when the gate is closed, else True."""
        with self._idle:
            allowed = not self._paused
            if allowed:
                self._active += 1
        try:
            yield allowed
        finally:
            if allowed:
                with self._idle:
                    self._active -= 1
                    self._idle.notify_all()


gate = CaptureGate()
