"""Find the game's window and follow it, so capture works in windowed games.

Picking a window by hand beats guessing from a game's name: the list comes from
the OS, and a window that moves between monitors or changes resolution keeps
working because the stored dialogue box is relative to the client area.

Windows-only. The user32 calls live inside functions (invariant 7), and all
coordinates are physical pixels -- the same space mss grabs in -- because the
process is made DPI aware before anything is measured.
"""

from __future__ import annotations

import ctypes
import io
import json
import logging
import os
import sys
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy.orm import Session

from kotoba.models import Source
from kotoba.services.capture.screen import Grab, Region, displays

log = logging.getLogger(__name__)

MIN_WIDTH = 200
MIN_HEIGHT = 150

# The default dialogue band: most galgames put the box in the lower middle, and
# the user refines it once; the refinement is what gets remembered.
DEFAULT_LEFT = 0.15
DEFAULT_TOP = 0.62
DEFAULT_WIDTH = 0.70
DEFAULT_HEIGHT = 0.24


@dataclass(slots=True)
class WindowInfo:
    """One visible top-level window, in physical screen pixels."""

    handle: int
    title: str
    process: str
    pid: int
    left: int
    top: int
    width: int
    height: int
    client: tuple[int, int, int, int]  # client area: left, top, width, height
    display: int

    def to_dict(self) -> dict:
        return {
            "handle": self.handle,
            "title": self.title,
            "process": self.process,
            "pid": self.pid,
            "left": self.left,
            "top": self.top,
            "width": self.width,
            "height": self.height,
            "client": list(self.client),
            "display": self.display,
        }


def available() -> bool:
    return sys.platform == "win32"


def default_relative_region(width: int, height: int) -> dict:
    """The initial dialogue box inside a client area, before the user refines it."""
    left = round(width * DEFAULT_LEFT)
    top = round(height * DEFAULT_TOP)
    return {
        "left": left,
        "top": top,
        "width": max(1, round(width * DEFAULT_WIDTH)),
        "height": max(1, round(height * DEFAULT_HEIGHT)),
    }


def relative_from_region(region: Region, window: WindowInfo) -> dict | None:
    """`region` rewritten relative to the window's client area, or None when outside."""
    cx = region.left + region.width / 2
    cy = region.top + region.height / 2
    left, top, width, height = window.client
    if not (left <= cx < left + width and top <= cy < top + height):
        return None
    return {
        "left": region.left - left,
        "top": region.top - top,
        "width": region.width,
        "height": region.height,
    }


def region_for(window: WindowInfo, relative: dict) -> Region | None:
    """The absolute region to grab, clamped to the client area; None when unusable."""
    left, top, width, height = window.client
    rel_left = max(0, int(relative.get("left", 0)))
    rel_top = max(0, int(relative.get("top", 0)))
    if rel_left >= width or rel_top >= height:
        return None
    return Region(
        left=left + rel_left,
        top=top + rel_top,
        width=max(1, min(int(relative.get("width", 1)), width - rel_left)),
        height=max(1, min(int(relative.get("height", 1)), height - rel_top)),
        display=window.display,
    )


def parse_binding(window_json: str | None) -> dict | None:
    if not window_json:
        return None
    try:
        binding = json.loads(window_json)
    except ValueError:
        return None
    return binding if isinstance(binding, dict) and binding.get("process") else None


def region_or_none(data: dict | None) -> Region | None:
    """Build a Region from untrusted JSON, or None when it does not fit the shape."""
    if not data:
        return None
    try:
        region = Region(**data)
    except TypeError:
        return None
    if region.width <= 0 or region.height <= 0:
        return None
    return region


def saved_region(source: Source) -> Region | None:
    """The last absolute region, used when the bound window is not around."""
    if not source.region_json:
        return None
    try:
        return region_or_none(json.loads(source.region_json))
    except ValueError:
        return None


