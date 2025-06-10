from tkinter import *
from tkinter import messagebox
from tkinter.ttk import Treeview

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

        Button(self.form, text="Add Dealer", command=self.add_dealer).grid(row=6, column=0, pady=10)
        Button(self.form, text="Update Dealer", command=self.update_dealer).grid(row=6, column=1, pady=10)
        Button(self.form, text="Delete Dealer", command=self.delete_dealer).grid(row=6, column=2, pady=10)

        self.dealer_list = Treeview(
            self.master_frame,
            columns=("ID", "Code", "Name", "Place", "Pincode", "Mobile", "Distance"),
            show="headings"
        )
        for col in self.dealer_list["columns"]:
            self.dealer_list.heading(col, text=col)
            self.dealer_list.column(col, width=100)

        self.dealer_list.bind("<<TreeviewSelect>>", self.on_select)
        self.dealer_list.pack(fill="both", expand=True, padx=10, pady=10)

        self.load_dealers()

    def get_entry(self, field):
        return self.entries[field].get().strip()

    def clear_fields(self):
        for entry in self.entries.values():
            entry.delete(0, END)

    def load_dealers(self):
        for row in self.dealer_list.get_children():
            self.dealer_list.delete(row)

        self.cursor.execute("SELECT id, code, name, place, pincode, mobile, distance FROM dealer")
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

        if not code or not name:
            messagebox.showerror("Input Error", "Code and Name are required")
            return

        try:
            self.cursor.execute(
                "INSERT INTO dealer (code, name, place, pincode, mobile, distance) VALUES (?, ?, ?, ?, ?, ?)",
                (code, name, place, pincode, mobile, float(distance))
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
        try:
            self.cursor.execute(
                "UPDATE dealer SET code=?, name=?, place=?, pincode=?, mobile=?, distance=? WHERE id=?",
                (
                    self.get_entry("code"),
                    self.get_entry("name"),
                    self.get_entry("place"),
                    self.get_entry("pincode"),
                    self.get_entry("mobile"),
                    float(self.get_entry("distance")),
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


# To initialize the page:
# DealerManager(frame, home_frame, conn)
