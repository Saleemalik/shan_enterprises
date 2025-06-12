from tkinter import *
from tkinter import ttk, messagebox
from datetime import datetime

class DestinationEntryViewer:
    def __init__(self, frame, home_frame, conn):
        self.frame = frame
        self.home_frame = home_frame
        self.conn = conn
        self.c = conn.cursor()

        Label(self.frame, text="View Destination Entries", font=("Arial", 16)).pack(pady=10)
        Button(self.frame, text="← Back to Dashboard", command=lambda: self.home_frame.tkraise()).pack(anchor='nw', padx=10)

        # Filters
        filter_frame = Frame(self.frame)
        filter_frame.pack(padx=10, pady=5)

        Label(filter_frame, text="Destination").grid(row=0, column=0)
        self.dest_cb = ttk.Combobox(filter_frame, state="readonly", width=25)
        self.dest_cb.grid(row=0, column=1, padx=5)

        Label(filter_frame, text="Date").grid(row=0, column=2)
        self.date_entry = Entry(filter_frame)
        self.date_entry.grid(row=0, column=3, padx=5)

        Label(filter_frame, text="Dealer Name").grid(row=0, column=4)
        self.dealer_entry = Entry(filter_frame)
        self.dealer_entry.grid(row=0, column=5, padx=5)

        Button(filter_frame, text="🔍 Search", command=self.search_entries).grid(row=0, column=6, padx=10)

        # Table
        columns = ("id", "date", "destination", "bill_number", "range", "dealer", "bags", "amount")
        self.tree = ttk.Treeview(self.frame, columns=columns, show="headings")
        for col in columns:
            self.tree.heading(col, text=col.capitalize())
        self.tree.pack(fill='both', expand=True, padx=10, pady=10)

        self.load_destinations()
        self.search_entries()  # Load initially

    def load_destinations(self):
        self.c.execute("SELECT id, name FROM destination")
        dests = self.c.fetchall()
        self.dest_map = {name: id for id, name in dests}
        self.dest_cb["values"] = list(self.dest_map.keys())

    def search_entries(self):
        dest_id = self.dest_map.get(self.dest_cb.get())
        date = self.date_entry.get().strip()
        dealer = self.dealer_entry.get().strip()

        query = """
        SELECT de.id, de.date, d.name, de.bill_number,
               rr.from_km || '-' || rr.to_km || 'km', dl.name,
               dr.no_bags, dr.amount
        FROM destination_entry de
        JOIN destination d ON de.destination_id = d.id
        JOIN range_entry re ON re.destination_entry_id = de.id
        JOIN rate_range rr ON re.rate_range_id = rr.id
        JOIN dealer_entry dr ON dr.range_entry_id = re.id
        JOIN dealer dl ON dr.dealer_id = dl.id
        WHERE 1=1
        """
        params = []

        if dest_id:
            query += " AND de.destination_id = ?"
            params.append(dest_id)
        if date:
            query += " AND de.date = ?"
            params.append(date)
        if dealer:
            query += " AND dl.name LIKE ?"
            params.append(f"%{dealer}%")

        self.c.execute(query, params)
        rows = self.c.fetchall()

        # Clear and insert new rows
        self.tree.delete(*self.tree.get_children())
        for row in rows:
            self.tree.insert("", END, values=row)
