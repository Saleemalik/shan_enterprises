import os, json
import platform
from tkinter import *
from tkinter import ttk, messagebox
from datetime import datetime
from collections import defaultdict
from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, TableStyle, Spacer
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from num2words import num2words
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_RIGHT
from tkcalendar import DateEntry


class MainBillPage:
    def __init__(self, frame, home_frame, conn):
        self.frame = frame
        self.home_frame = home_frame
        self.conn = conn
        self.c = conn.cursor()
        self.frame.bind("<<ShowFrame>>", lambda e: self.refresh())
        
        # --- TABLE UPDATE ---
        self.c.execute('''
            CREATE TABLE IF NOT EXISTS main_bill (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                bill_number TEXT UNIQUE,
                letter_note TEXT,
                to_address TEXT,
                date_of_clearing TEXT,
                fact_gst_number TEXT,
                product TEXT DEFAULT 'FACTOMFOS',
                hsn_sac_code TEXT,
                year TEXT,
                is_garage BOOLEAN DEFAULT 0
            )
        ''')

        self.c.execute('''
            CREATE TABLE IF NOT EXISTS main_bill_entries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                main_bill_id INTEGER,
                destination_entry_id INTEGER,
                FOREIGN KEY (main_bill_id) REFERENCES main_bill(id),
                FOREIGN KEY (destination_entry_id) REFERENCES destination_entry(id)
            )
        ''')

        Label(self.frame, text="Generate Main Bill", font=("Arial", 16, "bold")).pack(pady=10)
        Button(self.frame, text="← Back to Dashboard", command=lambda: self.home_frame.tkraise()).pack(anchor='nw', padx=10)

        form_frame = Frame(self.frame)
        form_frame.pack(padx=20, pady=10)

        Label(form_frame, text="Bill Number").grid(row=0, column=0, sticky=W)
        self.bill_number_entry = Entry(form_frame, width=40)
        self.bill_number_entry.grid(row=0, column=1, pady=5)

        Label(form_frame, text="Letter Note").grid(row=1, column=0, sticky=NW)
        self.letter_note_text = Text(form_frame, height=3, width=40)
        self.letter_note_text.grid(row=1, column=1, pady=5)

        Label(form_frame, text="To Address").grid(row=2, column=0, sticky=NW)
        self.to_address_text = Text(form_frame, height=3, width=40)
        self.to_address_text.grid(row=2, column=1, pady=5)

        Label(form_frame, text="Date of Clearing").grid(row=3, column=0, sticky=W)
        self.date_entry = DateEntry(form_frame, width=37, date_pattern='dd-mm-yyyy', 
                                    background='darkblue', foreground='white', borderwidth=2)
        self.date_entry.set_date(datetime.today())  # set today's date as default
        self.date_entry.grid(row=3, column=1, pady=5)

        Label(form_frame, text="FACT GST Number").grid(row=4, column=0, sticky=W)
        self.gst_entry = Entry(form_frame, width=40)
        self.gst_entry.grid(row=4, column=1, pady=5)

        Label(form_frame, text="Product").grid(row=5, column=0, sticky=W)
        self.product_entry = Entry(form_frame, width=40)
        self.product_entry.insert(0, "FACTOMFOS")
        self.product_entry.grid(row=5, column=1, pady=5)

        Label(form_frame, text="HSN/SAC Code").grid(row=6, column=0, sticky=W)
        self.hsn_entry = Entry(form_frame, width=40)
        self.hsn_entry.grid(row=6, column=1, pady=5)

        Label(form_frame, text="Year").grid(row=7, column=0, sticky=W)
        self.year_entry = Entry(form_frame, width=40)
        self.year_entry.grid(row=7, column=1, pady=5)

        # ✅ NEW: "Is Garage" checkbox
        self.is_garage_var = IntVar()
        Checkbutton(
            form_frame, text="Is Garage Bill",
            variable=self.is_garage_var,
            command=self.load_destination_entries
        ).grid(row=8, column=1, sticky=W, pady=5)

        # Destination Entries Table
        Label(self.frame, text="Select Destination Entries", font=("Arial", 12, "bold")).pack(pady=10)

        # Updated Destination Entries Table
        self.dest_tree = ttk.Treeview(
            self.frame,
            columns=("id", "date", "destination", "bill_number", "ranges"),
            show="headings",
            selectmode="extended"
        )

        for col, title in zip(
            ["id", "date", "destination", "bill_number", "ranges"],
            ["ID", "Date", "Destination", "Bill Number", "Ranges"]
        ):
            self.dest_tree.heading(col, text=title)
            if col == "ranges":
                self.dest_tree.column(col, width=200)
            elif col in ("id", "date"):
                self.dest_tree.column(col, width=80)
            else:
                self.dest_tree.column(col, width=150)

        self.dest_tree.pack(padx=20, fill="both", expand=True)
        Button(self.frame, text="🔍 Preview Main Bill", command=self.open_preview_page).pack(pady=10)

        self.load_destination_entries()
        self.load_form_cache()
        
        self.frame.bind_all("<Control-r>", self.refresh)
        self.refresh()

    def refresh(self, event=None):
        self.load_destination_entries()
        self.load_form_cache()
    
    def load_destination_entries(self):
        self.dest_tree.delete(*self.dest_tree.get_children())

        is_garage = self.is_garage_var.get()

        query = """
            SELECT 
                de.id,
                de.date,
                d.name AS destination,
                de.bill_number,
                (
                    SELECT GROUP_CONCAT(r, ', ')
                    FROM (
                        SELECT DISTINCT 
                            TRIM(REPLACE(rr.from_km, '.0', '')) || '-' || TRIM(REPLACE(rr.to_km, '.0', '')) AS r
                        FROM rate_range rr
                        JOIN range_entry re2 ON re2.rate_range_id = rr.id
                        WHERE re2.destination_entry_id = de.id
                        ORDER BY rr.from_km
                    )
                ) AS ranges
            FROM destination_entry de
            JOIN destination d ON de.destination_id = d.id
            WHERE (de.main_bill_id IS NULL OR de.main_bill_id = "")
            AND d.is_garage = ?
            GROUP BY de.id
            ORDER BY de.date DESC, de.id DESC
        """

        self.c.execute(query, (is_garage,))
        rows = self.c.fetchall()

        for row in rows:
            self.dest_tree.insert("", END, values=row)

    def save_form_cache(self):
        cache = {
            "bill_number": self.bill_number_entry.get(),
            "letter_note": self.letter_note_text.get("1.0", END).strip(),
            "to_address": self.to_address_text.get("1.0", END).strip(),
            "date_of_clearing": self.date_entry.get(),
            "fact_gst_number": self.gst_entry.get(),
            "product": self.product_entry.get(),
            "hsn_sac_code": self.hsn_entry.get(),
            "year": self.year_entry.get(),
            "is_garage": self.is_garage_var.get(),
        }
        with open("main_bill_cache.json", "w") as f:
            json.dump(cache, f)

    def load_form_cache(self):
        if os.path.exists("main_bill_cache.json"):
            with open("main_bill_cache.json", "r") as f:
                data = json.load(f)

            # Clear and insert into each widget
            self.bill_number_entry.delete(0, END)
            self.bill_number_entry.insert(0, data.get("bill_number", ""))

            self.letter_note_text.delete("1.0", END)
            self.letter_note_text.insert("1.0", data.get("letter_note", ""))

            self.to_address_text.delete("1.0", END)
            self.to_address_text.insert("1.0", data.get("to_address", ""))

            self.gst_entry.delete(0, END)
            self.gst_entry.insert(0, data.get("fact_gst_number", ""))

            self.product_entry.delete(0, END)
            self.product_entry.insert(0, data.get("product", "FACTOMFOS"))

            self.hsn_entry.delete(0, END)
            self.hsn_entry.insert(0, data.get("hsn_sac_code", ""))

            self.year_entry.delete(0, END)
            self.year_entry.insert(0, data.get("year", ""))

    def generate_preview(self):
        selected = self.dest_tree.selection()
        if not selected:
            messagebox.showwarning("No selection", "Please select at least one destination entry.")
            return

        dest_entry_ids = [self.dest_tree.item(i, "values")[0] for i in selected]
        placeholders = ",".join("?" for _ in dest_entry_ids)

        query = f'''
            SELECT d.name AS destination, re.id AS range_entry_id, rr.from_km, rr.to_km, rr.rate, rr.is_mtk,
                   dr.no_bags, dr.mt, dr.km, dr.mtk, dr.amount
            FROM range_entry re
            JOIN destination d ON de.destination_id = d.id
            JOIN dealer_entry dr ON dr.range_entry_id = re.id
            JOIN rate_range rr ON re.rate_range_id = rr.id
            WHERE de.id IN ({placeholders})
            JOIN destination_entry de ON re.destination_entry_id = de.id
            ORDER BY d.name, rr.from_km
        '''

        self.c.execute(query, dest_entry_ids)
        rows = self.c.fetchall()

        # Grouping by (destination, range)
        grouped = {}
        for row in rows:
            key = (row[0], row[1], row[2], row[3], row[4], row[5])  # destination, range_entry_id, from_km, to_km, rate, is_mtk
            grouped.setdefault(key, []).append(row)

        self.preview_tree.delete(*self.preview_tree.get_children())
        sl = 1
        grand_qty = grand_mt = grand_mtk = grand_amount = 0

        for (destination, _, from_km, to_km, rate, is_mtk), entries in grouped.items():
            qty = sum(r[6] for r in entries)
            mt = sum(r[7] for r in entries)
            mtk = sum(r[9] for r in entries)
            amount = sum(r[10] for r in entries)

            self.preview_tree.insert("", END, values=(
                sl, destination, qty, round(mt, 2), f"{from_km}-{to_km}", round(mtk, 2), rate, round(amount, 2)
            ))

            grand_qty += qty
            grand_mt += mt
            grand_mtk += mtk
            grand_amount += amount
            sl += 1

        # Add grand total row
        self.preview_tree.insert("", END, values=(
            "", "TOTAL", grand_qty, round(grand_mt, 2), "", round(grand_mtk, 2), "", round(grand_amount, 2)
        ))
        
    def open_preview_page(self):
        selected = self.dest_tree.selection()
        if not selected:
            messagebox.showwarning("No selection", "Please select at least one destination entry.")
            return

        dest_entry_ids = [int(self.dest_tree.item(i, "values")[0]) for i in selected]

        bill_data = {
            "bill_number": self.bill_number_entry.get().strip(),
            "letter_note": self.letter_note_text.get("1.0", END).strip(),
            "to_address": self.to_address_text.get("1.0", END).strip(),
            "date_of_clearing": self.date_entry.get().strip(),
            "fact_gst_number": self.gst_entry.get().strip(),
            "product": self.product_entry.get().strip(),
            "hsn_sac_code": self.hsn_entry.get().strip(),
            "year": self.year_entry.get().strip(),
            "is_garage": self.is_garage_var.get(),
            "created_date": datetime.today().strftime("%d-%m-%Y")
        }

        if not bill_data["bill_number"] or not bill_data["date_of_clearing"]:
            messagebox.showwarning("Missing Info", "Bill number and Date of Clearing are required.")
            return

        from ui.mainbillentry import MainBillPreviewPage
        preview_frame = Frame(self.frame.master)
        preview_frame.grid(row=0, column=0, sticky='nsew')

        self.preview_page = MainBillPreviewPage(preview_frame, self.frame, self.conn, bill_data, dest_entry_ids)
        preview_frame.tkraise()

        # Ensure scroll works
        self.frame.master.update_idletasks()
        self.frame.master.master.configure(scrollregion=self.frame.master.master.bbox("all"))
        self.save_form_cache()

