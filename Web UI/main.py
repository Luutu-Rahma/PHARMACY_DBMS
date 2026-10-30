"""PharmaFlow web application. Existing MySQL tables/triggers are the source of truth."""
from __future__ import annotations

import argparse
import os
import re
import hmac
import threading
from contextlib import asynccontextmanager
from contextlib import contextmanager
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

import pymysql
from dotenv import load_dotenv
from fastapi import FastAPI, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

from auth import ROLE_PAGES, VALID_ROLES, current_user, csrf_token, new_sale_nonce, require_role, require_user, verify_csrf
from db import APP_DIR, DatabaseConfigurationError, DatabaseUnavailable, connect, test_connection

load_dotenv(APP_DIR.parent / ".env", override=False)
load_dotenv(APP_DIR / ".env", override=True)
TEMPLATES = Jinja2Templates(directory=str(APP_DIR / "templates"))
TEMPLATES.env.filters["money"] = lambda value: f"{Decimal(value or 0):,.0f}"
TEMPLATES.env.filters["datefmt"] = lambda value: value.strftime("%Y-%m-%d") if hasattr(value, "strftime") else value
LOW_STOCK = 50
SOON_DAYS = 90
PAYMENT_METHODS = ("Cash", "Mobile Money")
UNIT_MEASURES = ("tablets", "capsules", "syrup", "injection", "cream")

MENUS = {
    "Admin": [("Sales", "/sales"), ("Inventory", "/inventory"), ("Drugs & Suppliers", "/catalogue/drugs"), ("Reports", "/reports"), ("Users", "/users")],
    "InventoryManager": [("Inventory", "/inventory"), ("Drugs & Suppliers", "/catalogue/drugs"), ("Reports", "/reports")],
    "Pharmacist": [("View Drugs", "/drugs"), ("View Stock", "/stock"), ("Reports", "/reports")],
    "Cashier": [("Sales", "/sales")],
}

@asynccontextmanager
async def lifespan(_: FastAPI):
    require_app_config()
    yield


app = FastAPI(title="PharmaFlow", docs_url=None, redoc_url=None, lifespan=lifespan)
secret = os.getenv("SESSION_SECRET", "")
if len(secret) < 32 or "replace-with" in secret.lower():
    # App import remains usable for tests; startup rejects the ephemeral key.
    secret = os.urandom(48).hex()
app.add_middleware(
    SessionMiddleware,
    secret_key=secret,
    session_cookie="pharmaflow_session",
    same_site="lax",
    https_only=os.getenv("COOKIE_SECURE", "false").strip().lower() == "true",
    max_age=60 * 60 * 8,
)
app.mount("/static", StaticFiles(directory=str(APP_DIR / "static")), name="static")
_used_sale_nonces: set[str] = set()
_sale_nonce_lock = threading.Lock()


@contextmanager
def db_connection():
    connection = connect()
    try:
        yield connection
    finally:
        connection.close()


