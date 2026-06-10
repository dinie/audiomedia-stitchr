"""Dashboard: the current user's projects."""

from __future__ import annotations

import reflex as rx

from ..components.auth import require_login
from ..components.navbar import layout
from ..schemas import ProjectVM
from ..state.projects_state import ProjectsState

def _delete_dialog(p: ProjectVM) -> rx.Component:
    """Confirm-and-delete dialog, shown for errored runs."""
    return rx.alert_dialog.root(
        rx.alert_dialog.trigger(
            rx.button(
                rx.icon("trash-2", size=14),
                "Delete",
                color_scheme="red",
                variant="soft",
                size="1",
            ),
        ),
        rx.alert_dialog.content(
            rx.alert_dialog.title("Delete this run?"),
            rx.alert_dialog.description(
                "This permanently removes the run, its segments, and any files."
            ),
            rx.hstack(
                rx.alert_dialog.cancel(rx.button("Cancel", variant="soft")),
                rx.alert_dialog.action(
                    rx.button(
                        "Delete",
                        color_scheme="red",
                        on_click=ProjectsState.delete_project(p.id),
                    ),
                ),
                spacing="3",
                justify="end",
                margin_top="1rem",
            ),
        ),
    )


def _project_row(p: ProjectVM) -> rx.Component:
    return rx.card(
        rx.hstack(
            rx.icon("file-audio", size=20),
            rx.vstack(
                rx.link(
                    rx.text(p.filename, weight="bold"),
                    href=f"/project/{p.id}",
                    underline="none",
                    color="inherit",
                ),
                rx.text(
                    f"Media: {p.media_type} · {p.created_at}",
                    size="1",
                    color_scheme="gray",
                ),
                spacing="1",
                align="start",
            ),
            rx.spacer(),
            rx.badge(
                p.status,
                variant="soft",
                color_scheme=rx.cond(p.status == "error", "red",
                                     rx.cond(p.status == "complete", "green", "gray")),
            ),
            rx.cond(p.status == "error", _delete_dialog(p)),
            align="center",
            width="100%",
            spacing="3",
        ),
        width="100%",
    )


@require_login
def index() -> rx.Component:
    return layout(
        rx.vstack(
            rx.hstack(
                rx.heading("Your projects", size="7"),
                rx.spacer(),
                rx.link(rx.button("New upload", size="3"), href="/upload"),
                align="center",
                width="100%",
            ),
            rx.cond(
                ProjectsState.projects.length() > 0,
                rx.vstack(
                    rx.foreach(ProjectsState.projects, _project_row),
                    spacing="3",
                    width="100%",
                ),
                rx.callout(
                    "No projects yet — upload an audio file to get started.",
                    icon="info",
                ),
            ),
            spacing="5",
            width="100%",
        )
    )
