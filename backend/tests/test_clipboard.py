import threading
import time

from kotoba.services.capture.clipboard import (
    MAX_CLIPBOARD_CHARS,
    ClipboardWatcher,
    looks_like_line,
)


class FakeClipboard:
    """Scripted clipboard reads; once the script is exhausted it stays empty."""

    def __init__(self, *texts: str) -> None:
        self._texts = list(texts)

    def __call__(self) -> str:
        return self._texts.pop(0) if self._texts else ""


def wait_for(predicate, timeout: float = 5.0) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return True
        time.sleep(0.01)
    return predicate()


def watcher_threads() -> int:
    return sum(t.name == "clipboard-watcher" for t in threading.enumerate())


def test_looks_like_line():
    assert looks_like_line("今日はいい天気だね")
    assert looks_like_line("カタカナだけ")
    assert looks_like_line("ｶﾞｰﾙ")  # half-width katakana still counts
    assert looks_like_line("hello 世界")
    assert not looks_like_line("")
    assert not looks_like_line("  \n  ")
    assert not looks_like_line("hello world")
    assert not looks_like_line("あ" * (MAX_CLIPBOARD_CHARS + 1))
    assert looks_like_line("あ" * MAX_CLIPBOARD_CHARS)


def test_watch_captures_new_lines_and_filters_the_rest(client):
    src = client.post("/api/sources", json={"title": "作品"}).json()
    ses = client.post("/api/sessions", json={"source_id": src["id"]}).json()
    client.put("/api/settings", json={"active_session_id": ses["id"]})

    watcher = ClipboardWatcher(
        client.app.state.db.session,
        read=FakeClipboard(
            "hello world",  # no kana or kanji
            "今日はいい天気だね",  # captured
            "今日はいい天気だね",  # same as the previous read
            "あ" * (MAX_CLIPBOARD_CHARS + 1),  # too long
            "ありがとう",  # captured
        ),
        interval=0.01,
    )
    client.app.state.clipboard_watcher = watcher

    assert client.post("/api/capture/clipboard/start").json() == {
        "running": True,
        "captured": 0,
    }
    assert wait_for(lambda: watcher.captured == 2)
    assert client.get("/api/capture/clipboard/status").json() == {
        "running": True,
        "captured": 2,
    }

    assert client.post("/api/capture/clipboard/stop").json() == {
        "running": False,
        "captured": 2,
    }
    assert watcher_threads() == 0

    lines = client.get("/api/lines", params={"session_id": ses["id"]}).json()
    assert {line["text"] for line in lines} == {"今日はいい天気だね", "ありがとう"}
    assert all(line["origin"] == "hook" for line in lines)


def test_start_is_idempotent(client):
    watcher = ClipboardWatcher(client.app.state.db.session, read=lambda: "", interval=30.0)
    client.app.state.clipboard_watcher = watcher

    assert client.post("/api/capture/clipboard/start").json()["running"] is True
    assert client.post("/api/capture/clipboard/start").json()["running"] is True
    assert watcher_threads() == 1

    client.post("/api/capture/clipboard/stop")


def test_stop_interrupts_the_poll_and_joins_the_thread(client):
    watcher = ClipboardWatcher(client.app.state.db.session, read=lambda: "", interval=30.0)
    client.app.state.clipboard_watcher = watcher

    client.post("/api/capture/clipboard/start")
    assert watcher.running is True

    began = time.monotonic()
    assert client.post("/api/capture/clipboard/stop").json() == {
        "running": False,
        "captured": 0,
    }
    assert time.monotonic() - began < 1.0  # did not wait out the 30 s interval

    assert not any(t.name == "clipboard-watcher" for t in threading.enumerate())
