"""Read a Yomitan archive: its index.json and its term-bank file names."""

from __future__ import annotations

import json
import re
import zipfile
from dataclasses import dataclass

from kotoba.core.errors import ApiError

_TERM_BANK = re.compile(r"^term_bank_(\d+)\.json$")


@dataclass(slots=True)
class YomitanIndex:
    title: str
    revision: str | None
    author: str | None
    attribution: str | None


def read_index(archive: zipfile.ZipFile) -> YomitanIndex:
    """Parse index.json; a missing title means this is not a dictionary archive."""
    try:
        with archive.open("index.json") as fh:
            data = json.load(fh)
    except KeyError as exc:
        raise ApiError("bad_dictionary", "词典包缺少 index.json") from exc
    except json.JSONDecodeError as exc:
        raise ApiError("bad_dictionary", "index.json 不是有效的 JSON") from exc
    if not isinstance(data, dict) or not str(data.get("title") or "").strip():
        raise ApiError("bad_dictionary", "词典包的 index.json 缺少 title")
    revision = data.get("revision") or data.get("version") or data.get("format")
    return YomitanIndex(
        title=str(data["title"]).strip(),
        revision=str(revision) if revision is not None else None,
        author=str(data["author"]) if data.get("author") else None,
        attribution=str(data["attribution"]) if data.get("attribution") else None,
    )


def term_bank_names(archive: zipfile.ZipFile) -> list[str]:
    """term_bank_1.json, term_bank_2.json, ... in numeric order."""
    names = [name for name in archive.namelist() if _TERM_BANK.match(name)]
    return sorted(names, key=lambda name: int(_TERM_BANK.match(name).group(1)))
