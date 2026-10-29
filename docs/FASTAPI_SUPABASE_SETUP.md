# PharmaFlow Web App: Supabase setup

This guide starts the local FastAPI application and connects it to Supabase PostgreSQL. It does not publish the web server. The existing MySQL SQL scripts and XAMPP setup remain in place; the web app and the converted Tkinter app use the separate PostgreSQL scripts under `sql/postgres/`.

## Requirements

- Python 3.10 or later (3.11+ recommended).
- A Supabase project with access to its PostgreSQL connection URI.
- The database must allow remote connections from your network. Supabase may offer a direct endpoint and pooled/Supavisor endpoint. Use the URI from the Supabase dashboard; if direct IPv6 is unavailable on your network, use the dashboard's session pooler URI.
- VS Code is optional. The FastAPI UI runs in a browser.

## 1. Install packages

From the repository root:

**Linux/macOS**

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

**Windows PowerShell**

```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

In VS Code, install the Microsoft **Python** extension and choose the interpreter inside `.venv`. SQLTools and its PostgreSQL driver are optional; they are not required to run the application.

## 2. Configure Supabase connection

1. In Supabase, open **Project Settings → Database** and copy a PostgreSQL connection URI for the server-side application. Use the pooler address shown by Supabase if required by your network.
2. Copy `.env.example` to `.env` in the repository root.
3. Set `DATABASE_URL` to the copied URI. Ensure the URI has SSL enabled (`sslmode=require` at minimum). The app adds `sslmode=require` for non-local hosts if the parameter is missing.
4. Set `SESSION_SECRET` to a long, unique random value. Do not copy the example value into production.
5. Keep `COOKIE_SECURE=false` for local HTTP use. Set `COOKIE_SECURE=true` only when the app is behind HTTPS.
6. Never send `.env`, the database password, or a Supabase service-role key to Git or the browser. The browser never receives `DATABASE_URL`.

The repository intentionally does not include credentials. No Supabase connection test has been assumed or run unless you configure a real URI and run the check below.

## 3. Initialize the PostgreSQL schema

Run this explicitly from the repository root after setting `.env`:

```bash
python -m web.init_db
```

This applies `sql/postgres/01_schema.sql` and `sql/postgres/02_functions_triggers.sql`. It creates missing tables and replaces the pharmacy triggers/functions. It does **not** drop or reset a database. Review the SQL files before running against a shared project. The scripts use lowercase unquoted PostgreSQL names; the original MySQL scripts are unchanged.

Optionally create a non-login role for application grants by running `sql/postgres/04_roles_privileges.sql` as the database owner. The SQL creates/grants a `NOLOGIN` group role; create a login role through Supabase's trusted admin facilities and grant it membership only if that matches your operational setup. Supabase-managed role restrictions may mean role creation must be handled through the dashboard or SQL editor. Do not run the app with a database superuser in a publicly hosted deployment.

## 4. Seed development data (optional)

The seed is only for a fresh development database that has no existing users. Run:

```bash
python -m web.seed_db
```

It refuses to seed if the `users` table already contains rows and never drops data. It includes the verified sample accounts from the MySQL seed and representative pharmacy records, including expired and expiring batches. Demo accounts include `rahma` / `Lrahma@123`, `nicholas` / `Onicho@123`, `breiline` / `Mbreiline@123`, `raudha` / `Nraudha@123`, and `luutu` / `luutu@123`. These are public demo credentials only; never use them for real operations. Their legacy SHA-256 digests are upgraded to Argon2id after each successful login.

The web server never initializes schema or seeds data at startup.

## 5. Check connectivity

The check is read-only and does not change the database:

```bash
python -m web.check_db
```

It displays the connected database, database role, and expected tables found. This verifies remote Supabase access only when a valid `.env` is configured. Alternatively, inspect `sql/postgres/test_connection.sql` in the Supabase SQL editor.

## 6. Run the website locally

From the repository root, with the virtual environment active and the database available:

```bash
uvicorn web.main:app --reload --host 127.0.0.1 --port 8000
```

Open <http://127.0.0.1:8000>. Stop the development server with Ctrl+C. The app uses Jinja templates, plain HTML/CSS and minimal JavaScript.

## 7. Run tests

```bash
python -m pytest -q
```

The unit and smoke tests exercise password verification, templates, health checks, and unauthenticated route behavior without a database. PostgreSQL trigger/checkout integration tests require a separate isolated PostgreSQL test database; do not point test setup at a shared Supabase project. Remote schema, trigger execution, and production-pooler connectivity remain unverified until explicitly tested against the supplied Supabase project.

## Application roles

- **Admin:** sales, inventory, catalogue management, reports, user management.
- **InventoryManager:** inventory, drugs/suppliers/categories, reports.
- **Pharmacist:** read-only drug catalogue, stock, reports.
- **Cashier:** sales.

The application enforces role checks on routes, not just in navigation. All web sessions contain only the user ID; the current name and role are looked up from PostgreSQL.

## Tkinter desktop app

The existing Tkinter UI stays available. It now also connects to PostgreSQL using `DATABASE_URL`; launch it from the repository root with:

```bash
python app/login.py
```

The old XAMPP instructions and the original scripts in `sql/` still describe the legacy MySQL/MariaDB version. For the Supabase-backed Tkinter UI, use `sql/postgres/` and the shared `.env` configuration.

## Troubleshooting

- **Connection timeout or DNS error:** confirm the URI host/port, network reachability, and whether to use the Supabase pooler. Do not paste credentials into messages or source code.
- **SSL error:** use the exact Supabase URI and require SSL for remote connections. Do not disable remote SSL to work around certificate problems.
- **Password authentication failure:** re-copy the database password/URI from Supabase; it is separate from application user passwords.
- **Missing table/function:** run the explicit schema initializer against the intended database, then check it with `python -m web.check_db`.
- **Legacy MySQL commands in Tkinter errors:** make sure `DATABASE_URL` points to a PostgreSQL database initialized with the `sql/postgres/` scripts and that you are using the root requirements file.

## Future public hosting (not part of this implementation)

The immediate app runs locally only. Detailed future hosting considerations are in [FUTURE_WEB_HOSTING.md](FUTURE_WEB_HOSTING.md). Supabase hosts the database, not this FastAPI web server.
