"""AnkiConnect client (port of the anki_mpv AnkiService with self-healing deck/model setup)."""

from __future__ import annotations

import base64

import httpx

from kotoba.errors import ApiError
from kotoba.services.export.notes import BACK, CSS, FIELDS, FRONT, ExportNote

DECK_NAME = "Kotoba Studio"
MODEL_NAME = "KotobaStudio-v1"


class AnkiConnect:
    def __init__(
        self,
        url: str = "http://127.0.0.1:8765",
        transport: httpx.BaseTransport | None = None,
        timeout: float = 15.0,
    ):
        self.url = url
        self._client = httpx.Client(transport=transport, timeout=timeout)

    def close(self) -> None:
        self._client.close()

    def invoke(self, action: str, **params):
        try:
            resp = self._client.post(
                self.url, json={"action": action, "version": 6, "params": params}
            )
        except httpx.HTTPError as exc:
            raise ApiError(
                "anki_unreachable", "无法连接 AnkiConnect：请打开 Anki 并启用 AnkiConnect 插件", 503
            ) from exc
        data = resp.json()
        if data.get("error"):
            raise ApiError("anki_error", str(data["error"]), 502)
        return data.get("result")

    def version(self) -> int:
        return int(self.invoke("version"))

    def deck_names(self) -> list[str]:
        return list(self.invoke("deckNames") or [])

    def ensure_deck(self, name: str = DECK_NAME) -> None:
        if name not in self.deck_names():
            self.invoke("createDeck", deck=name)

    def ensure_model(self) -> None:
        if MODEL_NAME in (self.invoke("modelNames") or []):
            return
        self.invoke(
            "createModel",
            modelName=MODEL_NAME,
            inOrderFields=FIELDS,
            css=CSS,
            cardTemplates=[{"Name": "Recognition", "Front": FRONT, "Back": BACK}],
        )

    def store_media(self, filename: str, data: bytes) -> None:
        self.invoke("storeMediaFile", filename=filename, data=base64.b64encode(data).decode())

    def add_note(self, note: ExportNote, deck: str = DECK_NAME) -> int | None:
        """Add one note; returns the note id, or None when Anki reports a duplicate."""
        if note.image:
            self.store_media(note.image[0], note.image[1].read_bytes())
        if note.audio:
            self.store_media(note.audio[0], note.audio[1].read_bytes())
        payload = {
            "deckName": deck,
            "modelName": MODEL_NAME,
            "fields": note.fields(),
            "options": {"allowDuplicate": False, "duplicateScope": "deck"},
            "tags": note.tags,
        }
        try:
            result = self.invoke("addNote", note=payload)
        except ApiError as exc:
            if "duplicate" in exc.message.lower():
                return None
            raise
        return int(result) if result else None

    def add_notes(self, notes: list[ExportNote], deck: str = DECK_NAME) -> dict:
        self.version()
        self.ensure_deck(deck)
        self.ensure_model()
        added: list[dict] = []
        skipped: list[str] = []
        errors: list[dict] = []
        for note in notes:
            try:
                note_id = self.add_note(note, deck)
            except ApiError as exc:
                errors.append({"word": note.word, "error": exc.message})
                continue
            if note_id is None:
                skipped.append(note.word)
            else:
                added.append({"word": note.word, "note_id": note_id})
        return {"deck": deck, "added": added, "skipped": skipped, "errors": errors}
