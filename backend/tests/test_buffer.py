import io
import time
from datetime import timedelta

from PIL import Image

from kotoba.models import Line, utcnow
from kotoba.services.capture.buffer import MediaBuffer
from kotoba.services.capture.screen import Grab, Region
from kotoba.services.capture.watcher import RegionWatcher
from kotoba.services.ocr.base import OcrResult

REGION = {"left": 0, "top": 0, "width": 120, "height": 40}
NOW = utcnow()


def png(seed: int) -> bytes:
    image = Image.new("RGB", (120, 40), (seed, seed, seed))
    buf = io.BytesIO()
    image.save(buf, format="PNG")
    return buf.getvalue()


def wait_for(predicate, timeout: float = 5.0) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return True
        time.sleep(0.01)
    return predicate()


def test_frame_at_takes_the_latest_frame_not_after_the_time():
    buffer = MediaBuffer(seconds=600)
    buffer.add_frame(b"old", NOW - timedelta(seconds=10))
    buffer.add_frame(b"new", NOW - timedelta(seconds=2))
    buffer.add_frame(b"future", NOW + timedelta(seconds=1))

    frame = buffer.frame_at(NOW, tolerance_s=5)
    assert frame is not None and frame.data == b"new"


def test_frame_at_returns_none_outside_tolerance():
    buffer = MediaBuffer(seconds=600)
    buffer.add_frame(b"old", NOW - timedelta(seconds=9))
    assert buffer.frame_at(NOW, tolerance_s=5) is None


def test_frame_at_only_looks_backwards():
    buffer = MediaBuffer(seconds=600)
    buffer.add_frame(b"future", NOW + timedelta(seconds=1))
    assert buffer.frame_at(NOW, tolerance_s=5) is None


def test_byte_cap_drops_the_oldest_first():
    buffer = MediaBuffer(seconds=600, max_bytes=10)
    buffer.add_frame(b"aaaaaa", NOW - timedelta(seconds=3))
    buffer.add_audio(b"bbbbbb", NOW - timedelta(seconds=2))
    buffer.add_frame(b"cccccc", NOW)

    assert buffer.stats()["bytes"] == 6
    assert buffer.audio_at(NOW, tolerance_s=5) is None
    frame = buffer.frame_at(NOW, tolerance_s=5)
    assert frame is not None and frame.data == b"cccccc"


def test_age_cap_drops_frames_older_than_seconds():
    buffer = MediaBuffer(seconds=5)
    buffer.add_frame(b"old", utcnow() - timedelta(seconds=30))
    buffer.add_frame(b"new", utcnow())
    assert buffer.stats() == {"frames": 1, "audio_chunks": 0, "bytes": 3}


def test_clear_releases_everything():
    buffer = MediaBuffer(seconds=600)
    buffer.add_frame(b"frame", NOW)
    buffer.add_audio(b"audio", NOW)
    buffer.clear()
    assert buffer.stats() == {"frames": 0, "audio_chunks": 0, "bytes": 0}


def make_line(client, at=None) -> dict:
    line = client.post("/api/lines", json={"text": "あとから拾う"}).json()["line"]
    if at is not None:
        db = client.app.state.db.session()
        try:
            row = db.get(Line, line["id"])
            row.captured_at = at
            db.commit()
        finally:
            db.close()
    return line


def backfill(client, line_id: int, **params):
    return client.post(f"/api/lines/{line_id}/backfill", params=params)


def test_backfill_attaches_the_frame_before_captured_at(client):
    at = utcnow()
    line = make_line(client, at=at)
    buffer = client.app.state.media_buffer
    buffer.add_frame(png(1), at - timedelta(seconds=2))
    buffer.add_frame(png(2), at - timedelta(seconds=0.5))
    buffer.add_frame(png(3), at + timedelta(seconds=1))

    r = backfill(client, line["id"])
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["updated"] is True
    saved = client.app.state.paths.media_dir / body["line"]["screenshot_path"]
    assert saved.read_bytes() == png(2)


