"""SQLite has one writer, and a dictionary import is a long one.

The reported failure: installing JMdict made ordinary requests return 500. Two
things caused it — a single transaction spanning the whole 218k-entry import, so
the write lock was held for minutes, and no handler for the OperationalError that
came out the other side.

busy_timeout was the obvious suspect and was innocent: pysqlite already sets it
to five seconds, which is not a useful amount of time to wait for a lock held for
minutes.
"""

import threading

from sqlalchemy import text

from kotoba.core.db import make_engine


def test_the_connection_pragmas_are_what_we_think(tmp_path):
    """Characterisation, not regression: busy_timeout is already 5000 on main.

    pysqlite sets it from its own connect default, so it was never the missing
    piece — five seconds cannot save a writer that holds the lock for minutes.
    Asserted anyway so a driver change that drops it does not go unnoticed.
    """
    engine = make_engine(tmp_path / "k.db")
    with engine.connect() as conn:
        assert conn.execute(text("PRAGMA busy_timeout")).scalar() == 5000
        assert conn.execute(text("PRAGMA journal_mode")).scalar() == "wal"


def test_a_writer_waits_out_a_short_lock_and_succeeds(tmp_path):
    """A capture landing while an import commits a batch must not fail outright."""
    engine = make_engine(tmp_path / "k.db")
    with engine.begin() as setup:
        setup.execute(text("CREATE TABLE t (v INTEGER)"))

    holder_ready = threading.Event()
    release = threading.Event()

    def hold_the_lock() -> None:
        with engine.connect() as conn:
            conn.execute(text("BEGIN IMMEDIATE"))
            conn.execute(text("INSERT INTO t VALUES (1)"))
            holder_ready.set()
            release.wait(timeout=5)
            conn.execute(text("COMMIT"))

    holder = threading.Thread(target=hold_the_lock, daemon=True)
    holder.start()
    assert holder_ready.wait(timeout=5)

    # The lock is held right now. Let it go shortly; busy_timeout should absorb it.
    threading.Timer(0.3, release.set).start()
    with engine.begin() as conn:
        conn.execute(text("INSERT INTO t VALUES (2)"))
    holder.join(timeout=5)

    with engine.connect() as conn:
        assert conn.execute(text("SELECT count(*) FROM t")).scalar() == 2


def test_a_busy_database_answers_with_the_envelope_not_a_500():
    """Invariant: every error leaves through {"error": {...}} (AGENTS.md §5.6).

    Exercised against the handler itself rather than through one endpoint, because
    what changed is the mapping from OperationalError to a response — not the
    internals of whichever route happened to be unlucky.
    """
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from sqlalchemy.exc import OperationalError

    from kotoba.core.errors import install_error_handlers

    app = FastAPI()
    install_error_handlers(app)

    @app.get("/locked")
    def _locked():
        raise OperationalError("INSERT", {}, Exception("database is locked"))

    @app.get("/broken")
    def _broken():
        raise OperationalError("SELECT", {}, Exception("no such column: nope"))

    with TestClient(app, raise_server_exceptions=False) as c:
        busy = c.get("/locked")
        assert busy.status_code == 503
        assert busy.json()["error"]["code"] == "database_busy"
        assert "词典" in busy.json()["error"]["message"]

        # A real database fault is still an error, just not a "try again".
        other = c.get("/broken")
        assert other.status_code == 500
        assert other.json()["error"]["code"] == "database_error"


def test_jmdict_import_commits_as_it_goes(client, tmp_path):
    """Holding one transaction for 218k entries blocks every other writer for minutes."""
    from kotoba.services.dictionary.jmdict import importer

    seen: list[int] = []
    real_commit = importer._commit_batch

    def counting(db, entries, forms):
        real_commit(db, entries, forms)
        seen.append(len(entries))

    importer._commit_batch = counting
    try:
        words = [
            {"id": str(i), "kanji": [{"text": f"語{i}"}], "kana": [{"text": f"ご{i}"}], "sense": []}
            for i in range(importer.BATCH + 50)
        ]
        path = tmp_path / "jmdict.json"
        path.write_text(__import__("json").dumps({"words": words}), encoding="utf-8")
        db = client.app.state.db.session()
        try:
            importer.import_json(db, path)
        finally:
            db.close()
    finally:
        importer._commit_batch = real_commit

    # More than one commit means the write lock was released between batches.
    assert len(seen) >= 2, seen
