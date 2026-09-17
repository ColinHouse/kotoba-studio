# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for the Windows onedir build.

Run through ``packaging/build.py`` (or ``make package-windows``) rather than by
hand: the frontend has to be built first, and the smoke test afterwards is what
says the bundle actually works. See ``packaging/README.md``.
"""

from pathlib import Path

from PyInstaller.utils.hooks import (
    collect_data_files,
    collect_dynamic_libs,
    get_package_paths,
)

ROOT = Path(SPECPATH).resolve().parent
FRONTEND_DIST = ROOT / "frontend" / "dist"

datas = []
binaries = []
hiddenimports = []

# The SPA is served from `_MEIPASS/frontend/dist`, which is exactly where
# kotoba.spa.default_dist() looks when the app is frozen.
datas += [(str(FRONTEND_DIST), "frontend/dist")]

# Bundled JSON (contractions, homograph traps, the JMdict test fixture) and the
# Alembic scripts, which Alembic executes from disk instead of importing.
datas += collect_data_files(
    "kotoba",
    include_py_files=True,
    includes=["data/*.json", "data/*.png", "migrations/**/*"],
)

# unidic-lite is the tokenizer dictionary (~250 MB) and fugashi looks it up as a
# package, so it has to stay at `unidic_lite/dicdir` inside the bundle.
datas += collect_data_files("unidic_lite")

# delvewheel keeps MeCab's DLL outside the fugashi package directory; the
# patched fugashi/__init__.py adds `../fugashi.libs` to the DLL search path,
# so the bundle needs the DLL at that relative location.
_pkg_base, _pkg_dir = get_package_paths("fugashi")
for _dll in (Path(_pkg_base) / "fugashi.libs").glob("*.dll"):
    binaries.append((str(_dll), "fugashi.libs"))
binaries += collect_dynamic_libs("winrt")

hiddenimports += [
    # Everything below is imported lazily, so static analysis cannot see it
    # (invariant 7 keeps the app bootable without the platform pieces).
    "kotoba.app",  # uvicorn.run("kotoba.app:app") imports this by name
    "unidic_lite",  # fugashi imports it from its compiled extension
    "tkinter",  # the game overlay imports it inside the view
    "winocr",
    "mss",
    "pyperclip",
    "segno",
    "keyring",
    "keyring.backends.Windows",
    "pynput.keyboard._win32",
    "pynput._util.win32",
    "winrt.system",
    "winrt.runtime",
    "winrt.windows.foundation",
    "winrt.windows.foundation.collections",
    "winrt.windows.globalization",
    "winrt.windows.graphics.imaging",
    "winrt.windows.media.ocr",
    "winrt.windows.storage.streams",
]

a = Analysis(  # noqa: F821 - Analysis is injected by PyInstaller
    ["entrypoint.py"],
    pathex=[str(ROOT / "backend")],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    excludes=[
        # Optional features that would add hundreds of MB: the FSRS optimizer
        # pulls torch, the ONNX OCR engine is a separate download.
        "torch",
        "torchaudio",
        "torchvision",
        "rapidocr",
        "onnxruntime",
        "matplotlib",
    ],
    noarchive=False,
)
pyz = PYZ(a.pure)  # noqa: F821

exe = EXE(  # noqa: F821
    pyz,
    a.scripts,
    exclude_binaries=True,
    name="Kotobako",
    console=True,
    disable_windowed_traceback=False,
    icon=str(ROOT / "assets" / "kotoba.ico"),
)
coll = COLLECT(  # noqa: F821
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name="Kotobako",
)