def fetch_all(sql: str, values: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
    with db_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(sql, values)
            return list(cursor.fetchall())


def fetch_one(sql: str, values: tuple[Any, ...] = ()) -> dict[str, Any] | None:
    with db_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(sql, values)
            return cursor.fetchone()


def safe_db_message(error: BaseException) -> str:
    code = error.args[0] if getattr(error, "args", ()) else None
    if code == 1062:
        return "That value is already in use. Check usernames, categories, or the drug/batch number."
    if code == 1452:
        return "A selected drug, supplier, category, or user no longer exists. Refresh and try again."
    if code == 1644:
        return "The database rejected the sale because the batch is expired or has insufficient stock."
    if code in {1044, 1045, 1698}:
        return "Aiven rejected the database account. Verify its credentials and required grants."
    if code in {1049, 1146}:
        return "The configured Aiven database or required PharmaFlow tables are missing. Review database setup."
    if isinstance(error, DatabaseUnavailable):
        return str(error)
    if isinstance(error, DatabaseConfigurationError):
        return str(error)
    if isinstance(error, pymysql.MySQLError):
        return "The database operation failed. Check the Aiven service, schema, and account privileges."
    return "The request could not be completed. Please try again or contact the database administrator."


def render(request: Request, template: str, **context: Any) -> HTMLResponse:
    user = current_user(request)
    messages = request.session.pop("messages", [])
    return TEMPLATES.TemplateResponse(
        request=request,
        name=template,
        context={
            "user": user,
            "menu": MENUS.get(user["role"], []) if user else [],
            "csrf": csrf_token(request),
            "messages": messages,
            **context,
        },
    )


def flash(request: Request, text: str, kind: str = "success") -> None:
    messages = request.session.get("messages", [])
    messages.append({"text": text, "kind": kind})
    request.session["messages"] = messages[-4:]


def redirect(path: str) -> RedirectResponse:
    return RedirectResponse(path, status_code=303)


def normalized_text(value: str, label: str, maximum: int, required: bool = True) -> str | None:
    text = value.strip()
    if not text:
        if required:
            raise ValueError(f"{label} is required.")
        return None
    if len(text) > maximum:
        raise ValueError(f"{label} must be {maximum} characters or fewer.")
    return text


def parse_positive_int(value: str, label: str) -> int:
    if not re.fullmatch(r"[1-9][0-9]{0,8}", value.strip()):
        raise ValueError(f"{label} must be a whole number above 0.")
    return int(value)


def parse_price(value: str, label: str = "Price") -> Decimal:
    try:
        amount = Decimal(value.strip())
    except (InvalidOperation, AttributeError):
        raise ValueError(f"{label} must be a valid amount above 0.") from None
    if not amount.is_finite() or amount <= 0 or amount > Decimal("9999999999.99"):
        raise ValueError(f"{label} must be a valid amount above 0.")
    return amount.quantize(Decimal("0.01"))


def require_app_config() -> None:
    configured_secret = os.getenv("SESSION_SECRET", "")
    if len(configured_secret) < 32 or "replace-with" in configured_secret.lower():
        raise DatabaseConfigurationError("Set a unique SESSION_SECRET of at least 32 characters in Web UI/.env.")


@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    user = current_user(request)
    if not user:
        return redirect("/login")
    destinations = {"Admin": "/dashboard", "InventoryManager": "/inventory", "Pharmacist": "/drugs", "Cashier": "/sales"}
    return redirect(destinations[user["role"]])


@app.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    if current_user(request):
        return redirect("/")
    return render(request, "login.html", page_title="Sign in", error=None)


@app.post("/login", response_class=HTMLResponse)
def login(request: Request, username: str = Form(""), password: str = Form(""), csrf: str = Form("", alias="_csrf")):
    try:
        verify_csrf(request, csrf)
        username = username.strip()
        if not username or not password or len(username) > 50:
            raise ValueError("Enter your username and password.")
        user = fetch_one(
            "SELECT UserID, FullName, `Role` FROM USERS WHERE UserName=%s AND Password=SHA2(%s,256)",
            (username, password),
        )
        if not user or user["Role"] not in ROLE_PAGES:
            raise ValueError("Username or password is incorrect.")
        request.session.clear()
        request.session["user"] = {"id": user["UserID"], "name": user["FullName"], "role": user["Role"]}
        csrf_token(request)
        request.session["basket"] = []
        return redirect("/")
    except HTTPException:
        raise
    except (ValueError, DatabaseConfigurationError, DatabaseUnavailable, pymysql.MySQLError) as exc:
        message = str(exc) if isinstance(exc, ValueError) else safe_db_message(exc)
        return render(request, "login.html", page_title="Sign in", error=message)
    finally:
        password = ""


@app.post("/logout")
def logout(request: Request, csrf: str = Form("", alias="_csrf")):
    verify_csrf(request, csrf)
    request.session.clear()
    return redirect("/login")


@app.get("/dashboard", response_class=HTMLResponse)
def dashboard(request: Request):
    user = require_user(request)
    cards: list[dict[str, Any]] = []
    try:
        if user["role"] in {"Admin", "InventoryManager", "Pharmacist"}:
            row = fetch_one(
                "SELECT COUNT(DISTINCT d.DrugID) AS drug_count, COALESCE(SUM(CASE WHEN b.ExpiryDate > CURDATE() THEN b.QuantityLeft ELSE 0 END),0) AS sellable "
                "FROM DRUGS d LEFT JOIN INVENTORY_BATCHES b ON b.DrugID=d.DrugID"
            )
            cards.extend([{"label": "Drug catalogue", "value": row["drug_count"]}, {"label": "Sellable units", "value": row["sellable"]}])
            expiring = fetch_one("SELECT COUNT(*) AS n FROM INVENTORY_BATCHES WHERE QuantityLeft>0 AND ExpiryDate BETWEEN CURDATE() AND CURDATE()+INTERVAL 90 DAY")
            cards.append({"label": "Batches expiring in 90 days", "value": expiring["n"], "warning": bool(expiring["n"])})
        if user["role"] == "Admin":
            sales = fetch_one("SELECT COUNT(*) AS n, COALESCE(SUM(TotalAmount),0) AS total FROM TRANSACTIONS WHERE DATE(`TimeStamp`)=CURDATE()")
            cards.extend([{"label": "Sales today", "value": sales["n"]}, {"label": "Revenue today (UGX)", "value": f"{Decimal(sales['total']):,.0f}"}])
        if user["role"] in {"Admin", "Cashier"}:
            cards.append({"label": "Sale entry", "value": "Open Sales"})
    except (DatabaseConfigurationError, DatabaseUnavailable, pymysql.MySQLError) as exc:
        flash(request, safe_db_message(exc), "error")
    return render(request, "dashboard.html", page_title="Overview", cards=cards)


@app.get("/sales", response_class=HTMLResponse)
def sales_page(request: Request):
    user = require_role(request, "sales")
    try:
        batches = fetch_all(
            "SELECT b.BatchID, d.GenericName, d.BrandName, b.BatchNumber, b.QuantityLeft, b.ExpiryDate, b.UnitPrice "
            "FROM INVENTORY_BATCHES b JOIN DRUGS d ON d.DrugID=b.DrugID "
            "WHERE b.ExpiryDate>CURDATE() AND b.QuantityLeft>0 ORDER BY b.ExpiryDate, d.GenericName"
        )
        basket = request.session.get("basket", [])
        basket_by_id = {int(item["batch_id"]): int(item["qty"]) for item in basket}
        basket_ids = set(basket_by_id)
        basket_rows = [batch for batch in batches if batch["BatchID"] in basket_ids]
        total = sum((Decimal(row["UnitPrice"]) * basket_by_id[row["BatchID"]] for row in basket_rows), Decimal(0))
        return render(request, "sales.html", page_title="New sale", batches=batches,
                      basket=basket_rows, quantities=basket_by_id, total=total,
                      sale_nonce=new_sale_nonce(request), payment_methods=PAYMENT_METHODS)
    except (DatabaseConfigurationError, DatabaseUnavailable, pymysql.MySQLError) as exc:
        return render(request, "sales.html", page_title="New sale", batches=[], basket=[], quantities={}, total=Decimal(0),
                      sale_nonce=new_sale_nonce(request), payment_methods=PAYMENT_METHODS, page_error=safe_db_message(exc))


def _get_eligible_batch(batch_id: int) -> dict[str, Any] | None:
    return fetch_one(
        "SELECT BatchID, QuantityLeft, ExpiryDate FROM INVENTORY_BATCHES "
        "WHERE BatchID=%s AND QuantityLeft>0 AND ExpiryDate>CURDATE()", (batch_id,)
    )


@app.post("/sales/basket/add")
def basket_add(request: Request, batch_id: str = Form(""), quantity: str = Form("1"), csrf: str = Form("", alias="_csrf")):
    user = require_role(request, "sales")
    verify_csrf(request, csrf)
    try:
        bid = parse_positive_int(batch_id, "Batch")
        qty = parse_positive_int(quantity, "Quantity")
        batch = _get_eligible_batch(bid)
        if not batch:
            raise ValueError("That batch is expired, empty, or no longer available.")
        basket = request.session.get("basket", [])
        existing = next((item for item in basket if int(item["batch_id"]) == bid), None)
        requested = qty + (int(existing["qty"]) if existing else 0)
        if requested > int(batch["QuantityLeft"]):
            raise ValueError(f"Only {batch['QuantityLeft']} units are currently available in that batch.")
        if existing:
            existing["qty"] = requested
        else:
            basket.append({"batch_id": bid, "qty": qty})
        request.session["basket"] = basket
        flash(request, "Item added to the basket.")
    except ValueError as exc:
        flash(request, str(exc), "error")
    except (DatabaseConfigurationError, DatabaseUnavailable, pymysql.MySQLError) as exc:
        flash(request, safe_db_message(exc), "error")
    return redirect("/sales")


@app.post("/sales/basket/remove")
def basket_remove(request: Request, batch_id: str = Form(""), csrf: str = Form("", alias="_csrf")):
    require_role(request, "sales")
    verify_csrf(request, csrf)
    try:
        bid = parse_positive_int(batch_id, "Batch")
        request.session["basket"] = [item for item in request.session.get("basket", []) if int(item["batch_id"]) != bid]
        flash(request, "Basket line removed.")
    except ValueError as exc:
        flash(request, str(exc), "error")
    return redirect("/sales")


@app.post("/sales/basket/clear")
def basket_clear(request: Request, csrf: str = Form("", alias="_csrf")):
    require_role(request, "sales")
    verify_csrf(request, csrf)
    request.session["basket"] = []
    flash(request, "Basket cleared.")
    return redirect("/sales")


@app.post("/sales/complete", response_class=HTMLResponse)
def sales_complete(request: Request, payment_method: str = Form("Cash"), sale_nonce_value: str = Form(""), csrf: str = Form("", alias="_csrf")):
    user = require_role(request, "sales")
    verify_csrf(request, csrf)
    expected_nonce = request.session.get("sale_nonce", "")
    if not sale_nonce_value or not expected_nonce or not hmac.compare_digest(sale_nonce_value, expected_nonce):
        flash(request, "This sale form was already submitted or expired. Reload before trying again.", "error")
        return redirect("/sales")
    with _sale_nonce_lock:
        if sale_nonce_value in _used_sale_nonces:
            flash(request, "This sale form was already submitted. Start a new checkout.", "error")
            return redirect("/sales")
        _used_sale_nonces.add(sale_nonce_value)
    try:
        if payment_method not in PAYMENT_METHODS:
            raise ValueError("Choose Cash or Mobile Money.")
        basket = request.session.get("basket", [])
        if not basket:
            raise ValueError("Add at least one item before completing a sale.")
        quantities: dict[int, int] = {}
        for item in basket:
            bid = int(item["batch_id"])
            qty = int(item["qty"])
            if bid <= 0 or qty <= 0:
                raise ValueError("The basket contains an invalid line. Clear it and try again.")
            quantities[bid] = quantities.get(bid, 0) + qty

        connection = connect()
        try:
            connection.begin()
            with connection.cursor() as cursor:
                # Lock all batches in a stable order so competing checkouts cannot oversell.
                locked: dict[int, dict[str, Any]] = {}
                for bid in sorted(quantities):
                    cursor.execute(
                        "SELECT BatchID, QuantityLeft, ExpiryDate FROM INVENTORY_BATCHES WHERE BatchID=%s FOR UPDATE",
                        (bid,),
                    )
                    locked_row = cursor.fetchone()
                    if not locked_row or locked_row["ExpiryDate"] <= date.today():
                        raise ValueError("A basket batch has expired or is no longer available.")
                    if int(locked_row["QuantityLeft"]) < quantities[bid]:
                        raise ValueError("There is insufficient stock for one or more basket lines.")
                    locked[bid] = locked_row

                # The existing AFTER INSERT trigger deducts stock and updates transaction totals.
                cursor.execute("SELECT TRIGGER_NAME FROM information_schema.TRIGGERS WHERE TRIGGER_SCHEMA=DATABASE() AND EVENT_OBJECT_TABLE='SALES_ITEMS'")
                triggers = {row["TRIGGER_NAME"] for row in cursor.fetchall()}
                if not {"trg_sale_before_insert", "trg_sale_after_insert"}.issubset(triggers):
                    raise RuntimeError("The required PharmaFlow sale triggers are missing. See the setup README.")
                cursor.execute("SELECT TABLE_NAME, ENGINE FROM information_schema.TABLES WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME IN ('TRANSACTIONS','SALES_ITEMS','INVENTORY_BATCHES')")
                engines = {row["TABLE_NAME"]: row["ENGINE"] for row in cursor.fetchall()}
                if set(engines) != {"TRANSACTIONS", "SALES_ITEMS", "INVENTORY_BATCHES"} or any(engine != "InnoDB" for engine in engines.values()):
                    raise RuntimeError("Sales require the existing transaction and stock tables to use InnoDB.")

                cursor.execute("INSERT INTO TRANSACTIONS (UserID, PaymentMethod) VALUES (%s, %s)", (user["id"], payment_method))
                transaction_id = cursor.lastrowid
                for bid in sorted(quantities):
                    cursor.execute(
                        "INSERT INTO SALES_ITEMS (TransactionID, BatchID, QuantitySold) VALUES (%s, %s, %s)",
                        (transaction_id, bid, quantities[bid]),
                    )
                cursor.execute("SELECT TotalAmount, `TimeStamp` FROM TRANSACTIONS WHERE TransactionID=%s", (transaction_id,))
                transaction = cursor.fetchone()
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

        request.session["basket"] = []
        request.session["sale_nonce"] = os.urandom(24).hex()
        request.session["receipt"] = {"id": transaction_id, "method": payment_method, "total": str(transaction["TotalAmount"]), "timestamp": str(transaction["TimeStamp"])}
        flash(request, f"Sale #{transaction_id} completed.")
        return redirect(f"/sales/receipt/{transaction_id}")
    except ValueError as exc:
        request.session["sale_nonce"] = os.urandom(24).hex()
        flash(request, str(exc), "error")
    except RuntimeError as exc:
        request.session["sale_nonce"] = os.urandom(24).hex()
        flash(request, str(exc), "error")
    except (DatabaseConfigurationError, DatabaseUnavailable, pymysql.MySQLError) as exc:
        request.session["sale_nonce"] = os.urandom(24).hex()
        flash(request, safe_db_message(exc), "error")
    return redirect("/sales")


@app.get("/sales/receipt/{transaction_id}", response_class=HTMLResponse)
def sale_receipt(request: Request, transaction_id: int):
    user = require_role(request, "sales")
    try:
        header = fetch_one(
            "SELECT t.TransactionID, t.UserID, t.`TimeStamp`, t.PaymentMethod, t.TotalAmount, u.FullName "
            "FROM TRANSACTIONS t JOIN USERS u ON u.UserID=t.UserID WHERE t.TransactionID=%s", (transaction_id,)
        )
        if not header or (user["role"] == "Cashier" and int(header["UserID"]) != int(user["id"])):
            raise HTTPException(status_code=404, detail="Receipt not found.")
        lines = fetch_all(
            "SELECT d.GenericName, b.BatchNumber, si.QuantitySold, b.UnitPrice, si.SubTotal "
            "FROM SALES_ITEMS si JOIN INVENTORY_BATCHES b ON b.BatchID=si.BatchID "
            "JOIN DRUGS d ON d.DrugID=b.DrugID WHERE si.TransactionID=%s ORDER BY si.SalesItemID", (transaction_id,)
        )
        return render(request, "receipt.html", page_title=f"Receipt #{transaction_id}", receipt=header, lines=lines)
    except HTTPException:
        raise
    except (DatabaseConfigurationError, DatabaseUnavailable, pymysql.MySQLError) as exc:
        raise HTTPException(status_code=503, detail=safe_db_message(exc)) from None


@app.get("/inventory", response_class=HTMLResponse)
def inventory_page(request: Request):
    require_role(request, "inventory")
    try:
        batches = fetch_all(
            "SELECT b.BatchID, d.GenericName, b.BatchNumber, s.SupplierName, b.QuantityReceived, b.QuantityLeft, "
            "b.MFD, b.ExpiryDate, b.UnitPrice, DATEDIFF(b.ExpiryDate,CURDATE()) AS DaysLeft "
            "FROM INVENTORY_BATCHES b JOIN DRUGS d ON d.DrugID=b.DrugID JOIN SUPPLIERS s ON s.SupplierID=b.SupplierID "
            "ORDER BY b.ExpiryDate, d.GenericName"
        )
        drugs = fetch_all("SELECT DrugID, GenericName, BrandName FROM DRUGS ORDER BY GenericName")
        suppliers = fetch_all("SELECT SupplierID, SupplierName FROM SUPPLIERS ORDER BY SupplierName")
        return render(request, "inventory.html", page_title="Inventory", batches=batches, drugs=drugs, suppliers=suppliers, page_error=None)
    except (DatabaseConfigurationError, DatabaseUnavailable, pymysql.MySQLError) as exc:
        return render(request, "inventory.html", page_title="Inventory", batches=[], drugs=[], suppliers=[], page_error=safe_db_message(exc))


@app.post("/inventory/receive")
def inventory_receive(request: Request, drug_id: str = Form(""), supplier_id: str = Form(""), batch_number: str = Form(""), quantity: str = Form(""), mfd: str = Form(""), expiry_date: str = Form(""), unit_price: str = Form(""), csrf: str = Form("", alias="_csrf")):
    require_role(request, "inventory")
    verify_csrf(request, csrf)
    try:
        did = parse_positive_int(drug_id, "Drug")
        sid = parse_positive_int(supplier_id, "Supplier")
        batch = normalized_text(batch_number, "Batch number", 50)
        qty = parse_positive_int(quantity, "Quantity")
        price = parse_price(unit_price, "Unit price")
        manufactured = date.fromisoformat(mfd)
        expires = date.fromisoformat(expiry_date)
        if manufactured >= expires:
            raise ValueError("Expiry date must be after the manufacture date.")
        if expires <= date.today():
            raise ValueError("This batch is already expired.")
        with db_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    "INSERT INTO INVENTORY_BATCHES (DrugID,SupplierID,BatchNumber,QuantityReceived,QuantityLeft,MFD,ExpiryDate,UnitPrice) "
                    "VALUES (%s,%s,%s,%s,%s,%s,%s,%s)", (did, sid, batch, qty, qty, manufactured, expires, price)
                )
            connection.commit()
        flash(request, f"Batch {batch} received ({qty} units).")
    except (ValueError, OverflowError) as exc:
        flash(request, str(exc) or "Enter valid dates and quantities.", "error")
    except (DatabaseConfigurationError, DatabaseUnavailable, pymysql.MySQLError) as exc:
        flash(request, safe_db_message(exc), "error")
    return redirect("/inventory")


