import mysql.connector

# Connection settings (change in one place)
DB = dict(
    host="localhost",
    user="pf_admin",
    password="Admin@123",
    database="pharmacy_sales_and_inventory_db",
)


def connect():
    return mysql.connector.connect(**DB)
