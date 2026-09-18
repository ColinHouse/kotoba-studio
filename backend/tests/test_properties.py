"""Property tests for the Japanese text pipeline (issue #71).

Hand-written examples only cover the cases someone thought of; these properties
must hold for every input. Counterexamples found here are frozen as plain tests
at the bottom, so a regression cannot hide behind the generator.
"""

from __future__ import annotations

from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from kotoba.core.errors import ApiError
from kotoba.services.dictionary.pitch import pattern
from kotoba.services.jp.mora import mora_count
from kotoba.services.jp.normalize import normalize_ocr
from kotoba.services.jp.tokenizer import tokenize
from kotoba.services.text.subtitles import parse_subtitles

# Every letter the pipeline can meet: kana, kanji, half-width kana, punctuation.
# ASCII alone would never reach the interpunct, the half-width kana or the
# full-width minus that the OCR path actually sees.
_ALPHABET = (
    "あいうえおかきくけこさしすせそたちつてとなにぬねのはひふへほまみむめもやゆよらりるれろわをん"
    "がぎぐげござじずぜぞだぢづでどばびぶべぼぱぴぷぺぽっゃゅょゎー"
    "アイウエオカキクケコサシスセソタチツテトナニヌネノハヒフヘホマミムメモヤユヨラリルレロワオン"
    "ガギグゲゴザジズゼゾダヂヅデドバビブベボパピプペポッャュョヮ"
    "漢字日本語文字猫犬辛奢願買売"
    "ｱｲｳｴｵｶﾞｷﾞｸﾞｯｰ"
    "。、！？…・「」『』（）〈〉【】〜～\n\r\t 　.．,，:：;；-－_"
)

JP = st.text(st.sampled_from(_ALPHABET), max_size=12)

# `sampled_from` draws single characters, so the half-width `ｶﾞ` above also lets a
# bare voiced mark be generated on its own, anywhere in the string. That is worth
# keeping — OCR really does emit stray marks — but a mark means whatever precedes
# it, so any property that *removes a character* is not well defined against one.
_DANGLING_MARKS = "ﾞﾟ゛゜"
JP_NO_DANGLING_MARKS = st.text(
    st.sampled_from([ch for ch in _ALPHABET if ch not in _DANGLING_MARKS]), max_size=12
)

# Bounded on purpose: CI should not pay for the generator, only for the finding.
_QUICK = settings(max_examples=200, deadline=None)
_SLOW = settings(max_examples=80, deadline=None, suppress_health_check=[HealthCheck.too_slow])


@_QUICK
@given(JP)
def test_normalize_ocr_is_idempotent(text):
    """The pipeline normalizes more than once (ingest, then looks_like_line);
    a second pass that changes the text again would poison the stored hash."""
    once = normalize_ocr(text)
    assert normalize_ocr(once) == once


@_SLOW
@given(JP)
def test_tokenize_offsets_point_at_their_surface(text):
    """Highlighting slices the line by these offsets. Dropped or invented
    characters, or an offset that points somewhere else, shifts every later
    span; the surfaces themselves are the tagger's business (it drops ASCII
    spaces and keeps U+3000 — both frozen below)."""
    normalized = normalize_ocr(text)
    cursor = 0
    for token in tokenize(normalized):
        assert token.start >= cursor
        assert normalized[token.start : token.end] == token.surface
        cursor = token.end


@_SLOW
@given(JP)
def test_parse_subtitles_returns_cues_or_a_readable_error(text):
    """Subtitle files come from the internet: junk must become an ApiError
    (the error envelope), never a stray exception or half-parsed output."""
    try:
        cues = parse_subtitles(text)
    except ApiError:
        return
    assert isinstance(cues, list)
    assert all(cue.start_ms >= 0 and cue.end_ms >= cue.start_ms for cue in cues)


@_QUICK
@given(JP_NO_DANGLING_MARKS)
def test_mora_count_is_non_negative_and_ignores_small_kana_positions(text):
    assert mora_count(text) >= 0
    small_kana = "ぁぃぅぇぉゃゅょゎァィゥェォャュョヮ"
    assert mora_count(text) == mora_count("".join(ch for ch in text if ch not in small_kana))


def test_a_voiced_mark_belongs_to_whatever_precedes_it():
    """Why the property above excludes bare marks, pinned so the reason survives.

    `mora_count` normalises before counting, so a mark that follows a small kana
    stays separate, while the same mark after a full kana composes into one. Take
    the small kana out and the mark changes owner — the count legitimately drops.
    Neither order of normalise-and-remove avoids this; it is what a combining
    character means, not a defect in `mora_count`.
    """
    assert mora_count("かゎﾞ") == 2  # か + ゎ, mark cannot attach to the small kana
    assert mora_count("かﾞ") == 1  # composes to が


@_QUICK
@given(JP, st.integers(min_value=0, max_value=40))
def test_pitch_pattern_is_always_one_of_the_four(text, accent):
    """An out-of-range accent (a hand-written deck, a bad import) must not crash
    the card face; every accent maps to one of the four patterns."""
    assert pattern(text, accent) in {"heiban", "atamadaka", "nakadaka", "odaka"}


# --- Frozen examples: the rules the generator is not good at expressing. ------


def test_mora_count_rules():
    """拗音一拍；促音与长音各占一拍；ん算一拍。"""
    assert mora_count("きょ") == 1
    assert mora_count("がっこう") == 4
    assert mora_count("コーヒー") == 4
    assert mora_count("ん") == 1
    assert mora_count("") == 0


def test_pitch_pattern_rules():
    assert pattern("きょ", 0) == "heiban"
    assert pattern("きょ", 1) == "atamadaka"
    assert pattern("きょ", 2) == "odaka"  # accent == mora count
    assert pattern("きょ", 99) == "odaka"  # out of range must not crash
    assert pattern("がっこう", 2) == "nakadaka"


def test_tokenize_whitespace_is_the_taggers_business():
    """Two counterexamples the property above found, in order: ASCII spaces are
    dropped (': :' -> '::' with offsets 0 and 2), while the ideographic space is
    kept inside a token (':\\u3000:' joins to the same string). The offsets stay
    correct in both cases, which is what highlighting needs."""
    narrow = tokenize(normalize_ocr(": :"))
    assert "".join(token.surface for token in narrow) == "::"
    assert [token.start for token in narrow] == [0, 2]

    wide = tokenize(normalize_ocr(":\u3000:"))
    assert "".join(token.surface for token in wide) == ":\u3000:"
    assert wide[0].start == 0
