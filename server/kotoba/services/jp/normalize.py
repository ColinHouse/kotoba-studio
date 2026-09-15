"""Clean up OCR / hook text before storing or tokenizing it."""

from __future__ import annotations

import hashlib
import re
import unicodedata

_CJK = r"[　-〿぀-ヿ㐀-䶿一-鿿！-｠]"
_ELLIPSIS_RUN = re.compile(r"(?:[・･.．]\s*){2,}")
_SPACE_BETWEEN_CJK = re.compile(rf"(?<={_CJK})[ \t　]+(?={_CJK})")
_NEWLINE_BETWEEN_CJK = re.compile(rf"(?<={_CJK})[ \t]*\n[ \t]*(?={_CJK})")
_MULTI_SPACE = re.compile(r"[ \t]+")


def _halfwidth_katakana_to_fullwidth(text: str) -> str:
    if not any(0xFF61 <= ord(c) <= 0xFF9F for c in text):
        return text
    out: list[str] = []
    for c in text:
        out.append(unicodedata.normalize("NFKC", c) if 0xFF61 <= ord(c) <= 0xFF9F else c)
    # NFKC may leave combining (han)dakuten; compose them.
    return unicodedata.normalize("NFC", "".join(out))


def normalize_ocr(text: str) -> str:
    """Normalize typography without touching the words themselves.

    - runs of middle dots / periods become a single ellipsis (…)
    - half-width katakana become full-width
    - whitespace and line breaks between CJK characters are removed
    - remaining whitespace runs collapse to one space
    """
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = _halfwidth_katakana_to_fullwidth(text)
    text = _ELLIPSIS_RUN.sub("…", text)
    text = _NEWLINE_BETWEEN_CJK.sub("", text)
    text = _SPACE_BETWEEN_CJK.sub("", text)
    text = _MULTI_SPACE.sub(" ", text)
    return text.strip()


def text_hash(text: str) -> str:
    return hashlib.sha1(normalize_ocr(text).encode("utf-8")).hexdigest()
