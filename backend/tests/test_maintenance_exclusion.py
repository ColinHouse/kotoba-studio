"""Restore and long-running writers must not overlap.

A JMdict import holds one session for minutes. Waiting for it would block a restore
for just as long, so the two refuse each other instead: whichever starts second loses.
"""

import pytest

from kotoba.core.errors import ApiError
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
