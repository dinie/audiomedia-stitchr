"""Rich pipeline progress: a stage stepper + live detail line + progress bar."""

from __future__ import annotations

import reflex as rx

from ..state.pipeline_state import PipelineState

# (ordinal, label, lucide icon for the pending/idle state)
_STEPS = [
    (1, "Transcribe", "audio-lines"),
    (2, "Analyze", "sparkles"),
    (3, "Search media", "images"),
    (4, "Compose video", "clapperboard"),
    (5, "Complete", "circle-check"),
]


def _step(num: int, label: str, icon: str) -> rx.Component:
    done = PipelineState.status_index > num
    active = PipelineState.status_index == num
    return rx.hstack(
        rx.cond(
            done,
            rx.icon("circle-check", size=20, color=rx.color("grass", 9)),
            rx.cond(
                active,
                rx.spinner(size="3"),
                rx.icon(icon, size=20, color=rx.color("gray", 7)),
            ),
        ),
        rx.text(
            label,
            size="2",
            weight=rx.cond(active, "bold", "regular"),
            color=rx.cond(done | active, rx.color("gray", 12), rx.color("gray", 9)),
        ),
        align="center",
        spacing="2",
    )


def pipeline_status() -> rx.Component:
    """Shown while a run is in progress or complete (hidden on error)."""
    return rx.cond(
        PipelineState.in_pipeline,
        rx.card(
            rx.vstack(
                rx.hstack(
                    *[_step(n, label, icon) for (n, label, icon) in _STEPS],
                    spacing="5",
                    wrap="wrap",
                    align="center",
                ),
                rx.cond(
                    PipelineState.detail != "",
                    rx.text(PipelineState.detail, size="2", color_scheme="gray"),
                ),
                rx.progress(value=PipelineState.progress, max=100, width="100%"),
                spacing="3",
                width="100%",
            ),
            width="100%",
        ),
    )
