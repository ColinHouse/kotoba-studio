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
            "hello world",
            "今日はいい天気だね",
            "今日はいい天気だね",
            "あ" * (MAX_CLIPBOARD_CHARS + 1),
            "ありがとう",
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
    assert time.monotonic() - began < 1.0

    assert not any(t.name == "clipboard-watcher" for t in threading.enumerate())


def test_ingest_survives_an_unexpected_database_error(client):
    """A transient failure costs one line, not the whole watcher thread."""
    calls = {"n": 0}

    def failing_factory():
        calls["n"] += 1
        if calls["n"] == 1:
            raise RuntimeError("database is locked")
        return client.app.state.db.session()

    watcher = ClipboardWatcher(failing_factory, read=lambda: "", interval=0.01)
    assert watcher._ingest("最初の台詞") is False
    assert watcher._ingest("次の台詞") is True


def test_watcher_follows_the_database_across_a_restore(client):
    """app.state.db is replaced by restore; the watcher must not hold the old one."""
    watcher = client.app.state.clipboard_watcher
    first = client.app.state.db
    client.post("/api/backups", json={"name": "before"})
    client.post("/api/backups/restore", json={"name": "before"})
    assert client.app.state.db is not first
    session = watcher._session_factory()
    try:
        assert session.get_bind() is client.app.state.db.engine
    finally:
        session.close()


def test_stop_keeps_a_watcher_that_a_concurrent_start_installed():
    """stop() must not orphan a thread that started while it was joining."""
    watcher = ClipboardWatcher(lambda: None, read=lambda: "", interval=0.01)
    watcher._thread = threading.Thread(target=lambda: None, name="clipboard-watcher")
    watcher._thread.start()
    watcher._thread.join()
    watcher._thread = threading.Thread(target=lambda: time.sleep(0.2), name="clipboard-watcher")
    watcher._thread.start()
    live = watcher._thread
    watcher.stop(timeout=0.01)
    assert watcher._thread is live, "stop() dropped the handle of a different thread"
    live.join()


def test_lifespan_constructs_clipboard_watcher_once(data_dir, monkeypatch):
    """A duplicate assignment would leak a watcher thread if start() is later wired in."""
    from fastapi.testclient import TestClient

    from kotoba.app import create_app
    from kotoba.services.capture.clipboard import ClipboardWatcher

    calls = {"n": 0}
    original = ClipboardWatcher

    def counting(*args, **kwargs):
        calls["n"] += 1
        return original(*args, **kwargs)

    monkeypatch.setattr("kotoba.app.ClipboardWatcher", counting)
    with TestClient(create_app()) as client:
        assert calls["n"] == 1
        assert isinstance(client.app.state.clipboard_watcher, original)
