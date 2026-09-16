"""Windows.Media.Ocr through the `winocr` package (Windows 10/11 with the Japanese language pack).

Not exercised on the development Mac; the shape follows winocr's documented API
(`recognize_pil(image, lang)` returning `.text` and `.lines[].words[].bounding_rect`).
"""

from __future__ import annotations

import asyncio
import io
import sys
import time

from kotoba.core.errors import ApiError
from kotoba.services.ocr.base import OcrBlock, OcrResult, join_blocks

INSTALL_HINT = (
    "需要 Windows 日语 OCR 语言包：设置 → 时间和语言 → 语言和区域 → 添加日语，"
    "或以管理员运行 Add-WindowsCapability -Online -Name Language.OCR~~~ja-JP~0.0.1.0"
)


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
        return True

    def recognize(self, png: bytes) -> OcrResult:
        if not self.available():
            raise ApiError("ocr_unavailable", "Windows OCR 不可用。" + INSTALL_HINT, 503)
        import winocr
        from PIL import Image

        t0 = time.perf_counter()
        image = Image.open(io.BytesIO(png)).convert("RGB")
        width, height = image.size
        try:
            result = asyncio.run(winocr.recognize_pil(image, "ja"))
        except Exception as exc:  # noqa: BLE001
            raise ApiError("ocr_failed", f"Windows OCR 失败: {exc}. {INSTALL_HINT}") from exc
        blocks: list[OcrBlock] = []
        for line in getattr(result, "lines", []) or []:
            words = getattr(line, "words", []) or []
            rects = [getattr(w, "bounding_rect", None) for w in words]
            rects = [r for r in rects if r is not None]
            if rects:
                x0 = min(r.x for r in rects)
                y0 = min(r.y for r in rects)
                x1 = max(r.x + r.width for r in rects)
                y1 = max(r.y + r.height for r in rects)
                box = (x0 / width, y0 / height, (x1 - x0) / width, (y1 - y0) / height)
            else:
                box = (0.0, 0.0, 1.0, 1.0)
            blocks.append(OcrBlock(text=str(line.text), confidence=1.0, box=box))
        text = join_blocks(blocks) if blocks else str(getattr(result, "text", ""))
        return OcrResult(
            text=text,
            blocks=blocks,
            provider=self.name,
            elapsed_ms=int((time.perf_counter() - t0) * 1000),
        )
