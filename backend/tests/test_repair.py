"""OCR kana repair: tokenizer and dictionary have to agree before a word changes.

The tokenizer alone calls both ください and どうじよう words, so every lexical
fix here is gated on the dictionary callback; the 促音便 rule is grammar and
needs no dictionary. When in doubt the original text wins.
"""

from __future__ import annotations

from kotoba.services.jp.repair import repair_ocr

WORDS = {"やっぱり", "ください", "カッコ", "もっと", "ずっと"}


def in_dict(form: str) -> bool:
    return form in WORDS


def test_small_kana_is_restored_inside_a_word():
    assert repair_ocr("やつばりそうだったんだ", in_dict) == "やっぱりそうだったんだ"


def test_dakuten_is_restored():
    assert repair_ocr("しゃべらないでくたさい", in_dict) == "しゃべらないでください"


def test_katakana_small_kana_is_restored():
    assert repair_ocr("カツコ", in_dict) == "カッコ"


def test_sokuon_before_te_needs_no_dictionary():
    nothing = lambda _: False  # noqa: E731
    assert repair_ocr("まつてください", nothing) == "まってください"
    assert repair_ocr("たつてしまつた", nothing) == "たってしまった"
    assert repair_ocr("わかつてる", nothing) == "わかってる"


def test_without_a_dictionary_the_lexical_half_stays_off():
    assert repair_ocr("やつばり", lambda _: False) == "やつばり"


def test_ambiguous_text_is_left_alone():
    # どうじよう is a word to the tokenizer (動じよう) but not a dictionary
    # form; かつて, きて, そとにでる are already words. Nothing here may change.
    for text in (
        "どうしようもない。",
        "きてよ",
        "してる",
        "みよう",
        "かつてそうだった。",
        "そとにでる。",
        "打つ手がない。",
    ):
        assert repair_ocr(text, in_dict) == text


def test_a_candidate_that_is_not_one_word_is_refused():
    # またね -> まだね would split into まだ + ね, and ずっとひ -> すっとび
    # would cut ひとり in half to find a word; neither is a repair.
    assert repair_ocr("またね", lambda _: True) == "またね"
    assert repair_ocr("ずっとひとりだった。", lambda _: True) == "ずっとひとりだった。"


def test_repair_is_idempotent():
    for text in ("やつばりそうだったんだ", "しゃべらないでくたさい", "カツコ", "まつてください"):
        once = repair_ocr(text, in_dict)
        assert repair_ocr(once, in_dict) == once
