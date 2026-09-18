import io
import itertools
import json
import threading
import time
import zipfile

import httpx
import pytest
from PIL import Image

from kotoba.services import backup as backup_service
from kotoba.services.capture.clipboard import ClipboardWatcher
from kotoba.services.capture.gate import CaptureGate, gate
from kotoba.services.export.anki_connect import AnkiConnect


@pytest.fixture(autouse=True)
def _always_resume_capture():
    yield
    gate.resume()


def wait_for(predicate, timeout: float = 5.0) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return True
        time.sleep(0.01)
    return predicate()


def _png():
    buf = io.BytesIO()
    Image.new("RGB", (64, 32), (200, 100, 50)).save(buf, format="PNG")
    return buf.getvalue()


def _seed(client, data_dir):
    src = client.post("/api/sources", json={"title": "Summer Pockets"}).json()
    ses = client.post("/api/sessions", json={"source_id": src["id"]}).json()
    shot_dir = data_dir / "media" / "screens" / "20260916"
    shot_dir.mkdir(parents=True)
    (shot_dir / "a.png").write_bytes(_png())
    text = "今日は俺が奢ってやるよ。"
    line = client.post(
        "/api/lines",
        json={"session_id": ses["id"], "text": text, "screenshot_path": "screens/20260916/a.png"},
    ).json()["line"]
    client.patch(f"/api/lines/{line['id']}", json={"translation_zh": "今天我请客。"})
    enc = client.post(
        "/api/encounters",
        json={
            "line_id": line["id"],
            "headword": "奢る",
            "reading": "おごる",
            "surface": "奢っ",
            "span_start": text.index("奢っ"),
            "span_end": text.index("奢っ") + 2,
            "sense": {"gloss_zh": "请客", "gloss_en": "to treat"},
            "card_types": ["reading", "cloze"],
        },
    ).json()
    client.patch(
        f"/api/encounters/{enc['encounter']['id']}",
        json={"ai_explanation": {"meaning_here": "我请客", "tone": "随意"}},
    )
    line2 = client.post("/api/lines", json={"session_id": ses["id"], "text": "猫が好き。"}).json()[
        "line"
    ]
    client.post(
        "/api/encounters",
        json={
            "line_id": line2["id"],
            "headword": "猫",
            "reading": "ねこ",
            "surface": "猫",
            "card_types": ["reading"],
        },
    )
    return enc


def test_capture_gate_waits_for_the_in_flight_write_and_skips_new_ones():
    gate = CaptureGate()
    entered, release, finished = threading.Event(), threading.Event(), threading.Event()

    def writer():
        with gate.ingest() as allowed:
            assert allowed
            entered.set()
            release.wait(2)
        finished.set()

    thread = threading.Thread(target=writer, daemon=True)
    thread.start()
    assert entered.wait(2)

    pauser = threading.Thread(target=gate.pause, daemon=True)
    pauser.start()
    time.sleep(0.05)
    assert pauser.is_alive()  # pause is waiting for the write, not killing it
    release.set()
    thread.join(2)
    pauser.join(2)
    assert finished.is_set() and not pauser.is_alive()

    with gate.ingest() as allowed:
        assert allowed is False  # a new write is skipped while paused
    gate.resume()
    with gate.ingest() as allowed:
        assert allowed is True


def test_restore_pauses_a_running_capture_source(client, data_dir, monkeypatch):
    _seed(client, data_dir)
    name = client.post("/api/backups").json()["name"]

    counter = itertools.count(1)
    watcher = ClipboardWatcher(
        lambda: client.app.state.db.session(),
        read=lambda: f"恢复期间的台词{next(counter)}",
        interval=0.01,
    )
    client.app.state.clipboard_watcher = watcher
    watcher.start()
    assert wait_for(lambda: watcher.captured >= 1)

    state = {"captured_at_pause": 0}
    real_restore = backup_service.restore

    def slow_restore(paths, backup_name):
        # By now the endpoint has closed the gate; the watcher keeps polling in
        # this window and none of those lines may reach the database.
        state["captured_at_pause"] = watcher.captured
        deadline = time.monotonic() + 1.0
        while time.monotonic() < deadline:
            time.sleep(0.02)
        assert watcher.captured == state["captured_at_pause"]
        return real_restore(paths, backup_name)

    monkeypatch.setattr(backup_service, "restore", slow_restore)
    r = client.post("/api/backups/restore", json={"name": name})
    assert r.status_code == 200 and r.json()["snapshot"].startswith("pre-restore")

    assert watcher.running is True  # it was running and it stays running
    assert wait_for(lambda: watcher.captured > state["captured_at_pause"])
    watcher.stop()


