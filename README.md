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
  03_seed.sql                 sample data (run after 02)
  04_queries_reports.sql      reports for each project objective
  05_roles_privileges.sql     one MySQL account per role
  06_tests.sql                statements that are SUPPOSED to fail
docs/                         requirements, abstract, data dictionary, ERD
setup.bat                     one-click rebuild for XAMPP on Windows
```

## Quick start
1. Start **MySQL** in the XAMPP Control Panel.
2. Run `setup.bat` (or run the files in order 00, 01, 02, 03, 05 with
   `C:\xampp\mysql\bin\mysql.exe -u root < sql\<file>.sql`).
3. In VS Code copy `.vscode/settings.example.json` to `.vscode/settings.json`
   (this file is git-ignored), then connect with SQLTools.
4. Open `sql/04_queries_reports.sql` and run the queries.

## Desktop application
The project also includes a Tkinter desktop app for sales, inventory, drug and supplier records, user management, and reports. For first-time setup—including Python packages, database preparation, optional VS Code extensions, and how to launch the app—see [docs/TKINTER_APP_GUIDE.md](docs/TKINTER_APP_GUIDE.md).

## Key rules enforced by the database
- Only 4 valid roles; only `Cash` or `Mobile Money` payments.
- Expiry date must be after manufacture date; stock can never go negative.
- A sale from an expired batch or beyond available stock is rejected.
- Each sale line deducts stock and updates the receipt total automatically.
- Every transaction belongs to exactly one user (accountability).
