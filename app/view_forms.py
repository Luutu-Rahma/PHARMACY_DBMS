import tkinter as tk
from tkinter import ttk, messagebox
from datetime import date
import mysql.connector
from db import connect

LOW_STOCK = 50   # drugs with fewer sellable units than this are flagged
SOON_DAYS = 90   # batches expiring within this many days are flagged


class ListWindow(tk.Toplevel):
    """Read-only list with a search box. Subclasses set the columns and the data."""
    heading = ""
    columns = ()
    widths = ()
    legend = ""

    def __init__(self, master, user):
        super().__init__(master)
        self.user_id, self.full_name, self.role = user
        self.title(self.heading)
        self.geometry("980x600")
        self.all_rows = []

        tk.Label(self, text=self.heading, font=("Arial", 16, "bold")).pack(pady=(12, 4))
        bar = tk.Frame(self)
        bar.pack(fill="x", padx=15, pady=6)
        tk.Label(bar, text="Search:").pack(side="left")
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda *a: self.apply_filter())
        entry = tk.Entry(bar, textvariable=self.search_var, width=32)
        entry.pack(side="left", padx=6)
        entry.focus()
        self.build_options(bar)
        tk.Button(bar, text="Refresh", command=self.load).pack(side="right")

        self.tree = ttk.Treeview(self, columns=self.columns, show="headings")
        for c, w in zip(self.columns, self.widths):
            self.tree.heading(c, text=c)
            self.tree.column(c, width=w, anchor="w")
        self.tree.tag_configure("bad", background="#f8d7da")
        self.tree.tag_configure("warn", background="#ffe5b4")
        scroll = ttk.Scrollbar(self, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scroll.set)
        scroll.pack(side="right", fill="y", padx=(0, 10), pady=6)
        self.tree.pack(fill="both", expand=True, padx=(15, 0), pady=6)

        foot = tk.Frame(self)
        foot.pack(side="bottom", fill="x", padx=15, pady=6)
        self.count_label = tk.Label(foot, text="")
        self.count_label.pack(side="left")
        tk.Label(foot, text=self.legend).pack(side="left", padx=20)
        tk.Button(foot, text="Close", width=10, command=self.destroy).pack(side="right")

        self.load()

    # hooks for subclasses
    def build_options(self, bar):
        pass

    def fetch(self):
        raise NotImplementedError

    def display(self, row):
        """Return (values, tag) for a database row."""
        raise NotImplementedError

    def keep(self, row):
        return True

    # logic
    def load(self):
        try:
            con = connect()
            cur = con.cursor()
            cur.execute(self.fetch())
            self.all_rows = cur.fetchall()
            con.close()
        except mysql.connector.Error as e:
            messagebox.showerror("Database error", str(e), parent=self)
            return
        self.apply_filter()

    def apply_filter(self):
        text = self.search_var.get().strip().lower()
        self.tree.delete(*self.tree.get_children())
        shown = 0
        for row in self.all_rows:
            if not self.keep(row):
                continue
            values, tag = self.display(row)
            if text and text not in " ".join(str(v) for v in values).lower():
                continue
            self.tree.insert("", "end", values=values, tags=(tag,) if tag else ())
            shown += 1
        self.count_label.config(text=f"Showing {shown} of {len(self.all_rows)}")


class ViewDrugsForm(ListWindow):
    heading = "Drug Catalogue"
    columns = ("Generic name", "Brand", "Category", "Unit", "Price (UGX)", "Sellable stock")
    widths = (200, 160, 150, 90, 100, 110)
    legend = f"Red = out of stock, orange = below {LOW_STOCK} units"

    def fetch(self):
        return ("SELECT d.GenericName, d.BrandName, c.CategoryName, d.UnitMeasure, d.UnitPrice, "
                "COALESCE(SUM(CASE WHEN b.ExpiryDate > CURDATE() THEN b.QuantityLeft ELSE 0 END), 0) "
                "FROM DRUGS d JOIN CATEGORIES c ON c.CategoryID = d.CategoryID "
                "LEFT JOIN INVENTORY_BATCHES b ON b.DrugID = d.DrugID "
                "GROUP BY d.DrugID, d.GenericName, d.BrandName, c.CategoryName, d.UnitMeasure, d.UnitPrice "
                "ORDER BY d.GenericName")

    def display(self, row):
        name, brand, cat, unit, price, stock = row
        stock = int(stock)
        tag = "bad" if stock == 0 else "warn" if stock < LOW_STOCK else ""
        return (name, brand, cat, unit, f"{float(price):,.0f}", stock), tag


class ViewStockForm(ListWindow):
    heading = "Stock by Batch"
    columns = ("Drug", "Batch", "Supplier", "Left", "Expiry", "Status")
    widths = (190, 120, 180, 70, 100, 130)
    legend = f"Red = expired, orange = expires within {SOON_DAYS} days"

    def build_options(self, bar):
        self.hide_expired = tk.BooleanVar(value=False)
        self.hide_empty = tk.BooleanVar(value=False)
        tk.Checkbutton(bar, text="Hide expired", variable=self.hide_expired,
                       command=self.apply_filter).pack(side="left", padx=(15, 0))
        tk.Checkbutton(bar, text="Hide empty batches", variable=self.hide_empty,
                       command=self.apply_filter).pack(side="left")

    def fetch(self):
        return ("SELECT d.GenericName, b.BatchNumber, s.SupplierName, b.QuantityLeft, b.ExpiryDate "
                "FROM INVENTORY_BATCHES b JOIN DRUGS d ON d.DrugID = b.DrugID "
                "JOIN SUPPLIERS s ON s.SupplierID = b.SupplierID "
                "ORDER BY d.GenericName, b.ExpiryDate")

    def keep(self, row):
        left, expiry = row[3], row[4]
        if self.hide_expired.get() and (expiry - date.today()).days <= 0:
            return False
        if self.hide_empty.get() and left == 0:
            return False
        return True

    def display(self, row):
        drug, batch, supplier, left, expiry = row
        days = (expiry - date.today()).days
        if days <= 0:
            status, tag = "EXPIRED", "bad"
        elif days <= SOON_DAYS:
            status, tag = f"Expires in {days}d", "warn"
        else:
            status, tag = "OK", ""
        return (drug, batch, supplier, left, expiry, status), tag