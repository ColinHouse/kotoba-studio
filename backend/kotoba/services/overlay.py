"""A topmost overlay that puts the current line's words inside the game.

Windows-only, built on tkinter (stdlib) so it adds no dependency; the pywebview
shell (#60) may replace it later. Exclusive fullscreen will not show it --
windowed and borderless do, and the settings page says so.

Design notes:

- The Tk thread owns every widget call. Other threads only enqueue commands, so
  the hotkey can toggle the window without touching Tk from a foreign thread.
- Transparent areas use tkinter's colour-key transparency; on Windows those
  pixels are also click-through, so the panel is interactive while the rest of
  the overlay never blocks the game.
- The overlay never writes lines. It reads the active session's latest line,
  offers the same dictionary candidates the inbox shows, and its 收藏 button
  records an Encounter -- the same service call the inbox's first step makes.
"""

from __future__ import annotations

import json
import logging
import queue
import sys
import threading
from collections.abc import Callable
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from kotoba.core.errors import ApiError
from kotoba.models import CaptureSession, Line, Source
from kotoba.services import learning, settings_store
from kotoba.services.capture import windows
from kotoba.services.capture.screen import Region
from kotoba.services.text import analysis

log = logging.getLogger(__name__)

DEFAULT_HOTKEY = "Ctrl+Shift+O"
POLL_MS = 600
GAP = 14
PANEL_MIN_WIDTH = 520
PANEL_MAX_WIDTH = 980

# The dark-theme palette from frontend/src/style.css, so the overlay reads as
# the same product. KEY_COLOR is deliberately a colour no theme uses: on Windows
# tkinter punches it out entirely (and lets clicks through).
KEY_COLOR = "#010203"
INK = "#eae7e7"
PAPER = "#211f1e"
INK_SOFT = "#9b9797"
ACCENT = "#e1ad66"
FONT = "Yu Gothic UI"


@dataclass(slots=True)
class OverlayWord:
    surface: str
    headword: str
    reading: str
    start: int
    end: int
    content: bool
    term_id: int | None
    known: bool
    meanings: list[str]


def _first_gloss(sense: dict) -> str:
    for key in ("gloss_zh", "gloss_en"):
        values = sense.get(key) or []
        if values:
            return str(values[0])
    return ""


def overlay_words(analysis_result: dict) -> list[OverlayWord]:
    """What the overlay renders: one entry per token, candidates condensed to glosses."""
    words: list[OverlayWord] = []
    for token in analysis_result.get("tokens", []):
        candidates = token.get("candidates") or []
        top = candidates[0] if candidates else {}
        meanings: list[str] = []
        for candidate in candidates[:3]:
            label = candidate.get("headword") or token.get("base") or token.get("surface", "")
            gloss = ""
            for sense in candidate.get("senses") or []:
                gloss = _first_gloss(sense)
                if gloss:
                    break
            if gloss:
                meanings.append(f"{label}｜{gloss}")
        words.append(
            OverlayWord(
                surface=token.get("surface", ""),
                headword=top.get("headword") or token.get("base") or token.get("surface", ""),
                reading=top.get("reading")
                or token.get("reading_base")
                or token.get("reading")
                or "",
                start=int(token.get("start", 0)),
                end=int(token.get("end", 0)),
                content=bool(token.get("is_content")),
                term_id=token.get("term_id"),
                known=token.get("known_status") == "known",
                meanings=meanings,
            )
        )
    return words


def latest_line(db: Session, session_id: int | None) -> Line | None:
    if session_id is None:
        return None
    return db.scalar(
        select(Line).where(Line.session_id == session_id).order_by(Line.id.desc()).limit(1)
    )


def current_words(db: Session, session_id: int | None) -> tuple[Line | None, list[OverlayWord]]:
    line = latest_line(db, session_id)
    if line is None:
        return None, []
    return line, overlay_words(analysis.analyze_line(db, line))


def overlay_position(
    region: Region | None, size: tuple[int, int], screen: tuple[int, int]
) -> tuple[int, int]:
    """Above the dialogue box when it fits, below it otherwise, clamped to the screen."""
    width, height = size
    screen_w, screen_h = screen
    if region is not None:
        x = region.left
        y = region.top - height - GAP
        if y < 0:
            y = region.top + region.height + GAP
    else:
        x = (screen_w - width) // 2
        y = screen_h - height - 140
    x = max(0, min(x, max(0, screen_w - width)))
    y = max(0, min(y, max(0, screen_h - height)))
    return x, y


