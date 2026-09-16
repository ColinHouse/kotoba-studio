"""WebSockets: /ws/events pushes new lines to clients; /ws/hook receives text from hook tools."""

from __future__ import annotations

import json

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from kotoba.core.errors import ApiError
from kotoba.core.events import broker
from kotoba.schemas import LineCreate
from kotoba.services import settings_store
from kotoba.services.text.ingest import create_line

router = APIRouter(tags=["websocket"])


@router.websocket("/ws/events")
async def events(ws: WebSocket) -> None:
    await ws.accept()
    queue = broker.subscribe()
    try:
        while True:
            event = await queue.get()
            await ws.send_json(event)
    except WebSocketDisconnect:
        pass
    finally:
        broker.unsubscribe(queue)


def _parse_hook_message(raw: str) -> dict:
    raw = raw.strip()
    if raw.startswith("{"):
        try:
            data = json.loads(raw)
            if isinstance(data, dict) and data.get("text"):
                return data
        except json.JSONDecodeError:
            pass
    return {"text": raw}


@router.websocket("/ws/hook")
async def hook(ws: WebSocket) -> None:
    """Accepts plain text or JSON {"text": ..., "speaker"?: ..., "session_id"?: ...}."""
    await ws.accept()
    db_factory = ws.app.state.db.session
    try:
        while True:
            raw = await ws.receive_text()
            message = _parse_hook_message(raw)
            if not message.get("text", "").strip():
                await ws.send_json({"ok": False, "error": "empty"})
                continue
            db = db_factory()
            try:
                session_id = message.get("session_id") or settings_store.get(
                    db, "active_session_id"
                )
                line, duplicate = create_line(
                    db,
                    LineCreate(
                        session_id=session_id,
                        text=message["text"],
                        origin="hook",
                        speaker=message.get("speaker"),
                    ),
                )
                await ws.send_json({"ok": True, "line_id": line.id, "duplicate": duplicate})
            except ApiError as exc:
                await ws.send_json({"ok": False, "error": exc.code, "message": exc.message})
            finally:
                db.close()
    except WebSocketDisconnect:
        pass
