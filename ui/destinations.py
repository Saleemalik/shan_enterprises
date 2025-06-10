from tkinter import *
from tkinter import messagebox
from tkinter.ttk import Treeview

class DestinationPage:
    def __init__(self, frame, home_frame, conn):
        self.frame = frame
        self.home_frame = home_frame
        self.conn = conn
        self.c = conn.cursor()

        self.c.execute('''CREATE TABLE IF NOT EXISTS destination (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            place TEXT,
            description TEXT,
            is_garage BOOLEAN DEFAULT 0
        )''')

        self.build_ui()
        self.load_destinations()

    def build_ui(self):
        Button(self.frame, text="← Back to Dashboard", command=lambda: self.home_frame.tkraise()).pack(anchor='nw', padx=10, pady=5)
        Label(self.frame, text="Destination / Garage Management", font=("Arial", 16)).pack(pady=10)

        form = Frame(self.frame)
        form.pack(pady=10)

        Label(form, text="Name").grid(row=0, column=0)
        Label(form, text="Place").grid(row=1, column=0)
        Label(form, text="Description").grid(row=2, column=0)
        Label(form, text="Is Garage").grid(row=3, column=0)

        self.name_entry = Entry(form)
        self.place_entry = Entry(form)
        self.desc_entry = Entry(form)
        self.is_garage_var = IntVar()  # Variable for Checkbutton
        self.is_garage_check = Checkbutton(form, text="", variable=self.is_garage_var)

        self.name_entry.grid(row=0, column=1)
        self.place_entry.grid(row=1, column=1)
        self.desc_entry.grid(row=2, column=1)
        self.is_garage_check.grid(row=3, column=1)

        Button(form, text="Add", command=self.add_destination).grid(row=4, column=0, pady=10)
        Button(form, text="Update", command=self.update_destination).grid(row=4, column=1, pady=10)
        Button(form, text="Delete", command=self.delete_destination).grid(row=4, column=2, pady=10)

        self.dest_list = Treeview(self.frame, columns=("ID", "Name", "Place", "Description", "Is Garage"), show="headings")
        for col in self.dest_list["columns"]:
            self.dest_list.heading(col, text=col)
            self.dest_list.column(col, width=120)
        self.dest_list.bind("<<TreeviewSelect>>", self.on_select)
        self.dest_list.pack(fill="both", expand=True, padx=10, pady=10)

    def add_destination(self):
        try:
            name = self.name_entry.get().strip()
            place = self.place_entry.get().strip()
            desc = self.desc_entry.get().strip()
            is_garage = self.is_garage_var.get()
            if not name:
                raise Exception("Name is required")
            self.c.execute("INSERT INTO destination (name, place, description, is_garage) VALUES (?, ?, ?, ?)",
                           (name, place, desc, is_garage))
            self.conn.commit()
            self.load_destinations()
            self.clear_fields()
            messagebox.showinfo("Success", "Destination added successfully")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def update_destination(self):
        selected = self.dest_list.focus()
        if not selected:
            messagebox.showerror("Select Error", "Please select a destination to update")
            return
        dest_id = self.dest_list.item(selected, 'values')[0]
        try:
            self.c.execute("UPDATE destination SET name=?, place=?, description=?, is_garage=? WHERE id=?",
                           (self.name_entry.get(), self.place_entry.get(), self.desc_entry.get(), self.is_garage_var.get(), dest_id))
            self.conn.commit()
            self.load_destinations()
            self.clear_fields()
            messagebox.showinfo("Updated", "Destination updated")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def delete_destination(self):
        selected = self.dest_list.focus()
        if not selected:
            messagebox.showerror("Select Error", "Please select a destination to delete")
            return
        dest_id = self.dest_list.item(selected, 'values')[0]
        if messagebox.askyesno("Delete", "Are you sure to delete this destination?"):
            self.c.execute("DELETE FROM destination WHERE id=?", (dest_id,))
            self.conn.commit()
            self.load_destinations()
            self.clear_fields()

    def load_destinations(self):
        for row in self.dest_list.get_children():
            self.dest_list.delete(row)
        for row in self.c.execute("SELECT * FROM destination"):
            row = list(row)
            row[4] = "Yes" if row[4] else "No"
            self.dest_list.insert("", END, values=row)

    def on_select(self, event):
        selected = self.dest_list.focus()
        if not selected:
            return
        values = self.dest_list.item(selected, 'values')
        self.name_entry.delete(0, END); self.name_entry.insert(0, values[1])
        self.place_entry.delete(0, END); self.place_entry.insert(0, values[2])
        self.desc_entry.delete(0, END); self.desc_entry.insert(0, values[3])
        self.is_garage_var.set(1 if values[4] == "Yes" else 0)

    def clear_fields(self):
        self.name_entry.delete(0, END)
        self.place_entry.delete(0, END)
        self.desc_entry.delete(0, END)
        self.is_garage_var.set(0)