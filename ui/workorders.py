from tkinter import *
from tkinter import messagebox
from tkinter.ttk import Treeview

class WorkOrderRatePage:
    def __init__(self, frame, home_frame, conn):
        self.frame = frame
        self.home_frame = home_frame
        self.conn = conn
        self.c = conn.cursor()
        self.frame.bind("<<ShowFrame>>", lambda e: self.load_rates())
        
        self.c.execute('''CREATE TABLE IF NOT EXISTS rate_range (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            from_km REAL,
            to_km REAL,
            rate REAL,
            is_mtk BOOLEAN DEFAULT 1
        )''')

        self.build_ui()
        self.load_rates()

    def build_ui(self):
        Button(self.frame, text="← Back to Dashboard", command=lambda: self.home_frame.tkraise()).pack(anchor='nw', padx=10, pady=5)
        Label(self.frame, text="Work Order Rate Management", font=("Arial", 16)).pack(pady=10)

        form = Frame(self.frame)
        form.pack(pady=10)

        Label(form, text="From (km)").grid(row=0, column=0)
        Label(form, text="To (km)").grid(row=1, column=0)
        Label(form, text="Rate").grid(row=2, column=0)
        Label(form, text="Is MTK").grid(row=3, column=0)

        self.from_entry = Entry(form)
        self.to_entry = Entry(form)
        self.rate_entry = Entry(form)
        self.is_mtk_var = IntVar(value=1)
        self.is_mtk_check = Checkbutton(form, variable=self.is_mtk_var)

        self.from_entry.grid(row=0, column=1)
        self.to_entry.grid(row=1, column=1)
        self.rate_entry.grid(row=2, column=1)
        self.is_mtk_var = BooleanVar(value=True)
        self.is_mtk_check = Checkbutton(form, text="MTK", variable=self.is_mtk_var)
        self.is_mtk_check.grid(row=3, columnspan=2, pady=5)

        Button(form, text="Add Rate", command=self.add_rate).grid(row=4, column=0, pady=10)
        Button(form, text="Update Rate", command=self.update_rate).grid(row=4, column=1, pady=10)
        Button(form, text="Delete Rate", command=self.delete_rate).grid(row=4, column=2, pady=10)

        self.rate_list = Treeview(self.frame, columns=("ID", "From", "To", "Rate", "IS MTK"), show="headings")
        for col in self.rate_list["columns"]:
            self.rate_list.heading(col, text=col)
            self.rate_list.column(col, width=100)

        self.rate_list.bind("<<TreeviewSelect>>", self.on_select)
        self.rate_list.pack(fill="both", expand=True, padx=10, pady=10)

    def add_rate(self):
        try:
            from_km = float(self.from_entry.get())
            to_km = float(self.to_entry.get())
            rate = float(self.rate_entry.get())
            is_mtk = 1 if self.is_mtk_var.get() else 0
            self.c.execute("INSERT INTO rate_range (from_km, to_km, rate, is_mtk) VALUES (?, ?, ?, ?)",
                           (from_km, to_km, rate, is_mtk))
            self.conn.commit()
            self.load_rates()
            self.clear_fields()
            messagebox.showinfo("Success", "Rate added successfully")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def update_rate(self):
        selected = self.rate_list.focus()
        if not selected:
            messagebox.showerror("Selection Error", "Please select a rate to update")
            return
        rate_id = self.rate_list.item(selected, 'values')[0]
        is_mtk = 1 if self.is_mtk_var.get() else 0
        try:
            self.c.execute("UPDATE rate_range SET from_km=?, to_km=?, rate=?, is_mtk=? WHERE id=?",
                          (float(self.from_entry.get()), float(self.to_entry.get()), float(self.rate_entry.get()), is_mtk, rate_id))
            self.conn.commit()
            self.load_rates()
            self.clear_fields()
            messagebox.showinfo("Success", "Rate updated successfully")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def delete_rate(self):
        selected = self.rate_list.focus()
        if not selected:
            messagebox.showerror("Selection Error", "Please select a rate to delete")
            return
        rate_id = self.rate_list.item(selected, 'values')[0]
        if messagebox.askyesno("Confirm Delete", "Are you sure you want to delete this rate?"):
            try:
                self.c.execute("DELETE FROM rate_range WHERE id=?", (rate_id,))
                self.conn.commit()
                self.load_rates()
                self.clear_fields()
                messagebox.showinfo("Success", "Rate deleted successfully")
            except Exception as e:
                messagebox.showerror("Error", str(e))

    def clear_fields(self):
        self.from_entry.delete(0, END)
        self.to_entry.delete(0, END)
        self.rate_entry.delete(0, END)
        self.is_mtk_var.set(True)

    def load_rates(self):
        for row in self.rate_list.get_children():
            self.rate_list.delete(row)
        self.c.execute("SELECT * FROM rate_range")
        for row in self.c.fetchall():
            id, from_km, to_km, rate, is_mtk = row
            self.rate_list.insert("", END, values=(id, from_km, to_km, rate, "Yes" if is_mtk else "No"))

    def on_select(self, event):
        selected = self.rate_list.focus()
        if not selected:
            return
        values = self.rate_list.item(selected, 'values')
        self.from_entry.delete(0, END); self.from_entry.insert(0, values[1])
        self.to_entry.delete(0, END); self.to_entry.insert(0, values[2])
        self.rate_entry.delete(0, END); self.rate_entry.insert(0, values[3])
        self.is_mtk_var.set(True if values[4] == "Yes" else False)
