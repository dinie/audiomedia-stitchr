"""Typed view-models for state vars.

Reflex needs typed vars to render `rx.foreach` / `.length()` over nested data,
so we expose DB rows to the UI as these dataclasses rather than dicts.
"""

from __future__ import annotations

import dataclasses


@dataclasses.dataclass
class MediaVM:
    url: str = ""
    thumbnail_url: str = ""
    source: str = ""
    attribution: str = ""


@dataclasses.dataclass
class SegmentVM:
    id: int = 0
    index: int = 0
    time_label: str = ""
    text: str = ""
    search_query: str = ""
    images: list[MediaVM] = dataclasses.field(default_factory=list)
    videos: list[MediaVM] = dataclasses.field(default_factory=list)


@dataclasses.dataclass
class ProjectVM:
    id: int = 0
    filename: str = ""
    media_type: str = ""
    segment_seconds: int = 0
    status: str = ""
    created_at: str = ""
