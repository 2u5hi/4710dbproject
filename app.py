import io
import os
import tkinter as tk
from tkinter import ttk, messagebox

from PIL import Image, ImageTk

import db


def money(x):
    return "" if x is None else f"${x:,.0f}"


class ResultsTable(ttk.Frame):

    def __init__(self, master, columns, headings, widths=None, height=12,
                 on_open=None):
        super().__init__(master)
        self.columns = columns
        self.on_open = on_open
        self.tree = ttk.Treeview(self, columns=columns, show="headings",
                                 height=height)
        for col, head in zip(columns, headings):
            self.tree.heading(
                col, text=head,
                command=lambda c=col: self._sort_by(c, False))
            self.tree.column(col, width=(widths or {}).get(col, 120), anchor="w")
        vsb = ttk.Scrollbar(self, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)
        if on_open:
            self.tree.bind("<Double-1>", self._emit_open)

    def set_rows(self, rows, iids=None):
        self.tree.delete(*self.tree.get_children())
        for i, row in enumerate(rows):
            iid = None if iids is None else str(iids[i])
            self.tree.insert("", "end", iid=iid, values=row)

    def selected_iid(self):
        sel = self.tree.selection()
        return sel[0] if sel else None

    def _emit_open(self, _evt):
        iid = self.selected_iid()
        if iid is not None and self.on_open:
            self.on_open(iid)

    def _sort_by(self, col, descending):
        def conv(v):
            t = v.replace("$", "").replace(",", "").strip()
            try:
                return (0, float(t))
            except ValueError:
                return (1, v.lower())
        data = [(self.tree.set(k, col), k) for k in self.tree.get_children("")]
        data.sort(key=lambda x: conv(x[0]), reverse=descending)
        for i, (_, k) in enumerate(data):
            self.tree.move(k, "", i)
        self.tree.heading(col, command=lambda: self._sort_by(col, not descending))


