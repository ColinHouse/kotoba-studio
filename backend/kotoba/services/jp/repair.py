"""Conservative repair of OCR-confused kana.

OCR engines read a small kana as its full-size sibling (っ→つ, カッコ→カツコ)
or drop a dakuten (ください→くたさい) often enough that the user has to fix
the line by hand. Nothing downstream can notice: every character is valid
Japanese, and the wrong spelling tokenizes too — just to the wrong words.

This module retries the neighbouring spellings of a kana run and keeps a
candidate only when two independent things agree: the tokenizer must read the
whole span as exactly one content word, and the caller's dictionary must have
that word. Among the words that fit, the one restoring the most small kana
(the mistake OCR is known to make) wins; if that still leaves two overlapping
candidates, the line is left alone. A candidate that merely makes the line
"score better" is not enough — ``だね`` would become ``たね`` that way, and
``どうしよう`` would become ``どうじよう``. The rule for つ-verbs before て/た
(促音便) is grammar, not a guess.

The dictionary enters as a callback (like ``expressions.group``'s reading
lookup) so this module stays free of the database. Only OCR output goes
through it: hook and clipboard text is already exact and must never be
rewritten.
"""

from __future__ import annotations

from collections.abc import Callable
from itertools import combinations, product

from kotoba.services.jp.kana import is_all_kana, is_kana
from kotoba.services.jp.tokenizer import Token, tokenize

WordCheck = Callable[[str], bool]

# Longer than this is prose, not a misread word. Two substitutions cover the
# observed errors (つ→っ, た→だ); the caps keep tokenizing sane on a kana-only
# line, and when the budget runs out the text is simply left alone.
_MAX_SPAN = 6
_MAX_SUBSTITUTIONS = 2
_MAX_VARIANTS = 64
_MAX_CHECKS = 200

_CONTENT_POS = {"名詞", "動詞", "形容詞", "副詞", "形状詞", "接続詞"}
_VERB_LIKE_POS = {"動詞", "助動詞", "名詞", "記号"}
_SEMI = set("ぱぴぷぺぽパピプペポ")

_SMALL_LARGE = (
    ("ぁ", "あ"),
    ("ぃ", "い"),
    ("ぅ", "う"),
    ("ぇ", "え"),
    ("ぉ", "お"),
    ("っ", "つ"),
    ("ゃ", "や"),
    ("ゅ", "ゆ"),
    ("ょ", "よ"),
    ("ゎ", "わ"),
    ("ァ", "ア"),
    ("ィ", "イ"),
    ("ゥ", "ウ"),
    ("ェ", "エ"),
    ("ォ", "オ"),
    ("ッ", "ツ"),
    ("ャ", "ヤ"),
    ("ュ", "ユ"),
    ("ョ", "ヨ"),
    ("ヮ", "ワ"),
)

# One group per sound that OCR hears unclearly: the base kana, its voiced
# form and (for は行) its semi-voiced form are all one edit away.
_ROWS = (
    "かが",
    "きぎ",
    "くぐ",
    "けげ",
    "こご",
    "さざ",
    "しじ",
    "すず",
    "せぜ",
    "そぞ",
    "ただ",
    "ちぢ",
    "つづ",
    "てで",
    "とど",
    "はばぱ",
    "ひびぴ",
    "ふぶぷ",
    "へべぺ",
    "ほぼぽ",
    "うゔ",
    "カガ",
    "キギ",
    "クグ",
    "ケゲ",
    "コゴ",
    "サザ",
    "シジ",
    "スズ",
    "セゼ",
    "ソゾ",
    "タダ",
    "チヂ",
    "ツヅ",
    "テデ",
    "トド",
    "ハバパ",
    "ヒビピ",
    "フブプ",
    "ヘベペ",
    "ホボポ",
    "ウヴ",
)


def _build_alternates() -> dict[str, frozenset[str]]:
    table: dict[str, set[str]] = {}
    for group in (*_SMALL_LARGE, *_ROWS):
        for char in group:
            table.setdefault(char, set()).update(set(group) - {char})
    return {char: frozenset(alts) for char, alts in table.items()}


_ALTERNATES = _build_alternates()
_SMALL_OF = {large: small for small, large in _SMALL_LARGE}


def _has_kana(text: str) -> bool:
    return any(is_kana(char) for char in text)


def _mutable(token: Token) -> bool:
    """A token whose spelling the repair is allowed to question."""
    return token.pos1 in {"未知語", "記号"} or is_all_kana(token.surface)


def _spans(tokens: list[Token]) -> list[tuple[int, int]]:
    """Index ranges of adjacent mutable tokens (inclusive)."""
    spans: list[tuple[int, int]] = []
    index = 0
    while index < len(tokens):
        if not _mutable(tokens[index]):
            index += 1
            continue
        end = index
        while end + 1 < len(tokens) and _mutable(tokens[end + 1]):
            end += 1
        if end > index:
            spans.append((index, end))
        index = end + 1
    return spans


def _variants(span: str) -> list[str]:
    positions = [i for i, char in enumerate(span) if char in _ALTERNATES]
    out: list[str] = []
    for count in (1, _MAX_SUBSTITUTIONS):
        for indexes in combinations(positions, count):
            options = [sorted(_ALTERNATES[span[i]]) for i in indexes]
            for replacement in product(*options):
                chars = list(span)
                for i, char in zip(indexes, replacement, strict=True):
                    chars[i] = char
                out.append("".join(chars))
                if len(out) >= _MAX_VARIANTS:
                    return out
    return out


