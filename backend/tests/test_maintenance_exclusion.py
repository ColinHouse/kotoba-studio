"""Restore and long-running writers must not overlap.

A JMdict import holds one session for minutes. Waiting for it would block a restore
for just as long, so the two refuse each other instead: whichever starts second loses.
"""

import threading
import time
from pathlib import Path
from types import SimpleNamespace

import pytest

from kotoba.api.capture import condensed
from kotoba.core.errors import ApiError
from kotoba.models import CaptureSession, Line, Source
from kotoba.services.capture import media
from kotoba.services.capture.gate import gate


@pytest.fixture(autouse=True)
def _clean_gate():
    yield
    # A leaked claim would block every later test's restore.
    for name in list(gate._long_writers):
        gate.end_long_write(name)
    gate.resume()


def _wait(predicate, timeout: float = 5.0) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return True
        time.sleep(0.02)
    return False


def _timed_source(db) -> int:
    source = Source(title="凝缩验证", kind="anime")
    db.add(source)
    db.commit()
    session = CaptureSession(source_id=source.id, mode="import")
    db.add(session)
    db.commit()
    db.add(
        Line(
            source_id=source.id,
            session_id=session.id,
            text="一句台词",
            text_hash="maintenance-1",
            origin="subtitle",
            start_ms=0,
            end_ms=1200,
            ord=1,
        )
    )
    db.commit()
    return source.id


def _start(client, source_id: int) -> condensed.CondenseJob:
    job = condensed.CondenseJob()
    job.start(
        client.app.state.db.session,
        client.app.state.paths,
        source_id,
        Path("in.mp4"),
        gap_ms=500,
        silence_ms=200,
    )
    return job


def test_restore_refuses_while_a_long_job_is_writing(client):
    name = client.post("/api/backups", json={}).json()["name"]
    gate.begin_long_write("jmdict-install")
    try:
        response = client.post("/api/backups/restore", json={"name": name})
        assert response.status_code >= 400
        body = response.json()["error"]
        assert body["code"] == "busy"
        assert "jmdict-install" in body["message"]
    finally:
        gate.end_long_write("jmdict-install")


def test_a_long_job_refuses_to_start_while_a_restore_holds(client):
    with gate.hold():
        with pytest.raises(ApiError) as err:
            gate.begin_long_write("fsrs-optimize")
        assert err.value.code == "restoring"


def test_restore_works_once_the_job_has_finished(client):
    name = client.post("/api/backups", json={}).json()["name"]
    gate.begin_long_write("jmdict-install")
    gate.end_long_write("jmdict-install")
    assert client.post("/api/backups/restore", json={"name": name}).status_code < 400


def test_hold_releases_the_maintenance_flag_even_when_the_body_raises(client):
    with pytest.raises(RuntimeError), gate.hold():
        raise RuntimeError("restore blew up")
    # A stuck flag would refuse every future job for the life of the process.
    gate.begin_long_write("pitch-install")
    gate.end_long_write("pitch-install")


def test_two_jobs_can_run_together(client):
    """Jobs exclude restore, not each other — that is a separate concern."""
    gate.begin_long_write("jmdict-install")
    gate.begin_long_write("pitch-install")
    gate.end_long_write("jmdict-install")
    gate.end_long_write("pitch-install")


def test_restore_refuses_while_condensed_audio_is_running(client, db, monkeypatch):
    """The fifth long job must claim the gate like the other four (#163)."""
    name = client.post("/api/backups", json={}).json()["name"]
    started, release = threading.Event(), threading.Event()

    def fake_condense(video, spans, media_dir, out_name, *, gap_ms, silence_ms, progress=None):
        started.set()
        assert release.wait(5)
        if progress is not None:
            progress(1, 1)
        return media.CondenseReport(segments=1, lines_used=len(spans), output=out_name)

    monkeypatch.setattr(media, "condense", fake_condense)
    source_id = _timed_source(db)
    job = _start(client, source_id)
    try:
        assert started.wait(5)
        response = client.post("/api/backups/restore", json={"name": name})
        assert response.status_code >= 400
        body = response.json()["error"]
        assert body["code"] == "busy"
        assert "condensed-audio" in body["message"]
    finally:
        release.set()
    assert _wait(lambda: job.state != "running")
    # Both sides recover: the gate is free again once the job ends.
    assert client.post("/api/backups/restore", json={"name": name}).status_code < 400


def test_condensed_audio_refuses_to_start_while_a_restore_holds(client, db):
    source_id = _timed_source(db)
    job = condensed.CondenseJob()
    with gate.hold():
        with pytest.raises(ApiError) as err:
            job.start(
                client.app.state.db.session,
                client.app.state.paths,
                source_id,
                Path("in.mp4"),
                gap_ms=500,
                silence_ms=200,
            )
        assert err.value.code == "restoring"
    # No half-started job: state is untouched and no thread exists.
    assert job.state != "running"
    assert job._thread is None


def test_condensed_audio_releases_the_gate_when_the_thread_cannot_start(client, db, monkeypatch):
    """A claim that outlives a failed thread.start() would block every restore."""

    class NoThread:
        def __init__(self, *args, **kwargs):
            raise RuntimeError("no threads today")

    monkeypatch.setattr(condensed, "threading", SimpleNamespace(Thread=NoThread))
    source_id = _timed_source(db)
    job = condensed.CondenseJob()
    with pytest.raises(RuntimeError):
        job.start(
            client.app.state.db.session,
            client.app.state.paths,
            source_id,
            Path("in.mp4"),
            gap_ms=500,
            silence_ms=200,
        )
    assert "condensed-audio" not in gate._long_writers
    assert job.state == "error"
