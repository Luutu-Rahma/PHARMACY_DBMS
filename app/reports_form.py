import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import mysql.connector
from matplotlib.figure import Figure
from matplotlib.ticker import FuncFormatter
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from db import connect

LOW_STOCK = 50      # drugs with fewer sellable units than this are flagged red
SOON_DAYS = 90      # batches expiring within this many days are flagged


def q(sql):
    con = connect()
    try:
        cur = con.cursor()
        cur.execute(sql)
        return cur.fetchall()
    finally:
        con.close()


def money(x, pos=None):
    return f"{x:,.0f}"


def empty_chart(fig, message):
    ax = fig.add_subplot(111)
    ax.text(0.5, 0.5, message, ha="center", va="center", fontsize=13)
    ax.axis("off")


# ---------- report loaders: draw on fig, return insight text (or (text, table rows)) ----------
def sales_over_time(fig):
    rows = q("SELECT DATE(`TimeStamp`), COUNT(*), SUM(TotalAmount) FROM TRANSACTIONS "
             "GROUP BY DATE(`TimeStamp`) ORDER BY 1")
    if not rows:
        empty_chart(fig, "No sales recorded yet")
        return "No sales recorded yet."
    days = [r[0] for r in rows]
    revenue = [float(r[2] or 0) for r in rows]
    sales = sum(r[1] for r in rows)
    total = sum(revenue)
    best = max(range(len(rows)), key=lambda i: revenue[i])
    ax = fig.add_subplot(111)
    ax.plot(days, revenue, marker="o", color="#1565c0")
    ax.set_title("Daily sales revenue")
    ax.set_ylabel("Revenue (UGX)")
    ax.yaxis.set_major_formatter(FuncFormatter(money))
    ax.grid(alpha=0.3)
    fig.autofmt_xdate()
    return (f"Total revenue: UGX {total:,.0f} from {sales} sales over {len(rows)} days. "
            f"Best day: {days[best]} (UGX {revenue[best]:,.0f}). "
            f"Average sale: UGX {total / sales:,.0f}.")


def payment_methods(fig):
    rows = q("SELECT PaymentMethod, COUNT(*), SUM(TotalAmount) FROM TRANSACTIONS GROUP BY PaymentMethod")
    if not rows:
        empty_chart(fig, "No sales recorded yet")
        return "No sales recorded yet."
    names = [r[0] for r in rows]
    counts = [r[1] for r in rows]
    revenue = [float(r[2] or 0) for r in rows]
    total = sum(revenue)
    ax1 = fig.add_subplot(121)
    ax2 = fig.add_subplot(122)
    if total > 0:
        ax1.pie(revenue, labels=names, autopct="%1.0f%%", startangle=90)
    ax1.set_title("Share of revenue")
    ax2.bar(names, counts, color=["#2e7d32", "#ef6c00", "#6a1b9a", "#00838f"][:len(names)])
    ax2.set_title("Number of transactions")
    ax2.set_ylabel("Transactions")
    top = max(range(len(rows)), key=lambda i: revenue[i])
    share = (revenue[top] / total * 100) if total else 0
    return (f"{names[top]} brings in the most revenue: UGX {revenue[top]:,.0f} "
            f"({share:.0f}% of UGX {total:,.0f}).")


def stock_per_drug(fig):
    rows = q("SELECT d.GenericName, "
             "COALESCE(SUM(CASE WHEN b.ExpiryDate > CURDATE() THEN b.QuantityLeft ELSE 0 END), 0) AS stock "
             "FROM DRUGS d LEFT JOIN INVENTORY_BATCHES b ON b.DrugID = d.DrugID "
             "GROUP BY d.DrugID, d.GenericName ORDER BY stock ASC")
    if not rows:
        empty_chart(fig, "No drugs found")
        return "No drugs found."
    names = [r[0] for r in rows]
    stock = [int(r[1]) for r in rows]
    colors = ["#c62828" if s < LOW_STOCK else "#2e7d32" for s in stock]
    ax = fig.add_subplot(111)
    ax.barh(names, stock, color=colors)
    ax.set_title(f"Sellable stock per drug (red = below {LOW_STOCK} units)")
    ax.set_xlabel("Units in stock (expired batches excluded)")
    low = [n for n, s in zip(names, stock) if s < LOW_STOCK]
    text = f"Lowest stock: {names[0]} ({stock[0]} units). "
    text += (f"{len(low)} drug(s) below {LOW_STOCK} units: " + ", ".join(low[:5]) + "."
             if low else f"No drug is below {LOW_STOCK} units.")
    return text


def top_sellers(fig):
    rows = q("SELECT d.GenericName, SUM(si.QuantitySold) AS qty, SUM(si.SubTotal) "
             "FROM SALES_ITEMS si JOIN INVENTORY_BATCHES b ON b.BatchID = si.BatchID "
             "JOIN DRUGS d ON d.DrugID = b.DrugID "
             "GROUP BY d.DrugID, d.GenericName ORDER BY qty DESC LIMIT 10")
    if not rows:
        empty_chart(fig, "No sales recorded yet")
        return "No sales recorded yet."
    names = [r[0] for r in rows][::-1]
    qty = [int(r[1]) for r in rows][::-1]
    ax = fig.add_subplot(111)
    ax.barh(names, qty, color="#1565c0")
    ax.set_title("Top selling drugs (units sold)")
    ax.set_xlabel("Units sold")
    return (f"Best seller: {rows[0][0]} with {int(rows[0][1])} units "
            f"(UGX {float(rows[0][2] or 0):,.0f}). Showing the top {len(rows)} drugs.")


