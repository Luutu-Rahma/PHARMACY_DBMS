"""Aiven-only MySQL connection helpers. No local or alternate database fallback."""
from __future__ import annotations

import os
import ssl
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

import pymysql
from dotenv import load_dotenv

APP_DIR = Path(__file__).resolve().parent
# The repository's existing environment may hold the real Aiven URI. The new
# app-specific .env takes precedence when present; no config file is modified.
load_dotenv(APP_DIR.parent / ".env", override=False)
load_dotenv(APP_DIR / ".env", override=True)


class DatabaseConfigurationError(RuntimeError):
    """Raised when required remote MySQL configuration is missing or unsafe."""


class DatabaseUnavailable(RuntimeError):
    """A safe-to-display database connectivity error."""


@dataclass(frozen=True)
class MySQLSettings:
    host: str
    port: int
    user: str
    password: str
    database: str
    ca_file: Path


def settings_from_env() -> MySQLSettings:
    """Read the Aiven URI and mandatory CA file without exposing credentials."""
    uri = os.getenv("DATABASE_URL", "").strip()
    if not uri:
        raise DatabaseConfigurationError("DATABASE_URL is missing from Web UI/.env.")

    parsed = urlparse(uri)
    if parsed.scheme not in {"mysql", "mysql+pymysql"}:
        raise DatabaseConfigurationError("DATABASE_URL must use the MySQL scheme.")
    host = parsed.hostname or ""
    if not host.endswith(".aivencloud.com"):
        raise DatabaseConfigurationError("DATABASE_URL must target the configured Aiven MySQL host.")
    try:
        port = parsed.port
    except ValueError as exc:
        raise DatabaseConfigurationError("The MySQL port in DATABASE_URL is invalid.") from exc
    if not port or not parsed.username or parsed.password is None or not parsed.path.strip("/"):
        raise DatabaseConfigurationError("DATABASE_URL must include host, port, user, password, and database.")

    query = parse_qs(parsed.query)
    ssl_mode = query.get("ssl-mode", query.get("ssl_mode", [""]))[0].upper()
    if ssl_mode not in {"REQUIRED", "VERIFY_CA", "VERIFY_IDENTITY"}:
        raise DatabaseConfigurationError("Set ssl-mode=REQUIRED in DATABASE_URL; certificate checks remain mandatory.")

    ca_value = os.getenv("AIVEN_CA_CERT", "").strip()
    if not ca_value:
        raise DatabaseConfigurationError("AIVEN_CA_CERT must point to the CA certificate downloaded from Aiven.")
    ca_file = Path(ca_value).expanduser()
    if not ca_file.is_absolute():
        ca_file = APP_DIR / ca_file
    if not ca_file.is_file():
        raise DatabaseConfigurationError("The configured Aiven CA certificate file was not found.")

    return MySQLSettings(
        host=host,
        port=port,
        user=unquote(parsed.username),
        password=unquote(parsed.password),
        database=unquote(parsed.path.lstrip("/")),
        ca_file=ca_file,
    )


def _safe_connection_message(error: BaseException) -> str:
    """Map driver errors to useful messages without returning driver text/secrets."""
    code = error.args[0] if getattr(error, "args", ()) else None
    if code in {1044, 1045, 1698}:
        return "Aiven rejected the configured database account. Verify its username, password, and grants."
    if code == 1049:
        return "Aiven reached the server, but the configured database does not exist or is not accessible."
    if code in {2003, 2005, 2006, 2013}:
        return "Could not reach Aiven MySQL. Check the service status, hostname, port, firewall, and network access."
    if isinstance(error, (ssl.SSLError, OSError)):
        return "TLS verification or network connection failed. Check the Aiven CA certificate and network access."
    return "Aiven MySQL operation failed. Check the database configuration and service logs."


def connect():
    """Open a hostname-verified TLS connection to the configured Aiven database."""
    config = settings_from_env()
    try:
        tls = ssl.create_default_context(cafile=str(config.ca_file))
        tls.verify_mode = ssl.CERT_REQUIRED
        tls.check_hostname = True
        return pymysql.connect(
            host=config.host,
            port=config.port,
            user=config.user,
            password=config.password,
            database=config.database,
            charset="utf8mb4",
            cursorclass=pymysql.cursors.DictCursor,
            autocommit=False,
            connect_timeout=8,
            read_timeout=20,
            write_timeout=20,
            ssl=tls,
        )
    except (pymysql.MySQLError, OSError, ssl.SSLError) as exc:
        raise DatabaseUnavailable(_safe_connection_message(exc)) from None


def test_connection() -> dict[str, str]:
    """Verify TLS, server reachability, and selection of the configured database."""
    config = settings_from_env()
    connection = connect()
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1 AS ok, DATABASE() AS selected_database")
            row = cursor.fetchone()
        if row["ok"] != 1 or row["selected_database"] != config.database:
            raise DatabaseUnavailable("The server connected, but the configured database was not selected.")
        return {"host": config.host, "port": str(config.port), "database": config.database}
    finally:
        connection.close()
