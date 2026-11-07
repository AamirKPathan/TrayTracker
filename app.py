import os
import sqlite3
from datetime import datetime
from flask import Flask, render_template_string, request, redirect, url_for, send_file
import pandas as pd

app = Flask(__name__)
DB_NAME = "food_waste_tracker.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # Table for tray scans at the gate
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tray_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            date TEXT,
            student_id TEXT,
            meal_slot TEXT,
            menu_item TEXT,
            weight_kg REAL
        )
    ''')
    
    # Table for staff to schedule menus in advance
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS menu_schedule (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT UNIQUE,
            meal_slot TEXT,
            menu_item TEXT
        )
    ''')
    conn.commit()
    conn.close()

# ==================== HTML TEMPLATES ====================

HOME_TEMPLATE = '''
<!doctype html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <title>TrayTrack Kitchen Dashboard</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 40px; background: #f4f4f9; color: #333; }
        h1 { color: #2c3e50; }
        .card { background: white; padding: 20px; margin-bottom: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        .nav-buttons a { display: inline-block; padding: 10px 15px; background: #3498db; color: white; text-decoration: none; border-radius: 4px; margin-right: 10px; }
        .nav-buttons a:hover { background: #2980b9; }
        .kiosk-btn { background: #e67e22 !important; }
        .kiosk-btn:hover { background: #d35400 !important; }
        table { width: 100%; border-collapse: collapse; margin-top: 10px; }
        th, td { padding: 10px; border: 1px solid #ddd; text-align: left; }
        th { background: #ecf0f1; }
        .highlight { font-size: 24px; color: #e74c3c; font-weight: bold; }
    </style>
</head>
<body>
    <h1>TrayTrack Kitchen Dashboard</h1>
    
    <div class="card nav-buttons">
        <a href="/staff">Staff Menu Input</a>
        <a href="/kiosk" class="kiosk-btn">Open Virtual Gate Kiosk</a>
        <a href="/export">Export Daily Excel Report</a>
    </div>

    <div class="card">
        <h2>Today's Menu & Prep Prediction</h2>
        <p><strong>Date:</strong> {{ today }} | <strong>Active Meal Slot:</strong> {{ current_meal }}</p>
        <p><strong>Today's Menu:</strong> {{ current_menu }}</p>
        <p>Recommended Prep Amount:</p>
        <div class="highlight">{{ prediction }}</div>
        <p style="font-size: 12px; color: #7f8c8d;">*Calculated from historical consumption averages for this menu item.</p>
    </div>

    <div class="card">
        <h2>Recent Tray Scans</h2>
        <table>
            <tr><th>Timestamp</th><th>Student ID</th><th>Meal</th><th>Menu Item</th><th>Total Weight (kg)</th></tr>
            {% for row in recent_logs %}
            <tr>
                <td>{{ row[1] }}</td>
                <td>{{ row[3] }}</td>
                <td>{{ row[4] }}</td>
                <td>{{ row[5] }}</td>
                <td>{{ row[6] }}</td>
            </tr>
            {% endfor %}
        </table>
    </div>
</body>
</html>
'''

STAFF_TEMPLATE = '''
<!doctype html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <title>Staff Menu Entry</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 40px; background: #f4f4f9; color: #333; }
        .card { background: white; padding: 25px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); max-width: 500px; }
        input, select { width: 100%; padding: 10px; margin: 10px 0; box-sizing: border-box; }
        button { background: #2ecc71; color: white; border: none; padding: 10px 15px; border-radius: 4px; cursor: pointer; font-size: 16px; }
        button:hover { background: #27ae60; }
        a { color: #3498db; text-decoration: none; }
    </style>
</head>
<body>
    <div class="card">
        <h2>Enter Upcoming Menu</h2>
        <form method="POST">
            <label>Date (YYYY-MM-DD):</label>
            <input type="date" name="date" required value="{{ today }}">
            
            <label>Meal Slot:</label>
            <select name="meal_slot">
                <option value="Breakfast">Breakfast</option>
                <option value="Lunch" selected>Lunch</option>
                <option value="Dinner">Dinner</option>
            </select>
            
            <label>Menu Item Name:</label>
            <input type="text" name="menu_item" placeholder="e.g. Chicken Alfredo" required>
            
            <button type="submit">Save Menu</button>
        </form>
        <br>
        <p><a href="/">Back to Dashboard</a></p>
    </div>
</body>
</html>
'''

