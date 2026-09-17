from __future__ import annotations

import socket
import time

import pytest
from fastapi import FastAPI

from kotoba.desktop import shell
from kotoba.desktop.ui import DesktopUnavailable, require_desktop


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _health_app() -> FastAPI:
    app = FastAPI()

    @app.get("/api/health")
    def health() -> dict:
        return {"ok": True}

    return app


def test_find_port_skips_a_port_that_is_taken():
    taken = _free_port()
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as blocker:
        blocker.bind(("127.0.0.1", taken))
        found = shell.find_port(taken, "127.0.0.1")
    assert found != taken
    assert found > taken


def test_local_server_starts_answers_health_and_stops():
    port = _free_port()
    server = shell.LocalServer(_health_app(), "127.0.0.1", port)
    server.start()
    try:
        assert server.wait_healthy(timeout=10.0) is True
        assert server.url == f"http://127.0.0.1:{port}/"
    finally:
        server.stop()
    time.sleep(0.2)
    # stop() joined the server thread and released the port
    assert shell.find_port(port, "127.0.0.1") == port


class FakeWindow:
    def __init__(self) -> None:
        self.destroyed = False

    def destroy(self) -> None:
        self.destroyed = True


class FakeTray:
    def __init__(self, log: list[str]) -> None:
        self.log = log

    def start(self) -> None:
        self.log.append("tray.start")

    def stop(self) -> None:
        self.log.append("tray.stop")


class FakeUI:
    def __init__(self, log: list[str]) -> None:
        self.log = log
        self.window = FakeWindow()
        self.quit: object = None

    def create_window(self, url: str) -> FakeWindow:
        self.log.append(f"window:{url}")
        return self.window

    def create_tray(self, window: object, on_quit: object) -> FakeTray:
        self.log.append("tray.create")
        self.quit = on_quit
        return FakeTray(self.log)

    def run(self, window: object) -> None:
        self.log.append("ui.run")


class FakeServer:
    def __init__(self, app: FastAPI, host: str, port: int, log: list[str], healthy: bool = True):
        self.log = log
        self._healthy = healthy
        self.url = f"http://{host}:{port}/"

    def start(self) -> None:
        self.log.append("server.start")

    def wait_healthy(self, timeout: float) -> bool:
        self.log.append("server.wait_healthy")
        return self._healthy

    def stop(self) -> None:
        self.log.append("server.stop")


def _fake_server_factory(log: list[str], healthy: bool = True):
    def factory(app: FastAPI, host: str, port: int) -> FakeServer:
        return FakeServer(app, host, port, log, healthy=healthy)

    return factory


def test_run_starts_server_first_and_stops_everything_on_exit():
    log: list[str] = []
    assert shell.run(_health_app(), ui=FakeUI(log), server_factory=_fake_server_factory(log)) == 0
    assert log[0:2] == ["server.start", "server.wait_healthy"]
    assert log[2].startswith("window:http://127.0.0.1:")
    assert log[3:] == ["tray.create", "tray.start", "ui.run", "tray.stop", "server.stop"]


def test_tray_quit_destroys_the_window():
    log: list[str] = []
    ui = FakeUI(log)

    def run_ui(window: object) -> None:
        log.append("ui.run")
        assert callable(ui.quit)
        ui.quit()  # what the tray's "退出" item does

    ui.run = run_ui
    assert shell.run(_health_app(), ui=ui, server_factory=_fake_server_factory(log)) == 0
    assert ui.window.destroyed is True
    assert log[-2:] == ["tray.stop", "server.stop"]


def test_run_gives_up_when_the_server_never_becomes_healthy():
    log: list[str] = []
    ui = FakeUI(log)
    factory = _fake_server_factory(log, healthy=False)
    assert shell.run(_health_app(), ui=ui, server_factory=factory) == 1
    assert log == ["server.start", "server.wait_healthy", "server.stop"]
    assert ui.quit is None  # the window was never opened


def test_require_desktop_names_the_missing_extra(monkeypatch):
    monkeypatch.setattr("kotoba.desktop.ui.importlib.util.find_spec", lambda name: None)
    with pytest.raises(DesktopUnavailable) as excinfo:
        require_desktop()
    assert "uv sync --extra desktop" in str(excinfo.value)
