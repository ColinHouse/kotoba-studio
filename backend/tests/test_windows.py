import io
import json
import os

import pytest
from PIL import Image

from kotoba.core.errors import ApiError
from kotoba.services.capture import windows
from kotoba.services.capture.screen import Grab, Region
from kotoba.services.capture.watcher import RegionWatcher
from kotoba.services.ocr.base import OcrResult

MONITORS = [{"index": 0, "left": 0, "top": 0, "width": 1920, "height": 1080}]


class FakeProvider:
    name = "fake"

    def available(self):
        return True

    def recognize(self, png):
        return OcrResult("", [], "fake", 1)


def fake_grab(region: Region) -> Grab:
    buf = io.BytesIO()
    Image.new("RGB", (region.width, region.height), (20, 20, 30)).save(buf, format="PNG")
    return Grab(png=buf.getvalue(), width=region.width, height=region.height, scale=1.0)


@pytest.fixture()
def capture_client(client):
    client.app.state.capture_grabber = fake_grab
    client.app.state.capture_displays = lambda: MONITORS
    client.app.state.ocr_provider = FakeProvider()
    return client


def raw_window(**overrides):
    entry = {
        "handle": 1,
        "title": "PARQUET",
        "process": "PARQUET.exe",
        "pid": 4242,
        "left": 100,
        "top": 50,
        "width": 1280,
        "height": 720,
        "client_left": 108,
        "client_top": 78,
        "client_width": 1264,
        "client_height": 680,
    }
    entry.update(overrides)
    return entry


def window_info(**overrides):
    entry = raw_window(**overrides)
    return windows._window_info(entry, MONITORS)


def test_list_windows_filters_self_and_tiny_windows():
    raw = [
        raw_window(handle=1),
        raw_window(handle=2, pid=99, width=100, height=80, title="小窗"),
        raw_window(handle=3, title="其他", process="other.exe"),
    ]
    own = raw_window(handle=4, pid=os.getpid())
    listed = windows.list_windows(fetch=lambda: [*raw, own], displays_fn=lambda: MONITORS)
    assert [w.handle for w in listed] == [1, 3]  # biggest first, own/tiny dropped


def test_display_picks_the_monitor_with_the_largest_overlap():
    monitors = [
        {"index": 0, "left": 0, "top": 0, "width": 1000, "height": 1000},
        {"index": 1, "left": 1000, "top": 0, "width": 1000, "height": 1000},
    ]
    right = raw_window(handle=1, left=900, top=100, width=800, height=600)
    left = raw_window(handle=2, left=10, top=10, width=400, height=300)
    listed = windows.list_windows(fetch=lambda: [right, left], displays_fn=lambda: monitors)
    by_handle = {w.handle: w.display for w in listed}
    assert by_handle == {1: 1, 2: 0}


def test_find_window_matches_process_case_insensitively_and_prefers_title():
    raw = [
        raw_window(handle=1, title="PARQUET"),
        raw_window(handle=2, title="PARQUET - 设置"),
    ]
    found = windows.find_window(
        "parquet.exe", "PARQUET - 设置", fetch=lambda: raw, displays_fn=lambda: MONITORS
    )
    assert found is not None and found.handle == 2
    assert windows.find_window("nope.exe", fetch=lambda: raw, displays_fn=lambda: MONITORS) is None
    assert (
        windows.find_window("PARQUET.EXE", fetch=lambda: raw, displays_fn=lambda: MONITORS).handle
        == 1
    )


def test_relative_and_absolute_regions_round_trip():
    window = window_info()
    absolute = Region(
        left=window.client[0] + 120,
        top=window.client[1] + 80,
        width=400,
        height=160,
        display=window.display,
    )

    relative = windows.relative_from_region(absolute, window)
    assert relative is not None
    assert relative["unit"] == "ratio"
    assert relative["left"] == round(120 / window.client[2], 4)

    back = windows.region_for(window, relative)
    assert back is not None
    assert (back.left, back.top, back.width, back.height) == (
        absolute.left,
        absolute.top,
        absolute.width,
        absolute.height,
    )
    assert back.display == window.display


