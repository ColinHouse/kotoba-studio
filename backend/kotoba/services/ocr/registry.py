"""Pick an OCR provider for this platform."""

from __future__ import annotations

import sys
import time

from kotoba.core.errors import ApiError
from kotoba.services.ocr.base import ManualProvider, OcrProvider
from kotoba.services.ocr.providers.rapidocr import RapidOcrProvider
from kotoba.services.ocr.providers.vision_macos import VisionProvider
from kotoba.services.ocr.providers.windows_ocr import WindowsOcrProvider

PROVIDERS: dict[str, type] = {
    "vision": VisionProvider,
    "winocr": WindowsOcrProvider,
    "rapidocr": RapidOcrProvider,
    "manual": ManualProvider,
}


def platform_order() -> list[str]:
    if sys.platform == "darwin":
        return ["vision", "rapidocr"]
    if sys.platform == "win32":
        return ["winocr", "rapidocr"]
    return ["rapidocr"]


def list_providers() -> list[dict]:
    order = platform_order()
    out = []
    for name, cls in PROVIDERS.items():
        provider = cls()
        out.append(
            {
                "name": name,
                "available": provider.available(),
                "note": provider.note,
                "recommended": bool(order) and order[0] == name,
            }
        )
    return out


def get_provider(name: str | None = None) -> OcrProvider:
    """Return an available provider; `name` None/"auto" picks the platform default."""
    if name in (None, "", "auto"):
        for candidate in platform_order():
            provider = PROVIDERS[candidate]()
            if provider.available():
                return provider
        raise ApiError(
            "ocr_unavailable",
            "没有可用的 OCR 引擎：macOS 请安装 extra `macos`，Windows 请安装日语语言包，"
            "或安装 extra `ocr-onnx`（RapidOCR）。",
            503,
        )
    cls = PROVIDERS.get(name)
    if cls is None:
        raise ApiError("ocr_unavailable", f"未知的 OCR 引擎: {name}", 404)
    provider = cls()
    if not provider.available():
        raise ApiError("ocr_unavailable", f"OCR 引擎 {name} 在此设备上不可用。{provider.note}", 503)
    return provider


def compare(png: bytes) -> list[dict]:
    """Run every available provider on the same image; a failure stays in its own row."""
    rows: list[dict] = []
    for name, cls in PROVIDERS.items():
        started = time.perf_counter()
        try:
            provider = cls()
            if not provider.available():
                continue
            text, error = provider.recognize(png).text, None
        except Exception as exc:  # noqa: BLE001 - one engine failing must not hide the others
            text = ""
            error = exc.message if isinstance(exc, ApiError) else str(exc)
        rows.append(
            {
                "provider": name,
                "text": text,
                "ms": int((time.perf_counter() - started) * 1000),
                "error": error,
            }
        )
    return rows
