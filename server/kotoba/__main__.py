"""Command line entry point: `python -m kotoba serve`."""

from __future__ import annotations

import argparse
import os
import threading
import webbrowser

import uvicorn

from kotoba.config import get_settings


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="kotoba", description="Kotoba Studio server")
    sub = parser.add_subparsers(dest="command")
    serve = sub.add_parser("serve", help="run the API + web server")
    serve.add_argument("--host", default=None, help="bind address (0.0.0.0 for LAN access)")
    serve.add_argument("--port", type=int, default=None)
    serve.add_argument("--open", action="store_true", help="open the web UI in a browser")
    serve.add_argument("--data-dir", default=None, help="override the data directory")
    serve.add_argument("--reload", action="store_true", help="auto-reload (development)")
    args = parser.parse_args(argv)

    if args.command != "serve":
        parser.print_help()
        return 1

    if args.data_dir:
        os.environ["KOTOBA_DATA_DIR"] = args.data_dir
    if args.host:
        os.environ["KOTOBA_HOST"] = args.host
    if args.port:
        os.environ["KOTOBA_PORT"] = str(args.port)
    get_settings.cache_clear()
    settings = get_settings()
    host, port = settings.host, settings.port
    if args.open:
        url = f"http://{'127.0.0.1' if host == '0.0.0.0' else host}:{port}/"
        threading.Timer(1.0, lambda: webbrowser.open(url)).start()
    uvicorn.run(
        "kotoba.main:app",
        factory=True,
        host=host,
        port=port,
        log_level="info",
        reload=args.reload,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
