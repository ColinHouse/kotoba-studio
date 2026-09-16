from sqlalchemy import select

from kotoba.models import Line
from kotoba.services.learning import ranking
from kotoba.services.text import analysis as analysis_service


def make_source_session(client) -> int:
    src = client.post("/api/sources", json={"title": "作品"}).json()
    return client.post("/api/sessions", json={"source_id": src["id"]}).json()["id"]


def add_line(client, session_id: int, text: str) -> dict:
    return client.post("/api/lines", json={"session_id": session_id, "text": text}).json()["line"]


def learn(client, line_id: int, headword: str) -> None:
    client.post(
        "/api/encounters",
        json={"line_id": line_id, "headword": headword, "reading": "", "surface": headword},
    )
    terms = client.get("/api/terms", params={"q": headword}).json()
    client.patch(f"/api/terms/{terms[0]['id']}", json={"known_status": "known"})


def count_for(client, db, session_id: int, text: str, known: tuple[str, ...] = ()) -> int:
    line = add_line(client, session_id, text)
    for headword in known:
        learn(client, line["id"], headword)
    count = ranking.enrich(db, db.get(Line, line["id"]))
    db.commit()  # release the write lock so the next HTTP call can insert
    return count


def test_unknown_count_counts_content_words_once(client, db):
    session_id = make_source_session(client)
    assert count_for(client, db, session_id, "猫と犬と猫と鳥") == 3  # と is a particle
    assert count_for(client, db, session_id, "海と山と川", known=("山",)) == 2
    assert count_for(client, db, session_id, "花と空", known=("花",)) == 1
    assert count_for(client, db, session_id, "星", known=("星",)) == 0
    assert count_for(client, db, session_id, "１２３と４５６") == 0  # numbers are not words


def test_inbox_sorts_by_i_plus_one(client):
    session_id = make_source_session(client)
    three = add_line(client, session_id, "猫と犬と鳥")
    zero = add_line(client, session_id, "花")
    one = add_line(client, session_id, "空")
    two = add_line(client, session_id, "海と山")
    learn(client, zero["id"], "花")

    rows = client.get("/api/lines", params={"session_id": session_id, "sort": "iplus1"}).json()
    assert [row["id"] for row in rows] == [one["id"], zero["id"], two["id"], three["id"]]
    assert [row["unknown_count"] for row in rows] == [1, 0, 2, 3]

    # The default order stays recency; only sort=iplus1 reorders.
    recent = client.get("/api/lines", params={"session_id": session_id}).json()
    assert [row["id"] for row in recent] == [two["id"], one["id"], zero["id"], three["id"]]


def test_enrichment_is_cached_until_the_line_changes(client, db, monkeypatch):
    session_id = make_source_session(client)
    add_line(client, session_id, "猫と犬")
    calls: list[int] = []
    real = analysis_service.analyze_line

    def counting(db_session, line, force=False):  # noqa: ANN001
        calls.append(line.id)
        return real(db_session, line, force=force)

    monkeypatch.setattr(analysis_service, "analyze_line", counting)
    client.get("/api/lines", params={"session_id": session_id, "sort": "iplus1"})
    first = len(calls)
    assert first == 1  # one uncached line

    client.get("/api/lines", params={"session_id": session_id, "sort": "iplus1"})
    assert len(calls) == first  # cache hit, no recomputation

    line = db.scalar(select(Line).where(Line.session_id == session_id))
    client.patch(f"/api/lines/{line.id}", json={"text": "猫と犬と鳥"})
    client.get("/api/lines", params={"session_id": session_id, "sort": "iplus1"})
    assert len(calls) == first + 1  # edited text invalidates the cache
