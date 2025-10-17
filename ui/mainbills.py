from tkinter import *
from tkinter import ttk, messagebox
from ui.mainbillentry import MainBillPreviewPage
import pandas as pd

class ViewMainBillsPage:
    def __init__(self, frame, home_frame, conn):
        self.frame = frame
        self.home_frame = home_frame
        self.conn = conn
        self.c = conn.cursor()
        self.frame.bind("<<ShowFrame>>", lambda e: self.load_bills())
        Label(self.frame, text="View Main Bills", font=("Arial", 16, "bold")).pack(pady=10)
        Button(self.frame, text="← Back to Dashboard", command=lambda: self.home_frame.tkraise()).pack(anchor='nw', padx=10)

        # Updated columns: Removed "to_address", added "ranges"
        self.tree = ttk.Treeview(
            self.frame,
            columns=("bill_number", "date", "ranges", "amount"),
            show="headings"
        )
        self.tree.heading("bill_number", text="Bill Number")
        self.tree.heading("date", text="Date")
        self.tree.heading("ranges", text="Ranges")
        self.tree.heading("amount", text="Amount")

        self.tree.column("bill_number", width=150)
        self.tree.column("date", width=100)
        self.tree.column("ranges", width=250)
        self.tree.column("amount", width=100, anchor=E)

        self.tree.pack(fill='both', expand=True, padx=20, pady=10)
        self.tree.bind("<Double-1>", self.open_selected_bill)

        # Search and buttons
        search_frame = Frame(self.frame)
        search_frame.pack(pady=5)

        Label(search_frame, text="Search by Bill Number:").pack(side=LEFT)
        self.search_var = StringVar()
        search_entry = Entry(search_frame, textvariable=self.search_var, width=30)
        search_entry.pack(side=LEFT, padx=5)

        Button(search_frame, text="🔍 Search", command=self.filter_bills).pack(side=LEFT)
        Button(search_frame, text="🧹 Clear", command=self.clear_filter).pack(side=LEFT, padx=(5, 0))
        Button(self.frame, text="🗑️ Delete Selected Bill", command=self.delete_selected_bill).pack(pady=(5, 10))

        self.load_bills()

    # --------------------------
    # 🔍 FILTERING
    # --------------------------
    def filter_bills(self):
        query = self.search_var.get().strip().lower()
        for item in self.tree.get_children():
            bill_no = str(self.tree.item(item)['values'][0]).lower()
            if query not in bill_no:
                self.tree.detach(item)
            else:
                self.tree.reattach(item, '', 'end')

    def clear_filter(self):
        self.search_var.set("")
        for item in self.tree.get_children():
            self.tree.reattach(item, '', 'end')

    # --------------------------
    # 📥 LOAD BILLS (with RANGES)
    # --------------------------
    def load_bills(self):
        self.tree.delete(*self.tree.get_children())

        self.c.execute("""
            SELECT 
                mb.id,
                mb.bill_number,
                mb.date_of_clearing,
                (
                    SELECT GROUP_CONCAT(r, ', ')
                    FROM (
                        SELECT DISTINCT 
                            TRIM(REPLACE(rr.from_km, '.0', '')) || '-' || TRIM(REPLACE(rr.to_km, '.0', '')) AS r
                        FROM rate_range rr
                        JOIN range_entry re2 ON re2.rate_range_id = rr.id
                        JOIN destination_entry de2 ON de2.id = re2.destination_entry_id
                        JOIN main_bill_entries mbe2 ON mbe2.destination_entry_id = de2.id
                        WHERE mbe2.main_bill_id = mb.id
                        ORDER BY rr.from_km
                    )
                ) AS ranges,
                IFNULL(SUM(dr.amount), 0) AS total_amount
            FROM main_bill mb
            LEFT JOIN main_bill_entries mbe ON mbe.main_bill_id = mb.id
            LEFT JOIN destination_entry de ON de.id = mbe.destination_entry_id
            LEFT JOIN range_entry re ON re.destination_entry_id = de.id
            LEFT JOIN dealer_entry dr ON dr.range_entry_id = re.id
            GROUP BY mb.id
            ORDER BY mb.date_of_clearing DESC
        """)

        for row in self.c.fetchall():
            _, bill_number, date, ranges, amount = row
            self.tree.insert("", END, values=(bill_number, date, ranges or "-", round(amount, 2)))

    # --------------------------
    # 📄 OPEN SELECTED BILL
    # --------------------------
    def open_selected_bill(self, event=None):
        selected = self.tree.selection()
        if not selected:
            return

        bill_number = self.tree.item(selected[0])['values'][0]
        self.c.execute('SELECT * FROM main_bill WHERE bill_number = ?', (bill_number,))
        row = self.c.fetchone()
        if not row:
            messagebox.showerror("Error", "Bill not found.")
            return

        main_bill_id = row[0]
        main_bill_data = {
            "bill_number": row[1],
            "letter_note": row[2],
            "to_address": row[3],
            "date_of_clearing": row[4],
            "fact_gst_number": row[5],
            "product": row[6],
            "hsn_sac_code": row[7],
            "year": row[8],
            "created_date": row[4] or ""
        }

        # Get linked destination entries
        self.c.execute('SELECT destination_entry_id FROM main_bill_entries WHERE main_bill_id = ?', (main_bill_id,))
        destination_entry_ids = [r[0] for r in self.c.fetchall()]

        preview_frame = Frame(self.frame.master)
        preview_frame.grid(row=0, column=0, sticky='nsew')
        
        preview_page = MainBillPreviewPage(preview_frame, self.frame, self.conn, main_bill_data, destination_entry_ids)
        preview_frame.tkraise()

    # --------------------------
    # 🗑️ DELETE BILL
    # --------------------------
    def delete_selected_bill(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("No selection", "Please select a bill to delete.")
            return

        bill_number = self.tree.item(selected[0])['values'][0]
        confirm = messagebox.askyesno("Confirm Deletion", f"Are you sure you want to delete Bill #{bill_number}?")
        if not confirm:
            return

        try:
            # Get main_bill_id
            self.c.execute("SELECT id FROM main_bill WHERE bill_number = ?", (bill_number,))
            row = self.c.fetchone()
            if not row:
                messagebox.showerror("Error", "Main bill not found.")
                return

            main_bill_id = row[0]

            # Unlink and delete
            self.c.execute("UPDATE destination_entry SET main_bill_id = NULL WHERE main_bill_id = ?", (main_bill_id,))
            self.c.execute("DELETE FROM main_bill_entries WHERE main_bill_id = ?", (main_bill_id,))
            self.c.execute("DELETE FROM main_bill WHERE id = ?", (main_bill_id,))
            self.conn.commit()

            messagebox.showinfo("Deleted", f"Bill #{bill_number} deleted successfully.")
            self.load_bills()

        except Exception as e:
            messagebox.showerror("Error", f"Failed to delete bill:\n{e}")
