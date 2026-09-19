"""Outbound hook connections: connect, disconnect, list."""

from __future__ import annotations

from fastapi import APIRouter, Request
from pydantic import BaseModel

from kotoba.services.capture.hook_client import HookManager

router = APIRouter(prefix="/capture/hooks", tags=["capture"])


class HookConnectIn(BaseModel):
    url: str | None = None


def _manager(request: Request) -> HookManager:
    return request.app.state.hook_manager


@router.get("")
def get_hooks(request: Request) -> list[dict]:
    return _manager(request).list()


@router.post("/{name}/connect")
async def connect_hook(name: str, request: Request, body: HookConnectIn | None = None) -> dict:
    return await _manager(request).connect(name, body.url if body else None)


@router.post("/{name}/disconnect")
async def disconnect_hook(name: str, request: Request) -> dict:
    return await _manager(request).disconnect(name)


@router.post("/{name}/probe")
async def probe_hook(name: str, request: Request, body: HookConnectIn | None = None) -> dict:
    return await _manager(request).probe(name, body.url if body else None)
