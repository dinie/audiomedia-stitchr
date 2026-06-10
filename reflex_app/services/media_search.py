"""Semantic stock-media search via Pexels and Pixabay (free APIs).

All functions are async (httpx) and defensive: a failed query for one source
returns an empty list rather than raising, so one bad call never kills a run.
Results are normalized to the `MediaResult` field shape.
"""

from __future__ import annotations

import httpx

from .. import config

_TIMEOUT = httpx.Timeout(20.0)


def _norm(
    *,
    kind: str,
    url: str,
    thumbnail_url: str = "",
    source: str = "",
    width: int = 0,
    height: int = 0,
    attribution: str = "",
) -> dict:
    return {
        "kind": kind,
        "url": url,
        "thumbnail_url": thumbnail_url or url,
        "source": source,
        "width": int(width or 0),
        "height": int(height or 0),
        "attribution": attribution or "",
    }


async def _pexels_images(client: httpx.AsyncClient, query: str, limit: int) -> list[dict]:
    key = config.pexels_api_key()
    if not key:
        return []
    try:
        r = await client.get(
            "https://api.pexels.com/v1/search",
            params={"query": query, "per_page": max(1, limit)},
            headers={"Authorization": key},
        )
        r.raise_for_status()
        out = []
        for p in r.json().get("photos", []):
            src = p.get("src", {})
            out.append(
                _norm(
                    kind="image",
                    url=src.get("large") or src.get("original", ""),
                    thumbnail_url=src.get("tiny") or src.get("small", ""),
                    source="pexels",
                    width=p.get("width", 0),
                    height=p.get("height", 0),
                    attribution=p.get("photographer", ""),
                )
            )
        return out
    except (httpx.HTTPError, ValueError):
        return []


async def _pexels_videos(client: httpx.AsyncClient, query: str, limit: int) -> list[dict]:
    key = config.pexels_api_key()
    if not key:
        return []
    try:
        r = await client.get(
            "https://api.pexels.com/videos/search",
            params={"query": query, "per_page": max(1, limit)},
            headers={"Authorization": key},
        )
        r.raise_for_status()
        out = []
        for v in r.json().get("videos", []):
            files = v.get("video_files", [])
            # Prefer an SD/HD mp4 of moderate size.
            chosen = next(
                (f for f in files if f.get("quality") == "sd" and f.get("file_type") == "video/mp4"),
                files[0] if files else None,
            )
            if not chosen:
                continue
            out.append(
                _norm(
                    kind="video",
                    url=chosen.get("link", ""),
                    thumbnail_url=v.get("image", ""),
                    source="pexels",
                    width=chosen.get("width", 0),
                    height=chosen.get("height", 0),
                    attribution=(v.get("user", {}) or {}).get("name", ""),
                )
            )
        return out
    except (httpx.HTTPError, ValueError):
        return []


async def _pixabay_images(client: httpx.AsyncClient, query: str, limit: int) -> list[dict]:
    key = config.pixabay_api_key()
    if not key:
        return []
    try:
        r = await client.get(
            "https://pixabay.com/api/",
            params={"key": key, "q": query, "per_page": max(3, limit), "image_type": "photo"},
        )
        r.raise_for_status()
        out = []
        for h in r.json().get("hits", []):
            out.append(
                _norm(
                    kind="image",
                    url=h.get("webformatURL") or h.get("largeImageURL", ""),
                    thumbnail_url=h.get("previewURL", ""),
                    source="pixabay",
                    width=h.get("imageWidth", 0),
                    height=h.get("imageHeight", 0),
                    attribution=h.get("user", ""),
                )
            )
        return out
    except (httpx.HTTPError, ValueError):
        return []


async def _pixabay_videos(client: httpx.AsyncClient, query: str, limit: int) -> list[dict]:
    key = config.pixabay_api_key()
    if not key:
        return []
    try:
        r = await client.get(
            "https://pixabay.com/api/videos/",
            params={"key": key, "q": query, "per_page": max(3, limit)},
        )
        r.raise_for_status()
        out = []
        for h in r.json().get("hits", []):
            vids = h.get("videos", {})
            pick = vids.get("medium") or vids.get("small") or {}
            if not pick.get("url"):
                continue
            out.append(
                _norm(
                    kind="video",
                    url=pick.get("url", ""),
                    thumbnail_url=pick.get("thumbnail", ""),
                    source="pixabay",
                    width=pick.get("width", 0),
                    height=pick.get("height", 0),
                    attribution=h.get("user", ""),
                )
            )
        return out
    except (httpx.HTTPError, ValueError):
        return []


async def search(query: str, media_type: str, limit: int | None = None) -> list[dict]:
    """Search both providers for the given media_type and return up to `limit` per kind.

    media_type: "images" | "video" | "both".
    """
    limit = limit or config.MEDIA_PER_SEGMENT
    want_images = media_type in ("images", "both")
    want_video = media_type in ("video", "both")

    results: list[dict] = []
    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        if want_images:
            imgs = await _pexels_images(client, query, limit)
            if len(imgs) < limit:
                imgs += await _pixabay_images(client, query, limit)
            results += imgs[:limit]
        if want_video:
            vids = await _pexels_videos(client, query, limit)
            if len(vids) < limit:
                vids += await _pixabay_videos(client, query, limit)
            results += vids[:limit]
    return results
