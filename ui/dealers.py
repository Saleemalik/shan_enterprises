from tkinter import *
from tkinter import messagebox, filedialog
from tkinter.ttk import Treeview, Combobox
from datetime import datetime
import pandas as pd

class DealerManager:
    def __init__(self, master_frame, home_frame, conn):
        self.conn = conn
        self.cursor = conn.cursor()
        self.master_frame = master_frame
        self.home_frame = home_frame

        self.setup_ui()

    def setup_ui(self):
        Button(self.master_frame, text="← Back to Dashboard", command=lambda: self.home_frame.tkraise()).pack(anchor='nw', padx=10, pady=5)
        Label(self.master_frame, text="Dealer Management", font=("Arial", 16)).pack(pady=10)

        self.form = Frame(self.master_frame)
        self.form.pack(pady=10)

        labels = ["Code", "Name", "Place", "Pincode", "Mobile", "Distance"]
        self.entries = {}

        for i, label in enumerate(labels):
            Label(self.form, text=label).grid(row=i, column=0)
            entry = Entry(self.form)
            entry.grid(row=i, column=1)
            self.entries[label.lower()] = entry
        
        # Add Destination field
        Label(self.form, text="Destination").grid(row=6, column=0)
        self.destination_cb = Combobox(self.form, state="readonly")
        self.destination_cb.grid(row=6, column=1)
        
        # Load destination options
        self.cursor.execute("SELECT id, name FROM destination")
        dest_rows = self.cursor.fetchall()
        self.destination_map = {f"{id} - {name}": id for id, name in dest_rows}
        self.destination_cb['values'] = list(self.destination_map.keys())

        Button(self.form, text="Add Dealer", command=self.add_dealer).grid(row=7, column=0, pady=10)
        Button(self.form, text="Update Dealer", command=self.update_dealer).grid(row=7, column=1, pady=10)
        Button(self.form, text="Delete Dealer", command=self.delete_dealer).grid(row=7, column=2, pady=10)
        
        Button(self.form, text="Import Dealers from File", command=self.import_dealers_from_file).grid(row=8, column=1, pady=10)
        
        # Search bar
        search_frame = Frame(self.master_frame)
        search_frame.pack(fill="x", padx=10, pady=5)

        Label(search_frame, text="Search:").pack(side="left", padx=(0, 5))
        self.search_var = StringVar()
        search_entry = Entry(search_frame, textvariable=self.search_var)
        search_entry.pack(side="left", fill="x", expand=True)

        Button(search_frame, text="Go", command=self.search_dealers).pack(side="left", padx=5)
        Button(search_frame, text="Clear", command=self.load_dealers).pack(side="left")
        
        search_entry.bind("<Return>", lambda e: self.search_dealers())

        self.dealer_list = Treeview(
            self.master_frame,
            columns=("ID", "Code", "Name", "Place", "Pincode", "Mobile", "Distance", "Destination"),
            show="headings"
        )

        for col in self.dealer_list["columns"]:
            self.dealer_list.heading(col, text=col)
            self.dealer_list.column(col, width=100)

        self.dealer_list.bind("<<TreeviewSelect>>", self.on_select)
        self.dealer_list.pack(fill="both", expand=True, padx=10, pady=10)

        self.load_dealers()
        
    def search_dealers(self):
        query = self.search_var.get().strip()
        if not query:
            self.load_dealers()
            return

        for row in self.dealer_list.get_children():
            self.dealer_list.delete(row)

        sql = """
            SELECT dealer.id, dealer.code, dealer.name, dealer.place, dealer.pincode, dealer.mobile,
                dealer.distance, destination.name
            FROM dealer
            LEFT JOIN destination ON dealer.destination_id = destination.id
            WHERE dealer.code LIKE ? OR dealer.name LIKE ? OR dealer.place LIKE ? 
                OR dealer.mobile LIKE ? OR destination.name LIKE ?
        """
        like_query = f"%{query}%"
        self.cursor.execute(sql, (like_query, like_query, like_query, like_query, like_query))

        for row in self.cursor.fetchall():
            self.dealer_list.insert("", END, values=row)


    def get_entry(self, field):
        return self.entries[field].get().strip()

    def clear_fields(self):
        for entry in self.entries.values():
            entry.delete(0, END)

    def load_dealers(self):
        for row in self.dealer_list.get_children():
            self.dealer_list.delete(row)

        self.cursor.execute("""
            SELECT dealer.id, dealer.code, dealer.name, dealer.place, dealer.pincode, dealer.mobile,
                dealer.distance, destination.name
            FROM dealer
            LEFT JOIN destination ON dealer.destination_id = destination.id
        """)
        for row in self.cursor.fetchall():
            self.dealer_list.insert("", END, values=row)

    def on_select(self, event):
        selected = self.dealer_list.focus()
        if not selected:
            return
        values = self.dealer_list.item(selected, 'values')
        keys = ["code", "name", "place", "pincode", "mobile", "distance"]
        for key, value in zip(keys, values[1:]):
            self.entries[key].delete(0, END)
            self.entries[key].insert(0, value)

    def add_dealer(self):
        code = self.get_entry("code")
        name = self.get_entry("name")
        place = self.get_entry("place")
        pincode = self.get_entry("pincode")
        mobile = self.get_entry("mobile")
        distance = self.get_entry("distance")
        dest_val = self.destination_cb.get()
        destination_id = self.destination_map.get(dest_val)

        if not code or not name or not destination_id:
            messagebox.showerror("Input Error", "Code, Name, and Destination are required")
            return

        try:
            self.cursor.execute(
                "INSERT INTO dealer (code, name, place, pincode, mobile, distance, destination_id) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (code, name, place, pincode, mobile, float(distance), destination_id)
            )
            self.conn.commit()
            self.load_dealers()
            self.clear_fields()
            messagebox.showinfo("Success", "Dealer added successfully")
        except Exception as e:
            messagebox.showerror("Database Error", str(e))


    def update_dealer(self):
        selected = self.dealer_list.focus()
        if not selected:
            messagebox.showerror("Selection Error", "Please select a dealer to update")
            return

        dealer_id = self.dealer_list.item(selected, 'values')[0]
        destination_id = self.destination_map.get(self.destination_cb.get())

        try:
            self.cursor.execute(
                "UPDATE dealer SET code=?, name=?, place=?, pincode=?, mobile=?, distance=?, destination_id=? WHERE id=?",
                (
                    self.get_entry("code"),
                    self.get_entry("name"),
                    self.get_entry("place"),
                    self.get_entry("pincode"),
                    self.get_entry("mobile"),
                    float(self.get_entry("distance")),
                    destination_id,
                    dealer_id
                )
            )
            self.conn.commit()
            self.load_dealers()
            self.clear_fields()
            messagebox.showinfo("Success", "Dealer updated successfully")
        except Exception as e:
            messagebox.showerror("Database Error", str(e))

    def delete_dealer(self):
        selected = self.dealer_list.focus()
        if not selected:
            messagebox.showerror("Selection Error", "Please select a dealer to delete")
            return
        dealer_id = self.dealer_list.item(selected, 'values')[0]
        if messagebox.askyesno("Confirm Delete", "Are you sure you want to delete this dealer?"):
            try:
                self.cursor.execute("DELETE FROM dealer WHERE id=?", (dealer_id,))
                self.conn.commit()
                self.load_dealers()
                self.clear_fields()
                messagebox.showinfo("Success", "Dealer deleted successfully")
            except Exception as e:
                messagebox.showerror("Database Error", str(e))


    def import_dealers_from_file(self, file_path=None):
        # If no file_path is provided, open file dialog
        if not file_path:
            file_path = filedialog.askopenfilename(
                title="Select Excel File",
                filetypes=[("Excel files", "*.xlsx *.xls")]
            )
            if not file_path:
                return  # User cancelled the file selection
        
        try:
            # Read the Excel file
            excel_file = pd.ExcelFile(file_path)
            
            # Get all sheet names
            sheet_names = excel_file.sheet_names
            
            skipped_rows = []
            
            for sheet_name in sheet_names:
                # Skip empty sheets (like Sheet1)
                if sheet_name == "Sheet1":
                    continue
                    
                # Check if destination exists by name or place (case-insensitive)
                self.cursor.execute(
                    "SELECT id FROM destination WHERE UPPER(name) = UPPER(?) OR UPPER(place) = UPPER(?)",
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
                    # append 'FOL' to the dealer name
                    name = f"{str(row['NAME']).strip()} FOL"
                    place = str(row['Place']).strip()
                    pincode = str(row['Pin Code']).strip()
                    mobile = str(row['Mob No.']).strip() if not pd.isna(row['Mob No.']) else ""
                    
                    # Handle distance: set to None for 'NIL' or non-numeric values
                    distance = None
                    if not pd.isna(row['Distance']):
                        if str(row['Distance']).strip().upper() == 'NIL':
                            skipped_rows.append(f"Sheet: {sheet_name}, Dealer: {code}, Distance set to NULL (was 'NIL')")
                        else:
                            try:
                                distance = float(row['Distance'])
                            except (ValueError, TypeError):
                                skipped_rows.append(f"Sheet: {sheet_name}, Dealer: {code}, Distance set to NULL (invalid: {row['Distance']})")
                    
                    # Skip rows with missing required fields
                    if not code or not name:
                        skipped_rows.append(f"Sheet: {sheet_name}, Row: {index+2}, Missing code or name")
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
                        skipped_rows.append(f"Sheet: {sheet_name}, Dealer: {code}, Error: {str(e)}")
                        continue
                
                self.conn.commit()
            
            # Reload the dealers in the UI
            self.load_dealers()
            self.clear_fields()
            
            # Show success message with warning about skipped rows or NULL distances
            message = f"Dealers imported successfully from {len(sheet_names)-1} destinations"
            if skipped_rows:
                message += f"\n\nWarnings:\n" + "\n".join(skipped_rows)
            messagebox.showinfo("Success", message)
            
        except Exception as e:
            messagebox.showerror("Import Error", f"Failed to import dealers: {str(e)}")

# To initialize the page:
# DealerManager(frame, home_frame, conn)