KIOSK_TEMPLATE = '''
<!doctype html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <title>Virtual Gate Kiosk</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 40px; background: #f4f4f9; color: #333; }
        .card { background: white; padding: 25px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); max-width: 450px; }
        input, button { width: 100%; padding: 12px; margin: 10px 0; box-sizing: border-box; font-size: 16px; }
        button { background: #e67e22; color: white; border: none; border-radius: 4px; cursor: pointer; }
        button:hover { background: #d35400; }
        .success { background: #d4edda; color: #155724; padding: 10px; border-radius: 4px; margin-bottom: 15px; }
        a { color: #3498db; text-decoration: none; }
    </style>
</head>
<body>
    <div class="card">
        <h2>Virtual Gate Kiosk</h2>
        <p>Scan ID card or type ID. Multiple scans accumulate weight for the meal.</p>
        
        {% if message %}
            <div class="success">{{ message }}</div>
        {% endif %}

        <form method="POST" id="scanForm">
            <label>Student ID:</label>
            <input type="text" id="student_id" name="student_id" placeholder="Scan ID or type..." required autofocus>
            
            <label>Tray Weight (kg):</label>
            <input type="number" step="0.01" name="weight_kg" value="0.75" required>
            
            <button type="submit">Scan & Unlock Gate</button>
        </form>
        <br>
        <p><a href="/">Back to Kitchen Dashboard</a></p>
    </div>
    
    <script>
        // Keep focus locked on student ID input for continuous scanner usage
        window.onload = function() {
            document.getElementById("student_id").focus();
        };
    </script>
</body>
</html>
'''

# ==================== HELPER FUNCTIONS ====================

def get_current_meal_slot():
    hour = datetime.now().hour
    if 7 <= hour < 11:
        return "Breakfast"
    elif 11 <= hour < 15:
        return "Lunch"
    elif 17 <= hour < 21:
        return "Dinner"
    else:
        return "Lunch"

# ==================== FLASK ROUTES ====================

@app.route("/")
def index():
    today = datetime.now().strftime("%Y-%m-%d")
    current_meal = get_current_meal_slot()
    
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    cursor.execute("SELECT menu_item FROM menu_schedule WHERE date = ? AND meal_slot = ?", (today, current_meal))
    menu_row = cursor.fetchone()
    current_menu = menu_row[0] if menu_row else "Not Set Yet"
    
    prediction = "N/A (Need More History)"
    if current_menu != "Not Set Yet":
        cursor.execute("""
            SELECT date, SUM(weight_kg) 
            FROM tray_logs 
            WHERE meal_slot = ? AND menu_item = ? 
            GROUP BY date
        """, (current_meal, current_menu))
        history_sums = [row[1] for row in cursor.fetchall()]
        
        if history_sums:
            avg_total = sum(history_sums) / len(history_sums)
            prediction = f"{round(avg_total, 2)} kg"
            
    cursor.execute("SELECT * FROM tray_logs ORDER BY id DESC LIMIT 10")
    recent_logs = cursor.fetchall()
    conn.close()
    
    return render_template_string(HOME_TEMPLATE, today=today, current_meal=current_meal, current_menu=current_menu, prediction=prediction, recent_logs=recent_logs)

