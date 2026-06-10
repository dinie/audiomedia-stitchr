"""Tests for the video-compose timeline math (pure, no moviepy/network)."""

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
