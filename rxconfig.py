import os

import reflex as rx
from dotenv import load_dotenv

# Load .env from the project root (if present) before anything reads os.environ.
# Reflex does not auto-load .env, so this is what makes ANTHROPIC_API_KEY,
# PEXELS_API_KEY, PIXABAY_API_KEY, HF_TOKEN, DATABASE_URL, etc. available to the
# app. override=False so real shell env vars still win.
load_dotenv(override=False)

# Persistence: SQLite for local dev, Postgres-ready for production.
# Set DATABASE_URL (e.g. postgresql://user:pass@host:5432/db) to override.
DB_URL = os.environ.get("DATABASE_URL", "sqlite:///reflex.db")

config = rx.Config(
    app_name="reflex_app",
    db_url=DB_URL,
    plugins=[
        rx.plugins.SitemapPlugin(),
        rx.plugins.TailwindV4Plugin(),
        rx.plugins.RadixThemesPlugin(),
    ],
)
