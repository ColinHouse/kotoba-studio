"""Outbound WebSocket connections to text hook tools.

Textractor, Agent and LunaTranslator each run their own WebSocket server, so
instead of waiting for them to connect to /ws/hook we connect to them. They
are frequently not running; that is normal, so failures log at debug level and
the client keeps retrying with exponential backoff.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
from collections.abc import Callable
from datetime import datetime
from typing import Any

import websockets
from sqlalchemy.orm import Session

from kotoba.core.errors import ApiError
from kotoba.models import utcnow
from kotoba.schemas import LineCreate
from kotoba.services import settings_store
from kotoba.services.capture.gate import gate
from kotoba.services.text.hook import parse_hook_message
from kotoba.services.text.ingest import create_line

log = logging.getLogger(__name__)

PRESETS: dict[str, str] = {
    "textractor": "ws://127.0.0.1:6677",
    "agent": "ws://127.0.0.1:9001",
    "luna": "ws://127.0.0.1:2333",
}

# A one-shot connection test must answer quickly; the retrying client is the
# patient one.
PROBE_TIMEOUT = 2.0


class HookClient:
    """One outbound WebSocket with exponential backoff between attempts."""

    def __init__(
        self,
        url: str,
        on_text: Callable[[str], None],
        *,
        connect: Callable[[str], Any] = websockets.connect,
        initial_backoff: float = 0.5,
        max_backoff: float = 30.0,
    ) -> None:
        self.url = url
        self._on_text = on_text
        self._connect = connect
        self._initial_backoff = initial_backoff
        self._max_backoff = max_backoff
        self._stopped = asyncio.Event()
        self._task: asyncio.Task[None] | None = None
        self.connected = False
        self.last_text_at: datetime | None = None
        self.last_text: str | None = None
        self.error: str | None = None

    @property
    def running(self) -> bool:
        return self._task is not None and not self._task.done()

    @property
    def state(self) -> str:
        """idle / connecting / connected — the three states the capture UI shows."""
        if self.connected:
            return "connected"
        return "connecting" if self.running else "idle"

    def start(self) -> None:
        if self.running:
            return
        self._stopped.clear()
        self._task = asyncio.create_task(self._run(), name=f"hook-client:{self.url}")

    async def stop(self) -> None:
        """Stop now: set the flag and cancel a task that is blocked on I/O or the backoff."""
        self._stopped.set()
        task, self._task = self._task, None
        if task is not None and not task.done():
            task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await task
        self.connected = False

    async def _run(self) -> None:
        backoff = self._initial_backoff
        while not self._stopped.is_set():
            try:
                async with self._connect(self.url) as ws:
                    self.connected = True
                    self.error = None
                    async for raw in ws:
                        if not isinstance(raw, str):
                            continue
                        # Reset on a delivered message, not on the handshake: a server
                        # that accepts and immediately closes would otherwise be retried
                        # every 0.5s for ever instead of backing off.
                        backoff = self._initial_backoff
                        self.last_text_at = utcnow()
                        # The parsed text, not the raw frame: a JSON payload should
                        # not show up as JSON in the status line.
                        self.last_text = parse_hook_message(raw).get("text", "").strip() or None
                        try:
                            self._on_text(raw)
                        except Exception:  # noqa: BLE001 - one bad line must not end the reconnect loop
                            log.debug("hook message dropped", exc_info=True)
            except asyncio.CancelledError:
                raise
            except Exception as exc:  # noqa: BLE001 - any socket or protocol error just means reconnect
                self.error = f"{type(exc).__name__}: {exc}"
                log.debug("hook client %s failed: %s", self.url, exc)
            finally:
                self.connected = False
            if self._stopped.is_set():
                break
            if await self._wait(backoff):
                break
            backoff = min(backoff * 2, self._max_backoff)

    async def _wait(self, delay: float) -> bool:
        """Wait out the backoff unless stopped; returns True when stopped meanwhile."""
        try:
            await asyncio.wait_for(self._stopped.wait(), timeout=delay)
            return True
        except TimeoutError:
            return False


class HookManager:
    """Owns one HookClient per target name and turns its messages into lines."""

    def __init__(self, session_factory: Callable[[], Session]) -> None:
        self._session_factory = session_factory
        self._clients: dict[str, HookClient] = {}
        self._locks: dict[str, asyncio.Lock] = {}

    def _lock(self, name: str) -> asyncio.Lock:
        """One lock per target: connect and disconnect both await, and interleaving
        them would let a resumed connect revive a client that disconnect just stopped."""
        lock = self._locks.get(name)
        if lock is None:
            lock = self._locks[name] = asyncio.Lock()
        return lock

    def get(self, name: str) -> HookClient | None:
        return self._clients.get(name)

    async def connect(self, name: str, url: str | None = None) -> dict:
        url = (url or PRESETS.get(name) or "").strip()
        if not url:
            raise ApiError("unknown_hook", f"未知的 Hook 目标：{name}")
        async with self._lock(name):
            client = self._clients.get(name)
            if client is not None and client.url != url:
                await client.stop()
                self._clients.pop(name, None)
                client = None
            if client is None:
                client = HookClient(url, self._ingest)
                self._clients[name] = client
            client.start()
            return self.describe(name)

    async def disconnect(self, name: str) -> dict:
        async with self._lock(name):
            client = self._clients.get(name)
            if client is None and name not in PRESETS:
                raise ApiError("not_found", f"未知的 Hook 目标：{name}", 404)
            if client is not None:
                await client.stop()
            return self.describe(name)

    def list(self) -> list[dict]:
        names = list(dict.fromkeys([*PRESETS, *self._clients]))
        return [self.describe(name) for name in names]

    def describe(self, name: str) -> dict:
        client = self._clients.get(name)
        return {
            "name": name,
            "url": client.url if client is not None else PRESETS.get(name, ""),
            "connected": client.connected if client is not None else False,
            "status": client.state if client is not None else "idle",
            "last_text": client.last_text if client is not None else None,
            "last_text_at": (
                client.last_text_at.isoformat()
                if client is not None and client.last_text_at is not None
                else None
            ),
            "error": client.error if client is not None else None,
        }

    async def probe(self, name: str, url: str | None = None) -> dict:
        """Open one connection and close it, without touching the retrying client.

        This backs the UI's test button: an immediate yes/no instead of watching
        a backoff that may be 30 seconds long.
        """
        client = self._clients.get(name)
        target = url or (client.url if client is not None else None) or PRESETS.get(name) or ""
        target = target.strip()
        if not target:
            raise ApiError("unknown_hook", f"未知的 Hook 目标：{name}")
        try:
            async with asyncio.timeout(PROBE_TIMEOUT):
                async with websockets.connect(target):
                    pass
        except Exception as exc:  # noqa: BLE001 - any failure is simply "not reachable"
            return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}
        return {"ok": True, "error": None}

    async def shutdown(self) -> None:
        for client in list(self._clients.values()):
            await client.stop()

    def _ingest(self, raw: str) -> None:
        message = parse_hook_message(raw)
        text = message.get("text", "").strip()
        if not text:
            return
        with gate.ingest() as allowed:
            if not allowed:
                return
            db = self._session_factory()
            try:
                session_id = message.get("session_id") or settings_store.get(
                    db, "active_session_id"
                )
                create_line(
                    db,
                    LineCreate(
                        session_id=session_id,
                        text=text,
                        origin="hook",
                        speaker=message.get("speaker"),
                    ),
                )
            except ApiError as exc:
                log.debug("hook text skipped: %s", exc.message)
            finally:
                db.close()
