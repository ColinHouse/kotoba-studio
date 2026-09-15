import pytest
from fastapi.testclient import TestClient


def test_connect_info(client):
    body = client.get("/api/connect-info").json()
    assert body["qr_svg"].startswith("<svg") and body["port"] == 8720
    assert body["primary_url"].startswith("http://")
    assert body["lan_enabled"] is False and body["hint"]


@pytest.fixture()
def spa_client(tmp_path, monkeypatch):
    dist = tmp_path / "dist"
    (dist / "assets").mkdir(parents=True)
    (dist / "index.html").write_text("<html><body>kotoba</body></html>", encoding="utf-8")
    (dist / "assets" / "app.js").write_text("console.log(1)", encoding="utf-8")
    (dist / "manifest.webmanifest").write_text("{}", encoding="utf-8")
    monkeypatch.setenv("KOTOBA_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("KOTOBA_WEB_DIST", str(dist))
    from kotoba.config import get_settings

    get_settings.cache_clear()
    from kotoba.main import create_app

    with TestClient(create_app()) as c:
        yield c
    get_settings.cache_clear()


def test_spa_fallback_and_api_404(spa_client):
    assert "kotoba" in spa_client.get("/").text
    assert "kotoba" in spa_client.get("/library").text
    assert "kotoba" in spa_client.get("/terms/12").text
    assert spa_client.get("/assets/app.js").text == "console.log(1)"
    assert spa_client.get("/manifest.webmanifest").text == "{}"
    assert spa_client.get("/api/nope").json()["error"]["code"] == "not_found"
    assert spa_client.get("/media/nope.png").status_code == 404
    assert spa_client.get("/api/health").json()["status"] == "ok"
