import tkinter as tk
from tkinter import ttk, messagebox
import mysql.connector
from db import connect


class CrudTab(ttk.Frame):
    """One tab: a form on top, a list below. Pick a row to edit it, or fill the form to add."""

    def __init__(self, parent, table, id_col, fields, list_sql, headings, widths):
        super().__init__(parent)
        # fields: (label, column, kind, extra, required)
        #   kind: "entry" | "price" | "lookup" (extra = SQL returning id, label) | "combo" (extra = values)
        self.table, self.id_col, self.fields, self.list_sql = table, id_col, fields, list_sql
        self.selected_id = None
        self.widgets = {}
        self.lookups = {}  # column -> {label: id}

        form = tk.Frame(self)
        form.pack(fill="x", padx=12, pady=10)
        for n, (label, col, kind, extra, required) in enumerate(fields):
            r, c = divmod(n, 2)
            text = label + (" *" if required else "")
            tk.Label(form, text=text).grid(row=r * 2, column=c, sticky="w", padx=(0, 14))
            if kind == "lookup":
                w = ttk.Combobox(form, state="readonly", width=32)
            elif kind == "combo":
                w = ttk.Combobox(form, values=extra, width=32)
            else:
                w = tk.Entry(form, width=35)
            w.grid(row=r * 2 + 1, column=c, sticky="w", padx=(0, 14), pady=(0, 6))
            self.widgets[col] = w

        btns = tk.Frame(self)
        btns.pack(fill="x", padx=12, pady=(0, 8))
        self.save_btn = tk.Button(btns, text="Add new", width=16, bg="#2e7d32", fg="white", command=self.save)
        self.save_btn.pack(side="left")
        tk.Button(btns, text="New / clear", width=12, command=self.clear).pack(side="left", padx=8)
        tk.Button(btns, text="Refresh", width=10, command=self.refresh).pack(side="left")
        self.hint = tk.Label(btns, text="Select a row below to edit it. * = required")
        self.hint.pack(side="right")

        cols = ("ID",) + tuple(headings)
        self.tree = ttk.Treeview(self, columns=cols, show="headings", height=12)
        self.tree.heading("ID", text="ID")
        self.tree.column("ID", width=40, anchor="w")
        for h, w in zip(headings, widths):
            self.tree.heading(h, text=h)
            self.tree.column(h, width=w, anchor="w")
        self.tree.pack(fill="both", expand=True, padx=12, pady=(0, 10))
        self.tree.bind("<<TreeviewSelect>>", self.on_select)

        self.refresh()

    # ---------- loading ----------
    def refresh(self):
        self.load_lookups()
        self.load_rows()

    def load_lookups(self):
        try:
            con = connect()
            cur = con.cursor()
            for label, col, kind, extra, required in self.fields:
                if kind == "lookup":
                    cur.execute(extra)
                    self.lookups[col] = {name: i for i, name in cur.fetchall()}
                    self.widgets[col]["values"] = list(self.lookups[col].keys())
            con.close()
        except mysql.connector.Error as e:
            messagebox.showerror("Database error", str(e), parent=self)

    def load_rows(self):
        try:
            con = connect()
            cur = con.cursor()
            cur.execute(self.list_sql)
            rows = cur.fetchall()
            con.close()
        except mysql.connector.Error as e:
            messagebox.showerror("Database error", str(e), parent=self)
            return
        self.tree.delete(*self.tree.get_children())
        for row in rows:
            self.tree.insert("", "end", values=["" if v is None else v for v in row])

    # ---------- form ----------
    def clear(self):
        self.selected_id = None
        self.save_btn.config(text="Add new")
        self.tree.selection_remove(self.tree.selection())
        for label, col, kind, extra, required in self.fields:
            w = self.widgets[col]
            if isinstance(w, ttk.Combobox):
                w.set("")
            else:
                w.delete(0, tk.END)

    def on_select(self, event=None):
        sel = self.tree.selection()
        if not sel:
            return
        row_id = self.tree.item(sel[0], "values")[0]
        cols = ", ".join(f[1] for f in self.fields)
        try:
            con = connect()
            cur = con.cursor()
            cur.execute(f"SELECT {cols} FROM {self.table} WHERE {self.id_col} = %s", (row_id,))
            row = cur.fetchone()
            con.close()
        except mysql.connector.Error as e:
            messagebox.showerror("Database error", str(e), parent=self)
            return
        if row is None:
            return
        self.selected_id = row_id
        self.save_btn.config(text="Update selected")
        for (label, col, kind, extra, required), val in zip(self.fields, row):
            w = self.widgets[col]
            if kind == "lookup":
                names = {i: n for n, i in self.lookups.get(col, {}).items()}
                w.set(names.get(val, ""))
            elif isinstance(w, ttk.Combobox):
                w.set("" if val is None else str(val))
            else:
                w.delete(0, tk.END)
                w.insert(0, "" if val is None else str(val))

    def collect(self):
        values = []
        for label, col, kind, extra, required in self.fields:
            text = self.widgets[col].get().strip()
            if not text:
                if required:
                    messagebox.showwarning("Missing details", f"{label} is required.", parent=self)
                    return None
                values.append(None)
                continue
            if kind == "lookup":
                values.append(self.lookups[col][text])
            elif kind == "price":
                try:
                    price = float(text)
                    if price <= 0:
                        raise ValueError
                except ValueError:
                    messagebox.showwarning("Price", f"{label} must be a number above 0.", parent=self)
                    return None
                values.append(price)
            else:
                values.append(text)
        return values

    def save(self):
        values = self.collect()
        if values is None:
            return
        cols = [f[1] for f in self.fields]
        con = None
        try:
            con = connect()
            cur = con.cursor()
            if self.selected_id is None:
                marks = ", ".join(["%s"] * len(cols))
                cur.execute(f"INSERT INTO {self.table} ({', '.join(cols)}) VALUES ({marks})", values)
                done = "added"
            else:
                sets = ", ".join(f"{c} = %s" for c in cols)
                cur.execute(f"UPDATE {self.table} SET {sets} WHERE {self.id_col} = %s",
                            values + [self.selected_id])
                done = "updated"
            con.commit()
        except mysql.connector.Error as e:
            if con:
                con.rollback()
            messagebox.showerror("Could not save", e.msg, parent=self)
            return
        finally:
            if con:
                con.close()
        messagebox.showinfo("Saved", f"Record {done}.", parent=self)
        self.clear()
        self.refresh()


