"""Small per-operation PostgreSQL connection helper."""

from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator
from urllib.parse import parse_qs, urlencode, urlsplit, urlunsplit

import psycopg
from psycopg.rows import dict_row

from web.config import DATABASE_URL


def connection_url() -> str:
    if not DATABASE_URL:
        raise RuntimeError("DATABASE_URL is not configured. Copy .env.example to .env and set it.")
    parts = urlsplit(DATABASE_URL)
    if parts.scheme not in {"postgres", "postgresql"}:
        raise RuntimeError("DATABASE_URL must be a PostgreSQL connection URL.")
    query = parse_qs(parts.query, keep_blank_values=True)
    if "sslmode" not in query:
        query["sslmode"] = ["prefer" if parts.hostname in {"localhost", "127.0.0.1"} else "require"]
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query, doseq=True), parts.fragment))


@contextmanager
def connect() -> Iterator[psycopg.Connection]:
    """Yield a fresh connection, commit/rollback its transaction, and always close it."""
    connection = psycopg.connect(connection_url(), row_factory=dict_row, connect_timeout=10)
    try:
        with connection:
            yield connection
    finally:
        connection.close()
