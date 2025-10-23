from tkinter import *
from tkinter import messagebox, Toplevel
from tkinter.ttk import Treeview
import re

class DestinationPage:
    def __init__(self, frame, home_frame, conn):
        self.frame = frame
        self.home_frame = home_frame
        self.conn = conn
        self.c = conn.cursor()
        self.frame.bind("<<ShowFrame>>", lambda e: self.load_destinations())

        # Destination table
        self.c.execute('''CREATE TABLE IF NOT EXISTS destination (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            place TEXT,
            description TEXT,
            is_garage BOOLEAN DEFAULT 0
        )''')

        self.build_ui()
        self.load_destinations()

    # ---------- UI ----------
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
        self.is_garage_var = IntVar()
        self.is_garage_check = Checkbutton(form, variable=self.is_garage_var)

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

    # ---------- ADD ----------
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
            dest_id = self.c.lastrowid
            self.conn.commit()

            if is_garage:
                self.popup_garage_dealer(dest_id, name, place)
            else:
                messagebox.showinfo("Success", "Destination added successfully")

            self.load_destinations()
            self.clear_fields()

        except Exception as e:
            messagebox.showerror("Error", str(e))

    # ---------- UPDATE ----------
    def update_destination(self):
        selected = self.dest_list.focus()
        if not selected:
            messagebox.showerror("Select Error", "Please select a destination to update")
            return

        dest_id = self.dest_list.item(selected, 'values')[0]
        try:
            name = self.name_entry.get().strip()
            place = self.place_entry.get().strip()
            desc = self.desc_entry.get().strip()
            is_garage = self.is_garage_var.get()

            # Get previous garage status
            self.c.execute("SELECT is_garage FROM destination WHERE id=?", (dest_id,))
            old_is_garage = self.c.fetchone()[0]

            # Update destination
            self.c.execute("UPDATE destination SET name=?, place=?, description=?, is_garage=? WHERE id=?",
                        (name, place, desc, is_garage, dest_id))
            self.conn.commit()

            # -----------------------------
            # CASE 1: Converted to Garage
            # -----------------------------
            if is_garage and not old_is_garage:
                # Inactivate all existing dealers
                self.c.execute("UPDATE dealer SET active=0 WHERE destination_id=?", (dest_id,))

                # Check for existing garage dealer with same name
                self.c.execute("SELECT id FROM dealer WHERE name=? AND destination_id=?", (name, dest_id))
                existing_dealer = self.c.fetchone()

                if existing_dealer:
                    # Reactivate if already exists
                    self.c.execute("UPDATE dealer SET active=1 WHERE id=?", (existing_dealer[0],))
                    self.conn.commit()
                    self.popup_garage_dealer(dest_id, name, place, edit_mode=True)
                else:
                    # Create new garage dealer
                    dealer_code = f"GAR-{int(dest_id):04d}"
                    self.c.execute("""INSERT INTO dealer (code, name, place, distance, mobile, pincode, destination_id, active)
                                    VALUES (?, ?, ?, 0, '', '', ?, 1)""",
                                (dealer_code, name, place, dest_id))
                    self.conn.commit()
                    self.popup_garage_dealer(dest_id, name, place, edit_mode=True)

            # -----------------------------
            # CASE 2: Converted back to Common Destination
            # -----------------------------
            elif not is_garage and old_is_garage:
                # Reactivate all dealers (including garage dealer)
                self.c.execute("UPDATE dealer SET active=1 WHERE destination_id=?", (dest_id,))
                self.conn.commit()
                messagebox.showinfo("Updated", "Destination updated successfully.")

            # -----------------------------
            # CASE 3: Regular update
            # -----------------------------
            elif is_garage and old_is_garage:
                # Garage remains garage → edit garage dealer if needed
                self.popup_garage_dealer(dest_id, name, place, edit_mode=True)
            else:
                messagebox.showinfo("Updated", "Destination updated successfully")

            self.load_destinations()
            self.clear_fields()

        except Exception as e:
            messagebox.showerror("Error", str(e))

    # ---------- DELETE ----------
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

    # ---------- POPUP ----------
    def popup_garage_dealer(self, dest_id, name, place, edit_mode=False):
        """Popup for creating or editing garage dealer."""
        popup = Toplevel(self.frame)
        popup.title(f"Garage Dealer - {name}")
        popup.geometry("320x330")
        popup.resizable(False, False)
        popup.transient(self.frame)
        popup.grab_set()

        # Center the popup
        popup.update_idletasks()
        w, h = 320, 330
        x = popup.winfo_screenwidth() // 2 - w // 2
        y = popup.winfo_screenheight() // 2 - h // 2
        popup.geometry(f"{w}x{h}+{x}+{y}")

        Label(popup, text=f"Garage Dealer for: {name}", font=("Arial", 12, "bold")).pack(pady=8)
        form = Frame(popup)
        form.pack(pady=5)

        Label(form, text="Distance (KM):").grid(row=0, column=0, sticky="e", pady=4)
        dist_entry = Entry(form, width=15)
        dist_entry.grid(row=0, column=1)

        Label(form, text="Mobile:").grid(row=1, column=0, sticky="e", pady=4)
        mob_entry = Entry(form, width=15)
        mob_entry.grid(row=1, column=1)

        Label(form, text="Pincode:").grid(row=2, column=0, sticky="e", pady=4)
        pin_entry = Entry(form, width=15)
        pin_entry.grid(row=2, column=1)

        # Prefill if exists
        self.c.execute("SELECT distance, mobile, pincode FROM dealer WHERE destination_id=?", (dest_id,))
        dealer = self.c.fetchone()
        if dealer:
            dist_entry.insert(0, dealer[0] or "")
            mob_entry.insert(0, dealer[1] or "")
            pin_entry.insert(0, dealer[2] or "")

        def save_dealer():
            distance = dist_entry.get().strip()
            mobile = mob_entry.get().strip()
            pincode = pin_entry.get().strip()

            if distance and not re.match(r'^\d+(\.\d+)?$', distance):
                messagebox.showerror("Invalid Input", "Distance must be a numeric value.")
                return

            # Check if dealer exists for this destination
            self.c.execute("SELECT id FROM dealer WHERE name=? AND place=? AND destination_id=?", (name, place, dest_id))
            existing = self.c.fetchone()

            if existing:
                self.c.execute("""UPDATE dealer 
                                  SET distance=?, mobile=?, pincode=? 
                                  WHERE name=? AND place=? AND destination_id=?""",
                               ( distance or 0, mobile, pincode, name, place, dest_id))
            else:
                dealer_code = f"GAR-{int(dest_id):04d}"
                self.c.execute("""INSERT INTO dealer (code, name, place, distance, mobile, pincode, destination_id)
                                  VALUES (?, ?, ?, ?, ?, ?, ?)""",
                               (dealer_code, name, place, distance or 0, mobile, pincode, dest_id))
            self.conn.commit()
            popup.destroy()
            messagebox.showinfo("Saved", "Garage Dealer saved successfully.")

        Button(popup, text="Save Dealer", command=save_dealer, width=15, bg="#4CAF50", fg="white").pack(pady=12)

    # ---------- LOAD ----------
    def load_destinations(self):
        for row in self.dest_list.get_children():
            self.dest_list.delete(row)
        for row in self.c.execute("SELECT * FROM destination"):
            row = list(row)
            row[4] = "Yes" if row[4] else "No"
            self.dest_list.insert("", END, values=row)

    # ---------- SELECT ----------
    def on_select(self, event):
        selected = self.dest_list.focus()
        if not selected:
            return
        values = self.dest_list.item(selected, 'values')
        self.name_entry.delete(0, END); self.name_entry.insert(0, values[1])
        self.place_entry.delete(0, END); self.place_entry.insert(0, values[2])
        self.desc_entry.delete(0, END); self.desc_entry.insert(0, values[3])
        self.is_garage_var.set(1 if values[4] == "Yes" else 0)

    # ---------- CLEAR ----------
    def clear_fields(self):
        self.name_entry.delete(0, END)
        self.place_entry.delete(0, END)
        self.desc_entry.delete(0, END)
        self.is_garage_var.set(0)
