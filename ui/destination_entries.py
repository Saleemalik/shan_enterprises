from tkinter import *
from tkinter import ttk, messagebox
from datetime import datetime
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
import os

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

    def refresh(self):
        # Clear range frames
        for rf in self.range_frames:
            rf.destroy()
        self.range_frames.clear()
        self.used_ranges.clear()

        # Clear form fields
        self.letter_note_text.delete("1.0", END)
        self.bill_number_entry.delete(0, END)
        self.date_entry.delete(0, END)
        self.date_entry.insert(0, datetime.now().strftime("%Y-%m-%d"))
        self.to_address_text.delete("1.0", END)

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
        self.letter_note_text = Text(form, height=5, width=60, pady=5)
        self.letter_note_text.grid(row=1, column=1, pady=5)

        Label(form, text="Bill Number").grid(row=2, column=0)
        self.bill_number_entry = Entry(form)
        self.bill_number_entry.grid(row=2, column=1)

        Label(form, text="Date").grid(row=3, column=0)
        self.date_entry = Entry(form)
        self.date_entry.insert(0, datetime.now().strftime("%Y-%m-%d"))
        self.date_entry.grid(row=3, column=1)

        Label(form, text="To Address").grid(row=4, column=0, pady=5)
        self.to_address_text = Text(form, height=5, width=60)
        self.to_address_text.grid(row=4, column=1, pady=5)

        Button(form, text="+ Add Range", command=self.add_range_frame).grid(row=5, column=0, columnspan=2, pady=10)

        self.range_container = Frame(self.frame)
        self.range_container.pack(fill='both', expand=True)

        self.load_destinations()
        self.save_button.pack(pady=10)

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
                            range_entry_id, dealer_id, km, no_bags, rate,
                            mt, mtk, amount, mda_number, date, description, remarks
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        range_entry_id, row['dealer_id'], row['km'], row['bags'],
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

        except Exception as e:
            self.conn.rollback()
            messagebox.showerror("Error", f"Failed to save entry:\n{e}")

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

    def setup_range(self, frame, range_cb):
        val = range_cb.get()
        if val == "Select Range":
            return

        rate_range_id = int(val.split("|")[0].strip())
        self.used_ranges.add(rate_range_id)

        self.c.execute("SELECT from_km, to_km, rate, is_mtk FROM rate_range WHERE id=?", (rate_range_id,))
        from_km, to_km, rate, is_mtk = self.c.fetchone()

        range_label = f"Range: {from_km} – {to_km} km | Rate: ₹{rate:.2f} | {'MTK' if is_mtk else 'MT'}"
        range_cb.grid_remove()
        for widget in frame.grid_slaves():
            if isinstance(widget, Button):
                widget.grid_remove()

        Label(frame, text=range_label).grid(row=0, column=0, columnspan=3, pady=5, sticky='w')
        Button(frame, text="Remove This Range", command=lambda: self.remove_range(frame, rate_range_id)).grid(row=0, column=3, sticky='e')

        Label(frame, text="Dealers for this range", font=("Arial", 10, "bold")).grid(row=1, column=0, columnspan=4, pady=(10, 0))
        dealer_frame = Frame(frame)
        Label(dealer_frame, text="Dealer", font=("Arial", 9, "bold")).grid(row=0, column=0)
        Label(dealer_frame, text="MDA No.", font=("Arial", 9, "bold")).grid(row=0, column=1)
        Label(dealer_frame, text="Date", font=("Arial", 9, "bold")).grid(row=0, column=2)
        Label(dealer_frame, text="Bags", font=("Arial", 9, "bold")).grid(row=0, column=3)
        Label(dealer_frame, text="Description", font=("Arial", 9, "bold")).grid(row=0, column=4)
        Label(dealer_frame, text="Remarks", font=("Arial", 9, "bold")).grid(row=0, column=5)
        Label(dealer_frame, text="Details", font=("Arial", 9, "bold")).grid(row=0, column=6)
        Label(dealer_frame, text="Actions", font=("Arial", 9, "bold")).grid(row=0, column=7)

        dealer_frame.grid(row=4, column=0, columnspan=4, sticky="w")
        
        selected_dest = self.destination_cb.get()
        destination_id = self.destination_map.get(selected_dest)

        self.c.execute("""
            SELECT id, name, distance FROM dealer
            WHERE distance BETWEEN ? AND ? AND destination_id = ?
        """, (from_km, to_km, destination_id))
        dealers = self.c.fetchall()
        dealer_map = {f"{id} - {name} ({distance}km)": (id, distance) for id, name, distance in dealers}

        dealer_rows = []

        totals_label = Label(frame, text="Total Bags: 0 | MT: 0.00 | MTK: 0.00 | ₹0.00", font=("Arial", 10, "bold"), fg="green")
        totals_label.grid(row=5, column=0, columnspan=4, pady=5)

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

            def filter_dealers(event):
                typed = dealer_var.get().lower()
                filtered = [k for k in dealer_map.keys() if typed in k.lower()]
                dealer_cb['values'] = filtered
                if filtered:
                    dealer_cb.event_generate('<Down>')

            dealer_cb.bind('<KeyRelease>', filter_dealers)
            
            mda_entry = Entry(dealer_frame, width=12)
            mda_entry.grid(row=row_idx, column=1)
            row['mda_entry'] = mda_entry

            date_entry = Entry(dealer_frame, width=12)
            date_entry.insert(0, datetime.now().strftime("%Y-%m-%d"))
            date_entry.grid(row=row_idx, column=2)
            row['date_entry'] = date_entry

            bags_entry = Entry(dealer_frame, width=5)
            bags_entry.grid(row=row_idx, column=3, padx=2)
            row['bags_entry'] = bags_entry

            desc_entry = Entry(dealer_frame, width=15)
            desc_entry.insert(0, "FACTOM FOS")
            desc_entry.grid(row=row_idx, column=4, padx=2)
            row['desc_entry'] = desc_entry

            remarks_entry = Entry(dealer_frame, width=15)
            remarks_entry.grid(row=row_idx, column=5, padx=2)
            row['remarks_entry'] = remarks_entry

            result_lbl = Label(dealer_frame, text="", width=40, anchor='w')
            result_lbl.grid(row=row_idx, column=6, padx=2)
            row['result_lbl'] = result_lbl

            def calculate_row():
                selected = dealer_cb.get()
                if not selected or selected not in dealer_map:
                    result_lbl.config(text="Select valid dealer")
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
                for widget in [dealer_cb, mda_entry, date_entry, bags_entry, desc_entry, remarks_entry, result_lbl, calc_btn, remove_btn]:
                    widget.destroy()
                dealer_rows.remove(row)
                update_totals()

            calc_btn = Button(dealer_frame, text="Calc", command=calculate_row)
            calc_btn.grid(row=row_idx, column=7)

            remove_btn = Button(dealer_frame, text="❌", command=remove_dealer_row)
            remove_btn.grid(row=row_idx, column=8)

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

        Button(self.frame, text="➕ Add New Entry", command=lambda:self.refresh(False)).pack(pady=20)
    
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
                            SET dealer_id=?, km=?, no_bags=?, rate=?,
                                mt=?, mtk=?, amount=?, mda_number=?, date=?,
                                description=?, remarks=?
                            WHERE id=?
                        """, (
                            row['dealer_id'], row['km'], row['bags'], frame.rate,
                            row['mt'], row['mtk'], row['amount'],
                            row['mda_number'], row['date'],
                            row.get('description', 'FACTOM FOS'), row.get('remarks', ''),
                            dealer_entry_id
                        ))
                    else:
                        # Insert new dealer_entry
                        self.c.execute("""
                            INSERT INTO dealer_entry (
                                range_entry_id, dealer_id, km, no_bags, rate,
                                mt, mtk, amount, mda_number, date, description, remarks
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (
                            range_entry_id, row['dealer_id'], row['km'], row['bags'],
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
    
    def refresh(self, stat=True):
        if self.editing_mode and stat:
            self.load_existing_entry(self.destination_entry_id)
        else:            
            self.destination_entry_id = None
            self.range_entry_ids.clear()
            self.dealer_entry_ids.clear()

            for widget in self.frame.winfo_children():
                widget.destroy()

            self.__init__(self.frame, self.home_frame, self.conn)

    def load_existing_entry(self, destination_entry_id):
        self.refresh(False)
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
                SELECT id, dealer_id, km, no_bags, rate, mt, mtk, amount, mda_number, date, description, remarks
                FROM dealer_entry WHERE range_entry_id = ?
            """, (range_entry_id,))
            dealer_entries = self.c.fetchall()

            for dealer_index, (dealer_entry_id, dealer_id, km, no_bags, rate, mt, mtk, amount, mda_number, entry_date, description, remarks) in enumerate(dealer_entries):
                if dealer_index > 0:
                    range_frame.add_dealer_row()
                row = range_frame.dealer_rows[-1]

                dealer_str = next((k for k, v in range_frame.dealer_map.items() if v[0] == dealer_id), None)
                if dealer_str:
                    row['dealer_cb'].set(dealer_str)

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
                SELECT dealer_id, km, no_bags, mt, mtk, amount, mda_number, date, description, remarks
                FROM dealer_entry WHERE range_entry_id = ?
            """, (range_entry_id,))
            dealer_entries = self.c.fetchall()

            table_data = [["SL NO", "Date", "MDA NO", "Description", "Despatched to", "Bag", "MT", "KM", "MTK", "Rate", "Amount", "Remarks"]]
            for idx, (dealer_id, km, no_bags, mt, mtk, amount, mda_number, entry_date, description, remarks) in enumerate(dealer_entries, 1):
                self.c.execute("SELECT name, place FROM dealer WHERE id = ?", (dealer_id,))
                dealer_name, dealer_place = self.c.fetchone()
                dispatched_to = f"{dealer_name}, {dealer_place or ''}"
                table_data.append([
                    str(idx), entry_date, mda_number, description, dispatched_to, str(no_bags), f"{mt:.3f}", str(km), f"{mtk:.2f}", f"₹{rate:.2f}", f"₹{amount:.2f}", remarks or ''
                ])

            # Add total row
            self.c.execute("""
                SELECT total_bags, total_mt, total_mtk, total_amount
                FROM range_entry WHERE id = ?
            """, (range_entry_id,))
            total_bags, total_mt, total_mtk, total_amount = self.c.fetchone()
            table_data.append(["", "", "", "", "TOTAL", str(total_bags), f"{total_mt:.3f}", "", f"{total_mtk:.2f}", f"₹{rate:.2f}", f"₹{total_amount:.2f}", ""])

            range_data.append((range_name, table_data))

        # Generate PDF
        pdf_file = "bill_report.pdf"
        doc = SimpleDocTemplate(pdf_file, pagesize=A4, leftMargin=30, rightMargin=30, topMargin=20, bottomMargin=20)
        elements = []

        styles = getSampleStyleSheet()
        styles.add(ParagraphStyle(name='Small', fontSize=8, leading=10))
        styles.add(ParagraphStyle(name='NormalBold', fontSize=8, leading=10, fontName='Helvetica-Bold'))
        styles.add(ParagraphStyle(name='TitleBold', fontSize=12, leading=14, fontName='Helvetica-Bold', alignment=0))
        styles.add(ParagraphStyle(name='CustomNormal', fontSize=10, leading=12))
        
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
        
        # Create Table with 2 columns
        table_data = [[left_column,"", right_column]]
        table = Table(table_data, colWidths=[310,100, 125])
        
        table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ]))

        elements.append(table)
        elements.append(Spacer(1, 12))
        elements.append(Paragraph(f"Bill No.: {bill_number},", styles['CustomNormal']))
        elements.append(Spacer(1, 6))
        
        elements.append(Paragraph('Sir,', styles['CustomNormal']))
        elements.append(Paragraph(letter_note if letter_note else "Please find the details below:", styles['CustomNormal']))
        elements.append(Spacer(1, 8))

        # Tables
        for range_name, table_data in range_data:
            elements.append(Paragraph(range_name, styles['NormalBold']))
            table = Table(table_data, colWidths=[20, 40, 40, 60, 91, 35, 35, 35, 40, 35, 45, 45])
            table.setStyle(TableStyle([
                ('FONT', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONT', (0, 1), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), 6),  # Reduced font size
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('BACKGROUND', (0, -1), (-1, -1), colors.lightgrey),
                ('LEFTPADDING', (0, 0), (-1, -1), 3),  # Reduced padding
                ('RIGHTPADDING', (0, 0), (-1, -1), 3),
                ('TOPPADDING', (0, 0), (-1, -1), 1),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 1),
            ]))
            elements.append(table)
            elements.append(Spacer(1, 4))  # Reduced spacer height

        # Footer
        passedby = Paragraph("Passed by", styles['CustomNormal'])
        incharge = Paragraph("officer in charge", styles['CustomNormal'])
        sign = Paragraph("signature of contractor", styles['CustomNormal'])
        
        table_footer_data = [[passedby, "", incharge, "", sign]]
        footer_table = Table(table_footer_data, colWidths=[100, 120, 100, 110, 100])
        footer_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
        ]))
        elements.append(footer_table)

        doc.build(elements)

        # Open the PDF
        try:
            os.startfile(pdf_file)
        except AttributeError:
            try:
                os.system(f"open {pdf_file}")
            except:
                os.system(f"xdg-open {pdf_file}")

        messagebox.showinfo("Success", "PDF generated and opened for printing.")