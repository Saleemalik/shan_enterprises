import sqlite3
from tkinter import *
from tkinter import ttk
from ui.dealers import DealerManager
from ui.workorders import WorkOrderRatePage
from ui.destinations import DestinationPage
from ui.destination_entries import DestinationEntryPage
from ui.destinationentryview import DestinationEntryViewer
from ui.mainbillentry import MainBillPage

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
    distance REAL,
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
root.geometry("1600x900")
root.resizable(True, True)

# Canvas + Scrollbar
main_canvas = Canvas(root, highlightthickness=0)
main_canvas.pack(side=LEFT, fill=BOTH, expand=True)

v_scrollbar = Scrollbar(root, orient=VERTICAL, command=main_canvas.yview)
v_scrollbar.pack(side=RIGHT, fill=Y)

main_canvas.configure(yscrollcommand=v_scrollbar.set)

# Scrollable Frame
scrollable_frame = Frame(main_canvas)
frame_window = main_canvas.create_window((0, 0), window=scrollable_frame, anchor="nw", tags="frame_window")

# Update scroll region and canvas window size
def update_canvas(event=None):
    main_canvas.itemconfig("frame_window", width=main_canvas.winfo_width())
    main_canvas.configure(scrollregion=main_canvas.bbox("all"))
    # Ensure the scrollable_frame height matches content or canvas
    content_height = scrollable_frame.winfo_reqheight()
    canvas_height = main_canvas.winfo_height()
    if content_height < canvas_height:
        main_canvas.itemconfig("frame_window", height=canvas_height)
    else:
        main_canvas.itemconfig("frame_window", height=content_height)

main_canvas.bind('<Configure>', update_canvas)
scrollable_frame.bind('<Configure>', update_canvas)

# Mouse wheel scrolling
def _on_mousewheel(event):
    main_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

scrollable_frame.bind_all("<MouseWheel>", _on_mousewheel)  # Windows and Mac
scrollable_frame.bind_all("<Button-4>", lambda e: main_canvas.yview_scroll(-1, "units"))  # Linux
scrollable_frame.bind_all("<Button-5>", lambda e: main_canvas.yview_scroll(1, "units"))  # Linux

# Frames
main_frame = Frame(scrollable_frame)
dealer_frame = Frame(scrollable_frame)
workorder_frame = Frame(scrollable_frame)
destination_frame = Frame(scrollable_frame)
destination_entry_frame = Frame(scrollable_frame)
destination_entry_viewer_frame = Frame(scrollable_frame)
edit_entry_frame = Frame(scrollable_frame)
main_bill_frame = Frame(scrollable_frame)

# Configure frames to expand
for frame in (main_frame, dealer_frame, workorder_frame, destination_frame, destination_entry_frame, destination_entry_viewer_frame, edit_entry_frame, main_bill_frame):
    frame.grid(row=0, column=0, sticky='nsew')
    frame.grid_rowconfigure(0, weight=1)
    frame.grid_columnconfigure(0, weight=1)

scrollable_frame.grid_rowconfigure(0, weight=1)
scrollable_frame.grid_columnconfigure(0, weight=1)

# Configure main_frame for vertical centering
main_frame.grid_rowconfigure(0, weight=1)  # Spacer above
main_frame.grid_rowconfigure(8, weight=1)  # Spacer below
main_frame.grid_columnconfigure(0, weight=1)  # Spacer left
main_frame.grid_columnconfigure(1, weight=0)  # Content area
main_frame.grid_columnconfigure(2, weight=1)  # Spacer right

# Navigation (Centered in main_frame)
dashboard_label = Label(main_frame, text="Billing Dashboard", font=("Arial", 18))
dashboard_label.grid(row=1, column=1, pady=20, sticky="ew")

# Navigation Buttons
Button(main_frame, text="Manage Dealers", command=lambda: show_frame(dealer_frame)).grid(row=2, column=1, pady=5, sticky="ew")
Button(main_frame, text="Manage Work Order Rates", command=lambda: show_frame(workorder_frame)).grid(row=3, column=1, pady=5, sticky="ew")
Button(main_frame, text="Manage Destinations", command=lambda: show_frame(destination_frame)).grid(row=4, column=1, pady=5, sticky="ew")
Button(main_frame, text="Destination Entries", command=lambda: show_frame(destination_entry_frame)).grid(row=5, column=1, pady=5, sticky="ew")
Button(main_frame, text="View Destination Entries", command=lambda: show_frame(destination_entry_viewer_frame)).grid(row=6, column=1, pady=5, sticky="ew")
Button(main_frame, text="Create Main Bills", command=lambda: show_frame(main_bill_frame)).grid(row=7, column=1, pady=5, sticky="ew")

# Load Pages (commented out since custom modules are unavailable)
DealerManager(dealer_frame, main_frame, conn)
WorkOrderRatePage(workorder_frame, main_frame, conn)
DestinationPage(destination_frame, main_frame, conn)
DestinationEntryPage(destination_entry_frame, main_frame, conn)
edit_entry_page = DestinationEntryPage(edit_entry_frame, main_frame, conn)
DestinationEntryViewer(destination_entry_viewer_frame, main_frame, conn, edit_entry_page)
MainBillPage(main_bill_frame, main_frame, conn)

# Frame switch
def show_frame(frame):
    frame.tkraise()
    root.update_idletasks()
    update_canvas()

show_frame(main_frame)
root.mainloop()