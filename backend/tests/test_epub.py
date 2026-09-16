import posixpath
from io import BytesIO
from zipfile import ZIP_DEFLATED, ZipFile

from kotoba.services.text.epub import iter_chapters

CONTAINER = """<?xml version="1.0" encoding="utf-8"?>
<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
  <rootfiles>
    <rootfile full-path="{opf}" media-type="application/oebps-package+xml"/>
  </rootfiles>
</container>
"""


def xhtml(body: str) -> str:
    return (
        '<?xml version="1.0" encoding="utf-8"?>'
        '<html xmlns="http://www.w3.org/1999/xhtml">'
        f"<head><title>章节</title></head><body>{body}</body></html>"
    )


def build_epub(
    documents: list[tuple[str, str]],
    spine: list[str] | None = None,
    linear_no: set[str] | None = None,
    opf_path: str = "OEBPS/content.opf",
) -> bytes:
    spine = spine if spine is not None else [href for href, _ in documents]
    linear_no = linear_no or set()
    ids = {href: f"item{index}" for index, (href, _) in enumerate(documents, start=1)}
    manifest = "".join(
        f'<item id="{ids[href]}" href="{href}" media-type="application/xhtml+xml"/>'
        for href, _ in documents
    )

    def ref(href: str) -> str:
        linear = ' linear="no"' if href in linear_no else ""
        return f'<itemref idref="{ids[href]}"{linear}/>'

    opf = (
        '<?xml version="1.0" encoding="utf-8"?>'
        '<package xmlns="http://www.idpf.org/2007/opf" version="3.0" unique-identifier="id">'
        '<metadata xmlns:dc="http://purl.org/dc/elements/1.1/"><dc:title>测试</dc:title></metadata>'
        f"<manifest>{manifest}</manifest><spine>{''.join(ref(h) for h in spine)}</spine></package>"
    )
    archive = BytesIO()
    with ZipFile(archive, "w", ZIP_DEFLATED) as zf:
        zf.writestr("mimetype", "application/epub+zip")
        zf.writestr("META-INF/container.xml", CONTAINER.format(opf=opf_path))
        zf.writestr(opf_path, opf)
        directory = posixpath.dirname(opf_path)
        for href, body in documents:
            name = f"{directory}/{href}" if directory else href
            zf.writestr(name, xhtml(body))
    return archive.getvalue()


def paragraphs_epub(*paragraphs: str) -> bytes:
    return build_epub([("ch1.xhtml", "".join(f"<p>{text}</p>" for text in paragraphs))])


def upload(client, source_id: int, data: bytes):
    return client.post(
        f"/api/sources/{source_id}/epub",
        files={"file": ("book.epub", data, "application/epub+zip")},
    )


def make_source(client) -> int:
    return client.post("/api/sources", json={"title": "轻小说"}).json()["id"]


def lines_of(client, session_id: int) -> list[dict]:
    return client.get("/api/lines", params={"session_id": session_id}).json()


def test_import_follows_spine_order_not_file_names(client):
    data = build_epub(
        [("a.xhtml", "<p>あとの章。</p>"), ("b.xhtml", "<p>さきの章。</p>")],
        spine=["b.xhtml", "a.xhtml"],
    )
    body = upload(client, make_source(client), data).json()
    assert body["chapters"] == 2 and body["created"] == 2 and body["skipped"] == 0

    lines = lines_of(client, body["session_id"])
    assert [line["text"] for line in lines] == ["さきの章。", "あとの章。"]
    assert [line["locator"]["chapter"] for line in lines] == [1, 2]
    assert [line["ord"] for line in lines] == [1, 2]
    assert all(line["origin"] == "subtitle" for line in lines)


def test_import_skips_non_linear_documents(client):
    data = build_epub(
        [("main.xhtml", "<p>本編。</p>"), ("extra.xhtml", "<p>補遺。</p>")],
        spine=["extra.xhtml", "main.xhtml"],
        linear_no={"extra.xhtml"},
    )
    body = upload(client, make_source(client), data).json()
    assert body["chapters"] == 1
    assert [line["text"] for line in lines_of(client, body["session_id"])] == ["本編。"]


