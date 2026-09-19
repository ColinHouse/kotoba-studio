import threading

import pytest

from kotoba.services.capture.screen import Region
from kotoba.services.overlay import (
    OverlayController,
    OverlayWord,
    TkOverlay,
    apply_user_position,
    latest_line,
    overlay_position,
    overlay_words,
    save_word,
)


def analysis_result():
    return {
        "tokens": [
            {
                "surface": "今日",
                "base": "今日",
                "reading": "きょう",
                "is_content": True,
                "start": 0,
                "end": 2,
                "known_status": "known",
                "term_id": 7,
                "candidates": [
                    {
                        "headword": "今日",
                        "reading": "きょう",
                        "senses": [{"gloss_zh": ["今天"], "gloss_en": ["today"]}],
                    }
                ],
            },
            {
                "surface": "は",
                "base": "は",
                "reading": "は",
                "is_content": False,
                "start": 2,
                "end": 3,
                "known_status": None,
                "term_id": None,
                "candidates": [],
            },
            {
                "surface": "奢っ",
                "base": "奢る",
                "reading": "おごる",
                "is_content": True,
                "start": 4,
                "end": 6,
                "known_status": None,
                "term_id": None,
                "candidates": [
                    {
                        "headword": "奢る",
                        "reading": "おごる",
                        "senses": [{"gloss_en": ["to treat"]}],
                    },
                    {"headword": "奢る", "reading": "おごる", "senses": [{"gloss_zh": ["请客"]}]},
                ],
            },
        ]
    }


def test_overlay_words_condenses_candidates_and_state():
    words = overlay_words(analysis_result())
    assert [w.surface for w in words] == ["今日", "は", "奢っ"]
    assert words[0].known is True and words[0].term_id == 7
    assert words[0].meanings == ["今日｜今天"]
    assert words[1].content is False and words[1].meanings == []
    assert words[2].headword == "奢る" and words[2].reading == "おごる"
    assert words[2].meanings == ["奢る｜to treat", "奢る｜请客"]
    assert (words[2].start, words[2].end) == (4, 6)


def test_overlay_position_sits_above_the_dialogue_box():
    region = Region(left=300, top=700, width=800, height=160)
    x, y = overlay_position(region, (600, 200), (1920, 1080))
    assert (x, y) == (300, 700 - 200 - 14)


def test_overlay_position_falls_below_when_there_is_no_room():
    region = Region(left=300, top=50, width=800, height=160)
    x, y = overlay_position(region, (600, 200), (1920, 1080))
    assert y == 50 + 160 + 14
    assert x == 300


def test_overlay_position_clamps_and_centers_without_a_region():
    x, y = overlay_position(None, (600, 200), (1000, 800))
    assert 0 <= x <= 400 and 0 <= y <= 600
    x, y = overlay_position(
        Region(left=950, top=900, width=300, height=100), (600, 200), (1000, 800)
    )
    assert x == 400 and y == 600


def test_latest_line_and_save_word(client, db):
    from sqlalchemy import func, select

    from kotoba.models import Encounter

    src = client.post("/api/sources", json={"title": "覆盖层"}).json()
    ses = client.post("/api/sessions", json={"source_id": src["id"], "mode": "companion"}).json()
    first = client.post(
        "/api/lines", json={"session_id": ses["id"], "text": "最初の行", "origin": "manual"}
    ).json()["line"]
    second = client.post(
        "/api/lines",
        json={"session_id": ses["id"], "text": "今日は俺が奢ってやるよ。", "origin": "manual"},
    ).json()["line"]

    assert latest_line(db, ses["id"]).id == second["id"]
    assert latest_line(db, None) is None

    word = OverlayWord(
        surface="奢っ",
        headword="奢る",
        reading="おごる",
        start=4,
        end=6,
        content=True,
        term_id=None,
        known=False,
        meanings=[],
    )
    saved = save_word(db, latest_line(db, ses["id"]), word)
    assert saved["encounter_id"] and saved["term_id"]
    count = db.scalar(select(func.count(Encounter.id)).where(Encounter.line_id == second["id"]))
    assert count == 1
    assert first["id"] != second["id"]


class FakeView:
    def __init__(self, snapshot, save, position, load_position, store_position):
        self.snapshot = snapshot
        self.save = save
        self.position = position
        self.load_position = load_position
        self.store_position = store_position
        self.commands: list[str] = []
        self.running = threading.Event()
        self.done = threading.Event()

    def run(self):
        self.running.set()
        self.done.wait(3)

    def command(self, name):
        self.commands.append(name)
        if name == "quit":
            self.done.set()

    @property
    def visible(self):
        return "show" in self.commands and self.commands[-1] != "hide"


