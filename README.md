# PharmaFlow - Pharmacy Inventory and Sales Management System (DBMS)
**Group 16** | MySQL / MariaDB (XAMPP) | VS Code

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
  03_seed.sql                 core sample data: 4 users, 3 drugs, 5 batches, 2 sales (run after 02)
  03b_seed_extra.sql          extra sample data: 15 drugs, 23 batches, 20 sales over ~18 days
  04_queries_reports.sql      reports for each project objective
  05_roles_privileges.sql     one MySQL account per role (+ a login-only account)
  06_tests.sql                statements that are SUPPOSED to fail
app/                          Python/Tkinter desktop app (login, sales, inventory, reports ...)
docs/                         requirements, abstract, data dictionary, ERD
setup.bat                     one-click rebuild for XAMPP on Windows
requirements.txt              Python packages the app needs
```

## Quick start
1. Start **MySQL** in the XAMPP Control Panel.
2. Run `setup.bat` (it runs 00, 01, 02, 03, 03b and 05 in order using
   `C:\xampp\mysql\bin\mysql.exe -u root`). Re-run it any time to reset the data.
3. In VS Code copy `.vscode/settings.example.json` to `.vscode/settings.json`
   (this file is git-ignored), then connect with SQLTools.
4. Open `sql/04_queries_reports.sql` and run the queries.
   `sql/06_tests.sql` contains statements that are SUPPOSED to fail (screenshot the errors).

## Running the desktop app
Needs Python 3.9+ (Tkinter is included with the Windows installer) and the database from the steps above.
```powershell
pip install -r requirements.txt
cd app
python login.py
```
Connection settings are in `app/db.py`. The host and database name can be overridden with the
environment variables `PF_DB_HOST` and `PF_DB_NAME`.

### How role security works
The app uses a different MySQL account for each role, so MySQL itself (not just the menus) decides
what a user may do. Accounts are created by `sql/05_roles_privileges.sql`.

1. At the login screen the app connects as `pf_login`, an account that can ONLY read the `USERS` table.
2. It checks the username and SHA2 password hash.
3. On success it switches to the account for that user's role (`db.set_role(role)`), and every screen
   from then on runs with only that role's privileges. Logging out switches back to `pf_login`.

| Role | MySQL account | Can do | Cannot do |
|---|---|---|---|
| Admin | pf_admin | everything, including user management | - |
| InventoryManager | pf_inventory | receive/edit batches, drugs, suppliers, categories; read sales for reports | record sales, touch users |
| Pharmacist | pf_pharmacist | read drugs, stock, suppliers and sales | change anything |
| Cashier | pf_cashier | read drugs/batches, record sales (stock and totals update via triggers) | edit prices or stock, delete receipts, read users |

If you change grants in `05_roles_privileges.sql`, re-run `setup.bat` so the accounts are rebuilt.

Demo logins (created by `03_seed.sql` - change them before any real use):

| Username | Password | Role | Menu |
|---|---|---|---|
| rahma | Lrahma@123 | Admin | Sales, Inventory, Drugs & Suppliers, Reports, Users |
| nicholas | Onicho@123 | InventoryManager | Inventory, Drugs & Suppliers, Reports |
| breiline | Mbreiline@123 | Pharmacist | View Drugs, View Stock, Reports |
| raudha | Nraudha@123 | Cashier | Sales |

## Key rules enforced by the database
- Only 4 valid roles; only `Cash` or `Mobile Money` payments.
- Expiry date must be after manufacture date; stock can never go negative.
- A sale from an expired batch or beyond available stock is rejected.
- Each sale line deducts stock and updates the receipt total automatically.
- Every transaction belongs to exactly one user (accountability).
