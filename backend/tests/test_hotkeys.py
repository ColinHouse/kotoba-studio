import io
import threading
import time

import pytest
from PIL import Image

from kotoba.core.errors import ApiError
from kotoba.services.capture.gate import gate
from kotoba.services.capture.hotkeys import (
    HotkeyListener,
    make_collector,
    normalize_hotkey,
    pynput_listener,
)
from kotoba.services.capture.screen import Grab, Region
from kotoba.services.ocr.base import OcrBlock, OcrResult


def _wait_for(predicate, timeout=2.0):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return True
        time.sleep(0.01)
    return predicate()


class FakeProvider:
    name = "fake"

    def __init__(self, text="今日は俺が奢ってやるよ。"):
        self.text = text
        self.calls = 0

    def available(self):
        return True

    def recognize(self, png):
        self.calls += 1
        return OcrResult(self.text, [OcrBlock(self.text, 0.9, (0.1, 0.1, 0.5, 0.2))], "fake", 1)


def fake_grab(region: Region) -> Grab:
    buf = io.BytesIO()
    Image.new("RGB", (region.width, region.height), (20, 20, 30)).save(buf, format="PNG")
    return Grab(png=buf.getvalue(), width=region.width, height=region.height, scale=1.0)


class FakeHook:
    def __init__(self, spec, callback, *, fail=False):
        self.spec = spec
        self.callback = callback
        self.fail = fail
        self.started = False
        self.stopped = False

    def start(self):
        if self.fail:
            raise RuntimeError("hook 不可用")
        self.started = True

    def stop(self):
        self.stopped = True

    @property
    def running(self):
        return self.started and not self.stopped

    def die(self):
        self.started = False

    def fire(self):
        self.callback()


class FakeFactory:
    def __init__(self, *, fail=False):
        self.hooks: list[FakeHook] = []
        self.fail = fail

    def __call__(self, spec, callback):
        hook = FakeHook(spec, callback, fail=self.fail)
        self.hooks.append(hook)
        return hook


def test_normalize_hotkey_translates_and_validates():
    assert normalize_hotkey("Ctrl+Shift+S") == "<ctrl>+<shift>+s"
    assert normalize_hotkey("control+alt+s") == "<ctrl>+<alt>+s"
    assert normalize_hotkey("Ctrl+F5") == "<ctrl>+<f5>"
    assert normalize_hotkey("Space") == "<space>"
    with pytest.raises(ValueError, match="无法识别"):
        normalize_hotkey("Ctrl+Oops")
    with pytest.raises(ValueError, match="非修饰键"):
        normalize_hotkey("Ctrl+Shift")
    with pytest.raises(ValueError, match="不能为空"):
        normalize_hotkey("  ")
    with pytest.raises(ValueError, match="重复"):
        normalize_hotkey("Ctrl+Ctrl+S")


def test_windows_control_character_still_matches_the_hotkey():
    try:
        import pynput.keyboard as keyboard
    except ImportError:  # a platform without a keyboard backend (headless Linux CI)
        pytest.skip("pynput has no keyboard backend here")
    fired = threading.Event()
    listener = pynput_listener("<ctrl>+<shift>+s", fired.set)

    # A real Windows Ctrl+S press arrives as DC3, not as "s".
    for key in (keyboard.Key.ctrl_l, keyboard.Key.shift, keyboard.KeyCode.from_char("\x13")):
        for hotkey in listener._hotkeys:
            hotkey.press(listener.canonical(key))
    assert fired.is_set()


def test_listener_starts_and_fires_the_action():
    fired = threading.Event()
    factory = FakeFactory()
    listener = HotkeyListener(lambda: fired.set() or True, factory=factory)

    assert listener.start("Ctrl+Shift+S") is True
    assert listener.running is True
    assert listener.hotkey == "Ctrl+Shift+S"
    assert factory.hooks[0].spec == "<ctrl>+<shift>+s"
    assert factory.hooks[0].started is True
    assert listener.start() is False  # already running

    factory.hooks[0].fire()
    assert fired.wait(2.0)
    assert _wait_for(lambda: listener.captured == 1)
    assert listener.last_error is None
    assert listener.status()["last_captured_at"] is not None

    listener.stop()
    assert listener.running is False
    assert factory.hooks[0].stopped is True


