import io
import threading
import time

from PIL import Image, ImageDraw, ImageFont

from kotoba.core.errors import ApiError
from kotoba.services.capture.screen import Grab, Region
from kotoba.services.capture.watcher import RegionWatcher
from kotoba.services.ocr.base import OcrResult

CANVAS = (480, 100)
REGION = {"left": 0, "top": 0, "width": 480, "height": 100}


def frame_png(text: str = "") -> bytes:
    image = Image.new("RGB", CANVAS, (18, 18, 28))
    if text:
        draw = ImageDraw.Draw(image)
        font = ImageFont.load_default(size=40)
        draw.text((14, 20), text, font=font, fill=(240, 240, 240))
    buf = io.BytesIO()
    image.save(buf, format="PNG")
    return buf.getvalue()


class ScriptedFrames:
    """Feeds scripted frames, repeating the last one once the script is exhausted."""

    def __init__(self, *texts: str) -> None:
        self._pngs = [frame_png(text) for text in texts]
        self.calls = 0

    def __call__(self, region: Region) -> Grab:
        png = self._pngs[min(self.calls, len(self._pngs) - 1)]
        self.calls += 1
        return Grab(png=png, width=region.width, height=region.height, scale=1.0)


class AlternatingFrames:
    """Two very different frames, so the tracker never settles."""

    def __init__(self) -> None:
        self._pngs = [frame_png("AA"), frame_png("MMMMMMMMMMMMMM")]
        self.calls = 0

    def __call__(self, region: Region) -> Grab:
        png = self._pngs[self.calls % len(self._pngs)]
        self.calls += 1
        return Grab(png=png, width=region.width, height=region.height, scale=1.0)


class ScriptedProvider:
    name = "scripted"
    note = "test"

    def __init__(self, *texts: str) -> None:
        self._texts = list(texts)

    def available(self) -> bool:
        return True

    def recognize(self, png: bytes) -> OcrResult:
        text = self._texts.pop(0) if self._texts else ""
        return OcrResult(text, [], self.name, 1)


class FailingProvider:
    name = "boom"
    note = "test"

    def available(self) -> bool:
        return True

    def recognize(self, png: bytes) -> OcrResult:
        raise ApiError("ocr_failed", "引擎炸了")


def wait_for(predicate, timeout: float = 5.0) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return True
        time.sleep(0.01)
    return predicate()


def watcher_threads() -> int:
    return sum(t.name == "region-watcher" for t in threading.enumerate())


def start_session(client) -> int:
    src = client.post("/api/sources", json={"title": "作品"}).json()
    ses = client.post("/api/sessions", json={"source_id": src["id"]}).json()
    client.put("/api/settings", json={"active_session_id": ses["id"]})
    return ses["id"]


def make_watcher(client, frames, provider, **kwargs) -> RegionWatcher:
    return RegionWatcher(
        Region(0, 0, CANVAS[0], CANVAS[1]),
        lambda: client.app.state.db.session(),
        provider,
        grabber=frames,
        interval=0.01,
        **kwargs,
    )


TWO_SCENES = (
    # "AA" typing to "AAAAAAAAAAAAAA", then a new line "WW" typing out.
    "AA",
    "AAAAAA",
    "AAAAAAAAAA",
    "AAAAAAAAAAAAAA",
    "AAAAAAAAAAAAAA",
    "AAAAAAAAAAAAAA",
    "WW",
    "WWWWWW",
    "WWWWWWWWWW",
    "WWWWWWWWWWWWWW",
    "WWWWWWWWWWWWWW",
    "WWWWWWWWWWWWWW",
)


def test_watcher_creates_one_line_per_settled_scene(client):
    session_id = start_session(client)
    watcher = make_watcher(
        client, ScriptedFrames(*TWO_SCENES), ScriptedProvider("第一句", "第二句")
    )
    watcher.start()
    try:
        assert wait_for(lambda: watcher.captured == 2)
    finally:
        watcher.stop()

    lines = client.get("/api/lines", params={"session_id": session_id}).json()
    assert {line["text"] for line in lines} == {"第一句", "第二句"}
    assert {line["origin"] for line in lines} == {"ocr"}
    assert watcher.last_error is None
    assert watcher.running is False


def test_watcher_survives_ocr_failure(client):
    start_session(client)
    frames = ScriptedFrames(*TWO_SCENES[:6])
    watcher = make_watcher(client, frames, FailingProvider())
    watcher.start()
    try:
        # The trigger is frame 6. Later polls keep succeeding but need no OCR;
        # the error must stay visible instead of vanishing after one frame.
        assert wait_for(lambda: frames.calls > 10)
        assert watcher.last_error == "引擎炸了"
        assert watcher.running is True
        assert watcher.captured == 0
    finally:
        watcher.stop()


def test_watch_endpoints_are_idempotent_and_stop_cleanly(client):
    client.app.state.capture_grabber = AlternatingFrames()
    client.app.state.ocr_provider = ScriptedProvider("第一句")

    started = client.post("/api/capture/watch/start", json={"region": REGION})
    assert started.status_code == 200
    assert started.json() == {"running": True, "captured": 0, "last_error": None}

    again = client.post("/api/capture/watch/start", json={"region": REGION})
    assert again.status_code == 200
    assert again.json()["running"] is True
    assert watcher_threads() == 1

    status = client.get("/api/capture/watch/status").json()
    assert status["running"] is True

    stopped = client.post("/api/capture/watch/stop").json()
    assert stopped == {"running": False, "captured": 0, "last_error": None}
    assert watcher_threads() == 0

    idle = client.get("/api/capture/watch/status").json()
    assert idle["running"] is False
