import io
import sys
from pathlib import Path

import pytest
from PIL import Image, ImageDraw, ImageFont

from kotoba.core.errors import ApiError
from kotoba.services.capture.screen import Grab, Region
from kotoba.services.ocr import registry
from kotoba.services.ocr.base import OcrBlock, OcrResult, join_words


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


@pytest.mark.parametrize("preference", ["hook", "ocr"])
def test_both_text_routes_stay_available_under_either_preference(capture_client, preference):
    """The preference only orders the recommendation; it must never be a switch."""
    capture_client.put("/api/settings", json={"preferred_text_source": preference})
    src = capture_client.post("/api/sources", json={"title": "作品"}).json()
    ses = capture_client.post("/api/sessions", json={"source_id": src["id"]}).json()
    region = {"left": 10, "top": 20, "width": 300, "height": 80}

    body = capture_client.post(
        "/api/capture/collect", json={"region": region, "session_id": ses["id"]}
    ).json()
    assert body["line"]["origin"] == "ocr"

    with capture_client.websocket_connect("/ws/hook") as hook:
        hook.send_text("今日は俺が奢ってやるよ。")
        assert hook.receive_json()["ok"] is True
    origins = {line["origin"] for line in capture_client.get("/api/lines").json()}
    assert {"ocr", "hook"} <= origins


def test_collect_repairs_kana_the_dictionary_knows(capture_client, jmdict_fixture):
    capture_client.app.state.ocr_provider = FakeProvider("てかみ")
    src = capture_client.post("/api/sources", json={"title": "作品"}).json()
    ses = capture_client.post("/api/sessions", json={"source_id": src["id"]}).json()
    region = {"left": 10, "top": 20, "width": 300, "height": 80}
    body = capture_client.post(
        "/api/capture/collect", json={"region": region, "session_id": ses["id"]}
    ).json()
    assert body["line"]["text"] == "てがみ"
    # The engine's original reading stays for audit.
    assert body["line"]["raw_text"] == "てかみ"


def test_hook_text_is_never_repaired(capture_client, jmdict_fixture):
    with capture_client.websocket_connect("/ws/hook") as hook:
        hook.send_text("てかみ")
        assert hook.receive_json()["ok"] is True
    lines = capture_client.get("/api/lines").json()
    assert [line["text"] for line in lines] == ["てかみ"]


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


def test_ocr_compare_runs_available_providers_and_isolates_failures(capture_client, monkeypatch):
    class FailingProvider:
        name = "boom"
        note = "test"

        def available(self):
            return True

        def recognize(self, png):
            raise ApiError("ocr_failed", "引擎崩了")

    class UnavailableProvider:
        name = "off"
        note = "test"

        def available(self):
            return False

        def recognize(self, png):
            raise AssertionError("unavailable provider must not run")

    monkeypatch.setattr(
        registry,
        "PROVIDERS",
        {"good": FakeProvider, "boom": FailingProvider, "off": UnavailableProvider},
    )
    region = {"left": 0, "top": 0, "width": 120, "height": 40}
    rows = capture_client.post("/api/capture/ocr/compare", json={"region": region}).json()
    assert [row["provider"] for row in rows] == ["good", "boom"]
    assert rows[0]["text"] == "え、本当に？"
    assert rows[0]["error"] is None and rows[0]["ms"] >= 0
    assert rows[1]["text"] == "" and rows[1]["error"] == "引擎崩了"


def test_ocr_compare_requires_a_region_or_path(capture_client):
    r = capture_client.post("/api/capture/ocr/compare", json={})
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "validation_error"


@pytest.mark.skipif(sys.platform != "darwin", reason="Apple Vision only on macOS")
def test_vision_provider_reads_japanese_dialog():
    from kotoba.services.ocr.providers.vision_macos import VisionProvider

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


def test_join_words_keeps_cjk_tight_and_latin_spaced():
    assert join_words(["奢", "っ", "て", "やる", "よ", "。"]) == "奢ってやるよ。"
    assert join_words(["I", "love", "you"]) == "I love you"
    assert join_words(["iPod", "を", "買った"]) == "iPodを買った"


@pytest.mark.skipif(sys.platform != "win32", reason="Windows OCR only on Windows")
def test_windows_ocr_provider_reads_japanese_dialog():
    from kotoba.services.ocr.providers.windows_ocr import WindowsOcrProvider

    provider = WindowsOcrProvider()
    if not provider.available():
        pytest.skip("winocr or the Windows Japanese OCR language pack is missing")
    font_path = next(
        (
            p
            for p in ("C:/Windows/Fonts/meiryo.ttc", "C:/Windows/Fonts/YuGothR.ttc")
            if Path(p).is_file()
        ),
        None,
    )
    if font_path is None:
        pytest.skip("no Japanese font installed")
    img = Image.new("RGB", (900, 120), (30, 30, 40))
    d = ImageDraw.Draw(img)
    d.text(
        (30, 30),
        "今日は俺が奢ってやるよ。",
        font=ImageFont.truetype(font_path, 40),
        fill=(240, 240, 240),
    )
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    result = provider.recognize(buf.getvalue())
    assert result.provider == "winocr"
    # The engine joins its words with spaces; the provider must have undone that.
    assert "奢って" in result.text and " " not in result.text
    x, y, w, h = result.blocks[0].box
    assert 0 <= x < 0.2 and 0 <= y < 0.6 and w > 0.3 and h > 0.1


def test_hook_websocket_is_silenced_while_a_restore_holds_the_gate(capture_client):
    """/ws/hook is a live capture source and must respect the same gate as the rest.

    A hook tool is a program: it has to be told the line was dropped, or it will
    believe a silent success and move on.
    """
    from kotoba.services.capture.gate import gate

    with capture_client.websocket_connect("/ws/hook") as hook:
        gate.pause()
        try:
            hook.send_text("閉じている間の台詞。")
            assert hook.receive_json() == {"ok": False, "error": "paused"}
        finally:
            gate.resume()
        hook.send_text("開いてからの台詞。")
        assert hook.receive_json()["ok"] is True

    texts = {line["text"] for line in capture_client.get("/api/lines").json()}
    assert "閉じている間の台詞。" not in texts
    assert "開いてからの台詞。" in texts


def test_hook_websocket_resolves_the_database_per_message(capture_client):
    """A Textractor connection stays open all evening and restore replaces app.state.db.

    Asserted structurally rather than by data: SQLite reconnects a disposed engine to
    the same path, so a captured handle still writes the row here — the real damage is
    a connection held open across the file swap, which does not reproduce on macOS.
    Counting resolutions is what actually distinguishes the two implementations.
    """

    class CountingDatabase:
        def __init__(self, inner):
            self._inner = inner
            self.resolved = 0

        def session(self):
            self.resolved += 1
            return self._inner.session()

        def __getattr__(self, name):
            return getattr(self._inner, name)

    with capture_client.websocket_connect("/ws/hook") as hook:
        counting = CountingDatabase(capture_client.app.state.db)
        capture_client.app.state.db = counting
        try:
            hook.send_text("一言目。")
            assert hook.receive_json()["ok"] is True
            hook.send_text("二言目。")
            assert hook.receive_json()["ok"] is True
        finally:
            capture_client.app.state.db = counting._inner

    # Captured once at connect time this is 0; resolved per message it is 2.
    assert counting.resolved == 2
