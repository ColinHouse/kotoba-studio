"""Windows.Media.Ocr through the `winocr` package (Windows 10/11 with the Japanese language pack).

Verified against Windows 11 on real hardware. Two Windows-only quirks are handled
here: the engine refuses images larger than `OcrEngine.MaxImageDimension` (an 8K
screenshot is over it), and its `line.text` puts a space between every word —
including Japanese ones, where no space belongs.
"""

from __future__ import annotations

import io
import sys
import time

from kotoba.core.errors import ApiError
from kotoba.services.ocr.base import OcrBlock, OcrResult, join_blocks, join_words

OCR_LANG = "ja"

INSTALL_HINT = (
    "需要 Windows 日语 OCR 语言包：设置 → 时间和语言 → 语言和区域 → 添加日语，"
    "或以管理员运行 Add-WindowsCapability -Online -Name Language.OCR~~~ja-JP~0.0.1.0"
)


def _language_supported() -> bool:
    from winrt.windows.globalization import Language
    from winrt.windows.media.ocr import OcrEngine

    return bool(OcrEngine.is_language_supported(Language(OCR_LANG)))


def _max_image_dimension() -> int:
    from winrt.windows.media.ocr import OcrEngine

    return int(OcrEngine.max_image_dimension)


def _fit_within(image, limit: int):
    """Scale down to the engine's limit; boxes are normalized, so they stay valid."""
    from PIL import Image

    longest = max(image.size)
    if longest <= limit:
        return image
    ratio = limit / longest
    size = (max(1, round(image.width * ratio)), max(1, round(image.height * ratio)))
    return image.resize(size, Image.LANCZOS)


class WindowsOcrProvider:
    name = "winocr"
    note = "Windows 内置 OCR（需要日语语言包）"

    def available(self) -> bool:
        if sys.platform != "win32":
            return False
        try:
            import winocr  # noqa: F401
        except ImportError:
            return False
        try:
            return _language_supported()
        except Exception:  # noqa: BLE001 - a missing/broken WinRT projection is "unavailable"
            return False

    def recognize(self, png: bytes) -> OcrResult:
        if not self.available():
            raise ApiError("ocr_unavailable", "Windows OCR 不可用。" + INSTALL_HINT, 503)
        import winocr
        from PIL import Image

        t0 = time.perf_counter()
        image = Image.open(io.BytesIO(png)).convert("RGB")
        try:
            image = _fit_within(image, _max_image_dimension())
            result = winocr.recognize_pil_sync(image, OCR_LANG)
        except Exception as exc:  # noqa: BLE001 - a broken WinRT projection is 'unavailable'
            raise ApiError("ocr_failed", f"Windows OCR 失败: {exc}. {INSTALL_HINT}") from exc
        width, height = image.size
        blocks: list[OcrBlock] = []
        for line in result.get("lines") or []:
            words = line.get("words") or []
            rects = [w.get("bounding_rect") for w in words]
            rects = [r for r in rects if r]
            if rects:
                x0 = min(r["x"] for r in rects)
                y0 = min(r["y"] for r in rects)
                x1 = max(r["x"] + r["width"] for r in rects)
                y1 = max(r["y"] + r["height"] for r in rects)
                box = (x0 / width, y0 / height, (x1 - x0) / width, (y1 - y0) / height)
            else:
                box = (0.0, 0.0, 1.0, 1.0)
            text = join_words(str(w.get("text") or "") for w in words) or str(
                line.get("text") or ""
            )
            blocks.append(OcrBlock(text=text, confidence=1.0, box=box))
        text = join_blocks(blocks) if blocks else str(result.get("text") or "")
        return OcrResult(
            text=text,
            blocks=blocks,
            provider=self.name,
            elapsed_ms=int((time.perf_counter() - t0) * 1000),
        )
