import os
import tkinter as tk
from tkinter import messagebox
import mysql.connector

# Connection settings (change in one place).
# The database password is NOT stored in the code. Set it in your terminal
# before running (PowerShell):   $env:PF_DB_PASSWORD = "Admin@123"
DB = dict(
    host=os.environ.get("PF_DB_HOST", "localhost"),
    user=os.environ.get("PF_DB_USER", "pf_admin"),
    password=os.environ.get("PF_DB_PASSWORD", ""),
    database="pharmacy_sales_and_inventory_db",
)

# Menu items shown per role
MENUS = {
    "Admin": ["Sales", "Inventory", "Drugs & Suppliers", "Reports", "Users"],
    "InventoryManager": ["Inventory", "Drugs & Suppliers", "Reports"],
    "Pharmacist": ["View Drugs", "View Stock", "Reports"],
    "Cashier": ["Sales"],
}


def check_login(username, password):
    """Return (UserID, FullName, Role) if valid, else None."""
    con = mysql.connector.connect(**DB)
    try:
        cur = con.cursor()
        # The typed password is hashed with SHA-256 and compared with the
        # hash stored in USERS (03_seed.sql stores SHA2 hashes).
        # %s placeholders keep user input separate from the SQL (no injection).
        cur.execute(
            "SELECT UserID, FullName, `Role` FROM USERS "
            "WHERE UserName=%s AND Password=SHA2(%s,256)",
            (username, password),
        )
        return cur.fetchone()
    finally:
        con.close()


class MenuWindow(tk.Toplevel):
    def __init__(self, master, user):
        super().__init__(master)
        self.user = user
        user_id, full_name, role = user
        self.title("Pharmacy System - Main Menu")
        self.geometry("360x420")
        tk.Label(self, text=f"Welcome, {full_name}", font=("Arial", 14, "bold")).pack(pady=(20, 2))
        tk.Label(self, text=f"Role: {role}").pack(pady=(0, 15))
        for item in MENUS.get(role, []):
            tk.Button(self, text=item, width=26, height=2,
                      command=lambda i=item: self.open_item(i)).pack(pady=4)
        tk.Button(self, text="Logout", width=26, command=self.logout).pack(pady=(20, 0))
        self.protocol("WM_DELETE_WINDOW", self.logout)

    def open_item(self, item):
        # Placeholder: each form gets connected here later
        messagebox.showinfo(item, f"{item} form coming soon")

    def logout(self):
        self.destroy()
        self.master.deiconify()


class LoginWindow(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Pharmacy System - Login")
        self.geometry("320x240")
        self.resizable(False, False)
        tk.Label(self, text="Pharmacy Login", font=("Arial", 16, "bold")).pack(pady=15)
        tk.Label(self, text="Username").pack()
        self.user_entry = tk.Entry(self, width=28)
        self.user_entry.pack(pady=3)
        tk.Label(self, text="Password").pack()
        self.pass_entry = tk.Entry(self, width=28, show="*")
        self.pass_entry.pack(pady=3)
        tk.Button(self, text="Login", width=15, command=self.login).pack(pady=15)
        self.bind("<Return>", lambda e: self.login())
        self.user_entry.focus()

    def login(self):
        username = self.user_entry.get().strip()
        password = self.pass_entry.get()
        if not username or not password:
            messagebox.showwarning("Missing details", "Enter username and password.")
            return
        try:
            user = check_login(username, password)
        except mysql.connector.Error as e:
            messagebox.showerror("Database error", str(e))
            return
        if user is None:
            messagebox.showerror("Login failed", "Wrong username or password.")
            self.pass_entry.delete(0, tk.END)
            return
        self.pass_entry.delete(0, tk.END)
        self.withdraw()
        MenuWindow(self, user)


if __name__ == "__main__":
    LoginWindow().mainloop()