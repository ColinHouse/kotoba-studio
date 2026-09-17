"""Cross-platform fallback: RapidOCR (onnxruntime, PP-OCRv5 covers Japanese)."""

from __future__ import annotations

import io
import time

from kotoba.core.errors import ApiError
from kotoba.services.ocr.base import OcrBlock, OcrResult, join_blocks


class RapidOcrProvider:
    name = "rapidocr"
    note = "RapidOCR（跨平台，onnxruntime；安装 extra `ocr-onnx`）"
    _engine = None

    def available(self) -> bool:
        try:
            import rapidocr  # noqa: F401
        except ImportError:
            return False
        return True

    def _get_engine(self):
        if RapidOcrProvider._engine is None:
            from rapidocr import RapidOCR

            RapidOcrProvider._engine = RapidOCR()
        return RapidOcrProvider._engine

    def recognize(self, png: bytes) -> OcrResult:
        if not self.available():
            raise ApiError("ocr_unavailable", "RapidOCR 未安装：pip install rapidocr", 503)
        from PIL import Image

        t0 = time.perf_counter()
        image = Image.open(io.BytesIO(png)).convert("RGB")
        width, height = image.size
        try:
            import numpy as np

            output = self._get_engine()(np.asarray(image))
        except Exception as exc:  # noqa: BLE001 - onnxruntime and model loading fail in many ways
            raise ApiError("ocr_failed", f"RapidOCR 失败: {exc}") from exc
        blocks: list[OcrBlock] = []
        boxes = getattr(output, "boxes", None)
        txts = getattr(output, "txts", None)
        scores = getattr(output, "scores", None)
        if boxes is not None and txts is not None:
            for poly, txt, score in zip(boxes, txts, scores or [1.0] * len(txts), strict=False):
                xs = [float(p[0]) for p in poly]
                ys = [float(p[1]) for p in poly]
                box = (
                    min(xs) / width,
                    min(ys) / height,
                    (max(xs) - min(xs)) / width,
                    (max(ys) - min(ys)) / height,
                )
                blocks.append(OcrBlock(text=str(txt), confidence=float(score), box=box))
        return OcrResult(
            text=join_blocks(blocks),
            blocks=blocks,
            provider=self.name,
            elapsed_ms=int((time.perf_counter() - t0) * 1000),
        )
