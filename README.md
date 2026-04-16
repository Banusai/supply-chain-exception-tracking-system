# supply-chain-exception-tracking-system
Backend system to track shipment lifecycle and detect anomalies like delays, duplicate events, and sequence errors with a dashboard UI.


# 🚚 Supply Chain Exception Tracking System

## 📌 Overview

This project is a backend-driven supply chain monitoring system that tracks shipment lifecycle events and detects anomalies in real time.

It simulates how logistics companies monitor shipments and identify issues such as delays, duplicate updates, and incorrect status sequences.

---

## ⚙️ Features

* 📦 Create and manage shipments
* 🔄 Track shipment lifecycle events
* 🚨 Real-time exception detection:

  * Sequence Errors (invalid status order)
  * Duplicate Events
  * Delay Detection
* 📊 Dashboard UI for:

  * Viewing shipments
  * Filtering exceptions
  * Shipment timeline visualization
  * Progress tracking

---

## 🏗️ System Design

User → FastAPI Backend → Rule Engine → MySQL Database → Dashboard UI

👉 Each shipment event triggers validation logic to detect anomalies and store exceptions.

---

## 🛠️ Tech Stack

* Backend: FastAPI (Python)
* Database: MySQL
* Frontend: HTML, CSS, JavaScript
* Architecture: Layered + Event-driven simulation

---

## ▶️ How to Run

### 1. Clone Repository

```bash
git clone https://github.com/your-username/supply-chain-exception-tracking-system.git
cd supply-chain-exception-tracking-system
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Setup Database

* Open MySQL
* Run `database/schema.sql`

### 4. Start Server

```bash
python -m uvicorn main:app --reload
```

---

## 🧪 Demo Flow

1. Create a shipment

2. Add events (PICKED_UP, IN_TRANSIT, etc.)

3. Trigger exceptions:

   * ❌ Wrong order → SEQUENCE_ERROR
   * ❌ Duplicate update → DUPLICATE_EVENT
   * ⏱ Delay → DELAY

4. View:

   * Exception alerts
   * Shipment timeline
   * Progress tracking

---

## 💡 Future Improvements

* Event streaming using Kafka
* Real-time updates using WebSockets
* Authentication & role-based access
* Advanced analytics dashboard

---

## 👨‍💻 Author

Banu Prasad
