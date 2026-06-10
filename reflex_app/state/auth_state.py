"""State that finalizes a Google sign-in on the frontend.

The OAuth callback redirects to /auth/complete/[token]; this reads the token
(a LocalAuthSession id minted server-side) and writes it into the LocalStorage
auth_token so reflex_local_auth treats the user as authenticated.
"""

from __future__ import annotations

import reflex as rx
import reflex_local_auth


class AuthCompleteState(reflex_local_auth.LocalAuthState):
    @rx.event
    def complete(self):
        token = getattr(self, "token", "")
        if token:
            self.auth_token = token
        return rx.redirect("/")
