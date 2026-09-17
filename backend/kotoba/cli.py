"""Command line interface."""

from __future__ import annotations

import argparse
import os
import threading
import webbrowser

import uvicorn

from kotoba.core.config import get_settings


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="kotoba", description="Kotoba Studio server")
    sub = parser.add_subparsers(dest="command")
    serve = sub.add_parser("serve", help="run the API and web server")
    serve.add_argument(
        "--host", default=None, help="bind address (0.0.0.0 to reach it from a phone)"
    )
    serve.add_argument("--port", type=int, default=None)
    serve.add_argument("--data-dir", default=None, help="override the data directory")
    serve.add_argument("--open", action="store_true", help="open the web UI in a browser")
    serve.add_argument("--reload", action="store_true", help="auto-reload (development)")
    desktop = sub.add_parser(
        "desktop", help="run the API and open the desktop window (needs the `desktop` extra)"
    )
    desktop.add_argument("--port", type=int, default=None)
    desktop.add_argument("--data-dir", default=None, help="override the data directory")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "desktop":
        from kotoba.desktop.shell import run_cli

        return run_cli(args.data_dir, args.port)
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

    if args.open:
        host = "127.0.0.1" if settings.host in ("0.0.0.0", "::", "") else settings.host
        url = f"http://{host}:{settings.port}/"
        threading.Timer(1.0, lambda: webbrowser.open(url)).start()

    uvicorn.run(
        "kotoba.app:app",
        factory=True,
        host=settings.host,
        port=settings.port,
        log_level="info",
        reload=args.reload,
    )
    return 0
