from __future__ import annotations

from pathlib import Path

import pytest

from kotoba.core.errors import ApiError
from kotoba.models import Source
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