def test_default_region_is_a_fraction_of_the_client_area():
    window = window_info()
    default = windows.default_relative_region()
    region = windows.region_for(window, default)
    assert region is not None
    assert region.left == window.client[0] + round(default["left"] * window.client[2])
    assert region.width == round(default["width"] * window.client[2])


def test_resizing_the_window_keeps_the_same_relative_picture():
    """#124: a bound region is a fraction of the client area, so scaling the
    window scales the region instead of leaving it at the old pixels."""
    before = window_info()
    after = window_info(
        left=100,
        top=50,
        width=2560,
        height=1440,
        client_width=2528,
        client_height=1360,
    )
    absolute = Region(
        left=before.client[0] + 158,
        top=before.client[1] + 136,
        width=632,
        height=340,
        display=before.display,
    )
    relative = windows.relative_from_region(absolute, before)
    assert relative is not None

    resized = windows.region_for(after, relative)
    assert resized is not None
    assert resized.left - after.client[0] == round(relative["left"] * after.client[2])
    assert resized.top - after.client[1] == round(relative["top"] * after.client[3])
    assert resized.width == round(relative["width"] * after.client[2])
    assert resized.height == round(relative["height"] * after.client[3])
    assert (resized.width, resized.height) != (absolute.width, absolute.height)


def test_legacy_pixel_bindings_still_read_as_pixels():
    """Bindings stored before #124 carry no unit and must keep working."""
    window = window_info()
    region = windows.region_for(window, {"left": 10, "top": 20, "width": 300, "height": 100})
    assert region is not None
    assert (region.left, region.top, region.width, region.height) == (
        window.client[0] + 10,
        window.client[1] + 20,
        300,
        100,
    )


def test_region_for_clamps_to_the_client_area():
    window = window_info()
    region = windows.region_for(
        window, {"unit": "ratio", "left": 0.9, "top": 0.9, "width": 0.4, "height": 0.4}
    )
    assert region is not None
    assert region.width == window.client[2] - round(0.9 * window.client[2])
    assert region.height == window.client[3] - round(0.9 * window.client[3])
    assert (
        windows.region_for(
            window, {"unit": "ratio", "left": 1.2, "top": 0.2, "width": 0.1, "height": 0.1}
        )
        is None
    )


def test_resolve_region_prefers_the_live_window(db, client):
    from kotoba.models import Source

    src = Source(
        title="作品", region_json=json.dumps({"left": 1, "top": 2, "width": 30, "height": 40})
    )
    db.add(src)
    db.commit()
    src.window_json = json.dumps(
        {
            "process": "PARQUET.exe",
            "title": "PARQUET",
            "region": {"left": 10, "top": 20, "width": 300, "height": 100},
        }
    )
    db.commit()

    window = window_info()
    region = windows.resolve_region(db, src.id, finder=lambda *a, **k: window)
    assert (region.left, region.top, region.width, region.height) == (
        window.client[0] + 10,
        window.client[1] + 20,
        300,
        100,
    )

    db.refresh(src)
    assert windows.resolve_region(db, src.id, finder=lambda *a, **k: None) == Region(
        left=1, top=2, width=30, height=40
    )


def test_grab_from_window_is_none_off_windows(monkeypatch):
    monkeypatch.setattr(windows, "available", lambda: False)
    assert windows.grab_from_window(window_info()) is None


def test_collect_prefers_the_window_pixels(client, db, monkeypatch):
    from kotoba.services.capture import collect as collect_service
    from kotoba.services.ocr.base import OcrBlock, OcrResult

    class TextProvider:
        name = "fake"

        def recognize(self, png):
            return OcrResult("行けって", [OcrBlock("行けって", 1.0, (0, 0, 1, 1))], "fake", 1)

    window_shot = io.BytesIO()
    Image.new("RGB", (60, 20), (255, 0, 0)).save(window_shot, format="PNG")
    calls = {"window": 0, "screen": 0}

    def fake_window_grab(window, region):
        calls["window"] += 1
        return Grab(png=window_shot.getvalue(), width=60, height=20, scale=1.0)

    def fake_screen_grab(region):
        calls["screen"] += 1
        return fake_grab(region)

    monkeypatch.setattr(collect_service, "grab_from_window", fake_window_grab)
    payload = collect_service.collect(
        db,
        client.app.state.paths,
        None,
        Region(left=0, top=0, width=60, height=20),
        TextProvider(),
        grabber=fake_screen_grab,
        window=window_info(),
    )
    assert calls == {"window": 1, "screen": 0}
    assert payload["line"]["text"] == "行けって"


