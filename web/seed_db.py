"""Explicit demo seed loader. Requires an empty PostgreSQL schema."""

from pathlib import Path

from psycopg import ClientCursor

from web.db import connect

SEED_FILE = Path(__file__).resolve().parents[1] / "sql" / "postgres" / "03_seed.sql"


def main() -> None:
    print("This loads demo pharmacy data and must only be used with a fresh development database.")
    with connect() as connection:
        ClientCursor(connection).execute(SEED_FILE.read_text(encoding="utf-8"))
    print("Demo records loaded. Seed accounts begin with legacy SHA-256 digests and migrate to Argon2 after first successful login.")


if __name__ == "__main__":
    main()
