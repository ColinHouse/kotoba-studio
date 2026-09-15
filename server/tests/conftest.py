from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def data_dir(tmp_path, monkeypatch):
    d = tmp_path / "data"
    monkeypatch.setenv("KOTOBA_DATA_DIR", str(d))
    from kotoba.config import get_settings

    get_settings.cache_clear()
    yield d
    get_settings.cache_clear()


@pytest.fixture()
def app(data_dir):
    from kotoba.main import create_app

    return create_app()


@pytest.fixture()
def client(app):
    with TestClient(app) as c:
        yield c


@pytest.fixture()
def db(client):
    """A SQLAlchemy session bound to the running test app's database."""
    session = client.app.state.db.session()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def jmdict_fixture(db):
    """Import the small bundled JMdict fixture into the test database."""
    from pathlib import Path

    from kotoba.services.dictionary import jmdict
    from kotoba.services.jp import expressions

    path = Path(jmdict.__file__).resolve().parents[2] / "data" / "jmdict_fixture.json"
    count = jmdict.import_json(db, path)
    expressions.reset_cache()
    return count