CATALOGUE = {
    "drugs": {
        "table": "DRUGS", "pk": "DrugID", "heading": "Drugs",
        "list_sql": "SELECT d.DrugID,d.GenericName,d.BrandName,c.CategoryName,d.UnitMeasure,d.UnitPrice FROM DRUGS d JOIN CATEGORIES c ON c.CategoryID=d.CategoryID ORDER BY d.GenericName",
        "fields": (("generic_name", "Generic name", "text", 150, True), ("brand_name", "Brand name", "text", 150, True), ("category_id", "Category", "category", 0, True), ("unit_measure", "Unit of measure", "unit", 0, True), ("unit_price", "Unit price (UGX)", "price", 0, True)),
        "columns": ("ID", "Generic name", "Brand", "Category", "Unit", "Price (UGX)"),
    },
    "suppliers": {
        "table": "SUPPLIERS", "pk": "SupplierID", "heading": "Suppliers",
        "list_sql": "SELECT SupplierID,SupplierName,ContactPerson,PhoneNumber,Email,Address FROM SUPPLIERS ORDER BY SupplierName",
        "fields": (("supplier_name", "Supplier name", "text", 150, True), ("contact_person", "Contact person", "text", 100, False), ("phone_number", "Phone number", "text", 20, True), ("email", "Email", "email", 100, False), ("address", "Address", "text", 1000, False)),
        "columns": ("ID", "Supplier", "Contact", "Phone", "Email", "Address"),
    },
    "categories": {
        "table": "CATEGORIES", "pk": "CategoryID", "heading": "Categories",
        "list_sql": "SELECT CategoryID,CategoryName,Description FROM CATEGORIES ORDER BY CategoryName",
        "fields": (("category_name", "Category name", "text", 100, True), ("description", "Description", "text", 4000, False)),
        "columns": ("ID", "Category", "Description"),
    },
}


