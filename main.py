import sqlite3
from tkinter import *
from tkinter import ttk
from ui.dealers import DealerManager
from ui.workorders import WorkOrderRatePage
from ui.destinations import DestinationPage
from ui.destination_entries import DestinationEntryPage

# DB setup
conn = sqlite3.connect("billing_app.db")
c = conn.cursor()

# Tables
c.execute('''CREATE TABLE IF NOT EXISTS dealer (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT UNIQUE,
    name TEXT,
    place TEXT,
    pincode TEXT,
    mobile TEXT,
    distance REAL
)''')

c.execute('''CREATE TABLE IF NOT EXISTS rate_range (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    from_km REAL,
    to_km REAL,
    rate REAL,
    is_mtk BOOLEAN DEFAULT 1
)''')

c.execute('''CREATE TABLE IF NOT EXISTS destination (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    place TEXT,
    description TEXT,
    is_garage BOOLEAN DEFAULT 0
)''')

conn.commit()

# Root Window Fullscreen
root = Tk()
root.title("Billing App")
root.geometry('900x800') # Fullscreen on Windows

# Canvas + Scrollbar
main_canvas = Canvas(root)
main_canvas.pack(side=LEFT, fill=BOTH, expand=True)

v_scrollbar = Scrollbar(root, orient=VERTICAL, command=main_canvas.yview)
v_scrollbar.pack(side=RIGHT, fill=Y)

main_canvas.configure(yscrollcommand=v_scrollbar.set)
main_canvas.bind('<Configure>', lambda e: main_canvas.configure(scrollregion=main_canvas.bbox("all")))

scrollable_frame = Frame(main_canvas)
main_canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")

# Frames
main_frame = Frame(scrollable_frame)
dealer_frame = Frame(scrollable_frame)
workorder_frame = Frame(scrollable_frame)
destination_frame = Frame(scrollable_frame)
destination_entry_frame = Frame(scrollable_frame)

for frame in (main_frame, dealer_frame, workorder_frame, destination_frame, destination_entry_frame):
    frame.grid(row=0, column=0, sticky='nsew')

# Navigation
Label(main_frame, text="Billing Dashboard", font=("Arial", 18)).pack(pady=20)
Button(main_frame, text="Manage Dealers", command=lambda: show_frame(dealer_frame)).pack(pady=5)
Button(main_frame, text="Manage Work Order Rates", command=lambda: show_frame(workorder_frame)).pack(pady=5)
Button(main_frame, text="Manage Destinations", command=lambda: show_frame(destination_frame)).pack(pady=5)
Button(main_frame, text="Destination Entries", command=lambda: show_frame(destination_entry_frame)).pack(pady=5)
Button(main_frame, text="Create Main Bills", command=lambda: print("Coming soon...")).pack(pady=5)

# Load Pages
DealerManager(dealer_frame, main_frame, conn)
WorkOrderRatePage(workorder_frame, main_frame, conn)
DestinationPage(destination_frame, main_frame, conn)
DestinationEntryPage(destination_entry_frame, main_frame, conn)

# Frame switch
def show_frame(frame):
    frame.tkraise()

show_frame(main_frame)
root.mainloop()
