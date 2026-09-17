"""Locations of files shipped inside the package."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

PACKAGE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = PACKAGE_DIR / "data"

CONTRACTIONS_FILE = DATA_DIR / "jp_contractions.json"
HOMOGRAPH_TRAPS_FILE = DATA_DIR / "homograph_traps_zh.json"
JMDICT_FIXTURE_FILE = DATA_DIR / "jmdict_fixture.json"
TRAY_ICON_FILE = DATA_DIR / "tray.png"


@lru_cache(maxsize=8)
def load_json(path: Path) -> Any:
    """Read a bundled JSON file once and cache it for the process lifetime."""
    with path.open(encoding="utf-8") as fh:
        return json.load(fh)
