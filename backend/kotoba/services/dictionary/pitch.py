"""Pitch accent: Kanjium downloads, Yomitan banks and the four pattern names.

Only the data format is handled here; no pitch data is bundled. Kanjium is
CC BY-SA 4.0 (Uros O.), the same licence family as JMdict. Chinese speakers
tend to project tone onto Japanese, so this is the one cue the app can give
that most Anki-front-end tools do not.
"""

from __future__ import annotations

import json
import re
import threading
import zipfile
from collections.abc import Callable
from pathlib import Path
from typing import Any, Literal

import httpx
from sqlalchemy import delete, insert, select
from sqlalchemy.orm import Session

from kotoba.core.config import Paths
from kotoba.models import TermPitch
from kotoba.services.capture.gate import gate
from kotoba.services.dictionary.yomitan.archive import meta_bank_names
from kotoba.services.jp import mora

BATCH = 2000
KANJIUM_URL = (
    "https://raw.githubusercontent.com/mifunetoshiro/kanjium/"
    "master/data/source_files/raw/accents.txt"
)
KANJIUM_FILE = "kanjium-accents.txt"
_NUMBER = re.compile(r"\d+")

Pattern = Literal["heiban", "atamadaka", "nakadaka", "odaka"]

PATTERN_LABELS: dict[str, str] = {
    "heiban": "平板",
    "atamadaka": "头高",
    "nakadaka": "中高",
    "odaka": "尾高",
}


def pattern(reading: str, accent: int) -> Pattern:
    """0 = heiban, 1 = atamadaka, accent == mora count = odaka, else nakadaka."""
    morae = mora.mora_count(reading)
    if accent == 0:
        return "heiban"
    if accent == 1:
        return "atamadaka"
    if accent >= morae:
        return "odaka"
    return "nakadaka"


def parse_kanjium_line(line: str) -> list[tuple[str, str, int]]:
    """`word\\treading\\t0,2` (annotations allowed); unusable lines yield nothing."""
    parts = line.rstrip("\n").split("\t")
    if len(parts) < 3:
        return []
    headword, reading = parts[0].strip(), parts[1].strip()
    if not headword or not reading:
        return []
    return [(headword, reading, int(number)) for number in _NUMBER.findall(parts[2])]


def import_kanjium(db: Session, text: str, source: str = "kanjium") -> int:
    rows: dict[tuple[str, str, int], None] = {}
    for line in text.splitlines():
        for headword, reading, accent in parse_kanjium_line(line):
            rows[(headword, reading, accent)] = None
    return _replace(
        db,
        source,
        [
            {"headword": headword, "reading": reading, "accent": accent, "source": source}
            for headword, reading, accent in rows
        ],
    )


def parse_yomitan_entry(raw: Any) -> list[tuple[str, str, int]]:
    if not isinstance(raw, list) or len(raw) < 3 or raw[1] != "pitch":
        return []
    headword = str(raw[0] or "").strip()
    data = raw[2]
    if not headword or not isinstance(data, dict):
        return []
    reading = str(data.get("reading") or "").strip()
    pitches = data.get("pitches")
    if not reading or not isinstance(pitches, list):
        return []
    out: list[tuple[str, str, int]] = []
    for item in pitches:
        position = item.get("position") if isinstance(item, dict) else item
        if isinstance(position, int) and not isinstance(position, bool) and position >= 0:
            out.append((headword, reading, int(position)))
    return out


def import_yomitan(db: Session, archive: zipfile.ZipFile, source: str = "yomitan") -> int:
    rows: dict[tuple[str, str, int], None] = {}
    for name in meta_bank_names(archive):
        with archive.open(name) as fh:
            bank = json.load(fh)
        if not isinstance(bank, list):
            continue
        for raw in bank:
            for headword, reading, accent in parse_yomitan_entry(raw):
                rows[(headword, reading, accent)] = None
    return _replace(
        db,
        source,
        [
            {"headword": headword, "reading": reading, "accent": accent, "source": source}
            for headword, reading, accent in rows
        ],
    )


def _replace(db: Session, source: str, rows: list[dict]) -> int:
    db.execute(delete(TermPitch).where(TermPitch.source == source))
    for start in range(0, len(rows), BATCH):
        db.execute(insert(TermPitch), rows[start : start + BATCH])
        db.commit()
    db.commit()
    return len(rows)


def has_any(db: Session) -> bool:
    return db.scalar(select(TermPitch.id).limit(1)) is not None


def pitches_for(db: Session, headword: str, reading: str = "") -> list[dict]:
    """Recorded pitches for a word; a given reading narrows to its own rows."""
    rows = db.scalars(
        select(TermPitch)
        .where(TermPitch.headword == headword)
        .order_by(TermPitch.reading, TermPitch.accent)
    ).all()
    if reading:
        exact = [row for row in rows if row.reading == reading]
        if exact:
            rows = exact
    seen: set[tuple[str, int]] = set()
    out: list[dict] = []
    for row in rows:
        key = (row.reading, row.accent)
        if key in seen:
            continue
        seen.add(key)
        name = pattern(row.reading, row.accent)
        out.append(
            {
                "reading": row.reading,
                "accent": row.accent,
                "pattern": name,
                "label": PATTERN_LABELS[name],
            }
        )
    return out


def download_text(url: str, dest: Path) -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    with httpx.stream("GET", url, follow_redirects=True, timeout=None) as resp:
        resp.raise_for_status()
        with dest.open("wb") as fh:
            for chunk in resp.iter_bytes(1 << 16):
                fh.write(chunk)
    return dest


class PitchInstallJob:
    """Background download-and-import job, shaped like the JMdict one."""

    def __init__(self) -> None:
        self.state = "idle"
        self.message = ""
        self.done = 0
        self.total = 0
        self._thread: threading.Thread | None = None

    def snapshot(self) -> dict:
        return {
            "state": self.state,
            "message": self.message,
            "done": self.done,
            "total": self.total,
        }

    def start(
        self,
        session_factory: Callable[[], Session],
        paths: Paths,
        url: str | None = None,
    ) -> bool:
        if self._thread and self._thread.is_alive():
            return False
        gate.begin_long_write("pitch-install")

        def run() -> None:
            db = session_factory()
            try:
                self.state, self.message = "downloading", "正在下载音高数据（Kanjium）…"
                path = download_text(url or KANJIUM_URL, paths.dicts_dir / KANJIUM_FILE)
                self.state, self.message = "importing", "正在导入音高数据…"
                self.done = self.total = import_kanjium(db, path.read_text(encoding="utf-8"))
                self.state, self.message = "done", "音高数据已安装"
            except Exception as exc:  # noqa: BLE001
                db.rollback()
                self.state, self.message = "error", str(exc)
            finally:
                db.close()
                gate.end_long_write("pitch-install")

        # If the thread never starts, the claim must not outlive this call: a leaked
        # claim blocks every future restore until the application is restarted.
        try:
            self._thread = threading.Thread(target=run, name="pitch-install", daemon=True)
            self._thread.start()
        except BaseException:
            gate.end_long_write("pitch-install")
            raise
        return True


install_job = PitchInstallJob()
