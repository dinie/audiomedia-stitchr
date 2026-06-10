"""Tests for pure helpers in the pipeline state module."""

from reflex_app.models import Status
from reflex_app.state.pipeline_state import _STATUS_ORDER, _time_label


def test_time_label_formats_mm_ss_range():
    assert _time_label(0, 65) == "00:00–01:05"
    assert _time_label(5.9, 10.2) == "00:05–00:10"


def test_status_order_is_monotonic_through_pipeline():
    order = [
        Status.UPLOADED,
        Status.TRANSCRIBING,
        Status.ANALYZING,
        Status.SEARCHING,
        Status.COMPOSING,
        Status.COMPLETE,
    ]
    values = [_STATUS_ORDER[s] for s in order]
    assert values == sorted(values)
    assert values == [0, 1, 2, 3, 4, 5]
