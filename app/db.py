import os
import mysql.connector

HOST = os.environ.get("PF_DB_HOST", "localhost")
NAME = os.environ.get("PF_DB_NAME", "pharmacy_sales_and_inventory_db")

# One MySQL account per role (created by sql/05_roles_privileges.sql).
# "login" is the account used BEFORE we know who the user is: it can only
# read the USERS table, to check the username and password.
ACCOUNTS = {
    "login":            ("pf_login",      "Login@123"),
    "Admin":            ("pf_admin",      "Admin@123"),
    "InventoryManager": ("pf_inventory",  "Inventory@123"),
    "Pharmacist":       ("pf_pharmacist", "Pharmacist@123"),
    "Cashier":          ("pf_cashier",    "Cashier@123"),
}

_current = "login"


def set_role(role):
    """Switch every later connect() to the MySQL account of this role.
    Call set_role(<Role>) after a successful login and set_role("login") on logout."""
    global _current
    if role not in ACCOUNTS:
        raise ValueError(f"Unknown role: {role}")
    _current = role


def connect():
    user, password = ACCOUNTS[_current]
    return mysql.connector.connect(host=HOST, user=user, password=password, database=NAME)