def test_listener_reports_failures_instead_of_dying():
    factory = FakeFactory(fail=True)
    listener = HotkeyListener(lambda: True, factory=factory)
    assert listener.start() is False
    assert listener.running is False
    assert "全局快捷键启动失败" in listener.last_error

    bad_spec = HotkeyListener(lambda: True, factory=FakeFactory())
    assert bad_spec.start("Ctrl+Shift") is False
    assert "非修饰键" in bad_spec.last_error

    called = threading.Event()

    def failing() -> bool:
        called.set()
        raise ApiError("ocr_failed", "识别失败了")

    listener = HotkeyListener(failing, factory=FakeFactory())
    listener.start()
    listener._on_hotkey()
    assert called.wait(2.0)
    assert _wait_for(lambda: listener.last_error == "识别失败了")
    assert listener.captured == 0
    assert listener.running is True
    listener.stop()


def test_listener_reports_a_dead_hook_and_rebinds():
    factory = FakeFactory()
    listener = HotkeyListener(lambda: True, factory=factory)
    assert listener.start("Ctrl+Shift+S") is True

    factory.hooks[0].die()
    assert listener.running is False

    assert listener.start("Ctrl+Shift+S") is True
    assert len(factory.hooks) == 2
    assert factory.hooks[0].stopped is True
    assert factory.hooks[1].running is True
    listener.stop()


def test_listener_keeps_one_press_queued_while_busy():
    first_running = threading.Event()
    release = threading.Event()
    calls = 0

    def blocking() -> bool:
        nonlocal calls
        calls += 1
        first_running.set()
        release.wait(2.0)
        return True

    listener = HotkeyListener(blocking, factory=FakeFactory())
    listener.start()
    listener._on_hotkey()
    assert first_running.wait(2.0)
    listener._on_hotkey()  # queued
    listener._on_hotkey()  # dropped: the queue is full
    release.set()
    assert _wait_for(lambda: listener.captured == 2)
    assert calls == 2
    listener.stop()


def _collector(client, provider: FakeProvider | None = None):
    return make_collector(
        lambda: client.app.state.db.session(),
        client.app.state.paths,
        lambda db: provider or FakeProvider(),
        lambda: None,
        grabber=fake_grab,
    )


def _active_session(client, region: dict | None) -> dict:
    payload = {"title": "作品"}
    if region is not None:
        payload["region"] = region
    src = client.post("/api/sources", json=payload).json()
    ses = client.post("/api/sessions", json={"source_id": src["id"]}).json()
    client.put("/api/settings", json={"active_session_id": ses["id"]})
    return ses


def test_collector_uses_the_saved_region_and_stores_a_line(client):
    ses = _active_session(client, {"left": 10, "top": 20, "width": 300, "height": 80})
    provider = FakeProvider()
    collector = _collector(client, provider)

    assert collector() is True
    lines = client.get("/api/lines", params={"session_id": ses["id"]}).json()
    assert len(lines) == 1
    assert lines[0]["text"] == "今日は俺が奢ってやるよ。"
    assert lines[0]["origin"] == "ocr"
    assert lines[0]["screenshot_path"]
    assert lines[0]["position"]["region"]["width"] == 300
    assert provider.calls == 1


def test_collector_needs_a_region_and_respects_the_gate(client):
    _active_session(client, None)
    collector = _collector(client)
    with pytest.raises(ApiError) as exc:
        collector()
    assert exc.value.code == "no_region"

    _active_session(client, {"left": 0, "top": 0, "width": 120, "height": 40})
    with gate.hold(), pytest.raises(ApiError) as exc:
        collector()
    assert exc.value.code == "capture_paused"


def test_hotkey_endpoints_start_restart_and_stop(client):
    factory = FakeFactory()
    client.app.state.hotkey_listener = HotkeyListener(lambda: True, factory=factory)

    status = client.get("/api/capture/hotkeys/status").json()
    assert status["running"] is False
    assert "available" in status and "note" in status

    started = client.post("/api/capture/hotkeys/start").json()
    assert started["running"] is True
    assert started["hotkey"] == "Ctrl+Shift+S"
    assert factory.hooks[0].spec == "<ctrl>+<shift>+s"

    client.put("/api/settings", json={"capture_hotkey": "Ctrl+Alt+K"})
    restarted = client.post("/api/capture/hotkeys/start").json()
    assert restarted["hotkey"] == "Ctrl+Alt+K"
    assert len(factory.hooks) == 2
    assert factory.hooks[0].stopped is True
    assert factory.hooks[1].spec == "<ctrl>+<alt>+k"

    stopped = client.post("/api/capture/hotkeys/stop").json()
    assert stopped["running"] is False


def test_settings_reject_an_unusable_hotkey(client):
    r = client.put("/api/settings", json={"capture_hotkey": "Ctrl+Oops"})
    assert r.status_code == 400
    assert r.json()["error"]["code"] == "invalid_value"
    assert client.get("/api/settings").json()["capture_hotkey"] == "Ctrl+Shift+S"
