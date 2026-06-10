"""Audio → LLM → semantic media search → final video app.

Pipeline: upload/record audio → transcribe (faster-whisper) → Claude derives one
visual search query per N-second window → fetch stock media (Pexels/Pixabay) →
compose a final video synced to the original audio.
"""

import reflex as rx
import reflex_local_auth

from . import auth_routes, models  # noqa: F401  (models registers tables)
from .pages.auth_pages import auth_complete_page, login_page
from .pages.index import index
from .pages.project import project_page
from .pages.upload import upload_page
from .state.auth_state import AuthCompleteState
from .state.pipeline_state import PipelineState
from .state.projects_state import ProjectsState

app = rx.App()

# Application pages (all gated by our require_login wrapper in components/auth.py).
app.add_page(index, route="/", title="Dashboard", on_load=ProjectsState.load_projects)
app.add_page(upload_page, route="/upload", title="New Upload")
app.add_page(
    project_page,
    route="/project/[project_id]",
    title="Project",
    on_load=PipelineState.load_project,
)

# Authentication: custom login (username/password + Google), package register,
# and the Google OAuth completion bridge.
app.add_page(
    login_page,
    route=reflex_local_auth.routes.LOGIN_ROUTE,
    title="Login",
)
app.add_page(
    reflex_local_auth.pages.register_page,
    route=reflex_local_auth.routes.REGISTER_ROUTE,
    title="Register",
)
app.add_page(
    auth_complete_page,
    route="/auth/complete/[token]",
    title="Signing in…",
    on_load=AuthCompleteState.complete,
)

# Backend (Starlette) routes for the Google OAuth flow.
auth_routes.register(app)
