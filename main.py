import sqlite3
from tkinter import *
from ui.dealers import DealerManager
from ui.workorders import WorkOrderRatePage
from ui.destinations import DestinationPage
from ui.sub_bills import SubBillManagementPage 
from ui.destination_entries import DestinationEntryPage


# Initialize DB
conn = sqlite3.connect("billing_app.db")
c = conn.cursor()

# Create Tables
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

c.execute('''
    CREATE TABLE IF NOT EXISTS destination (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        place TEXT,
        description TEXT,
        is_garage BOOLEAN DEFAULT 0
    )
''')

conn.commit()

# Main Dashboard Window
root = Tk()
root.title("Billing App Dashboard")
root.geometry("2000x1000")

# Frame Containers
main_frame = Frame(root)
dealer_frame = Frame(root)
workorder_frame = Frame(root)
destination_frame = Frame(root)
destination_entry_frame = Frame(root)

for frame in (main_frame, dealer_frame):
    frame.place(x=0, y=0, width=1500, height=1000)

for frame in (main_frame, workorder_frame):
    frame.place(x=0, y=0, width=1500, height=1000)

for frame in (main_frame, destination_frame):
    frame.place(x=0, y=0, width=1500, height=1000)
    
for frame in (main_frame, destination_entry_frame):
    frame.place(x=0, y=0, width=1500, height=1000)


# Dashboard Frame
Label(main_frame, text="Billing Application", font=("Arial", 18)).pack(pady=20)
Button(main_frame, text="Manage Dealers", width=25, command=lambda: show_frame(dealer_frame)).pack(pady=10)
Button(main_frame, text="Manage Work Order Rates", width=25, command=lambda: show_frame(workorder_frame)).pack(pady=10)
Button(main_frame, text="Manage Destinations", width=25, command=lambda: show_frame(destination_frame)).pack(pady=10)
Button(main_frame, text="Destination Entries", width=25, command=lambda: show_frame(destination_entry_frame)).pack(pady=10)
Button(main_frame, text="Create Main Bills", width=25, command=lambda: print("Coming soon...")).pack(pady=10)

# Load Dealer Page UI into Frame
DealerManager(dealer_frame, main_frame, conn)

# Load work order rate Page UI into Frame
WorkOrderRatePage(workorder_frame, main_frame, conn)

# Load Destination Page UI into Frame
DestinationPage(destination_frame, main_frame, conn)

# Load Destination Entry Page UI into Frame
DestinationEntryPage(destination_entry_frame, main_frame, conn)


def show_frame(frame):
    print(f"Switching to frame: {frame}")
    frame.tkraise()

show_frame(main_frame)
root.mainloop()
