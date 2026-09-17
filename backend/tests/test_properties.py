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
def test_tokenize_covers_every_non_space_character(text):
    """Highlighting uses token offsets; a dropped or invented character shifts
    every later span. Whitespace is deliberately not tokenized, so the property
    is over the non-space characters (frozen example below)."""
    normalized = normalize_ocr(text)
    tokens = tokenize(normalized)
    assert "".join(token.surface for token in tokens) == "".join(normalized.split())


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
@given(JP)
def test_mora_count_is_non_negative_and_ignores_small_kana_positions(text):
    assert mora_count(text) >= 0
    small_kana = "ぁぃぅぇぉゃゅょゎァィゥェォャュョヮ"
    assert mora_count(text) == mora_count("".join(ch for ch in text if ch not in small_kana))


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


def test_tokenize_does_not_emit_whitespace():
    """Found by the property test above: ': :' tokenizes to two tokens whose
    surfaces join to '::'. The offsets still point at the right characters, but
    the concatenation is not character-for-character the input."""
    normalized = normalize_ocr(": :")
    assert "".join(token.surface for token in tokenize(normalized)) == "::"
    starts = [token.start for token in tokenize(normalized)]
    assert starts == [0, 2]
