from __future__ import annotations

import time
from pathlib import Path

import pytest

from kotoba.api.capture import condensed
from kotoba.core.errors import ApiError
from kotoba.models import CaptureSession, Line, Source
from kotoba.services.capture import media
from kotoba.services.text.subtitles import Cue

SRT = (
    "1\n00:00:01,000 --> 00:00:03,000\nこんにちは\n\n2\n00:00:04,000 --> 00:00:06,500\nさようなら\n"
)


def _source(db) -> Source:
    source = Source(title="episode 1", kind="anime")
    db.add(source)
    db.commit()
    return source


def _video_in(tmp_path) -> Path:
    folder = tmp_path / "anime"
    folder.mkdir(exist_ok=True)
    video = folder / "ep01.mkv"
    video.write_bytes(b"")
    return video


def test_audio_args_pad_both_ends():
    args = media.audio_args("ffmpeg", Path("in.mp4"), 1000, 3000, Path("out.opus"))
    assert args == [
        "ffmpeg",
        "-y",
        "-ss",
        "0.750",
        "-i",
        "in.mp4",
        "-t",
        "2.750",
        "-vn",
        "-c:a",
        "libopus",
        "-b:a",
        "64k",
        "out.opus",
    ]


def test_audio_args_clamp_the_head_at_zero():
    args = media.audio_args("ffmpeg", Path("in.mp4"), 100, 200, Path("out.opus"))
    assert args[args.index("-ss") + 1] == "0.000"
    assert args[args.index("-t") + 1] == "0.700"  # 200 + 500 tail, no negative head


def test_frame_args_take_the_midpoint():
    args = media.frame_args("ffmpeg", Path("in.mp4"), 2000, Path("out.jpg"))
    assert args[args.index("-ss") + 1] == "2.000"
    assert args[-1] == "out.jpg"


def test_resolve_video_allows_only_listed_directories(tmp_path):
    video = _video_in(tmp_path)
    assert media.resolve_video(str(video), [str(video.parent)]) == video.resolve()

    with pytest.raises(ApiError) as outside:
        media.resolve_video(str(video), [str(tmp_path / "elsewhere")])
    assert outside.value.code == "video_not_allowed"

    with pytest.raises(ApiError) as missing:
        media.resolve_video(str(video.parent / "nope.mkv"), [str(video.parent)])
    assert missing.value.code == "video_not_found"


def test_cut_cues_isolates_a_failing_cue(tmp_path, monkeypatch):
    monkeypatch.setattr(media, "ffmpeg_path", lambda: "ffmpeg")
    calls: list[list[str]] = []

    def runner(args) -> None:
        calls.append(list(args))
        if "00002" in args[-1]:
            raise RuntimeError("boom")
        Path(args[-1]).write_bytes(b"x")

    cues = [
        Cue(1000, 2000, "a"),
        Cue(3000, 4000, "b"),
        Cue(5000, 6000, "c"),
        Cue(7000, 8000, "d"),
    ]
    cuts = media.cut_cues(Path("in.mp4"), cues, tmp_path, runner=runner, max_workers=2)

    assert [cut is None for cut in cuts] == [False, False, True, False]
    assert cuts[1] is not None
    assert cuts[1].audio_path.startswith("audio/") and cuts[1].audio_path.endswith(".opus")
    assert cuts[1].screenshot_path.startswith("screens/")
    assert cuts[1].screenshot_path.endswith(".jpg")
    assert (tmp_path / cuts[1].audio_path).exists()
    # the failed cue left no half-written file behind
    failed = [call for call in calls if "00002" in call[-1]]
    assert failed and not Path(failed[0][-1]).exists()


def test_cut_cues_without_ffmpeg_takes_no_media(tmp_path, monkeypatch):
    monkeypatch.setattr(media, "ffmpeg_path", lambda: None)
    called = []

    cuts = media.cut_cues(
        Path("in.mp4"),
        [Cue(1000, 2000, "a")],
        tmp_path,
        runner=lambda args: called.append(args),
    )
    assert cuts == [None]
    assert called == []