def test_restore_failure_still_releases_the_capture_gate(client, data_dir):
    _seed(client, data_dir)
    counter = itertools.count(1)
    watcher = ClipboardWatcher(
        lambda: client.app.state.db.session(),
        read=lambda: f"失败之后的台词{next(counter)}",
        interval=0.01,
    )
    client.app.state.clipboard_watcher = watcher
    watcher.start()
    assert wait_for(lambda: watcher.captured >= 1)

    r = client.post("/api/backups/restore", json={"name": "missing.zip"})
    assert r.status_code == 404

    captured_before = watcher.captured
    assert wait_for(lambda: watcher.captured > captured_before)
    watcher.stop()


def test_apkg_export_contains_media_and_fields(client, data_dir):
    _seed(client, data_dir)
    r = client.post("/api/export/apkg", json={})
    assert r.status_code == 200 and r.headers["content-disposition"].endswith('.apkg"')
    assert len(r.content) > 1000
    with zipfile.ZipFile(io.BytesIO(r.content)) as zf:
        names = zf.namelist()
        assert any(n.startswith("collection.anki") for n in names)
        media = json.loads(zf.read("media"))
        assert any(v.endswith("a.png") for v in media.values())
    only_cat = client.get("/api/terms", params={"q": "猫"}).json()[0]
    cards = client.get("/api/cards", params={"term_id": only_cat["id"]}).json()
    assert client.post("/api/export/apkg", json={"card_ids": [cards[0]["id"]]}).status_code == 200
    assert (
        client.post("/api/export/apkg", json={"card_ids": [999999]}).json()["error"]["code"]
        == "nothing_to_export"
    )


def test_anki_connect_export_flow(client, data_dir):
    _seed(client, data_dir)
    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        calls.append(body["action"])
        action = body["action"]
        if action == "version":
            return httpx.Response(200, json={"result": 6, "error": None})
        if action == "deckNames":
            return httpx.Response(200, json={"result": ["Default"], "error": None})
        if action == "modelNames":
            return httpx.Response(200, json={"result": [], "error": None})
        if action in ("createDeck", "createModel", "storeMediaFile"):
            return httpx.Response(200, json={"result": None, "error": None})
        if action == "addNote":
            word = body["params"]["note"]["fields"]["Word"]
            if word == "猫":
                return httpx.Response(
                    200,
                    json={"result": None, "error": "cannot create note because it is a duplicate"},
                )
            fields = body["params"]["note"]["fields"]
            assert fields["Sentence"] == "今日は俺が<b>奢っ</b>てやるよ。"
            assert fields["Meaning"] == "请客" and fields["Translation"] == "今天我请客。"
            assert (
                fields["Image"].startswith("<img src=") and "这句里的意思" in fields["Explanation"]
            )
            assert body["params"]["note"]["modelName"] == "KotobaStudio-v1"
            return httpx.Response(200, json={"result": 1500000000001, "error": None})
        return httpx.Response(200, json={"result": None, "error": f"unknown {action}"})

    client.app.state.anki_transport = httpx.MockTransport(handler)
    r = client.post("/api/export/anki-connect", json={"deck": "日语"})
    assert r.status_code == 200, r.text
    body = r.json()
    assert [a["word"] for a in body["added"]] == ["奢る"] and body["skipped"] == ["猫"]
    assert (
        calls[:4] == ["version", "deckNames", "createDeck", "modelNames"] and "createModel" in calls
    )
    assert "storeMediaFile" in calls


def test_anki_connect_unreachable():
    def handler(request):
        raise httpx.ConnectError("refused")

    ac = AnkiConnect(transport=httpx.MockTransport(handler))
    try:
        ac.version()
    except Exception as exc:  # noqa: BLE001
        assert getattr(exc, "code", None) == "anki_unreachable"
    else:
        raise AssertionError("expected anki_unreachable")


