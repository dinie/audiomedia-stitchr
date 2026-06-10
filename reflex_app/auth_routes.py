"""Backend (Starlette) routes for Google OAuth, registered on app._api.

Flow: /auth/google/login -> Google consent -> /auth/google/callback. The
callback finds/creates a LocalUser, mints a LocalAuthSession token, and
redirects to the frontend /auth/complete/<token> page, which stores the token
in LocalStorage so reflex_local_auth recognizes the session.
"""

from __future__ import annotations

import datetime
import secrets

import reflex as rx
from reflex_local_auth.auth_session import LocalAuthSession
from reflex_local_auth.user import LocalUser
from sqlmodel import select
from starlette.requests import Request
from starlette.responses import RedirectResponse

from . import config
from .services import google_oauth

_SESSION_DAYS = 7


def _fail(reason: str) -> RedirectResponse:
    return RedirectResponse(f"{config.FRONTEND_URL}/login?error={reason}")


async def google_login(request: Request) -> RedirectResponse:
    if not config.google_enabled():
        return _fail("google_not_configured")
    state = secrets.token_urlsafe(16)
    return RedirectResponse(google_oauth.authorize_url(state))


async def google_callback(request: Request) -> RedirectResponse:
    if not config.google_enabled():
        return _fail("google_not_configured")
    code = request.query_params.get("code")
    if not code:
        return _fail("google_denied")

    try:
        info = google_oauth.exchange_code_for_userinfo(code)
    except Exception:  # noqa: BLE001
        return _fail("google_failed")

    email = (info or {}).get("email")
    if not email:
        return _fail("google_no_email")

    with rx.session() as session:
        user = session.exec(
            select(LocalUser).where(LocalUser.username == email)
        ).one_or_none()
        if user is None:
            user = LocalUser()  # type: ignore[call-arg]
            user.username = email
            # Random unusable password — this account signs in via Google only.
            user.password_hash = LocalUser.hash_password(secrets.token_urlsafe(32))
            user.enabled = True
            session.add(user)
            session.commit()
            session.refresh(user)
        user_id = user.id

        token = secrets.token_urlsafe(32)
        session.add(
            LocalAuthSession(  # type: ignore[call-arg]
                user_id=user_id,
                session_id=token,
                expiration=datetime.datetime.now(datetime.timezone.utc)
                + datetime.timedelta(days=_SESSION_DAYS),
            )
        )
        session.commit()

    return RedirectResponse(f"{config.FRONTEND_URL}/auth/complete/{token}")


def register(app: rx.App) -> None:
    """Attach the OAuth routes to the Reflex backend (Starlette)."""
    app._api.add_route("/auth/google/login", google_login, methods=["GET"])
    app._api.add_route("/auth/google/callback", google_callback, methods=["GET"])
