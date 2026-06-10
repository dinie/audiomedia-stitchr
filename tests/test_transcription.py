"""Tests for transcript windowing (pure, no model needed)."""

from reflex_app.services.transcription import RawSegment, bucket_into_windows


def _seg(start, end, text):
    return RawSegment(start=start, end=end, text=text)


def test_empty_input():
    assert bucket_into_windows([], 15) == []


def test_groups_into_windows():
    raw = [
        _seg(0.0, 4.0, "Hello there"),
        _seg(4.0, 9.0, "welcome to the show"),
        _seg(16.0, 20.0, "second window"),
    ]
    windows = bucket_into_windows(raw, window_seconds=15)
    assert len(windows) == 2
    assert [w.index for w in windows] == [0, 1]
    assert "Hello there welcome to the show" == windows[0].text
    assert windows[1].text == "second window"
    assert windows[0].start == 0.0 and windows[0].end == 15.0
    assert windows[1].start == 15.0


def test_window_indices_are_contiguous_when_buckets_skipped():
    # Nothing in the 15-30s bucket; output indices must stay contiguous.
    raw = [_seg(0.0, 2.0, "a"), _seg(31.0, 33.0, "b")]
    windows = bucket_into_windows(raw, 15)
    assert [w.index for w in windows] == [0, 1]
    assert windows[1].text == "b"


def test_blank_segments_dropped():
    raw = [_seg(0.0, 2.0, "   "), _seg(3.0, 4.0, "real")]
    windows = bucket_into_windows(raw, 15)
    assert len(windows) == 1
    assert windows[0].text == "real"