def test_json_export(client, data_dir):
    _seed(client, data_dir)
    body = client.get("/api/export/json").json()
    assert body["app"] == "kotobako"
    assert len(body["terms"]) == 2 and len(body["lines"]) == 2 and len(body["cards"]) == 3


def test_backup_roundtrip(client, data_dir):
    _seed(client, data_dir)
    r = client.post("/api/backups")
    assert r.status_code == 201
    name = r.json()["name"]
    with zipfile.ZipFile(data_dir / "backups" / name) as zf:
        names = zf.namelist()
        assert "kotoba.db" in names and "media/screens/20260916/a.png" in names
    assert client.get("/api/backups").json()[0]["name"] == name

    # destroy data, then restore
    ogoru = client.get("/api/terms", params={"q": "奢"}).json()[0]
    cat_line = next(ln for ln in client.get("/api/lines").json() if ln["text"] == "猫が好き。")
    assert (
        client.delete(f"/api/lines/{cat_line['id']}").status_code == 204
    )  # cascades to encounters
    assert client.get("/api/terms", params={"q": "猫"}).json()[0]["encounter_count"] == 0
    client.patch(f"/api/terms/{ogoru['id']}", json={"known_status": "ignored"})
    (data_dir / "media" / "screens" / "20260916" / "a.png").unlink()
    r = client.post("/api/backups/restore", json={"name": name})
    assert r.status_code == 200 and r.json()["snapshot"].startswith("pre-restore")
    assert client.get(f"/api/terms/{ogoru['id']}").json()["known_status"] == "learning"
    assert (data_dir / "media" / "screens" / "20260916" / "a.png").is_file()
    assert len(client.get("/api/backups").json()) == 2
    assert client.post("/api/backups/restore", json={"name": "../evil.zip"}).status_code == 400
    assert client.post("/api/backups/restore", json={"name": "missing.zip"}).status_code == 404


def _tampered_backup(client, data_dir, member: str) -> str:
    """A real backup with one extra member whose path points outside media/."""
    name = client.post("/api/backups").json()["name"]
    source = data_dir / "backups" / name
    with zipfile.ZipFile(source) as zf:
        entries = [(info, zf.read(info.filename)) for info in zf.infolist()]
    with zipfile.ZipFile(source, "w") as zf:
        for info, payload in entries:
            zf.writestr(info, payload)
        zf.writestr(member, b"payload")
    return name


def test_restore_refuses_a_member_that_escapes_the_media_directory(client, data_dir):
    """A backup is a file users carry between machines, so its paths are untrusted."""
    _seed(client, data_dir)
    name = _tampered_backup(client, data_dir, "media/../../escaped.txt")
    term = client.get("/api/terms", params={"q": "奢"}).json()[0]
    client.patch(f"/api/terms/{term['id']}", json={"known_status": "ignored"})

    response = client.post("/api/backups/restore", json={"name": name})

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "invalid_backup"
    assert not (data_dir.parent / "escaped.txt").exists()
    # Refused before anything was replaced: a half-restored database is worse than none.
    # The pre-restore snapshot is only taken once the paths check out, so its absence
    # says the refusal happened first, and the edit above survives untouched.
    assert not list((data_dir / "backups").glob("pre-restore-*.zip"))
    assert client.get(f"/api/terms/{term['id']}").json()["known_status"] == "ignored"


def test_restore_refuses_an_absolute_member_path(client, data_dir, tmp_path):
    _seed(client, data_dir)
    target = tmp_path / "absolute.txt"
    name = _tampered_backup(client, data_dir, f"media/{target}")

    response = client.post("/api/backups/restore", json={"name": name})

    assert response.status_code == 400
    assert not target.exists()


def test_restore_still_accepts_an_ordinary_nested_member(client, data_dir):
    """The guard must not reject the deep paths a real backup is full of."""
    _seed(client, data_dir)
    name = _tampered_backup(client, data_dir, "media/screens/20260916/nested/ok.png")
    assert client.post("/api/backups/restore", json={"name": name}).status_code == 200
    assert (data_dir / "media" / "screens" / "20260916" / "nested" / "ok.png").is_file()
