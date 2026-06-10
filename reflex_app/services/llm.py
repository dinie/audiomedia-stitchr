"""Turn timestamped transcript windows into visual search queries using Claude.

Uses the official Anthropic SDK with adaptive thinking and structured outputs
so the response is a guaranteed-shape JSON object we can map back by index.
"""

from __future__ import annotations

import json

from .. import config


class LLMConfigError(RuntimeError):
    """Raised when the LLM is not configured (missing API key)."""


_SYSTEM = (
    "You convert a timestamped audio transcript into visual stock-media search "
    "queries. For each numbered window, output ONE concise query (3-6 keywords) "
    "describing concrete, visually depictable subjects, scenes, or objects that "
    "would illustrate what is being discussed. Avoid abstract words, speaker "
    "names, and filler. Return a query for every window index you are given."
)

_SCHEMA = {
    "type": "object",
    "properties": {
        "queries": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "index": {"type": "integer"},
                    "query": {"type": "string"},
                },
                "required": ["index", "query"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["queries"],
    "additionalProperties": False,
}


def segment_queries(windows: list[dict]) -> dict[int, str]:
    """Map each window index to a search query.

    Args:
        windows: list of {"index": int, "text": str}.

    Returns:
        dict of index -> query string.
    """
    if not windows:
        return {}

    api_key = config.anthropic_api_key()
    if not api_key:
        raise LLMConfigError(
            "ANTHROPIC_API_KEY is not set. Add it to your environment (.env)."
        )

    import anthropic

    client = anthropic.Anthropic(api_key=api_key)

    lines = "\n".join(f"[{w['index']}] {w['text']}" for w in windows)
    user_msg = (
        "Generate one visual search query per window below. "
        "Respond using the provided schema.\n\n" + lines
    )

    response = client.messages.create(
        model=config.ANTHROPIC_MODEL,
        max_tokens=4096,
        thinking={"type": "adaptive"},
        system=_SYSTEM,
        output_config={"format": {"type": "json_schema", "schema": _SCHEMA}},
        messages=[{"role": "user", "content": user_msg}],
    )

    text = next((b.text for b in response.content if b.type == "text"), "")
    data = json.loads(text)
    result: dict[int, str] = {}
    for item in data.get("queries", []):
        try:
            result[int(item["index"])] = str(item["query"]).strip()
        except (KeyError, ValueError, TypeError):
            continue
    return result