class RealEstateApp(tk.Tk):
    POOL_OPTS = {"Any": None, "No pool": False, "Has pool": True}
    STATUS_OPTS = {"For sale": "for_sale", "Sold": "sold", "All": "all"}

    def __init__(self):
        super().__init__()
        self.title("DNA Realty — Office Database")
        self.geometry("880x620")
        self.minsize(760, 540)

        if not os.path.exists(db.DB_PATH):
            messagebox.showerror(
                "Database missing",
                "realestate.db was not found.\n\nRun 'python seed.py' first.")
            self.destroy()
            return

        self.conn = db.get_connection()
        self.status = tk.StringVar()

        nb = ttk.Notebook(self)
        nb.pack(fill="both", expand=True, padx=8, pady=8)
        nb.add(self._tab_properties(nb),  text="Properties")
        nb.add(self._tab_sales_agents(nb), text="Sales & Agents")
        nb.add(self._tab_manage(nb),       text="Manage")

        ttk.Label(self, textvariable=self.status, relief="sunken",
                  anchor="w").pack(fill="x", side="bottom")
        self._show_counts()
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    #housekeeping
    def _on_close(self):
        try:
            self.conn.close()
        finally:
            self.destroy()

    def _show_counts(self):
        c = db.table_counts(self.conn)
        self.status.set("   ".join(f"{k}: {v}" for k, v in c.items()))


    # Properties

    def _tab_properties(self, master):
        f = ttk.Frame(master, padding=10)

        filt = ttk.LabelFrame(f, text="Find properties", padding=8)
        filt.pack(fill="x")

        ttk.Label(filt, text="City:").grid(row=0, column=0, sticky="e", padx=3, pady=3)
        self.p_city = ttk.Combobox(filt, width=16, values=[""] + db.list_cities(self.conn))
        self.p_city.grid(row=0, column=1, padx=3, pady=3)

        ttk.Label(filt, text="District:").grid(row=0, column=2, sticky="e", padx=3)
        self.p_dist = ttk.Combobox(filt, width=16,
                                   values=[""] + db.list_districts(self.conn))
        self.p_dist.grid(row=0, column=3, padx=3)

        ttk.Label(filt, text="Min beds:").grid(row=0, column=4, sticky="e", padx=3)
        self.p_beds = ttk.Spinbox(filt, from_=0, to=10, width=5)
        self.p_beds.set(0)
        self.p_beds.grid(row=0, column=5, padx=3)

        ttk.Label(filt, text="Pool:").grid(row=1, column=0, sticky="e", padx=3, pady=3)
        self.p_pool = ttk.Combobox(filt, width=16, state="readonly",
                                   values=list(self.POOL_OPTS))
        self.p_pool.current(0)
        self.p_pool.grid(row=1, column=1, padx=3)

        ttk.Label(filt, text="Min $:").grid(row=1, column=2, sticky="e", padx=3)
        self.p_lo = ttk.Entry(filt, width=12)
        self.p_lo.grid(row=1, column=3, padx=3, sticky="w")

        ttk.Label(filt, text="Max $:").grid(row=1, column=4, sticky="e", padx=3)
        self.p_hi = ttk.Entry(filt, width=12)
        self.p_hi.grid(row=1, column=5, padx=3, sticky="w")

        ttk.Label(filt, text="Status:").grid(row=1, column=6, sticky="e", padx=3)
        self.p_status = ttk.Combobox(filt, width=10, state="readonly",
                                     values=list(self.STATUS_OPTS))
        self.p_status.current(0)
        self.p_status.grid(row=1, column=7, padx=3)

        btns = ttk.Frame(filt)
        btns.grid(row=0, column=6, columnspan=2, padx=3)
        ttk.Button(btns, text="Search", command=self._run_property_search).pack(side="left")
        ttk.Button(btns, text="Reset", command=self._reset_property_filters).pack(
            side="left", padx=4)

        ttk.Label(
            f, foreground="#555",
            text="Double-click a property for full details and its photo.  "
                 "Tip: City=Bethlehem, $200000–250000 → query (a);  "
                 "District=Parkland, Min beds=4, Pool=No pool → query (b).",
        ).pack(anchor="w", pady=(8, 4))

        self.p_table = ResultsTable(
            f,
            ("address", "city", "district", "beds", "baths", "pool",
             "price", "status"),
            ("Address", "City", "District", "Beds", "Baths", "Pool",
             "List Price", "Status"),
            widths={"address": 170, "city": 90, "district": 120, "beds": 50,
                    "baths": 55, "pool": 55, "price": 100, "status": 80},
            on_open=self._open_property_detail,
        )
        self.p_table.pack(fill="both", expand=True)

        self._run_property_search()
        return f

    def _reset_property_filters(self):
        self.p_city.set("")
        self.p_dist.set("")
        self.p_beds.set(0)
        self.p_pool.current(0)
        self.p_lo.delete(0, "end")
        self.p_hi.delete(0, "end")
        self.p_status.current(0)
        self._run_property_search()

    def _run_property_search(self):
        def num(entry):
            v = entry.get().strip()
            if not v:
                return None
            try:
                return float(v)
            except ValueError:
                raise ValueError(f"'{v}' is not a valid number.")
        try:
            lo, hi = num(self.p_lo), num(self.p_hi)
        except ValueError as e:
            messagebox.showwarning("Invalid input", str(e))
            return
        beds = int(self.p_beds.get() or 0)
        rows = db.search_properties(
            self.conn,
            city=self.p_city.get().strip() or None,
            district=self.p_dist.get().strip() or None,
            min_price=lo, max_price=hi,
            min_bedrooms=beds or None,
            has_pool=self.POOL_OPTS[self.p_pool.get()],
            status=self.STATUS_OPTS[self.p_status.get()],
        )
        display, iids = [], []
        for r in rows:
            photo = " 📷" if r["has_photo"] else ""
            sold = r["sale_id"] is not None
            display.append((
                r["address"] + photo, r["city"], r["school_district"],
                r["bedrooms"], r["bathrooms"],
                "yes" if r["has_pool"] else "no",
                money(r["list_price"]),
                "Sold" if sold else "For sale",
            ))
            iids.append(r["property_id"])
        self.p_table.set_rows(display, iids=iids)
        self.status.set(f"{len(rows)} propert{'y' if len(rows)==1 else 'ies'} found.")

    def _open_property_detail(self, property_id):
        r = db.get_property(self.conn, int(property_id))
        if not r:
            return
        win = tk.Toplevel(self)
        win.title(r["address"])
        win.transient(self)
        win.resizable(False, False)

        left = ttk.Frame(win, padding=12)
        left.grid(row=0, column=0, sticky="n")

        sold = r["sale_id"] is not None
        lines = [
            (r["address"], ("Segoe UI", 13, "bold")),
            (f"{r['city']} — {r['school_district']} school district", None),
            ("", None),
            (f"List price:  {money(r['list_price'])}", None),
            (f"Bedrooms:  {r['bedrooms']}     Bathrooms:  {r['bathrooms']}", None),
            (f"Pool:  {'yes' if r['has_pool'] else 'no'}", None),
            (f"Listed:  {r['listing_date']}", None),
            (f"Listing agent:  {r['agent_name']}", None),
            (f"Seller:  {r['seller_name']}", None),
            ("", None),
            ("Status:  " + ("SOLD" if sold else "For sale"),
             ("Segoe UI", 10, "bold")),
        ]
        if sold:
            lines += [
                (f"Sold for:  {money(r['sale_price'])} on {r['sale_date']}", None),
                (f"Buyer:  {r['buyer_name']}", None),
            ]
        for text, font in lines:
            ttk.Label(left, text=text, font=font, justify="left").pack(anchor="w")

        if r["photo"]:
            image = Image.open(io.BytesIO(r["photo"]))
            photo_img = ImageTk.PhotoImage(image)
            lbl = ttk.Label(win, image=photo_img, padding=12)
            lbl.image = photo_img            # keep a reference
            lbl.grid(row=0, column=1, sticky="n")
        else:
            ttk.Label(win, text="(no photo on file)", padding=24,
                      foreground="#888").grid(row=0, column=1)

        ttk.Button(win, text="Close", command=win.destroy).grid(
            row=1, column=0, columnspan=2, pady=(0, 10))
        win.grab_set()


    #Sales & Agents
  
    def _tab_sales_agents(self, master):
        f = ttk.Frame(master, padding=10)

        #performance reports
        rpt = ttk.LabelFrame(f, text="Agent performance", padding=8)
        rpt.pack(fill="both", expand=True)

        bar = ttk.Frame(rpt)
        bar.pack(fill="x")
        ttk.Label(bar, text="Year:").pack(side="left")
        self.rpt_year = ttk.Spinbox(bar, from_=2000, to=2030, width=6)
        self.rpt_year.set(2004)
        self.rpt_year.pack(side="left", padx=6)
        ttk.Button(bar, text="Show", command=self._run_reports).pack(side="left")
        self.top_agent_lbl = ttk.Label(bar, text="", font=("Segoe UI", 10, "bold"))
        self.top_agent_lbl.pack(side="left", padx=16)

        self.rpt_table = ResultsTable(
            rpt, ("name", "sales", "avg_price", "avg_days"),
            ("Agent", "# Sales", "Avg Sale Price", "Avg Days on Market"),
            widths={"name": 190, "sales": 80, "avg_price": 150, "avg_days": 170},
            height=7)
        self.rpt_table.pack(fill="both", expand=True, pady=(8, 0))

        # ---- record a sale (bottom) --------------------------------------
        sale = ttk.LabelFrame(f, text="Record a sale", padding=8)
        sale.pack(fill="x", pady=(10, 0))
        self._prop_map, self._buyer_map, self._agent_map = {}, {}, {}

        ttk.Label(sale, text="Property:").grid(row=0, column=0, sticky="e", pady=3, padx=3)
        self.s_prop = ttk.Combobox(sale, width=46, state="readonly")
        self.s_prop.grid(row=0, column=1, columnspan=3, sticky="w", pady=3)
        self.s_prop.bind("<<ComboboxSelected>>", self._prefill_sale_price)

        ttk.Label(sale, text="Buyer:").grid(row=1, column=0, sticky="e", pady=3, padx=3)
        self.s_buyer = ttk.Combobox(sale, width=24, state="readonly")
        self.s_buyer.grid(row=1, column=1, sticky="w", pady=3)

        ttk.Label(sale, text="Selling agent:").grid(row=1, column=2, sticky="e", padx=3)
        self.s_sagent = ttk.Combobox(sale, width=22, state="readonly")
        self.s_sagent.grid(row=1, column=3, sticky="w", pady=3)

        ttk.Label(sale, text="Buyer's agent:").grid(row=2, column=0, sticky="e", pady=3, padx=3)
        self.s_bagent = ttk.Combobox(sale, width=24, state="readonly")
        self.s_bagent.grid(row=2, column=1, sticky="w", pady=3)

        ttk.Label(sale, text="Sale price $:").grid(row=2, column=2, sticky="e", padx=3)
        self.s_price = ttk.Entry(sale, width=16)
        self.s_price.grid(row=2, column=3, sticky="w", pady=3)

        ttk.Label(sale, text="Sale date:").grid(row=3, column=0, sticky="e", pady=3, padx=3)
        self.s_date = ttk.Entry(sale, width=16)
        self.s_date.insert(0, "2004-09-01")
        self.s_date.grid(row=3, column=1, sticky="w", pady=3)
        ttk.Label(sale, text="(YYYY-MM-DD)").grid(row=3, column=2, sticky="w")

        ttk.Button(sale, text="Record sale", command=self._submit_sale).grid(
            row=4, column=1, sticky="w", pady=8)

        self._reload_sale_choices()
        self._run_reports()
        return f

    def _run_reports(self):
        year = int(self.rpt_year.get())
        top = db.top_selling_agent(self.conn, year)
        if top:
            self.top_agent_lbl.config(
                text=f"Top agent {year}:  {top['name']} — "
                     f"{money(top['total_value'])} ({top['num_sales']} sale(s))")
        else:
            self.top_agent_lbl.config(text=f"No sales in {year}.")
        rows = db.agent_sales_stats(self.conn, year)
        self.rpt_table.set_rows([
            (r["name"], r["num_sales"], money(r["avg_price"]),
             f"{r['avg_days_on_market']:.0f}") for r in rows])

    def _reload_sale_choices(self):
        self._prop_map.clear(); self._buyer_map.clear(); self._agent_map.clear()
        prop_vals = []
        for p in db.list_properties_for_sale(self.conn):
            label = f"{p['address']}, {p['city']} ({money(p['list_price'])})"
            self._prop_map[label] = (p["property_id"], p["list_price"])
            prop_vals.append(label)
        self.s_prop["values"] = prop_vals
        if prop_vals:
            self.s_prop.current(0)
        else:
            self.s_prop.set("")

        buyer_vals = []
        for b in db.list_buyers(self.conn):
            self._buyer_map[b["name"]] = b["buyer_id"]
            buyer_vals.append(b["name"])
        self.s_buyer["values"] = buyer_vals
        if buyer_vals:
            self.s_buyer.current(0)

        agent_vals = []
        for a in db.list_agents(self.conn):
            self._agent_map[a["name"]] = a["agent_id"]
            agent_vals.append(a["name"])
        self.s_sagent["values"] = agent_vals
        self.s_bagent["values"] = ["(none)"] + agent_vals
        if agent_vals:
            self.s_sagent.current(0)
        self.s_bagent.current(0)

    def _prefill_sale_price(self, _evt=None):
        sel = self.s_prop.get()
        if sel in self._prop_map:
            self.s_price.delete(0, "end")
            self.s_price.insert(0, str(int(self._prop_map[sel][1])))

    def _submit_sale(self):
        sel = self.s_prop.get()
        if sel not in self._prop_map:
            messagebox.showwarning("Missing", "Select a property to sell.")
            return
        if not self.s_buyer.get() or not self.s_sagent.get():
            messagebox.showwarning("Missing", "Select a buyer and a selling agent.")
            return
        try:
            price = float(self.s_price.get())
        except ValueError:
            messagebox.showwarning("Invalid", "Sale price must be a number.")
            return
        b_agent = self.s_bagent.get()
        buyer_agent_id = None if b_agent == "(none)" else self._agent_map.get(b_agent)
        try:
            sale_id = db.record_sale(
                self.conn,
                self._prop_map[sel][0],
                self._buyer_map[self.s_buyer.get()],
                self._agent_map[self.s_sagent.get()],
                buyer_agent_id,
                price, self.s_date.get().strip())
        except Exception as e:
            messagebox.showerror("Could not record sale", str(e))
            return
        messagebox.showinfo("Sale recorded", f"Sale #{sale_id} recorded.")
        self.s_price.delete(0, "end")
        self._reload_sale_choices()
        self._run_reports()
        self._run_property_search()   # the sold home leaves the for-sale list
        self._show_counts()

    #Manage
    def _tab_manage(self, master):
        f = ttk.Frame(master, padding=10)
        form = ttk.LabelFrame(f, text="Add a new agent", padding=8)
        form.pack(fill="x")

        ttk.Label(form, text="Name:").grid(row=0, column=0, sticky="e", pady=4, padx=3)
        self.a_name = ttk.Entry(form, width=30)
        self.a_name.grid(row=0, column=1, sticky="w", pady=4)

        ttk.Label(form, text="Phone:").grid(row=1, column=0, sticky="e", pady=4, padx=3)
        self.a_phone = ttk.Entry(form, width=30)
        self.a_phone.grid(row=1, column=1, sticky="w", pady=4)

        ttk.Label(form, text="Email:").grid(row=2, column=0, sticky="e", pady=4, padx=3)
        self.a_email = ttk.Entry(form, width=30)
        self.a_email.grid(row=2, column=1, sticky="w", pady=4)

        ttk.Button(form, text="Add agent", command=self._submit_agent).grid(
            row=3, column=1, sticky="w", pady=8)

        ttk.Label(f, text="Current agents:").pack(anchor="w", pady=(10, 2))
        self.a_table = ResultsTable(
            f, ("id", "name"), ("Agent ID", "Name"),
            widths={"id": 80, "name": 280}, height=10)
        self.a_table.pack(fill="both", expand=True)

        self._refresh_agents()
        return f

    def _refresh_agents(self):
        self.a_table.set_rows(
            [(a["agent_id"], a["name"]) for a in db.list_agents(self.conn)])

    def _submit_agent(self):
        name = self.a_name.get().strip()
        if not name:
            messagebox.showwarning("Missing", "Name is required.")
            return
        try:
            agent_id = db.add_agent(
                self.conn, name, self.a_phone.get().strip(),
                self.a_email.get().strip())
        except Exception as e:
            messagebox.showerror("Could not add agent", str(e))
            return
        messagebox.showinfo("Agent added", f"Added agent #{agent_id}: {name}")
        for e in (self.a_name, self.a_phone, self.a_email):
            e.delete(0, "end")
        self._refresh_agents()
        self._reload_sale_choices()
        self._show_counts()


if __name__ == "__main__":
    RealEstateApp().mainloop()
