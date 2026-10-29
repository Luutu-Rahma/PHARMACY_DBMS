"""Root-level PostgreSQL helper used by test_connection.py."""

import os
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urlsplit, urlunsplit

import psycopg
from dotenv import load_dotenv
from psycopg.rows import dict_row

load_dotenv(Path(__file__).resolve().parent / ".env")

def get_connection():
    """Establishes a Supabase/PostgreSQL connection from DATABASE_URL."""
    url = os.getenv("DATABASE_URL", "")
    if not url:
        raise RuntimeError("DATABASE_URL is not configured in .env")
    parts = urlsplit(url)
    if parts.scheme not in {"postgres", "postgresql"}:
        raise RuntimeError("DATABASE_URL must use PostgreSQL")
    query = parse_qs(parts.query, keep_blank_values=True)
    if "sslmode" not in query:
        query["sslmode"] = ["prefer" if parts.hostname in {"localhost", "127.0.0.1"} else "require"]
    safe_url = urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query, doseq=True), parts.fragment))
    return psycopg.connect(safe_url, connect_timeout=10, row_factory=dict_row)