def test_collect_falls_back_to_the_screen_when_the_game_is_in_front(client, db, monkeypatch):
    """PrintWindow fails on plenty of real games; the screen is fine *if* they are visible."""
    from kotoba.services.capture import collect as collect_service

    class TextProvider:
        name = "fake"

        def recognize(self, png):
            return OcrResult("行けって", [], "fake", 1)

    calls = {"screen": 0}

    def fake_screen_grab(region):
        calls["screen"] += 1
        return fake_grab(region)

    monkeypatch.setattr(collect_service, "grab_from_window", lambda window, region: None)
    collect_service.collect(
        db,
        client.app.state.paths,
        None,
        Region(left=0, top=0, width=60, height=20),
        TextProvider(),
        grabber=fake_screen_grab,
        window=window_info(),
    )
    assert calls["screen"] == 1


def test_source_window_binding_round_trip(capture_client, monkeypatch):
    window = window_info()
    monkeypatch.setattr(windows, "available", lambda: True)
    monkeypatch.setattr(windows, "find_window", lambda *a, **k: window)

    src = capture_client.post("/api/sources", json={"title": "作品"}).json()
    bound = capture_client.patch(
        f"/api/sources/{src['id']}", json={"window": {"process": "PARQUET.exe", "title": "PARQUET"}}
    ).json()
    assert bound["window"]["process"] == "PARQUET.exe"
    assert bound["window"]["region"]["width"] > 0
    assert bound["window"]["region"]["left"] > 0

    region = {"left": 300, "top": 400, "width": 500, "height": 120}
    saved = capture_client.patch(f"/api/sources/{src['id']}", json={"region": region}).json()
    assert saved["region"] == region
    client = window.client
    assert saved["window"]["region"] == {
        "unit": "ratio",
        "left": round((300 - client[0]) / client[2], 4),
        "top": round((400 - client[1]) / client[3], 4),
        "width": round(500 / client[2], 4),
        "height": round(120 / client[3], 4),
    }

    cleared = capture_client.patch(f"/api/sources/{src['id']}", json={"window": None}).json()
    assert cleared["window"] is None and cleared["region"] == region


def test_list_game_windows_endpoint(capture_client, monkeypatch):
    monkeypatch.setattr(windows, "available", lambda: True)
    monkeypatch.setattr(windows, "list_windows", lambda: [window_info()])
    listed = capture_client.get("/api/capture/windows").json()
    assert listed[0]["process"] == "PARQUET.exe" and listed[0]["client"][2] == 1264


def test_watch_start_resolves_the_bound_window_each_cycle(capture_client, monkeypatch):
    window = window_info()
    monkeypatch.setattr(windows, "available", lambda: True)
    monkeypatch.setattr(windows, "find_window", lambda *a, **k: window)

    src = capture_client.post("/api/sources", json={"title": "作品"}).json()
    capture_client.patch(
        f"/api/sources/{src['id']}", json={"window": {"process": "PARQUET.exe", "title": "PARQUET"}}
    )
    capture_client.post(
        "/api/capture/watch/start",
        json={"region": {"left": 0, "top": 0, "width": 100, "height": 50}, "source_id": src["id"]},
    )
    watcher: RegionWatcher = capture_client.app.state.region_watcher
    try:
        resolved = watcher._region_provider()
        stored = capture_client.get(f"/api/sources/{src['id']}").json()
        relative = stored["window"]["region"]
        assert relative["unit"] == "ratio"
        assert resolved.left == window.client[0] + round(relative["left"] * window.client[2])
        assert resolved.top == window.client[1] + round(relative["top"] * window.client[3])
        assert (resolved.width, resolved.height) == (
            round(relative["width"] * window.client[2]),
            round(relative["height"] * window.client[3]),
        )

        # The watcher must read the game's own pixels, not whatever covers it.
        window_png = io.BytesIO()
        Image.new("RGB", (60, 20), (0, 255, 0)).save(window_png, format="PNG")
        monkeypatch.setattr(
            windows,
            "grab_from_window",
            lambda w, r: Grab(png=window_png.getvalue(), width=60, height=20, scale=1.0),
        )
        shot = watcher._grabber(resolved)
        assert (shot.width, shot.height) == (60, 20)
    finally:
        watcher.stop()


