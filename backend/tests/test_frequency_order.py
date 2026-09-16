import io
import json
import zipfile


def frequency_zip() -> bytes:
    entries = [["水", "freq", 5000], ["犬", "freq", 10]]
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("index.json", json.dumps({"title": "频率表", "format": 3}))
        zf.writestr("term_meta_bank_1.json", json.dumps(entries))
    return buf.getvalue()


def upload_frequencies(client):
    return client.post(
        "/api/dict/yomitan/import",
        files={"file": ("freq.zip", frequency_zip(), "application/zip")},
    )


def seed_line(client, text: str = "水と犬と鳥") -> dict:
    src = client.post("/api/sources", json={"title": "作品"}).json()
    ses = client.post("/api/sessions", json={"source_id": src["id"]}).json()
    line = client.post("/api/lines", json={"session_id": ses["id"], "text": text}).json()["line"]
    return client.post(f"/api/lines/{line['id']}/analyze").json()


def ensure_terms(client) -> None:
    """水, 犬 and 鳥 as library terms, in that creation order."""
    src = client.post("/api/sources", json={"title": "作品二"}).json()
    ses = client.post("/api/sessions", json={"source_id": src["id"]}).json()
    line = client.post("/api/lines", json={"session_id": ses["id"], "text": "水と犬と鳥"}).json()[
        "line"
    ]
    for headword, reading in (("水", "みず"), ("犬", "いぬ"), ("鳥", "とり")):
        client.post(
            "/api/encounters",
            json={
                "line_id": line["id"],
                "headword": headword,
                "reading": reading,
                "surface": headword,
            },
        )


def test_dict_status_reports_whether_frequencies_exist(client):
    assert client.get("/api/dict/status").json()["has_frequencies"] is False
    upload_frequencies(client)
    assert client.get("/api/dict/status").json()["has_frequencies"] is True


def test_terms_carry_the_rank_and_sort_by_it_with_unranked_last(client):
    upload_frequencies(client)
    ensure_terms(client)

    recent = client.get("/api/terms").json()
    assert [t["headword"] for t in recent] == ["鳥", "犬", "水"]  # created order

    ranked = client.get("/api/terms", params={"sort": "frequency"}).json()
    assert [t["headword"] for t in ranked] == ["犬", "水", "鳥"]
    assert [t["frequency_rank"] for t in ranked] == [10, 5000, None]


def test_analysis_tokens_carry_the_rank(client):
    upload_frequencies(client)
    analysis = seed_line(client)
    ranks = {t["base"]: t["frequency_rank"] for t in analysis["tokens"] if t["is_content"]}
    assert ranks["水"] == 5000
    assert ranks["犬"] == 10
    assert ranks["鳥"] is None
    assert all("frequency_rank" in t for t in analysis["tokens"])
