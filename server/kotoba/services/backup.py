"""Backups: consistent SQLite snapshot (VACUUM INTO) + media, zipped."""

from __future__ import annotations

import shutil
import sqlite3
import tempfile
import zipfile
from datetime import UTC, datetime
from pathlib import Path

from kotoba.config import Paths
from kotoba.errors import ApiError

DB_NAME = "kotoba.db"


def _snapshot_db(db_path: Path, dest: Path) -> None:
    if dest.exists():
        dest.unlink()
    conn = sqlite3.connect(db_path)
    try:
        conn.execute("VACUUM INTO ?", (str(dest),))
    finally:
        conn.close()


def create(paths: Paths, prefix: str = "kotoba-backup") -> Path:
    paths.backups_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
    out = paths.backups_dir / f"{prefix}-{stamp}.zip"
    with tempfile.TemporaryDirectory() as tmp:
        snap = Path(tmp) / DB_NAME
        _snapshot_db(paths.db_path, snap)
        with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.write(snap, DB_NAME)
            if paths.media_dir.is_dir():
                for file in sorted(paths.media_dir.rglob("*")):
                    if file.is_file():
                        zf.write(file, f"media/{file.relative_to(paths.media_dir).as_posix()}")
    return out


def list_backups(paths: Paths) -> list[dict]:
    if not paths.backups_dir.is_dir():
        return []
    out = []
    for file in sorted(paths.backups_dir.glob("*.zip"), reverse=True):
        stat = file.stat()
        out.append(
            {
                "name": file.name,
                "size": stat.st_size,
                "created_at": datetime.fromtimestamp(stat.st_mtime, UTC).isoformat(),
            }
        )
    return out


def restore(paths: Paths, name: str) -> dict:
    """Replace the database and merge media from a backup zip. Caller must have closed the DB
    before and must reopen/upgrade it afterwards."""
    if "/" in name or "\\" in name or not name.endswith(".zip"):
        raise ApiError("invalid_backup", "invalid backup name")
    source = paths.backups_dir / name
    if not source.is_file():
        raise ApiError("not_found", f"backup {name} not found", 404)
    with zipfile.ZipFile(source) as zf:
        names = zf.namelist()
        if DB_NAME not in names:
            raise ApiError("invalid_backup", "backup does not contain kotoba.db")
        snapshot = create(paths, prefix="pre-restore") if paths.db_path.exists() else None
        for suffix in ("", "-wal", "-shm"):
            p = Path(str(paths.db_path) + suffix)
            if p.exists():
                p.unlink()
        with zf.open(DB_NAME) as src, paths.db_path.open("wb") as dst:
            shutil.copyfileobj(src, dst)
        media_count = 0
        for member in names:
            if member.startswith("media/") and not member.endswith("/"):
                target = paths.media_dir / member[len("media/") :]
                target.parent.mkdir(parents=True, exist_ok=True)
                with zf.open(member) as src, target.open("wb") as dst:
                    shutil.copyfileobj(src, dst)
                media_count += 1
    return {"restored": name, "snapshot": snapshot.name if snapshot else None, "media": media_count}
