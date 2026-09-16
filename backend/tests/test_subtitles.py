import pytest

from kotoba.core.errors import ApiError
from kotoba.services.text.subtitles import Cue, parse_subtitles

SRT = """\
1
00:00:01,500 --> 00:00:03,000
「おはよう」

2
00:00:04,000 --> 00:00:06,250
今日はいい天気だね
"""

ASS = (
    "[Script Info]\n"
    "Title: test\n"
    "ScriptType: v4.00+\n"
    "\n"
    "[Events]\n"
    "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"
    "Dialogue: 0,0:00:01.50,0:00:03.00,Default,アリス,0,0,0,,{\\pos(320,240)}こんにちは\\N世界\n"
    "Dialogue: 0,0:00:04.00,0:00:06.00,Default,,0,0,0,,次の台詞, ここにもカンマ\n"
)


def test_parse_srt_reads_timings_and_text():
    assert parse_subtitles(SRT) == [
        Cue(1500, 3000, "「おはよう」"),
        Cue(4000, 6250, "今日はいい天気だね"),
    ]


def test_parse_srt_merges_multiline_body_and_tolerates_missing_index():
    content = "00:00:01,000 --> 00:00:02,000\n第一行\n第二行\n\n00:00:03,000-->00:00:04,500\n次の行"
    cues = parse_subtitles(content)
    assert [c.text for c in cues] == ["第一行 第二行", "次の行"]
    assert (cues[1].start_ms, cues[1].end_ms) == (3000, 4500)


def test_parse_srt_tolerates_bom_crlf_and_trailing_blank_lines():
    content = "\ufeff1\r\n00:00:01,000 --> 00:00:02,000\r\nセリフ\r\n\r\n\r\n"
    assert parse_subtitles(content) == [Cue(1000, 2000, "セリフ")]


def test_parse_srt_drops_cues_that_are_empty_after_cleaning():
    content = "1\n00:00:01,000 --> 00:00:02,000\n   \n\n2\n00:00:03,000 --> 00:00:04,000\n本編\n"
    assert parse_subtitles(content) == [Cue(3000, 4000, "本編")]


def test_parse_ass_uses_format_line_for_field_order():
    content = (
        "[Script Info]\n"
        "Title: test\n"
        "\n"
        "[Events]\n"
        "Format: Start, End, Name, Text\n"
        "Dialogue: 0:00:01.50,0:00:03.00,ボブ,こんにちは\n"
        "Dialogue: 0:00:04.00,0:00:06.00,,またね\n"
    )
    assert parse_subtitles(content) == [
        Cue(1500, 3000, "こんにちは", "ボブ"),
        Cue(4000, 6000, "またね"),
    ]


def test_parse_ass_cleans_override_blocks_and_escapes():
    content = (
        "[Events]\n"
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"
        "Dialogue: 0,0:00:01.50,0:00:03.00,Default,,0,0,0,,"
        "{\\pos(320,240)\\fad(200,200)}おはよう\\Nいい天気だね\\hね\\n明日も\n"
    )
    assert parse_subtitles(content) == [Cue(1500, 3000, "おはよう いい天気だね ね 明日も")]


def test_parse_ass_keeps_commas_in_text_and_converts_centiseconds():
    content = (
        "[Events]\n"
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"
        "Dialogue: 0,0:00:01.25,0:01:02.75,Default,キャラ,0,0,0,,え、本当に？, そうか\n"
    )
    (cue,) = parse_subtitles(content)
    assert (cue.start_ms, cue.end_ms) == (1250, 62750)
    assert cue.text == "え、本当に？, そうか"
    assert cue.speaker == "キャラ"


def test_parse_ass_drops_cues_that_are_empty_after_cleaning():
    content = (
        "[Events]\n"
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"
        "Dialogue: 0,0:00:01.00,0:00:02.00,Default,,0,0,0,,{\\fad(100,100)}\n"
        "Dialogue: 0,0:00:03.00,0:00:04.00,Default,,0,0,0,,本編\n"
    )
    assert parse_subtitles(content) == [Cue(3000, 4000, "本編")]


