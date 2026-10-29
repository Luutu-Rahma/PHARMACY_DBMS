"""Explicit PostgreSQL schema initializer. Never imported by the web server."""

from pathlib import Path

from psycopg import ClientCursor

from web.db import connect

SCHEMA_DIR = Path(__file__).resolve().parents[1] / "sql" / "postgres"


def main() -> None:
    scripts = [SCHEMA_DIR / "01_schema.sql", SCHEMA_DIR / "02_functions_triggers.sql"]
    with connect() as connection:
        for path in scripts:
            ClientCursor(connection).execute(path.read_text(encoding="utf-8"))
    print("PostgreSQL schema and triggers initialized (no reset or seed was performed).")


if __name__ == "__main__":
    main()
