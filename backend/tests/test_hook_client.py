import asyncio
import contextlib
import logging
import socket
import threading
import time

from websockets.sync.server import serve

from kotoba.services.capture.hook_client import HookClient


def wait_for(predicate, timeout: float = 5.0) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return True
        time.sleep(0.01)
    return predicate()


def hooks(client) -> dict[str, dict]:
    return {hook["name"]: hook for hook in client.get("/api/capture/hooks").json()}


def line_texts(client, session_id: int) -> set[str]:
    return {
        line["text"] for line in client.get("/api/lines", params={"session_id": session_id}).json()
    }


def run_server(handler):
    server = serve(handler, "127.0.0.1", 0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, thread, server.socket.getsockname()[1]


def unused_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def failing_connector(attempts: list[str]):
    @contextlib.asynccontextmanager
    async def connect(url):
        attempts.append(url)
        raise OSError("connection refused")
        yield

    return connect


def test_presets_are_listed(client):
    listed = hooks(client)
    assert listed["textractor"]["url"] == "ws://127.0.0.1:6677"
    assert listed["agent"]["url"] == "ws://127.0.0.1:9001"
    assert listed["luna"]["url"] == "ws://127.0.0.1:2333"
    assert all(hook["connected"] is False for hook in listed.values())
    assert all(hook["status"] == "idle" for hook in listed.values())
    assert all(hook["last_text"] is None for hook in listed.values())
    assert all(hook["last_text_at"] is None for hook in listed.values())


def test_unknown_target_needs_a_url(client):
    r = client.post("/api/capture/hooks/nope/connect")
    assert r.status_code == 400
    assert r.json()["error"]["code"] == "unknown_hook"
    assert client.post("/api/capture/hooks/nope/disconnect").status_code == 404
    assert client.post("/api/capture/hooks/nope/probe").status_code == 400


def test_hook_client_ingests_text_then_reconnects(client):
    src = client.post("/api/sources", json={"title": "作品"}).json()
    ses = client.post("/api/sessions", json={"source_id": src["id"]}).json()
    client.put("/api/settings", json={"active_session_id": ses["id"]})

    holding = threading.Event()

    def handler(ws):
        ws.send("今日は俺が奢ってやるよ。")
        ws.send('{"text": "本当に？", "speaker": "太郎"}')
        holding.wait(5)

    server, thread, port = run_server(handler)
    try:
        r = client.post("/api/capture/hooks/test/connect", json={"url": f"ws://127.0.0.1:{port}"})
        assert r.status_code == 200
        assert wait_for(lambda: len(line_texts(client, ses["id"])) == 2)
        live = hooks(client)["test"]
        assert live["connected"] is True
        assert live["status"] == "connected"
        assert live["last_text_at"] is not None
        assert live["last_text"] == "本当に？"
        assert line_texts(client, ses["id"]) == {"今日は俺が奢ってやるよ。", "本当に？"}
        lines = client.get("/api/lines", params={"session_id": ses["id"]}).json()
        assert {line["origin"] for line in lines} == {"hook"}
    finally:
        holding.set()
        server.shutdown()
        thread.join(timeout=2)

    # The tool is gone: the client must go back to retrying, not die.
    assert wait_for(lambda: hooks(client)["test"]["connected"] is False)
    assert wait_for(lambda: hooks(client)["test"]["error"] is not None)
    assert client.app.state.hook_manager.get("test").running is True
    assert hooks(client)["test"]["status"] == "connecting"

    stopped = client.post("/api/capture/hooks/test/disconnect").json()
    assert stopped["connected"] is False
    assert stopped["status"] == "idle"


def test_probe_answers_immediately_without_starting_a_client(client):
    def handler(ws):
        pass

    server, thread, port = run_server(handler)
    try:
        live = client.post(
            "/api/capture/hooks/textractor/probe", json={"url": f"ws://127.0.0.1:{port}"}
        )
        assert live.status_code == 200
        assert live.json() == {"ok": True, "error": None}
    finally:
        server.shutdown()
        thread.join(timeout=2)

    dead = client.post(
        "/api/capture/hooks/textractor/probe", json={"url": f"ws://127.0.0.1:{unused_port()}"}
    )
    assert dead.status_code == 200
    assert dead.json()["ok"] is False
    assert dead.json()["error"]

    # Probing is not connecting: nothing was left behind for the retry loop.
    assert hooks(client)["textractor"]["status"] == "idle"
    assert client.app.state.hook_manager.get("textractor") is None


def test_probe_reuses_the_configured_url(client):
    def handler(ws):
        pass

    server, thread, port = run_server(handler)
    try:
        client.post("/api/capture/hooks/textractor/connect", json={"url": f"ws://127.0.0.1:{port}"})
        # No body: the probe must test the configured address, not the preset.
        probed = client.post("/api/capture/hooks/textractor/probe")
        assert probed.json() == {"ok": True, "error": None}
    finally:
        client.post("/api/capture/hooks/textractor/disconnect")
        server.shutdown()
        thread.join(timeout=2)


def test_connect_failures_are_debug_logged(client, caplog):
    logger_name = "kotoba.services.capture.hook_client"
    with caplog.at_level(logging.DEBUG, logger=logger_name):
        client.post(
            "/api/capture/hooks/dead/connect",
            json={"url": f"ws://127.0.0.1:{unused_port()}"},
        )
        assert wait_for(lambda: hooks(client)["dead"]["error"] is not None)
        client.post("/api/capture/hooks/dead/disconnect")

    records = [r for r in caplog.records if r.name == logger_name]
    assert any(r.levelno == logging.DEBUG for r in records)
    assert not any(r.levelno >= logging.WARNING for r in records)


def test_client_retries_and_stop_interrupts_a_long_backoff():
    async def retry_scenario():
        attempts: list[str] = []
        client = HookClient(
            "ws://127.0.0.1:1",
            on_text=lambda raw: None,
            connect=failing_connector(attempts),
            initial_backoff=0.01,
            max_backoff=0.02,
        )
        client.start()
        await asyncio.sleep(0.2)
        assert client.connected is False
        assert client.error is not None
        assert len(attempts) >= 3
        assert client.running is True
        await client.stop()
        assert client.running is False

    async def stop_scenario():
        attempts: list[str] = []
        client = HookClient(
            "ws://127.0.0.1:1",
            on_text=lambda raw: None,
            connect=failing_connector(attempts),
            initial_backoff=30.0,
        )
        client.start()
        await asyncio.sleep(0.05)
        assert len(attempts) == 1  # waiting out a 30 s backoff now
        began = time.monotonic()
        await client.stop()
        assert time.monotonic() - began < 0.5

    asyncio.run(retry_scenario())
    asyncio.run(stop_scenario())


class _ClosingSocket:
    """Delivers `messages`, then ends the iteration — i.e. the server hung up."""

    def __init__(self, messages):
        self._messages = list(messages)

    def __aiter__(self):
        return self

    async def __anext__(self):
        if not self._messages:
            raise StopAsyncIteration
        return self._messages.pop(0)


def flapping_connector(attempts: list[float], messages=()):
    """A server that completes the handshake and immediately closes."""

    @contextlib.asynccontextmanager
    async def connect(url):
        attempts.append(time.monotonic())
        yield _ClosingSocket(messages)

    return connect


def test_a_flapping_server_still_backs_off():
    """Accepting the handshake is not proof of a usable connection."""

    async def scenario():
        attempts: list[float] = []
        client = HookClient(
            "ws://127.0.0.1:1",
            on_text=lambda raw: None,
            connect=flapping_connector(attempts),
            initial_backoff=0.02,
            max_backoff=1.0,
        )
        client.start()
        await asyncio.sleep(0.35)
        await client.stop()
        # Doubling from 20ms reaches ~0.35s in about six attempts; resetting on the
        # handshake instead would retry every 20ms and pile up far more than that.
        assert 2 <= len(attempts) <= 9, attempts
        gaps = [b - a for a, b in zip(attempts, attempts[1:], strict=False)]
        assert gaps[-1] > gaps[0] * 1.5, gaps

    asyncio.run(scenario())


def test_backoff_resets_once_a_message_arrives():
    """A server that actually delivers text has proved itself; retry promptly."""

    async def scenario():
        attempts: list[float] = []
        seen: list[str] = []
        client = HookClient(
            "ws://127.0.0.1:1",
            on_text=seen.append,
            connect=flapping_connector(attempts, messages=["おはよう"]),
            initial_backoff=0.02,
            max_backoff=1.0,
        )
        client.start()
        await asyncio.sleep(0.35)
        await client.stop()
        assert len(seen) >= 5, seen
        gaps = [b - a for a, b in zip(attempts, attempts[1:], strict=False)]
        assert max(gaps) < 0.1, gaps  # never escalated

    asyncio.run(scenario())


def test_manager_serialises_reconfiguration_per_target():
    from kotoba.services.capture.hook_client import HookManager

    manager = HookManager(lambda: None)
    assert manager._lock("textractor") is manager._lock("textractor")
    assert manager._lock("textractor") is not manager._lock("luna")
