"""Tests for media search normalization and graceful no-key behavior."""

import asyncio

from reflex_app.services import media_search


def test_norm_shape_and_thumbnail_fallback():
    n = media_search._norm(kind="image", url="http://x/a.jpg", source="pexels")
    assert n["kind"] == "image"
    assert n["url"] == "http://x/a.jpg"
    # thumbnail falls back to url when not provided
    assert n["thumbnail_url"] == "http://x/a.jpg"
    assert set(n) == {
        "kind", "url", "thumbnail_url", "source", "width", "height", "attribution"
    }


def test_norm_coerces_missing_dims():
    n = media_search._norm(kind="video", url="u")
    assert n["width"] == 0 and n["height"] == 0
    assert n["attribution"] == ""


def test_search_without_keys_returns_empty(monkeypatch):
    # No API keys configured -> all providers skipped, no exception.
    monkeypatch.setattr(media_search.config, "pexels_api_key", lambda: None)
    monkeypatch.setattr(media_search.config, "pixabay_api_key", lambda: None)
    out = asyncio.run(media_search.search("sunset", "both"))
    assert out == []
