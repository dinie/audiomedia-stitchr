"""Upload/record page: choose audio (file or mic), media type, segment length."""

from __future__ import annotations

import reflex as rx

from .. import config
from ..components.auth import require_login
from ..components.navbar import layout
from ..state.projects_state import ProjectsState

_UPLOAD_ID = "audio_upload"


def _shared_controls() -> rx.Component:
    return rx.vstack(
        rx.text("Media to fetch per segment", weight="bold"),
        rx.radio(
            config.MEDIA_TYPES,
            value=ProjectsState.media_type,
            on_change=ProjectsState.set_media_type,
            direction="row",
            spacing="4",
        ),
        rx.text(
            "Segment length: ",
            ProjectsState.segment_seconds.to_string(),
            " seconds",
            weight="bold",
        ),
        rx.slider(
            default_value=[config.DEFAULT_SEGMENT_SECONDS],
            min=config.MIN_SEGMENT_SECONDS,
            max=config.MAX_SEGMENT_SECONDS,
            step=5,
            on_change=ProjectsState.set_segment_seconds,
            width="100%",
        ),
        spacing="3",
        width="100%",
    )


def _upload_section() -> rx.Component:
    return rx.vstack(
        rx.upload(
            rx.vstack(
                rx.icon("upload", size=24),
                rx.text("Drag & drop or click to select an audio file"),
                align="center",
                spacing="2",
            ),
            id=_UPLOAD_ID,
            accept={"audio/*": config.AUDIO_EXTENSIONS},
            max_files=1,
            border="1px dashed var(--gray-6)",
            border_radius="8px",
            padding="1.5rem",
            width="100%",
        ),
        rx.hstack(
            rx.foreach(rx.selected_files(_UPLOAD_ID), rx.badge),
            spacing="2",
        ),
        rx.button(
            "Transcribe & find media",
            on_click=ProjectsState.handle_upload(rx.upload_files(_UPLOAD_ID)),
            loading=ProjectsState.uploading,
            size="3",
        ),
        spacing="3",
        width="100%",
    )


def _record_section() -> rx.Component:
    return rx.vstack(
        rx.hstack(
            rx.cond(
                ProjectsState.recording,
                rx.button(
                    rx.icon("square", size=16),
                    "Stop recording",
                    color_scheme="red",
                    on_click=ProjectsState.stop_recording,
                    size="3",
                ),
                rx.button(
                    rx.icon("mic", size=16),
                    "Start recording",
                    on_click=ProjectsState.start_recording,
                    size="3",
                ),
            ),
            rx.cond(
                ProjectsState.recording,
                rx.hstack(
                    rx.spinner(),
                    rx.text("Recording…", color_scheme="red"),
                    align="center",
                    spacing="2",
                ),
            ),
            align="center",
            spacing="3",
        ),
        # Preview + submit / re-record once we have a recording.
        rx.cond(
            ProjectsState.recorded_data != "",
            rx.vstack(
                rx.el.audio(
                    src=ProjectsState.recorded_data,
                    controls=True,
                    style={"width": "100%"},
                ),
                rx.hstack(
                    rx.button(
                        "Submit recording",
                        on_click=ProjectsState.submit_recording,
                        size="3",
                    ),
                    rx.button(
                        rx.icon("rotate-ccw", size=16),
                        "Re-record",
                        variant="soft",
                        on_click=ProjectsState.start_recording,
                        size="3",
                    ),
                    spacing="3",
                ),
                spacing="2",
                width="100%",
            ),
        ),
        spacing="3",
        width="100%",
    )


@require_login
def upload_page() -> rx.Component:
    return layout(
        rx.vstack(
            rx.heading("New audio project", size="7"),
            rx.text(
                "Upload or record audio. We transcribe it, use Claude to derive a "
                "visual search query per segment, fetch matching stock media, then "
                "stitch it into a final video synced to your audio.",
                color_scheme="gray",
            ),
            _shared_controls(),
            rx.divider(),
            rx.text("Upload a file", weight="bold", size="3"),
            _upload_section(),
            rx.divider(),
            rx.text("…or record audio", weight="bold", size="3"),
            _record_section(),
            rx.cond(
                ProjectsState.upload_error != "",
                rx.callout(
                    ProjectsState.upload_error,
                    icon="triangle_alert",
                    color_scheme="red",
                ),
            ),
            spacing="4",
            width="100%",
        )
    )
