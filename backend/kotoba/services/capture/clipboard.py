"""Watch the OS clipboard and ingest new game lines.

Polling is deliberate: most Galgame text hookers write to the clipboard, and a
poll is the only interface that speaks to all of them.
"""

from __future__ import annotations

import logging
import threading
from collections.abc import Callable

from sqlalchemy.orm import Session

from kotoba.core.errors import ApiError
from kotoba.schemas import LineCreate
from kotoba.services import settings_store
from kotoba.services.jp import kana
from kotoba.services.jp.normalize import normalize_ocr
from kotoba.services.text.ingest import create_line

log = logging.getLogger(__name__)

DEFAULT_INTERVAL = 0.3
MAX_CLIPBOARD_CHARS = 200


def read_clipboard() -> str:
    """Read the OS clipboard; "" when the platform has no clipboard mechanism."""
    import pyperclip

    try:
        return pyperclip.paste() or ""
    except pyperclip.PyperclipException:
        return ""


def looks_like_line(text: str) -> bool:
    """A copied game line is short and contains kana or kanji; other copies are not."""
    text = normalize_ocr(text)
    if not text or len(text) > MAX_CLIPBOARD_CHARS:
        return False
    return any(kana.is_kana(ch) or kana.is_kanji(ch) for ch in text)


class ClipboardWatcher:
    """Poll the clipboard on a background thread and create lines from new text."""

    def __init__(
        self,
        session_factory: Callable[[], Session],
        read: Callable[[], str] = read_clipboard,
        interval: float = DEFAULT_INTERVAL,
    ) -> None:
        self._session_factory = session_factory
        self._read = read
        self._interval = interval
        self._stop = threading.Event()
        self._lock = threading.Lock()
        self._thread: threading.Thread | None = None
        self._captured = 0

    @property
    def running(self) -> bool:
        thread = self._thread
        return thread is not None and thread.is_alive()

    @property
    def captured(self) -> int:
        return self._captured

    def start(self) -> bool:
        """Start polling; returns False when it was already running."""
        with self._lock:
            if self.running:
                return False
            self._stop.clear()
            self._thread = threading.Thread(target=self._run, name="clipboard-watcher", daemon=True)
            self._thread.start()
            return True

    def stop(self, timeout: float = 2.0) -> None:
        """Signal the loop and wait for the thread; the waiter can never outlive this."""
        thread = self._thread
        if thread is None:
            return
        self._stop.set()
        thread.join(timeout)
        if not thread.is_alive():
            self._thread = None

    def _run(self) -> None:
        last: str | None = None
        while not self._stop.wait(self._interval):
            text = normalize_ocr(self._read() or "")
            if text == last:
                continue
            last = text
            if looks_like_line(text) and self._ingest(text):
                self._captured += 1

    def _ingest(self, text: str) -> bool:
        db = self._session_factory()
        try:
            session_id = settings_store.get(db, "active_session_id")
            _, duplicate = create_line(
                db, LineCreate(session_id=session_id, text=text, origin="hook")
            )
            return not duplicate
        except ApiError as exc:
            log.debug("clipboard text skipped: %s", exc.message)
            return False
        finally:
            db.close()
