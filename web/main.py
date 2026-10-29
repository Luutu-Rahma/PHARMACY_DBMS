from __future__ import annotations

import logging
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any

import psycopg
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.sessions import SessionMiddleware
from urllib.parse import quote, urlencode

from web.config import COOKIE_SECURE, ROOT, SESSION_SECRET
from web.db import connect
from web.security import (
    AuthenticationRequired,
    PermissionDenied,
    ROLES,
    csrf_token,
    hash_password,
    require_role,
    require_user,
    validate_csrf,
    verify_password,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("pharmaflow")
app = FastAPI(title="PharmaFlow")
app.add_middleware(
    SessionMiddleware,
    secret_key=SESSION_SECRET,
    session_cookie="pharmaflow_session",
    max_age=60 * 60 * 8,
    same_site="lax",
    https_only=COOKIE_SECURE,
)
app.mount("/static", StaticFiles(directory=ROOT / "web" / "static"), name="static")
templates = Jinja2Templates(directory=ROOT / "web" / "templates")
RECORDS: dict[str, dict[str, Any]] = {
    "drugs": {
        "title": "Drugs", "table": "drugs", "pk": "drugid",
        "roles": ("Admin", "InventoryManager"),
        "fields": [
            ("genericname", "Generic name", "text", True),
            ("brandname", "Brand name", "text", True),
            ("categoryid", "Category", "category", True),
            ("unitmeasure", "Unit of measure", "unit", True),
            ("unitprice", "Unit price (UGX)", "number", True),
        ],
        "list_sql": "SELECT d.drugid, d.genericname, d.brandname, c.categoryname, d.unitmeasure, d.unitprice FROM drugs d JOIN categories c USING (categoryid) ORDER BY d.genericname",
    },
    "suppliers": {
        "title": "Suppliers", "table": "suppliers", "pk": "supplierid",
        "roles": ("Admin", "InventoryManager"),
        "fields": [
            ("suppliername", "Supplier name", "text", True),
            ("contactperson", "Contact person", "text", False),
            ("phonenumber", "Phone number", "text", True),
            ("email", "Email", "email", False),
            ("address", "Address", "text", False),
        ],
        "list_sql": "SELECT supplierid, suppliername, contactperson, phonenumber, email, address FROM suppliers ORDER BY suppliername",
    },
    "categories": {
        "title": "Categories", "table": "categories", "pk": "categoryid",
        "roles": ("Admin", "InventoryManager"),
        "fields": [("categoryname", "Category name", "text", True), ("description", "Description", "textarea", False)],
        "list_sql": "SELECT categoryid, categoryname, description FROM categories ORDER BY categoryname",
    },
}


def render(
    request: Request,
    name: str,
    user: dict[str, Any] | None = None,
    *,
    status_code: int = 200,
    **context: Any,
) -> HTMLResponse:
    context.update(request=request, user=user, csrf=csrf_token(request), current_date=date.today())
    return templates.TemplateResponse(request=request, name=name, context=context, status_code=status_code)


def redirect(path: str, notice: str | None = None, error: str | None = None) -> RedirectResponse:
    params = {key: value for key, value in (("notice", notice), ("error", error)) if value}
    target = path + ("?" + urlencode(params) if params else "")
    return RedirectResponse(target, status_code=303)


def clean_text(value: str | None, label: str, required: bool = True) -> str | None:
    normalized = (value or "").strip()
    if not normalized:
        if required:
            raise ValueError(f"{label} is required.")
        return None
    return normalized


def as_money(value: str | None, label: str) -> Decimal:
    try:
        amount = Decimal((value or "").strip())
    except (InvalidOperation, AttributeError):
        raise ValueError(f"Enter a valid {label.lower()}.") from None
    if not amount.is_finite() or amount <= 0:
        raise ValueError(f"{label} must be greater than zero.")
    return amount.quantize(Decimal("0.01"))


def check_csrf(request: Request, form: Any) -> None:
    validate_csrf(request, form.get("csrf_token"))


@app.exception_handler(AuthenticationRequired)
async def login_required_handler(request: Request, exc: AuthenticationRequired) -> Response:
    target = request.url.path
    if target.startswith(("/static/", "/health", "/login")):
        target = "/"
    location = f"/login?next={quote(target, safe='/')}&error={quote('Please sign in to continue.')}"
    return RedirectResponse(location, status_code=303)


@app.exception_handler(PermissionDenied)
async def permission_denied_handler(request: Request, exc: PermissionDenied) -> Response:
    user = None
    try:
        user = require_user(request)
    except AuthenticationRequired:
        pass
    template = "message.html" if user else "error.html"
    return render(request, template, user, error=str(exc), status_code=403)


@app.exception_handler(psycopg.Error)
async def database_error_handler(request: Request, exc: psycopg.Error) -> Response:
    logger.warning("Database operation failed (%s)", type(exc).__name__)
    return render(
        request,
        "error.html",
        error="The database could not complete that request. Check the form or connection and try again.",
        status_code=503,
    )


@app.exception_handler(StarletteHTTPException)
async def http_error_handler(request: Request, exc: StarletteHTTPException) -> Response:
    if exc.status_code == 404:
        return render(request, "not_found.html", status_code=404)
    if exc.status_code == 403:
        return render(request, "error.html", error="You do not have permission to access that page.", status_code=403)
    return render(request, "error.html", error="The request could not be completed.", status_code=exc.status_code)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/login", response_class=HTMLResponse)
def login_page(request: Request) -> HTMLResponse:
    if request.session.get("user_id"):
        return redirect("/")
    next_url = request.query_params.get("next", "/")
    if not next_url.startswith("/") or next_url.startswith("//"):
        next_url = "/"
    return render(request, "login.html", error=request.query_params.get("error"), next_url=next_url)


@app.post("/login")
async def login(request: Request) -> Response:
    form = await request.form()
    try:
        check_csrf(request, form)
    except PermissionDenied as exc:
        return redirect("/login", error=str(exc))
    username = str(form.get("username", "")).strip()
    password = str(form.get("password", ""))
    next_url = str(form.get("next", "/"))
    if not next_url.startswith("/") or next_url.startswith("//"):
        next_url = "/"
    if not username or not password:
        return render(request, "login.html", error="Enter your username and password.", next_url=next_url, status_code=400)
    with connect() as connection:
        user = connection.execute(
            "SELECT userid, fullname, username, role, password FROM users WHERE username = %s",
            (username,),
        ).fetchone()
        if user is None:
            valid, legacy = False, False
        else:
            valid, legacy = verify_password(password, user["password"])
        if not valid:
            return render(request, "login.html", error="Username or password is incorrect.", next_url=next_url, status_code=401)
        if legacy:
            connection.execute(
                "UPDATE users SET password = %s WHERE userid = %s",
                (hash_password(password), user["userid"]),
            )
    request.session.clear()
    request.session["user_id"] = user["userid"]
    csrf_token(request)
    return redirect(next_url)


@app.post("/logout")
async def logout(request: Request) -> Response:
    form = await request.form()
    try:
        check_csrf(request, form)
    except PermissionDenied:
        request.session.clear()
        return redirect("/login")
    request.session.clear()
    return redirect("/login", notice="You have signed out.")


@app.get("/")
def dashboard(request: Request) -> HTMLResponse:
    user = require_user(request)
    with connect() as connection:
        stats = connection.execute(
            "SELECT (SELECT COUNT(*) FROM drugs) AS drug_count, "
            "(SELECT COUNT(*) FROM inventory_batches WHERE quantityleft > 0 AND expirydate > CURRENT_DATE) AS active_batches, "
            "(SELECT COUNT(*) FROM transactions WHERE timestamp::date = CURRENT_DATE) AS sales_today, "
            "(SELECT COALESCE(SUM(totalamount), 0) FROM transactions WHERE timestamp::date = CURRENT_DATE) AS revenue_today"
        ).fetchone()
    return render(request, "dashboard.html", user, stats=stats)


@app.get("/sales")
def sales_page(request: Request) -> HTMLResponse:
    user = require_role(request, "Admin", "Cashier")
    cart = request.session.get("cart", {})
    with connect() as connection:
        batches = connection.execute(
            "SELECT b.batchid, d.genericname, COALESCE(d.brandname, '') AS brandname, "
            "b.batchnumber, b.quantityleft, b.expirydate, b.unitprice "
            "FROM inventory_batches b JOIN drugs d USING (drugid) "
            "WHERE b.quantityleft > 0 AND b.expirydate > CURRENT_DATE "
            "ORDER BY d.genericname, b.expirydate, b.batchid"
        ).fetchall()
        basket = []
        for batch_id, quantity in cart.items():
            item = connection.execute(
                "SELECT b.batchid, d.genericname, b.batchnumber, b.quantityleft, b.expirydate, "
                "b.unitprice, %s::integer AS cart_quantity "
                "FROM inventory_batches b JOIN drugs d USING (drugid) WHERE b.batchid = %s",
                (quantity, int(batch_id)),
            ).fetchone()
            if item:
                basket.append(item)
    total = sum((item["unitprice"] * item["cart_quantity"] for item in basket), Decimal("0"))
    return render(request, "sales.html", user, batches=batches, basket=basket, total=total)


@app.post("/sales/cart/add")
async def sales_add(request: Request) -> Response:
    require_role(request, "Admin", "Cashier")
    form = await request.form()
    try:
        check_csrf(request, form)
        batch_id = int(str(form.get("batchid", "")))
        quantity = int(str(form.get("quantity", "")))
        if quantity <= 0:
            raise ValueError("Quantity must be a whole number above zero.")
        cart = dict(request.session.get("cart", {}))
        if len(cart) >= 25 and str(batch_id) not in cart:
            raise ValueError("The basket can contain up to 25 different batches.")
        with connect() as connection:
            batch = connection.execute(
                "SELECT quantityleft, expirydate FROM inventory_batches WHERE batchid = %s",
                (batch_id,),
            ).fetchone()
        if not batch or batch["expirydate"] <= date.today():
            raise ValueError("That batch is unavailable or expired.")
        new_quantity = int(cart.get(str(batch_id), 0)) + quantity
        if new_quantity > batch["quantityleft"]:
            raise ValueError(f"Only {batch['quantityleft']} units are currently available.")
        cart[str(batch_id)] = new_quantity
        request.session["cart"] = cart
        return redirect("/sales", notice="Item added to the basket.")
    except (ValueError, PermissionDenied) as exc:
        return redirect("/sales", error=str(exc))


@app.post("/sales/cart/remove")
async def sales_remove(request: Request) -> Response:
    require_role(request, "Admin", "Cashier")
    form = await request.form()
    try:
        check_csrf(request, form)
        cart = dict(request.session.get("cart", {}))
        cart.pop(str(int(str(form.get("batchid", "")))), None)
        request.session["cart"] = cart
        return redirect("/sales", notice="Item removed.")
    except (ValueError, PermissionDenied) as exc:
        return redirect("/sales", error=str(exc))


@app.post("/sales/cart/clear")
async def sales_clear(request: Request) -> Response:
    require_role(request, "Admin", "Cashier")
    form = await request.form()
    try:
        check_csrf(request, form)
    except PermissionDenied as exc:
        return redirect("/sales", error=str(exc))
    request.session["cart"] = {}
    return redirect("/sales", notice="Basket cleared.")


@app.post("/sales/complete")
async def sales_complete(request: Request) -> Response:
    user = require_role(request, "Admin", "Cashier")
    form = await request.form()
    try:
        check_csrf(request, form)
    except PermissionDenied as exc:
        return redirect("/sales", error=str(exc))
    method = str(form.get("paymentmethod", ""))
    if method not in {"Cash", "Mobile Money"}:
        return redirect("/sales", error="Choose Cash or Mobile Money.")
    cart = request.session.get("cart", {})
    if not cart:
        return redirect("/sales", error="Add at least one item before completing a sale.")
    try:
        with connect() as connection:
            transaction = connection.execute(
                "INSERT INTO transactions (userid, paymentmethod) VALUES (%s, %s) RETURNING transactionid",
                (user["userid"], method),
            ).fetchone()
            transaction_id = transaction["transactionid"]
            for batch_id, quantity in sorted(cart.items(), key=lambda pair: int(pair[0])):
                connection.execute(
                    "INSERT INTO sales_items (transactionid, batchid, quantitysold) VALUES (%s, %s, %s)",
                    (transaction_id, int(batch_id), int(quantity)),
                )
            receipt = connection.execute(
                "SELECT totalamount FROM transactions WHERE transactionid = %s",
                (transaction_id,),
            ).fetchone()
        request.session["cart"] = {}
        return render(
            request,
            "receipt.html",
            user,
            receipt={"id": transaction_id, "method": method, "total": receipt["totalamount"]},
        )
    except psycopg.Error as exc:
        logger.info("Checkout rejected (%s)", type(exc).__name__)
        return redirect("/sales", error="The sale could not be completed. Stock may have changed; check the basket and try again.")


@app.get("/inventory")
def inventory_page(request: Request) -> HTMLResponse:
    user = require_role(request, "Admin", "InventoryManager")
    with connect() as connection:
        drugs = connection.execute("SELECT drugid, genericname, brandname, unitprice FROM drugs ORDER BY genericname").fetchall()
        suppliers = connection.execute("SELECT supplierid, suppliername FROM suppliers ORDER BY suppliername").fetchall()
        batches = connection.execute(
            "SELECT b.batchid, d.genericname, b.batchnumber, s.suppliername, b.quantityreceived, "
            "b.quantityleft, b.mfd, b.expirydate, b.unitprice "
            "FROM inventory_batches b JOIN drugs d USING (drugid) JOIN suppliers s USING (supplierid) "
            "ORDER BY b.expirydate, b.batchid"
        ).fetchall()
    return render(
        request, "inventory.html", user, drugs=drugs, suppliers=suppliers, batches=batches,
        notice=request.query_params.get("notice"), error=request.query_params.get("error"),
    )


@app.post("/inventory/batches")
async def inventory_create(request: Request) -> Response:
    require_role(request, "Admin", "InventoryManager")
    form = await request.form()
    try:
        check_csrf(request, form)
        drug_id = int(str(form.get("drugid", "")))
        supplier_id = int(str(form.get("supplierid", "")))
        batch_number = clean_text(str(form.get("batchnumber", "")), "Batch number")
        quantity = int(str(form.get("quantityreceived", "")))
        if quantity <= 0:
            raise ValueError("Quantity must be a whole number above zero.")
        price = as_money(str(form.get("unitprice", "")), "Unit price")
        mfd = date.fromisoformat(str(form.get("mfd", "")))
        expiry = date.fromisoformat(str(form.get("expirydate", "")))
        if expiry <= mfd:
            raise ValueError("Expiry date must be after the manufacture date.")
        if expiry <= date.today():
            raise ValueError("The batch must not already be expired.")
        with connect() as connection:
            connection.execute(
                "INSERT INTO inventory_batches (drugid, supplierid, batchnumber, quantityreceived, quantityleft, mfd, expirydate, unitprice) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
                (drug_id, supplier_id, batch_number, quantity, quantity, mfd, expiry, price),
            )
        return redirect("/inventory", notice=f"Batch {batch_number} was recorded.")
    except (ValueError, TypeError, PermissionDenied) as exc:
        return redirect("/inventory", error=str(exc))
    except psycopg.Error as exc:
        logger.info("Inventory insert rejected (%s)", type(exc).__name__)
        return redirect("/inventory", error="Batch could not be saved. Check that the selected drug and supplier exist and the batch number is unique.")


@app.get("/records/{entity}")
def records_page(request: Request, entity: str, edit_id: int | None = None) -> HTMLResponse:
    config = RECORDS.get(entity)
    if config is None:
        return render(request, "message.html", error="Page not found.", status_code=404)
    user = require_role(request, *config["roles"])
    with connect() as connection:
        rows = connection.execute(config["list_sql"]).fetchall()
        categories = connection.execute("SELECT categoryid, categoryname FROM categories ORDER BY categoryname").fetchall()
        record = None
        if edit_id:
            record = connection.execute(
                f"SELECT * FROM {config['table']} WHERE {config['pk']} = %s", (edit_id,)
            ).fetchone()
            if record is None:
                return render(request, "message.html", user, error="That record could not be found.", status_code=404)
    return render(
        request,
        "records.html",
        user,
        config=config,
        entity=entity,
        rows=rows,
        categories=categories,
        record=record,
        notice=request.query_params.get("notice"),
        error=request.query_params.get("error"),
    )


@app.post("/records/{entity}/save")
async def records_save(request: Request, entity: str) -> Response:
    config = RECORDS.get(entity)
    if config is None:
        return render(request, "message.html", error="Page not found.", status_code=404)
    require_role(request, *config["roles"])
    form = await request.form()
    destination = f"/records/{entity}"
    try:
        check_csrf(request, form)
        values: list[Any] = []
        columns: list[str] = []
        for column, label, kind, required in config["fields"]:
            raw = str(form.get(column, ""))
            if kind == "category":
                value = int(raw)
            elif kind == "unit":
                value = clean_text(raw, label)
                if value not in {"tablets", "capsules", "syrup", "injection", "cream"}:
                    raise ValueError("Choose a unit from the available options.")
            elif kind == "number":
                value = as_money(raw, label)
            else:
                value = clean_text(raw, label, required=required)
            columns.append(column)
            values.append(value)
        raw_id = str(form.get("record_id", "")).strip()
        with connect() as connection:
            if raw_id:
                assignments = ", ".join(f"{column} = %s" for column in columns)
                connection.execute(
                    f"UPDATE {config['table']} SET {assignments} WHERE {config['pk']} = %s",
                    (*values, int(raw_id)),
                )
                notice = f"{ {'drugs': 'Drug', 'suppliers': 'Supplier', 'categories': 'Category'}[entity] } updated."
            else:
                placeholders = ", ".join(["%s"] * len(columns))
                connection.execute(
                    f"INSERT INTO {config['table']} ({', '.join(columns)}) VALUES ({placeholders})",
                    values,
                )
                notice = f"{ {'drugs': 'Drug', 'suppliers': 'Supplier', 'categories': 'Category'}[entity] } added."
        return redirect(destination, notice=notice)
    except (ValueError, TypeError) as exc:
        return redirect(destination, error=str(exc))
    except PermissionDenied as exc:
        return redirect(destination, error=str(exc))
    except psycopg.Error as exc:
        logger.info("Record save rejected for %s (%s)", entity, type(exc).__name__)
        return redirect(destination, error="That record could not be saved. Check required fields and make sure names or identifiers are not duplicated.")


@app.get("/catalogue")
def catalogue_page(request: Request, q: str = "") -> HTMLResponse:
    user = require_role(request, "Pharmacist")
    search = f"%{q.strip()}%"
    with connect() as connection:
        rows = connection.execute(
            "SELECT d.genericname, d.brandname, c.categoryname, d.unitmeasure, d.unitprice, "
            "COALESCE(SUM(b.quantityleft) FILTER (WHERE b.expirydate > CURRENT_DATE), 0)::integer AS sellable_stock "
            "FROM drugs d JOIN categories c USING (categoryid) LEFT JOIN inventory_batches b USING (drugid) "
            "WHERE (d.genericname ILIKE %s OR COALESCE(d.brandname, '') ILIKE %s OR c.categoryname ILIKE %s) "
            "GROUP BY d.drugid, c.categoryname ORDER BY d.genericname",
            (search, search, search),
        ).fetchall()
    return render(request, "catalogue.html", user, rows=rows, search=q)


@app.get("/stock")
def stock_page(request: Request, q: str = "", hide_expired: bool = False, hide_empty: bool = False) -> HTMLResponse:
    user = require_role(request, "Pharmacist")
    search = f"%{q.strip()}%"
    with connect() as connection:
        rows = connection.execute(
            "SELECT d.genericname, b.batchnumber, s.suppliername, b.quantityleft, b.expirydate "
            "FROM inventory_batches b JOIN drugs d USING (drugid) JOIN suppliers s USING (supplierid) "
            "WHERE (d.genericname ILIKE %s OR b.batchnumber ILIKE %s OR s.suppliername ILIKE %s) "
            "AND (NOT %s OR b.expirydate > CURRENT_DATE) AND (NOT %s OR b.quantityleft > 0) "
            "ORDER BY d.genericname, b.expirydate, b.batchid",
            (search, search, search, hide_expired, hide_empty),
        ).fetchall()
    return render(request, "stock.html", user, rows=rows, search=q, hide_expired=hide_expired, hide_empty=hide_empty)


@app.get("/reports")
def reports_page(request: Request) -> HTMLResponse:
    user = require_role(request, "Admin", "InventoryManager", "Pharmacist")
    with connect() as connection:
        daily = connection.execute(
            "SELECT local_day AS day, COUNT(*) AS sales, SUM(totalamount) AS revenue FROM ("
            "SELECT (timestamp AT TIME ZONE current_setting('TIMEZONE'))::date AS local_day, totalamount "
            "FROM transactions) t GROUP BY local_day ORDER BY local_day"
        ).fetchall()
        payments = connection.execute(
            "SELECT paymentmethod, COUNT(*) AS sales, SUM(totalamount) AS revenue "
            "FROM transactions GROUP BY paymentmethod ORDER BY paymentmethod"
        ).fetchall()
        stocks = connection.execute(
            "SELECT d.genericname, COALESCE(SUM(b.quantityleft) FILTER (WHERE b.expirydate > CURRENT_DATE), 0)::integer AS stock "
            "FROM drugs d LEFT JOIN inventory_batches b USING (drugid) "
            "GROUP BY d.drugid ORDER BY stock, d.genericname"
        ).fetchall()
        sellers = connection.execute(
            "SELECT d.genericname, SUM(si.quantitysold)::integer AS quantity, SUM(si.subtotal) AS revenue "
            "FROM sales_items si JOIN inventory_batches b USING (batchid) JOIN drugs d USING (drugid) "
            "GROUP BY d.drugid ORDER BY quantity DESC, d.genericname LIMIT 10"
        ).fetchall()
        expiry = connection.execute(
            "SELECT d.genericname, b.batchnumber, b.quantityleft, b.expirydate, "
            "(b.expirydate - CURRENT_DATE)::integer AS days_left, b.quantityleft * b.unitprice AS value "
            "FROM inventory_batches b JOIN drugs d USING (drugid) "
            "WHERE b.quantityleft > 0 AND b.expirydate <= CURRENT_DATE + INTERVAL '90 days' "
            "ORDER BY b.expirydate, d.genericname"
        ).fetchall()
    total_revenue = sum((row["revenue"] or Decimal("0") for row in daily), Decimal("0"))
    total_sales = sum(row["sales"] for row in daily)
    best_day = max(daily, key=lambda row: row["revenue"] or Decimal("0"), default=None)
    payment_total = sum((row["revenue"] or Decimal("0") for row in payments), Decimal("0"))
    best_payment = max(payments, key=lambda row: row["revenue"] or Decimal("0"), default=None)
    expired_value = sum((row["value"] for row in expiry if row["days_left"] <= 0), Decimal("0"))
    soon_value = sum((row["value"] for row in expiry if row["days_left"] > 0), Decimal("0"))
    return render(
        request, "reports.html", user,
        daily=daily, payments=payments, stocks=stocks, sellers=sellers, expiry=expiry,
        total_revenue=total_revenue, total_sales=total_sales, best_day=best_day,
        avg_sale=(total_revenue / total_sales if total_sales else Decimal("0")),
        payment_total=payment_total, best_payment=best_payment,
        expired_value=expired_value, soon_value=soon_value,
        max_stock=max((row["stock"] for row in stocks), default=0),
    )


@app.get("/users")
def users_page(request: Request, edit_id: int | None = None) -> HTMLResponse:
    user = require_role(request, "Admin")
    with connect() as connection:
        users = connection.execute("SELECT userid, fullname, username, role FROM users ORDER BY fullname").fetchall()
        record = connection.execute(
            "SELECT userid, fullname, username, role FROM users WHERE userid = %s", (edit_id,)
        ).fetchone() if edit_id else None
    return render(
        request, "users.html", user, users=users, roles=ROLES, record=record,
        notice=request.query_params.get("notice"), error=request.query_params.get("error"),
    )


@app.post("/users/save")
async def users_save(request: Request) -> Response:
    user = require_role(request, "Admin")
    form = await request.form()
    try:
        check_csrf(request, form)
        fullname = clean_text(str(form.get("fullname", "")), "Full name")
        username = clean_text(str(form.get("username", "")), "Username")
        role = str(form.get("role", ""))
        if role not in ROLES:
            raise ValueError("Choose a valid role.")
        password = str(form.get("password", ""))
        confirmation = str(form.get("password_confirmation", ""))
        raw_id = str(form.get("record_id", "")).strip()
        if raw_id and int(raw_id) == user["userid"] and role != "Admin":
            raise ValueError("You cannot remove your own Admin role.")
        if not raw_id and not password:
            raise ValueError("A password is required for a new user.")
        if password or confirmation:
            if password != confirmation:
                raise ValueError("The passwords do not match.")
            if len(password) < 6:
                raise ValueError("Use a password with at least 6 characters.")
        with connect() as connection:
            if raw_id:
                if password:
                    connection.execute(
                        "UPDATE users SET fullname=%s, username=%s, role=%s, password=%s WHERE userid=%s",
                        (fullname, username, role, hash_password(password), int(raw_id)),
                    )
                else:
                    connection.execute(
                        "UPDATE users SET fullname=%s, username=%s, role=%s WHERE userid=%s",
                        (fullname, username, role, int(raw_id)),
                    )
            else:
                connection.execute(
                    "INSERT INTO users (fullname, username, role, password) VALUES (%s, %s, %s, %s)",
                    (fullname, username, role, hash_password(password)),
                )
        return redirect("/users", notice="User saved.")
    except (ValueError, TypeError, PermissionDenied) as exc:
        return redirect("/users", error=str(exc))
    except psycopg.Error as exc:
        logger.info("User save rejected (%s)", type(exc).__name__)
        return redirect("/users", error="User could not be saved. The username may already be in use.")
