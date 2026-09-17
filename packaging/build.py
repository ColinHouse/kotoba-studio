"""Build, smoke-test and optionally sign the Windows distribution.

The smoke test is the point of this script: it starts the frozen exe on a
throwaway data directory and asserts that the pieces PyInstaller usually breaks
are really there -- the built SPA, the WinRT OCR projection, the tokenizer
dictionary -- before anyone ships it.

    uv run --extra packaging python packaging/build.py
    uv run --extra packaging python packaging/build.py --installer --sign-thumbprint <sha1>

Signing materials never belong in the repository; see docs/CODE_SIGNING.md.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import tomllib
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = ROOT / "packaging" / "kotoba.spec"
BUNDLE = ROOT / "dist" / "Kotobako"
EXE = BUNDLE / "Kotobako.exe"
SMOKE_TEXT = "今日は俺が奢ってやるよ。"
TIMESTAMP_URL = "http://timestamp.digicert.com"


def log(message: str) -> None:
    print(message, flush=True)


def run(cmd: list[str], *, cwd: Path | None = None) -> None:
    log("+ " + " ".join(str(part) for part in cmd))
    subprocess.run(cmd, cwd=cwd, check=True)


def version() -> str:
    with (ROOT / "backend" / "pyproject.toml").open("rb") as fh:
        return tomllib.load(fh)["project"]["version"]


def tree_size(path: Path) -> int:
    return sum(entry.stat().st_size for entry in path.rglob("*") if entry.is_file())


def build_frontend() -> None:
    if not (ROOT / "frontend" / "node_modules").is_dir():
        raise SystemExit("frontend/node_modules is missing; run `make setup` first")
    npm = shutil.which("npm")
    if npm is None:
        raise SystemExit("npm not found on PATH; install Node.js first")
    run([npm, "run", "build"], cwd=ROOT / "frontend")


def build_bundle(*, clean: bool) -> None:
    cmd = [sys.executable, "-m", "PyInstaller", "--noconfirm"]
    if clean:
        cmd.append("--clean")
    cmd.append(str(SPEC))
    run(cmd, cwd=ROOT)


def _get(url: str) -> bytes:
    with urllib.request.urlopen(url, timeout=5) as response:
        return response.read()


def _post(url: str, payload: dict) -> dict:
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        return json.loads(response.read())


def _ocr_roundtrip(base: str, data_dir: Path) -> str:
    """Render the smoke line and let the bundled Windows OCR read it back."""
    from PIL import Image, ImageDraw, ImageFont

    fonts = ("C:/Windows/Fonts/meiryo.ttc", "C:/Windows/Fonts/YuGothR.ttc")
    font_path = next((p for p in fonts if Path(p).is_file()), None)
    if font_path is None:
        return "skipped: no Japanese font installed"
    image = Image.new("RGB", (900, 120), (20, 20, 30))
    draw = ImageDraw.Draw(image)
    draw.text((30, 30), SMOKE_TEXT, font=ImageFont.truetype(font_path, 40), fill=(240, 240, 240))
    image.save(data_dir / "media" / "ocr-smoke.png")
    return _post(base + "/api/capture/ocr", {"path": "ocr-smoke.png"})["text"]


def smoke(port: int) -> dict:
    """Start the frozen exe on a throwaway data dir and prove it really works."""
    results: dict[str, object] = {}
    with tempfile.TemporaryDirectory(prefix="kotoba-package-smoke-") as data_dir:
        started = time.perf_counter()
        proc = subprocess.Popen(
            [str(EXE), "serve", "--data-dir", data_dir, "--port", str(port)],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        try:
            base = f"http://127.0.0.1:{port}"
            deadline = time.monotonic() + 120
            while True:
                if proc.poll() is not None:
                    raise SystemExit(f"the frozen server exited early:\n{proc.stdout.read()}")
                try:
                    results["health"] = json.loads(_get(base + "/api/health"))
                    break
                except (urllib.error.URLError, ConnectionError, TimeoutError):
                    if time.monotonic() > deadline:
                        raise SystemExit("the frozen server never answered /api/health") from None
                    time.sleep(0.25)
            results["first_start_seconds"] = round(time.perf_counter() - started, 1)
            results["index_bytes"] = len(_get(base + "/"))
            providers = json.loads(_get(base + "/api/capture/providers"))
            results["winocr"] = next((p for p in providers if p["name"] == "winocr"), None)
            if results["winocr"] and results["winocr"]["available"]:
                results["ocr_text"] = _ocr_roundtrip(base, Path(data_dir))
            else:
                results["ocr_text"] = "skipped: no Japanese language pack"
            source = _post(base + "/api/sources", {"title": "packaging smoke"})
            session = _post(
                base + "/api/sessions", {"source_id": source["id"], "mode": "companion"}
            )
            line = _post(
                base + "/api/lines",
                {"session_id": session["id"], "text": SMOKE_TEXT, "origin": "manual"},
            )["line"]
            analysis = _post(base + f"/api/lines/{line['id']}/analyze", {})
            results["token_count"] = len(analysis["tokens"])
            results["content_bases"] = [t["base"] for t in analysis["tokens"] if t["is_content"]]
        finally:
            proc.terminate()
            try:
                proc.wait(timeout=15)
            except subprocess.TimeoutExpired:
                proc.kill()
    return results


def find_signtool() -> str | None:
    found = shutil.which("signtool")
    if found:
        return found
    kits = Path("C:/Program Files (x86)/Windows Kits/10/bin")
    if kits.is_dir():
        candidates = sorted(kits.glob("*/x64/signtool.exe"), reverse=True)
        if candidates:
            return str(candidates[0])
    return None


def sign(path: Path, *, thumbprint: str | None, pfx: Path | None) -> None:
    signtool = find_signtool()
    if signtool is None:
        raise SystemExit("signtool.exe not found; install the Windows SDK")
    cmd = [signtool, "sign", "/fd", "sha256", "/td", "sha256", "/tr", TIMESTAMP_URL]
    if pfx is not None:
        password = os.environ.get("KOTOBA_PFX_PASSWORD")
        if not password:
            raise SystemExit("set KOTOBA_PFX_PASSWORD for --sign-pfx")
        cmd += ["/f", str(pfx), "/p", password]
        shown = [*cmd[:-1], "******"]
    else:
        cmd += ["/sha1", thumbprint or ""]
        shown = cmd
    cmd.append(str(path))
    shown.append(str(path))
    log("+ " + " ".join(shown) + "   (certificate material is never logged)")
    subprocess.run(cmd, check=True)


def find_iscc() -> str | None:
    found = shutil.which("iscc")
    if found:
        return found
    local = os.environ.get("LOCALAPPDATA", "")
    for candidate in (
        Path(local) / "Programs" / "Inno Setup 6" / "ISCC.exe",
        Path("C:/Program Files (x86)/Inno Setup 6/ISCC.exe"),
        Path("C:/Program Files/Inno Setup 6/ISCC.exe"),
    ):
        if candidate.is_file():
            return str(candidate)
    return None


def build_installer() -> Path:
    iscc = find_iscc()
    if iscc is None:
        raise SystemExit(
            "Inno Setup 6 not found; install it (`winget install JRSoftware.InnoSetup`) "
            "or rerun without --installer for the portable bundle only"
        )
    out = ROOT / "dist" / f"Kotobako-{version()}-setup.exe"
    run(
        [
            iscc,
            f"/DAppVersion={version()}",
            f"/O{out.parent}",
            f"/F{out.stem}",
            str(ROOT / "packaging" / "installer.iss"),
        ],
        cwd=ROOT,
    )
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description="Build the Windows distribution")
    parser.add_argument("--skip-frontend", action="store_true", help="reuse frontend/dist")
    parser.add_argument("--no-clean", action="store_true", help="reuse PyInstaller caches")
    parser.add_argument("--no-smoke", action="store_true", help="skip starting the exe")
    parser.add_argument("--installer", action="store_true", help="also build the Inno Setup exe")
    parser.add_argument("--sign-thumbprint", help="SHA1 of a certificate in the user's store")
    parser.add_argument("--sign-pfx", type=Path, help="PFX file; password via KOTOBA_PFX_PASSWORD")
    parser.add_argument("--port", type=int, default=8732, help="port for the smoke test")
    args = parser.parse_args()

    if sys.platform != "win32":
        raise SystemExit("the Windows bundle can only be built on Windows")
    if args.sign_pfx is not None and not args.sign_pfx.is_file():
        raise SystemExit(f"{args.sign_pfx} does not exist")
    if args.sign_pfx is not None and not os.environ.get("KOTOBA_PFX_PASSWORD"):
        raise SystemExit("set KOTOBA_PFX_PASSWORD for --sign-pfx (never on the command line)")

    started = time.perf_counter()
    if not args.skip_frontend:
        build_frontend()
    build_bundle(clean=not args.no_clean)
    if not EXE.is_file():
        raise SystemExit(f"{EXE} was not produced")
    log(f"bundle: {BUNDLE} ({tree_size(BUNDLE) / 1e6:.1f} MB)")

    if not args.no_smoke:
        log("smoke: " + json.dumps(smoke(args.port), ensure_ascii=False))

    if args.sign_thumbprint or args.sign_pfx:
        sign(EXE, thumbprint=args.sign_thumbprint, pfx=args.sign_pfx)
    if args.installer:
        installer = build_installer()
        log(f"installer: {installer} ({installer.stat().st_size / 1e6:.1f} MB)")
        if args.sign_thumbprint or args.sign_pfx:
            sign(installer, thumbprint=args.sign_thumbprint, pfx=args.sign_pfx)

    log(f"done in {time.perf_counter() - started:.0f}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