def _changes(span: str, variant: str) -> tuple[list[int], list[int], list[int]]:
    """Where the variant restores small kana, loses them, or re-voices."""
    small: list[int] = []
    loss: list[int] = []
    voice: list[int] = []
    for index, (before, after) in enumerate(zip(span, variant, strict=True)):
        if before == after:
            continue
        if _SMALL_OF.get(before) == after:
            small.append(index)
        elif _SMALL_OF.get(after) == before:
            loss.append(index)
        else:
            voice.append(index)
    return small, loss, voice


def _is_word(variant: str) -> bool:
    tokens = tokenize(variant)
    return len(tokens) == 1 and tokens[0].surface == variant and tokens[0].pos1 in _CONTENT_POS


def _covers(line: str, start: int, end: int) -> bool:
    """The replaced span now reads as exactly one content word."""
    tokens = [t for t in tokenize(line) if t.start >= start and t.end <= end]
    if len(tokens) != 1:
        return False
    token = tokens[0]
    return token.start == start and token.end == end and token.pos1 in _CONTENT_POS


def _windows(text: str, tokens: list[Token], start: int, end: int):
    left = tokens[start].start
    right = tokens[end].end
    starts = {tokens[i].start for i in range(start, end + 1)}
    for window_start in range(left, right - 2):
        for length in range(3, _MAX_SPAN + 1):
            window_end = window_start + length
            if window_end > right:
                break
            if sum(1 for s in starts if window_start <= s < window_end) < 2:
                continue
            span = text[window_start:window_end]
            if not _has_kana(span) or not any(c in _ALTERNATES for c in span):
                continue
            yield window_start, window_end, span


def _lexical(text: str, in_dictionary: WordCheck) -> str:
    budget = _MAX_CHECKS
    known: dict[str, bool] = {}

    def dictionary_has(form: str) -> bool:
        if form not in known:
            known[form] = in_dictionary(form)
        return known[form]

    while budget > 0:
        tokens = tokenize(text)
        ends = {token.end for token in tokens}
        candidates: list[tuple[int, int, int, int, str]] = []
        for start, end in _spans(tokens):
            for left, right, span in _windows(text, tokens, start, end):
                # A word that ends mid-token is cutting one word in half and
                # gluing it to the next -- ずっとひ -> すっとび is born that way.
                if right not in ends:
                    continue
                for variant in _variants(span):
                    # The edges of a word are legible; OCR muddles the middle.
                    if variant[0] != span[0] or variant[-1] != span[-1]:
                        continue
                    small, loss, voice = _changes(span, variant)
                    # A change that loses a small kana is the wrong direction
                    # (OCR reads small as large, not the reverse), and a
                    # candidate that mixes both directions is not credible.
                    if loss or not (small or voice):
                        continue
                    # One kind of confusion per candidate -- except 促音便,
                    # where a restored っ semi-voices a following は行 kana
                    # (やつばり -> やっぱり).
                    if (
                        small
                        and voice
                        and any(
                            position - 1 not in small or variant[position] not in _SEMI
                            for position in voice
                        )
                    ):
                        continue
                    if not _is_word(variant):
                        continue
                    if not dictionary_has(variant):
                        continue
                    budget -= 1
                    if budget < 0:
                        return text
                    if not _covers(text[:left] + variant + text[right:], left, right):
                        continue
                    candidates.append((right - left, len(small), len(voice), left, variant))
        if not candidates:
            return text
        # Longest fit wins; small kana first, then dakuten. Two overlapping
        # candidates with the same evidence mean the choice is not forced.
        top = max(candidates, key=lambda c: (c[0], c[1], c[2]))
        best = [c for c in candidates if (c[0], c[1], c[2]) == (top[0], top[1], top[2])]
        if any(
            a[3] != b[3] and not (a[3] + a[0] <= b[3] or b[3] + b[0] <= a[3])
            for a in best
            for b in best
        ):
            return text
        if len({c[4] for c in best if c[3] == top[3]}) != 1:
            return text
        _, _, _, left, variant = top
        text = text[:left] + variant + text[left + top[0] :]
    return text


def _repair_te_form(text: str) -> str:
    """つ-verbs take 促音便 before て/た; anything else is a misread っ."""
    tokens = tokenize(text)
    fixes: list[int] = []
    for token, follower in zip(tokens, tokens[1:], strict=False):
        if token.pos1 not in _VERB_LIKE_POS or not token.surface.endswith(("つ", "ツ")):
            continue
        attaches = follower.surface.startswith(("て", "テ")) or (
            follower.pos1 == "助動詞" and follower.lemma == "た"
        )
        if not attaches or not follower.surface.startswith(("て", "た", "テ", "タ")):
            continue
        fixes.append(token.end - 1)
    for position in fixes:
        small = "ッ" if text[position] == "ツ" else "っ"
        candidate = text[:position] + small + text[position + 1 :]
        # Only keep the change when the tokenizer confirms a verb now covers
        # the spot and that verb sits in 促音便.
        repaired = next((t for t in tokenize(candidate) if t.start <= position < t.end), None)
        if repaired is None or repaired.pos1 != "動詞":
            continue
        if not repaired.surface.endswith(("っ", "ッ")):
            continue
        text = candidate
    return text


def repair_ocr(text: str, in_dictionary: WordCheck) -> str:
    """Fix the small-kana and voicing mistakes OCR is known to make.

    ``in_dictionary`` answers whether a written form exists in the user's
    imported dictionaries; without one the lexical half cannot run, because
    the tokenizer alone calls both ください and どうじよう words. Ambiguity is
    resolved in favour of the original text.
    """
    if not text:
        return text
    text = _repair_te_form(text)
    text = _lexical(text, in_dictionary)
    return _repair_te_form(text)
