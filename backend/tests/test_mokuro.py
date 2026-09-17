import io
import json
import zipfile

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


def volume_zip(files: dict[str, bytes]) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as archive:
        for name, data in files.items():
            archive.writestr(name, data)
    return buf.getvalue()


def upload_zip(client, source_id: int, data: bytes):
    return client.post(
        f"/api/sources/{source_id}/mokuro",
        files={"file": ("vol1.zip", data, "application/zip")},
    )


def two_page_mokuro() -> bytes:
    return mokuro_json(
        [
            page([block(["いち"], [quad(0)]), block(["に"], [quad(0)])]),
            page([block(["さん"], [quad(0)])]),
        ]
    )


def stored(client, line) -> bytes:
    return (client.app.state.paths.media_dir / line["screenshot_path"]).read_bytes()


def test_import_zip_stores_page_images(client):
    source_id = make_source(client)
    data = volume_zip(
        {
            "vol1/vol1.mokuro": two_page_mokuro(),
            "vol1/0001.jpg": b"page-one",
            "vol1/0002.png": b"page-two",
        }
    )
    r = upload_zip(client, source_id, data)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["images"] == 2 and body["pages"] == 2 and body["created"] == 3

    lines = client.get("/api/lines", params={"session_id": body["session_id"]}).json()
    assert lines[0]["screenshot_path"] == lines[1]["screenshot_path"]
    assert lines[0]["screenshot_path"].startswith("manga/")
    assert lines[0]["screenshot_path"].endswith("0001.jpg")
    assert lines[2]["screenshot_path"].endswith("0002.png")
    assert stored(client, lines[0]) == b"page-one"
    assert stored(client, lines[2]) == b"page-two"

    media = client.get(f"/media/{lines[0]['screenshot_path']}")
    assert media.status_code == 200 and media.content == b"page-one"


def test_import_zip_orders_pages_naturally(client):
    # Lexicographic order would put 10.jpg before 2.jpg and misalign every page.
    source_id = make_source(client)
    data = volume_zip(
        {
            "vol1.mokuro": mokuro_json(
                [
                    page([block(["いち"], [quad(0)])]),
                    page([block(["に"], [quad(0)])]),
                    page([block(["さん"], [quad(0)])]),
                ]
            ),
            "1.jpg": b"one",
            "2.jpg": b"two",
            "10.jpg": b"ten",
        }
    )
    body = upload_zip(client, source_id, data).json()
    lines = client.get("/api/lines", params={"session_id": body["session_id"]}).json()
    assert [stored(client, line) for line in lines] == [b"one", b"two", b"ten"]


def test_import_zip_rejects_a_page_count_mismatch(client):
    source_id = make_source(client)
    r = upload_zip(client, source_id, volume_zip({"vol1.mokuro": two_page_mokuro(), "1.jpg": b"x"}))
    assert r.status_code == 400
    assert r.json()["error"]["code"] == "bad_mokuro"


def test_import_zip_requires_a_mokuro_file(client):
    source_id = make_source(client)
    r = upload_zip(client, source_id, volume_zip({"1.jpg": b"x"}))
    assert r.status_code == 400
    assert r.json()["error"]["code"] == "bad_mokuro"


def test_import_zip_rejects_two_mokuro_files(client):
    source_id = make_source(client)
    data = volume_zip({"a.mokuro": two_page_mokuro(), "b.mokuro": two_page_mokuro()})
    r = upload_zip(client, source_id, data)
    assert r.status_code == 400
    assert r.json()["error"]["code"] == "bad_mokuro"


def test_import_rejects_a_broken_zip(client):
    source_id = make_source(client)
    r = upload_zip(client, source_id, b"PK\x03\x04 broken")
    assert r.status_code == 400
    assert r.json()["error"]["code"] == "bad_mokuro"


def test_import_zip_without_images_is_text_only(client):
    source_id = make_source(client)
    body = upload_zip(client, source_id, volume_zip({"vol1.mokuro": two_page_mokuro()})).json()
    assert body["images"] == 0
    lines = client.get("/api/lines", params={"session_id": body["session_id"]}).json()
    assert all(line["screenshot_path"] is None for line in lines)


def test_import_zip_ignores_macos_resource_forks(client):
    # A Finder-made zip stores every image twice; counting the ._ copies would
    # fail the page-count check and make the volume unimportable.
    source_id = make_source(client)
    data = volume_zip(
        {
            "vol1.mokuro": two_page_mokuro(),
            "0001.jpg": b"one",
            "0002.jpg": b"two",
            "__MACOSX/._0001.jpg": b"junk",
            "__MACOSX/._0002.jpg": b"junk",
        }
    )
    body = upload_zip(client, source_id, data).json()
    assert body["images"] == 2


def test_import_zip_never_writes_by_member_name(client):
    source_id = make_source(client)
    data = volume_zip(
        {
            "vol1.mokuro": mokuro_json([page([block(["いち"], [quad(0)])])]),
            "../../evil.jpg": b"x",
        }
    )
    body = upload_zip(client, source_id, data).json()
    lines = client.get("/api/lines", params={"session_id": body["session_id"]}).json()
    assert lines[0]["screenshot_path"].startswith("manga/")
    assert not (client.app.state.paths.data_dir / "evil.jpg").exists()
