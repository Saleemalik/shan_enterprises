
from tkinter import *
from tkinter import ttk
from ui.mainbillentry import MainBillPreviewPage
from tkinter import messagebox
import pandas as pd

class ViewMainBillsPage:
    def __init__(self, frame, home_frame, conn):
        self.frame = frame
        self.home_frame = home_frame
        self.conn = conn
        self.c = conn.cursor()
        
        Label(self.frame, text="View Main Bills", font=("Arial", 16, "bold")).pack(pady=10)
        Button(self.frame, text="← Back to Dashboard", command=lambda: self.home_frame.tkraise()).pack(anchor='nw', padx=10)

        self.tree = ttk.Treeview(self.frame, columns=("bill_number", "date", "to_address", "amount"), show="headings")
        self.tree.heading("bill_number", text="Bill Number")
        self.tree.heading("date", text="Date")
        self.tree.heading("to_address", text="To Address")
        self.tree.heading("amount", text="Amount")
        self.tree.pack(fill='both', expand=True, padx=20, pady=10)

        self.tree.bind("<Double-1>", self.open_selected_bill)

        self.load_bills()
        search_frame = Frame(self.frame)
        search_frame.pack(pady=5)

        Label(search_frame, text="Search by Bill Number:").pack(side=LEFT)
        self.search_var = StringVar()
        search_entry = Entry(search_frame, textvariable=self.search_var, width=30)
        search_entry.pack(side=LEFT, padx=5)

        Button(search_frame, text="🔍 Search", command=self.filter_bills).pack(side=LEFT)
        Button(search_frame, text="🧹 Clear", command=self.clear_filter).pack(side=LEFT, padx=(5, 0))
        Button(self.frame, text="🗑️ Delete Selected Bill", command=self.delete_selected_bill).pack(pady=(5, 10))

    
    def filter_bills(self):
        query = self.search_var.get().strip().lower()
        for item in self.tree.get_children():
            bill_no = self.tree.item(item)['values'][0].lower()
            self.tree.detach(item) if query not in bill_no else self.tree.reattach(item, '', 'end')

    def clear_filter(self):
        self.search_var.set("")
        for item in self.tree.get_children():
            self.tree.reattach(item, '', 'end')


    def load_bills(self):
        self.tree.delete(*self.tree.get_children())
        self.c.execute('''
            SELECT mb.id, mb.bill_number, mb.date_of_clearing, mb.to_address,
                   IFNULL(SUM(dr.amount), 0)
            FROM main_bill mb
            LEFT JOIN main_bill_entries mbe ON mbe.main_bill_id = mb.id
            LEFT JOIN destination_entry de ON de.id = mbe.destination_entry_id
            LEFT JOIN range_entry re ON re.destination_entry_id = de.id
            LEFT JOIN dealer_entry dr ON dr.range_entry_id = re.id
            GROUP BY mb.id
            ORDER BY mb.date_of_clearing DESC
        ''')
        for row in self.c.fetchall():
            self.tree.insert("", END, values=row[1:])

    def open_selected_bill(self, event=None):
        selected = self.tree.selection()
        if not selected:
            return

        bill_number = self.tree.item(selected[0])['values'][0]
        
        # Get main bill data
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
            "created_date": row[4]  # fallback
        }

        # Get destination_entry_ids
        self.c.execute('SELECT destination_entry_id FROM main_bill_entries WHERE main_bill_id = ?', (main_bill_id,))
        destination_entry_ids = [r[0] for r in self.c.fetchall()]

        # Open preview page in read-only mode (no Save button)
        preview_frame = Frame(self.frame.master)
        preview_frame.grid(row=0, column=0, sticky='nsew')
        
        preview_page = MainBillPreviewPage(
            preview_frame,
            self.frame,
            self.conn,
            main_bill_data,
            destination_entry_ids
        )
        preview_page.hide_save_button()  # <-- Hide Save button
        preview_frame.tkraise()

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

            # Unlink destination_entry
            self.c.execute("UPDATE destination_entry SET main_bill_id = NULL WHERE main_bill_id = ?", (main_bill_id,))

            # Delete linked entries
            self.c.execute("DELETE FROM main_bill_entries WHERE main_bill_id = ?", (main_bill_id,))
            self.c.execute("DELETE FROM main_bill WHERE id = ?", (main_bill_id,))

            self.conn.commit()
            messagebox.showinfo("Deleted", f"Bill #{bill_number} deleted successfully.")
            self.load_bills()

        except Exception as e:
            messagebox.showerror("Error", f"Failed to delete bill:\n{e}")


    def import_dealers_from_file(self, file_path):
        try:
            # Read the Excel file
            excel_file = pd.ExcelFile(file_path)
            
            # Get all sheet names
            sheet_names = excel_file.sheet_names
            
            for sheet_name in sheet_names:
                # Skip empty sheets (like Sheet1)
                if sheet_name == "Sheet1":
                    continue
                    
                # Check if destination exists by name or place
                self.cursor.execute(
                    "SELECT id FROM destination WHERE name = ? OR place = ?",
                    (sheet_name, sheet_name)
                )
                dest_result = self.cursor.fetchone()
                
                if dest_result:
                    destination_id = dest_result[0]
                else:
                    # Insert new destination if no match found
                    self.cursor.execute(
                        "INSERT INTO destination (name, place) VALUES (?, ?)",
                        (sheet_name, sheet_name)
                    )
                    self.conn.commit()
                    destination_id = self.cursor.lastrowid
                
                # Read the sheet data
                df = pd.read_excel(file_path, sheet_name=sheet_name)
                
                # Ensure column names match the expected format
                df.columns = ['Dealer code', 'NAME', 'Place', 'Pin Code', 'Mob No.', 'Distance']
                
                # Insert each row into the dealer table
                for index, row in df.iterrows():
                    code = str(row['Dealer code']).strip()
                    name = str(row['NAME']).strip()
                    place = str(row['Place']).strip()
                    pincode = str(row['Pin Code']).strip()
                    mobile = str(row['Mob No.']).strip() if not pd.isna(row['Mob No.']) else ""
                    distance = float(row['Distance']) if not pd.isna(row['Distance']) else 0.0
                    
                    # Skip rows with missing required fields
                    if not code or not name:
                        continue
                    
                    try:
                        self.cursor.execute(
                            """
                            INSERT OR IGNORE INTO dealer 
                            (code, name, place, pincode, mobile, distance, destination_id) 
                            VALUES (?, ?, ?, ?, ?, ?, ?)
                            """,
                            (code, name, place, pincode, mobile, distance, destination_id)
                        )
                    except Exception as e:
                        print(f"Error inserting dealer {code}: {str(e)}")
                        continue
                
                self.conn.commit()
            
            # Reload the dealers in the UI
            self.load_dealers()
            self.clear_fields()
            messagebox.showinfo("Success", f"Dealers imported successfully from {len(sheet_names)-1} destinations")
            
        except Exception as e:
            messagebox.showerror("Import Error", f"Failed to import dealers: {str(e)}")