def apply_user_position(
    user: tuple[int, int] | None,
    auto: tuple[int, int],
    size: tuple[int, int],
    screen: tuple[int, int],
) -> tuple[int, int]:
    """Where the panel actually goes: a spot the user dragged to beats the computed one.

    The override has to be applied on every refresh, not once, because the panel is
    repositioned each time a line arrives -- without this the next line would snap it
    straight back and the drag would look broken.

    Still clamped: the user can let go half off the edge, and a saved spot can end up
    outside after the resolution changes.
    """
    if user is None:
        return auto
    width, height = size
    screen_w, screen_h = screen
    x = max(0, min(user[0], max(0, screen_w - width)))
    y = max(0, min(user[1], max(0, screen_h - height)))
    return x, y


def save_word(db: Session, line: Line, word: OverlayWord) -> dict:
    """The 收藏 button: the same Encounter the inbox creates on its first step."""
    encounter = learning.add_encounter(
        db,
        line_id=line.id,
        headword=word.headword,
        reading=word.reading,
        surface=word.surface,
        span_start=word.start,
        span_end=word.end,
    )
    db.commit()
    return {"encounter_id": encounter.id, "term_id": encounter.term_id}


def _screen_size() -> tuple[int, int]:
    if sys.platform == "win32":
        import ctypes

        user32 = ctypes.windll.user32
        return int(user32.GetSystemMetrics(0)), int(user32.GetSystemMetrics(1))
    return 1920, 1080