def catalogue_values(entity: str, form: Any) -> tuple[list[str], list[Any]]:
    spec = CATALOGUE[entity]
    columns: list[str] = []
    values: list[Any] = []
    for key, label, kind, maximum, required in spec["fields"]:
        raw = str(form.get(key, "")).strip()
        if kind == "category":
            if not raw.isdigit() or int(raw) <= 0:
                raise ValueError("Choose a category.")
            columns.append("CategoryID")
            values.append(int(raw))
        elif kind == "unit":
            if raw not in UNIT_MEASURES:
                raise ValueError("Choose a supported unit of measure.")
            columns.append("UnitMeasure")
            values.append(raw)
        elif kind == "price":
            columns.append("UnitPrice")
            values.append(parse_price(raw, label))
        else:
            value = normalized_text(raw, label, maximum, required)
            if kind == "email" and value and (len(value) > 100 or not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", value)):
                raise ValueError("Enter a valid email address.")
            columns.append({"generic_name":"GenericName", "brand_name":"BrandName", "supplier_name":"SupplierName", "contact_person":"ContactPerson", "phone_number":"PhoneNumber", "email":"Email", "address":"Address", "category_name":"CategoryName", "description":"Description"}[key])
            values.append(value)
    return columns, values


@app.get("/catalogue/{entity}", response_class=HTMLResponse)
def catalogue_page(request: Request, entity: str, edit_id: int | None = None):
    require_role(request, "catalogue")
    if entity not in CATALOGUE:
        raise HTTPException(status_code=404, detail="Catalogue section not found.")
    spec = CATALOGUE[entity]
    try:
        rows = fetch_all(spec["list_sql"])
        categories = fetch_all("SELECT CategoryID,CategoryName FROM CATEGORIES ORDER BY CategoryName") if entity == "drugs" else []
        selected = None
        if edit_id is not None:
            selected = fetch_one(f"SELECT * FROM {spec['table']} WHERE {spec['pk']}=%s", (edit_id,))
            if not selected:
                raise HTTPException(status_code=404, detail="Record not found.")
        value_columns = {
            "drugs": {"generic_name": "GenericName", "brand_name": "BrandName", "category_id": "CategoryID", "unit_measure": "UnitMeasure", "unit_price": "UnitPrice"},
            "suppliers": {"supplier_name": "SupplierName", "contact_person": "ContactPerson", "phone_number": "PhoneNumber", "email": "Email", "address": "Address"},
            "categories": {"category_name": "CategoryName", "description": "Description"},
        }
        edit_values = {key: selected.get(column) for key, column in value_columns[entity].items()} if selected else None
        return render(request, "catalogue.html", page_title=spec["heading"], entity=entity, spec=spec, rows=rows, categories=categories, selected=selected, edit_values=edit_values, units=UNIT_MEASURES, page_error=None)
    except HTTPException:
        raise
    except (DatabaseConfigurationError, DatabaseUnavailable, pymysql.MySQLError) as exc:
        return render(request, "catalogue.html", page_title=spec["heading"], entity=entity, spec=spec, rows=[], categories=[], selected=None, edit_values=None, units=UNIT_MEASURES, page_error=safe_db_message(exc))


@app.post("/catalogue/{entity}/save")
async def catalogue_save(request: Request, entity: str):
    require_role(request, "catalogue")
    if entity not in CATALOGUE:
        raise HTTPException(status_code=404, detail="Catalogue section not found.")
    form = await request.form()
    verify_csrf(request, str(form.get("_csrf", "")))
    spec = CATALOGUE[entity]
    try:
        columns, values = catalogue_values(entity, form)
        selected_id = str(form.get("record_id", "")).strip()
        record_id = parse_positive_int(selected_id, "Record ID") if selected_id else None
        with db_connection() as connection:
            with connection.cursor() as cursor:
                if record_id is None:
                    marks = ",".join(["%s"] * len(columns))
                    cursor.execute(f"INSERT INTO {spec['table']} ({','.join(columns)}) VALUES ({marks})", tuple(values))
                    action = "created"
                else:
                    cursor.execute(f"SELECT {spec['pk']} FROM {spec['table']} WHERE {spec['pk']}=%s", (record_id,))
                    if cursor.fetchone() is None:
                        raise ValueError("That record no longer exists. Refresh and try again.")
                    updates = ",".join(f"{column}=%s" for column in columns)
                    cursor.execute(f"UPDATE {spec['table']} SET {updates} WHERE {spec['pk']}=%s", tuple(values + [record_id]))
                    action = "updated"
            connection.commit()
        flash(request, f"{spec['heading'][:-1] if spec['heading'].endswith('s') else spec['heading']} {action}.")
    except ValueError as exc:
        flash(request, str(exc), "error")
    except (DatabaseConfigurationError, DatabaseUnavailable, pymysql.MySQLError) as exc:
        flash(request, safe_db_message(exc), "error")
    return redirect(f"/catalogue/{entity}")


@app.get("/drugs", response_class=HTMLResponse)
def drugs_page(request: Request, q: str = ""):
    require_role(request, "drugs")
    term = q.strip()[:100]
    like = f"%{term}%"
    try:
        drugs = fetch_all(
            "SELECT d.GenericName,d.BrandName,c.CategoryName,d.UnitMeasure,d.UnitPrice,"
            "COALESCE(SUM(CASE WHEN b.ExpiryDate>CURDATE() THEN b.QuantityLeft ELSE 0 END),0) AS SellableStock "
            "FROM DRUGS d JOIN CATEGORIES c ON c.CategoryID=d.CategoryID LEFT JOIN INVENTORY_BATCHES b ON b.DrugID=d.DrugID "
            "WHERE d.GenericName LIKE %s OR COALESCE(d.BrandName,'') LIKE %s OR c.CategoryName LIKE %s "
            "GROUP BY d.DrugID,d.GenericName,d.BrandName,c.CategoryName,d.UnitMeasure,d.UnitPrice ORDER BY d.GenericName",
            (like, like, like),
        )
        return render(request, "drugs.html", page_title="Drug catalogue", drugs=drugs, q=term, low_stock=LOW_STOCK)
    except (DatabaseConfigurationError, DatabaseUnavailable, pymysql.MySQLError) as exc:
        return render(request, "drugs.html", page_title="Drug catalogue", drugs=[], q=term, low_stock=LOW_STOCK, page_error=safe_db_message(exc))


@app.get("/stock", response_class=HTMLResponse)
def stock_page(request: Request, q: str = "", hide_expired: bool = False, hide_empty: bool = False):
    require_role(request, "stock")
    term = q.strip()[:100]
    try:
        rows = fetch_all(
            "SELECT d.GenericName,b.BatchNumber,s.SupplierName,b.QuantityLeft,b.ExpiryDate,DATEDIFF(b.ExpiryDate,CURDATE()) AS DaysLeft "
            "FROM INVENTORY_BATCHES b JOIN DRUGS d ON d.DrugID=b.DrugID JOIN SUPPLIERS s ON s.SupplierID=b.SupplierID "
            "WHERE (d.GenericName LIKE %s OR b.BatchNumber LIKE %s OR s.SupplierName LIKE %s) "
            "AND (%s=0 OR b.ExpiryDate>CURDATE()) AND (%s=0 OR b.QuantityLeft>0) ORDER BY d.GenericName,b.ExpiryDate",
            (f"%{term}%", f"%{term}%", f"%{term}%", int(hide_expired), int(hide_empty)),
        )
        return render(request, "stock.html", page_title="Stock by batch", batches=rows, q=term, hide_expired=hide_expired, hide_empty=hide_empty, soon_days=SOON_DAYS)
    except (DatabaseConfigurationError, DatabaseUnavailable, pymysql.MySQLError) as exc:
        return render(request, "stock.html", page_title="Stock by batch", batches=[], q=term, hide_expired=hide_expired, hide_empty=hide_empty, soon_days=SOON_DAYS, page_error=safe_db_message(exc))


@app.get("/reports", response_class=HTMLResponse)
def reports_page(request: Request, report: str = "sales"):
    require_role(request, "reports")
    allowed = {"sales", "payments", "stock", "top", "expiry", "staff", "deliveries"}
    if report not in allowed:
        report = "sales"
    data: dict[str, Any] = {}
    error = None
    try:
        if report == "sales":
            data["rows"] = fetch_all("SELECT DATE(`TimeStamp`) AS SaleDate,COUNT(*) AS Transactions,SUM(TotalAmount) AS Revenue FROM TRANSACTIONS GROUP BY DATE(`TimeStamp`) ORDER BY SaleDate DESC")
        elif report == "payments":
            data["rows"] = fetch_all("SELECT PaymentMethod,COUNT(*) AS Transactions,SUM(TotalAmount) AS Revenue FROM TRANSACTIONS GROUP BY PaymentMethod ORDER BY Revenue DESC")
        elif report == "stock":
            data["rows"] = fetch_all("SELECT d.GenericName,COALESCE(SUM(CASE WHEN b.ExpiryDate>CURDATE() THEN b.QuantityLeft ELSE 0 END),0) AS SellableStock FROM DRUGS d LEFT JOIN INVENTORY_BATCHES b ON b.DrugID=d.DrugID GROUP BY d.DrugID,d.GenericName ORDER BY SellableStock,d.GenericName")
        elif report == "top":
            data["rows"] = fetch_all("SELECT d.GenericName,SUM(si.QuantitySold) AS UnitsSold,SUM(si.SubTotal) AS Revenue FROM SALES_ITEMS si JOIN INVENTORY_BATCHES b ON b.BatchID=si.BatchID JOIN DRUGS d ON d.DrugID=b.DrugID GROUP BY d.DrugID,d.GenericName ORDER BY UnitsSold DESC LIMIT 10")
        elif report == "expiry":
            data["rows"] = fetch_all("SELECT d.GenericName,b.BatchNumber,b.QuantityLeft,b.ExpiryDate,DATEDIFF(b.ExpiryDate,CURDATE()) AS DaysLeft,b.QuantityLeft*b.UnitPrice AS ValueAtRisk FROM INVENTORY_BATCHES b JOIN DRUGS d ON d.DrugID=b.DrugID WHERE b.QuantityLeft>0 AND b.ExpiryDate<=CURDATE()+INTERVAL 90 DAY ORDER BY b.ExpiryDate")
        elif report == "staff":
            data["rows"] = fetch_all("SELECT u.FullName,u.`Role`,COUNT(t.TransactionID) AS Transactions,COALESCE(SUM(t.TotalAmount),0) AS TotalSales FROM USERS u LEFT JOIN TRANSACTIONS t ON t.UserID=u.UserID GROUP BY u.UserID,u.FullName,u.`Role`")
        else:
            data["rows"] = fetch_all("SELECT sp.SupplierName,COUNT(b.BatchID) AS Batches,COALESCE(SUM(b.QuantityReceived),0) AS UnitsDelivered FROM SUPPLIERS sp LEFT JOIN INVENTORY_BATCHES b ON b.SupplierID=sp.SupplierID GROUP BY sp.SupplierID,sp.SupplierName ORDER BY sp.SupplierName")
    except (DatabaseConfigurationError, DatabaseUnavailable, pymysql.MySQLError) as exc:
        error = safe_db_message(exc)
    return render(request, "reports.html", page_title="Reports & insights", active_report=report, data=data, page_error=error, low_stock=LOW_STOCK)


@app.get("/users", response_class=HTMLResponse)
def users_page(request: Request, edit_id: int | None = None):
    require_role(request, "users")
    try:
        users = fetch_all("SELECT UserID,FullName,UserName,`Role` FROM USERS ORDER BY FullName")
        selected = fetch_one("SELECT UserID,FullName,UserName,`Role` FROM USERS WHERE UserID=%s", (edit_id,)) if edit_id else None
        return render(request, "users.html", page_title="User management", users=users, selected=selected, roles=VALID_ROLES)
    except (DatabaseConfigurationError, DatabaseUnavailable, pymysql.MySQLError) as exc:
        return render(request, "users.html", page_title="User management", users=[], selected=None, roles=VALID_ROLES, page_error=safe_db_message(exc))


@app.post("/users/save")
async def users_save(request: Request):
    user = require_role(request, "users")
    form = await request.form()
    verify_csrf(request, str(form.get("_csrf", "")))
    try:
        full_name = normalized_text(str(form.get("full_name", "")), "Full name", 150)
        username = normalized_text(str(form.get("username", "")), "Username", 50)
        role = str(form.get("role", ""))
        password = str(form.get("password", ""))
        confirm = str(form.get("confirm_password", ""))
        selected_id = str(form.get("user_id", "")).strip()
        if not re.fullmatch(r"[A-Za-z0-9_.-]{1,50}", username or ""):
            raise ValueError("Username may contain letters, numbers, dots, underscores, and hyphens.")
        if role not in VALID_ROLES:
            raise ValueError("Choose a supported role.")
        adding = not selected_id
        uid = parse_positive_int(selected_id, "User ID") if selected_id else None
        if adding and not password:
            raise ValueError("A password is required for a new user.")
        if password or confirm:
            if password != confirm:
                raise ValueError("The passwords do not match.")
            if len(password) < 6:
                raise ValueError("Use a password of at least 6 characters.")
        if not adding and uid == int(user["id"]) and role != "Admin":
            raise ValueError("You cannot remove your own Admin role.")
        with db_connection() as connection:
            with connection.cursor() as cursor:
                if adding:
                    cursor.execute("INSERT INTO USERS (FullName,UserName,Password,`Role`) VALUES (%s,%s,SHA2(%s,256),%s)", (full_name, username, password, role))
                    result = "created"
                elif password:
                    cursor.execute("UPDATE USERS SET FullName=%s,UserName=%s,`Role`=%s,Password=SHA2(%s,256) WHERE UserID=%s", (full_name, username, role, password, uid))
                    result = "updated; password changed"
                else:
                    cursor.execute("UPDATE USERS SET FullName=%s,UserName=%s,`Role`=%s WHERE UserID=%s", (full_name, username, role, uid))
                    result = "updated"
            connection.commit()
        flash(request, f"User {username} {result}.")
    except ValueError as exc:
        flash(request, str(exc), "error")
    except (DatabaseConfigurationError, DatabaseUnavailable, pymysql.MySQLError) as exc:
        flash(request, safe_db_message(exc), "error")
    return redirect("/users")


@app.exception_handler(HTTPException)
async def http_error_page(request: Request, exc: HTTPException):
    if exc.status_code == 303 and exc.headers and exc.headers.get("Location"):
        return RedirectResponse(exc.headers["Location"], status_code=303)
    if exc.status_code == 403:
        return TEMPLATES.TemplateResponse(request=request, name="error.html", context={"user": current_user(request), "menu": MENUS.get(current_user(request)["role"], []) if current_user(request) else [], "csrf": csrf_token(request), "messages": [], "status_code": 403, "message": str(exc.detail)}, status_code=403)
    return TEMPLATES.TemplateResponse(request=request, name="error.html", context={"user": current_user(request), "menu": MENUS.get(current_user(request)["role"], []) if current_user(request) else [], "csrf": csrf_token(request), "messages": [], "status_code": exc.status_code, "message": str(exc.detail)}, status_code=exc.status_code)


def main() -> None:
    parser = argparse.ArgumentParser(description="PharmaFlow FastAPI web application")
    parser.add_argument("--check-db", action="store_true", help="verify the configured Aiven MySQL connection")
    args = parser.parse_args()
    if args.check_db:
        try:
            details = test_connection()
            print(f"Connected securely to Aiven MySQL: {details['host']}:{details['port']} / {details['database']}")
        except (DatabaseConfigurationError, DatabaseUnavailable) as exc:
            print(f"Aiven MySQL connection test failed: {exc}")
            raise SystemExit(1) from None
        return
    require_app_config()
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=False)


if __name__ == "__main__":
    main()
