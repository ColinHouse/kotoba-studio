"""Desktop shell orchestration: pick a port, start the server, wait, then show the window.

The app runs in this process (ADR-free decision: one process owns the database),
so quitting the shell runs uvicorn's lifespan shutdown — the same path `kotoba
serve` takes — which stops watchers, hooks, the clipboard and disposes the DB.
There is no child process to orphan.
"""

from __future__ import annotations

import socket
import sys
import threading
import time
from collections.abc import Callable
from urllib.error import URLError
from urllib.request import urlopen

import uvicorn
from fastapi import FastAPI

from kotoba.desktop.ui import DesktopUI, PyWebviewUI, require_desktop

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8720
PORT_ATTEMPTS = 10
HEALTH_TIMEOUT = 15.0
LAST_PORT = 65535


def find_port(preferred: int, host: str = DEFAULT_HOST, attempts: int = PORT_ATTEMPTS) -> int:
    """First bindable port at or after `preferred`, so a second launch still works."""
    for port in range(preferred, min(preferred + attempts, LAST_PORT + 1)):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
            try:
                probe.bind((host, port))
            except OSError:
                continue
        return port
    raise OSError(f"{host} 上 {preferred} 之后的 {attempts} 个端口都被占用")


class LocalServer:
    """The API + web app on a background thread; `stop()` runs the app's lifespan."""

    def __init__(self, app: FastAPI, host: str = DEFAULT_HOST, port: int = DEFAULT_PORT) -> None:
        self.host = host
        self.port = port
        self._server = uvicorn.Server(uvicorn.Config(app, host=host, port=port, log_level="info"))
        self._thread = threading.Thread(target=self._server.run, name="kotoba-server", daemon=True)

    def start(self) -> None:
        self._thread.start()

    @property
    def http_host(self) -> str:
        # 0.0.0.0 is a bind address, not a destination the window can open.
        return "127.0.0.1" if self.host in ("0.0.0.0", "::", "") else self.host

    @property
    def url(self) -> str:
        return f"http://{self.http_host}:{self.port}/"

    def wait_healthy(self, timeout: float = HEALTH_TIMEOUT) -> bool:
        """Poll /api/health; False when the deadline passes or the server gave up."""
        deadline = time.monotonic() + timeout
        probe = f"http://{self.http_host}:{self.port}/api/health"
        while time.monotonic() < deadline:
            if self._server.should_exit:
                return False
            try:
                with urlopen(probe, timeout=0.5) as response:  # noqa: S310 - loopback only
                    if response.status == 200:
                        return True
            except (URLError, OSError):
                time.sleep(0.1)
        return False

    def stop(self, timeout: float = 10.0) -> None:
        self._server.should_exit = True
        self._thread.join(timeout)


def run(
    app: FastAPI,
    *,
    host: str = DEFAULT_HOST,
    port: int = DEFAULT_PORT,
    ui: DesktopUI | None = None,
    server_factory: Callable[[FastAPI, str, int], LocalServer] = LocalServer,
    health_timeout: float = HEALTH_TIMEOUT,
) -> int:
    """Start the server, wait for health, then hand the window to the UI. Returns an exit code."""
    if ui is None:
        require_desktop()
        ui = PyWebviewUI()
    chosen = find_port(port, host)
    server = server_factory(app, host, chosen)
    server.start()
    if not server.wait_healthy(health_timeout):
        server.stop()
        print("后端没有在预期时间内就绪，桌面壳退出。", file=sys.stderr)
        return 1
    window = ui.create_window(server.url)
    quitting = threading.Event()

    def request_quit() -> None:
        quitting.set()
        window.destroy()

    tray = ui.create_tray(window, request_quit)
    try:
        tray.start()
        ui.run(window)
    finally:
        tray.stop()
        server.stop()
    return 0


def run_cli(data_dir: str | None, port: int | None, host: str | None = None) -> int:
    """Entry point used by `kotoba desktop`: build the app from settings and run."""
    import os

    from kotoba.app import create_app
    from kotoba.core.config import get_settings
    from kotoba.desktop.ui import DesktopUnavailable

    if data_dir:
        os.environ["KOTOBA_DATA_DIR"] = data_dir
    if port:
        os.environ["KOTOBA_PORT"] = str(port)
    get_settings.cache_clear()
    settings = get_settings()
    try:
        return run(
            create_app(settings),
            host=host or settings.host,
            port=settings.port,
        )
    except DesktopUnavailable as exc:
        print(str(exc), file=sys.stderr)
        return 2
