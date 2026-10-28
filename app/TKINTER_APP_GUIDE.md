# Getting started with the PharmaFlow desktop app

This guide explains how to prepare the database, open the desktop app, and use its main screens. You do not need to understand the SQL or Python code to follow it.

## Before you start

You will need:

- This project downloaded or cloned to your computer, and opened as a folder in VS Code.
- Python 3 installed.
- MySQL or MariaDB installed and running. XAMPP is an option on Windows; the database service must be started before opening the app.
- A working internet connection for the first-time Python package installation.

The app is a desktop program, so it opens a window on your computer. It is not a website and does not run in a browser.

## 1. Prepare VS Code

1. Install the **Python** extension published by Microsoft in VS Code. It also offers the **Pylance** language support extension; install it if VS Code recommends it.
2. Open the project folder (the folder containing `README.md`) in VS Code.
3. Open **Terminal → New Terminal**.
4. Create a private Python environment in the project folder and install the app's packages. Choose the commands for your operating system:

   **Windows PowerShell**
   ```powershell
   py -m venv .venv
   .venv\Scripts\Activate.ps1
   python -m pip install -r requirements.txt
   ```

   **Linux or macOS**
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   python -m pip install -r requirements.txt
   ```

5. If VS Code asks you to choose a Python interpreter, choose the one inside this project's `.venv` folder. If it does not ask, open the Command Palette (`Ctrl+Shift+P` or `Cmd+Shift+P` on macOS), choose **Python: Select Interpreter**, and select `.venv`.

On Linux, if creating the environment or opening the app reports that `tkinter` is missing, install the operating-system package for Tkinter (often named `python3-tk`) and try again. Tkinter is included with many Python installations, but it is not installed from `requirements.txt`.

## 2. Start the database and prepare sample data

Start the MySQL/MariaDB service before continuing. For XAMPP, start **MySQL** in the XAMPP Control Panel. Keep that service running while using the app.

The app expects a local database named `pharmacy_sales_and_inventory_db` and a database account named `pf_admin`. The setup scripts create the database structure, demo records, and account.

### Windows with the default XAMPP setup

From the project folder, run `setup.bat` (double-click it or enter `setup.bat` in the terminal). It rebuilds the database using the included scripts.

> **Important:** `setup.bat` runs `sql/00_reset.sql`, which deletes the existing `pharmacy_sales_and_inventory_db` before rebuilding it. Use this only for a new/demo installation or when you intentionally want to erase and recreate the database. Do not run it if you need to keep existing data.

The included script assumes the default XAMPP location and a MySQL `root` account with no password. If your XAMPP installation or root password differs, ask the person managing the database to adjust the setup steps rather than changing passwords at random.

### Linux, macOS, or a non-default Windows setup

Use a MySQL/MariaDB client such as the `mysql` command-line client or a database management app. Run the scripts from the project folder, in this order:

1. `sql/00_reset.sql` — only if it is safe to erase and rebuild the database.
2. `sql/01_schema.sql`
3. `sql/02_triggers_procedures.sql`
4. `sql/03_seed.sql` — adds demonstration users and sample inventory/sales.
5. `sql/05_roles_privileges.sql` — creates the database accounts used by the app's roles.

With the `mysql` command-line client, run these from the project folder, entering the MySQL root password each time it is requested:

```bash
mysql -u root -p < sql/00_reset.sql
mysql -u root -p < sql/01_schema.sql
mysql -u root -p < sql/02_triggers_procedures.sql
mysql -u root -p < sql/03_seed.sql
mysql -u root -p < sql/05_roles_privileges.sql
```

Only run the first command if you are sure it is safe to erase and rebuild the database. If you already have data to keep, do not run the reset or demo-data scripts; ask your database administrator how to configure the app for the existing database.

## 3. Optional VS Code database extensions and settings

These are useful for browsing the database, but **are not required to launch the Tkinter app**:

- Install **SQLTools** and its MySQL/MariaDB driver if you want to view or run SQL inside VS Code.
- The example connection is in `.vscode/settings.example.json`. To use it, copy it to `.vscode/settings.json` and update the connection details to match your local MySQL setup. In VS Code, the SQLTools icon lets you connect to the database.
- The example uses the database's `root` account with a blank password, which is common for a default local XAMPP installation but is not universal. Do not use that example unchanged if your database has a different password.
- `.vscode/settings.json` is ignored by Git because it may contain a local password. Never commit it or share a copy that contains credentials.

The app itself connects using the settings in `app/db.py`: host `localhost`, database user `pf_admin`, and database `pharmacy_sales_and_inventory_db`. The bundled database setup creates this account with a demo password. If your database uses different details, have the project maintainer update the app's connection settings before launching it. Do not use the bundled demo password for a real deployment.

## 4. Open the app

Make sure the database service is running, then open a VS Code terminal in the project folder and run:

```bash
python app/login.py
```

On some Linux/macOS computers, use `python3 app/login.py` instead. A login window should appear. Keep the terminal open while using the app; close the app window when finished.

### Demo login

After loading the included sample data, sign in with:

- **Username:** `rahma`
- **Password:** `Lrahma@123`

The sample data also includes `nicholas`, `breiline`, `raudha`, and `luutu`. Each account has a different role and sees a different set of screens. These are demonstration accounts and passwords; change or replace them before using any real information.

## 5. What you can do in the app

Your available buttons depend on your account role:

| Screen | What it is for |
|---|---|
| Sales | Add available, unexpired batches to a basket, choose Cash or Mobile Money, and complete a sale. The app shows a receipt and updates stock. |
| Inventory | Record a new delivery batch and review quantities and expiry dates. Red rows are expired; orange rows expire soon. |
| Drugs & Suppliers | View and add or update drugs, suppliers, and categories using the tabs. Select an existing row to edit it. |
| Reports | Review sales, payment, stock, top-seller, and expiry charts. Use **Refresh** to reload a chart and **Save chart as image** to export it. |
| View Drugs / View Stock | Search the catalogue or stock batches. Stock can be filtered to hide expired or empty batches. |
| Users | Add or update app users and assign their role. This screen is available to Admin accounts. |

Use the **Refresh** buttons after changes if a list or chart has not updated. The app checks required fields, quantities, prices, and dates and shows a message if something needs correcting.

## Troubleshooting

- **A database connection error appears:** confirm MySQL/MariaDB is running, the database exists, and the settings in `app/db.py` match the database account. The app account is `pf_admin`; the optional SQLTools connection is separate and may use a different account.
- **The login is rejected:** the demo accounts only exist after `sql/03_seed.sql` has been run. Check username/password spelling and confirm that the app is connected to the expected database.
- **A package is missing:** activate the `.venv` environment in the VS Code terminal and run `python -m pip install -r requirements.txt` again.
- **The window will not open on Linux:** install the system Tkinter package (commonly `python3-tk`) and check that you are using a desktop session that can display windows.
- **A sale fails:** only batches with stock remaining and a future expiry date can be sold. The database also prevents selling more units than a batch contains.

For help, tell the project maintainer the exact error message and which setup step you were doing. Do not send passwords or connection files.
