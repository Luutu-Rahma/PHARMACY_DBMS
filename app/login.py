import tkinter as tk
from tkinter import messagebox
import mysql.connector
from db import connect
from sales_form import SalesForm
from inventory_form import InventoryForm
from drugs_suppliers_form import DrugsSuppliersForm
from reports_form import ReportsForm
from view_forms import ViewDrugsForm, ViewStockForm

# Menu items shown per role
MENUS = {
    "Admin": ["Sales", "Inventory", "Drugs & Suppliers", "Reports", "Users"],
    "InventoryManager": ["Inventory", "Drugs & Suppliers", "Reports"],
    "Pharmacist": ["View Drugs", "View Stock", "Reports"],
    "Cashier": ["Sales"],
}


def check_login(username, password):
    """Return (UserID, FullName, Role) if valid, else None."""
    con = connect()
    try:
        cur = con.cursor()
        cur.execute(
            "SELECT UserID, FullName, Role FROM users "
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
        if item == "Sales":
            SalesForm(self, self.user)
        elif item == "Inventory":
            InventoryForm(self, self.user)
        elif item == "Drugs & Suppliers":
            DrugsSuppliersForm(self,self.user)
        elif item =="Reports":
            ReportsForm(self,self.user)
        elif item == "View Drugs":
            ViewDrugsForm(self, self.user)
        elif item == "View Stock":
            ViewStockForm(self, self.user)
        else:
            # Placeholder: other forms get connected here later
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