def test_import_notes_when_ffmpeg_is_missing(client, db, monkeypatch):
    monkeypatch.setattr(media, "ffmpeg_available", lambda: False)
    source = _source(db)
    res = client.post(
        f"/api/sources/{source.id}/subtitles",
        files={"file": ("a.srt", SRT, "text/plain")},
        data={"video_path": "D:/anime/ep01.mkv"},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["media_note"] == "未找到 ffmpeg，本次只导入文本"
    assert body["media_cut"] == 0 and body["media_failed"] == 0

    lines = client.get(f"/api/lines?session_id={body['session_id']}").json()
    assert [line["text"] for line in lines] == ["こんにちは", "さようなら"]
    assert all(line["audio_path"] is None for line in lines)


def test_import_with_video_writes_audio_and_a_midpoint_still(client, db, tmp_path, monkeypatch):
    video = _video_in(tmp_path)
    client.put("/api/settings", json={"video_dirs": [str(video.parent)]})
    monkeypatch.setattr(media, "ffmpeg_path", lambda: "ffmpeg")
    calls: list[list[str]] = []
    monkeypatch.setattr(media, "run_ffmpeg", lambda args: calls.append(list(args)))
    source = _source(db)

    res = client.post(
        f"/api/sources/{source.id}/subtitles",
        files={"file": ("a.srt", SRT, "text/plain")},
        data={"video_path": str(video)},
    )
    assert res.status_code == 200
    body = res.json()
    assert (body["media_cut"], body["media_failed"], body["media_note"]) == (2, 0, None)

    audio_windows = {
        (call[call.index("-ss") + 1], call[call.index("-t") + 1])
        for call in calls
        if call[-1].endswith(".opus")
    }
    # cue 1: 1000-250 head .. 3000+500 tail; cue 2: 4000-250 .. 6500+500
    assert audio_windows == {("0.750", "2.750"), ("3.750", "3.250")}
    frame_starts = sorted(
        call[call.index("-ss") + 1] for call in calls if call[-1].endswith(".jpg")
    )
    assert frame_starts == ["2.000", "5.250"]  # midpoints, not cue starts

    lines = client.get(f"/api/lines?session_id={body['session_id']}").json()
    assert all(line["audio_path"] and line["screenshot_path"] for line in lines)


def test_import_rejects_a_video_outside_the_allowed_dirs(client, db, tmp_path, monkeypatch):
    video = _video_in(tmp_path)
    monkeypatch.setattr(media, "ffmpeg_path", lambda: "ffmpeg")
    source = _source(db)

    res = client.post(
        f"/api/sources/{source.id}/subtitles",
        files={"file": ("a.srt", SRT, "text/plain")},
        data={"video_path": str(video)},
    )
    assert res.status_code == 400
    assert res.json()["error"]["code"] == "video_not_allowed"


def _timed_source(db, spans: list[tuple[int, int]]) -> Source:
    source = Source(title="episode", kind="anime")
    db.add(source)
    db.commit()
    session = CaptureSession(source_id=source.id, mode="import")
    db.add(session)
    db.commit()
    for position, (start, end) in enumerate(spans, start=1):
        db.add(
            Line(
                source_id=source.id,
                session_id=session.id,
                text=f"line {position}",
                text_hash=f"hash-{position}",
                origin="subtitle",
                start_ms=start,
                end_ms=end,
                ord=position,
            )
        )
    # one line without a timeline: it must be skipped, not spoil the build
    db.add(
        Line(
            source_id=source.id,
            session_id=session.id,
            text="no timeline",
            text_hash="hash-none",
            origin="manual",
        )
    )
    db.commit()
    return source


def _wait_done(client, source_id: int, timeout: float = 10.0) -> dict:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        snapshot = client.get(f"/api/sources/{source_id}/condensed").json()
        if snapshot["state"] in ("done", "error"):
            return snapshot
        time.sleep(0.05)
    raise AssertionError("condensed job did not finish")


def test_merge_spans_joins_cues_closer_than_the_threshold():
    assert media.merge_spans([]) == []
    # 400ms apart: one segment, no click in the middle
    assert media.merge_spans([media.Span(0, 1000), media.Span(1400, 2000)]) == [media.Span(0, 2000)]
    # exactly at the threshold stays two segments (the gap means something)
    exact = [media.Span(0, 1000), media.Span(1500, 2000)]
    assert media.merge_spans(exact) == exact
    assert len(media.merge_spans([media.Span(0, 1000), media.Span(1600, 2000)])) == 2
    # overlaps merge and extend
    assert media.merge_spans([media.Span(0, 2000), media.Span(1500, 3000)]) == [media.Span(0, 3000)]
    # an episode of fragments becomes one segment
    fragments = [media.Span(i * 300, i * 300 + 250) for i in range(300)]
    assert len(media.merge_spans(fragments)) == 1


def test_condense_puts_silence_between_segments(tmp_path, monkeypatch):
    monkeypatch.setattr(media, "ffmpeg_path", lambda: "ffmpeg")
    lists: list[str] = []

    def runner(args) -> None:
        if "concat" in args:
            lists.append(Path(args[args.index("-i") + 1]).read_text(encoding="utf-8"))
        Path(args[-1]).write_bytes(b"x")

    spans = [media.Span(0, 3000), media.Span(4000, 6000)]  # gap 1000 > 500
    report = media.condense(Path("in.mp4"), spans, tmp_path, "condensed/1.opus", runner=runner)

    assert (report.segments, report.lines_used) == (2, 2)
    assert (tmp_path / "condensed/1.opus").exists()
    entries = lists[0].strip().splitlines()
    assert len(entries) == 3
    assert entries[0].endswith("part-00001.opus'")
    assert entries[1].endswith("silence.opus'")
    assert entries[2].endswith("part-00002.opus'")


def test_condense_without_ffmpeg_says_so(tmp_path, monkeypatch):
    monkeypatch.setattr(media, "ffmpeg_path", lambda: None)
    with pytest.raises(ApiError) as exc:
        media.condense(Path("in.mp4"), [media.Span(0, 1000)], tmp_path, "condensed/1.opus")
    assert exc.value.code == "ffmpeg_unavailable"


def test_condensed_job_builds_and_serves_the_track(client, db, tmp_path, monkeypatch):
    video = _video_in(tmp_path)
    client.put("/api/settings", json={"video_dirs": [str(video.parent)]})
    monkeypatch.setattr(media, "ffmpeg_path", lambda: "ffmpeg")
    monkeypatch.setattr(media, "run_ffmpeg", lambda args: Path(args[-1]).write_bytes(b"x"))
    monkeypatch.setattr(condensed, "condense_job", condensed.CondenseJob())
    source = _timed_source(db, [(0, 3000), (3400, 6000)])

    res = client.post(
        f"/api/sources/{source.id}/condensed",
        json={"video_path": str(video), "gap_ms": 500, "silence_ms": 200},
    )
    assert res.status_code == 202
    snapshot = _wait_done(client, source.id)
    assert snapshot["state"] == "done", snapshot
    assert snapshot["lines_used"] == 2  # the untimed line was skipped
    assert snapshot["segments"] == 1  # 400ms gap merged
    assert snapshot["output"] == f"condensed/{source.id}.opus"
    assert client.get(f"/media/{snapshot['output']}").status_code == 200


def test_condensed_job_reports_a_source_without_a_timeline(client, db, tmp_path, monkeypatch):
    video = _video_in(tmp_path)
    client.put("/api/settings", json={"video_dirs": [str(video.parent)]})
    monkeypatch.setattr(media, "ffmpeg_path", lambda: "ffmpeg")
    monkeypatch.setattr(condensed, "condense_job", condensed.CondenseJob())
    source = _source(db)

    res = client.post(f"/api/sources/{source.id}/condensed", json={"video_path": str(video)})
    assert res.status_code == 202
    snapshot = _wait_done(client, source.id)
    assert snapshot["state"] == "error"
    assert "时间轴" in snapshot["message"]


def test_condensed_needs_ffmpeg(client, db, monkeypatch):
    source = _source(db)
    monkeypatch.setattr(media, "ffmpeg_available", lambda: False)
    res = client.post(f"/api/sources/{source.id}/condensed", json={"video_path": "D:/a.mp4"})
    assert res.status_code == 503
    assert res.json()["error"]["code"] == "ffmpeg_unavailable"
