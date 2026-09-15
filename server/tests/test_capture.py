import io
import sys

import pytest
from PIL import Image, ImageDraw, ImageFont

from kotoba.errors import ApiError
from kotoba.services.capture.screen import Grab, Region
from kotoba.services.ocr import registry
from kotoba.services.ocr.base import OcrBlock, OcrResult


class FakeProvider:
    name = "fake"
    note = "test"

    def __init__(self, text="え、本当に？"):
        self.text = text
        self.calls = 0

    def available(self):
        return True

    def recognize(self, png):
        self.calls += 1
        return OcrResult(self.text, [OcrBlock(self.text, 0.9, (0.1, 0.1, 0.5, 0.2))], "fake", 1)


def _png(w=120, h=40):
    img = Image.new("RGB", (w, h), (20, 20, 30))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def fake_grab(region: Region) -> Grab:
    return Grab(
        png=_png(region.width, region.height), width=region.width, height=region.height, scale=1.0
    )


def fake_displays():
    return [{"index": 0, "left": 0, "top": 0, "width": 1470, "height": 956}]


@pytest.fixture()
def capture_client(client):
    client.app.state.capture_grabber = fake_grab
    client.app.state.capture_displays = fake_displays
    client.app.state.ocr_provider = FakeProvider()
    return client


def test_registry_lists_and_rejects(capture_client):
    names = {p["name"] for p in capture_client.get("/api/capture/providers").json()}
    assert {"vision", "winocr", "rapidocr", "manual"} <= names
    with pytest.raises(ApiError) as exc:
        registry.get_provider("nope")
    assert exc.value.code == "ocr_unavailable"
    with pytest.raises(ApiError):
        registry.get_provider("manual")


def test_screenshot_and_ocr_by_path(capture_client, data_dir):
    r = capture_client.post("/api/capture/screenshot", json={"display": 0})
    assert r.status_code == 200
    body = r.json()
    assert body["width"] == 1470 and (data_dir / "media" / body["path"]).is_file()
    ocr = capture_client.post("/api/capture/ocr", json={"path": body["path"]}).json()
    assert ocr["text"] == "え、本当に？" and ocr["provider"] == "fake"
    assert capture_client.get(f"/media/{body['path']}").status_code == 200


def test_collect_creates_line_with_screenshot(capture_client, data_dir):
    src = capture_client.post("/api/sources", json={"title": "作品"}).json()
    ses = capture_client.post("/api/sessions", json={"source_id": src["id"]}).json()
    region = {"left": 10, "top": 20, "width": 300, "height": 80}
    r = capture_client.post(
        "/api/capture/collect", json={"region": region, "session_id": ses["id"]}
    )
    assert r.status_code == 200
    body = r.json()
    assert body["line"]["text"] == "え、本当に？" and body["line"]["origin"] == "ocr"
    assert body["line"]["screenshot_path"].startswith("screens/")
    assert (data_dir / "media" / body["line"]["screenshot_path"]).is_file()
    assert body["line"]["position"]["region"]["width"] == 300
    # active session is used when session_id is omitted; identical text is a duplicate
    again = capture_client.post("/api/capture/collect", json={"region": region}).json()
    assert again["duplicate"] is True and again["line"]["id"] == body["line"]["id"]


def test_hook_websocket_creates_line_and_broadcasts(capture_client):
    src = capture_client.post("/api/sources", json={"title": "作品"}).json()
    ses = capture_client.post("/api/sessions", json={"source_id": src["id"]}).json()
    with capture_client.websocket_connect("/ws/events") as events:
        with capture_client.websocket_connect("/ws/hook") as hook:
            hook.send_text("今日は俺が奢ってやるよ。")
            ack = hook.receive_json()
            assert ack["ok"] is True and ack["duplicate"] is False
            hook.send_text('{"text": "今日は俺が奢ってやるよ。", "speaker": "太郎"}')
            assert hook.receive_json()["duplicate"] is True
            hook.send_text("   ")
            assert hook.receive_json()["ok"] is False
        event = events.receive_json()
        assert event["type"] == "line.created" and event["line"]["origin"] == "hook"
    lines = capture_client.get("/api/lines", params={"session_id": ses["id"]}).json()
    assert len(lines) == 1 and lines[0]["text"] == "今日は俺が奢ってやるよ。"


@pytest.mark.skipif(sys.platform != "darwin", reason="Apple Vision only on macOS")
def test_vision_provider_reads_japanese_dialog():
    from kotoba.services.ocr.vision_macos import VisionProvider

    provider = VisionProvider()
    if not provider.available():
        pytest.skip("pyobjc Vision not installed")
    img = Image.new("RGB", (900, 120), (30, 30, 40))
    d = ImageDraw.Draw(img)
    font = ImageFont.truetype("/System/Library/Fonts/Hiragino Sans GB.ttc", 40)
    d.text((30, 30), "今日は俺が奢ってやるよ。", font=font, fill=(240, 240, 240))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    result = provider.recognize(buf.getvalue())
    assert "奢って" in result.text and result.blocks[0].confidence > 0.5
    x, y, w, h = result.blocks[0].box
    assert 0 <= x < 0.2 and 0 <= y < 0.6 and w > 0.3 and h > 0.1