@app.route("/staff", methods=["GET", "POST"])
def staff():
    today = datetime.now().strftime("%Y-%m-%d")
    if request.method == "POST":
        date = request.form["date"]
        meal_slot = request.form["meal_slot"]
        menu_item = request.form["menu_item"]
        
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO menu_schedule (date, meal_slot, menu_item) 
            VALUES (?, ?, ?)
            ON CONFLICT(date) DO UPDATE SET menu_item=excluded.menu_item, meal_slot=excluded.meal_slot
        ''', (date, meal_slot, menu_item))
        conn.commit()
        conn.close()
        return redirect(url_for('index'))
        
    return render_template_string(STAFF_TEMPLATE, today=today)

@app.route("/kiosk", methods=["GET", "POST"])
def kiosk():
    message = None
    today = datetime.now().strftime("%Y-%m-%d")
    current_meal = get_current_meal_slot()
    
    if request.method == "POST":
        student_id = request.form["student_id"].strip()
        weight_kg = float(request.form["weight_kg"])
        
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        # Get active menu item for today/meal
        cursor.execute("SELECT menu_item FROM menu_schedule WHERE date = ? AND meal_slot = ?", (today, current_meal))
        row = cursor.fetchone()
        menu_item = row[0] if row else "Unknown Menu"
        
        # Check if student already has a log for this date and meal slot
        cursor.execute('''
            SELECT id, weight_kg FROM tray_logs 
            WHERE date = ? AND student_id = ? AND meal_slot = ?
        ''', (today, student_id, current_meal))
        existing_log = cursor.fetchone()
        
        if existing_log:
            # Accumulate weight on existing row
            log_id, current_weight = existing_log
            updated_weight = round(current_weight + weight_kg, 2)
            cursor.execute('''
                UPDATE tray_logs 
                SET weight_kg = ?, timestamp = CURRENT_TIMESTAMP 
                WHERE id = ?
            ''', (updated_weight, log_id))
            message = f"Updated Student {student_id}: Added {weight_kg}kg (New Total: {updated_weight}kg). Gate Unlocked!"
        else:
            # Create new row if first scan for this meal
            cursor.execute('''
                INSERT INTO tray_logs (date, student_id, meal_slot, menu_item, weight_kg)
                VALUES (?, ?, ?, ?, ?)
            ''', (today, student_id, current_meal, menu_item, weight_kg))
            message = f"Success! Logged {weight_kg}kg for Student {student_id} ({menu_item}). Gate Unlocked!"
            
        conn.commit()
        conn.close()
        
    return render_template_string(KIOSK_TEMPLATE, message=message)

@app.route("/api/scan", methods=["POST"])
def api_scan():
    """API endpoint for future hardware integration with weight accumulation"""
    data = request.json
    student_id = data.get("student_id")
    weight_kg = data.get("weight_kg")
    
    if not student_id or weight_kg is None:
        return {"status": "error", "message": "Missing student_id or weight_kg"}, 400
        
    today = datetime.now().strftime("%Y-%m-%d")
    meal_slot = get_current_meal_slot()
    
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    cursor.execute("SELECT menu_item FROM menu_schedule WHERE date = ? AND meal_slot = ?", (today, meal_slot))
    row = cursor.fetchone()
    menu_item = row[0] if row else "Unknown Menu"
    
    cursor.execute('''
        SELECT id, weight_kg FROM tray_logs 
        WHERE date = ? AND student_id = ? AND meal_slot = ?
    ''', (today, student_id, meal_slot))
    existing_log = cursor.fetchone()
    
    if existing_log:
        log_id, current_weight = existing_log
        updated_weight = round(current_weight + float(weight_kg), 2)
        cursor.execute('UPDATE tray_logs SET weight_kg = ? WHERE id = ?', (updated_weight, log_id))
    else:
        cursor.execute('''
            INSERT INTO tray_logs (date, student_id, meal_slot, menu_item, weight_kg)
            VALUES (?, ?, ?, ?, ?)
        ''', (today, student_id, meal_slot, menu_item, float(weight_kg)))
        
    conn.commit()
    conn.close()
    
    return {"status": "success", "message": f"Processed scan for student {student_id}"}

@app.route("/export")
def export():
    today = datetime.now().strftime("%Y-%m-%d")
    conn = sqlite3.connect(DB_NAME)
    df_raw = pd.read_sql_query("SELECT * FROM tray_logs", conn)
    conn.close()
    
    filename = f"Food_Waste_Report_{today}.xlsx"
    with pd.ExcelWriter(filename) as writer:
        df_raw.to_excel(writer, sheet_name="Consumption_Logs", index=False)
        
    return send_file(filename, as_attachment=True)

if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=5000, debug=True)