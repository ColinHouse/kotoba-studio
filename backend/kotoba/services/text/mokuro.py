"""Parse mokuro .mokuro manga OCR output into page-located text blocks.

Format reference: mokuro 0.2.5 (kha-white/mokuro master, ``mokuro/manga_page_ocr.py``
and ``mokuro/mokuro_generator.py``), cross-checked against the 0.2.0-beta.6
fixture ``tests/data/expected_results/test0/vol1.mokuro``. A volume is JSON with
``version``, ``title``, ``title_uuid``, ``volume``, ``volume_uuid`` and ``pages``;
every page has ``img_width``, ``img_height`` and ``blocks``; every block has
``box`` [x1, y1, x2, y2], ``vertical``, ``font_size``, ``lines_coords`` and
``lines``.

``lines`` already arrive in reading order: mokuro's detector sorts each block's
lines (vertical columns right to left, horizontal lines top to bottom) and keeps
re-sorting them while it splits and merges blocks. Joining them in that order is
the faithful reading; rebuilding the order from the line polygons tears apart a
vertical column the detector split into two stacked lines.

A volume also arrives as a zip: the mokuro output folder compressed, so the
``.mokuro`` file and the page images travel together. Page N is the N-th image
in natural filename order (``2.jpg`` before ``10.jpg``); the images are stored
under the media directory and linked from each line's screenshot, which is what
puts the page behind its text boxes in the reader.
"""

from __future__ import annotations

import io
import json
import re
import shutil
import uuid
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from kotoba.core.config import Paths
from kotoba.core.errors import ApiError
from kotoba.services.text.encoding import decode_text

_IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp", ".avif"}


@dataclass(slots=True)
class MokuroBlock:
    page: int
    box: list[float]
    text: str


@dataclass(slots=True)
class MokuroVolume:
    pages: int
    blocks: list[MokuroBlock]
    images: list[str] = field(default_factory=list)

    def image_for(self, page: int) -> str | None:
        """The media-relative page image, or None for a text-only import."""
        if 0 < page <= len(self.images):
            return self.images[page - 1]
        return None


def parse_mokuro(content: str | dict) -> MokuroVolume:
    data = content if isinstance(content, dict) else _load(content)
    pages = data.get("pages")
    if not isinstance(pages, list):
        raise _bad("缺少 pages 列表")
    blocks: list[MokuroBlock] = []
    for page_no, page in enumerate(pages, start=1):
        if not isinstance(page, dict):
            raise _bad(f"第 {page_no} 页不是对象")
        if not (_positive_int(page.get("img_width")) and _positive_int(page.get("img_height"))):
            raise _bad(f"第 {page_no} 页缺少 img_width / img_height")
        raw_blocks = page.get("blocks")
        if not isinstance(raw_blocks, list):
            raise _bad(f"第 {page_no} 页的 blocks 不是列表")
        for block_no, raw in enumerate(raw_blocks, start=1):
            block = _block(page_no, block_no, raw)
            if block.text:
                blocks.append(block)
    if not blocks:
        raise _bad("没有可导入的文本（是不是用了 disable_ocr？）")
    return MokuroVolume(pages=len(pages), blocks=blocks)


def load_volume(data: bytes, paths: Paths) -> MokuroVolume:
    """Read a .mokuro file or a whole-volume zip, storing page images under media/.

    The JSON is parsed before anything is written, so a bad volume cannot leave
    half a page set behind. Images are read and saved one at a time: a volume is
    hundreds of megabytes and must not sit in memory as a list of byte strings.
    """
    if data[:2] != b"PK":
        return parse_mokuro(decode_text(data))
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            volume = parse_mokuro(decode_text(archive.read(_mokuro_member(archive))))
            images = _image_members(archive)
            if not images:
                return volume
            if len(images) != volume.pages:
                raise _bad(f"zip 里有 {len(images)} 张页图，.mokuro 却记了 {volume.pages} 页")
            volume.images = _save_images(archive, images, paths)
            return volume
    except zipfile.BadZipFile as exc:
        raise _bad("zip 无法读取") from exc


def _mokuro_member(archive: zipfile.ZipFile) -> zipfile.ZipInfo:
    members = [
        member
        for member in archive.infolist()
        if member.filename.lower().endswith(".mokuro") and not _junk(member.filename)
    ]
    if not members:
        raise _bad("zip 里没有 .mokuro 文件")
    if len(members) > 1:
        raise _bad("zip 里有多个 .mokuro 文件")
    return members[0]


def _image_members(archive: zipfile.ZipFile) -> list[zipfile.ZipInfo]:
    members = [
        member
        for member in archive.infolist()
        if not member.is_dir()
        and not _junk(member.filename)
        and Path(member.filename).suffix.lower() in _IMAGE_SUFFIXES
    ]
    return sorted(members, key=lambda member: _natural_key(member.filename))


def _junk(name: str) -> bool:
    """macOS resource-fork entries double every image in a Finder-made zip."""
    path = Path(name)
    return "__MACOSX" in path.parts or path.name.startswith("._")


def _natural_key(name: str) -> tuple[int | str, ...]:
    return tuple(int(part) if part.isdigit() else part.lower() for part in re.split(r"(\d+)", name))


def _save_images(
    archive: zipfile.ZipFile, members: list[zipfile.ZipInfo], paths: Paths
) -> list[str]:
    """Store the pages under media/manga/<uuid>/<page>.<ext>, never by their own name.

    The archive's names are ignored for the destination path: a member called
    ``../../x.jpg`` is written as ``0001.jpg`` like any other.
    """
    folder = paths.manga_dir / uuid.uuid4().hex
    folder.mkdir(parents=True, exist_ok=True)
    saved: list[str] = []
    try:
        for page_no, member in enumerate(members, start=1):
            name = f"{page_no:04d}{Path(member.filename).suffix.lower()}"
            (folder / name).write_bytes(archive.read(member))
            saved.append(f"manga/{folder.name}/{name}")
    except (OSError, RuntimeError, zipfile.BadZipFile):
        shutil.rmtree(folder, ignore_errors=True)
        raise
    return saved


def _block(page_no: int, block_no: int, raw: Any) -> MokuroBlock:
    where = f"第 {page_no} 页第 {block_no} 个 block"
    if not isinstance(raw, dict):
        raise _bad(f"{where} 不是对象")
    box = raw.get("box")
    if not (
        isinstance(box, list)
        and len(box) == 4
        and all(isinstance(value, (int, float)) for value in box)
    ):
        raise _bad(f"{where} 的 box 无效")
    lines = raw.get("lines")
    if not isinstance(lines, list) or not all(isinstance(text, str) for text in lines):
        raise _bad(f"{where} 缺少 lines")
    coords = raw.get("lines_coords")
    if not isinstance(coords, list) or len(coords) != len(lines):
        raise _bad(f"{where} 的 lines_coords 与 lines 数量不一致")
    if not isinstance(raw.get("vertical"), bool):
        raise _bad(f"{where} 缺少 vertical")
    return MokuroBlock(page=page_no, box=[float(value) for value in box], text="".join(lines))


def _load(content: str) -> dict:
    try:
        data = json.loads(content)
    except json.JSONDecodeError as exc:
        raise _bad("不是有效的 .mokuro JSON") from exc
    if not isinstance(data, dict):
        raise _bad("顶层不是 JSON 对象")
    return data


def _positive_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value > 0


def _bad(message: str) -> ApiError:
    return ApiError("bad_mokuro", message)
