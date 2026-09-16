"""Decode uploaded text files the way Japanese subtitle and word lists arrive."""

from __future__ import annotations

from kotoba.core.errors import ApiError

ENCODINGS = ("utf-8", "utf-8-sig", "cp932")


def decode_text(data: bytes) -> str:
    for encoding in ENCODINGS:
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    raise ApiError("bad_encoding", "文件编码无法识别（支持 UTF-8 与 Shift_JIS）")
