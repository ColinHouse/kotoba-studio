"""Backups: consistent SQLite snapshot (VACUUM INTO) + media, zipped."""

from __future__ import annotations

import shutil
import sqlite3
import tempfile
import zipfile
from datetime import UTC, datetime
from pathlib import Path

from kotoba.core.config import Paths
from kotoba.core.errors import ApiError

DB_NAME = "kotoba.db"


def _snapshot_db(db_path: Path, dest: Path) -> None:
    if dest.exists():
        dest.unlink()
    conn = sqlite3.connect(db_path)
    try:
        conn.execute("VACUUM INTO ?", (str(dest),))
    finally:
        conn.close()


MEDIA_PREFIX = "media/"


def _media_targets(names: list[str], media_dir: Path) -> list[tuple[str, Path]]:
    """Map each media member to where it will be written, refusing any that escapes.

    A backup is a file people carry between machines, so the paths inside it are
    untrusted input: `media/../../x` would otherwise be written outside the media
    directory, and `mkdir(parents=True)` would create the way there. Everything is
    checked before the first byte is written — a half-restored database is a worse
    outcome than a refused one.
    """
    root = media_dir.resolve()
    targets = []
    for member in names:
        if not member.startswith(MEDIA_PREFIX) or member.endswith("/"):
            continue
        relative = member[len(MEDIA_PREFIX) :]
        target = (media_dir / relative).resolve()
        if target == root or root not in target.parents:
            raise ApiError("invalid_backup", f"backup contains an unsafe path: {member}")
        targets.append((member, target))
    return targets


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
        # Validate every path first: this must raise before the database is touched.
        targets = _media_targets(names, paths.media_dir)
        snapshot = create(paths, prefix="pre-restore") if paths.db_path.exists() else None
        for suffix in ("", "-wal", "-shm"):
            p = Path(str(paths.db_path) + suffix)
            if p.exists():
                p.unlink()
        with zf.open(DB_NAME) as src, paths.db_path.open("wb") as dst:
            shutil.copyfileobj(src, dst)
        media_count = 0
        for member, target in targets:
            target.parent.mkdir(parents=True, exist_ok=True)
            with zf.open(member) as src, target.open("wb") as dst:
                shutil.copyfileobj(src, dst)
            media_count += 1
    return {"restored": name, "snapshot": snapshot.name if snapshot else None, "media": media_count}
