"""Health, instance metadata and LAN connection info."""

from __future__ import annotations

import platform
import socket

from fastapi import APIRouter, Request

from kotoba import __version__

router = APIRouter(tags=["meta"])


@router.get("/health")
def health() -> dict:
    return {"status": "ok", "version": __version__, "platform": platform.system().lower()}


def lan_ips() -> list[str]:
    ips: list[str] = []
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("10.255.255.255", 1))
            ips.append(s.getsockname()[0])
    except OSError:
        pass
    try:
        for info in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET):
            ip = info[4][0]
            if ip not in ips and not ip.startswith("127."):
                ips.append(ip)
    except OSError:
        pass
    return ips


@router.get("/connect-info")
def connect_info(request: Request) -> dict:
    import segno

    settings = request.app.state.settings
    port = settings.port
    lan_enabled = settings.host in ("0.0.0.0", "::", "")
    urls = [f"http://{ip}:{port}/" for ip in lan_ips()]
    primary = urls[0] if urls else f"http://127.0.0.1:{port}/"
    qr = segno.make(primary, error="m").svg_inline(scale=6, border=1, dark="#2b2a28")
    return {
        "urls": urls,
        "primary_url": primary,
        "qr_svg": qr,
        "port": port,
        "host": settings.host,
        "lan_enabled": lan_enabled,
        "hint": None
        if lan_enabled
        else "服务器当前只监听本机。用 `kotoba serve --host 0.0.0.0` 启动后手机才能访问。",
    }
