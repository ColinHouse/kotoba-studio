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
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from kotoba.core.errors import ApiError


@dataclass(slots=True)
class MokuroBlock:
    page: int
    box: list[float]
    text: str


@dataclass(slots=True)
class MokuroVolume:
    pages: int
    blocks: list[MokuroBlock]


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
