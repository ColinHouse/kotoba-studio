"""Backup and restore."""

from __future__ import annotations

from fastapi import APIRouter, Request
from pydantic import BaseModel

from kotoba.core.db import Database, make_engine, upgrade
from kotoba.services import backup
from kotoba.services.capture.gate import gate

router = APIRouter(prefix="/backups", tags=["backups"])


class RestoreIn(BaseModel):
    name: str


@router.get("")
def list_backups(request: Request) -> list[dict]:
    return backup.list_backups(request.app.state.paths)


@router.post("", status_code=201)
def create_backup(request: Request) -> dict:
    path = backup.create(request.app.state.paths)
    return {"name": path.name, "size": path.stat().st_size}


@router.post("/restore")
def restore_backup(body: RestoreIn, request: Request) -> dict:
    app = request.app
    paths = app.state.paths
    # Silence every capture source and wait for the write in flight before the
    # file is swapped; a line arriving mid-restore would land in the database
    # that is about to be overwritten.
    with gate.hold():
        app.state.db.dispose()
        try:
            result = backup.restore(paths, body.name)
        finally:
            upgrade(paths.db_path)
            app.state.db = Database(make_engine(paths.db_path))
    return result