def _bound_source(db, client):
    from kotoba.models import Source

    source = Source(title="サクラノ詩", kind="visual_novel")
    source.window_json = json.dumps({"process": "sakura.exe", "title": "サクラノ詩"})
    db.add(source)
    db.commit()
    return source


def _collect_bound(client, db, source, monkeypatch, *, provider_text="行けって"):
    from kotoba.services.capture import collect as collect_service

    class TextProvider:
        name = "fake"

        def recognize(self, png):
            return OcrResult(provider_text, [], "fake", 1)

    calls = {"screen": 0}

    def fake_screen_grab(region):
        calls["screen"] += 1
        return fake_grab(region)

    payload = collect_service.collect(
        db,
        client.app.state.paths,
        None,
        Region(left=0, top=0, width=60, height=20),
        TextProvider(),
        grabber=fake_screen_grab,
        source_id=source.id,
    )
    return payload, calls


def test_collect_refuses_while_the_bound_game_is_behind_another_window(client, db, monkeypatch):
    """Capturing the window on top would put Discord's text in the user's deck."""
    source = _bound_source(db, client)
    monkeypatch.setattr(windows, "available", lambda: True)
    monkeypatch.setattr(windows, "find_window", lambda *a, **k: window_info())
    monkeypatch.setattr(windows, "is_foreground", lambda win: False)

    with pytest.raises(ApiError) as err:
        _collect_bound(client, db, source, monkeypatch)

    assert err.value.code == "capture_blocked"
    assert client.get("/api/lines").json() == []


def test_collect_refuses_when_the_bound_game_has_closed(client, db, monkeypatch):
    source = _bound_source(db, client)
    monkeypatch.setattr(windows, "available", lambda: True)
    monkeypatch.setattr(windows, "find_window", lambda *a, **k: None)

    with pytest.raises(ApiError) as err:
        _collect_bound(client, db, source, monkeypatch)

    assert err.value.code == "capture_blocked"
    assert client.get("/api/lines").json() == []


def test_collect_proceeds_when_the_bound_game_is_in_front(client, db, monkeypatch):
    """The whole point: the game that fails PrintWindow must still be capturable."""
    from kotoba.services.capture import collect as collect_service

    source = _bound_source(db, client)
    monkeypatch.setattr(windows, "available", lambda: True)
    monkeypatch.setattr(windows, "find_window", lambda *a, **k: window_info())
    monkeypatch.setattr(windows, "is_foreground", lambda win: True)
    monkeypatch.setattr(collect_service, "grab_from_window", lambda win, region: None)

    payload, calls = _collect_bound(client, db, source, monkeypatch)

    assert calls["screen"] == 1
    assert payload["line"]["text"] == "行けって"


def test_collect_without_a_binding_is_unchanged(client, db, monkeypatch):
    """No window identity (every macOS user, and anyone who never bound one)."""
    from kotoba.models import Source

    source = Source(title="unbound", kind="anime")
    db.add(source)
    db.commit()
    monkeypatch.setattr(windows, "available", lambda: True)

    payload, calls = _collect_bound(client, db, source, monkeypatch)

    assert calls["screen"] == 1
    assert payload["line"]["text"] == "行けって"