def resolve_region(
    db: Session,
    source_id: int,
    *,
    finder: Callable[..., WindowInfo | None] | None = None,
) -> Region | None:
    """Where to grab for this source: its bound window if live, else the saved region.

    The bound window wins on purpose -- that is what makes the region follow the
    game. When the window is gone (game closed), the last absolute region still
    works, so capture never fails just because the process list changed.
    """
    source = db.get(Source, source_id)
    if source is None:
        return None
    binding = parse_binding(source.window_json)
    if binding is not None:
        window = (finder or find_window)(str(binding["process"]), binding.get("title"))
        if window is not None:
            relative = binding.get("region")
            if isinstance(relative, dict):
                return region_for(window, relative)
            return region_for(window, default_relative_region(*window.client[2:]))
    return saved_region(source)


def window_for_source(
    db: Session,
    source_id: int,
    *,
    finder: Callable[..., WindowInfo | None] | None = None,
) -> WindowInfo | None:
    """The living window a source is bound to, if any."""
    source = db.get(Source, source_id)
    if source is None:
        return None
    binding = parse_binding(source.window_json)
    if binding is None:
        return None
    return (finder or find_window)(str(binding["process"]), binding.get("title"))


PW_RENDERFULLCONTENT = 0x00000002


def grab_from_window(window: WindowInfo, region: Region | None = None) -> Grab | None:
    """The window's own pixels, whatever is on top of it -- including our overlay.

    PrintWindow with PW_RENDERFULLCONTENT asks the window to render itself into
    a device context, which is the only way to read a game that another window
    covers. Returns None when the engine renders nothing (an all-black frame is
    treated as failure) or the region falls outside the client area; the caller
    then falls back to the screen grab.
    """
    if not available():
        return None
    import ctypes.wintypes as wt

    from PIL import Image

    user32 = ctypes.windll.user32
    gdi32 = ctypes.windll.gdi32
    width, height = window.width, window.height
    if width <= 0 or height <= 0 or not user32.IsWindow(window.handle):
        return None

    user32.GetWindowDC.argtypes = [wt.HWND]
    user32.GetWindowDC.restype = wt.HDC
    user32.ReleaseDC.argtypes = [wt.HWND, wt.HDC]
    user32.PrintWindow.argtypes = [wt.HWND, wt.HDC, wt.UINT]
    user32.PrintWindow.restype = wt.BOOL
    user32.IsWindow.argtypes = [wt.HWND]
    gdi32.CreateCompatibleDC.argtypes = [wt.HDC]
    gdi32.CreateCompatibleDC.restype = wt.HDC
    gdi32.CreateCompatibleBitmap.argtypes = [wt.HDC, ctypes.c_int, ctypes.c_int]
    gdi32.CreateCompatibleBitmap.restype = wt.HBITMAP
    gdi32.SelectObject.argtypes = [wt.HDC, wt.HGDIOBJ]
    gdi32.SelectObject.restype = wt.HGDIOBJ
    gdi32.DeleteObject.argtypes = [wt.HGDIOBJ]
    gdi32.DeleteDC.argtypes = [wt.HDC]
    gdi32.GetDIBits.argtypes = [
        wt.HDC,
        wt.HBITMAP,
        ctypes.c_uint,
        ctypes.c_uint,
        ctypes.c_void_p,
        ctypes.c_void_p,
        ctypes.c_uint,
    ]

    class BitmapInfoHeader(ctypes.Structure):
        _fields_ = [
            ("biSize", wt.DWORD),
            ("biWidth", wt.LONG),
            ("biHeight", wt.LONG),
            ("biPlanes", wt.WORD),
            ("biBitCount", wt.WORD),
            ("biCompression", wt.DWORD),
            ("biSizeImage", wt.DWORD),
            ("biXPelsPerMeter", wt.LONG),
            ("biYPelsPerMeter", wt.LONG),
            ("biClrUsed", wt.DWORD),
            ("biClrImportant", wt.DWORD),
        ]

    class BitmapInfo(ctypes.Structure):
        _fields_ = [("bmiHeader", BitmapInfoHeader), ("bmiColors", wt.DWORD * 3)]

    header = BitmapInfo()
    header.bmiHeader.biSize = ctypes.sizeof(BitmapInfoHeader)
    header.bmiHeader.biWidth = width
    header.bmiHeader.biHeight = -height  # top-down rows
    header.bmiHeader.biPlanes = 1
    header.bmiHeader.biBitCount = 32
    buffer = ctypes.create_string_buffer(width * height * 4)

    window_dc = user32.GetWindowDC(window.handle)
    if not window_dc:
        return None
    memory_dc = gdi32.CreateCompatibleDC(window_dc)
    bitmap = gdi32.CreateCompatibleBitmap(window_dc, width, height)
    if not memory_dc or not bitmap:
        user32.ReleaseDC(window.handle, window_dc)
        return None
    previous = gdi32.SelectObject(memory_dc, bitmap)
    try:
        if not user32.PrintWindow(window.handle, memory_dc, PW_RENDERFULLCONTENT):
            return None
        gdi32.GetDIBits(memory_dc, bitmap, 0, height, buffer, ctypes.byref(header), 0)
    finally:
        gdi32.SelectObject(memory_dc, previous)
        gdi32.DeleteObject(bitmap)
        gdi32.DeleteDC(memory_dc)
        user32.ReleaseDC(window.handle, window_dc)

    image = Image.frombuffer("RGBA", (width, height), buffer, "raw", "BGRA", 0, 1).convert("RGB")
    client_left, client_top, client_width, client_height = window.client
    offset_x, offset_y = client_left - window.left, client_top - window.top
    image = image.crop((offset_x, offset_y, offset_x + client_width, offset_y + client_height))
    if region is not None:
        left, top = region.left - client_left, region.top - client_top
        right, bottom = left + region.width, top + region.height
        if left < 0 or top < 0 or right > client_width or bottom > client_height:
            return None
        image = image.crop((left, top, right, bottom))

    if image.getextrema() == ((0, 0), (0, 0), (0, 0)):
        return None  # the engine painted nothing; let the caller grab the screen
    out = io.BytesIO()
    image.save(out, format="PNG", optimize=False)
    return Grab(png=out.getvalue(), width=image.width, height=image.height, scale=1.0)


