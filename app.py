import os
import sqlite3
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, send_file
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
    
    return render_template("index.html", today=today, current_meal=current_meal, current_menu=current_menu, prediction=prediction, recent_logs=recent_logs)

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
        
    return render_template("staff.html", today=today)

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
        
        cursor.execute("SELECT menu_item FROM menu_schedule WHERE date = ? AND meal_slot = ?", (today, current_meal))
        row = cursor.fetchone()
        menu_item = row[0] if row else "Unknown Menu"
        
        cursor.execute('''
            SELECT id, weight_kg FROM tray_logs 
            WHERE date = ? AND student_id = ? AND meal_slot = ?
        ''', (today, student_id, current_meal))
        existing_log = cursor.fetchone()
        
        if existing_log:
            log_id, current_weight = existing_log
            updated_weight = round(current_weight + weight_kg, 2)
            cursor.execute('''
                UPDATE tray_logs 
                SET weight_kg = ?, timestamp = CURRENT_TIMESTAMP 
                WHERE id = ?
            ''', (updated_weight, log_id))
            message = f"Updated Student {student_id}: Added {weight_kg}kg (New Total: {updated_weight}kg). Gate Unlocked!"
        else:
            cursor.execute('''
                INSERT INTO tray_logs (date, student_id, meal_slot, menu_item, weight_kg)
                VALUES (?, ?, ?, ?, ?)
            ''', (today, student_id, current_meal, menu_item, weight_kg))
            message = f"Success! Logged {weight_kg}kg for Student {student_id} ({menu_item}). Gate Unlocked!"
            
        conn.commit()
        conn.close()
        
    return render_template("kiosk.html", message=message)

@app.route("/api/scan", methods=["POST"])
def api_scan():
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