def test_controller_starts_toggles_and_stops(client, monkeypatch):
    ctrl = OverlayController(lambda: client.app.state.db.session(), view_factory=FakeView)
    monkeypatch.setattr(ctrl, "available", lambda: (True, None))

    assert ctrl.start() is True
    view = ctrl._view
    assert view.running.wait(2.0)
    assert ctrl.running is True
    assert view.commands == ["show"]  # enabling shows the panel; the hotkey hides it

    ctrl.toggle()
    ctrl.hide()
    assert view.commands == ["show", "toggle", "hide"]

    ctrl.stop()
    assert ctrl.running is False
    assert view.commands[-1] == "quit"


def test_controller_reports_unavailable(client, monkeypatch):
    ctrl = OverlayController(lambda: client.app.state.db.session(), view_factory=FakeView)
    monkeypatch.setattr(ctrl, "available", lambda: (False, "覆盖层目前只支持 Windows"))
    assert ctrl.start() is False
    assert ctrl.last_error == "覆盖层目前只支持 Windows"
    assert ctrl.status()["running"] is False


def test_controller_callbacks_read_the_active_session(client, monkeypatch):
    ctrl = OverlayController(lambda: client.app.state.db.session())
    monkeypatch.setattr(ctrl, "available", lambda: (True, None))

    src = client.post("/api/sources", json={"title": "覆盖层回调"}).json()
    ses = client.post("/api/sessions", json={"source_id": src["id"], "mode": "companion"}).json()
    client.put("/api/settings", json={"active_session_id": ses["id"]})
    client.post(
        "/api/lines",
        json={"session_id": ses["id"], "text": "今日は俺が奢ってやるよ。", "origin": "manual"},
    )

    snapshot = ctrl._snapshot()
    assert snapshot is not None
    line_text, words = snapshot
    assert line_text.startswith("今日")
    assert any(w.surface == "奢っ" for w in words)

    target = next(w for w in words if w.surface == "奢っ")
    saved = ctrl._save(target)
    assert saved["encounter_id"]

    position = ctrl._position((600, 200))
    assert len(position) == 3 and position[2] >= 520


def _active_session(client, *, source: str | None = "覆盖层位置") -> dict:
    body: dict = {}
    if source is not None:
        src = client.post("/api/sources", json={"title": source}).json()
        body["source_id"] = src["id"]
    ses = client.post("/api/sessions", json=body).json()
    client.put("/api/settings", json={"active_session_id": ses["id"]})
    return ses


def test_a_dragged_position_round_trips_per_work(client):
    ctrl = OverlayController(lambda: client.app.state.db.session())
    _active_session(client)

    assert ctrl._load_position() is None
    ctrl._store_position((640, 320))
    assert ctrl._load_position() == (640, 320)
    # A restart is a fresh controller reading the same work.
    assert OverlayController(lambda: client.app.state.db.session())._load_position() == (640, 320)
    # The global fallback is for sessions without a work and stays untouched.
    assert client.get("/api/settings").json()["overlay_position"] is None


def test_reset_clears_the_stored_position(client):
    ctrl = OverlayController(lambda: client.app.state.db.session())
    _active_session(client)

    ctrl._store_position((640, 320))
    ctrl._store_position(None)
    assert ctrl._load_position() is None


def test_each_work_keeps_its_own_position(client):
    ctrl = OverlayController(lambda: client.app.state.db.session())
    first = _active_session(client, source="作品 A")
    ctrl._store_position((10, 20))
    _active_session(client, source="作品 B")

    assert ctrl._load_position() is None  # B has its own, still empty, record
    ctrl._store_position((99, 88))

    client.put("/api/settings", json={"active_session_id": first["id"]})
    assert ctrl._load_position() == (10, 20)


def test_sessions_without_a_work_share_one_global_position(client):
    ctrl = OverlayController(lambda: client.app.state.db.session())
    _active_session(client, source=None)

    assert ctrl._load_position() is None
    ctrl._store_position((15, 25))
    assert ctrl._load_position() == (15, 25)
    assert client.get("/api/settings").json()["overlay_position"] == {"x": 15, "y": 25}


def test_a_saved_position_comes_back_clamped_on_a_smaller_screen(client):
    """Criterion: the read path runs through apply_user_position()."""
    ctrl = OverlayController(lambda: client.app.state.db.session())
    _active_session(client)

    ctrl._store_position((5000, 5000))  # saved while the screen was much larger
    loaded = ctrl._load_position()
    assert apply_user_position(loaded, (0, 0), (520, 160), (1920, 1080)) == (1400, 920)


def test_the_view_reports_its_rect_only_while_visible():
    view = TkOverlay(lambda: None, lambda word: {}, lambda size: (0, 0, 520))
    view._screen_rect = (10, 20, 300, 100)

    assert view.screen_rect() is None  # hidden: nothing to mask
    view._visible = True
    assert view.screen_rect() == (10, 20, 300, 100)


