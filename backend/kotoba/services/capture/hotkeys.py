"""Global hotkeys: collect the current line without leaving the game.

The OS-level key hook comes from pynput, imported inside the functions that
need it so a headless server still boots (invariant 7). The listener only knows
how to bind, unbind and report; what a press does is injected, and a worker
thread keeps OCR off the keyboard hook so the next press is never delayed.
"""

from __future__ import annotations

import contextlib
import logging
import queue
import sys
import threading
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

from kotoba.core.config import Paths
from kotoba.core.errors import ApiError
from kotoba.models import CaptureSession
from kotoba.services import settings_store
from kotoba.services.capture import collect as collect_service
from kotoba.services.capture import windows
from kotoba.services.capture.gate import gate
from kotoba.services.capture.screen import Grab, Region, grab
from kotoba.services.capture.watcher import RegionWatcher
from kotoba.services.ocr.base import OcrProvider

log = logging.getLogger(__name__)

DEFAULT_HOTKEY = "Ctrl+Shift+S"

_MODIFIERS = {
    "ctrl": "<ctrl>",
    "control": "<ctrl>",
    "shift": "<shift>",
    "alt": "<alt>",
    "option": "<alt>",
    "cmd": "<cmd>",
    "command": "<cmd>",
    "meta": "<cmd>",
    "super": "<cmd>",
    "win": "<cmd>",
}
_NAMED_KEYS = {
    "space": "<space>",
    "enter": "<enter>",
    "return": "<enter>",
    "tab": "<tab>",
    "esc": "<esc>",
    "escape": "<esc>",
    "backspace": "<backspace>",
    "delete": "<delete>",
    "insert": "<insert>",
    "home": "<home>",
    "end": "<end>",
    "pageup": "<page_up>",
    "pagedown": "<page_down>",
    "up": "<up>",
    "down": "<down>",
    "left": "<left>",
    "right": "<right>",
} | {f"f{n}": f"<f{n}>" for n in range(1, 25)}


def normalize_hotkey(spec: str) -> str:
    """Translate "Ctrl+Shift+S" into pynput's "<ctrl>+<shift>+s".

    Raises ValueError with a readable message for anything we cannot name.
    """
    parts = [part.strip() for part in spec.split("+") if part.strip()]
    if not parts:
        raise ValueError("快捷键不能为空")
    keys: list[str] = []
    for part in parts:
        token = part.lower()
        if token in _MODIFIERS:
            keys.append(_MODIFIERS[token])
        elif token in _NAMED_KEYS:
            keys.append(_NAMED_KEYS[token])
        elif len(part) == 1 and not part.isspace():
            keys.append(token)
        else:
            raise ValueError(f"无法识别的按键：{part}")
    if len(set(keys)) != len(keys):
        raise ValueError("快捷键里有重复的按键")
    if all(key in _MODIFIERS.values() for key in keys):
        raise ValueError("快捷键至少要有一个非修饰键，例如 Ctrl+Shift+S")
    return "+".join(keys)


def available() -> tuple[bool, str | None]:
    """Whether a global hook can be built here, with a readable reason when not."""
    try:
        import pynput.keyboard  # noqa: F401
    except Exception as exc:  # noqa: BLE001 - platform backends raise all sorts
        return False, f"全局快捷键不可用：{exc}"
    note = _macos_accessibility_note()
    return True, note


def _macos_accessibility_note() -> str | None:
    """A readable hint when macOS has not granted Accessibility to this process.

    Without the permission pynput receives no key events and fails silently, so
    the status endpoint has to say it out loud instead.
    """
    if sys.platform != "darwin":
        return None
    try:
        import ctypes
        import ctypes.util

        services = ctypes.CDLL(ctypes.util.find_library("ApplicationServices"))
        trusted = services.AXIsProcessTrusted
        trusted.restype = ctypes.c_bool
        if not trusted():
            return (
                "macOS 未授予「辅助功能」权限，全局快捷键不会生效："
                "系统设置 → 隐私与安全性 → 辅助功能"
            )
    except Exception:  # noqa: BLE001 - a missing framework must not break status
        return None
    return None


ListenerFactory = Callable[[str, Callable[[], None]], Any]


def pynput_listener(spec: str, on_activate: Callable[[], None]) -> Any:
    """Build a pynput GlobalHotKeys; imported here so module load stays portable.

    On Windows a held Ctrl turns a letter into its control character before the
    hotkey matcher sees it (Ctrl+S arrives as ``'\\x13'``), so ``<ctrl>+s`` would
    never equal the event; map control characters back to their letter first.
    """
    from pynput import keyboard

    class _GlobalHotKeys(keyboard.GlobalHotKeys):
        def canonical(self, key):
            if (
                isinstance(key, keyboard.KeyCode)
                and key.char is not None
                and len(key.char) == 1
                and ord(key.char) < 32
            ):
                return keyboard.KeyCode.from_char(chr(ord(key.char) + 96))
            return super().canonical(key)

    return _GlobalHotKeys({spec: on_activate})