class MainBillPreviewPage:
    def __init__(self, frame, home_frame, conn, main_bill_data, destination_entry_ids):
        self.frame = frame
        self.home_frame = home_frame
        self.conn = conn
        self.c = conn.cursor()
        self.main_bill_data = main_bill_data
        self.destination_entry_ids = destination_entry_ids

        self.build_ui()
    
    def build_ui(self):
        for widget in self.frame.winfo_children():
            widget.destroy()

        # Header - Fully centered
        Label(self.frame, text="M/S. SHAN ENTERPRISES", font=("Arial", 16, "bold")).pack(anchor="center")
        Label(
            self.frame,
            text="Clearing & Transporting Contractor\n21/4185 C, Meenchandathally, Gate\nP.O. Arts College Calicut – 673018\nMob: 9447004108",
            justify=CENTER
        ).pack()
        Label(self.frame, text="GST32ACNFSB060K1ZP", font=("Arial", 10, "bold")).pack(anchor="center", pady=(0, 10))

        # Container frame for all aligned rows
        container = Frame(self.frame)
        container.pack(padx=280, fill='x')  # Increased padding here

        # Row 1: BILL NO and DATE
        row1 = Frame(container)
        row1.pack(fill='x', pady=(2, 2))
        row1.grid_columnconfigure(0, weight=1)
        row1.grid_columnconfigure(1, weight=1)
        Label(row1, text=f"BILL NO: {self.main_bill_data['bill_number']}", anchor="w").grid(row=0, column=0, sticky="w")
        Label(row1, text=f"Date: {self.main_bill_data['created_date']}", anchor="e").grid(row=0, column=1, sticky="e")

        # TO Address
        Label(self.frame, text="TO", font=("Arial", 10, "bold")).pack(anchor="w", padx=280)
        Label(self.frame, text=self.main_bill_data['to_address'], justify=LEFT).pack(anchor="w", padx=280)

        # Row 2: Letter Note and Date of Clearing
        row2 = Frame(self.frame)
        row2.pack(fill='x', padx=280, pady=(5, 5))
        row2.grid_columnconfigure(0, weight=1)
        row2.grid_columnconfigure(1, weight=1)
        Label(row2, text=f"Sir,\nRef:- {self.main_bill_data['letter_note']}", justify=LEFT).grid(row=0, column=0, sticky="w")

        date_box = Frame(row2, bd=1, relief="solid", padx=5, pady=3)
        date_box.grid(row=0, column=1, sticky="e")
        Label(date_box, text=f"Date of Clearing:\n {self.main_bill_data['date_of_clearing']}").pack()

        # Row 3: PRODUCT and WESTHILL RH
        row3 = Frame(self.frame)
        row3.pack(fill="x", padx=280, pady=(3, 0))
        row3.grid_columnconfigure(0, weight=1)
        row3.grid_columnconfigure(1, weight=1)
        Label(row3, text=f"PRODUCT: {self.main_bill_data['product']}", anchor="w").grid(row=0, column=0, sticky="w")
        Label(row3, text="WESTHILL RH", anchor="e").grid(row=0, column=1, sticky="e")

        # Centered FACT GST
        Label(self.frame, text=f"FACT GST {self.main_bill_data['fact_gst_number']}", font=("Arial", 10)).pack(anchor="center", pady=(3, 3))

        # Row 4: HSN and Year
        row4 = Frame(self.frame)
        row4.pack(fill="x", padx=280)
        row4.grid_columnconfigure(0, weight=1)
        row4.grid_columnconfigure(1, weight=1)
        Label(row4, text=f"HSN/SAC CODE: {self.main_bill_data['hsn_sac_code']}", font=("Arial", 10, "bold")).grid(row=0, column=0, sticky="w")
        Label(row4, text=f"YEAR: {self.main_bill_data['year']}", font=("Arial", 10, "bold")).grid(row=0, column=1, sticky="e")

        # Table section
        self.build_grouped_table()

        # Buttons
        Button(self.frame, text="💾 Save Main Bill", command=self.save_main_bill).pack(pady=(10, 5))
        Button(self.frame, text="🖨️ Export PDF", command=self.export_pdf).pack(pady=(0, 10))
        Button(self.frame, text="← Back", command=lambda: self.home_frame.tkraise()).pack(pady=(0, 10))

    def build_grouped_table(self):
        Label(self.frame, text="TRANSPORTATION", font=("Arial", 12, "bold")).pack(pady=(10, 0))

        columns = ("destination", "qty_mt", "mtk", "amount")
        self.tree = ttk.Treeview(self.frame, columns=columns, show="tree headings")

        self.tree.heading("#0", text="Slab")
        self.tree.column("#0", width=200)

        self.tree.heading("destination", text="Destination")
        self.tree.column("destination", width=200)

        self.tree.heading("qty_mt", text="Qty / MT")
        self.tree.column("qty_mt", width=100, anchor="center")

        self.tree.heading("mtk", text="MTK")
        self.tree.column("mtk", width=80, anchor="center")

        self.tree.heading("amount", text="Amount")
        self.tree.column("amount", width=100, anchor="center")

        self.tree.pack(padx=10, pady=5, fill="x")

        placeholders = ",".join("?" for _ in self.destination_entry_ids)
        query = f'''
            SELECT rr.from_km, rr.to_km, rr.rate, rr.is_mtk,
                d.name AS dealer_name,
                (ds.name || CASE WHEN ds.place IS NOT NULL AND ds.place != '' THEN ' (' || ds.place || ')' ELSE '' END) AS destination_name,
                dr.no_bags, dr.mt, dr.km, dr.mtk, dr.amount
            FROM dealer_entry dr
            JOIN range_entry re ON dr.range_entry_id = re.id
            JOIN destination_entry de ON re.destination_entry_id = de.id
            JOIN dealer d ON dr.dealer_id = d.id
            JOIN destination ds ON de.destination_id = ds.id
            JOIN rate_range rr ON re.rate_range_id = rr.id
            WHERE de.id IN ({placeholders})
            ORDER BY rr.from_km, ds.name, d.name
        '''
        self.c.execute(query, self.destination_entry_ids)
        rows = self.c.fetchall()

        grouped = defaultdict(list)
        for row in rows:
            key = (row[0], row[1], row[2], row[3])  # from_km, to_km, rate, is_mtk
            grouped[key].append(row)

        self.grand_qty = self.grand_mt = self.grand_mtk = self.grand_amount = 0

        for (from_km, to_km, rate, is_mtk), entries in grouped.items():
            slab_label = f"SLAB {from_km}-{to_km} KM @ ₹{rate:.2f}"
            parent = self.tree.insert("", "end", text=slab_label)

            slab_qty = slab_mt = slab_mtk = slab_amount = 0

            for entry in entries:
                destination_name = entry[5]
                qty = entry[6]
                mt = entry[7]
                mtk = entry[9]
                amount = entry[10]

                self.tree.insert(parent, "end", text="", values=(
                    destination_name,
                    f"{qty} / {round(mt, 2)}",
                    round(mtk, 2),
                    round(amount, 2)
                ))

                slab_qty += qty
                slab_mt += mt
                slab_mtk += mtk
                slab_amount += amount

            self.tree.insert(parent, "end", text="TOTAL", values=(
                "",
                f"{slab_qty} / {round(slab_mt, 2)}",
                round(slab_mtk, 2),
                round(slab_amount, 2)
            ))

            self.grand_qty += slab_qty
            self.grand_mt += slab_mt
            self.grand_mtk += slab_mtk
            self.grand_amount += slab_amount

        self.tree.insert("", "end", text="GRAND TOTAL", values=(
            "",
            f"{self.grand_qty} / {round(self.grand_mt, 2)}",
            round(self.grand_mtk, 2),
            round(self.grand_amount, 2)
        ))

        amount = round(self.grand_amount, 2)
        amount_words = num2words(amount, to='currency', lang='en_IN').replace("euro", "rupees").replace("cents", "paise").capitalize()

        Label(
            self.frame,
            text=f"We are claiming for Rs. {amount:,.2f} ({amount_words})",
            font=("Arial", 10, "bold"),
            pady=10
        ).pack()

    def save_main_bill(self):
        try:
            # Check if the bill number already exists
            self.c.execute("SELECT id FROM main_bill WHERE bill_number = ?", (self.main_bill_data["bill_number"],))
            existing = self.c.fetchone()

            if existing:
                main_bill_id = existing[0]
                # Ask for confirmation before updating
                confirm = messagebox.askyesno(
                    "Confirm Update",
                    f"Bill number '{self.main_bill_data['bill_number']}' already exists.\nDo you want to update it?"
                )
                if not confirm:
                    return  # Cancel the save if user selects "No"

                # Update existing main bill
                self.c.execute('''
                    UPDATE main_bill SET
                        letter_note = ?, to_address = ?, date_of_clearing = ?,
                        fact_gst_number = ?, product = ?, hsn_sac_code = ?, year = ?
                    WHERE id = ?
                ''', (
                    self.main_bill_data["letter_note"],
                    self.main_bill_data["to_address"],
                    self.main_bill_data["date_of_clearing"],
                    self.main_bill_data["fact_gst_number"],
                    self.main_bill_data["product"],
                    self.main_bill_data["hsn_sac_code"],
                    self.main_bill_data["year"],
                    main_bill_id
                ))
            else:
                # Insert new main bill
                self.c.execute('''
                    INSERT INTO main_bill (
                        bill_number, letter_note, to_address, date_of_clearing,
                        fact_gst_number, product, hsn_sac_code, year
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    self.main_bill_data["bill_number"],
                    self.main_bill_data["letter_note"],
                    self.main_bill_data["to_address"],
                    self.main_bill_data["date_of_clearing"],
                    self.main_bill_data["fact_gst_number"],
                    self.main_bill_data["product"],
                    self.main_bill_data["hsn_sac_code"],
                    self.main_bill_data["year"]
                ))
                self.conn.commit()
                main_bill_id = self.c.lastrowid

            # Clear existing linked entries (in case of update)
            self.c.execute("DELETE FROM main_bill_entries WHERE main_bill_id = ?", (main_bill_id,))
            self.c.execute("UPDATE destination_entry SET main_bill_id = NULL WHERE main_bill_id = ?", (main_bill_id,))

            # Insert updated entries
            for de_id in self.destination_entry_ids:
                self.c.execute("INSERT INTO main_bill_entries (main_bill_id, destination_entry_id) VALUES (?, ?)", (main_bill_id, de_id))
                self.c.execute("UPDATE destination_entry SET main_bill_id=? WHERE id=?", (main_bill_id, de_id))

            self.conn.commit()
            messagebox.showinfo("Saved", f"Main Bill #{self.main_bill_data['bill_number']} saved successfully.")
            self.home_frame.tkraise()

        except Exception as e:
            messagebox.showerror("Error", f"Failed to save main bill:\n{e}")

    def export_pdf(self):
        
        filename = f"main_bill_{self.main_bill_data['bill_number']}.pdf"
        doc = SimpleDocTemplate(filename, pagesize=A4, rightMargin=20, leftMargin=20, topMargin=30, bottomMargin=20)

        styles = getSampleStyleSheet()
        styles.add(ParagraphStyle(name='SmallBold', fontSize=9, fontName='Helvetica-Bold'))
        styles.add(ParagraphStyle(name='Small', fontSize=9, fontName='Helvetica'))
        styles.add(ParagraphStyle(name='Justify', alignment=TA_CENTER))
        elements = []

        # Header paragraph
        header_para = Paragraph(
            "<font size=14><b>M/S. SHAN ENTERPRISES</b></font><br/>"
            "Clearing & Transporting Contractor<br/>"
            "21/4185 C, Meenchandathally, Gate<br/>"
            "P.O. Arts College Calicut – 673018<br/>"
            "Mob: 9447004108",
            styles['Normal']
        )

        # GST aligned to right
        gst_para = Paragraph("<b>GST32ACNFSB060K1ZP</b>", styles['Normal'])

        # Table to align left+center content with GST right
        header_table = Table(
            [[header_para, gst_para]],
            colWidths=[360, 160]  # adjust widths as per A4 width minus margins
        )
        header_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('ALIGN', (0, 0), (0, 0), 'LEFT'),
            ('ALIGN', (1, 0), (1, 0), 'RIGHT'),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ]))

        elements.append(header_table)
        elements.append(Spacer(1, 12))
        # Compact box for Date of Clearing
        date_paragraph = Paragraph(
            f"<b>Date of Clearing:</b><br/>{self.main_bill_data['date_of_clearing']}", styles['Normal']
        )

        # Narrower column, minimal padding
        date_box_table = Table([[date_paragraph]], colWidths=[100], hAlign='LEFT')
        date_box_table.setStyle(TableStyle([
            ('BOX', (0, 0), (-1, -1), 0.5, colors.black),
            ('LEFTPADDING', (0, 0), (-1, -1), 4),
            ('RIGHTPADDING', (0, 0), (-1, -1), 4),
            ('TOPPADDING', (0, 0), (-1, -1), 2),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
        ]))

        # Info rows as a structured table
        # Now replace the cell in info_rows with this table
        info_rows = [
            [f"BILL NO: {self.main_bill_data['bill_number']}", f"Date: {self.main_bill_data['created_date']}"],
            ["TO", ""],
            [self.main_bill_data['to_address'], ""],
            [f"Sir,\n Ref:- {self.main_bill_data['letter_note']}", date_box_table],  # ← this line
            [f"PRODUCT: {self.main_bill_data['product']}", "WESTHILL RH"],
            [f"FACT GST {self.main_bill_data['fact_gst_number']}", ""],
            [f"HSN/SAC CODE: {self.main_bill_data['hsn_sac_code']}", f"YEAR: {self.main_bill_data['year']}"],
        ]
        col_widths = [280, 250]
        elements.append(Table(info_rows, colWidths=col_widths, hAlign='LEFT', style=[
            ('LEFTPADDING', (0, 0), (-1, -1), 30),   # increase as needed
            ('RIGHTPADDING', (0, 0), (-1, -1), 30),
            ('SPAN', (0, 5), (1, 5)),  # Centered GST row
            ('ALIGN', (0, 5), (1, 5), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('ALIGN', (0, 0), (0, -1), 'LEFT'),
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
            ('SPAN', (0, 5), (1, 5)), # Span GST across both columns
            ('ALIGN', (0, 5), (0, 5), 'CENTER'),
        ]))
        
        elements.append(Spacer(1, 10))

        # Table headers
        table_data = [[
            'Sl. No.', 'Destinations', 'Qty', 'Total Qty', 'KM', 'MT x KM', 'Total MT x KM', 'Rate', 'Amount Rs.', 'Total Amount'
        ]]

        # Query and group dealer entries
        placeholders = ",".join("?" for _ in self.destination_entry_ids)
        self.c.execute(f'''
            SELECT rr.from_km, rr.to_km, rr.rate, rr.is_mtk,
                d.name AS dealer_name,
                dsd.place AS destination_place,
                dr.no_bags, dr.mt, dr.km, dr.mt * dr.km AS qty_km, dr.mtk, dr.amount
            FROM dealer_entry dr
            JOIN range_entry re ON dr.range_entry_id = re.id
            JOIN destination_entry de ON re.destination_entry_id = de.id
            JOIN dealer d ON dr.dealer_id = d.id
            JOIN destination dsd ON d.destination_id = dsd.id
            JOIN rate_range rr ON re.rate_range_id = rr.id
            WHERE de.id IN ({placeholders})
            ORDER BY rr.from_km, dsd.place, d.name
        ''', self.destination_entry_ids)
        rows = self.c.fetchall()

        # Group by slab
        grouped = defaultdict(list)
        for row in rows:
            key = (row[0], row[1], row[2], row[3])
            grouped[key].append(row)

        table_styles = []
        sl_no = 1
        row_index = 1
        grand_qty = grand_mt = grand_mtk = grand_amount = 0

        for (from_km, to_km, rate, is_mtk), entries in grouped.items():
            start_row = row_index
            slab_qty = slab_mt = slab_mtk = slab_amount = 0
            slab_label = f"SLAB {int(from_km)}-{int(to_km)}"

            for entry in entries:
                destination = entry[5]
                qty = entry[7]
                mt = entry[7]
                km = entry[8]
                qty_km = entry[9]
                mtk = entry[10]
                amount = entry[11]

                table_data.append([
                    sl_no, destination, f"{qty:.2f}", "", slab_label,
                    f"{qty_km:.2f}", "", f"{rate:.2f}", f"{amount:.2f}", ""
                ])

                slab_qty += qty
                slab_mt += mt
                slab_mtk += mtk
                slab_amount += amount
                row_index += 1

            # Merge total columns
            table_data[start_row][3] = f"{slab_mt:.2f}"
            table_data[start_row][6] = f"{slab_mtk:.2f}"
            table_data[start_row][9] = f"{slab_amount:.2f}"

            # Add row spans
            table_styles.extend([
                ('SPAN', (0, start_row), (0, row_index - 1)),
                ('SPAN', (3, start_row), (3, row_index - 1)),
                ('SPAN', (4, start_row), (4, row_index - 1)),
                ('SPAN', (6, start_row), (6, row_index - 1)),
                ('SPAN', (7, start_row), (7, row_index - 1)),
                ('SPAN', (9, start_row), (9, row_index - 1)),
            ])

            sl_no += 1
            grand_qty += slab_qty
            grand_mt += slab_mt
            grand_mtk += slab_mtk
            grand_amount += slab_amount

        # Grand total row
        table_data.append([
            "", "GRAND TOTAL", "", f"{grand_mt:.2f}", "", "", f"{grand_mtk:.2f}", "", "", f"{grand_amount:.2f}"
        ])

        # Table construction
        tbl = Table(table_data, colWidths=[35, 90, 40, 55, 55, 55, 70, 40, 70, 75])
        tbl.setStyle(TableStyle(table_styles + [
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BACKGROUND', (0, -1), (-1, -1), colors.lightgrey),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('GRID', (0, 0), (-1, -1), 0.25, colors.black),
            ('BOX', (0, 0), (-1, -1), 1, colors.black),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        elements.append(tbl)
        elements.append(Spacer(1, 12))

        # Rupees in words
        grand_amount_str = f"{grand_amount:,.2f}".replace(",", "")
        amount_words = num2words((float(grand_amount_str)), lang='en_IN').replace("euro", "rupees").title() + " Only"
        elements.append(Paragraph(
            f"We are claiming for Rs. {grand_amount:,.2f} ({amount_words}) for Clearing & Transportation Bill of Fertilizer.",
            styles['Small']
        ))
        elements.append(Spacer(1, 12))
        elements.append(Paragraph("Kindly arrange payment to M/S. Shan Enterprises, through IFSC NO.", styles['Small']))
        elements.append(Paragraph("CNRB0014404 - A/C. No.44041400000041 Canara Bank, Panniyankara Branch, Calicut.", styles['Small']))
        elements.append(Spacer(1, 12))
        elements.append(Paragraph("Acknowledge copies of Delivery advice attached with this bill", styles['Small']))
        elements.append(Paragraph("I request you to approve the bill and payment may be made at an early date.", styles['Small']))
        elements.append(Spacer(1, 20))
        
        elements.append(Paragraph("Thanking you", styles['Small']))
        elements.append(Spacer(1, 6))
        # add styles for alignment word right side
        styles.add(ParagraphStyle(name='RightAlign', alignment=TA_RIGHT, fontName='Helvetica'))
        elements.append(Paragraph("Yours faithfully", styles['RightAlign']))
        

        # Build and open PDF
        doc.build(elements)
        try:
            if platform.system() == "Windows":
                os.startfile(filename)
            elif platform.system() == "Darwin":
                os.system(f"open '{filename}'")
            else:
                os.system(f"xdg-open '{filename}'")
        except Exception as e:
            print("Could not open PDF automatically:", e)

        messagebox.showinfo("Exported", f"PDF saved and opened: {filename}")
