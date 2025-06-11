from tkinter import *
from tkinter import ttk, messagebox
from datetime import datetime

class DestinationEntryPage:
    def __init__(self, frame, home_frame, conn):
        self.frame = frame
        self.home_frame = home_frame
        self.conn = conn
        self.c = conn.cursor()

        self.used_ranges = set()
        self.range_frames = []

        self.c.execute('''CREATE TABLE IF NOT EXISTS destination_entry (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            destination_id INTEGER,
            letter_note TEXT,
            bill_number TEXT,
            date TEXT,
            to_address TEXT,
            FOREIGN KEY (destination_id) REFERENCES destination(id)
        )''')

        self.c.execute('''CREATE TABLE IF NOT EXISTS range_entry (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            destination_entry_id INTEGER,
            rate_range_id INTEGER,
            total_bags INTEGER,
            total_mt REAL,
            total_mtk REAL,
            total_amount REAL,
            FOREIGN KEY (destination_entry_id) REFERENCES destination_entry(id),
            FOREIGN KEY (rate_range_id) REFERENCES rate_range(id)
        )''')

        self.c.execute('''CREATE TABLE IF NOT EXISTS dealer_entry (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            range_entry_id INTEGER,
            dealer_id INTEGER,
            km REAL,
            no_bags INTEGER,
            rate REAL,
            mt REAL,
            mtk REAL,
            amount REAL,
            FOREIGN KEY (range_entry_id) REFERENCES range_entry(id),
            FOREIGN KEY (dealer_id) REFERENCES dealer(id)
        )''')

        self.build_ui()
        
    def refresh(self):
        # Clear range frames
        for rf in self.range_frames:
            rf.destroy()
        self.range_frames.clear()
        self.used_ranges.clear()

        # Clear form fields
        self.letter_note_entry.delete(0, END)
        self.bill_number_entry.delete(0, END)
        self.date_entry.delete(0, END)
        self.date_entry.insert(0, datetime.now().strftime("%Y-%m-%d"))
        self.to_address_entry.delete(0, END)

        # Reload destination combobox
        self.load_destinations()
        self.destination_cb.set('')

    def build_ui(self):
        top_row = Frame(self.frame)
        top_row.pack(fill='x', padx=10, pady=5)

        # ← Back button
        Button(top_row, text="← Back to Dashboard", command=lambda: self.home_frame.tkraise()).pack(side='left', pady=10)

        # Title centered
        Label(top_row, text="Destination Entry Form", font=("Arial", 16)).pack(side='left', expand=True, pady=10)

        # ⟳ Refresh Switch/Toggle Button
        Button(top_row, text="⟳ Refresh", command=self.refresh).pack(side='right', pady=10)

        form = Frame(self.frame)
        form.pack(pady=10)

        Label(form, text="Destination").grid(row=0, column=0)
        self.destination_cb = ttk.Combobox(form, state="readonly")
        self.destination_cb.grid(row=0, column=1, padx=5)

        Label(form, text="Letter Note").grid(row=1, column=0)
        self.letter_note_entry = Entry(form)
        self.letter_note_entry.grid(row=1, column=1)

        Label(form, text="Bill Number").grid(row=2, column=0)
        self.bill_number_entry = Entry(form)
        self.bill_number_entry.grid(row=2, column=1)

        Label(form, text="Date").grid(row=3, column=0)
        self.date_entry = Entry(form)
        self.date_entry.insert(0, datetime.now().strftime("%Y-%m-%d"))
        self.date_entry.grid(row=3, column=1)

        Label(form, text="To Address").grid(row=4, column=0)
        self.to_address_entry = Entry(form)
        self.to_address_entry.grid(row=4, column=1)

        Button(form, text="+ Add Range", command=self.add_range_frame).grid(row=5, column=0, columnspan=2, pady=10)

        self.range_container = Frame(self.frame)
        self.range_container.pack(fill='both', expand=True)

        self.load_destinations()

    def load_destinations(self):
        self.c.execute("SELECT id, name FROM destination")
        dests = self.c.fetchall()
        self.destination_cb["values"] = [f"{id} - {name}" for id, name in dests]
        self.destination_map = {f"{id} - {name}": id for id, name in dests}

    def add_range_frame(self):
        available_ranges = self.get_available_ranges()
        if not available_ranges:
            messagebox.showinfo("Done", "No more ranges available")
            return

        frame = LabelFrame(self.range_container, text=f"Range Slab", padx=10, pady=10)
        frame.pack(fill='x', padx=10, pady=5)

        range_cb = ttk.Combobox(frame, values=available_ranges, state="readonly")
        range_cb.grid(row=0, column=0, padx=5, pady=5)
        range_cb.set("Select Range")

        Button(frame, text="Select", command=lambda: self.setup_range(frame, range_cb)).grid(row=0, column=1, padx=5)

    def get_available_ranges(self):
        self.c.execute("SELECT id, from_km, to_km, rate, is_mtk FROM rate_range")
        ranges = self.c.fetchall()
        return [f"{id} | {from_km}-{to_km}km @ ₹{rate} ({'MTK' if is_mtk else 'MT'})" 
                for id, from_km, to_km, rate, is_mtk in ranges if id not in self.used_ranges]
        
    def remove_range(self, frame, rate_range_id):
        confirm = messagebox.askyesno("Confirm", "Remove this range and all its dealer entries?")
        if confirm:
            self.used_ranges.discard(rate_range_id)
            frame.destroy()
            self.range_frames.remove(frame)


    def setup_range(self, frame, range_cb):
        val = range_cb.get()
        if val == "Select Range":
            return

        rate_range_id = int(val.split("|")[0].strip())
        self.used_ranges.add(rate_range_id)

        self.c.execute("SELECT from_km, to_km, rate, is_mtk FROM rate_range WHERE id=?", (rate_range_id,))
        from_km, to_km, rate, is_mtk = self.c.fetchone()

        range_label = f"Range: {from_km} – {to_km} km | Rate: ₹{rate} | {'MTK' if is_mtk else 'MT'}"

        # Clear previous selector widgets
        range_cb.grid_remove()
        for widget in frame.grid_slaves():
            if isinstance(widget, Button):
                widget.grid_remove()

        Label(frame, text=range_label).grid(row=0, column=0, columnspan=3, pady=5, sticky='w')

        # Remove range button
        Button(frame, text="Remove This Range", command=lambda: self.remove_range(frame, rate_range_id)).grid(row=0, column=3, sticky='e')

        Label(frame, text="MDA No.").grid(row=1, column=0)
        mda_entry = Entry(frame)
        mda_entry.grid(row=1, column=1)

        Label(frame, text="Date").grid(row=2, column=0)
        date_entry = Entry(frame)
        date_entry.insert(0, datetime.now().strftime("%Y-%m-%d"))
        date_entry.grid(row=2, column=1)

        Label(frame, text="Dealers for this range", font=("Arial", 10, "bold")).grid(row=3, column=0, columnspan=3, pady=(10, 0))

        # Dealer list container
        dealer_frame = Frame(frame)
        dealer_frame.grid(row=4, column=0, columnspan=4, sticky="w")
        selected_dest = self.destination_cb.get()
        destination_id = self.destination_map.get(selected_dest)

        self.c.execute("""
            SELECT id, name, distance FROM dealer
            WHERE distance BETWEEN ? AND ?
            AND destination_id = ?
        """, (from_km, to_km, destination_id))

        dealers = self.c.fetchall()
        dealer_map = {f"{id} - {name} ({distance}km)": (id, distance) for id, name, distance in dealers}

        dealer_rows = []

        totals_label = Label(frame, text="Total Bags: 0 | MT: 0.00 | MTK: 0.00 | ₹0.00", font=("Arial", 10, "bold"), fg="green")
        totals_label.grid(row=6, column=0, columnspan=4, pady=5)

        def update_totals():
            total_bags = sum(row.get('bags', 0) for row in dealer_rows)
            total_mt = sum(row.get('mt', 0.0) for row in dealer_rows)
            total_mtk = sum(row.get('mtk', 0.0) for row in dealer_rows)
            total_amt = sum(row.get('amount', 0.0) for row in dealer_rows)
            totals_label.config(
                text=f"Total Bags: {total_bags} | MT: {total_mt:.2f} | MTK: {total_mtk:.2f} | ₹{total_amt:.2f}"
            )

        def add_dealer_row():
            row_idx = len(dealer_rows)
            row = {}

            dealer_var = StringVar()
            dealer_cb = ttk.Combobox(dealer_frame, textvariable=dealer_var, values=list(dealer_map.keys()), state="normal", width=30)
            dealer_cb.grid(row=row_idx, column=0, padx=2, pady=2)
            row['dealer_cb'] = dealer_cb

            def filter_dealers(event):
                typed = dealer_var.get().lower()
                filtered = [k for k in dealer_map.keys() if typed in k.lower()]
                dealer_cb['values'] = filtered
                if filtered:
                    dealer_cb.event_generate('<Down>')

            dealer_cb.bind('<KeyRelease>', filter_dealers)

            bags_entry = Entry(dealer_frame, width=5)
            bags_entry.grid(row=row_idx, column=1, padx=2)
            row['bags_entry'] = bags_entry

            result_lbl = Label(dealer_frame, text="", width=40, anchor='w')
            result_lbl.grid(row=row_idx, column=2, padx=2)
            row['result_lbl'] = result_lbl

            def calculate_row():
                selected = dealer_cb.get()
                if not selected or selected not in dealer_map:
                    result_lbl.config(text="Select valid dealer")
                    return

                # Prevent duplicate
                for existing_row in dealer_rows:
                    if existing_row is row:
                        continue
                    if existing_row.get('dealer_cb') and existing_row['dealer_cb'].get() == selected:
                        result_lbl.config(text="Duplicate dealer")
                        return

                dealer_id, km = dealer_map[selected]
                try:
                    bags = int(bags_entry.get())
                    mt = bags * 0.05
                    mtk = mt * km
                    amount = rate * (mtk if is_mtk else mt)
                    result_lbl.config(text=f"MT: {mt:.2f} | KM: {km} | MTK: {mtk:.2f} | ₹{amount:.2f}")
                    row.update({
                        'dealer_id': dealer_id,
                        'km': km,
                        'bags': bags,
                        'mt': mt,
                        'mtk': mtk,
                        'amount': amount
                    })
                    update_totals()
                except ValueError:
                    result_lbl.config(text="Invalid input")

            # ❌ Remove button
            def remove_dealer_row():
                for widget in [dealer_cb, bags_entry, result_lbl, calc_btn, remove_btn]:
                    widget.destroy()
                dealer_rows.remove(row)
                update_totals()

            calc_btn = Button(dealer_frame, text="Calc", command=calculate_row)
            calc_btn.grid(row=row_idx, column=3)

            remove_btn = Button(dealer_frame, text="❌", command=remove_dealer_row)
            remove_btn.grid(row=row_idx, column=4)

            dealer_rows.append(row)

        Button(frame, text="+ Add Dealer", command=add_dealer_row).grid(row=5, column=0, columnspan=2, pady=5)
        add_dealer_row()

        # Save for future use (e.g. DB save)
        frame.rate_range_id = rate_range_id
        frame.dealer_rows = dealer_rows
        frame.update_totals = update_totals
        frame.mda_entry = mda_entry
        frame.date_entry = date_entry
        self.range_frames.append(frame)
