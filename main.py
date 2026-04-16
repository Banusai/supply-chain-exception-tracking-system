from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
import sqlite3
from datetime import datetime, timedelta

app = FastAPI()
templates = Jinja2Templates(directory="templates")

# -------------------------
# DATABASE (SQLite)
# -------------------------
conn = sqlite3.connect("database.db", check_same_thread=False)
cursor = conn.cursor()

# Create tables
cursor.execute("""
CREATE TABLE IF NOT EXISTS shipments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tracking_id TEXT,
    status TEXT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    shipment_id INTEGER,
    status TEXT,
    location TEXT,
    event_time TEXT DEFAULT CURRENT_TIMESTAMP
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS exceptions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    shipment_id INTEGER,
    exception_type TEXT,
    message TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
)
""")

conn.commit()

# -------------------------
# HOME PAGE
# -------------------------
@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    return templates.TemplateResponse(
        request,
        "index.html",
        {"request": request}
    )

# -------------------------
# GET SHIPMENTS
# -------------------------
@app.get("/shipments")
def get_shipments():
    cursor.execute("""
        SELECT 
            s.id,
            s.tracking_id,
            COALESCE(
                (SELECT status 
                 FROM events e 
                 WHERE e.shipment_id = s.id 
                 ORDER BY e.id DESC 
                 LIMIT 1),
                s.status
            ) as status
        FROM shipments s
        ORDER BY s.id DESC
    """)
    return {"shipments": cursor.fetchall()}

# -------------------------
# CREATE SHIPMENT
# -------------------------
@app.post("/shipment")
def create_shipment(tracking_id: str):
    cursor.execute(
        "INSERT INTO shipments (tracking_id, status) VALUES (?, ?)",
        (tracking_id, "CREATED")
    )
    conn.commit()
    return {"message": "Shipment created"}

# -------------------------
# ADD EVENT + EXCEPTION ENGINE
# -------------------------
@app.post("/event")
def add_event(shipment_id: int, status: str, location: str):

    valid_flow = [
        "CREATED",
        "PICKED_UP",
        "IN_TRANSIT",
        "OUT_FOR_DELIVERY",
        "DELIVERED"
    ]

    # Get last event
    cursor.execute(
        "SELECT status, event_time FROM events WHERE shipment_id=? ORDER BY id DESC LIMIT 1",
        (shipment_id,)
    )
    last = cursor.fetchone()

    # -------------------------
    # SAFE TIME PARSING
    # -------------------------
    last_time = None
    if last:
        try:
            last_time = datetime.strptime(last[1], "%Y-%m-%d %H:%M:%S")
        except:
            last_time = datetime.now()

    # -------------------------
    # SEQUENCE ERROR
    # -------------------------
    if last:
        last_status = last[0]
        if valid_flow.index(status) < valid_flow.index(last_status):
            cursor.execute(
                "INSERT INTO exceptions (shipment_id, exception_type, message) VALUES (?, ?, ?)",
                (shipment_id, "SEQUENCE_ERROR", "Invalid status order")
            )

    # -------------------------
    # DUPLICATE EVENT
    # -------------------------
    if last and last[0] == status:
        cursor.execute(
            "INSERT INTO exceptions (shipment_id, exception_type, message) VALUES (?, ?, ?)",
            (shipment_id, "DUPLICATE_EVENT", "Duplicate status received")
        )

    # -------------------------
    # DELAY DETECTION (FIXED)
    # -------------------------
    if last_time:
        time_diff = datetime.now() - last_time

        # Ignore very old data (more than 1 hour)
        if time_diff < timedelta(hours=1):

            # Demo delay threshold (10 sec)
            if time_diff > timedelta(seconds=10):
                cursor.execute(
                    "INSERT INTO exceptions (shipment_id, exception_type, message) VALUES (?, ?, ?)",
                    (shipment_id, "DELAY", "Shipment delayed")
                )

    # Insert event
    cursor.execute(
        "INSERT INTO events (shipment_id, status, location) VALUES (?, ?, ?)",
        (shipment_id, status, location)
    )

    conn.commit()

    return {"message": "Event processed"}

# -------------------------
# GET EXCEPTIONS
# -------------------------
@app.get("/exceptions")
def get_exceptions():
    cursor.execute("SELECT * FROM exceptions")
    return {"exceptions": cursor.fetchall()}

# -------------------------
# GET SHIPMENT TIMELINE
# -------------------------
@app.get("/shipment/{shipment_id}")
def get_shipment(shipment_id: int):
    cursor.execute(
        "SELECT status, location, event_time FROM events WHERE shipment_id=?",
        (shipment_id,)
    )
    return {"timeline": cursor.fetchall()}
