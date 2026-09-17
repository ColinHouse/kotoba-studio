"""The real window and tray icon, behind lazy imports (invariant 7).

Nothing here imports pywebview or pystray at module import time: `kotoba serve`
and the tests must keep working on a machine where the `desktop` extra was never
installed. `require_desktop()` is the only check, and it uses `find_spec` so it
does not import either package either.
"""

from __future__ import annotations

import contextlib
import importlib.util
import sys
import threading
from collections.abc import Callable
from typing import Any, Protocol

WINDOW_TITLE = "Kotobako · ことばこ"
INSTALL_HINT = (
    "未安装桌面组件：在 backend 目录运行 `uv sync --extra desktop`（安装 pywebview 与 pystray），"
    "或继续用 `kotoba serve` 在浏览器里使用。"
)


class DesktopUnavailable(RuntimeError):
    """The `desktop` extra is missing; the CLI prints this without a traceback."""


def require_desktop() -> None:
    missing = [name for name in ("webview", "pystray") if importlib.util.find_spec(name) is None]
    if missing:
        raise DesktopUnavailable(INSTALL_HINT)


class TrayHandle(Protocol):
    def start(self) -> None: ...

    def stop(self) -> None: ...


class DesktopUI(Protocol):
    """Everything the shell needs from the desktop. Tests substitute a fake."""

    def create_window(self, url: str) -> Any: ...

    def create_tray(self, window: Any, on_quit: Callable[[], None]) -> TrayHandle: ...

    def run(self, window: Any) -> None: ...


class PyWebviewUI:
    """A pywebview window plus a pystray icon.

    Closing the window hides it (capture keeps running) as long as the tray came
    up; with no tray to come back from, closing the window ends the app so the
    user cannot strand themselves with a running server and no window.
    """

    def __init__(self) -> None:
        self._quitting = False
        self._tray_ready = threading.Event()

    def create_window(self, url: str) -> Any:
        import webview

        window = webview.create_window(
            WINDOW_TITLE, url, width=1100, height=760, min_size=(820, 560)
        )

        def on_closing() -> bool:
            if self._quitting or not self._tray_ready.is_set():
                return True
            window.hide()
            return False

        window.events.closing += on_closing
        return window

    def create_tray(self, window: Any, on_quit: Callable[[], None]) -> TrayHandle:
        import pystray

        def show(*_args: Any) -> None:
            window.show()

        def hide(*_args: Any) -> None:
            window.hide()

        def quit_app(icon: Any, *_args: Any) -> None:
            self._quitting = True
            icon.stop()
            on_quit()

        menu = pystray.Menu(
            pystray.MenuItem("显示窗口", show, default=True),
            pystray.MenuItem("隐藏窗口", hide),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("打开数据目录", _open_data_dir),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("退出", quit_app),
        )
        return _Tray(pystray.Icon("kotobako", _icon_image(), WINDOW_TITLE, menu), self._tray_ready)

    def run(self, window: Any) -> None:
        import webview

        webview.start()


class _Tray:
    """pystray's run() blocks, so it goes on its own thread; the shell needs run() free."""

    def __init__(self, icon: Any, ready: threading.Event) -> None:
        self._icon = icon
        self._ready = ready
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        def serve() -> None:
            self._ready.set()
            self._icon.run()

        self._thread = threading.Thread(target=serve, name="kotoba-tray", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        with contextlib.suppress(Exception):
            # A tray that never came up must not block exit.
            self._icon.stop()
        if self._thread is not None:
            self._thread.join(timeout=5)


def _open_data_dir(*_args: Any) -> None:
    """Reveal the data directory in the OS file manager."""
    import subprocess
    from pathlib import Path

    from kotoba.core.config import paths

    location = Path(paths().data_dir)
    location.mkdir(parents=True, exist_ok=True)
    if sys.platform == "darwin":
        subprocess.Popen(["open", str(location)])
    elif sys.platform == "win32":
        subprocess.Popen(["explorer", str(location)])
    else:
        subprocess.Popen(["xdg-open", str(location)])


def _icon_image() -> Any:
    """The tray icon: the same mascot the installer, favicon and README use.

    It ships as package data (``kotoba/data/tray.png``) rather than being drawn
    here, so there is exactly one icon to change. The fallback only fires if a
    build dropped that file — a plain square beats a tray that will not start.
    """
    from PIL import Image, ImageDraw

    from kotoba.core.resources import TRAY_ICON_FILE

    if TRAY_ICON_FILE.exists():
        return Image.open(TRAY_ICON_FILE).convert("RGBA")

    image = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    ImageDraw.Draw(image).rounded_rectangle((4, 4, 59, 59), radius=12, fill=(182, 130, 53, 255))
    return image
