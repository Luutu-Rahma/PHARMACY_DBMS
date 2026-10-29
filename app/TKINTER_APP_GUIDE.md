# Getting started with the PharmaFlow desktop app

The Tkinter desktop interface remains available alongside the FastAPI browser app. The Python UI now connects to PostgreSQL using the same `DATABASE_URL` configuration as the web UI; the original MySQL SQL scripts and XAMPP batch setup remain unchanged for the legacy database version.

## First-time setup

1. Install Python 3.10+ and create a virtual environment from the repository root.
2. Install the shared packages with `python -m pip install -r requirements.txt`.
3. Create a Supabase PostgreSQL project, copy `.env.example` to `.env`, and set the PostgreSQL `DATABASE_URL` and a private `SESSION_SECRET`.
4. Follow [the Supabase setup guide](../docs/FASTAPI_SUPABASE_SETUP.md) to initialize the PostgreSQL schema, optionally load demo data, and verify database connectivity.
5. In VS Code, install the Microsoft Python extension and select the interpreter inside `.venv`. SQLTools with a PostgreSQL driver is optional and is only needed if you want to explore the database in VS Code.
6. Start the desktop interface from the repository root:

   ```bash
   python app/login.py
   ```

The database must be reachable while using the app. It does not initialize or seed the database automatically.

## Demo account

After loading the optional development seed, use `rahma` / `Lrahma@123`. The other demonstration accounts are listed in the Supabase setup guide. Change or replace all demo accounts before using real pharmacy data.

## Screens

Your role controls which screens are available: Sales; Inventory; Drugs, Suppliers and Categories; Reports; Drug Catalogue; Stock by Batch; and Admin-only User Management. The web version offers matching workflows in a browser.

## Safety note

Do not use the legacy `setup.bat` or `sql/00_reset.sql` on valuable MySQL data. Those legacy MySQL files are separate from the Supabase PostgreSQL setup under `sql/postgres/`. Never share or commit `.env` or database credentials.
