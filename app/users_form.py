import tkinter as tk
from tkinter import ttk, messagebox
import psycopg
from db import connect
from passwords import hash_password

ROLES = ["Admin", "InventoryManager", "Pharmacist", "Cashier"]
MIN_PASSWORD = 6


class UsersForm(tk.Toplevel):
    def __init__(self, master, user):
        super().__init__(master)
        self.user_id, self.full_name, self.role = user
        self.title("User Management")
        self.geometry("820x600")
        self.selected_id = None

        tk.Label(self, text="User Management", font=("Arial", 16, "bold")).pack(pady=(12, 6))

        form = tk.Frame(self)
        form.pack(fill="x", padx=15, pady=6)

        tk.Label(form, text="Full name *").grid(row=0, column=0, sticky="w")
        self.name_entry = tk.Entry(form, width=36)
        self.name_entry.grid(row=1, column=0, sticky="w", padx=(0, 14), pady=(0, 6))

        tk.Label(form, text="Username *").grid(row=0, column=1, sticky="w")
        self.user_entry = tk.Entry(form, width=24)
        self.user_entry.grid(row=1, column=1, sticky="w", padx=(0, 14), pady=(0, 6))

        tk.Label(form, text="Role *").grid(row=0, column=2, sticky="w")
        self.role_box = ttk.Combobox(form, state="readonly", values=ROLES, width=20)
        self.role_box.grid(row=1, column=2, sticky="w", pady=(0, 6))

        self.pass_label = tk.Label(form, text="Password *")
        self.pass_label.grid(row=2, column=0, sticky="w")
        self.pass_entry = tk.Entry(form, width=36, show="*")
        self.pass_entry.grid(row=3, column=0, sticky="w", padx=(0, 14))

        tk.Label(form, text="Confirm password").grid(row=2, column=1, sticky="w")
        self.confirm_entry = tk.Entry(form, width=24, show="*")
        self.confirm_entry.grid(row=3, column=1, sticky="w")

        btns = tk.Frame(self)
        btns.pack(fill="x", padx=15, pady=10)
        self.save_btn = tk.Button(btns, text="Add user", width=16, bg="#2e7d32", fg="white", command=self.save)
        self.save_btn.pack(side="left")
        tk.Button(btns, text="New / clear", width=12, command=self.clear).pack(side="left", padx=8)
        tk.Button(btns, text="Refresh", width=10, command=self.load_users).pack(side="left")
        self.hint = tk.Label(btns, text="Select a user below to edit. Leave password blank to keep it.")
        self.hint.pack(side="right")

        cols = ("ID", "Full name", "Username", "Role")
        self.tree = ttk.Treeview(self, columns=cols, show="headings", height=12)
        for c, w in zip(cols, (50, 260, 180, 160)):
            self.tree.heading(c, text=c)
            self.tree.column(c, width=w, anchor="w")
        self.tree.pack(fill="both", expand=True, padx=15, pady=(0, 8))
        self.tree.bind("<<TreeviewSelect>>", self.on_select)

        tk.Button(self, text="Close", width=10, command=self.destroy).pack(pady=(0, 10))
        self.load_users()

    # ---------- data ----------
    def load_users(self):
        try:
            con = connect()
            cur = con.cursor()
            cur.execute("SELECT UserID, FullName, UserName, role FROM USERS ORDER BY FullName")
            rows = cur.fetchall()
            con.close()
        except psycopg.Error as e:
            messagebox.showerror("Database error", str(e), parent=self)
            return
        self.tree.delete(*self.tree.get_children())
        for row in rows:
            self.tree.insert("", "end", values=row)

    # ---------- form ----------
    def clear(self):
        self.selected_id = None
        self.save_btn.config(text="Add user")
        self.pass_label.config(text="Password *")
        self.tree.selection_remove(self.tree.selection())
        for e in (self.name_entry, self.user_entry, self.pass_entry, self.confirm_entry):
            e.delete(0, tk.END)
        self.role_box.set("")

    def on_select(self, event=None):
        sel = self.tree.selection()
        if not sel:
            return
        uid, name, username, role = self.tree.item(sel[0], "values")
        self.selected_id = str(uid)
        self.save_btn.config(text="Update user")
        self.pass_label.config(text="New password (optional)")
        for e, val in ((self.name_entry, name), (self.user_entry, username)):
            e.delete(0, tk.END)
            e.insert(0, val)
        self.pass_entry.delete(0, tk.END)
        self.confirm_entry.delete(0, tk.END)
        self.role_box.set(role)

    def save(self):
        name = self.name_entry.get().strip()
        username = self.user_entry.get().strip()
        role = self.role_box.get()
        password = self.pass_entry.get()
        confirm = self.confirm_entry.get()

        if not name or not username or role not in ROLES:
            messagebox.showwarning("Missing details", "Full name, username and role are required.", parent=self)
            return
        adding = self.selected_id is None
        if adding and not password:
            messagebox.showwarning("Password", "Enter a password for the new user.", parent=self)
            return
        if password or confirm:
            if password != confirm:
                messagebox.showwarning("Password", "The two passwords do not match.", parent=self)
                return
            if len(password) < MIN_PASSWORD:
                messagebox.showwarning("Password", f"Use at least {MIN_PASSWORD} characters.", parent=self)
                return
        # Stop the logged-in admin from locking themselves out
        if not adding and self.selected_id == str(self.user_id) and role != "Admin":
            messagebox.showwarning("Not allowed", "You cannot remove your own Admin role.", parent=self)
            return

        con = None
        try:
            con = connect()
            cur = con.cursor()
            if adding:
                cur.execute(
                    "INSERT INTO USERS (FullName, UserName, Password, role) VALUES (%s, %s, %s, %s)",
                    (name, username, hash_password(password), role))
                done = "added"
            elif password:
                cur.execute(
                    "UPDATE USERS SET FullName=%s, UserName=%s, role=%s, Password=%s WHERE UserID=%s",
                    (name, username, role, hash_password(password), self.selected_id))
                done = "updated (password changed)"
            else:
                cur.execute(
                    "UPDATE USERS SET FullName=%s, UserName=%s, role=%s WHERE UserID=%s",
                    (name, username, role, self.selected_id))
                done = "updated"
            con.commit()
        except psycopg.Error as e:
            if con:
                con.rollback()
            messagebox.showerror("Could not save", str(e), parent=self)
            return
        finally:
            if con:
                con.close()
        messagebox.showinfo("Saved", f"User {username} {done}.", parent=self)
        self.clear()
        self.load_users()