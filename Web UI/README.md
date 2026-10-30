# PharmaFlow Web UI

An independent FastAPI/Jinja2 web interface for the existing PharmaFlow MySQL schema. All new application files are inside `Web UI/`; the Tkinter app and repository files are unchanged. The application connects only to the Aiven host specified by `DATABASE_URL` and refuses localhost/other MySQL hosts.

## Requirements

- Python 3.10 or later (tested with the workspace Python 3.14 environment).
- The existing Aiven MySQL service, database, schema, tables, and sale triggers.
- The CA certificate downloaded from the Aiven service dashboard.
- Network access from this machine to the Aiven hostname and port.

## Configure Aiven securely

1. In `Web UI/`, copy `.env.example` to `.env`. This local `.env` is excluded by `Web UI/.gitignore`; never commit or share it. The app can read the existing repository-root `.env` as a fallback for `DATABASE_URL`, but `Web UI/.env` is authoritative when set.
2. Copy the actual Aiven service URI from the Aiven dashboard/local secure configuration into `DATABASE_URL`. Use the real Aiven hostname, port, user, password, and intended database. URL-encode special characters in the username/password. Keep the existing `ssl-mode=REQUIRED` parameter. Do not replace it with `localhost`. The implementation rejects hosts that are not Aiven.
3. Download the service CA certificate from Aiven and save it as `Web UI/ca.pem`. Set `AIVEN_CA_CERT=ca.pem` (or an absolute local path). The connector uses that CA and verifies the server hostname and certificate. TLS verification is never disabled.
4. Replace `SESSION_SECRET` with a unique random secret of at least 32 characters. Keep `COOKIE_SECURE=false` for local HTTP only. Set it to `true` when the app is served over HTTPS.
5. Create a dedicated Aiven application account rather than using `avnadmin` permanently. Grant only the operations this app needs (no `DELETE`, `DROP`, `CREATE`, or administrative privileges), substituting the actual database name:

   ```sql
   CREATE USER 'pharmaflow_web'@'%' IDENTIFIED BY 'use-a-unique-secret';
   GRANT SELECT, INSERT, UPDATE ON `your_database`.USERS TO 'pharmaflow_web'@'%';
   GRANT SELECT, INSERT, UPDATE ON `your_database`.CATEGORIES TO 'pharmaflow_web'@'%';
   GRANT SELECT, INSERT, UPDATE ON `your_database`.SUPPLIERS TO 'pharmaflow_web'@'%';
   GRANT SELECT, INSERT, UPDATE ON `your_database`.DRUGS TO 'pharmaflow_web'@'%';
   GRANT SELECT, INSERT, UPDATE ON `your_database`.INVENTORY_BATCHES TO 'pharmaflow_web'@'%';
   GRANT SELECT, INSERT, UPDATE ON `your_database`.TRANSACTIONS TO 'pharmaflow_web'@'%';
   GRANT SELECT, INSERT, UPDATE ON `your_database`.SALES_ITEMS TO 'pharmaflow_web'@'%';
   ```

   `CREATE USER` / `GRANT` syntax may be restricted by your Aiven plan and should be run by an authorized database administrator. Use the existing trigger definers; the web app does not update stock or totals itself after a sale trigger runs.

## Inspect and initialize the Aiven database (manual, non-destructive)

The app never creates tables, seeds records, resets a database, or runs SQL at startup. First use the Aiven query editor or a TLS-enabled MySQL client with the configured database selected:

```sql
SELECT DATABASE();
SHOW TABLES;
SHOW TRIGGERS;
SHOW PROCEDURE STATUS WHERE Db = DATABASE();
```

Compare the existing objects against the source definitions in `../sql/01_schema.sql` and `../sql/02_triggers_procedures.sql`. If the seven tables and the two sale triggers already exist, do not initialize them again. If the intended Aiven database is empty, the safe order is:

1. Run `schema.sql` from this folder while the intended database is selected. This is additive `CREATE TABLE IF NOT EXISTS` DDL; it never creates or selects a database.
2. If and only if both `trg_sale_before_insert` and `trg_sale_after_insert` are absent, run `triggers.sql` from this folder. It intentionally does not drop existing triggers. If only one trigger exists, stop and have an administrator reconcile the definition rather than running the file unchanged.
3. If and only if `sp_fifo_batches` is absent, run `fifo_procedure.sql`.
4. Add account data through the Admin page or your approved account process. This application does not create demo users or insert sample data automatically.