class DrugsSuppliersForm(tk.Toplevel):
    def __init__(self, master, user):
        super().__init__(master)
        self.user_id, self.full_name, self.role = user
        self.title("Drugs & Suppliers")
        self.geometry("920x640")
        tk.Label(self, text="Drugs, Suppliers & Categories", font=("Arial", 16, "bold")).pack(pady=(12, 6))

        self.tabs = ttk.Notebook(self)
        self.tabs.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        self.drugs_tab = CrudTab(
            self.tabs, "DRUGS", "DrugID",
            fields=[
                ("Generic name", "GenericName", "entry", None, True),
                ("Brand name", "BrandName", "entry", None, True),
                ("Category", "CategoryID", "lookup",
                 "SELECT CategoryID, CategoryName FROM CATEGORIES ORDER BY CategoryName", True),
                ("Unit of measure", "UnitMeasure", "combo",
                 ["tablets", "capsules", "syrup", "injection", "cream"], True),
                ("Unit price (UGX)", "UnitPrice", "price", None, True),
            ],
            list_sql=("SELECT d.DrugID, d.GenericName, d.BrandName, c.CategoryName, d.UnitMeasure, d.UnitPrice "
                      "FROM DRUGS d JOIN CATEGORIES c ON c.CategoryID = d.CategoryID ORDER BY d.GenericName"),
            headings=("Generic name", "Brand", "Category", "Unit", "Price"),
            widths=(200, 160, 150, 90, 90),
        )
        self.suppliers_tab = CrudTab(
            self.tabs, "SUPPLIERS", "SupplierID",
            fields=[
                ("Supplier name", "SupplierName", "entry", None, True),
                ("Contact person", "ContactPerson", "entry", None, False),
                ("Phone number", "PhoneNumber", "entry", None, True),
                ("Email", "Email", "entry", None, False),
                ("Address", "Address", "entry", None, False),
            ],
            list_sql=("SELECT SupplierID, SupplierName, ContactPerson, PhoneNumber, Email, Address "
                      "FROM SUPPLIERS ORDER BY SupplierName"),
            headings=("Supplier", "Contact", "Phone", "Email", "Address"),
            widths=(170, 130, 120, 170, 170),
        )
        self.categories_tab = CrudTab(
            self.tabs, "CATEGORIES", "CategoryID",
            fields=[
                ("Category name", "CategoryName", "entry", None, True),
                ("Description", "Description", "entry", None, False),
            ],
            list_sql="SELECT CategoryID, CategoryName, Description FROM CATEGORIES ORDER BY CategoryName",
            headings=("Category", "Description"),
            widths=(200, 400),
        )
        self.tabs.add(self.drugs_tab, text="Drugs")
        self.tabs.add(self.suppliers_tab, text="Suppliers")
        self.tabs.add(self.categories_tab, text="Categories")
        # Reload lists when switching tabs (e.g. a new category should appear in the Drugs tab)
        self.tabs.bind("<<NotebookTabChanged>>", lambda e: self.refresh_all())

        tk.Button(self, text="Close", width=10, command=self.destroy).pack(pady=(0, 10))

    def refresh_all(self):
        for tab in (self.drugs_tab, self.suppliers_tab, self.categories_tab):
            tab.refresh()