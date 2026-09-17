"""Download and import KANJIDIC2 (EDRDG) into the kanji table.

KANJIDIC2 is CC BY-SA 4.0 like JMdict; the acknowledgement lives in NOTICE.md,
the README and Settings. The download URL is EDRDG's current location:
``www.edrdg.org/kanjidic/kanjidic2.xml.gz`` now 404s after the site was
reorganised, ``/pub/Nihongo/`` is what still serves the file.
"""

from __future__ import annotations

import gzip
import json
import threading
from collections.abc import Callable
from pathlib import Path
from xml.etree import ElementTree

import httpx
from sqlalchemy import delete, func, insert, select
from sqlalchemy.orm import Session

from kotoba.core.config import Paths
from kotoba.models import Kanji
from kotoba.services.capture.gate import gate

DOWNLOAD_URL = "https://www.edrdg.org/pub/Nihongo/kanjidic2.xml.gz"
BATCH = 2000
ON_READING = "ja_on"
KUN_READING = "ja_kun"


def parse_kxml(raw: bytes) -> list[dict]:
    """Parse kanjidic2.xml into rows for the kanji table."""
    root = ElementTree.fromstring(raw)
    rows: list[dict] = []
    for element in root.iter():
        if _local(element.tag) != "character":
            continue
        literal = element.findtext("literal")
        if not literal:
            continue
        misc = next((child for child in element if _local(child.tag) == "misc"), None)
        readings = {ON_READING: [], KUN_READING: []}
        for child in element:
            if _local(child.tag) != "reading_meaning":
                continue
            for group in child:
                for reading in group:
                    if _local(reading.tag) != "reading":
                        continue
                    kind = reading.get("r_type")
                    if kind in readings and reading.text:
                        readings[kind].append(reading.text)

        rows.append(
            {
                "character": literal,
                "on_readings_json": json.dumps(readings[ON_READING], ensure_ascii=False),
                "kun_readings_json": json.dumps(readings[KUN_READING], ensure_ascii=False),
                "grade": _number(misc, "grade"),
                "jlpt": _number(misc, "jlpt"),
                "stroke_count": _number(misc, "stroke_count"),
                "frequency": _number(misc, "freq"),
            }
        )
    if not rows:
        raise ValueError("kanjidic2.xml 里没有 character 条目")
    return rows


def import_bytes(
    db: Session, raw: bytes, progress: Callable[[int, int], None] | None = None
) -> int:
    """Replace the kanji table with the contents of a kanjidic2.xml. Returns the count."""
    rows = parse_kxml(raw)
    db.execute(delete(Kanji))
    for start in range(0, len(rows), BATCH):
        db.execute(insert(Kanji), rows[start : start + BATCH])
        if progress:
            progress(min(start + BATCH, len(rows)), len(rows))
    db.commit()
    return len(rows)


def download(dest_dir: Path, url: str = DOWNLOAD_URL, client: httpx.Client | None = None) -> bytes:
    """Fetch kanjidic2.xml.gz, keep the archive and return the XML bytes."""
    own = client is None
    client = client or httpx.Client(timeout=None, follow_redirects=True)
    try:
        response = client.get(url)
        response.raise_for_status()
        raw = response.content
    finally:
        if own:
            client.close()
    dest_dir.mkdir(parents=True, exist_ok=True)
    (dest_dir / "kanjidic2.xml.gz").write_bytes(raw)
    if raw[:2] == b"\x1f\x8b":
        raw = gzip.decompress(raw)
    return raw


def status(db: Session) -> dict:
    count = db.scalar(select(func.count(Kanji.character))) or 0
    return {
        "kanjidic_installed": count > 0,
        "kanji_count": count,
        "kanjidic": install_job.snapshot(),
    }


class InstallJob:
    """Background download-and-import with observable state, like the JMdict one."""

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
        self, session_factory: Callable[[], Session], paths: Paths, url: str | None = None
    ) -> bool:
        if self._thread and self._thread.is_alive():
            return False
        gate.begin_long_write("kanjidic-install")

        def run() -> None:
            db = session_factory()
            try:
                self.state, self.message = "downloading", "正在下载 KANJIDIC2…"
                raw = download(paths.dicts_dir, url or DOWNLOAD_URL)

                def prog(done: int, total: int) -> None:
                    self.done, self.total = done, total

                self.state, self.message = "importing", "正在导入汉字表…"
                count = import_bytes(db, raw, progress=prog)
                self.state, self.message = "done", f"已导入 {count} 个汉字"
            except Exception as exc:  # noqa: BLE001 - report through state; the thread must reach its finally
                db.rollback()
                self.state, self.message = "error", str(exc)
            finally:
                db.close()
                gate.end_long_write("kanjidic-install")

        # If the thread never starts, the claim must not outlive this call: a leaked
        # claim blocks every future restore until the application is restarted.
        try:
            self._thread = threading.Thread(target=run, name="kanjidic-install", daemon=True)
            self._thread.start()
        except BaseException:
            gate.end_long_write("kanjidic-install")
            raise
        return True


install_job = InstallJob()


def _number(misc: ElementTree.Element | None, tag: str) -> int | None:
    text = misc.findtext(tag) if misc is not None else None
    return int(text) if text and text.isdigit() else None


def _local(tag: object) -> str:
    if not isinstance(tag, str):
        return ""
    return tag.rsplit("}", 1)[-1].lower()