def test_import_keeps_ruby_reading_out_of_the_text(client):
    data = build_epub([("ch1.xhtml", "<p><ruby>食べ物<rt>たべもの</rt></ruby>を買った。</p>")])
    body = upload(client, make_source(client), data).json()
    line = lines_of(client, body["session_id"])[0]
    assert line["text"] == "食べ物を買った。"
    assert line["raw_text"] == "食べ物（たべもの）を買った。"


def test_parse_records_ruby_readings_separately():
    data = build_epub(
        [
            (
                "ch1.xhtml",
                "<p><ruby>食<rt>た</rt>べ<rt>べ</rt>物<rt>もの</rt></ruby>は美味しい。</p>",
            )
        ]
    )
    chapters = list(iter_chapters(BytesIO(data)))
    assert [chapter.text for chapter in chapters] == ["食べ物は美味しい。"]
    assert [(ruby.base, ruby.reading) for ruby in chapters[0].ruby] == [("食べ物", "たべもの")]


def test_sentence_split_rules():
    data = paragraphs_epub("彼は言った。「そうか。すぐ行く」と。次へ。えっ！？……まだ。")
    chapters = list(iter_chapters(BytesIO(data)))
    assert [sentence.text for sentence in chapters[0].sentences] == [
        "彼は言った。",
        "「そうか。すぐ行く」と。",
        "次へ。",
        "えっ！？",
        "……まだ。",
    ]


def test_closing_quote_stays_with_its_sentence():
    data = paragraphs_epub("「そうか。」次へ。")
    chapters = list(iter_chapters(BytesIO(data)))
    assert [sentence.text for sentence in chapters[0].sentences] == ["「そうか。」", "次へ。"]


def test_locator_offsets_point_into_the_chapter_text(client):
    data = paragraphs_epub("これは最初の文です。", "次は二つ目の文。最後。")
    chapters = list(iter_chapters(BytesIO(data)))
    chapter = chapters[0]
    assert chapter.text == "これは最初の文です。\n次は二つ目の文。最後。"
    for sentence in chapter.sentences:
        assert chapter.text[sentence.start : sentence.end] == sentence.text

    body = upload(client, make_source(client), data).json()
    lines = lines_of(client, body["session_id"])
    assert [line["locator"]["start"] for line in lines] == [0, 11, 19]
    assert [line["locator"]["end"] for line in lines] == [10, 19, 22]


def test_import_skips_an_identical_sentence(client):
    data = paragraphs_epub("同じ文です。", "同じ文です。")
    body = upload(client, make_source(client), data).json()
    assert body["created"] == 1 and body["skipped"] == 1


def test_import_keeps_near_identical_sentences(client):
    data = paragraphs_epub(
        "今日はとても気持ちのいい天気でした。",
        "今日はとても気持ちのいい天気でした！",
    )
    body = upload(client, make_source(client), data).json()
    assert body["created"] == 2 and body["skipped"] == 0


def test_import_rejects_a_non_zip(client):
    r = upload(client, make_source(client), b"not a zip at all")
    assert r.status_code == 400
    assert r.json()["error"]["code"] == "bad_epub"


def test_import_rejects_an_epub_without_text(client):
    r = upload(client, make_source(client), build_epub([("ch1.xhtml", "<p></p>")]))
    assert r.status_code == 400
    assert r.json()["error"]["code"] == "bad_epub"
    assert client.get("/api/sessions").json() == []


def test_a_broken_chapter_imports_nothing(client):
    data = build_epub([("good.xhtml", "<p>大丈夫。</p>"), ("bad.xhtml", "<p>壊れた")])
    r = upload(client, make_source(client), data)
    assert r.status_code == 400
    assert r.json()["error"]["code"] == "bad_epub"
    assert client.get("/api/sessions").json() == []


def test_import_batches_a_long_book(client):
    body_xml = "".join(f"<p>第{index}文です。</p>" for index in range(600))
    data = build_epub([("ch1.xhtml", body_xml)])
    body = upload(client, make_source(client), data).json()
    assert body["chapters"] == 1 and body["created"] == 600 and body["skipped"] == 0

    session = client.get(f"/api/sessions/{body['session_id']}").json()
    assert session["mode"] == "import" and session["line_count"] == 600


def test_import_unknown_source(client):
    r = upload(client, 999, paragraphs_epub("本文。"))
    assert r.status_code == 404
    assert r.json()["error"]["code"] == "not_found"
