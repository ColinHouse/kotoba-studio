"""Screen capture with mss. Coordinates are logical (points); the grabbed image may be
larger on HiDPI displays — `scale` reports the ratio."""

from __future__ import annotations

import io
import uuid
from dataclasses import asdict, dataclass
from datetime import UTC, datetime

from kotoba.core.config import Paths
from kotoba.core.errors import ApiError


@dataclass(slots=True)
class Region:
    left: int
    top: int
    width: int
    height: int
    display: int = 0

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(slots=True)
class Grab:
    png: bytes
    width: int  # pixels of the PNG
    height: int
    scale: float  # pixels per logical point


def _mss():
    try:
        import mss
    except ImportError as exc:  # pragma: no cover
        raise ApiError("capture_unavailable", "mss 未安装", 503) from exc
    try:
        return mss.MSS()
    except Exception as exc:  # noqa: BLE001 - mss raises X11/Wayland/no-display errors of every shape
        raise ApiError("capture_failed", f"无法访问屏幕: {exc}", 503) from exc


def displays() -> list[dict]:
    with _mss() as sct:
        monitors = sct.monitors[1:] or sct.monitors[:1]
        return [
            {
                "index": i,
                "left": m["left"],
                "top": m["top"],
                "width": m["width"],
                "height": m["height"],
            }
            for i, m in enumerate(monitors)
        ]


def _to_png(shot) -> bytes:
    from PIL import Image

    image = Image.frombytes("RGB", shot.size, shot.bgra, "raw", "BGRX")
    buf = io.BytesIO()
    image.save(buf, format="PNG", optimize=False)
    return buf.getvalue()


def grab(region: Region) -> Grab:
    if region.width <= 0 or region.height <= 0:
        raise ApiError("invalid_region", "区域宽高必须大于 0")
    with _mss() as sct:
        monitors = sct.monitors[1:] or sct.monitors[:1]
        if not 0 <= region.display < len(monitors):
            raise ApiError("invalid_region", f"显示器 {region.display} 不存在")
        mon = monitors[region.display]
        box = {
            "left": mon["left"] + region.left,
            "top": mon["top"] + region.top,
            "width": region.width,
            "height": region.height,
        }
        try:
            shot = sct.grab(box)
        except Exception as exc:  # noqa: BLE001 - a stale region or a display that changed under us
            raise ApiError(
                "capture_failed",
                f"截屏失败: {exc}（macOS 请在 系统设置 → 隐私与安全性 → 屏幕录制 中授权）",
                503,
            ) from exc
    png = _to_png(shot)
    return Grab(png=png, width=shot.width, height=shot.height, scale=shot.width / region.width)


def grab_display(index: int = 0) -> tuple[Grab, dict]:
    mons = displays()
    if not 0 <= index < len(mons):
        raise ApiError("invalid_region", f"显示器 {index} 不存在")
    mon = mons[index]
    return grab(Region(0, 0, mon["width"], mon["height"], display=index)), mon


def save_screenshot(png: bytes, paths: Paths, subdir: str = "screens") -> str:
    """Write PNG under media/<subdir>/YYYYMMDD/ and return the media-relative path."""
    day = datetime.now(UTC).strftime("%Y%m%d")
    folder = paths.media_dir / subdir / day
    folder.mkdir(parents=True, exist_ok=True)
    name = f"{uuid.uuid4().hex}.png"
    (folder / name).write_bytes(png)
    return f"{subdir}/{day}/{name}"
