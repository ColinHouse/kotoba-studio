"""The text-source preference is a recommendation, never a switch.

Hook is the default for a fresh install; a user who already mines with OCR
keeps OCR first and gets no nudge, because the key did not exist when they
chose their route. Either value leaves both capture paths usable.
"""

from __future__ import annotations


def test_preferred_text_source_defaults_to_hook(client):
    assert client.get("/api/settings").json()["preferred_text_source"] == "hook"


def test_preferred_text_source_rejects_anything_else(client):
    r = client.put("/api/settings", json={"preferred_text_source": "clipboard"})
    assert r.status_code == 400
    assert r.json()["error"]["code"] == "invalid_value"
    assert client.get("/api/settings").json()["preferred_text_source"] == "hook"


def test_existing_ocr_history_keeps_ocr_first(client):
    client.post("/api/lines", json={"text": "今日は", "origin": "ocr"})
    assert client.get("/api/settings").json()["preferred_text_source"] == "ocr"


def test_hook_history_does_not_change_the_default(client):
    client.post("/api/lines", json={"text": "今日は", "origin": "hook"})
    assert client.get("/api/settings").json()["preferred_text_source"] == "hook"


def test_an_explicit_choice_wins_over_history(client):
    client.post("/api/lines", json={"text": "今日は", "origin": "ocr"})
    client.put("/api/settings", json={"preferred_text_source": "hook"})
    assert client.get("/api/settings").json()["preferred_text_source"] == "hook"
