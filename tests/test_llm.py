"""Tests for the LLM service guard rails (no network)."""

import pytest

from reflex_app.services import llm


def test_empty_windows_returns_empty():
    assert llm.segment_queries([]) == {}


def test_missing_api_key_raises(monkeypatch):
    monkeypatch.setattr(llm.config, "anthropic_api_key", lambda: None)
    with pytest.raises(llm.LLMConfigError):
        llm.segment_queries([{"index": 0, "text": "hello"}])
