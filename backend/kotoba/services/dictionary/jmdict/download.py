"""Fetch the latest jmdict-simplified release."""

from __future__ import annotations

import shutil
import zipfile
from pathlib import Path

import httpx

RELEASES_API = "https://api.github.com/repos/scriptin/jmdict-simplified/releases/latest"


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
