import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime, date
import psycopg
from db import connect

SOON_DAYS = 90  # batches expiring within this many days are flagged


class InventoryForm(tk.Toplevel):
    def __init__(self, master, user):
        super().__init__(master)
        self.user_id, self.full_name, self.role = user
        self.title("Inventory - Receive Stock")
        self.geometry("960x660")
        self.drugs = {}      # label -> (DrugID, UnitPrice)
        self.suppliers = {}  # label -> SupplierID
        self.build_ui()
        self.load_lists()
        self.load_batches()

    # ---------- UI ----------
    def build_ui(self):
        tk.Label(self, text="Receive New Stock Batch", font=("Arial", 16, "bold")).pack(pady=(12, 8))

        form = tk.Frame(self)
        form.pack(fill="x", padx=15)

        tk.Label(form, text="Drug").grid(row=0, column=0, sticky="w")
        self.drug_box = ttk.Combobox(form, state="readonly", width=34)
        self.drug_box.grid(row=1, column=0, padx=(0, 12), pady=2, sticky="w")
        self.drug_box.bind("<<ComboboxSelected>>", self.fill_price)

        tk.Label(form, text="Supplier").grid(row=0, column=1, sticky="w")
        self.supplier_box = ttk.Combobox(form, state="readonly", width=30)
        self.supplier_box.grid(row=1, column=1, padx=(0, 12), pady=2, sticky="w")

        tk.Label(form, text="Batch number").grid(row=0, column=2, sticky="w")
        self.batch_entry = tk.Entry(form, width=18)
        self.batch_entry.grid(row=1, column=2, pady=2, sticky="w")

        tk.Label(form, text="Quantity received").grid(row=2, column=0, sticky="w", pady=(8, 0))
        self.qty_entry = tk.Entry(form, width=14)
        self.qty_entry.grid(row=3, column=0, sticky="w")

        tk.Label(form, text="Manufacture date (YYYY-MM-DD)").grid(row=2, column=1, sticky="w", pady=(8, 0))
        self.mfd_entry = tk.Entry(form, width=18)
        self.mfd_entry.grid(row=3, column=1, sticky="w")

        tk.Label(form, text="Expiry date (YYYY-MM-DD)").grid(row=2, column=2, sticky="w", pady=(8, 0))
        self.exp_entry = tk.Entry(form, width=18)
        self.exp_entry.grid(row=3, column=2, sticky="w")

        tk.Label(form, text="Unit price (UGX)").grid(row=4, column=0, sticky="w", pady=(8, 0))
        self.price_entry = tk.Entry(form, width=14)
        self.price_entry.grid(row=5, column=0, sticky="w")

        btns = tk.Frame(self)
        btns.pack(fill="x", padx=15, pady=12)
        tk.Button(btns, text="Save batch", width=14, bg="#2e7d32", fg="white",
                  command=self.save_batch).pack(side="left")
        tk.Button(btns, text="Clear form", width=12, command=self.clear_form).pack(side="left", padx=8)
        tk.Button(btns, text="Refresh list", width=12, command=self.load_batches).pack(side="left")
        tk.Button(btns, text="Close", width=10, command=self.destroy).pack(side="right")

        tk.Label(self, text="All batches (red = expired, orange = expiring soon)",
                 font=("Arial", 11, "bold")).pack(anchor="w", padx=15)
        cols = ("ID", "Drug", "Batch", "Supplier", "Received", "Left", "MFD", "Expiry", "Price", "Status")
        self.tree = ttk.Treeview(self, columns=cols, show="headings", height=14)
        widths = (40, 150, 100, 150, 70, 60, 90, 90, 70, 100)
        for c, w in zip(cols, widths):
            self.tree.heading(c, text=c)
            self.tree.column(c, width=w, anchor="w")
        self.tree.tag_configure("expired", background="#f8d7da")
        self.tree.tag_configure("soon", background="#ffe5b4")
        self.tree.pack(fill="both", expand=True, padx=15, pady=8)

    # ---------- data ----------
    def load_lists(self):
        try:
            con = connect()
            cur = con.cursor()
            cur.execute("SELECT DrugID, GenericName, BrandName, UnitPrice FROM DRUGS ORDER BY GenericName")
            self.drugs = {f"{n} ({b})": (i, float(p)) for i, n, b, p in cur.fetchall()}
            cur.execute("SELECT SupplierID, SupplierName FROM SUPPLIERS ORDER BY SupplierName")
            self.suppliers = {n: i for i, n in cur.fetchall()}
            con.close()
        except psycopg.Error as e:
            messagebox.showerror("Database error", str(e), parent=self)
            return
        self.drug_box["values"] = list(self.drugs.keys())
        self.supplier_box["values"] = list(self.suppliers.keys())

    def load_batches(self):
        try:
            con = connect()
            cur = con.cursor()
            cur.execute(
                "SELECT b.BatchID, d.GenericName, b.BatchNumber, s.SupplierName, "
                "b.QuantityReceived, b.QuantityLeft, b.MFD, b.ExpiryDate, b.UnitPrice "
                "FROM INVENTORY_BATCHES b "
                "JOIN DRUGS d ON d.DrugID = b.DrugID "
                "JOIN SUPPLIERS s ON s.SupplierID = b.SupplierID "
                "ORDER BY b.ExpiryDate"
            )
            rows = cur.fetchall()
            con.close()
        except psycopg.Error as e:
            messagebox.showerror("Database error", str(e), parent=self)
            return
        self.tree.delete(*self.tree.get_children())
        today = date.today()
        for bid, drug, bno, sup, rec, left, mfd, exp, price in rows:
            days = (exp - today).days
            if days <= 0:
                status, tag = "EXPIRED", "expired"
            elif days <= SOON_DAYS:
                status, tag = f"Expires in {days}d", "soon"
            else:
                status, tag = "OK", ""
            self.tree.insert("", "end", tags=(tag,),
                             values=(bid, drug, bno, sup, rec, left, mfd, exp, f"{float(price):,.0f}", status))

    # ---------- form ----------
    def fill_price(self, event=None):
        label = self.drug_box.get()
        if label in self.drugs and not self.price_entry.get().strip():
            self.price_entry.insert(0, f"{self.drugs[label][1]:.2f}")

    def clear_form(self):
        self.drug_box.set("")
        self.supplier_box.set("")
        for e in (self.batch_entry, self.qty_entry, self.mfd_entry, self.exp_entry, self.price_entry):
            e.delete(0, tk.END)

    @staticmethod
    def parse_date(text):
        return datetime.strptime(text.strip(), "%Y-%m-%d").date()

    def save_batch(self):
        drug = self.drug_box.get()
        supplier = self.supplier_box.get()
        batch_no = self.batch_entry.get().strip()
        if drug not in self.drugs or supplier not in self.suppliers or not batch_no:
            messagebox.showwarning("Missing details", "Choose a drug and supplier, and enter a batch number.", parent=self)
            return
        try:
            qty = int(self.qty_entry.get())
            if qty <= 0:
                raise ValueError
        except ValueError:
            messagebox.showwarning("Quantity", "Quantity must be a whole number above 0.", parent=self)
            return
        try:
            price = float(self.price_entry.get())
            if price <= 0:
                raise ValueError
        except ValueError:
            messagebox.showwarning("Price", "Enter a unit price above 0.", parent=self)
            return
        try:
            mfd = self.parse_date(self.mfd_entry.get())
            exp = self.parse_date(self.exp_entry.get())
        except ValueError:
            messagebox.showwarning("Dates", "Use the format YYYY-MM-DD, for example 2027-03-31.", parent=self)
            return
        if mfd >= exp:
            messagebox.showwarning("Dates", "Expiry date must be after the manufacture date.", parent=self)
            return
        if exp <= date.today():
            messagebox.showwarning("Dates", "This batch is already expired.", parent=self)
            return

        con = None
        try:
            con = connect()
            cur = con.cursor()
            cur.execute(
                "INSERT INTO INVENTORY_BATCHES "
                "(DrugID, SupplierID, BatchNumber, QuantityReceived, QuantityLeft, MFD, ExpiryDate, UnitPrice) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
                (self.drugs[drug][0], self.suppliers[supplier], batch_no, qty, qty, mfd, exp, price),
            )
            con.commit()
        except psycopg.Error as e:
            if con:
                con.rollback()
            messagebox.showerror("Could not save", str(e), parent=self)
            return
        finally:
            if con:
                con.close()
        messagebox.showinfo("Saved", f"Batch {batch_no} added ({qty} units).", parent=self)
        self.clear_form()
        self.load_batches()