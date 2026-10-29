from db import get_connection

try:
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT current_database() AS database_name, (SELECT COUNT(*) FROM drugs) AS total")
            result = cursor.fetchone()
            print(f"Connected to PostgreSQL database '{result['database_name']}'. Drug rows: {result['total']}.")
    finally:
        conn.close()
except Exception as exc:
    print(f"Connection check failed ({type(exc).__name__}). Check DATABASE_URL and network/database settings; credentials are not displayed.")