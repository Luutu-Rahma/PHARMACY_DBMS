# PharmaFlow - Pharmacy Inventory and Sales Management System (DBMS)
**Group 16** | Tkinter desktop + FastAPI web app | MySQL/MariaDB legacy scripts + Supabase PostgreSQL

| Name | Reg. No. |
|---|---|
| Luutu Rahma Namayanja | 25/U/03438/PS |
| Nambuya Raudha | 25/U/03516/PS |
| Ojambo Nicholas | 25/U/03551/PS |
| Mumbere Breiline | 25/U/03472/PS |
| Luutu Gregory Valentino | 25/U/0347 |

A database that tracks drug stock by batch and expiry date (FIFO), links every
sale to the staff member who made it, and enforces four user roles
(Admin, InventoryManager, Pharmacist, Cashier).

## Project structure
```
sql/
  00_reset.sql                (DEV ONLY) drop the database
  01_schema.sql               7 tables, keys, constraints, FIFO index
  02_triggers_procedures.sql  stock check, auto-deduction, auto totals, FIFO procedure
  03_seed.sql                 sample data (run after 02)
  04_queries_reports.sql      reports for each project objective
  05_roles_privileges.sql     one MySQL account per role
  06_tests.sql                statements that are SUPPOSED to fail
   postgres/                   PostgreSQL schema, triggers, demo seed, grants
web/                          FastAPI/Jinja2 application
app/                          Tkinter desktop application
docs/                         requirements, abstract, data dictionary, ERD
setup.bat                     one-click rebuild for XAMPP on Windows
```

## Quick start
The current Python apps use Supabase PostgreSQL. Follow [docs/FASTAPI_SUPABASE_SETUP.md](docs/FASTAPI_SUPABASE_SETUP.md) for installing dependencies, configuring `.env`, initializing the PostgreSQL schema, optionally loading demo data, and launching either UI. The older `setup.bat` and SQL scripts at the root of `sql/` are retained for the legacy MySQL/MariaDB project only; they do not initialize Supabase.

## Desktop application
The project includes the Tkinter desktop app and a separate FastAPI web interface with sales, inventory, catalogue management, reports, and user management. The original SQL scripts and XAMPP setup are retained for the legacy MySQL/MariaDB version. The current Python applications are configured for PostgreSQL through `DATABASE_URL`.

- For Supabase PostgreSQL and the FastAPI web application, follow [docs/FASTAPI_SUPABASE_SETUP.md](docs/FASTAPI_SUPABASE_SETUP.md).
- For future public hosting considerations (not deployed), see [docs/FUTURE_WEB_HOSTING.md](docs/FUTURE_WEB_HOSTING.md).
- The desktop UI is still launched with `python app/login.py`; it also uses the PostgreSQL configuration.
- For a detailed functional mapping of the original Tkinter operations to the web application, see [docs/FASTAPI_WEB_APP_PROMPT_BRIEF.md](docs/FASTAPI_WEB_APP_PROMPT_BRIEF.md).

Do not run the legacy MySQL `setup.bat` against real data. The separate `sql/postgres/` setup scripts are opt-in and do not reset the database.

## Key rules enforced by the database
- Only 4 valid roles; only `Cash` or `Mobile Money` payments.
- Expiry date must be after manufacture date; stock can never go negative.
- A sale from an expired batch or beyond available stock is rejected.
- Each sale line deducts stock and updates the receipt total automatically.
- Every transaction belongs to exactly one user (accountability).
