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
    assert all(hook["last_text_at"] is None for hook in listed.values())


def test_unknown_target_needs_a_url(client):
    r = client.post("/api/capture/hooks/nope/connect")
    assert r.status_code == 400
    assert r.json()["error"]["code"] == "unknown_hook"
    assert client.post("/api/capture/hooks/nope/disconnect").status_code == 404


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
        assert live["last_text_at"] is not None
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

    stopped = client.post("/api/capture/hooks/test/disconnect").json()
    assert stopped["connected"] is False


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
