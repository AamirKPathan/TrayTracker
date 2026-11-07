# TrayTrack: Smart Food Waste & Prep Prediction System

**TrayTrack** is an automated dining hall portion-tracking system designed to reduce university food waste. By integrating a tray-weighing gate station with real-time logging and predictive kitchen analytics, TrayTrack enables dining hall management to forecast meal prep requirements based on historical consumption patterns and planned menu items.

---

## 📌 Project Overview & Features

- **Automated Weigh & Scan Gate:** Captures student IDs and tray weights at serving area exits.
- **Multi-Visit Aggregation:** Automatically groups multiple trips by the same student within a single meal window (Breakfast, Lunch, Dinner) to measure total meal intake rather than per-tray averages.
- **Advance Menu Input:** Allows kitchen staff to input daily menu items ahead of time (e.g., *"Taco Tuesday"* vs. *"Baked Ziti"*).
- **Predictive Demand Engine:** Calculates recommended kitchen prep quantities by matching upcoming menus against historical consumption data.
- **Excel Report Export:** Generates clean, downloadable daily logs and aggregate student usage reports.
- **Virtual Kiosk Mode:** Built-in web testing interface allowing software developers to simulate hardware scans without physical hardware connected.

---

## 🏗 System Architecture

```
                               ┌─────────────────────────┐
                               │  Kitchen Staff Input    │
                               │  (Schedule Menus)       │
                               └───────────┬─────────────┘
                                           │
                                           ▼
┌────────────────────────┐      ┌────────────────────────┐      ┌────────────────────────┐
│  Hardware Gate Station │      │  Flask Backend Server  │      │  Kitchen Dashboard     │
│  - Digital Scale       ├─────►│  - SQLite Database     ├─────►│  - Live Scan Feeds     │
│  - RFID Scanner        │ JSON │  - Prediction Logic    │      │  - Prep Forecasting    │
│  - Gate Solenoid/Relay │ POST │  - CSV/Excel Exporter  │      │  - Data Exports        │
└────────────────────────┘      └────────────────────────┘      └────────────────────────┘
```

---

## 🚀 Getting Started (Software Team Setup)

### Prerequisites
- Python 3.9 or higher
- `pip` (Python package installer)

### Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/your-username/traytrack.git
   cd traytrack
   ```

2. **Install required dependencies:**
   ```bash
   pip install flask pandas openpyxl
   ```

3. **Run the Flask application:**
   ```bash
   python app.py
   ```
   The application will automatically initialize the SQLite database (`food_waste_tracker.db`) on first startup.

4. **Access the application in your browser:**
   - **Kitchen Dashboard:** `http://localhost:5000/`
   - **Staff Menu Entry:** `http://localhost:5000/staff`
   - **Virtual Gate Kiosk (Software Testing):** `http://localhost:5000/kiosk`

---

## 🔌 Hardware-to-Software API Contract

The hardware controller (Raspberry Pi / Microcontroller) communicates with the backend via a lightweight REST endpoint.

### **Endpoint:** `POST /api/scan`

- **Headers:** `Content-Type: application/json`
- **Request Body:**
  ```json
  {
    "student_id": "S12345678",
    "weight_kg": 0.85
  }
  ```

- **Success Response (200 OK):**
  ```json
  {
    "status": "success",
    "message": "Logged 0.85kg for student S12345678 eating Spaghetti Bolognese"
  }
  ```

- **Error Response (400 Bad Request):**
  ```json
  {
    "status": "error",
    "message": "Missing student_id or weight_kg"
  }
  ```

---

## 📊 Database Schema Summary

The project utilizes two main SQLite tables:

### 1. `menu_schedule`
Stores planned menus set in advance by staff.
- `id` (INTEGER PRIMARY KEY)
- `date` (TEXT, YYYY-MM-DD)
- `meal_slot` (TEXT: Breakfast / Lunch / Dinner)
- `menu_item` (TEXT)

### 2. `tray_logs`
Stores individual tray weigh-ins recorded at the gate.
- `id` (INTEGER PRIMARY KEY)
- `timestamp` (DATETIME DEFAULT CURRENT_TIMESTAMP)
- `date` (TEXT)
- `student_id` (TEXT)
- `meal_slot` (TEXT)
- `menu_item` (TEXT)
- `weight_kg` (REAL)

---

## 🛠 Project Roadmap

- [x] Flask backend & SQLite database architecture
- [x] Staff menu entry web form
- [x] Hardware JSON API endpoint (`/api/scan`)
- [x] Virtual Kiosk simulator for software testing
- [x] Hardware load cell calibration & USB scale integration
- [x] RFID reader integration and solenoid relay gate lock
- [ ] Advanced machine learning forecasting model (incorporating weather & day-of-week weights)