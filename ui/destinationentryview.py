from tkinter import *
from tkinter import ttk, messagebox

class DestinationEntryViewer:
    def __init__(self, frame, home_frame, conn, edit_entry_page):
        self.frame = frame
        self.home_frame = home_frame
        self.edit_entry_page = edit_entry_page
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
        Button(filter_frame, text="Clear", command=lambda: self.dest_cb.set("")).grid(row=0, column=2, padx=5)


        Label(filter_frame, text="Date").grid(row=0, column=3)
        self.date_entry = Entry(filter_frame)
        self.date_entry.grid(row=0, column=4, padx=5)

        Label(filter_frame, text="Dealer Name").grid(row=0, column=5)
        self.dealer_entry = Entry(filter_frame)
        self.dealer_entry.grid(row=0, column=6, padx=5)

        Button(filter_frame, text="🔍 Search", command=self.search_entries).grid(row=0, column=7, padx=10)

        # Treeview with scrollbar
        tree_frame = Frame(self.frame)
        tree_frame.pack(fill='both', expand=True, padx=10, pady=10)

        scrollbar = Scrollbar(tree_frame)
        scrollbar.pack(side=RIGHT, fill=Y)

        columns = ("id", "date", "destination", "range", "dealer", "bags", "mt", "km", "rate", "mtk", "amount")
        column_titles = {
            "id": "ID", "date": "Date", "destination": "Destination", "range": "Range",
            "dealer": "Dealer", "bags": "Bags", "mt": "MT", "km": "KM", "rate": "Rate", "mtk": "MTK", "amount": "Amount"
        }

        self.tree = ttk.Treeview(tree_frame, columns=columns, show="headings", yscrollcommand=scrollbar.set)
        scrollbar.config(command=self.tree.yview)

        for col in columns:
            self.tree.heading(col, text=column_titles[col])
            self.tree.column(col, width=80 if col in ("id", "bags", "mt", "km", "rate", "mtk") else 120)

        self.tree.pack(fill='both', expand=True)
        self.tree.bind("<Double-1>", lambda e: self.edit_entry())  # Double-click to edit

        # Buttons
        btn_frame = Frame(self.frame)
        btn_frame.pack(pady=5)

        Button(btn_frame, text="✏️ Edit Entry", command=self.edit_entry).pack(side=LEFT, padx=10)
        Button(btn_frame, text="🗑 Delete Entry", command=self.delete_entry).pack(side=LEFT, padx=10)

        self.load_destinations()
        self.search_entries()  # Load initially

    def get_selected_entry_id(self):
        selected = self.tree.focus()
        if not selected:
            messagebox.showwarning("No selection", "Please select an entry.")
            return None
        values = self.tree.item(selected, "values")
        return values[0]

    def edit_entry(self):
        entry_id = self.get_selected_entry_id()
        if entry_id:
            self.edit_entry_page.load_existing_entry(entry_id)
            self.edit_entry_page.frame.tkraise()
            print(f"Edit Entry ID: {entry_id}")

    def delete_entry(self):
        entry_id = self.get_selected_entry_id()
        if not entry_id:
            return

        confirm = messagebox.askyesno("Confirm", "Are you sure you want to delete this entry?")
        if not confirm:
            return

        try:
            self.c.execute("DELETE FROM dealer_entry WHERE range_entry_id IN (SELECT id FROM range_entry WHERE destination_entry_id = ?)", (entry_id,))
            self.c.execute("DELETE FROM range_entry WHERE destination_entry_id = ?", (entry_id,))
            self.c.execute("DELETE FROM destination_entry WHERE id = ?", (entry_id,))
            self.conn.commit()
            messagebox.showinfo("Deleted", "Entry deleted successfully.")
            self.search_entries()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to delete: {e}")

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
            SELECT de.id, de.date, d.name, 
                rr.from_km || '-' || rr.to_km || 'km', dl.name,
                dr.no_bags, 
                ROUND(dr.no_bags * 0.05, 2) as mt,
                dl.distance,
                rr.rate,
                ROUND(dr.no_bags * 0.05 * dl.distance, 2) as mtk,
                dr.amount
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

        query += " ORDER BY de.date DESC, de.id DESC"

        self.c.execute(query, params)
        rows = self.c.fetchall()

        self.tree.delete(*self.tree.get_children())
        if not rows:
            messagebox.showinfo("No results", "No matching entries found.")
        for row in rows:
            self.tree.insert("", END, values=row)
