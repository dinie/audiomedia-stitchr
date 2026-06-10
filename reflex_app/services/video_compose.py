"""Compose a final MP4 from per-segment media + the original audio.

Pure module (no Reflex/DB). The pipeline gathers segment media from the DB and
calls `compose(...)`; this downloads the media, lays each segment's items across
its time window on a 1280x720 timeline, and muxes the original audio as the
soundtrack. moviepy is blocking, so the pipeline runs this via run_in_thread.
"""

from __future__ import annotations

import os
import tempfile
from dataclasses import dataclass, field

import httpx

CANVAS_W, CANVAS_H = 1280, 720
FPS = 24
MAX_ITEMS_PER_SEGMENT = 4  # bound render cost
MIN_SLOT = 0.4  # seconds


@dataclass
class MediaItem:
    kind: str  # "image" | "video"
    url: str


@dataclass
class SegmentMedia:
    start: float
    media: list[MediaItem] = field(default_factory=list)


def display_windows(starts: list[float], total: float) -> list[tuple[float, float]]:
    """Tile [0, total] across segments by start time.

    Each segment runs from its own start (the first from 0) to the next
    segment's start; the last runs to `total`. Every window is at least
    MIN_SLOT long. Pure function — unit tested.
    """
    n = len(starts)
    windows: list[tuple[float, float]] = []
    for i in range(n):
        d_start = 0.0 if i == 0 else starts[i]
        d_end = starts[i + 1] if i + 1 < n else total
        d_end = max(d_end, d_start + MIN_SLOT)
        windows.append((d_start, d_end))
    return windows


def _download(client: httpx.Client, url: str, dest_dir: str, idx: int, kind: str) -> str | None:
    try:
        suffix = ".mp4" if kind == "video" else ".jpg"
        path = os.path.join(dest_dir, f"{idx}{suffix}")
        with client.stream("GET", url, follow_redirects=True) as r:
            r.raise_for_status()
            with open(path, "wb") as f:
                for chunk in r.iter_bytes(65536):
                    f.write(chunk)
        return path if os.path.getsize(path) > 0 else None
    except (httpx.HTTPError, OSError):
        return None


def _fit(clip):
    """Scale a clip to fit within the canvas and letterbox it on black."""
    from moviepy import ColorClip, CompositeVideoClip

    scale = min(CANVAS_W / clip.w, CANVAS_H / clip.h)
    clip = clip.resized(scale)
    bg = ColorClip((CANVAS_W, CANVAS_H), color=(0, 0, 0), duration=clip.duration)
    return CompositeVideoClip(
        [bg, clip.with_position("center")], size=(CANVAS_W, CANVAS_H)
    ).with_duration(clip.duration)


def _clip_for_item(path: str, kind: str, slot: float):
    """Build a fixed-`slot`-second, canvas-sized clip for one media item."""
    from moviepy import ImageClip, VideoFileClip, vfx

    if kind == "video":
        v = VideoFileClip(path, audio=False)
        if v.duration and v.duration >= slot:
            v = v.subclipped(0, slot)
        else:
            # Loop short clips to fill the slot.
            v = v.with_effects([vfx.Loop(duration=slot)])
        return _fit(v)
    # image
    return _fit(ImageClip(path).with_duration(slot))


def compose(
    audio_path: str,
    segments: list[SegmentMedia],
    out_path: str,
    audio_duration: float | None = None,
) -> str:
    """Render the final video to out_path and return it.

    Each segment occupies the timeline from its own start to the next segment's
    start (the last one runs to the end of the audio), so the visuals span the
    full soundtrack with no gaps.
    """
    from moviepy import (
        AudioFileClip,
        ColorClip,
        concatenate_videoclips,
    )

    audio = AudioFileClip(audio_path)
    total = float(audio_duration or audio.duration)

    segments = sorted(segments, key=lambda s: s.start)
    work_dir = tempfile.mkdtemp(prefix="compose_")
    clips = []

    try:
        windows = display_windows([s.start for s in segments], total)
        with httpx.Client(timeout=httpx.Timeout(60.0)) as client:
            for i, seg in enumerate(segments):
                d_start, d_end = windows[i]
                duration = d_end - d_start

                items = seg.media[:MAX_ITEMS_PER_SEGMENT]
                built = []
                if items:
                    slot = max(MIN_SLOT, duration / len(items))
                    for j, item in enumerate(items):
                        local = _download(
                            client, item.url, work_dir, i * 100 + j, item.kind
                        )
                        if not local:
                            continue
                        try:
                            built.append(_clip_for_item(local, item.kind, slot))
                        except Exception:
                            # Skip any single item that fails to decode.
                            continue

                if built:
                    clips.extend(built)
                else:
                    # No usable media for this window -> black.
                    clips.append(
                        ColorClip(
                            (CANVAS_W, CANVAS_H), color=(0, 0, 0), duration=duration
                        )
                    )

        if not clips:
            clips = [ColorClip((CANVAS_W, CANVAS_H), color=(0, 0, 0), duration=total)]

        try:
            video = concatenate_videoclips(clips, method="chain")
        except Exception:
            video = concatenate_videoclips(clips, method="compose")

        video = video.with_audio(audio)
        video.write_videofile(
            out_path,
            fps=FPS,
            codec="libx264",
            audio_codec="aac",
            threads=4,
            logger=None,
        )
        return out_path
    finally:
        for c in clips:
            try:
                c.close()
            except Exception:
                pass
        try:
            audio.close()
        except Exception:
            pass
