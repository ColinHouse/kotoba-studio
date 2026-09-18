"""Restore and long-running writers must not overlap.

A JMdict import holds one session for minutes. Waiting for it would block a restore
for just as long, so the two refuse each other instead: whichever starts second loses.
"""

import threading
from pathlib import Path

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


def _timed_source(db):
    """A source with one timed line — enough for the condensed job to have work."""
    source = Source(title="episode", kind="anime")
    db.add(source)
    db.commit()
    session = CaptureSession(source_id=source.id, mode="import")
    db.add(session)
    db.commit()
    db.add(
        Line(
            source_id=source.id,
            session_id=session.id,
            text="台詞",
            text_hash="hash-1",
            origin="subtitle",
            start_ms=0,
            end_ms=3000,
            ord=1,
        )
    )
    db.commit()
    return source


def _allow_ffmpeg(monkeypatch, tmp_path):
    video = tmp_path / "ep.mkv"
    video.write_bytes(b"x")
    monkeypatch.setattr(media, "ffmpeg_path", lambda: "ffmpeg")
    monkeypatch.setattr(condensed, "condense_job", condensed.CondenseJob())
    return video


def test_condensed_audio_refuses_to_start_while_a_restore_holds(client, db, tmp_path, monkeypatch):
    """It writes into media_dir for minutes; a restore is merging media into the same place."""
    video = _allow_ffmpeg(monkeypatch, tmp_path)
    client.put("/api/settings", json={"video_dirs": [str(video.parent)]})
    source = _timed_source(db)
    with gate.hold():
        response = client.post(
            f"/api/sources/{source.id}/condensed", json={"video_path": str(video)}
        )
    assert response.status_code >= 400
    assert response.json()["error"]["code"] == "restoring"


def test_restore_refuses_while_condensed_audio_is_writing(client, db, tmp_path, monkeypatch):
    video = _allow_ffmpeg(monkeypatch, tmp_path)
    client.put("/api/settings", json={"video_dirs": [str(video.parent)]})
    source = _timed_source(db)
    backup_name = client.post("/api/backups", json={}).json()["name"]

    running, release = threading.Event(), threading.Event()

    def blocked_ffmpeg(args):
        running.set()
        release.wait(5)
        Path(args[-1]).write_bytes(b"x")

    monkeypatch.setattr(media, "run_ffmpeg", blocked_ffmpeg)
    assert (
        client.post(
            f"/api/sources/{source.id}/condensed", json={"video_path": str(video)}
        ).status_code
        == 202
    )
    assert running.wait(5), "the condensed job never reached ffmpeg"
    try:
        response = client.post("/api/backups/restore", json={"name": backup_name})
        assert response.status_code >= 400
        body = response.json()["error"]
        assert body["code"] == "busy"
        assert "condensed-audio" in body["message"]
    finally:
        release.set()


def test_condensed_audio_releases_the_claim_when_the_thread_will_not_start(
    client, db, tmp_path, monkeypatch
):
    """A claim leaked here would refuse every restore for the life of the process."""
    video = _allow_ffmpeg(monkeypatch, tmp_path)
    client.put("/api/settings", json={"video_dirs": [str(video.parent)]})
    source = _timed_source(db)

    def refuse_to_start(self):
        raise RuntimeError("can't start new thread")

    monkeypatch.setattr(threading.Thread, "start", refuse_to_start)
    with pytest.raises(RuntimeError):
        client.post(f"/api/sources/{source.id}/condensed", json={"video_path": str(video)})
    monkeypatch.undo()
    assert not gate._long_writers, "the condensed job leaked its claim"
