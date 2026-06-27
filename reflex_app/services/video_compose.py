"""Compose a final MP4 from per-segment media + the original audio.

Pure module (no Reflex/DB). The pipeline gathers segment media from the DB and
calls `compose(...)`; this downloads the media, lays each segment's items across
its time window on a 1280x720 timeline, and muxes the original audio as the
soundtrack. moviepy is blocking, so the pipeline runs this via run_in_thread.

Memory profile: segments are rendered to temp files **one at a time** (only one
segment's clips are ever in memory), then joined with ffmpeg's concat demuxer and
muxed with the audio. Media is downscaled to the canvas at decode time. This keeps
peak memory bounded regardless of audio length (see the OOM fix).
"""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from dataclasses import dataclass, field

import httpx

CANVAS_W, CANVAS_H = 1280, 720
FPS = 24
MAX_ITEMS_PER_SEGMENT = 3  # bound render cost (no longer drives peak memory)
MIN_SLOT = 0.4  # seconds


@dataclass
class MediaItem:
    kind: str  # "image" | "video"
    url: str


@dataclass
class SegmentMedia:
    start: float
    media: list[MediaItem] = field(default_factory=list)


def _ffmpeg() -> str:
    import imageio_ffmpeg

    return imageio_ffmpeg.get_ffmpeg_exe()


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
    """Build a fixed-`slot`-second, canvas-sized clip for one media item.

    Media is downscaled to the canvas at decode time so we never hold a
    full-resolution (e.g. 1080p / megapixel) frame in memory.
    """
    from moviepy import ImageClip, VideoFileClip, vfx

    if kind == "video":
        # target_resolution decodes at ~720p height (keeps aspect) — big saving.
        v = VideoFileClip(path, audio=False, target_resolution=(CANVAS_H, None))
        if v.duration and v.duration >= slot:
            v = v.subclipped(0, slot)
        else:
            # Loop short clips to fill the slot.
            v = v.with_effects([vfx.Loop(duration=slot)])
        return _fit(v)

    # image: shrink with PIL before handing a numpy array to moviepy.
    import numpy as np
    from PIL import Image

    with Image.open(path) as im:
        im = im.convert("RGB")
        im.thumbnail((CANVAS_W, CANVAS_H))  # in-place, preserves aspect, <= canvas
        arr = np.asarray(im)
    return _fit(ImageClip(arr).with_duration(slot))


def _safe_close(obj) -> None:
    try:
        obj.close()
    except Exception:
        pass


def _write_clip(clip, path: str) -> None:
    """Write a silent, canvas-sized segment file with uniform params.

    Uniform codec/size/fps/pixfmt across segments is what makes the later
    concat-demuxer stream copy valid.
    """
    clip.write_videofile(
        path,
        fps=FPS,
        codec="libx264",
        audio=False,
        preset="medium",
        pixel_format="yuv420p",
        threads=2,
        logger=None,
    )


def _render_segment(
    client: httpx.Client, seg: SegmentMedia, window: tuple[float, float],
    work_dir: str, index: int,
) -> str:
    """Render one segment to its own temp mp4; close its clips immediately.

    Only this segment's clips are alive at a time → bounded peak memory.
    """
    from moviepy import ColorClip, concatenate_videoclips

    d_start, d_end = window
    duration = d_end - d_start
    seg_path = os.path.join(work_dir, f"seg_{index:04d}.mp4")

    built = []
    items = seg.media[:MAX_ITEMS_PER_SEGMENT]
    if items:
        slot = max(MIN_SLOT, duration / len(items))
        for j, item in enumerate(items):
            local = _download(client, item.url, work_dir, index * 100 + j, item.kind)
            if not local:
                continue
            try:
                built.append(_clip_for_item(local, item.kind, slot))
            except Exception:
                continue  # skip an item that fails to decode

    # Track extra clips to close explicitly — never use `in`/`==` on moviepy
    # clips (Clip.__eq__ does duration*fps and crashes when fps is None).
    extra = []  # concatenated and/or black clips we created here
    try:
        if len(built) > 1:
            clip = concatenate_videoclips(built, method="chain")
            extra.append(clip)
        elif len(built) == 1:
            clip = built[0]
        else:
            clip = ColorClip((CANVAS_W, CANVAS_H), color=(0, 0, 0), duration=duration)
            extra.append(clip)
        _write_clip(clip, seg_path)
    except Exception:
        # Any render failure → fall back to a black segment of the right length
        # so the concat stays uniform and the run still completes.
        black = ColorClip((CANVAS_W, CANVAS_H), color=(0, 0, 0), duration=duration)
        extra.append(black)
        _write_clip(black, seg_path)
    finally:
        for c in built:
            _safe_close(c)
        for c in extra:
            _safe_close(c)

    return seg_path


def _run_ffmpeg(args: list[str]) -> None:
    proc = subprocess.run(
        [_ffmpeg(), "-y", *args],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
    )
    if proc.returncode != 0:
        tail = (proc.stderr or b"").decode("utf-8", "replace")[-800:]
        raise RuntimeError(f"ffmpeg failed ({proc.returncode}): {tail}")


def _concat_and_mux(
    seg_paths: list[str], audio_path: str, out_path: str, work_dir: str
) -> None:
    """Join segment files (stream copy) and mux the original audio."""
    list_file = os.path.join(work_dir, "concat.txt")
    with open(list_file, "w") as f:
        for p in seg_paths:
            f.write(f"file '{os.path.abspath(p)}'\n")

    silent = os.path.join(work_dir, "silent.mp4")
    _run_ffmpeg(["-f", "concat", "-safe", "0", "-i", list_file, "-c", "copy", silent])
    _run_ffmpeg([
        "-i", silent, "-i", audio_path,
        "-map", "0:v:0", "-map", "1:a:0",
        "-c:v", "copy", "-c:a", "aac", "-shortest", out_path,
    ])


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
    from moviepy import AudioFileClip, ColorClip

    if audio_duration is not None:
        total = float(audio_duration)
    else:
        a = AudioFileClip(audio_path)
        try:
            total = float(a.duration)
        finally:
            _safe_close(a)

    segments = sorted(segments, key=lambda s: s.start)
    work_dir = tempfile.mkdtemp(prefix="compose_")

    try:
        if segments:
            windows = display_windows([s.start for s in segments], total)
            seg_paths = []
            with httpx.Client(timeout=httpx.Timeout(60.0)) as client:
                for i, seg in enumerate(segments):
                    seg_paths.append(_render_segment(client, seg, windows[i], work_dir, i))
        else:
            # No segments at all → a single black clip spanning the audio.
            seg_path = os.path.join(work_dir, "seg_0000.mp4")
            black = ColorClip((CANVAS_W, CANVAS_H), color=(0, 0, 0), duration=total)
            try:
                _write_clip(black, seg_path)
            finally:
                _safe_close(black)
            seg_paths = [seg_path]

        _concat_and_mux(seg_paths, audio_path, out_path, work_dir)
        return out_path
    finally:
        shutil.rmtree(work_dir, ignore_errors=True)
