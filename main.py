import sqlite3
from tkinter import *
from ui.dealers import DealerManager
from ui.workorders import WorkOrderRatePage

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

conn.commit()

# Main Dashboard Window
root = Tk()
root.title("Billing App Dashboard")
root.geometry("800x500")

# Frame Containers
main_frame = Frame(root)
dealer_frame = Frame(root)
workorder_frame = Frame(root)

for frame in (main_frame, dealer_frame):
    frame.place(x=0, y=0, width=800, height=500)

for frame in (main_frame, workorder_frame):
    frame.place(x=0, y=0, width=800, height=500)

# Dashboard Frame
Label(main_frame, text="Billing Application", font=("Arial", 18)).pack(pady=20)
Button(main_frame, text="Manage Dealers", width=25, command=lambda: show_frame(dealer_frame)).pack(pady=10)
Button(main_frame, text="Manage Work Order Rates", width=25, command=lambda: show_frame(workorder_frame)).pack(pady=10)
Button(main_frame, text="Create Sub Bills", width=25, command=lambda: print("Coming soon...")).pack(pady=10)
Button(main_frame, text="Create Main Bills", width=25, command=lambda: print("Coming soon...")).pack(pady=10)

# Load Dealer Page UI into Frame
DealerManager(dealer_frame, main_frame, conn)

# Load work order rate Page UI into Frame
WorkOrderRatePage(workorder_frame, main_frame, conn)



def show_frame(frame):
    print(f"Switching to frame: {frame}")
    frame.tkraise()

show_frame(main_frame)
root.mainloop()
