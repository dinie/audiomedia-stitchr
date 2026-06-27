"""Tests for the video-compose timeline math (pure) + a render integration test."""

import subprocess

from reflex_app.services import video_compose as vc
from reflex_app.services.video_compose import MIN_SLOT, display_windows


def test_tiles_full_timeline_no_gaps():
    starts = [0.0, 5.0, 10.0]
    windows = display_windows(starts, total=16.0)
    assert windows[0] == (0.0, 5.0)
    assert windows[1] == (5.0, 10.0)
    assert windows[2] == (10.0, 16.0)
    # contiguous: each window starts where the previous ended
    for (_, end), (nxt_start, _) in zip(windows, windows[1:]):
        assert end == nxt_start


def test_first_window_starts_at_zero_even_with_leading_silence():
    windows = display_windows([3.0, 8.0], total=12.0)
    assert windows[0][0] == 0.0  # covers the 0-3s lead-in
    assert windows[-1][1] == 12.0  # last runs to the end of audio


def test_single_segment_spans_whole_audio():
    assert display_windows([0.0], total=16.0) == [(0.0, 16.0)]


def test_min_slot_enforced():
    # total shorter than the segment start -> clamp to a positive MIN_SLOT window
    windows = display_windows([0.0, 10.0], total=10.0)
    assert windows[-1][1] - windows[-1][0] >= MIN_SLOT


def _video_duration(path: str) -> float:
    from moviepy import VideoFileClip

    clip = VideoFileClip(path)
    try:
        return float(clip.duration)
    finally:
        clip.close()


def test_compose_renders_media_less_segments_end_to_end(tmp_path):
    """compose() renders → concats → muxes audio with no network/media.

    Segments with no media become black; this exercises the full
    per-segment-render → ffmpeg-concat → mux path. Needs the bundled ffmpeg.
    """
    ffmpeg = vc._ffmpeg()
    # 3s of silent audio.
    audio = tmp_path / "audio.m4a"
    subprocess.run(
        [ffmpeg, "-y", "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo",
         "-t", "3", "-c:a", "aac", str(audio)],
        check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )

    segments = [vc.SegmentMedia(start=0.0, media=[]),
                vc.SegmentMedia(start=1.5, media=[])]
    out = tmp_path / "out.mp4"
    result = vc.compose(str(audio), segments, str(out))

    assert result == str(out)
    assert out.exists() and out.stat().st_size > 0
    # Output spans ~the audio length (two windows: 0-1.5, 1.5-3.0).
    assert abs(_video_duration(str(out)) - 3.0) < 0.5
