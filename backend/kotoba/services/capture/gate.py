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


class CaptureGate:
    """Pause capture writes and wait for the in-flight one, without killing sources."""

    def __init__(self) -> None:
        self._idle = threading.Condition()
        self._paused = False
        self._active = 0

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
        """Hold the gate closed for a block, and always open it again."""
        self.pause()
        try:
            yield
        finally:
            self.resume()

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
