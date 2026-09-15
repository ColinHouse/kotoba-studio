"""Apple Vision OCR (macOS 13+) through pyobjc."""

from __future__ import annotations

import sys
import time

from kotoba.errors import ApiError
from kotoba.services.ocr.base import OcrBlock, OcrResult, join_blocks


class VisionProvider:
    name = "vision"
    note = "Apple Vision（macOS 内置，日语识别质量高，约 1 秒）"

    def available(self) -> bool:
        if sys.platform != "darwin":
            return False
        try:
            import Quartz  # noqa: F401
            import Vision  # noqa: F401
        except ImportError:
            return False
        return True

    def recognize(self, png: bytes) -> OcrResult:
        if not self.available():
            raise ApiError("ocr_unavailable", "Apple Vision 不可用（需要 macOS 与 pyobjc）", 503)
        import Quartz
        import Vision
        from Foundation import NSData

        t0 = time.perf_counter()
        data = NSData.dataWithBytes_length_(png, len(png))
        source = Quartz.CGImageSourceCreateWithData(data, None)
        if source is None:
            raise ApiError("ocr_failed", "无法解码截图")
        cgimg = Quartz.CGImageSourceCreateImageAtIndex(source, 0, None)
        request = Vision.VNRecognizeTextRequest.alloc().init()
        request.setRecognitionLevel_(Vision.VNRequestTextRecognitionLevelAccurate)
        request.setRecognitionLanguages_(["ja-JP"])
        request.setUsesLanguageCorrection_(True)
        handler = Vision.VNImageRequestHandler.alloc().initWithCGImage_options_(cgimg, None)
        ok, err = handler.performRequests_error_([request], None)
        if not ok:
            raise ApiError("ocr_failed", f"Vision 识别失败: {err}")
        blocks: list[OcrBlock] = []
        for obs in request.results() or []:
            candidates = obs.topCandidates_(1)
            if not candidates:
                continue
            cand = candidates[0]
            bb = obs.boundingBox()  # normalized, origin bottom-left
            x, y, w, h = bb.origin.x, bb.origin.y, bb.size.width, bb.size.height
            blocks.append(
                OcrBlock(
                    text=str(cand.string()),
                    confidence=float(cand.confidence()),
                    box=(float(x), float(1.0 - (y + h)), float(w), float(h)),
                )
            )
        return OcrResult(
            text=join_blocks(blocks),
            blocks=blocks,
            provider=self.name,
            elapsed_ms=int((time.perf_counter() - t0) * 1000),
        )
