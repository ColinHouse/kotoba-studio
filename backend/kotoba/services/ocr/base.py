"""OCR provider interface."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import asdict, dataclass, field
from typing import Protocol

from kotoba.core.errors import ApiError


@dataclass(slots=True)
class OcrBlock:
    text: str
    confidence: float
    box: tuple[float, float, float, float]  # x, y, w, h normalized to 0..1, top-left origin


@dataclass(slots=True)
class OcrResult:
    text: str
    blocks: list[OcrBlock] = field(default_factory=list)
    provider: str = ""
    elapsed_ms: int = 0

    def to_dict(self) -> dict:
        return {
            "text": self.text,
            "blocks": [asdict(b) for b in self.blocks],
            "provider": self.provider,
            "elapsed_ms": self.elapsed_ms,
        }


class OcrProvider(Protocol):
    name: str
    note: str

    def available(self) -> bool: ...

    def recognize(self, png: bytes) -> OcrResult: ...


def join_blocks(blocks: list[OcrBlock]) -> str:
    """Join blocks top-to-bottom, left-to-right into lines of text."""
    ordered = sorted(blocks, key=lambda b: (round(b.box[1], 2), b.box[0]))
    return "\n".join(b.text for b in ordered if b.text.strip())


def join_words(words: Iterable[str]) -> str:
    """Join word-level OCR output, separating only Latin words.

    Windows OCR splits every line into words and joins them with spaces, which is
    wrong for Japanese: ``奢 っ て`` must read ``奢って``. A separator is only kept
    between two ASCII alphanumerics, so ``I love you`` stays spaced.
    """
    out = ""
    for text in words:
        if not text:
            continue
        if (
            out
            and out[-1].isascii()
            and out[-1].isalnum()
            and text[0].isascii()
            and text[0].isalnum()
        ):
            out += " "
        out += text
    return out


class ManualProvider:
    name = "manual"
    note = "手动粘贴文本；没有可用的 OCR 引擎时使用"

    def available(self) -> bool:
        return False

    def recognize(self, png: bytes) -> OcrResult:
        raise ApiError("ocr_unavailable", "没有可用的 OCR 引擎，请手动粘贴文本", 503)
