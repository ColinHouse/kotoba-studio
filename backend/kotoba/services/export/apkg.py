"""Offline Anki package export with genanki."""

from __future__ import annotations

from pathlib import Path

import genanki

from kotoba.services.export.notes import BACK, CSS, FIELDS, FRONT, ExportNote

MODEL_ID = 1726090001
DECK_ID = 1726090002


def _model() -> genanki.Model:
    return genanki.Model(
        MODEL_ID,
        # Must stay identical to anki_connect.MODEL_NAME, and stays on the
        # pre-rename name for the reason given there.
        "KotobaStudio-v1",
        fields=[{"name": f} for f in FIELDS],
        templates=[{"name": "Recognition", "qfmt": FRONT, "afmt": BACK}],
        css=CSS,
    )


class _Note(genanki.Note):
    @property
    def guid(self):  # stable per term so re-exports update instead of duplicating
        return genanki.guid_for(self.fields[FIELDS.index("KotobaId")])


def build(notes: list[ExportNote], out_path: Path, deck_name: str = "Kotobako") -> Path:
    model = _model()
    deck = genanki.Deck(DECK_ID, deck_name)
    media: list[str] = []
    for note in notes:
        fields = note.fields()
        deck.add_note(_Note(model=model, fields=[fields[f] for f in FIELDS], tags=note.tags))
        for asset in (note.image, note.audio):
            if asset:
                filename, path = asset
                alias = path.parent / filename
                if not alias.exists():
                    try:
                        alias.symlink_to(path)
                    except OSError:
                        alias.write_bytes(path.read_bytes())
                media.append(str(alias))
    out_path.parent.mkdir(parents=True, exist_ok=True)
    genanki.Package(deck, media_files=media).write_to_file(str(out_path))
    return out_path
