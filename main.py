import sqlite3
from tkinter import *
from tkinter import ttk
from ui.dealers import DealerManager
from ui.workorders import WorkOrderRatePage
from ui.destinations import DestinationPage
from ui.destination_entries import DestinationEntryPage
from ui.destinationentryview import DestinationEntryViewer

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
    destination_id INTEGER,
    FOREIGN KEY (destination_id) REFERENCES destination(id)
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

# Root Window
root = Tk()
root.title("Billing App")
root.geometry('1600x1000')  # Initial size

# Canvas + Scrollbar
main_canvas = Canvas(root)
main_canvas.pack(side=LEFT, fill=BOTH, expand=True)

v_scrollbar = Scrollbar(root, orient=VERTICAL, command=main_canvas.yview)
v_scrollbar.pack(side=RIGHT, fill=Y)

main_canvas.configure(yscrollcommand=v_scrollbar.set)
main_canvas.bind('<Configure>', lambda e: main_canvas.configure(scrollregion=main_canvas.bbox("all")))

scrollable_frame = Frame(main_canvas)
scrollable_frame.bind(
    "<Configure>",
    lambda e: main_canvas.configure(scrollregion=main_canvas.bbox("all"))
)
main_canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
def resize_canvas(event):
    canvas_width = event.width
    main_canvas.itemconfig("frame_window", width=canvas_width)

frame_window = main_canvas.create_window((0, 0), window=scrollable_frame, anchor="nw", tags="frame_window")
main_canvas.bind("<Configure>", resize_canvas)

# Frames
main_frame = Frame(scrollable_frame)
dealer_frame = Frame(scrollable_frame)
workorder_frame = Frame(scrollable_frame)
destination_frame = Frame(scrollable_frame)
destination_entry_frame = Frame(scrollable_frame)
destination_entry_viewer_frame = Frame(scrollable_frame)
edit_entry_frame = Frame(scrollable_frame)

for frame in (main_frame, dealer_frame, workorder_frame, destination_frame, destination_entry_frame, destination_entry_viewer_frame, edit_entry_frame):
    frame.grid(row=0, column=0, sticky='nsew')

# Configure main_frame to center its contents
main_frame.grid_rowconfigure(0, weight=1)  # Add weight to center vertically
main_frame.grid_rowconfigure(7, weight=1)  # Extra row for spacing
main_frame.grid_columnconfigure(0, weight=1)  # Add weight to center horizontally
main_frame.grid_columnconfigure(2, weight=1)  # Extra column for spacing

# Navigation (Centered in main_frame using grid)
Label(main_frame, text="Billing Dashboard", font=("Arial", 18)).grid(row=1, column=1, pady=20, sticky="ew")
Button(main_frame, text="Manage Dealers", command=lambda: show_frame(dealer_frame)).grid(row=2, column=1, pady=5, sticky="ew")
Button(main_frame, text="Manage Work Order Rates", command=lambda: show_frame(workorder_frame)).grid(row=3, column=1, pady=5, sticky="ew")
Button(main_frame, text="Manage Destinations", command=lambda: show_frame(destination_frame)).grid(row=4, column=1, pady=5, sticky="ew")
Button(main_frame, text="Destination Entries", command=lambda: show_frame(destination_entry_frame)).grid(row=5, column=1, pady=5, sticky="ew")
Button(main_frame, text="View Destination Entries", command=lambda: show_frame(destination_entry_viewer_frame)).grid(row=6, column=1, pady=5, sticky="ew")
Button(main_frame, text="Create Main Bills", command=lambda: print("Coming soon...")).grid(row=7, column=1, pady=5, sticky="ew")

# Load Pages
DealerManager(dealer_frame, main_frame, conn)
WorkOrderRatePage(workorder_frame, main_frame, conn)
DestinationPage(destination_frame, main_frame, conn)
DestinationEntryPage(destination_entry_frame, main_frame, conn)
edit_entry_page = DestinationEntryPage(edit_entry_frame, main_frame, conn)
DestinationEntryViewer(destination_entry_viewer_frame, main_frame, conn, edit_entry_page)

# Frame switch
def show_frame(frame):
    frame.tkraise()
    root.update_idletasks()  # Ensures all widgets are updated
    main_canvas.configure(scrollregion=main_canvas.bbox("all"))  # Update scroll region

show_frame(main_frame)
root.mainloop()