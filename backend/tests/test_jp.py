from kotoba.services.jp import contractions, kana
from kotoba.services.jp.normalize import normalize_ocr, text_hash
from kotoba.services.jp.tokenizer import tokenize


def test_normalize_collapses_ocr_dots_into_ellipsis():
    assert normalize_ocr("しょうがないなぁ・・・・・今日は") == "しょうがないなぁ…今日は"
    assert normalize_ocr("え...本当に？") == "え…本当に？"


def test_normalize_removes_whitespace_between_cjk():
    assert normalize_ocr("今日 は\n俺が　奢る") == "今日は俺が奢る"
    assert normalize_ocr("  hello   world ") == "hello world"


def test_normalize_halfwidth_katakana():
    assert normalize_ocr("ｶﾞｰﾙ") == "ガール"


def test_text_hash_is_stable_across_ocr_jitter():
    assert text_hash("え…本当に？") == text_hash("え・・・本当に？")


def test_tokenize_gives_base_form_and_readings():
    tokens = tokenize("今日は俺が奢ってやるよ。")
    ogoru = next(t for t in tokens if t.surface == "奢っ")
    assert ogoru.base == "奢る"
    assert ogoru.reading == "おごっ"
    assert ogoru.reading_base == "おごる"
    assert ogoru.pos1 == "動詞"
    assert ogoru.is_content
    assert "今日は俺が奢ってやるよ。"[ogoru.start : ogoru.end] == "奢っ"
    particle = next(t for t in tokens if t.surface == "は")
    assert not particle.is_content


def test_tokenize_positions_cover_text():
    text = "「え、本当に？」"
    tokens = tokenize(text)
    assert "".join(text[t.start : t.end] for t in tokens) == text


def test_contractions():
    assert contractions.expand("ちゃう") == "てしまう"
    assert contractions.expand("奢る") is None
    forms = [r["form"] for r in contractions.find_in("食べちゃったんだ")]
    assert forms[0] == "ちゃった"
    assert "んだ" in forms


def test_kana_helpers():
    assert kana.to_hiragana("キョウ") == "きょう"
    assert kana.to_katakana("おごる") == "オゴル"
    assert kana.kana_equal("オゴル", "おごる")
    assert kana.kana_equal("きょう ", "ｷｮｳ")
    assert kana.is_kanji("奢") and not kana.is_kanji("あ")
    assert kana.has_kanji("奢る") and not kana.has_kanji("おごる")
    assert kana.is_all_kana("おごって") and not kana.is_all_kana("奢って")


def test_contractions_align_to_token_boundaries():
    surfaces = [t.surface for t in tokenize("しょうがないなぁ…今日は俺が奢ってやるよ。")]
    forms = [r["form"] for r in contractions.find_in_tokens(surfaces)]
    assert "しょうがない" in forms
    assert "って" not in forms  # って inside 奢って is the te-form, not the quotative
    surfaces = [t.surface for t in tokenize("食べちゃったんだ")]
    forms = [r["form"] for r in contractions.find_in_tokens(surfaces)]
    assert "ちゃった" in forms and "んだ" in forms
