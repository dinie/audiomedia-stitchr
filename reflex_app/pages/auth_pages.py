"""Custom login page (username/password + Google) and the OAuth completion page."""

from __future__ import annotations

import reflex as rx
import reflex_local_auth
from reflex_local_auth.pages.login import login_form

from .. import config


def login_page() -> rx.Component:
    """Login with the reflex-local-auth form plus a 'Sign in with Google' button."""
    google_button = rx.link(
        rx.button(
            rx.icon("log-in", size=16),
            "Sign in with Google",
            width="100%",
            variant="surface",
            size="3",
        ),
        href=f"{config.BACKEND_URL}/auth/google/login",
        width="100%",
    )

    return rx.center(
        rx.cond(
            reflex_local_auth.LoginState.is_hydrated,
            rx.card(
                rx.vstack(
                    login_form(),
                    rx.hstack(
                        rx.divider(),
                        rx.text("or", color_scheme="gray", size="1"),
                        rx.divider(),
                        align="center",
                        width="100%",
                    ),
                    google_button,
                    spacing="4",
                    width="100%",
                ),
            ),
        ),
        padding_top="10vh",
    )


def auth_complete_page() -> rx.Component:
    """Shown briefly while we store the Google session token and redirect home."""
    return rx.center(
        rx.vstack(
            rx.spinner(size="3"),
            rx.text("Signing you in…", color_scheme="gray"),
            spacing="3",
            align="center",
        ),
        width="100%",
        min_height="100vh",
    )
