"""Environment-based configuration for local development and Supabase."""

from __future__ import annotations

import os
import secrets
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")

DATABASE_URL = os.getenv("DATABASE_URL", "")
_configured_session_secret = os.getenv("SESSION_SECRET")
if os.getenv("APP_ENV", "development").lower() == "production" and not _configured_session_secret:
    raise RuntimeError("SESSION_SECRET must be configured in production.")
# The local-only fallback invalidates sessions whenever the server restarts.
SESSION_SECRET = _configured_session_secret or secrets.token_urlsafe(48)
COOKIE_SECURE = os.getenv("COOKIE_SECURE", "false").lower() in {"1", "true", "yes"}