class TkOverlay:
    """The window itself. Every method here runs on the Tk thread."""

    def __init__(
        self,
        snapshot: Callable[[], tuple[str, list[OverlayWord]] | None],
        save: Callable[[OverlayWord], dict],
        position: Callable[[tuple[int, int]], tuple[int, int, int]],
        load_position: Callable[[], tuple[int, int] | None] | None = None,
        store_position: Callable[[tuple[int, int] | None], None] | None = None,
    ) -> None:
        self._snapshot = snapshot
        self._save = save
        self._position = position
        self._load_position = load_position or (lambda: None)
        self._store_position = store_position or (lambda position: None)
        self._commands: queue.Queue[str] = queue.Queue()
        self._root = None
        self._visible = False
        self._words: list[OverlayWord] = []
        self._selected = -1
        self._collected: set[tuple[int, int]] = set()
        self._fingerprint: tuple | None = None
        self.last_error: str | None = None

    @property
    def visible(self) -> bool:
        return self._visible

    def command(self, name: str) -> None:
        self._commands.put(name)

    def run(self) -> None:
        import tkinter as tk

        root = tk.Tk()
        self._root = root
        self._user_position: tuple[int, int] | None = self._load_position()
        self._drag_from: tuple[int, int] | None = None
        self._drag_origin: tuple[int, int] = (0, 0)
        root.withdraw()
        root.overrideredirect(True)
        root.attributes("-topmost", True)
        root.attributes("-alpha", 0.97)
        root.configure(bg=KEY_COLOR)
        if sys.platform == "win32":
            root.attributes("-transparentcolor", KEY_COLOR)
        self._make_tool_window(root)

        self._panel = tk.Frame(root, bg=PAPER, highlightthickness=1, highlightbackground=ACCENT)
        self._panel.pack(fill="both", expand=True)
        title = tk.Label(
            self._panel,
            text="覆盖层 · 当前句",
            fg=ACCENT,
            bg=PAPER,
            font=(FONT, 10),
            anchor="w",
            cursor="fleur",
        )
        title.pack(fill="x", padx=12, pady=(8, 0))
        # Dragged by the title, the way a title bar works -- the window has no frame
        # of its own (overrideredirect). Deliberately not bound on the whole panel:
        # the words carry their own <Button-1> for picking, and a drag that also
        # picked a word would make both feel unreliable. Double-click gives the
        # automatic position back; the release persists what the drag left behind.
        for widget in (title, self._panel):
            widget.bind("<Button-1>", self._drag_start)
            widget.bind("<B1-Motion>", self._drag_move)
            widget.bind("<ButtonRelease-1>", self._drag_end)
            widget.bind("<Double-Button-1>", self._drag_reset)
        self._line = tk.Label(
            self._panel,
            text="等待采集…",
            fg=INK,
            bg=PAPER,
            font=(FONT, 12),
            justify="left",
            anchor="w",
            wraplength=PANEL_MAX_WIDTH - 24,
        )
        self._line.pack(fill="x", padx=12, pady=(2, 4))
        self._text = tk.Text(
            self._panel,
            height=1,
            wrap="word",
            bg=PAPER,
            fg=INK,
            font=(FONT, 15),
            relief="flat",
            highlightthickness=0,
            cursor="hand2",
            padx=0,
            pady=0,
        )
        self._text.pack(fill="x", padx=12)
        self._text.configure(state="disabled")
        self._meaning = tk.Label(
            self._panel,
            text="点一个词看释义，再按「收藏这个词」。",
            fg=INK_SOFT,
            bg=PAPER,
            font=(FONT, 11),
            justify="left",
            anchor="w",
            wraplength=PANEL_MAX_WIDTH - 24,
        )
        self._meaning.pack(fill="x", padx=12, pady=(6, 6))
        buttons = tk.Frame(self._panel, bg=PAPER)
        buttons.pack(fill="x", padx=12, pady=(0, 10))
        self._collect = tk.Button(
            buttons,
            text="收藏这个词",
            command=self._on_collect,
            bg=ACCENT,
            fg="#1b1a18",
            relief="flat",
            font=(FONT, 11),
            padx=12,
            state="disabled",
        )
        self._collect.pack(side="left")
        self._status = tk.Label(buttons, text="", fg=INK_SOFT, bg=PAPER, font=(FONT, 10))
        self._status.pack(side="left", padx=10)
        tk.Button(
            buttons,
            text="隐藏",
            command=lambda: self.command("hide"),
            bg=PAPER,
            fg=INK_SOFT,
            relief="flat",
            font=(FONT, 10),
        ).pack(side="right")

        root.after(POLL_MS, self._tick)
        root.mainloop()

    @staticmethod
    def _make_tool_window(root) -> None:
        """Keep it out of Alt-Tab and never steal focus from the game."""
        if sys.platform != "win32":
            return
        import ctypes

        user32 = ctypes.windll.user32
        hwnd = user32.GetParent(root.winfo_id()) or root.winfo_id()
        GWL_EXSTYLE = -20
        WS_EX_TOOLWINDOW = 0x00000080
        WS_EX_NOACTIVATE = 0x08000000
        style = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
        user32.SetWindowLongW(hwnd, GWL_EXSTYLE, style | WS_EX_TOOLWINDOW | WS_EX_NOACTIVATE)

    def _drain(self) -> None:
        while True:
            try:
                command = self._commands.get_nowait()
            except queue.Empty:
                return
            if command == "quit":
                self._root.destroy()
                self._root = None
                return
            if command == "toggle":
                command = "hide" if self._visible else "show"
            if command == "show":
                self._visible = True
                self._fingerprint = None
                self._root.deiconify()
                self._root.lift()
            elif command == "hide":
                self._visible = False
                self._root.withdraw()

    def _tick(self) -> None:
        try:
            self._drain()
            if self._visible and self._root is not None:
                self._refresh()
                self.last_error = None
        except Exception as exc:  # noqa: BLE001 - the overlay must never kill the server
            self.last_error = str(exc)
            log.warning("overlay refresh failed", exc_info=True)
        finally:
            if self._root is not None:
                self._root.after(POLL_MS, self._tick)

    def _drag_start(self, event) -> None:
        if self._root is None:
            return
        self._drag_from = (event.x_root, event.y_root)
        self._drag_origin = (self._root.winfo_x(), self._root.winfo_y())

    def _drag_move(self, event) -> None:
        if self._root is None or self._drag_from is None:
            return
        x = self._drag_origin[0] + (event.x_root - self._drag_from[0])
        y = self._drag_origin[1] + (event.y_root - self._drag_from[1])
        size = (self._root.winfo_width(), self._root.winfo_height())
        x, y = apply_user_position((x, y), (x, y), size, _screen_size())
        self._user_position = (x, y)
        self._root.geometry(f"+{x}+{y}")

    def _drag_end(self, _event=None) -> None:
        """A drag is only persisted once the button is released.

        Tk's implicit grab delivers the release to the widget the press started
        on even when the pointer is already outside the panel, so a fast drag
        still lands here. A plain click moves nothing and saves nothing.
        """
        self._drag_from = None
        if self._user_position is not None:
            self._store_position(self._user_position)

    def _drag_reset(self, _event=None) -> None:
        """Back to sitting above the dialogue box, forgetting the saved spot too."""
        self._drag_from = None
        self._user_position = None
        self._store_position(None)
        self._refresh()

    def _refresh(self) -> None:
        snapshot = self._snapshot()
        if snapshot is None:
            line_text, words = "等待采集…", []
        else:
            line_text, words = snapshot
        fingerprint = (
            line_text,
            tuple((w.surface, w.known, (w.start, w.end) in self._collected) for w in words),
        )
        if fingerprint != self._fingerprint:
            self._fingerprint = fingerprint
            self._words = words
            if words:
                self._line.pack_forget()  # the token row is the line; no duplicate line
            else:
                self._line.configure(text=line_text)
                self._line.pack(fill="x", padx=12, pady=(2, 4), before=self._text)
            if self._selected >= len(words):
                self._selected = -1
                self._collect.configure(state="disabled")
                self._meaning.configure(text="点一个词看释义，再按「收藏这个词」。")
            self._render_words()

        width = PANEL_MIN_WIDTH
        self._root.update_idletasks()
        height = max(120, self._panel.winfo_reqheight())
        x, y, width = self._position((width, height))
        # Applied on every refresh, not once: _position() recomputes from the dialogue
        # region each time a line arrives, so a drag would otherwise last 600ms.
        # A position saved for this work arrives by the same path, which is also
        # what clamps it back on screen after a resolution change.
        user = self._user_position if self._user_position is not None else self._load_position()
        x, y = apply_user_position(user, (x, y), (width, height), _screen_size())
        self._line.configure(wraplength=width - 24)
        self._meaning.configure(wraplength=width - 24)
        self._root.geometry(f"{width}x{height}+{x}+{y}")

    def _render_words(self) -> None:
        text = self._text
        text.configure(state="normal")
        text.delete("1.0", "end")
        for index, word in enumerate(self._words):
            tag = f"w{index}"
            text.insert("end", word.surface, (tag,))
            if (word.start, word.end) in self._collected:
                text.tag_configure(tag, foreground=ACCENT)
            elif index == self._selected:
                text.tag_configure(tag, foreground=INK, underline=True)
            elif word.known or not word.content:
                text.tag_configure(tag, foreground=INK_SOFT)
            else:
                text.tag_configure(tag, foreground=INK)
            text.tag_bind(tag, "<Button-1>", lambda _event, i=index: self._pick(i))
        text.configure(state="disabled")

    def _pick(self, index: int) -> None:
        if index < 0 or index >= len(self._words):
            self._selected = -1
            self._collect.configure(state="disabled")
            self._meaning.configure(text="点一个词看释义，再按「收藏这个词」。")
        else:
            self._selected = index
            word = self._words[index]
            detail = "\n".join(word.meanings) or "词典里没有这个词的条目"
            self._meaning.configure(text=f"{word.headword}【{word.reading}】\n{detail}")
            self._collect.configure(state="normal")
        self._render_words()

    def _on_collect(self) -> None:
        if self._selected < 0:
            return
        word = self._words[self._selected]
        try:
            saved = self._save(word)
        except ApiError as exc:
            self._status.configure(text=exc.message)
            return
        except Exception as exc:  # noqa: BLE001 - show it, do not die
            self._status.configure(text=str(exc))
            return
        self._collected.add((word.start, word.end))
        self._status.configure(text=f"已收藏 #{saved['encounter_id']}")
        self._render_words()


