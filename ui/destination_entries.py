from tkinter import *
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
import os
import json
from tkcalendar import DateEntry


class DestinationEntryPage:
    def __init__(self, frame, home_frame, conn):
        self.frame = frame
        self.home_frame = home_frame
        self.conn = conn
        self.c = conn.cursor()
        self.editing_mode = False
        self.destination_entry_id = None
        self.range_entry_ids = {}   # key = range_index, value = range_entry_id
        self.dealer_entry_ids = {}  # key = (range_index, dealer_index), value = dealer_entry_id
        self.save_button = Button(self.frame, text="💾 Save Entry", font=("Arial", 12), command=self.save_entries)
        self.print_button = Button(self.frame, text="🖨️ Print Entry", font=("Arial", 12), command=self.print_entry)
        
        # Bind to virtual event so this page can refresh when shown
        # (the main app will generate <<ShowFrame>> when raising frames)
        self.frame.bind("<<ShowFrame>>", lambda e: self.refresh())

        self.used_ranges = set()
        self.range_frames = []

        self.c.execute('''CREATE TABLE IF NOT EXISTS destination_entry (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            destination_id INTEGER,
            letter_note TEXT,
            bill_number TEXT,
            date TEXT,
            to_address TEXT,
            main_bill_id INTEGER DEFAULT NULL,
            FOREIGN KEY (destination_id) REFERENCES destination(id),
            FOREIGN KEY (main_bill_id) REFERENCES main_bill(id)
        )''')

        self.c.execute('''CREATE TABLE IF NOT EXISTS range_entry (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            destination_entry_id INTEGER,
            rate_range_id INTEGER,
            rate REAL,  
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
            despatched_to TEXT,
            km REAL,
            no_bags INTEGER,
            rate REAL,
            mt REAL,
            mtk REAL,
            amount REAL,
            mda_number TEXT,
            date TEXT,
            description TEXT DEFAULT 'FACTOM FOS',
            remarks TEXT,
            FOREIGN KEY (range_entry_id) REFERENCES range_entry(id),
            FOREIGN KEY (dealer_id) REFERENCES dealer(id)
        )''')

        self.build_ui()

    def build_ui(self):
        top_row = Frame(self.frame)
        top_row.pack(fill='x', padx=10, pady=5)

        # ← Back button
        Button(top_row, text="← Back to Dashboard", command=lambda: self.home_frame.tkraise()).pack(side='left', pady=10)
        Button(top_row, text="⟳ Clear", command=self.clear).pack(side='left', pady=10, padx=5)

        # Title centered
        Label(top_row, text="Destination Entry Form", font=("Arial", 16)).pack(side='left', expand=True, pady=10)

        # ⟳ Refresh Switch/Toggle Button
        Button(top_row, text="⟳ Refresh", command=self.refresh).pack(side='right', pady=10)

        form = Frame(self.frame)
        form.pack(pady=10)
        
        form.grid_columnconfigure(0, weight=1, uniform="col")
        form.grid_columnconfigure(1, weight=3, uniform="col")

        Label(form, text="Destination").grid(row=0, column=0)
        self.destination_cb = ttk.Combobox(form, state="readonly", width=60)
        self.destination_cb.grid(row=0, column=1, padx=5)

        Label(form, text="Letter Note").grid(row=1, column=0)
        self.letter_note_text = Text(form, height=5, width=100, pady=5)
        self.letter_note_text.grid(row=1, column=1, pady=5)

        Label(form, text="Bill Number").grid(row=2, column=0)
        self.bill_number_entry = Entry(form)
        self.bill_number_entry.grid(row=2, column=1)

        Label(form, text="Date").grid(row=3, column=0)
        self.date_entry = DateEntry(form, width=37, date_pattern='dd-mm-yyyy', 
                                    background='darkblue', foreground='white', borderwidth=2)
        self.date_entry.grid(row=3, column=1)

        Label(form, text="To Address").grid(row=4, column=0, pady=5)
        self.to_address_text = Text(form, height=5, width=100, pady=5)
        self.to_address_text.grid(row=4, column=1, pady=5)

        Button(form, text="+ Add Range", command=self.add_range_frame).grid(row=5, column=0, columnspan=2, pady=10)
        
        dealer_select_frame = Frame(form)
        dealer_select_frame.grid(row=6, column=0, columnspan=2, pady=5)

        Label(dealer_select_frame, text="Search Dealer").grid(row=0, column=0, padx=5)
        self.dealer_search_var = StringVar()
        self.dealer_search_cb = ttk.Combobox(dealer_select_frame, textvariable=self.dealer_search_var, width=70)
        self.dealer_search_cb.bind('<KeyRelease>', self.filter_dealers)
        self.dealer_search_cb.bind('<Button-1>', lambda e: self.dealer_search_cb.event_generate('<Down>'))
        self.dealer_search_cb.bind('<Return>', lambda e: self.dealer_search_cb.event_generate('<Down>'))
        self.dealer_search_cb.grid(row=0, column=1, padx=5)
        
        self.destination_cb.bind("<<ComboboxSelected>>", self.load_dealers_for_destination)

        Button(dealer_select_frame, text="➕ Add Selected Dealer", command=self.add_dealer_by_search).grid(row=0, column=3, padx=5)
        
        Button(
            dealer_select_frame,
            text="✖",
            width=3,
            command=lambda: self.clear_dealer_search() 
        ).grid(row=0, column=2, padx=2)

        self.range_container = Frame(self.frame)
        self.range_container.pack(fill='both', expand=True)

        self.load_destinations()
        self.load_entry_cache()
        self.filter_dealers()
        self.save_button.pack(pady=10)
        
    def clear_dealer_search(self):
        self.dealer_search_var.set("")

        # Reload full dealer list again
        self.filter_dealers()

    
    def filter_dealers(self, event=None):
        """Filter dealer combobox options based on user input."""
        
        # if no dealer_map yet, nothing to filter
        if not hasattr(self, 'dealer_map') or not self.dealer_map:
            return

        # preserve current text and caret position
        current_text = self.dealer_search_var.get()
        try:
            caret_pos = self.dealer_search_cb.index(tk.INSERT)
        except Exception:
            caret_pos = len(current_text)

        low = current_text.strip().lower()

        # filter values by substring match
        all_keys = list(self.dealer_map.keys())
        if low == "":
            filtered = all_keys
        else:
            filtered = [k for k in all_keys if low in k.lower()]

        # update combobox values without changing the text the user is typing
        self.dealer_search_cb['values'] = filtered

        # restore typed text and caret, and keep focus
        self.dealer_search_var.set(current_text)
        self.dealer_search_cb.focus_set()
        # ensure index is within bounds
        caret_pos = max(0, min(len(current_text), caret_pos))
        try:
            self.dealer_search_cb.icursor(caret_pos)
        except Exception:
            pass

        # Optionally open dropdown when there are matches and user has typed >=1 char:
        # (uncomment the next two lines if you want the dropdown to auto-open after typing)
        # if filtered and len(current_text) >= 1:
        #     self.dealer_search_cb.event_generate('<Down>')
        
    def select_current_dealer(self, event=None):
        """When user presses Enter, confirm dealer selection."""
        current_text = self.dealer_search_var.get().strip()
        if not current_text:
            return

        # If the text exactly matches a dealer key, select that dealer
        if current_text in self.dealer_map:
            self.dealer_search_cb.set(current_text)
            self.add_dealer_by_search()
            return

        # Otherwise, check if there's a close match
        matches = [k for k in self.dealer_map.keys() if current_text.lower() in k.lower()]
        if matches:
            self.dealer_search_cb.set(matches[0])
            self.add_dealer_by_search()

    def save_entry_cache(self):
        cache = {
            "destination": self.destination_cb.get(),
            "letter_note": self.letter_note_text.get("1.0", "end").strip(),
            "bill_number": self.bill_number_entry.get().strip(),
            "date": self.date_entry.get().strip(),
            "to_address": self.to_address_text.get("1.0", "end").strip(),
        }

        with open("destination_entry_cache.json", "w") as f:
            json.dump(cache, f)
            
    def load_entry_cache(self):
        if os.path.exists("destination_entry_cache.json"):
            with open("destination_entry_cache.json", "r") as f:
                data = json.load(f)

            self.destination_cb.set(data.get("destination", ""))
            self.letter_note_text.delete("1.0", "end")
            self.letter_note_text.insert("1.0", data.get("letter_note", ""))

            self.bill_number_entry.delete(0, "end")
            self.bill_number_entry.insert(0, data.get("bill_number", ""))

            self.date_entry.delete(0, "end")
            self.date_entry.insert(0, data.get("date", datetime.now().strftime("%Y-%m-%d")))

            self.to_address_text.delete("1.0", "end")
            self.to_address_text.insert("1.0", data.get("to_address", ""))

    def save_entries(self):
        selected_dest = self.destination_cb.get()
        if not selected_dest:
            messagebox.showerror("Error", "Please select a destination.")
            return

        destination_id = self.destination_map[selected_dest]
        letter_note = self.letter_note_text.get("1.0", END).strip()
        bill_number = self.bill_number_entry.get().strip()
        date = self.date_entry.get().strip()
        to_address = self.to_address_text.get("1.0", END).strip()

        try:
            self.c.execute("""
                INSERT INTO destination_entry (destination_id, letter_note, bill_number, date, to_address)
                VALUES (?, ?, ?, ?, ?)
            """, (destination_id, letter_note, bill_number, date, to_address))
            destination_entry_id = self.c.lastrowid
            
            saved_range_ids = {}
            saved_dealer_ids = {}

            for range_index, frame in enumerate(self.range_frames):
                rate_range_id = frame.rate_range_id
                rate = frame.rate
                dealer_rows = frame.dealer_rows

                total_bags = sum(row.get('bags', 0) for row in dealer_rows)
                total_mt = sum(row.get('mt', 0.0) for row in dealer_rows)
                total_mtk = sum(row.get('mtk', 0.0) for row in dealer_rows)
                total_amount = sum(row.get('amount', 0.0) for row in dealer_rows)

                # Insert range_entry with rate
                self.c.execute("""
                    INSERT INTO range_entry (
                        destination_entry_id, rate_range_id, rate, total_bags,
                        total_mt, total_mtk, total_amount
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    destination_entry_id, rate_range_id, rate,
                    total_bags, total_mt, total_mtk, total_amount
                ))
                range_entry_id = self.c.lastrowid
                saved_range_ids[range_index] = range_entry_id

                for dealer_index, row in enumerate(dealer_rows):
                    if 'dealer_id' not in row or 'bags' not in row:
                        continue

                    self.c.execute("""
                        INSERT INTO dealer_entry (
                            range_entry_id, dealer_id, despatched_to, km, no_bags, rate,
                            mt, mtk, amount, mda_number, date, description, remarks
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        range_entry_id, row['dealer_id'], row['despatched_to'], row['km'], row['bags'],
                        frame.rate, row['mt'], row['mtk'], row['amount'], 
                        row['mda_number'], row['date'], 
                        row.get('description', 'FACTOM FOS'), row.get('remarks', '')
                    ))
                    dealer_entry_id = self.c.lastrowid
                    saved_dealer_ids[(range_index, dealer_index)] = dealer_entry_id

            self.conn.commit()
            messagebox.showinfo("Success", "Destination Entry saved successfully.")

            self.editing_mode = True
            self.destination_entry_id = destination_entry_id
            self.range_entry_ids = saved_range_ids
            self.dealer_entry_ids = saved_dealer_ids
            self.update_buttons_to_edit_mode()
            self.save_entry_cache()

        except Exception as e:
            self.conn.rollback()
            messagebox.showerror("Error", f"Failed to save entry:\n{e}")

    def load_destinations(self):
        self.c.execute("SELECT id, name FROM destination")
        dests = self.c.fetchall()
        self.destination_cb["values"] = [f"{id} - {name}" for id, name in dests]
        self.destination_map = {f"{id} - {name}": id for id, name in dests}

        # Bind selection
        self.destination_cb.bind("<<ComboboxSelected>>", self.load_dealers_for_destination)

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
        frame.range_cb = range_cb
        frame.dealer_rows = []
        frame.update_totals = lambda: None
        frame.rate = 0
        self.range_frames.append(frame)

    def get_available_ranges(self):
        self.c.execute("SELECT id, from_km, to_km, rate, is_mtk FROM rate_range")
        ranges = self.c.fetchall()
        return [f"{id} | {from_km}-{to_km}km @ ₹{rate} ({'MTK' if is_mtk else 'MT'})" 
                for id, from_km, to_km, rate, is_mtk in ranges if id not in self.used_ranges]

    def remove_range(self, frame, rate_range_id):
        confirm = messagebox.askyesno("Confirm", "Remove this range and all its dealer entries?")
        if confirm:
            # Remove UI references
            self.used_ranges.discard(rate_range_id)
            frame.destroy()
            self.range_frames.remove(frame)

            # Ensure we are editing an existing destination entry
            if self.editing_mode and self.destination_entry_id:
                # Get the corresponding range_entry.id
                self.c.execute('''SELECT id FROM range_entry 
                                WHERE destination_entry_id = ? AND rate_range_id = ?''',
                            (self.destination_entry_id, rate_range_id))
                result = self.c.fetchone()
                if result:
                    range_entry_id = result[0]
                    
                    # Delete all dealer entries linked to this range entry
                    self.c.execute("DELETE FROM dealer_entry WHERE range_entry_id = ?", (range_entry_id,))

                    # Delete the range entry
                    self.c.execute("DELETE FROM range_entry WHERE id = ?", (range_entry_id,))

                    self.conn.commit()

    def setup_range(self, frame, range_cb=None, rate_range_id=None):
        # CASE 1: Called from UI (range combobox selection)
        if range_cb is not None:
            val = range_cb.get()
            if val == "Select Range":
                return
            rate_range_id = int(val.split("|")[0].strip())

            val = range_cb.get()
        # CASE 2: Called programmatically (Add Dealer by Search)
        elif rate_range_id is None:
            raise ValueError("setup_range() requires either range_cb or rate_range_id")
        
        self.used_ranges.add(rate_range_id)
        
        # Fetch range details
        self.c.execute("SELECT from_km, to_km, rate, is_mtk FROM rate_range WHERE id=?", (rate_range_id,))
        from_km, to_km, rate, is_mtk = self.c.fetchone()
        
        # Remove combobox UI if exists
        if range_cb is not None:
            range_cb.grid_remove()
            for widget in frame.grid_slaves():
                if isinstance(widget, Button):
                    widget.grid_remove()

        range_label = f"Range: {from_km} – {to_km} km | Rate: ₹{rate:.2f} | {'MTK' if is_mtk else 'MT'}"
        
        Label(frame, text=range_label).grid(row=0, column=0, columnspan=4, pady=5, sticky='w')
        Button(frame, text="Remove This Range", command=lambda: self.remove_range(frame, rate_range_id)).grid(row=0, column=4, sticky='e')

        Label(frame, text="Dealers for this range", font=("Arial", 10, "bold")).grid(row=1, column=0, columnspan=6, pady=(10, 0))
        dealer_frame = Frame(frame)

        Label(dealer_frame, text="Dealer", font=("Arial", 9, "bold")).grid(row=0, column=0)
        Label(dealer_frame, text="Despatched To", font=("Arial", 9, "bold")).grid(row=0, column=1)   # new column
        Label(dealer_frame, text="MDA No.", font=("Arial", 9, "bold")).grid(row=0, column=2)
        Label(dealer_frame, text="Date", font=("Arial", 9, "bold")).grid(row=0, column=3)
        Label(dealer_frame, text="Bags", font=("Arial", 9, "bold")).grid(row=0, column=4)
        Label(dealer_frame, text="Description", font=("Arial", 9, "bold")).grid(row=0, column=5)
        Label(dealer_frame, text="Remarks", font=("Arial", 9, "bold")).grid(row=0, column=6)
        Label(dealer_frame, text="Details", font=("Arial", 9, "bold")).grid(row=0, column=7)
        Label(dealer_frame, text="Actions", font=("Arial", 9, "bold")).grid(row=0, column=8)

        dealer_frame.grid(row=4, column=0, columnspan=6, sticky="w")

        selected_dest = self.destination_cb.get()
        destination_id = self.destination_map.get(selected_dest)

        self.c.execute("""
            SELECT id, name, place, distance FROM dealer
            WHERE distance BETWEEN ? AND ? AND destination_id = ?
        """, (from_km, to_km, destination_id))
        dealers = self.c.fetchall()
        dealer_map = {
            f"{id} - {name} ({distance}km)": (id, name, place, distance)
            for id, name, place, distance in dealers
        }

        dealer_rows = []

        totals_label = Label(frame, text="Total Bags: 0 | MT: 0.00 | MTK: 0.00 | ₹0.00", font=("Arial", 10, "bold"), fg="green")
        totals_label.grid(row=5, column=0, columnspan=6, pady=5)

        def update_totals():
            total_bags = sum(row.get('bags', 0) for row in dealer_rows)
            total_mt = sum(row.get('mt', 0.0) for row in dealer_rows)
            total_mtk = sum(row.get('mtk', 0.0) for row in dealer_rows)
            total_amt = sum(row.get('amount', 0.0) for row in dealer_rows)
            totals_label.config(
                text=f"Total Bags: {total_bags} | MT: {total_mt:.2f} | MTK: {total_mtk:.2f} | ₹{total_amt:.2f}"
            )

        def add_dealer_row():
            row_idx = len(dealer_rows) + 1
            row = {}

            dealer_var = StringVar()
            dealer_cb = ttk.Combobox(dealer_frame, textvariable=dealer_var, values=list(dealer_map.keys()), state="customNormal", width=30)
            dealer_cb.grid(row=row_idx, column=0, padx=2, pady=2)
            row['dealer_cb'] = dealer_cb

            despatched_entry = Entry(dealer_frame, width=30)
            despatched_entry.grid(row=row_idx, column=1, padx=2)
            row['despatched_entry'] = despatched_entry

            def on_dealer_selected(event=None):
                selected = dealer_cb.get()
                if selected in dealer_map:
                    _, name, place, _ = dealer_map[selected]
                    despatched_entry.delete(0, END)
                    despatched_entry.insert(0, f"{name}, {place}")

            dealer_cb.bind("<<ComboboxSelected>>", on_dealer_selected)

            def filter_dealers(event):
                typed = dealer_var.get().lower()
                filtered = [k for k in dealer_map.keys() if typed in k.lower()]
                dealer_cb['values'] = filtered
                if filtered:
                    dealer_cb.event_generate('<Down>')

            dealer_cb.bind('<KeyRelease>', filter_dealers)

            mda_entry = Entry(dealer_frame, width=20)
            mda_entry.grid(row=row_idx, column=2)
            row['mda_entry'] = mda_entry

            date_entry = Entry(dealer_frame, width=12)
            date_entry.insert(0, datetime.now().strftime("%Y-%m-%d"))
            date_entry.grid(row=row_idx, column=3)
            row['date_entry'] = date_entry

            bags_entry = Entry(dealer_frame, width=5)
            bags_entry.grid(row=row_idx, column=4, padx=2)
            row['bags_entry'] = bags_entry

            desc_entry = Entry(dealer_frame, width=15)
            desc_entry.insert(0, "FACTOM FOS")
            desc_entry.grid(row=row_idx, column=5, padx=2)
            row['desc_entry'] = desc_entry

            remarks_entry = Entry(dealer_frame, width=15)
            remarks_entry.grid(row=row_idx, column=6, padx=2)
            row['remarks_entry'] = remarks_entry

            result_lbl = Label(dealer_frame, text="", width=40, anchor='w')
            result_lbl.grid(row=row_idx, column=7, padx=2)
            row['result_lbl'] = result_lbl

            def calculate_row():
                selected = dealer_cb.get()
                if not selected or selected not in dealer_map:
                    result_lbl.config(text="Select valid dealer")
                    return

                dealer_id, name, place, km = dealer_map[selected]
                try:
                    bags = int(bags_entry.get())
                    mt = bags * 0.05
                    mtk = mt * km
                    amount = rate * (mtk if is_mtk else mt)
                    result_lbl.config(text=f"MT: {mt:.2f} | KM: {km} | MTK: {mtk:.2f} | ₹{amount:.2f}")
                    row.update({
                        'dealer_id': dealer_id,
                        'dealer_name': name,
                        'dealer_place': place,
                        'despatched_to': despatched_entry.get(),
                        'km': km,
                        'bags': bags,
                        'mt': mt,
                        'mtk': mtk,
                        'amount': amount,
                        'mda_number': mda_entry.get(),
                        'date': date_entry.get(),
                        'description': desc_entry.get(),
                        'remarks': remarks_entry.get()
                    })
                    update_totals()
                except ValueError:
                    result_lbl.config(text="Invalid input")

            def remove_dealer_row():
                for widget in [dealer_cb, despatched_entry, mda_entry, date_entry, bags_entry,
                            desc_entry, remarks_entry, result_lbl, calc_btn, remove_btn]:
                    widget.destroy()
                dealer_rows.remove(row)
                update_totals()

            calc_btn = Button(dealer_frame, text="Calc", command=calculate_row)
            calc_btn.grid(row=row_idx, column=8)

            remove_btn = Button(dealer_frame, text="❌", command=remove_dealer_row)
            remove_btn.grid(row=row_idx, column=9)

            dealer_rows.append(row)

        Button(frame, text="+ Add Dealer", command=add_dealer_row).grid(row=6, column=0, columnspan=2, pady=5)
        add_dealer_row()

        frame.rate_range_id = rate_range_id
        frame.dealer_rows = dealer_rows
        frame.update_totals = update_totals
        frame.add_dealer_row = add_dealer_row
        frame.rate = rate
        frame.dealer_map = dealer_map

    def update_buttons_to_edit_mode(self):
        self.save_button.destroy()
        self.save_button = Button(self.frame, text="💾 Save Changes", command=self.save_changes)
        self.save_button.pack(pady=10)
        self.print_button.pack(pady=10)

        Button(self.frame, text="➕ Add New Entry", command=lambda:self.clear(False)).pack(pady=20)
    
    def save_changes(self):
        letter_note = self.letter_note_text.get("1.0", END).strip()
        bill_number = self.bill_number_entry.get().strip()
        date = self.date_entry.get().strip()
        to_address = self.to_address_text.get("1.0", END).strip()

        if not self.editing_mode or not self.destination_entry_id:
            messagebox.showwarning("Error", "Not in edit mode or missing destination entry.")
            return

        try:
            # Update destination_entry
            self.c.execute("""
                UPDATE destination_entry
                SET date=?, to_address=?, bill_number=?, letter_note=?
                WHERE id=?
            """, (
                date, to_address, bill_number, letter_note, self.destination_entry_id
            ))

            current_dealer_ids = set()
            new_dealer_entry_ids = {}
            new_range_entry_ids = {}

            for range_index, frame in enumerate(self.range_frames):
                rate_range_id = frame.rate_range_id
                rate = frame.rate
                dealer_rows = frame.dealer_rows

                # Check if range_entry already exists or is new
                range_entry_id = self.range_entry_ids.get(range_index)
                is_new_range = range_entry_id is None

                # Calculate totals
                total_bags = sum(row.get('bags', 0) for row in dealer_rows)
                total_mt = sum(row.get('mt', 0.0) for row in dealer_rows)
                total_mtk = sum(row.get('mtk', 0.0) for row in dealer_rows)
                total_amount = sum(row.get('amount', 0.0) for row in dealer_rows)

                if is_new_range:
                    # Insert new range_entry with rate
                    self.c.execute("""
                        INSERT INTO range_entry (
                            destination_entry_id, rate_range_id, rate,
                            total_bags, total_mt, total_mtk, total_amount
                        ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (
                        self.destination_entry_id, rate_range_id, rate,
                        total_bags, total_mt, total_mtk, total_amount
                    ))
                    range_entry_id = self.c.lastrowid
                else:
                    # Update existing range_entry with rate
                    self.c.execute("""
                        UPDATE range_entry
                        SET rate=?, total_bags=?, total_mt=?, total_mtk=?, total_amount=?
                        WHERE id=?
                    """, (
                        rate, total_bags, total_mt, total_mtk, total_amount, range_entry_id
                    ))

                new_range_entry_ids[range_index] = range_entry_id

                existing_ids_for_range = set()

                for dealer_index, row in enumerate(dealer_rows):
                    dealer_entry_id = self.dealer_entry_ids.get((range_index, dealer_index))

                    if dealer_entry_id:
                        # Update existing dealer_entry
                        self.c.execute("""
                            UPDATE dealer_entry
                            SET dealer_id=?, despatched_to=?, km=?, no_bags=?, rate=?,
                                mt=?, mtk=?, amount=?, mda_number=?, date=?,
                                description=?, remarks=?
                            WHERE id=?
                        """, (
                            row['dealer_id'], row['despatched_to'], row['km'], row['bags'], frame.rate,
                            row['mt'], row['mtk'], row['amount'],
                            row['mda_number'], row['date'],
                            row.get('description', 'FACTOM FOS'), row.get('remarks', ''),
                            dealer_entry_id
                        ))
                    else:
                        # Insert new dealer_entry
                        self.c.execute("""
                            INSERT INTO dealer_entry (
                                range_entry_id, dealer_id, despatched_to, km, no_bags, rate,
                                mt, mtk, amount, mda_number, date, description, remarks
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (
                            range_entry_id, row['dealer_id'], row['despatched_to'], row['km'], row['bags'],
                            frame.rate, row['mt'], row['mtk'], row['amount'],
                            row['mda_number'], row['date'],
                            row.get('description', 'FACTOM FOS'), row.get('remarks', '')
                        ))
                        dealer_entry_id = self.c.lastrowid

                    new_dealer_entry_ids[(range_index, dealer_index)] = dealer_entry_id
                    current_dealer_ids.add(dealer_entry_id)
                    existing_ids_for_range.add(dealer_entry_id)

                # Delete old dealer entries no longer present in UI
                self.c.execute("SELECT id FROM dealer_entry WHERE range_entry_id = ?", (range_entry_id,))
                all_db_ids = {r[0] for r in self.c.fetchall()}
                to_delete_ids = all_db_ids - existing_ids_for_range
                for del_id in to_delete_ids:
                    self.c.execute("DELETE FROM dealer_entry WHERE id = ?", (del_id,))

            self.conn.commit()

            # Update stored IDs to match the new state
            self.range_entry_ids = new_range_entry_ids
            self.dealer_entry_ids = new_dealer_entry_ids

            messagebox.showinfo("Success", "Changes saved successfully.")
        except Exception as e:
            self.conn.rollback()
            messagebox.showerror("Error", f"Failed to update:\n{e}")
    
    def refresh(self):
        self.load_destinations()
        for frame in self.range_frames:
            if hasattr(frame, 'dealer_map'):
                self.refresh_dealers_for_frame(frame)
                
        # After loading destination and entry cache
        selected = self.destination_cb.get()
        if selected:
            self.load_dealers_for_destination() 
        self.filter_dealers()   # This will now work because dealer_map exists
         
    def clear(self, stat=True):
        if self.editing_mode and stat:
            self.load_existing_entry(self.destination_entry_id)
        else:            
            self.destination_entry_id = None
            self.range_entry_ids.clear()
            self.dealer_entry_ids.clear()

            for widget in self.frame.winfo_children():
                widget.destroy()

            self.__init__(self.frame, self.home_frame, self.conn)

    def refresh_dealers_for_frame(self, frame):
        """Refresh dealer list for a specific range slab frame"""
        rate_range_id = frame.rate_range_id

        # get range slab limits
        self.c.execute("SELECT from_km, to_km FROM rate_range WHERE id=?", (rate_range_id,))
        from_km, to_km = self.c.fetchone()

        selected_dest = self.destination_cb.get()
        destination_id = self.destination_map.get(selected_dest)

        # fetch updated dealers from DB
        self.c.execute("""
            SELECT id, name, place, distance FROM dealer
            WHERE distance BETWEEN ? AND ? AND destination_id = ?
        """, (from_km, to_km, destination_id))
        dealers = self.c.fetchall()

        dealer_map = {
            f"{id} - {name} ({distance}km)": (id, name, place, distance)
            for id, name, place, distance in dealers
        }
        frame.dealer_map = dealer_map

        # update all existing dealer comboboxes in this frame
        for row in frame.dealer_rows:
            if 'dealer_cb' in row:
                row['dealer_cb']['values'] = list(dealer_map.keys())
    
    def load_dealers_for_destination(self, event=None):
        selected_dest = self.destination_cb.get()
        if not selected_dest:
            return

        destination_id = self.destination_map[selected_dest]

        self.c.execute("SELECT id, name, place, distance FROM dealer WHERE destination_id=?", (destination_id,))
        dealers = self.c.fetchall()

        if not dealers:
            self.dealer_search_cb['values'] = []
        # Load dealers for this destination
            self.dealer_map = {}
            self.dealer_search_var.set("")
            messagebox.showinfo("No Dealers", "No dealers found for this destination.")
            return

        # Update dealer map and dropdown values
        self.dealer_map = {
            f"{id} - {name} ({place}) [{distance} km]": (id, name, place, distance)
            for id, name, place, distance in dealers
        }
        self.dealer_search_cb['values'] = list(self.dealer_map.keys())

        # Clear old text and set focus to dealer search box
        self.dealer_search_var.set("")
        self.dealer_search_cb.focus_set()

        # 👇 Open the DEALER dropdown — not the destination one
        if self.dealer_map:
            self.frame.after(100, lambda: self.dealer_search_cb.event_generate('<Down>'))
        
        self.dealer_map_search = {
            f"{id} - {name} ({place}) [{distance} km]": (id, name, place, distance)
            for id, name, place, distance in dealers
        }
        self.dealer_search_cb["values"] = list(self.dealer_map_search.keys())

    def add_dealer_by_search(self):
        selected = self.dealer_search_cb.get()
        if not selected or selected not in self.dealer_map_search:
            messagebox.showerror("Error", "Please select a valid dealer.")
            return

        dealer_id, name, place, distance = self.dealer_map_search[selected]

        # Find rate range for dealer distance
        self.c.execute("SELECT id, from_km, to_km, rate, is_mtk FROM rate_range WHERE ? BETWEEN from_km AND to_km", (distance,))
        range_row = self.c.fetchone()
        if not range_row:
            messagebox.showerror("Error", f"No rate range found for {distance} km.")
            return

        rate_range_id, from_km, to_km, rate, is_mtk = range_row

        # Check if range frame exists, else create it
        frame = None
        for rf in self.range_frames:
            if getattr(rf, 'rate_range_id', None) == rate_range_id:
                frame = rf
                break

        if frame is None:
            # Automatically create the range frame for this slab
            frame = LabelFrame(self.range_container, text=f"Range Slab", padx=10, pady=10)
            frame.pack(fill='x', padx=10, pady=5)
            self.used_ranges.add(rate_range_id)
            self.setup_range(frame, rate_range_id=rate_range_id)
            # self.setup_range(frame, range_cb=None)  # We'll modify setup_range to support None
            frame.rate_range_id = rate_range_id
            frame.rate = rate
            self.range_frames.append(frame)

        # Now add dealer row into that range’s table
        self.add_dealer_to_range(frame, dealer_id, name, place, distance, rate, is_mtk)
    
    def add_dealer_to_range(self, frame, dealer_id, name, place, km, rate, is_mtk):
        """
        Add dealer into slab:
        - If slab was newly created (setup_range already made 1st row) → use that row.
        - If slab exists → add a new dealer row.
        No calculation here.
        """

        dealer_rows = frame.dealer_rows   # already created in setup_range()
        dealer_map = frame.dealer_map     # created inside setup_range()

        # ✅ If this slab already existed, create a new dealer row
        if getattr(frame, "initialized", False):
            frame.add_dealer_row()
        else:
            # First time setup_range is used: Do NOT create a new row
            frame.initialized = True      # mark as initialized

        # Get last row (either created just now, or the initial one from setup_range)
        row = dealer_rows[-1]

        # Build key as stored in dealer dropdown
        key = f"{dealer_id} - {name} ({km}km)"

        # ✅ Select dealer in combobox
        if key in dealer_map:
            row["dealer_cb"].set(key)

        # ✅ Set dispatched-to text
        row["despatched_entry"].delete(0, END)
        row["despatched_entry"].insert(0, f"{name}, {place}")

        # Save values in row dictionary (used later when saving to DB)
        row.update({
            "dealer_id": dealer_id,
            "dealer_name": name,
            "dealer_place": place,
            "km": km,
            "rate": rate,
            "is_mtk": is_mtk,
        })

    def load_existing_entry(self, destination_entry_id):
        self.clear(False)
        self.editing_mode = True
        self.destination_entry_id = destination_entry_id
        self.range_entry_ids = {}
        self.dealer_entry_ids = {}
        self.used_ranges = set()

        # Fetch and set header fields
        self.c.execute("""
            SELECT destination_id, letter_note, bill_number, date, to_address
            FROM destination_entry WHERE id = ?
        """, (destination_entry_id,))
        row = self.c.fetchone()
        if not row:
            messagebox.showerror("Error", "Destination entry not found.")
            return

        destination_id, letter_note, bill_number, date, to_address = row
        dest_name = next((name for name, id_ in self.destination_map.items() if id_ == destination_id), None)
        if dest_name:
            self.destination_cb.set(dest_name)

        self.letter_note_text.delete("1.0", END)
        self.letter_note_text.insert("1.0", letter_note)
        self.bill_number_entry.delete(0, END)
        self.bill_number_entry.insert(0, bill_number)
        self.date_entry.delete(0, END)
        self.date_entry.insert(0, date)
        self.to_address_text.delete("1.0", END)
        self.to_address_text.insert("1.0", to_address)

        # Fetch all range entries
        self.c.execute("SELECT id, rate_range_id, rate FROM range_entry WHERE destination_entry_id = ?", (destination_entry_id,))
        range_entries = self.c.fetchall()

        for range_index, (range_entry_id, rate_range_id, rate) in enumerate(range_entries):
            
            # Add range frame
            self.add_range_frame()
            range_frame = self.range_frames[-1]
            range_cb = range_frame.range_cb
            
            self.range_entry_ids[range_index] = range_entry_id
            self.used_ranges.add(rate_range_id)

            # Set the combobox value
            self.c.execute("SELECT from_km, to_km FROM rate_range WHERE id = ?", (rate_range_id,))
            from_km, to_km = self.c.fetchone()
            range_display = f"{rate_range_id} | {from_km}-{to_km} km"
            range_cb.set(range_display)

            # Setup range
            self.setup_range(range_frame, range_cb)

            # Update rate in frame
            range_frame.rate = rate

            # Fetch all dealer entries
            self.c.execute("""
                SELECT id, dealer_id, despatched_to, km, no_bags, rate, mt, mtk, amount, mda_number, date, description, remarks
                FROM dealer_entry WHERE range_entry_id = ?
            """, (range_entry_id,))
            dealer_entries = self.c.fetchall()

            for dealer_index, (dealer_entry_id, dealer_id, despatched_to, km, no_bags, rate, mt, mtk, amount, mda_number, entry_date, description, remarks) in enumerate(dealer_entries):
                if dealer_index > 0:
                    range_frame.add_dealer_row()
                row = range_frame.dealer_rows[-1]

                dealer_str = next((k for k, v in range_frame.dealer_map.items() if v[0] == dealer_id), None)
                if dealer_str:
                    row['dealer_cb'].set(dealer_str)

                row['despatched_entry'].delete(0, END)
                row['despatched_entry'].insert(0, despatched_to or '')

                row['mda_entry'].delete(0, END)
                row['mda_entry'].insert(0, mda_number or '')
                

                row['date_entry'].delete(0, END)
                row['date_entry'].insert(0, entry_date or '')

                row['bags_entry'].delete(0, END)
                row['bags_entry'].insert(0, str(no_bags or 0))

                row['desc_entry'].delete(0, END)
                row['desc_entry'].insert(0, description or 'FACTOM FOS')

                row['remarks_entry'].delete(0, END)
                row['remarks_entry'].insert(0, remarks or '')

                row.update({
                    'dealer_id': dealer_id,
                    'despatched_to': despatched_to,
                    'km': km,
                    'bags': no_bags,
                    'mt': mt,
                    'mtk': mtk,
                    'amount': amount,
                    'mda_number': mda_number,
                    'date': entry_date,
                    'description': description,
                    'remarks': remarks
                })

                row['result_lbl'].config(text=f"MT: {mt:.2f} | KM: {km} | MTK: {mtk:.2f} | ₹{amount:.2f}")
                range_frame.update_totals()

                self.dealer_entry_ids[(range_index, dealer_index)] = dealer_entry_id
        self.update_buttons_to_edit_mode()

    def print_entry(self):
        if not self.editing_mode or not self.destination_entry_id:
            messagebox.showwarning("Error", "Please save the entry before printing.")
            return

        # Fetch destination entry details
        self.c.execute("""
            SELECT destination_id, letter_note, bill_number, date, to_address
            FROM destination_entry WHERE id = ?
        """, (self.destination_entry_id,))
        row = self.c.fetchone()
        if not row:
            messagebox.showerror("Error", "Destination entry not found.")
            return

        destination_id, letter_note, bill_number, date, to_address = row
        self.c.execute("SELECT name FROM destination WHERE id = ?", (destination_id,))
        destination_name = self.c.fetchone()[0]

        # Fetch range entries and their dealers
        self.c.execute("SELECT id, rate_range_id, rate FROM range_entry WHERE destination_entry_id = ?", (self.destination_entry_id,))
        range_entries = self.c.fetchall()
        
        range_data = []
        for range_entry_id, rate_range_id, rate in range_entries:
            self.c.execute("SELECT from_km, to_km FROM rate_range WHERE id = ?", (rate_range_id,))
            from_km, to_km = self.c.fetchone()
            range_name = f"{destination_name.upper()} {from_km}-{to_km}"

            self.c.execute("""
                SELECT dealer_id, despatched_to, km, no_bags, mt, mtk, amount, mda_number, date, description, remarks
                FROM dealer_entry WHERE range_entry_id = ?
            """, (range_entry_id,))
            dealer_entries = self.c.fetchall()

            table_data = [["SL NO", "Date", "MDA NO", "Description", "Despatched to", "Bag", "MT", "KM", "MTK", "Rate", "Amount", "Remarks"]]
            for idx, (_, despatched_to, km, no_bags, mt, mtk, amount, mda_number, entry_date, description, remarks) in enumerate(dealer_entries, 1):
                table_data.append([
                    str(idx), entry_date, mda_number, description, despatched_to,
                    str(no_bags), f"{mt:.3f}", str(km), f"{mtk:.2f}", f"{rate:.2f}", f"{amount:.2f}", remarks or ''
            ])

            # Add total row
            self.c.execute("""
                SELECT total_bags, total_mt, total_mtk, total_amount
                FROM range_entry WHERE id = ?
            """, (range_entry_id,))
            total_bags, total_mt, total_mtk, total_amount = self.c.fetchone()
            table_data.append(["", "", "", "", "TOTAL", str(total_bags), f"{total_mt:.3f}", "", f"{total_mtk:.2f}", f"{rate:.2f}", f"{total_amount:.2f}", ""])

            range_data.append((range_name, table_data))

        # Generate PDF
        pdf_file = "bill_report.pdf"
        doc = SimpleDocTemplate(pdf_file, pagesize=landscape(A4), leftMargin=20, rightMargin=20, topMargin=20, bottomMargin=20)
        elements = []

        styles = getSampleStyleSheet()
        styles.add(ParagraphStyle(name='Small', fontSize=8, leading=10))
        styles.add(ParagraphStyle(name='NormalBold', fontSize=10, leading=10,  fontName='Helvetica-Bold'))
        styles.add(ParagraphStyle(name='TitleBold', fontSize=13, leading=14, fontName='Helvetica-Bold', alignment=0))
        styles.add(ParagraphStyle(name='CustomNormal', fontSize=10, leading=12))
        styles.add(ParagraphStyle(name='CenterBold', fontSize=10, fontName='Helvetica-Bold', alignment=1))

        # LEFT COLUMN - Company Info
        left_column = [
            Paragraph("GSTIN: 32ACNFS 8060K1ZP", styles['Small']),
            Paragraph("M/s. SHAN ENTERPRISES", styles['TitleBold']),
            Paragraph("Clearing & Transporting contractor", styles['CustomNormal']),
            Paragraph("21-4185, C-Meenchanda gate Calicut - 673018", styles['CustomNormal']),
            Paragraph("Mob: 9447004108", styles['CustomNormal']),
        ]

        # RIGHT COLUMN - To Address and Bill Info
        to_address_lines = to_address.split('\n')
        to_address_paragraphs = [Paragraph(line, styles['CustomNormal']) for line in to_address_lines]
        right_column = to_address_paragraphs + [
            Spacer(1, 6),
            Paragraph(f"Date: {date}", styles['CustomNormal']),
        ]

        # Header
        header_table = Table([[left_column, "", right_column]], colWidths=[480, 40, 280])
        header_table.setStyle(TableStyle([('VALIGN', (0, 0), (-1, -1), 'TOP')]))
        elements.append(header_table)
        elements.append(Spacer(1, 12))
        elements.append(Paragraph(f"Bill No.: {bill_number},", styles['CustomNormal']))
        elements.append(Spacer(1, 6))
        elements.append(Paragraph('Sir,', styles['CustomNormal']))
        elements.append(Paragraph(letter_note if letter_note else "Please find the details below:", styles['CustomNormal']))
        elements.append(Spacer(1, 8))

        # Tables for ranges
        page_width, _ = landscape(A4)
        usable_width = page_width - doc.leftMargin - doc.rightMargin

        for range_name, table_data in range_data:
            elements.append(Paragraph(range_name, styles['CenterBold']))
            elements.append(Spacer(1, 3))

            # dynamic column widths across reduced width (e.g. 90% of usable width)
            shrink_factor = 0.98   # reduce table width to 90% of page
            target_width = usable_width * shrink_factor  

            col_widths = [30, 45, 60, 60, 160, 35, 40, 40, 45, 40, 50, 40]
            scale = target_width / sum(col_widths)
            col_widths = [w * scale for w in col_widths]

            table = Table(table_data, colWidths=col_widths, hAlign="CENTER")  # center table

            table.setStyle(TableStyle([
                ('FONT', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONT', (0, 1), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, 0), 10.5),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('GRID', (0, 0), (-1, -1), 0.8, colors.black),
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
                ('ALIGN', (0, 1), (-1, -1), 'CENTER'),
                ('ALIGN', (3, 1), (4, -2), 'LEFT'),
                ('ALIGN', (11, 1), (11, -2), 'LEFT'),
                ('LEADING', (0, 0), (-1, -1), 14),

                ('LEFTPADDING', (0, 0), (-1, -1), 3),
                ('RIGHTPADDING', (0, 0), (-1, -1), 3),
                ('TOPPADDING', (0, 0), (-1, -1), 4),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 4),

                # Footer row
                ('FONTSIZE', (0, -1), (-1, -1), 9.5),
                ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
                ('BACKGROUND', (0, -1), (-1, -1), colors.lightgrey),
            ]))

            elements.append(table)
            elements.append(Spacer(1, 6))

        # Footer
        footer_data = [[
            Paragraph("Passed by", styles['CustomNormal']),
            "",
            Paragraph("Officer in charge", styles['CustomNormal']),
            "",
            Paragraph("Signature of contractor", styles['CustomNormal'])
        ]]
        footer_table = Table(footer_data, colWidths=[120, 140, 140, 140, 140])
        footer_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
        ]))
        elements.append(Spacer(1, 20))
        elements.append(footer_table)

        doc.build(elements)

        # Open PDF
        try:
            os.startfile(pdf_file)
        except AttributeError:
            try:
                os.system(f"open {pdf_file}")
            except:
                os.system(f"xdg-open {pdf_file}")

        messagebox.showinfo("Success", "PDF generated and opened for printing.")