If the database has no users yet, create the first Admin manually in the Aiven query editor after the `USERS` table exists. Replace every placeholder before executing; the password is hashed in MySQL and is not stored as plaintext:

```sql
INSERT INTO USERS (FullName, UserName, Password, `Role`)
VALUES ('Your full name', 'your_admin_username', SHA2('choose-a-new-unique-password', 256), 'Admin');
```

Then sign in with that username and password and add other staff in User management. Do not use any demo credentials or passwords from the repository seed script for a real deployment.

These new scripts are a MySQL-compatible, non-destructive adaptation of the checked-in table/trigger/procedure definitions. The original scripts contain `USE pharmacy_sales_and_inventory_db`, and the reset script is destructive; do not run `sql/00_reset.sql` on Aiven. The original seed script has demo users, fixed IDs, and sample transactions. It is not run by this app and should only be considered for a deliberately empty demo database after reviewing it and adapting the selected database manually. Do not run it against existing production data.

All operational tables must use InnoDB for a sale's transaction and trigger-based stock updates to roll back together. The sale page verifies both existing triggers and InnoDB before creating a transaction.

## Install, test the connection, and run

From the repository root:

```bash
python3 -m venv "Web UI/.venv"
"Web UI/.venv/bin/python" -m pip install -r "Web UI/requirements.txt"
cp "Web UI/.env.example" "Web UI/.env"
# Edit Web UI/.env and place Aiven's CA certificate at Web UI/ca.pem
"Web UI/.venv/bin/python" "Web UI/main.py" --check-db
"Web UI/.venv/bin/python" -m pytest -q "Web UI/tests"
"Web UI/.venv/bin/python" "Web UI/main.py"
```

Open <http://127.0.0.1:8000>. `--check-db` tests TLS connection, executes `SELECT 1`, and confirms MySQL selected the configured database. Errors are sanitized and never include a connection string or password. If network restrictions, CA configuration, credentials, or schema prevent connection, the app reports the problem and never falls back to local MySQL.

## Implemented pages and behavior

- Sign in/out using the existing `SHA2(password, 256)` verifier; no plaintext password is stored or displayed.
- Role-based server authorization and navigation: Admin, InventoryManager, Pharmacist, and Cashier permissions match `app/login.py`.
- Role-aware dashboard with live stock, expiry and (Admin) daily sales summary.
- Sales basket with batch availability, quantity merging, removal/clear, Cash/Mobile Money, UGX subtotal/total, receipt, authenticated cashier attribution, CSRF, a sale nonce replay guard, transaction row locks, and rollback. Existing MySQL triggers alone set line subtotals, deduct stock, and update transaction totals.
- Inventory batch receiving and list with manufacture/expiry validation, unique drug/batch behavior, expiry warnings, and supplier/drug lookups.
- Admin/InventoryManager create/update for drugs, suppliers, and categories; no delete controls. Fields mirror the desktop form.
- Pharmacist read-only searchable drug catalogue and stock-by-batch filters; expired batches are excluded from sellable totals; 50-unit low-stock and 90-day expiry conventions match desktop screens.
- Reports: daily sales, payment method, sellable stock, top sellers, expiry value at risk, staff accountability, and supplier deliveries. Revenue aggregates use transaction totals or line subtotals as appropriate to avoid join double-counting.
- Admin user create/update with unique usernames, supported roles, SHA-256-compatible password updates, optional blank password on edit, and protection against removing the signed-in Admin's role.
- Responsive styling, warning colors, and print-friendly sale receipt.

Session cookies are signed and HTTP-only by Starlette's session middleware, with SameSite=Lax and an eight-hour expiry. CSRF tokens protect all state-changing forms. Sale replay suppression is in-process; run the documented single local Uvicorn process (no multi-worker setting) for the nonce guard. Database account access should still be restricted to trusted operators and the local machine.

## Tests and limitations

`pytest` tests role authorization, login's legacy SHA-256 query shape, CSRF rejection, validation, Aiven-only host configuration, and safe database errors without touching or mutating a live database. MySQL trigger/transaction integration tests require a separately provisioned non-production Aiven database; this implementation does not run destructive integration tests. Aiven connectivity was not tested until the local CA certificate and a non-placeholder session secret are configured.