def list_windows(
    *,
    fetch: Callable[[], list[dict]] | None = None,
    displays_fn: Callable[[], Sequence[dict]] | None = None,
) -> list[WindowInfo]:
    """Visible, sizable, self-owned windows; biggest first, so games come first."""
    raw = (fetch or _enumerate_raw)()
    monitors = list((displays_fn or displays)())
    own = os.getpid()
    windows = [
        _window_info(entry, monitors)
        for entry in raw
        if entry["pid"] != own and entry["width"] >= MIN_WIDTH and entry["height"] >= MIN_HEIGHT
    ]
    windows.sort(key=lambda w: w.width * w.height, reverse=True)
    return windows


def find_window(
    process: str,
    title: str | None = None,
    *,
    fetch: Callable[[], list[dict]] | None = None,
    displays_fn: Callable[[], Sequence[dict]] | None = None,
) -> WindowInfo | None:
    """The best living window for a process: exact title first, then a prefix, then any."""
    wanted = process.lower()
    candidates = [
        w for w in list_windows(fetch=fetch, displays_fn=displays_fn) if w.process.lower() == wanted
    ]
    if not candidates:
        return None
    if title:
        exact = [w for w in candidates if w.title == title]
        if exact:
            return exact[0]
        prefixed = [w for w in candidates if w.title.startswith(title)]
        if prefixed:
            return prefixed[0]
    return candidates[0]


def _window_info(entry: dict, monitors: Sequence[dict]) -> WindowInfo:
    window = WindowInfo(
        handle=entry["handle"],
        title=entry["title"],
        process=entry["process"],
        pid=entry["pid"],
        left=entry["left"],
        top=entry["top"],
        width=entry["width"],
        height=entry["height"],
        client=(
            entry["client_left"],
            entry["client_top"],
            entry["client_width"],
            entry["client_height"],
        ),
        display=_display_index(entry, monitors),
    )
    return window


def _display_index(entry: dict, monitors: Sequence[dict]) -> int:
    """The monitor with the largest overlap; the first one when there is none."""
    best = 0
    best_area = 0
    right = entry["left"] + entry["width"]
    bottom = entry["top"] + entry["height"]
    for monitor in monitors:
        m_right = monitor["left"] + monitor["width"]
        m_bottom = monitor["top"] + monitor["height"]
        overlap = max(0, min(right, m_right) - max(entry["left"], monitor["left"])) * max(
            0, min(bottom, m_bottom) - max(entry["top"], monitor["top"])
        )
        if overlap > best_area:
            best_area = overlap
            best = monitor["index"]
    return best


