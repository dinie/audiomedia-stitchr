"""Minimal Google OAuth 2.0 (authorization code) helpers via httpx.

No extra dependency — just the standard authorize → token → userinfo flow.
"""

from __future__ import annotations

import urllib.parse

import httpx

from .. import config

_AUTH_ENDPOINT = "https://accounts.google.com/o/oauth2/v2/auth"
_TOKEN_ENDPOINT = "https://oauth2.googleapis.com/token"
_USERINFO_ENDPOINT = "https://openidconnect.googleapis.com/v1/userinfo"


def authorize_url(state: str) -> str:
    """Build the Google consent-screen URL to redirect the user to."""
    params = {
        "client_id": config.google_client_id() or "",
        "redirect_uri": config.GOOGLE_REDIRECT_URI,
        "response_type": "code",
        "scope": "openid email profile",
        "state": state,
        "access_type": "online",
        "prompt": "select_account",
    }
    return f"{_AUTH_ENDPOINT}?{urllib.parse.urlencode(params)}"


def exchange_code_for_userinfo(code: str) -> dict:
    """Exchange an auth code for tokens and return the user's profile info.

    Returns a dict with at least 'email' and 'sub' on success. Raises on failure.
    """
    with httpx.Client(timeout=httpx.Timeout(20.0)) as client:
        token_resp = client.post(
            _TOKEN_ENDPOINT,
            data={
                "code": code,
                "client_id": config.google_client_id() or "",
                "client_secret": config.google_client_secret() or "",
                "redirect_uri": config.GOOGLE_REDIRECT_URI,
                "grant_type": "authorization_code",
            },
        )
        token_resp.raise_for_status()
        access_token = token_resp.json()["access_token"]

        info_resp = client.get(
            _USERINFO_ENDPOINT,
            headers={"Authorization": f"Bearer {access_token}"},
        )
        info_resp.raise_for_status()
        return info_resp.json()
