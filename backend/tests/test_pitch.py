import io
import json
import time
import zipfile

from sqlalchemy import func, select

from kotoba.models import TermPitch
from kotoba.services.dictionary import pitch
from kotoba.services.jp import mora

KANJIUM_SAMPLE = (
    "１\tいち\t2\n"
    "１\tひと\t0,2\n"
    "猫\tねこ\t1\n"
    "卵\tたまご\t2\n"
    "妹\tいもうと\t4\n"
    "東京\tとうきょう\t0\n"
    "壊れ物\tこわれもの\t(名)0\n"
    "ゴミ\tごみ\t\n"  # no number at all: skipped
    "tabless\n"  # not a three-column line: skipped
)


def pitch_zip(entries: list) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("index.json", json.dumps({"title": "音高表", "format": 3}))
        zf.writestr("term_meta_bank_1.json", json.dumps(entries))
    return buf.getvalue()


def upload_yomitan(client, data: bytes):
    return client.post(
        "/api/dict/yomitan/import",
        files={"file": ("pitch.zip", data, "application/zip")},
    )


def rows(db) -> list[tuple[str, str, int]]:
    return [
        (p.headword, p.reading, p.accent)
        for p in db.scalars(select(TermPitch).order_by(TermPitch.id)).all()
    ]


def test_mora_count_handles_youon_sokuon_and_chouon():
    assert mora.mora_count("きょう") == 2  # きょ is one mora
    assert mora.mora_count("しゅう") == 2
    assert mora.mora_count("がっこう") == 4  # っ is its own mora
    assert mora.mora_count("コーヒー") == 4  # ー is its own mora
    assert mora.mora_count("しんぶん") == 4  # ん counts
    assert mora.mora_count("とうきょう") == 4
    assert mora.mora_count("きって") == 3
    assert mora.mora_count("ｷｮｳ") == 2  # half-width katakana read the same
    assert mora.mora_count("") == 0


def test_pattern_covers_the_four_accent_types():
    assert pitch.pattern("とうきょう", 0) == "heiban"
    assert pitch.pattern("ねこ", 1) == "atamadaka"
    assert pitch.pattern("たまご", 2) == "nakadaka"
    assert pitch.pattern("いもうと", 4) == "odaka"  # accent == mora count
    assert pitch.pattern("いもうと", 5) == "odaka"  # dirty data past the last mora


def test_import_kanjium_reads_multi_and_dirty_accents(client, db):
    count = pitch.import_kanjium(db, KANJIUM_SAMPLE)
    assert count == 8  # 0,2 counts twice; the two bad lines are skipped
    stored = rows(db)
    assert ("１", "いち", 2) in stored
    assert ("１", "ひと", 0) in stored and ("１", "ひと", 2) in stored
    assert ("壊れ物", "こわれもの", 0) in stored  # the (名) annotation is ignored
    assert not [row for row in stored if row[0] == "ゴミ"]

    # Re-import replaces instead of piling up.
    pitch.import_kanjium(db, "猫\tねこ\t1\n")
    assert rows(db) == [("猫", "ねこ", 1)]


def test_import_yomitan_pitch_bank(client, db):
    data = pitch_zip(
        [
            ["水", "pitch", {"reading": "みず", "pitches": [{"position": 0}, {"position": 2}]}],
            ["犬", "pitch", {"reading": "いぬ", "pitches": [1]}],
            ["鳥", "pitch", {"pitches": [{"position": 0}]}],  # no reading → skipped
            ["魚", "freq", 10],  # not pitch → skipped
        ]
    )
    r = upload_yomitan(client, data)
    assert r.status_code == 200, r.text
    assert r.json()["kind"] == "pitch"
    assert r.json()["pitches"] == 3
    assert ("水", "みず", 0) in rows(db)
    assert ("水", "みず", 2) in rows(db)
    assert ("犬", "いぬ", 1) in rows(db)


def test_pitch_install_endpoint_runs_the_job(client, monkeypatch, data_dir):
    def fake_download(url: str, dest):
        dest.write_text(KANJIUM_SAMPLE, encoding="utf-8")
        return dest

    monkeypatch.setattr(pitch, "download_text", fake_download)
    r = client.post("/api/dict/pitch/install")
    assert r.status_code == 202
    assert r.json()["started"] is True

    def finished() -> bool:
        return client.get("/api/dict/status").json()["pitch"]["state"] == "done"

    deadline = time.monotonic() + 5
    while time.monotonic() < deadline and not finished():
        time.sleep(0.02)
    assert finished()
    assert client.get("/api/dict/status").json()["pitch"]["message"] == "音高数据已安装"
    assert client.get("/api/dict/status").json()["has_pitch"] is True


def test_pitch_table_is_unique_per_headword_reading_accent(client, db):
    pitch.import_kanjium(db, "猫\tねこ\t1\n猫\tねこ\t1\n")
    assert db.scalar(select(func.count(TermPitch.id))) == 1
