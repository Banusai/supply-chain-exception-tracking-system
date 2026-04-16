from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
import sqlite3
from datetime import datetime, timedelta
from fastapi.responses import FileResponse

app = FastAPI()
templates = Jinja2Templates(directory="templates")

# -------------------------
# DATABASE CONNECTION
# -------------------------
conn = sqlite3.connect("database.db", check_same_thread=False)
cursor = conn.cursor()

# -------------------------
# CREATE TABLES
# -------------------------
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

# ✅ NEW METRICS TABLE
cursor.execute("""
CREATE TABLE IF NOT EXISTS metrics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    total_events INTEGER,
    total_exceptions INTEGER,
    detected_exceptions INTEGER,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
)
""")

conn.commit()

# -------------------------
# HOME PAGE
# -------------------------
@app.get("/", response_class=HTMLResponse)
def home():
    return FileResponse("templates/index.html")

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
# ADD EVENT + EXCEPTION ENGINE + METRICS
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

    exception_detected = False

    # Get last event
    cursor.execute(
        "SELECT status, event_time FROM events WHERE shipment_id=? ORDER BY id DESC LIMIT 1",
        (shipment_id,)
    )
    last = cursor.fetchone()

    last_time = None
    last_status = None

    if last:
        last_status = last[0]
        try:
            last_time = datetime.strptime(last[1], "%Y-%m-%d %H:%M:%S")
        except:
            last_time = datetime.now()

    # -------------------------
    # INVALID STATUS (NEW)
    # -------------------------
    if status not in valid_flow:
        cursor.execute(
            "INSERT INTO exceptions (shipment_id, exception_type, message) VALUES (?, ?, ?)",
            (shipment_id, "INVALID_STATUS", f"Invalid status: {status}")
        )
        exception_detected = True

    # -------------------------
    # SEQUENCE ERROR
    # -------------------------
    if last and status in valid_flow and last_status in valid_flow:
        if valid_flow.index(status) < valid_flow.index(last_status):
            cursor.execute(
                "INSERT INTO exceptions (shipment_id, exception_type, message) VALUES (?, ?, ?)",
                (shipment_id, "SEQUENCE_ERROR", "Invalid status order")
            )
            exception_detected = True

    # -------------------------
    # DUPLICATE EVENT
    # -------------------------
    if last and last_status == status:
        cursor.execute(
            "INSERT INTO exceptions (shipment_id, exception_type, message) VALUES (?, ?, ?)",
            (shipment_id, "DUPLICATE_EVENT", "Duplicate status received")
        )
        exception_detected = True

    # -------------------------
    # DELAY DETECTION
    # -------------------------
    if last_time:
        time_diff = datetime.now() - last_time

        if time_diff < timedelta(hours=1):
            if time_diff > timedelta(seconds=10):
                cursor.execute(
                    "INSERT INTO exceptions (shipment_id, exception_type, message) VALUES (?, ?, ?)",
                    (shipment_id, "DELAY", "Shipment delayed")
                )
                exception_detected = True

    # -------------------------
    # INSERT EVENT
    # -------------------------
    cursor.execute(
        "INSERT INTO events (shipment_id, status, location) VALUES (?, ?, ?)",
        (shipment_id, status, location)
    )

    # -------------------------
    # METRICS TRACKING
    # -------------------------
    cursor.execute("SELECT COUNT(*) FROM events")
    total_events = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM exceptions")
    total_exceptions = cursor.fetchone()[0]

    detected = 1 if exception_detected else 0

    cursor.execute(
        "INSERT INTO metrics (total_events, total_exceptions, detected_exceptions) VALUES (?, ?, ?)",
        (total_events, total_exceptions, detected)
    )

    conn.commit()

    return {"message": "Event processed", "exception_detected": exception_detected}

# -------------------------
# GET EXCEPTIONS
# -------------------------
@app.get("/exceptions")
def get_exceptions():
    cursor.execute("SELECT * FROM exceptions ORDER BY id DESC")
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

# -------------------------
# SYSTEM METRICS API
# -------------------------
@app.get("/metrics")
def get_metrics():
    cursor.execute("""
        SELECT 
            COUNT(*),
            SUM(detected_exceptions)
        FROM metrics
    """)

    data = cursor.fetchone()

    total_requests = data[0] or 0
    detected = data[1] or 0

    cursor.execute("SELECT COUNT(*) FROM exceptions")
    total_exceptions = cursor.fetchone()[0]

    detection_rate = 0
    if total_exceptions > 0:
        detection_rate = (detected / total_exceptions) * 100

    return {
        "total_events": total_requests,
        "total_exceptions": total_exceptions,
        "detected_exceptions": detected,
        "detection_rate": round(detection_rate, 2)
    }
