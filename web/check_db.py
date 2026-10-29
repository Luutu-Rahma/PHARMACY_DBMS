"""Read-only connectivity/schema check for the configured PostgreSQL database."""

from web.db import connect


def main() -> None:
    with connect() as connection:
        row = connection.execute(
            "SELECT current_database() AS database_name, current_user AS connected_role, version() AS server_version"
        ).fetchone()
        tables = connection.execute(
            "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' "
            "AND table_name = ANY(%s) ORDER BY table_name",
            (["users", "categories", "suppliers", "drugs", "inventory_batches", "transactions", "sales_items"],),
        ).fetchall()
    print(f"Connected to database: {row['database_name']}")
    print(f"Database role: {row['connected_role']}")
    print("Expected tables found: " + (", ".join(table["table_name"] for table in tables) or "none"))
    if len(tables) != 7:
        raise SystemExit("Connection succeeded, but the schema is missing one or more expected tables.")


if __name__ == "__main__":
    main()
