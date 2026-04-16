from fastapi import FastAPI
import mysql.connector
from datetime import datetime, timedelta
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi import Request

app = FastAPI()
templates = Jinja2Templates(directory="templates")



conn = mysql.connector.connect(
    host="localhost",
    user="root",
    password="Banusai@9010127799",
    database="supply_chain"
)
@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    return templates.TemplateResponse(
        request,
        "index.html",
        {}
    )
# -------------------------
# CREATE SHIPMENT
# -------------------------
@app.get("/shipments")
def get_shipments():

    cursor = conn.cursor()

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

    data = cursor.fetchall()

    return {"shipments": data}
# -------------------------
# ADD EVENT + EXCEPTION ENGINE
# -------------------------
@app.post("/event")
def add_event(shipment_id: int, status: str, location: str):

    cursor = conn.cursor()

    valid_flow = [
        "CREATED",
        "PICKED_UP",
        "IN_TRANSIT",
        "OUT_FOR_DELIVERY",
        "DELIVERED"
    ]

    # get last event
    cursor.execute(
        "SELECT status, event_time FROM events WHERE shipment_id=%s ORDER BY id DESC LIMIT 1",
        (shipment_id,)
    )

    last = cursor.fetchone()

    # -------------------------
    # SEQUENCE ERROR
    # -------------------------
    if last:
        last_status = last[0]

        if valid_flow.index(status) < valid_flow.index(last_status):
            cursor.execute(
                "INSERT INTO exceptions (shipment_id, exception_type, message) VALUES (%s,%s,%s)",
                (shipment_id, "SEQUENCE_ERROR", "Invalid status order")
            )

    # -------------------------
    # DUPLICATE EVENT
    # -------------------------
    if last and last[0] == status:
        cursor.execute(
            "INSERT INTO exceptions (shipment_id, exception_type, message) VALUES (%s,%s,%s)",
            (shipment_id, "DUPLICATE_EVENT", "Duplicate status received")
        )

    # -------------------------
    # DELAY DETECTION (2 minutes demo)
    # -------------------------
    if last:
        last_time = last[1]

        if datetime.now() - last_time > timedelta(minutes=2):
            cursor.execute(
                "INSERT INTO exceptions (shipment_id, exception_type, message) VALUES (%s,%s,%s)",
                (shipment_id, "DELAY", "Shipment delayed")
            )

    # insert event
    cursor.execute(
        "INSERT INTO events (shipment_id, status, location) VALUES (%s,%s,%s)",
        (shipment_id, status, location)
    )

    conn.commit()

    return {"message": "Event processed"}


# -------------------------
# GET EXCEPTIONS
# -------------------------
@app.get("/exceptions")
def get_exceptions():

    cursor = conn.cursor()

    cursor.execute("SELECT * FROM exceptions")

    data = cursor.fetchall()

    return {"exceptions": data}


# -------------------------
# GET SHIPMENT EVENTS
# -------------------------
@app.get("/shipment/{shipment_id}")
def get_shipment(shipment_id: int):

    cursor = conn.cursor()

    cursor.execute(
        "SELECT status, location, event_time FROM events WHERE shipment_id=%s",
        (shipment_id,)
    )

    data = cursor.fetchall()

    return {"timeline": data}