def test_the_controller_hands_out_the_view_rect():
    ctrl = OverlayController(lambda: None)
    assert ctrl.screen_rect() is None

    class View:
        def screen_rect(self):
            return (1, 2, 3, 4)

    ctrl._view = View()
    assert ctrl.screen_rect() == (1, 2, 3, 4)


def test_release_saves_the_dragged_spot_and_reset_clears_it():
    stored: list[tuple[int, int] | None] = []
    view = TkOverlay(
        lambda: None,
        lambda word: {},
        lambda size: (0, 0, 520),
        lambda: None,
        stored.append,
    )
    view._refresh = lambda: None  # no Tk widgets in this test

    view._user_position = (12, 34)
    view._drag_end()
    view._drag_reset()
    assert stored == [(12, 34), None]


def test_a_click_that_moved_nothing_saves_nothing():
    stored: list[tuple[int, int] | None] = []
    view = TkOverlay(
        lambda: None,
        lambda word: {},
        lambda size: (0, 0, 520),
        lambda: None,
        stored.append,
    )

    view._user_position = None
    view._drag_end()
    assert stored == []


class FakeRoot:
    """Stands in for the Tk root so the tick loop can be tested without a display."""

    def __init__(self) -> None:
        self.destroyed = False
        self.after_calls = 0

    def destroy(self) -> None:
        self.destroyed = True

    def after(self, *_args) -> str:
        self.after_calls += 1
        return "after#1"


def test_quit_stops_the_tick_loop_before_it_refreshes():
    view = TkOverlay(lambda: None, lambda word: {}, lambda size: (0, 0, 520))
    root = FakeRoot()
    view._root = root
    view._visible = True

    view.command("quit")
    view._tick()

    assert root.destroyed is True
    assert view._root is None
    assert view.last_error is None
    assert root.after_calls == 0


def test_overlay_endpoints_report_status(client, monkeypatch):
    ctrl = OverlayController(lambda: client.app.state.db.session(), view_factory=FakeView)
    monkeypatch.setattr(ctrl, "available", lambda: (False, "test-only"))
    client.app.state.overlay = ctrl

    status = client.get("/api/overlay/status").json()
    assert set(status) >= {"available", "running", "visible", "hotkey", "hotkey_running"}
    started = client.post("/api/overlay/start").json()
    assert started["running"] is False
    assert started["note"] == "test-only"
    client.post("/api/overlay/toggle")
    stopped = client.post("/api/overlay/stop").json()
    assert stopped["running"] is False


def test_settings_validate_the_overlay_hotkey(client):
    bad = client.put("/api/settings", json={"overlay_hotkey": "Ctrl+Oops"})
    assert bad.status_code == 400
    assert bad.json()["error"]["code"] == "invalid_value"
    assert client.get("/api/settings").json()["overlay_hotkey"] == "Ctrl+Shift+O"


def test_settings_validate_the_overlay_position(client):
    bad = client.put("/api/settings", json={"overlay_position": {"x": "left", "y": 0}})
    assert bad.status_code == 400
    assert bad.json()["error"]["code"] == "invalid_value"
    ok = client.put("/api/settings", json={"overlay_position": {"x": 10, "y": 20}})
    assert ok.json()["overlay_position"] == {"x": 10, "y": 20}
    cleared = client.put("/api/settings", json={"overlay_position": None})
    assert cleared.json()["overlay_position"] is None


@pytest.mark.parametrize("platform", ["linux", "darwin"])
def test_overlay_is_windows_only(monkeypatch, platform):
    import sys

    from kotoba.services import overlay

    monkeypatch.setattr(sys, "platform", platform)
    ok, note = overlay.OverlayController(lambda: None).available()
    assert ok is False and note


def test_a_dragged_position_wins_over_the_computed_one():
    """Otherwise the next line snaps the panel back: _position() runs every refresh."""
    auto = (100, 200)
    assert apply_user_position(None, auto, (520, 160), (1920, 1080)) == auto
    assert apply_user_position((40, 60), auto, (520, 160), (1920, 1080)) == (40, 60)


def test_a_dragged_position_is_kept_on_screen():
    """Dragged half off the edge, or the same spot after the resolution changed."""
    size, screen = (520, 160), (1920, 1080)
    assert apply_user_position((5000, 5000), (0, 0), size, screen) == (1400, 920)
    assert apply_user_position((-80, -30), (0, 0), size, screen) == (0, 0)


def test_a_panel_wider_than_the_screen_still_lands_at_the_origin():
    assert apply_user_position((300, 300), (0, 0), (2400, 1400), (1920, 1080)) == (0, 0)
