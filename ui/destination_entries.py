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

    def build_ui(self):
        Button(self.frame, text="← Back to Dashboard", command=lambda: self.home_frame.tkraise()).pack(anchor='nw', padx=10, pady=5)
        Label(self.frame, text="Destination Entry Form", font=("Arial", 16)).pack(pady=10)

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

    def setup_range(self, frame, range_cb):
        val = range_cb.get()
        if val == "Select Range":
            return

        rate_range_id = int(val.split("|")[0].strip())
        self.used_ranges.add(rate_range_id)

        self.c.execute("SELECT from_km, to_km, rate, is_mtk FROM rate_range WHERE id=?", (rate_range_id,))
        range_info = self.c.fetchone()
        from_km, to_km, rate, is_mtk = range_info

        range_label = f"Range: {from_km} – {to_km} km | Rate: ₹{rate} | {'MTK' if is_mtk else 'MT'}"

        range_cb.grid_remove()
        for widget in frame.grid_slaves():
            if isinstance(widget, Button):
                widget.grid_remove()

        Label(frame, text=range_label).grid(row=0, column=0, columnspan=3, pady=5)

        Label(frame, text="MDA No.").grid(row=1, column=0)
        mda_entry = Entry(frame)
        mda_entry.grid(row=1, column=1)

        Label(frame, text="Date").grid(row=2, column=0)
        date_entry = Entry(frame)
        date_entry.insert(0, datetime.now().strftime("%Y-%m-%d"))
        date_entry.grid(row=2, column=1)

        # Dealer section
        Label(frame, text="Select Dealer").grid(row=3, column=0)
        dealer_cb = ttk.Combobox(frame, state="readonly")
        dealer_cb.grid(row=3, column=1)

        self.c.execute("SELECT id, name, distance FROM dealer WHERE distance BETWEEN ? AND ?", (from_km, to_km))
        dealers = self.c.fetchall()
        dealer_map = {f"{id} - {name} ({distance}km)": (id, distance) for id, name, distance in dealers}
        dealer_cb['values'] = list(dealer_map.keys())

        Label(frame, text="No. of Bags").grid(row=4, column=0)
        bags_entry = Entry(frame)
        bags_entry.grid(row=4, column=1)

        result_label = Label(frame, text="")
        result_label.grid(row=5, column=0, columnspan=3, pady=5)

        def calculate():
            dealer_info = dealer_map.get(dealer_cb.get())
            if not dealer_info:
                return
            dealer_id, km = dealer_info
            try:
                bags = int(bags_entry.get())
                mt = bags * 0.05
                mtk = mt * km
                amount = rate * (mtk if is_mtk else mt)
                result_label.config(text=f"MT: {mt:.2f}, KM: {km}, MTK: {mtk:.2f}, Amount: ₹{amount:.2f}")
            except ValueError:
                result_label.config(text="Invalid input")

        Button(frame, text="Calculate", command=calculate).grid(row=4, column=2, padx=5)
