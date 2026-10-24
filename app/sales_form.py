import tkinter as tk
from tkinter import ttk, messagebox
import mysql.connector
from db import connect

PAYMENT_METHODS = ["Cash", "Mobile Money"]


class SalesForm(tk.Toplevel):
    def __init__(self, master, user):
        super().__init__(master)
        self.user_id, self.full_name, self.role = user
        self.title("New Sale")
        self.geometry("780x560")
        self.batches = {}  # combobox label -> (BatchID, drug, batch_no, left, price)
        self.basket = []   # list of [BatchID, drug, batch_no, qty, price]
        self.build_ui()
        self.load_batches()

    # ---------- UI ----------
    def build_ui(self):
        tk.Label(self, text="New Sale", font=("Arial", 16, "bold")).pack(pady=(12, 0))
        tk.Label(self, text=f"Served by: {self.full_name} ({self.role})").pack(pady=(0, 10))

        top = tk.Frame(self)
        top.pack(fill="x", padx=15)
        tk.Label(top, text="Drug / batch (soonest expiry first)").grid(row=0, column=0, sticky="w")
        self.batch_box = ttk.Combobox(top, state="readonly", width=75)
        self.batch_box.grid(row=1, column=0, columnspan=3, sticky="w", pady=3)
        tk.Label(top, text="Quantity").grid(row=2, column=0, sticky="w", pady=(8, 0))
        self.qty_var = tk.StringVar(value="1")
        tk.Spinbox(top, from_=1, to=10000, textvariable=self.qty_var, width=8).grid(row=3, column=0, sticky="w")
        tk.Button(top, text="Add to basket", width=16, command=self.add_item).grid(row=3, column=1, padx=10, sticky="w")

        cols = ("Drug", "Batch", "Qty", "Price", "Subtotal")
        self.tree = ttk.Treeview(self, columns=cols, show="headings", height=10)
        widths = (240, 130, 70, 100, 110)
        for c, w in zip(cols, widths):
            self.tree.heading(c, text=c)
            self.tree.column(c, width=w, anchor="w" if c in ("Drug", "Batch") else "e")
        self.tree.pack(fill="x", padx=15, pady=12)

        mid = tk.Frame(self)
        mid.pack(fill="x", padx=15)
        tk.Button(mid, text="Remove selected", command=self.remove_item).pack(side="left")
        tk.Button(mid, text="Clear basket", command=self.clear_basket).pack(side="left", padx=8)
        self.total_label = tk.Label(mid, text="Total: UGX 0", font=("Arial", 13, "bold"))
        self.total_label.pack(side="right")

        bottom = tk.Frame(self)
        bottom.pack(fill="x", padx=15, pady=18)
        tk.Label(bottom, text="Payment method").pack(side="left")
        self.pay_box = ttk.Combobox(bottom, state="readonly", values=PAYMENT_METHODS, width=16)
        self.pay_box.set(PAYMENT_METHODS[0])
        self.pay_box.pack(side="left", padx=8)
        tk.Button(bottom, text="Close", width=10, command=self.destroy).pack(side="right")
        tk.Button(bottom, text="Complete sale", width=16, bg="#2e7d32", fg="white",
                  command=self.complete_sale).pack(side="right", padx=8)

    # ---------- data ----------
    def load_batches(self):
        """Only non-expired batches that still have stock, soonest expiry first."""
        try:
            con = connect()
            cur = con.cursor()
            cur.execute(
                "SELECT b.BatchID, d.GenericName, b.BatchNumber, b.QuantityLeft, "
                "b.ExpiryDate, b.UnitPrice "
                "FROM INVENTORY_BATCHES b JOIN DRUGS d ON d.DrugID = b.DrugID "
                "WHERE b.ExpiryDate > CURDATE() AND b.QuantityLeft > 0 "
                "ORDER BY d.GenericName, b.ExpiryDate"
            )
            rows = cur.fetchall()
            con.close()
        except mysql.connector.Error as e:
            messagebox.showerror("Database error", str(e), parent=self)
            return
        self.batches = {}
        for bid, name, bno, left, exp, price in rows:
            label = f"{name} | {bno} | stock {left} | exp {exp} | UGX {float(price):,.0f}"
            self.batches[label] = (bid, name, bno, left, float(price))
        self.batch_box["values"] = list(self.batches.keys())
        self.batch_box.set("")

    # ---------- basket ----------
    def add_item(self):
        label = self.batch_box.get()
        if label not in self.batches:
            messagebox.showwarning("Select a drug", "Choose a drug/batch first.", parent=self)
            return
        try:
            qty = int(self.qty_var.get())
            if qty <= 0:
                raise ValueError
        except ValueError:
            messagebox.showwarning("Quantity", "Enter a whole number above 0.", parent=self)
            return
        bid, name, bno, left, price = self.batches[label]
        in_basket = sum(i[3] for i in self.basket if i[0] == bid)
        if qty + in_basket > left:
            messagebox.showwarning(
                "Not enough stock",
                f"Only {left - in_basket} more available in this batch.", parent=self)
            return
        for item in self.basket:
            if item[0] == bid:
                item[3] += qty
                break
        else:
            self.basket.append([bid, name, bno, qty, price])
        self.qty_var.set("1")
        self.refresh_basket()

    def remove_item(self):
        sel = self.tree.selection()
        if not sel:
            return
        idx = self.tree.index(sel[0])
        del self.basket[idx]
        self.refresh_basket()

    def clear_basket(self):
        self.basket = []
        self.refresh_basket()

    def refresh_basket(self):
        self.tree.delete(*self.tree.get_children())
        total = 0
        for bid, name, bno, qty, price in self.basket:
            sub = qty * price
            total += sub
            self.tree.insert("", "end", values=(name, bno, qty, f"{price:,.0f}", f"{sub:,.0f}"))
        self.total_label.config(text=f"Total: UGX {total:,.0f}")

    # ---------- save ----------
    def complete_sale(self):
        if not self.basket:
            messagebox.showwarning("Empty basket", "Add at least one item.", parent=self)
            return
        method = self.pay_box.get()
        if method not in PAYMENT_METHODS:
            messagebox.showwarning("Payment", "Choose a payment method.", parent=self)
            return
        con = None
        try:
            con = connect()
            cur = con.cursor()
            cur.execute("INSERT INTO TRANSACTIONS (UserID, PaymentMethod) VALUES (%s, %s)",
                        (self.user_id, method))
            tid = cur.lastrowid
            # The triggers check expiry/stock, set SubTotal, deduct stock, update the total
            for bid, name, bno, qty, price in self.basket:
                cur.execute(
                    "INSERT INTO SALES_ITEMS (TransactionID, BatchID, QuantitySold) "
                    "VALUES (%s, %s, %s)", (tid, bid, qty))
            cur.execute("SELECT TotalAmount FROM TRANSACTIONS WHERE TransactionID = %s", (tid,))
            total = cur.fetchone()[0]
            con.commit()
        except mysql.connector.Error as e:
            if con:
                con.rollback()
            messagebox.showerror("Sale failed", e.msg, parent=self)
            return
        finally:
            if con:
                con.close()
        messagebox.showinfo(
            "Sale complete",
            f"Receipt #{tid}\nPayment: {method}\nTotal: UGX {float(total):,.0f}", parent=self)
        self.clear_basket()
        self.load_batches()
