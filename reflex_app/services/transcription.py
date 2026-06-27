"""Local speech-to-text via faster-whisper.

Pure module — no Reflex imports. The model is heavy and CPU/GPU bound, so the
pipeline calls these functions through `reflex.utils.misc.run_in_thread` to
avoid blocking the websocket event loop.
"""

from __future__ import annotations

from dataclasses import dataclass

from .. import config

_model = None


def _get_model():
    """Lazily construct and cache the WhisperModel (downloaded on first use)."""
    global _model
    if _model is None:
        from faster_whisper import WhisperModel

        # int8 on CPU keeps memory/latency reasonable for a local dev app.
        _model = WhisperModel(
            config.WHISPER_MODEL_SIZE, device="cpu", compute_type="int8"
        )
    return _model


def unload_model() -> None:
    """Drop the cached model to reclaim its memory (e.g. before video compose).

    The next transcription lazily reloads it (one-time cost).
    """
    global _model
    _model = None
    import gc

    gc.collect()


@dataclass
class RawSegment:
    start: float
    end: float
    text: str


def transcribe(path: str) -> list[RawSegment]:
    """Transcribe an audio file into timestamped segments."""
    model = _get_model()
    segments, _info = model.transcribe(path, vad_filter=True)
    return [
        RawSegment(start=float(s.start), end=float(s.end), text=s.text.strip())
        for s in segments
        if s.text and s.text.strip()
    ]


@dataclass
class Window:
    index: int
    start: float
    end: float
    text: str


def bucket_into_windows(
    segments: list[RawSegment], window_seconds: int
) -> list[Window]:
    """Group raw whisper segments into fixed-width time windows.

    A segment is assigned to a window by its start time; window text is the
    concatenation of the segments that fall in it. Empty windows are dropped.
    """
    if not segments:
        return []

    total_end = max(s.end for s in segments)
    buckets: dict[int, list[RawSegment]] = {}
    for seg in segments:
        idx = int(seg.start // window_seconds)
        buckets.setdefault(idx, []).append(seg)

    windows: list[Window] = []
    out_index = 0
    n_buckets = int(total_end // window_seconds) + 1
    for b in range(n_buckets):
        segs = buckets.get(b)
        if not segs:
            continue
        text = " ".join(s.text for s in segs).strip()
        if not text:
            continue
        windows.append(
            Window(
                index=out_index,
                start=float(b * window_seconds),
                end=float(min((b + 1) * window_seconds, total_end)),
                text=text,
            )
        )
        out_index += 1
    return windows
