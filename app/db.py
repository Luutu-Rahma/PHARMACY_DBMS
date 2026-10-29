"""PostgreSQL connection for Tkinter; reads DATABASE_URL from the project .env."""

import os
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urlsplit, urlunsplit

import psycopg
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")


def _database_url() -> str:
    url = os.getenv("DATABASE_URL", "")
    if not url:
        raise RuntimeError("DATABASE_URL is not set. Configure the project .env file first.")
    parts = urlsplit(url)
    if parts.scheme not in {"postgres", "postgresql"}:
        raise RuntimeError("DATABASE_URL must be a PostgreSQL connection URL.")
    query = parse_qs(parts.query, keep_blank_values=True)
    if "sslmode" not in query:
        query["sslmode"] = ["prefer" if parts.hostname in {"localhost", "127.0.0.1"} else "require"]
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query, doseq=True), parts.fragment))


def connect() -> psycopg.Connection:
    """Return a new PostgreSQL connection; caller is responsible for closing it."""
    return psycopg.connect(_database_url(), connect_timeout=10)