def expiry_watch(fig):
    rows = q("SELECT d.GenericName, b.BatchNumber, b.QuantityLeft, b.ExpiryDate, "
             "DATEDIFF(b.ExpiryDate, CURDATE()) AS days, b.QuantityLeft * b.UnitPrice AS value "
             "FROM INVENTORY_BATCHES b JOIN DRUGS d ON d.DrugID = b.DrugID "
             f"WHERE b.QuantityLeft > 0 AND b.ExpiryDate <= CURDATE() + INTERVAL {SOON_DAYS} DAY "
             "ORDER BY b.ExpiryDate")
    if not rows:
        empty_chart(fig, "No expired or expiring batches")
        return "No expired batches and none expiring soon.", []
    labels = [f"{r[0]}\n{r[1]}" for r in rows]
    values = [float(r[5]) for r in rows]
    colors = ["#c62828" if r[4] <= 0 else "#ef6c00" for r in rows]
    ax = fig.add_subplot(111)
    ax.bar(labels, values, color=colors)
    ax.set_title("Value at risk per batch (red = expired, orange = expiring soon)")
    ax.set_ylabel("Value (UGX)")
    ax.yaxis.set_major_formatter(FuncFormatter(money))
    ax.tick_params(axis="x", labelsize=8)
    expired = sum(v for v, r in zip(values, rows) if r[4] <= 0)
    soon = sum(v for v, r in zip(values, rows) if r[4] > 0)
    n_exp = sum(1 for r in rows if r[4] <= 0)
    text = (f"{n_exp} expired batch(es) worth UGX {expired:,.0f}; "
            f"{len(rows) - n_exp} batch(es) expiring within {SOON_DAYS} days worth UGX {soon:,.0f}.")
    table = [(r[0], r[1], r[2], r[3], r[4], f"{float(r[5]):,.0f}") for r in rows]
    return text, table


# ---------- UI ----------
class ChartTab(ttk.Frame):
    def __init__(self, parent, loader, table_cols=None):
        super().__init__(parent)
        self.loader = loader
        self.insight = tk.Label(self, text="", justify="left", anchor="w",
                                wraplength=900, font=("Arial", 11))
        self.insight.pack(fill="x", padx=12, pady=(10, 4))

        btns = tk.Frame(self)
        btns.pack(side="bottom", fill="x", padx=12, pady=6)
        tk.Button(btns, text="Refresh", width=10, command=self.refresh).pack(side="left")
        tk.Button(btns, text="Save chart as image", command=self.save_image).pack(side="left", padx=8)

        self.tree = None
        if table_cols:
            self.tree = ttk.Treeview(self, columns=table_cols, show="headings", height=5)
            for c in table_cols:
                self.tree.heading(c, text=c)
                self.tree.column(c, width=130, anchor="w")
            self.tree.pack(side="bottom", fill="x", padx=12, pady=(4, 0))

        self.fig = Figure(figsize=(8.8, 4.2), dpi=100)
        self.canvas = FigureCanvasTkAgg(self.fig, master=self)
        self.canvas.get_tk_widget().pack(fill="both", expand=True, padx=12)
        self.refresh()

    def refresh(self):
        self.fig.clear()
        try:
            result = self.loader(self.fig)
        except mysql.connector.Error as e:
            messagebox.showerror("Database error", str(e), parent=self)
            return
        text, rows = result if isinstance(result, tuple) else (result, None)
        self.insight.config(text=text)
        if self.tree is not None:
            self.tree.delete(*self.tree.get_children())
            for row in rows or []:
                self.tree.insert("", "end", values=row)
        try:
            self.fig.tight_layout()
        except Exception:
            pass
        self.canvas.draw()

    def save_image(self):
        path = filedialog.asksaveasfilename(
            parent=self, defaultextension=".png", filetypes=[("PNG image", "*.png")])
        if path:
            self.fig.savefig(path, dpi=150, bbox_inches="tight")
            messagebox.showinfo("Saved", f"Chart saved to:\n{path}", parent=self)


class ReportsForm(tk.Toplevel):
    def __init__(self, master, user):
        super().__init__(master)
        self.user_id, self.full_name, self.role = user
        self.title("Reports")
        self.geometry("1000x740")
        tk.Label(self, text="Reports & Insights", font=("Arial", 16, "bold")).pack(pady=(12, 4))

        tabs = ttk.Notebook(self)
        tabs.pack(fill="both", expand=True, padx=10, pady=(0, 8))
        tabs.add(ChartTab(tabs, sales_over_time), text="Sales over time")
        tabs.add(ChartTab(tabs, payment_methods), text="Payment methods")
        tabs.add(ChartTab(tabs, stock_per_drug), text="Stock levels")
        tabs.add(ChartTab(tabs, top_sellers), text="Top sellers")
        tabs.add(ChartTab(tabs, expiry_watch,
                          table_cols=("Drug", "Batch", "Left", "Expiry", "Days left", "Value (UGX)")),
                 text="Expiry watch")
        tk.Button(self, text="Close", width=10, command=self.destroy).pack(pady=(0, 10))