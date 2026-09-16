"""Watch a screen region and turn settled frames into lines.

The loop grabs the region, hashes the frame and only runs OCR when the picture
has changed and stopped moving; a typewriter effect would otherwise yield one
partial line per frame. Grabbing and OCR are injected so tests never touch a
real screen.
"""

from __future__ import annotations

import io
import logging
import threading
from collections.abc import Callable

from PIL import Image
from sqlalchemy.orm import Session

from kotoba.core.errors import ApiError
from kotoba.schemas import LineCreate
from kotoba.services import settings_store
from kotoba.services.capture.buffer import MediaBuffer
from kotoba.services.capture.framehash import StabilityTracker, dhash
from kotoba.services.capture.gate import gate
from kotoba.services.capture.screen import Grab, Region, grab
from kotoba.services.jp.normalize import normalize_ocr
from kotoba.services.ocr.base import OcrProvider
from kotoba.services.text.ingest import create_line

log = logging.getLogger(__name__)

DEFAULT_INTERVAL = 0.4


class RegionWatcher:
    """Grab a region on a background thread; OCR once per changed-and-settled frame."""

    def __init__(
        self,
        region: Region,
        session_factory: Callable[[], Session],
        provider: OcrProvider,
        *,
        grabber: Callable[[Region], Grab] = grab,
        interval: float = DEFAULT_INTERVAL,
        source_id: int | None = None,
        buffer: MediaBuffer | None = None,
    ) -> None:
        self.region = region
        self.source_id = source_id
        self._session_factory = session_factory
        self._provider = provider
        self._grabber = grabber
        self._interval = interval
        self._buffer = buffer
        self._tracker = StabilityTracker()
        self._stop = threading.Event()
        self._lock = threading.Lock()
        self._thread: threading.Thread | None = None
        self._captured = 0
        self.last_error: str | None = None

    @property
    def running(self) -> bool:
        thread = self._thread
        return thread is not None and thread.is_alive()

    @property
    def captured(self) -> int:
        return self._captured

    def start(self) -> bool:
        """Start watching; returns False when it was already running."""
        with self._lock:
            if self.running:
                return False
            self._stop.clear()
            self._thread = threading.Thread(target=self._run, name="region-watcher", daemon=True)
            self._thread.start()
            return True

    def stop(self, timeout: float = 2.0) -> None:
        """Signal the loop and wait for the thread; never leaves it behind.

        Stopping also releases the media buffer: a few hundred MB must not sit
        in memory for a watcher nobody is running.
        """
        thread = self._thread
        if thread is None:
            return
        self._stop.set()
        thread.join(timeout)
        if not thread.is_alive():
            self._thread = None
        if self._buffer is not None:
            self._buffer.clear()

    def _run(self) -> None:
        while not self._stop.wait(self._interval):
            try:
                png = self._grabber(self.region).png
                if self._buffer is not None:
                    self._buffer.add_frame(png)
                image = Image.open(io.BytesIO(png))
                if self._tracker.update(dhash(image)):
                    self._recognize(png)
            except ApiError as exc:
                self.last_error = exc.message
                log.debug("region watcher skipped a frame: %s", exc.message)
            except Exception as exc:  # noqa: BLE001
                self.last_error = str(exc)
                log.debug("region watcher failed a frame", exc_info=True)

    def _recognize(self, png: bytes) -> None:
        result = self._provider.recognize(png)
        # Only a successful OCR clears the error: clearing it on the next quiet
        # frame would hide a failed engine from /watch/status almost at once.
        self.last_error = None
        text = normalize_ocr(result.text)
        if not text:
            return
        with gate.ingest() as allowed:
            if not allowed:
                return
            db = self._session_factory()
            try:
                session_id = settings_store.get(db, "active_session_id")
                _, duplicate = create_line(
                    db,
                    LineCreate(
                        session_id=session_id,
                        source_id=self.source_id,
                        text=text,
                        raw_text=result.text,
                        origin="ocr",
                        position={"region": self.region.to_dict()},
                    ),
                )
            finally:
                db.close()
            if not duplicate:
                self._captured += 1