class OverlayController:
    """Start/stop the window and answer status; the Tk thread does the rest."""

    def __init__(
        self,
        session_factory: Callable[[], Session],
        *,
        view_factory: Callable[..., TkOverlay] | None = None,
    ) -> None:
        self._session_factory = session_factory
        self._view_factory = view_factory or TkOverlay
        self._view: TkOverlay | None = None
        self._thread: threading.Thread | None = None
        self.last_error: str | None = None

    def available(self) -> tuple[bool, str | None]:
        if sys.platform != "win32":
            return False, "覆盖层目前只支持 Windows"
        try:
            import tkinter  # noqa: F401
        except Exception as exc:  # noqa: BLE001 - a missing or broken tkinter means no overlay, not a crash
            return False, f"缺少 tkinter：{exc}"
        return True, None

    @property
    def running(self) -> bool:
        thread = self._thread
        return thread is not None and thread.is_alive()

    @property
    def visible(self) -> bool:
        return self._view is not None and self._view.visible

    def start(self) -> bool:
        if self.running:
            return False
        ok, note = self.available()
        if not ok:
            self.last_error = note
            return False
        view = self._view_factory(
            self._snapshot,
            self._save,
            self._position,
            self._load_position,
            self._store_position,
        )
        self._view = view
        self._thread = threading.Thread(target=self._run, args=(view,), name="overlay", daemon=True)
        self._thread.start()
        view.command("show")  # enabling the overlay should show it; the hotkey hides it
        self.last_error = None
        return True

    def stop(self, timeout: float = 3.0) -> None:
        view, thread = self._view, self._thread
        self._view = None
        self._thread = None
        if view is None:
            return
        view.command("quit")
        if thread is not None:
            thread.join(timeout)

    def toggle(self) -> bool:
        if self._view is not None:
            self._view.command("toggle")
        return True

    def show(self) -> bool:
        if self._view is not None:
            self._view.command("show")
        return True

    def hide(self) -> bool:
        if self._view is not None:
            self._view.command("hide")
        return True

    def status(self) -> dict:
        ok, note = self.available()
        return {
            "available": ok,
            "note": note,
            "running": self.running,
            "visible": self.visible,
            "last_error": self.last_error,
        }

    def _run(self, view: TkOverlay) -> None:
        try:
            view.run()
        except Exception as exc:  # noqa: BLE001 - keep the reason for the UI
            self.last_error = str(exc)
            log.warning("overlay window failed", exc_info=True)

    # Callbacks used by the view; they run on the Tk thread.

    def _snapshot(self) -> tuple[str, list[OverlayWord]] | None:
        db = self._session_factory()
        try:
            session_id = settings_store.get(db, "active_session_id")
            line, words = current_words(db, session_id)
            return (line.text, words) if line is not None else None
        finally:
            db.close()

    def _save(self, word: OverlayWord) -> dict:
        db = self._session_factory()
        try:
            session_id = settings_store.get(db, "active_session_id")
            line = latest_line(db, session_id)
            if line is None:
                raise ApiError("no_line", "当前没有可收藏的句子")
            return save_word(db, line, word)
        finally:
            db.close()

    def _position(self, size: tuple[int, int]) -> tuple[int, int, int]:
        region: Region | None = None
        db = self._session_factory()
        try:
            session_id = settings_store.get(db, "active_session_id")
            session = db.get(CaptureSession, session_id) if session_id is not None else None
            if session is not None and session.source_id is not None:
                region = windows.resolve_region(db, session.source_id)
        except Exception:  # noqa: BLE001 - a positioning hiccup must not stop the overlay
            log.debug("overlay could not resolve the dialogue region", exc_info=True)
        finally:
            db.close()
        width = size[0]
        if region is not None:
            width = max(PANEL_MIN_WIDTH, min(region.width, PANEL_MAX_WIDTH))
        x, y = overlay_position(region, (width, size[1]), _screen_size())
        return x, y, width

    # Position persistence: one spot per work when the session is bound to one,
    # a single global fallback otherwise. Resolved on every call so switching
    # works picks up that work's spot without restarting the overlay.

    def _position_scope(self, db: Session) -> tuple[str, int]:
        session_id = settings_store.get(db, "active_session_id")
        session = db.get(CaptureSession, session_id) if session_id is not None else None
        if session is not None and session.source_id is not None:
            return "source", session.source_id
        return "global", 0

    def _load_position(self) -> tuple[int, int] | None:
        db = self._session_factory()
        try:
            scope, key = self._position_scope(db)
            if scope == "source":
                source = db.get(Source, key)
                data = json.loads(source.overlay_position_json or "null")
            else:
                data = settings_store.get(db, "overlay_position")
            if not isinstance(data, dict):
                return None
            return int(data["x"]), int(data["y"])
        except Exception:  # noqa: BLE001 - a broken saved spot must not stop the overlay
            log.debug("overlay could not load a saved position", exc_info=True)
            return None
        finally:
            db.close()

    def _store_position(self, position: tuple[int, int] | None) -> None:
        data = None if position is None else {"x": int(position[0]), "y": int(position[1])}
        db = self._session_factory()
        try:
            scope, key = self._position_scope(db)
            if scope == "source":
                source = db.get(Source, key)
                if source is not None:
                    source.overlay_position_json = json.dumps(data) if data else None
            else:
                settings_store.set_value(db, "overlay_position", data)
            db.commit()
        except Exception:  # noqa: BLE001 - losing a spot is not worth killing the overlay
            db.rollback()
            log.debug("overlay could not store the dragged position", exc_info=True)
        finally:
            db.close()
