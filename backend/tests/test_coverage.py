import io
import json
import zipfile


def frequency_zip(entries: list) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("index.json", json.dumps({"title": "频率表", "format": 3}))
        zf.writestr("term_meta_bank_1.json", json.dumps(entries))
    return buf.getvalue()


def upload_frequencies(client, entries: list):
    return client.post(
        "/api/dict/yomitan/import",
        files={"file": ("freq.zip", frequency_zip(entries), "application/zip")},
    )


def seed_work(client) -> tuple[int, dict[str, int]]:
    """One source with 猫×3, 犬×1, 鳥×5 encounters on separate lines."""
    src = client.post("/api/sources", json={"title": "作品"}).json()
    ses = client.post("/api/sessions", json={"source_id": src["id"]}).json()
    line = client.post("/api/lines", json={"session_id": ses["id"], "text": "猫と犬と鳥"}).json()[
        "line"
    ]
    terms: dict[str, int] = {}
    for headword, count in (("猫", 3), ("犬", 1), ("鳥", 5)):
        enc = client.post(
            "/api/encounters",
            json={
                "line_id": line["id"],
                "headword": headword,
                "reading": "",
                "surface": headword,
            },
        )
        terms[headword] = enc.json()["term"]["id"]
        # Extra encounters on their own lines so the token count differs from the term count.
        for _ in range(count - 1):
            extra = client.post(
                "/api/lines", json={"session_id": ses["id"], "text": headword}
            ).json()["line"]
            client.post(
                "/api/encounters",
                json={
                    "line_id": extra["id"],
                    "headword": headword,
                    "reading": "",
                    "surface": headword,
                },
            )
    return src["id"], terms


def set_status(client, term_id: int, status: str) -> None:
    client.patch(f"/api/terms/{term_id}", json={"known_status": status})


def test_coverage_counts_tokens_and_terms_separately(client):
    source_id, terms = seed_work(client)
    set_status(client, terms["犬"], "known")

    body = client.get(f"/api/sources/{source_id}/coverage").json()
    assert body["total_tokens"] == 9
    assert body["distinct_terms"] == 3
    assert body["known_tokens"] == 1
    assert body["known_terms"] == 1
    assert body["coverage"] == 1 / 9  # by occurrences
    assert body["distinct_coverage"] == 1 / 3  # by distinct words
    assert body["has_frequency"] is False

    unknown_ids = [u["term_id"] for u in body["unknown_top"]]
    assert set(unknown_ids) == {terms["猫"], terms["鳥"]}
    assert unknown_ids[0] == terms["鳥"]  # no frequency data: by count desc
    assert body["unknown_top"][0]["count"] == 5


def test_unknown_top_uses_frequency_before_count(client):
    source_id, terms = seed_work(client)
    upload_frequencies(
        client,
        [["猫", "freq", 100], ["犬", "freq", 50]],  # 鳥 has no rank
    )

    body = client.get(f"/api/sources/{source_id}/coverage").json()
    assert body["has_frequency"] is True
    order = [u["headword"] for u in body["unknown_top"]]
    assert order == ["犬", "猫", "鳥"]  # rank first, unranked last (count ignored until then)
    assert body["unknown_top"][0]["rank"] == 50
    assert body["unknown_top"][-1]["rank"] is None


def test_unknown_top_honours_the_limit(client):
    source_id, _ = seed_work(client)
    body = client.get(f"/api/sources/{source_id}/coverage", params={"limit": 1}).json()
    assert len(body["unknown_top"]) == 1
    assert body["unknown_top"][0]["headword"] == "鳥"


def test_coverage_unknown_source(client):
    r = client.get("/api/sources/999/coverage")
    assert r.status_code == 404
    assert r.json()["error"]["code"] == "not_found"