def _ensure_dpi_aware() -> None:
    """Physical pixels only: without this, coordinates are virtualized and mss disagrees."""
    if not available():
        return
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)  # PER_MONITOR_DPI_AWARE
    except Exception:  # noqa: BLE001 - already set, or Windows 8.1 shcore missing
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:  # noqa: BLE001 - the 8.1 fallback too; neither API may exist
            log.debug("could not set DPI awareness", exc_info=True)


def _enumerate_raw() -> list[dict]:
    """Every visible, titled, unowned top-level window; the only ctypes-heavy part."""
    import ctypes.wintypes as wt

    _ensure_dpi_aware()
    user32 = ctypes.windll.user32
    dwmapi = ctypes.windll.dwmapi
    kernel32 = ctypes.windll.kernel32

    user32.GetWindowLongW.restype = ctypes.c_long
    user32.GetWindowLongW.argtypes = [wt.HWND, ctypes.c_int]
    user32.GetWindowThreadProcessId.argtypes = [wt.HWND, ctypes.POINTER(wt.DWORD)]
    user32.GetWindowTextLengthW.argtypes = [wt.HWND]
    user32.GetWindowTextW.argtypes = [wt.HWND, wt.LPWSTR, ctypes.c_int]
    user32.IsWindowVisible.argtypes = [wt.HWND]
    user32.IsIconic.argtypes = [wt.HWND]
    user32.GetWindow.argtypes = [wt.HWND, wt.UINT]
    user32.EnumWindows.argtypes = [ctypes.WINFUNCTYPE(wt.BOOL, wt.HWND, wt.LPARAM), wt.LPARAM]

    PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
    GWL_EXSTYLE = -20
    GW_OWNER = 4
    DWMWA_EXTENDED_FRAME_BOUNDS = 9
    WS_EX_TOOLWINDOW = 0x00000080

    class RECT(ctypes.Structure):
        _fields_ = [("left", wt.LONG), ("top", wt.LONG), ("right", wt.LONG), ("bottom", wt.LONG)]

    def process_name(pid: int) -> str:
        handle = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
        if not handle:
            return ""
        try:
            buf = ctypes.create_unicode_buffer(1024)
            size = wt.DWORD(1024)
            if kernel32.QueryFullProcessImageNameW(handle, 0, buf, ctypes.byref(size)):
                return Path(buf.value).name
            return ""
        finally:
            kernel32.CloseHandle(handle)

    results: list[dict] = []

    @ctypes.WINFUNCTYPE(wt.BOOL, wt.HWND, wt.LPARAM)
    def visit(hwnd: int, _lparam: int) -> bool:
        if not user32.IsWindowVisible(hwnd) or user32.IsIconic(hwnd):
            return True
        if user32.GetWindow(hwnd, GW_OWNER):
            return True
        if user32.GetWindowLongW(hwnd, GWL_EXSTYLE) & WS_EX_TOOLWINDOW:
            return True
        length = user32.GetWindowTextLengthW(hwnd)
        if length == 0:
            return True
        title_buf = ctypes.create_unicode_buffer(length + 1)
        user32.GetWindowTextW(hwnd, title_buf, length + 1)
        frame = RECT()
        if (
            dwmapi.DwmGetWindowAttribute(
                hwnd, DWMWA_EXTENDED_FRAME_BOUNDS, ctypes.byref(frame), ctypes.sizeof(frame)
            )
            != 0
        ):
            user32.GetWindowRect(hwnd, ctypes.byref(frame))
        pid = wt.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        client = RECT()
        user32.GetClientRect(hwnd, ctypes.byref(client))
        origin = wt.POINT(0, 0)
        user32.ClientToScreen(hwnd, ctypes.byref(origin))
        results.append(
            {
                "handle": int(hwnd),
                "title": title_buf.value,
                "process": process_name(pid.value),
                "pid": int(pid.value),
                "left": frame.left,
                "top": frame.top,
                "width": frame.right - frame.left,
                "height": frame.bottom - frame.top,
                "client_left": origin.x,
                "client_top": origin.y,
                "client_width": client.right - client.left,
                "client_height": client.bottom - client.top,
            }
        )
        return True

    user32.EnumWindows(visit, 0)
    return [entry for entry in results if entry["process"]]
