"""SQLite engine, sessions and schema upgrades."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

from alembic import command
from alembic.config import Config
from fastapi import Request
from sqlalchemy import Engine, create_engine, event
from sqlalchemy.orm import Session, sessionmaker

MIGRATIONS_DIR = Path(__file__).resolve().parents[1] / "migrations"


def sqlite_url(db_path: Path) -> str:
    return f"sqlite:///{db_path}"


def make_engine(db_path: Path) -> Engine:
    engine = create_engine(
        sqlite_url(db_path),
        connect_args={"check_same_thread": False},
        future=True,
    )

    @event.listens_for(engine, "connect")
    def _set_pragmas(dbapi_conn, _record):
        cur = dbapi_conn.cursor()
        cur.execute("PRAGMA journal_mode=WAL")
        cur.execute("PRAGMA foreign_keys=ON")
        cur.execute("PRAGMA synchronous=NORMAL")
        # pysqlite already sets this from its own `timeout=5.0` connect default, so
        # this line changes nothing today. It is here so the value sits beside the
        # other pragmas instead of depending on a driver default that could move --
        # and so the next person chasing a lock error does not have to rediscover
        # that it was never the missing piece. Five seconds does not save you from a
        # writer that holds the lock for minutes; keeping transactions short does.
        cur.execute("PRAGMA busy_timeout=5000")
        cur.close()

    return engine


def alembic_config(db_path: Path) -> Config:
    cfg = Config()
    cfg.set_main_option("script_location", str(MIGRATIONS_DIR))
    cfg.set_main_option("sqlalchemy.url", sqlite_url(db_path))
    return cfg


def upgrade(db_path: Path) -> None:
    """Bring the database at db_path to the latest schema (creates it if missing)."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    command.upgrade(alembic_config(db_path), "head")


class Database:
    def __init__(self, engine: Engine):
        self.engine = engine
        self.session_factory = sessionmaker(bind=engine, expire_on_commit=False, future=True)

    def session(self) -> Session:
        return self.session_factory()

    def dispose(self) -> None:
        self.engine.dispose()


def get_db(request: Request) -> Iterator[Session]:
    db: Database = request.app.state.db
    session = db.session()
    try:
        yield session
    finally:
        session.close()
