"""Entry point of the frozen build: `Kotobako.exe [serve] [options]`.

Double-clicking the exe has no arguments and starts the server on the default
port; `Kotobako.exe --port 9000` (or any other `serve` flag) still works.
"""

from __future__ import annotations

import multiprocessing
import sys

from kotoba.cli import main

if __name__ == "__main__":
    multiprocessing.freeze_support()
    raise SystemExit(main(sys.argv[1:] or ["serve"]))