class HotkeyListener:
    """One global hotkey bound to one action, safe to start and stop repeatedly."""

    def __init__(
        self,
        activate: Callable[[], bool],
        *,
        factory: ListenerFactory = pynput_listener,
    ) -> None:
        self._activate = activate
        self._factory = factory
        self._listener: Any = None
        self._worker: threading.Thread | None = None
        self._queue: queue.Queue[None] = queue.Queue(maxsize=1)
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._captured = 0
        self._hotkey: str | None = None
        self.last_error: str | None = None
        self.last_captured_at: datetime | None = None

    @property
    def running(self) -> bool:
        return self._listener is not None and self._listener.running

    @property
    def hotkey(self) -> str | None:
        return self._hotkey

    @property
    def captured(self) -> int:
        return self._captured

    def start(self, hotkey: str = DEFAULT_HOTKEY) -> bool:
        """Bind and listen; returns False when already running or the hook fails."""
        try:
            spec = normalize_hotkey(hotkey)
        except ValueError as exc:
            self.last_error = str(exc)
            return False
        if self._listener is not None and not self.running:
            self.stop()  # the hook thread died; drop it before binding a new one
        with self._lock:
            if self.running:
                return False
            try:
                listener = self._factory(spec, self._on_hotkey)
                listener.start()
            except Exception as exc:  # noqa: BLE001 - keep the reason for the UI
                self.last_error = f"全局快捷键启动失败：{exc}"
                log.warning("global hotkey listener failed", exc_info=True)
                return False
            self._hotkey = hotkey
            self.last_error = available()[1]
            self._stop.clear()
            self._listener = listener
            self._worker = threading.Thread(target=self._work, name="hotkey-worker", daemon=True)
            self._worker.start()
            return True

    def stop(self, timeout: float = 2.0) -> None:
        """Release the hook and wait for the worker; never leaves either behind."""
        with self._lock:
            listener, worker = self._listener, self._worker
            self._listener = None
            self._worker = None
        if listener is None:
            return
        self._stop.set()
        try:
            listener.stop()
        except Exception:  # noqa: BLE001 - a dead hook must not block shutdown
            log.debug("global hotkey listener stop failed", exc_info=True)
        if worker is not None:
            worker.join(timeout)

    def status(self) -> dict:
        return {
            "running": self.running,
            "hotkey": self._hotkey,
            "captured": self._captured,
            "last_error": self.last_error,
            "last_captured_at": (
                self.last_captured_at.isoformat() if self.last_captured_at else None
            ),
        }

    def _on_hotkey(self) -> None:
        """Runs on the hook thread: hand off at once, never do OCR here."""
        # A full queue means the previous press is still being handled, so this one
        # is already represented and dropping it is the intended behaviour.
        with contextlib.suppress(queue.Full):
            self._queue.put_nowait(None)

    def _work(self) -> None:
        while not self._stop.is_set():
            try:
                self._queue.get(timeout=0.2)
            except queue.Empty:
                continue
            try:
                captured = self._activate()
            except ApiError as exc:
                self.last_error = exc.message
                log.debug("global hotkey capture skipped: %s", exc.message)
            except Exception as exc:  # noqa: BLE001 - report, never kill the worker
                self.last_error = str(exc)
                log.warning("global hotkey capture failed", exc_info=True)
            else:
                self.last_error = None
                if captured:
                    self._captured += 1
                    self.last_captured_at = datetime.now(UTC)


def make_collector(
    session_factory: Callable[[], Session],
    paths: Paths,
    provider_for: Callable[[Session], OcrProvider],
    watcher_for: Callable[[], RegionWatcher | None],
    *,
    grabber: Callable[[Region], Grab] = grab,
) -> Callable[[], bool]:
    """The hotkey action: screenshot the active region, OCR it, store the line.

    The region is the running watcher's, else the active source's -- resolved
    through its bound window, so the hotkey still finds the dialogue box after
    the game window moved. A source with nothing saved yields a readable error
    instead of a silent miss.
    """

    def collect_current() -> bool:
        with gate.ingest() as allowed:
            if not allowed:
                raise ApiError("capture_paused", "正在恢复备份，采集已暂停")
            watcher = watcher_for()
            db = session_factory()
            try:
                session_id = settings_store.get(db, "active_session_id")
                source_id = _source_of(db, session_id)
                region = watcher.region if watcher is not None and watcher.running else None
                if region is None and source_id is not None:
                    region = windows.resolve_region(db, source_id)
                if region is None:
                    raise ApiError(
                        "no_region", "还没有对话区域：先在采集页框选一次，快捷键只认已保存的区域"
                    )
                window = (
                    windows.window_for_source(db, source_id)
                    if source_id is not None and windows.available()
                    else None
                )
                payload = collect_service.collect(
                    db,
                    paths,
                    session_id,
                    region,
                    provider_for(db),
                    grabber=grabber,
                    source_id=source_id,
                    window=window,
                )
                return payload["line"] is not None
            finally:
                db.close()

    return collect_current


def _source_of(db: Session, session_id: int | None) -> int | None:
    if session_id is None:
        return None
    session = db.get(CaptureSession, session_id)
    return session.source_id if session is not None else None
