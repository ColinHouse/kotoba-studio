"""Download and import jmdict-simplified JSON into the dictionary tables."""

from __future__ import annotations

import json
import shutil
import threading
import zipfile
from collections.abc import Callable
from pathlib import Path

import httpx
from sqlalchemy import delete, func, insert, select
from sqlalchemy.orm import Session

from kotoba.config import Paths
from kotoba.models import DictEntry, DictForm, Dictionary

RELEASES_API = "https://api.github.com/repos/scriptin/jmdict-simplified/releases/latest"
BATCH = 2000


def latest_asset(client: httpx.Client | None = None) -> tuple[str, str]:
    """Return (download_url, tag) of the latest jmdict-eng JSON zip."""
    own = client is None
    client = client or httpx.Client(timeout=30, follow_redirects=True)
    try:
        data = client.get(RELEASES_API, headers={"Accept": "application/vnd.github+json"}).json()
    finally:
        if own:
            client.close()
    for asset in data.get("assets", []):
        name = asset["name"]
        if name.startswith("jmdict-eng-") and "common" not in name and name.endswith(".json.zip"):
            return asset["browser_download_url"], data.get("tag_name", "")
    raise RuntimeError("jmdict-eng asset not found in latest release")


def download(url: str, dest_dir: Path, client: httpx.Client | None = None) -> Path:
    """Download a jmdict zip and return the path of the extracted JSON file."""
    dest_dir.mkdir(parents=True, exist_ok=True)
    zip_path = dest_dir / "jmdict-eng.json.zip"
    own = client is None
    client = client or httpx.Client(timeout=None, follow_redirects=True)
    try:
        with client.stream("GET", url) as resp, zip_path.open("wb") as fh:
            resp.raise_for_status()
            for chunk in resp.iter_bytes(1 << 16):
                fh.write(chunk)
    finally:
        if own:
            client.close()
    with zipfile.ZipFile(zip_path) as zf:
        names = [n for n in zf.namelist() if n.endswith(".json")]
        if not names:
            raise RuntimeError("zip contains no json")
        zf.extract(names[0], dest_dir)
    json_path = dest_dir / "jmdict-eng.json"
    shutil.move(dest_dir / names[0], json_path)
    zip_path.unlink(missing_ok=True)
    return json_path


def _entry_rows(word: dict, entry_id: int, dict_id: int) -> tuple[dict, list[dict]]:
    senses = []
    pos_all: list[str] = []
    for s in word.get("sense", []):
        pos = s.get("partOfSpeech", [])
        pos_all.extend(p for p in pos if p not in pos_all)
        senses.append(
            {
                "pos": pos,
                "gloss_en": [
                    g["text"] for g in s.get("gloss", []) if g.get("lang", "eng") == "eng"
                ],
                "misc": s.get("misc", []),
                "field": s.get("field", []),
                "info": s.get("info", []),
            }
        )
    forms = []
    common = False
    for k in word.get("kanji", []):
        forms.append(
            {
                "entry_id": entry_id,
                "text": k["text"],
                "kind": "kanji",
                "common": bool(k.get("common")),
            }
        )
        common = common or bool(k.get("common"))
    for k in word.get("kana", []):
        forms.append(
            {
                "entry_id": entry_id,
                "text": k["text"],
                "kind": "kana",
                "common": bool(k.get("common")),
            }
        )
        common = common or bool(k.get("common"))
    entry = {
        "id": entry_id,
        "dict_id": dict_id,
        "ext_id": str(word["id"]),
        "senses_json": json.dumps(senses, ensure_ascii=False),
        "pos_json": json.dumps(pos_all, ensure_ascii=False),
        "common": common,
        "is_expression": "exp" in pos_all,
    }
    return entry, forms


def import_json(
    db: Session,
    path: Path,
    title: str = "JMdict (eng)",
    progress: Callable[[int, int], None] | None = None,
) -> int:
    """Replace any existing JMdict dictionary with the contents of `path`. Returns entry count."""
    with path.open(encoding="utf-8") as fh:
        data = json.load(fh)
    words = data["words"]

    for old in db.scalars(select(Dictionary).where(Dictionary.kind == "jmdict")).all():
        old_entry_ids = select(DictEntry.id).where(DictEntry.dict_id == old.id)
        db.execute(delete(DictForm).where(DictForm.entry_id.in_(old_entry_ids)))
        db.execute(delete(DictEntry).where(DictEntry.dict_id == old.id))
        db.delete(old)
    db.flush()

    dictionary = Dictionary(
        title=title,
        revision=str(data.get("dictDate") or data.get("version") or ""),
        kind="jmdict",
        entry_count=len(words),
    )
    db.add(dictionary)
    db.flush()

    next_id = (db.scalar(select(func.max(DictEntry.id))) or 0) + 1
    entry_batch: list[dict] = []
    form_batch: list[dict] = []
    total = len(words)
    for i, word in enumerate(words):
        entry, forms = _entry_rows(word, next_id + i, dictionary.id)
        entry_batch.append(entry)
        form_batch.extend(forms)
        if len(entry_batch) >= BATCH:
            db.execute(insert(DictEntry), entry_batch)
            db.execute(insert(DictForm), form_batch)
            entry_batch, form_batch = [], []
            if progress:
                progress(i + 1, total)
    if entry_batch:
        db.execute(insert(DictEntry), entry_batch)
        db.execute(insert(DictForm), form_batch)
    db.commit()
    if progress:
        progress(total, total)
    return total


def status(db: Session) -> dict:
    dicts = db.scalars(select(Dictionary).order_by(Dictionary.id)).all()
    return {
        "installed": any(d.kind == "jmdict" for d in dicts),
        "dictionaries": [
            {
                "id": d.id,
                "title": d.title,
                "kind": d.kind,
                "revision": d.revision,
                "entry_count": d.entry_count,
                "imported_at": d.imported_at.isoformat(),
            }
            for d in dicts
        ],
    }


class InstallJob:
    """Background JMdict install with observable state."""

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

        def run() -> None:
            db = session_factory()
            try:
                self.state, self.message = "downloading", "正在下载 JMdict…"
                asset_url = url or latest_asset()[0]
                json_path = download(asset_url, paths.dicts_dir)

                def prog(done: int, total: int) -> None:
                    self.done, self.total = done, total

                self.state, self.message = "importing", "正在导入词典…"
                import_json(db, json_path, progress=prog)
                self.state, self.message = "done", "词典已安装"
            except Exception as exc:  # noqa: BLE001
                db.rollback()
                self.state, self.message = "error", str(exc)
            finally:
                db.close()

        self._thread = threading.Thread(target=run, name="jmdict-install", daemon=True)
        self._thread.start()
        return True


install_job = InstallJob()