def test_parse_ass_tolerates_bom_crlf_and_missing_name_field():
    content = (
        "\ufeff[Events]\r\nFormat: Start, End, Text\r\nDialogue: 0:00:01.50,0:00:03.00,朝だ\r\n"
    )
    assert parse_subtitles(content) == [Cue(1500, 3000, "朝だ")]


def test_parse_subtitles_detects_ass_by_events_section():
    cues = parse_subtitles(ASS)
    assert cues[0] == Cue(1500, 3000, "こんにちは 世界", "アリス")
    assert cues[1] == Cue(4000, 6000, "次の台詞, ここにもカンマ")


def test_parse_subtitles_honours_explicit_format():
    assert parse_subtitles(SRT, fmt="srt")[0].start_ms == 1500
    with pytest.raises(ApiError) as err:
        parse_subtitles(SRT, fmt="ass")
    assert err.value.code == "bad_subtitle"


def test_parse_subtitles_rejects_unknown_format():
    with pytest.raises(ApiError) as err:
        parse_subtitles(SRT, fmt="vtt")
    assert err.value.code == "bad_subtitle"


def test_parse_subtitles_raises_when_nothing_parses():
    for content in ("", "这不是字幕", "1\n00:00:01,000 --> 00:00:02,000\n   "):
        with pytest.raises(ApiError) as err:
            parse_subtitles(content)
        assert err.value.code == "bad_subtitle"


def test_srt_quoting_events_is_not_mistaken_for_ass():
    content = "1\n00:00:01,000 --> 00:00:02,000\nゲームの [Events] について\n"
    assert parse_subtitles(content) == [Cue(1000, 2000, "ゲームの [Events] について")]


def test_parse_srt_strips_inline_markup_but_keeps_a_bare_angle_bracket():
    content = (
        "1\n00:00:01,000 --> 00:00:02,000\n<i>今日は</i>\n\n"
        "2\n00:00:03,000 --> 00:00:04,000\n{\\an8}上の字幕\n\n"
        '3\n00:00:05,000 --> 00:00:06,000\n<font color="#fff">色</font>\n\n'
        "4\n00:00:07,000 --> 00:00:08,000\n5 < 10 だ\n"
    )
    assert [c.text for c in parse_subtitles(content)] == ["今日は", "上の字幕", "色", "5 < 10 だ"]


def test_parse_srt_drops_cues_that_are_only_markup():
    content = (
        "1\n00:00:01,000 --> 00:00:02,000\n<i></i>\n\n2\n00:00:03,000 --> 00:00:04,000\n本編\n"
    )
    assert parse_subtitles(content) == [Cue(3000, 4000, "本編")]


def test_parse_ass_removes_drawing_mode_payloads():
    header = (
        "[Events]\n"
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"
    )
    content = header + (
        "Dialogue: 0,0:00:01.00,0:00:02.00,D,,0,0,0,,{\\p1}m 0 0 l 100 0 100 100{\\p0}\n"
        "Dialogue: 0,0:00:03.00,0:00:04.00,D,,0,0,0,,{\\p1}m 0 0 l 5 5{\\p0}こんにちは\n"
        "Dialogue: 0,0:00:05.00,0:00:06.00,D,,0,0,0,,{\\pos(320,240)}おはよう\n"
    )
    assert parse_subtitles(content) == [
        Cue(3000, 4000, "こんにちは"),
        Cue(5000, 6000, "おはよう"),
    ]


def test_parse_ass_drops_an_unterminated_drawing_event():
    content = (
        "[Events]\n"
        "Format: Start, End, Text\n"
        "Dialogue: 0:00:01.00,0:00:02.00,{\\p4}m 0 0 l 9 9\n"
        "Dialogue: 0:00:03.00,0:00:04.00,本編\n"
    )
    assert parse_subtitles(content) == [Cue(3000, 4000, "本編")]


def test_parse_ass_collapses_runs_of_whitespace_from_escapes():
    content = "[Events]\nFormat: Start, End, Text\nDialogue: 0:00:01.00,0:00:02.00,あ\\N\\Nい\n"
    assert parse_subtitles(content) == [Cue(1000, 2000, "あ い")]