def test_backfill_keeps_existing_media_without_force(client):
    at = utcnow()
    line = make_line(client, at=at)
    buffer = client.app.state.media_buffer
    buffer.add_frame(png(1), at)
    first = backfill(client, line["id"]).json()["line"]["screenshot_path"]

    buffer.clear()
    buffer.add_frame(png(2), at)
    again = backfill(client, line["id"]).json()
    assert again["updated"] is False
    assert again["line"]["screenshot_path"] == first

    forced = backfill(client, line["id"], force="true").json()
    assert forced["updated"] is True
    assert forced["line"]["screenshot_path"] != first
    saved = client.app.state.paths.media_dir / forced["line"]["screenshot_path"]
    assert saved.read_bytes() == png(2)


def test_backfill_reports_a_miss_outside_tolerance(client):
    at = utcnow()
    line = make_line(client, at=at)
    client.app.state.media_buffer.add_frame(png(1), at - timedelta(seconds=30))

    r = backfill(client, line["id"])
    assert r.status_code == 404
    assert r.json()["error"]["code"] == "buffer_miss"


def test_backfill_tolerance_is_configurable(client):
    at = utcnow()
    line = make_line(client, at=at)
    client.app.state.media_buffer.add_frame(png(1), at - timedelta(seconds=30))
    assert backfill(client, line["id"]).status_code == 404

    client.put("/api/settings", json={"backfill_tolerance_s": 60})
    assert backfill(client, line["id"]).status_code == 200


def test_backfill_attaches_audio_too(client):
    at = utcnow()
    line = make_line(client, at=at)
    buffer = client.app.state.media_buffer
    buffer.add_frame(png(1), at)
    buffer.add_audio(b"RIFFfake", at - timedelta(seconds=1))

    body = backfill(client, line["id"]).json()
    saved = client.app.state.paths.media_dir / body["line"]["audio_path"]
    assert saved.read_bytes() == b"RIFFfake"


def test_the_buffer_writes_nothing_into_the_data_dir(client):
    data_dir = client.app.state.paths.data_dir
    before = {str(path) for path in data_dir.rglob("*") if path.is_file()}

    buffer = client.app.state.media_buffer
    buffer.add_frame(png(1), utcnow())
    buffer.add_audio(b"x", utcnow())

    after = {str(path) for path in data_dir.rglob("*") if path.is_file()}
    assert before == after


class Frames:
    def __init__(self) -> None:
        self.calls = 0

    def __call__(self, region: Region) -> Grab:
        self.calls += 1
        return Grab(png=png(7), width=region.width, height=region.height, scale=1.0)


class SilentProvider:
    name = "scripted"
    note = "test"

    def available(self) -> bool:
        return True

    def recognize(self, png: bytes) -> OcrResult:
        return OcrResult("", [], self.name, 1)


def test_stopping_the_watcher_releases_the_buffer(client):
    buffer = MediaBuffer(seconds=600)
    watcher = RegionWatcher(
        Region(0, 0, 120, 40),
        lambda: client.app.state.db.session(),
        SilentProvider(),
        grabber=Frames(),
        interval=0.01,
        buffer=buffer,
    )
    watcher.start()
    try:
        assert wait_for(lambda: buffer.stats()["frames"] > 0)
    finally:
        watcher.stop()
    assert buffer.stats() == {"frames": 0, "audio_chunks": 0, "bytes": 0}


def test_stopping_the_watch_endpoint_clears_the_app_buffer(client):
    client.app.state.capture_grabber = Frames()
    client.app.state.ocr_provider = SilentProvider()

    client.post("/api/capture/watch/start", json={"region": REGION})
    buffer = client.app.state.media_buffer
    assert wait_for(lambda: buffer.stats()["frames"] > 0)

    client.post("/api/capture/watch/stop")
    assert buffer.stats() == {"frames": 0, "audio_chunks": 0, "bytes": 0}
