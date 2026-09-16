import json

from kotoba.services.text import mokuro

BOX = [10, 20, 110, 220]


def block(lines, coords, vertical=False, box=None):
    return {
        "box": box or BOX,
        "vertical": vertical,
        "font_size": 26,
        "lines_coords": coords,
        "lines": lines,
    }


def quad(x, y=0.0, w=20.0, h=100.0):
    return [[x, y], [x + w, y], [x + w, y + h], [x, y + h]]


def mokuro_json(pages, title="漫画", volume="vol1") -> bytes:
    return json.dumps(
        {
            "version": "0.2.0-beta.6",
            "title": title,
            "volume": volume,
            "pages": pages,
        }
    ).encode()


def page(blocks, width=827, height=1170) -> dict:
    return {
        "version": "0.2.0-beta.6",
        "img_width": width,
        "img_height": height,
        "blocks": blocks,
    }


def upload(client, source_id: int, data: bytes):
    return client.post(
        f"/api/sources/{source_id}/mokuro",
        files={"file": ("vol1.mokuro", data, "application/json")},
    )


def make_source(client) -> int:
    return client.post("/api/sources", json={"title": "漫画作品"}).json()["id"]


def test_parse_keeps_vertical_columns_in_mokuro_order():
    # Coordinates from mokuro's own fixture (test0 vol1 page 2): the block lists
    # its columns right to left and split the leftmost column into two stacked
    # lines. Re-deriving the order from box centres would jump "．．．" ahead of
    # the "なのかしら！？" it belongs to.
    payload = json.loads(
        mokuro_json(
            [
                page(
                    [
                        block(
                            lines=["ご主人さま", "トカゲはおキライ", "なのかしら！？", "．．．"],
                            coords=[
                                quad(751, y=868, w=24, h=116),
                                quad(724, y=868, w=23, h=186),
                                quad(693, y=868, w=25, h=140),
                                quad(700, y=1004, w=13, h=27),
                            ],
                            vertical=True,
                            box=[693, 868, 777, 1058],
                        )
                    ]
                )
            ]
        )
    )
    blocks = mokuro.parse_mokuro(payload).blocks
    assert [b.text for b in blocks] == ["ご主人さまトカゲはおキライなのかしら！？．．．"]


def test_parse_keeps_horizontal_lines_in_mokuro_order():
    payload = json.loads(
        mokuro_json(
            [
                page(
                    [
                        block(
                            lines=["うえ", "した"],
                            coords=[quad(0, y=10), quad(0, y=80)],
                            vertical=False,
                        )
                    ]
                )
            ]
        )
    )
    blocks = mokuro.parse_mokuro(payload).blocks
    assert [b.text for b in blocks] == ["うえした"]


def test_parse_keeps_page_and_block_order():
    payload = json.loads(
        mokuro_json(
            [
                page([block(["いち"], [quad(0)]), block(["に"], [quad(0)])]),
                page([block(["さん"], [quad(0)])]),
            ]
        )
    )
    blocks = mokuro.parse_mokuro(payload).blocks
    assert [b.text for b in blocks] == ["いち", "に", "さん"]
    assert [b.page for b in blocks] == [1, 1, 2]


def test_parse_rejects_broken_fields():
    cases = [
        {"version": "0.2.0", "title": "x"},  # no pages
        {"version": "0.2.0", "pages": "nope"},
        {"version": "0.2.0", "pages": [{"blocks": []}]},  # page without size
        {"version": "0.2.0", "pages": [{"img_width": 100, "img_height": 100}]},  # no blocks
        {"version": "0.2.0", "pages": [page([{"box": [1, 2, 3]}])]},  # block without lines
        {"version": "0.2.0", "pages": [page([block(["a", "b"], [quad(0)])])]},  # coords mismatch
    ]
    for data in cases:
        try:
            mokuro.parse_mokuro(data)
        except Exception as exc:  # noqa: BLE001
            assert getattr(exc, "code", None) == "bad_mokuro", data
        else:
            raise AssertionError(f"expected bad_mokuro for {data}")


def test_import_creates_a_session_with_page_locators(client):
    source_id = make_source(client)
    data = mokuro_json(
        [
            page([block(["いち"], [quad(0)]), block(["に"], [quad(0)])]),
            page([block(["さん"], [quad(0)])]),
        ]
    )
    r = upload(client, source_id, data)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["pages"] == 2 and body["created"] == 3 and body["skipped"] == 0

    session = client.get(f"/api/sessions/{body['session_id']}").json()
    assert session["mode"] == "import" and session["text_source"] == "ocr"

    lines = client.get("/api/lines", params={"session_id": body["session_id"]}).json()
    assert [line["text"] for line in lines] == ["いち", "に", "さん"]
    assert [line["ord"] for line in lines] == [1, 2, 3]
    assert all(line["origin"] == "ocr" for line in lines)
    assert lines[0]["locator"] == {"kind": "page", "page": 1, "box": BOX}
    assert lines[2]["locator"] == {"kind": "page", "page": 2, "box": BOX}


def test_import_dedupes_repeated_text(client):
    source_id = make_source(client)
    data = mokuro_json([page([block(["おなじ"], [quad(0)]), block(["おなじ"], [quad(0)])])])
    body = upload(client, source_id, data).json()
    assert body["created"] == 1 and body["skipped"] == 1


def test_import_rejects_an_empty_page_list(client):
    source_id = make_source(client)
    r = upload(client, source_id, mokuro_json([]))
    assert r.status_code == 400
    assert r.json()["error"]["code"] == "bad_mokuro"


def test_import_unknown_source(client):
    r = upload(client, 999, mokuro_json([page([block(["x"], [quad(0)])])]))
    assert r.status_code == 404
    assert r.json()["error"]["code"] == "not_found"
