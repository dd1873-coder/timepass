from flask import Flask, render_template, request, redirect, url_for, session, flash
from datetime import datetime, date
import sqlite3
import hashlib
import os

app = Flask(__name__)
app.secret_key = '11123'  # Change this in production

# Database initialization
def init_db():
    conn = sqlite3.connect('attendance.db')
    c = conn.cursor()
    
    # Create users table
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  username TEXT UNIQUE NOT NULL,
                  password TEXT NOT NULL,
                  role TEXT NOT NULL DEFAULT 'user',
                  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    
    # Create attendance table
    c.execute('''CREATE TABLE IF NOT EXISTS attendance
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  user_id INTEGER NOT NULL,
                  date DATE NOT NULL,
                  status TEXT NOT NULL,
                  timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                  FOREIGN KEY (user_id) REFERENCES users (id))''')
    
    # Create admin user if not exists
    admin_password = hashlib.sha256('admin11123'.encode()).hexdigest()
    try:
        c.execute("INSERT INTO users (username, password, role) VALUES (?, ?, ?)",
                  ('admin', admin_password, 'admin'))
    except sqlite3.IntegrityError:
        pass  # Admin already exists
    
    conn.commit()
    conn.close()

# Hash password
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# Check if user is logged in
def is_logged_in():
    return 'user_id' in session

# Check if user is admin
def is_admin():
    return session.get('role') == 'admin'

# Database connection helper
def get_db_connection():
    conn = sqlite3.connect('attendance.db')
    conn.row_factory = sqlite3.Row
    return conn

@app.route('/')
def index():
    if not is_logged_in():
        return redirect(url_for('login'))
    
    if is_admin():
        return redirect(url_for('admin_dashboard'))
    else:
        return redirect(url_for('user_dashboard'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if is_logged_in():
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        hashed_password = hash_password(password)
        
        conn = get_db_connection()
        user = conn.execute('SELECT * FROM users WHERE username = ? AND password = ?',
                            (username, hashed_password)).fetchone()
        conn.close()
        
        if user:
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['role'] = user['role']
            flash('Login successful!', 'success')
            return redirect(url_for('index'))
        else:
            flash('Invalid username or password', 'error')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out', 'info')
    return redirect(url_for('login'))

@app.route('/admin/dashboard')
def admin_dashboard():
    if not is_logged_in() or not is_admin():
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    users = conn.execute('SELECT * FROM users').fetchall()
    today_attendance = conn.execute('''
        SELECT users.username, attendance.status, attendance.timestamp 
        FROM attendance 
        JOIN users ON attendance.user_id = users.id 
        WHERE date(attendance.date) = date('now')
        ORDER BY attendance.timestamp DESC
    ''').fetchall()
    conn.close()
    
    return render_template('admin_dashboard.html', users=users, attendance=today_attendance)

@app.route('/admin/create_user', methods=['GET', 'POST'])
def create_user():
    if not is_logged_in() or not is_admin():
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        role = request.form['role']
        hashed_password = hash_password(password)
        
        conn = get_db_connection()
        try:
            conn.execute('INSERT INTO users (username, password, role) VALUES (?, ?, ?)',
                         (username, hashed_password, role))
            conn.commit()
            flash('User created successfully!', 'success')
        except sqlite3.IntegrityError:
            flash('Username already exists', 'error')
        finally:
            conn.close()
        
        return redirect(url_for('create_user'))
    
    return render_template('create_user.html')

@app.route('/admin/mark_attendance', methods=['GET', 'POST'])
def mark_attendance():
    if not is_logged_in() or not is_admin():
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    
    if request.method == 'POST':
        user_id = request.form['user_id']
        status = request.form['status']
        attendance_date = request.form.get('date', date.today().isoformat())
        
        # Check if attendance already exists for this user on this date
        existing = conn.execute('SELECT * FROM attendance WHERE user_id = ? AND date = ?',
                               (user_id, attendance_date)).fetchone()
        
        if existing:
            flash('Attendance already marked for this user today', 'error')
        else:
            conn.execute('INSERT INTO attendance (user_id, date, status) VALUES (?, ?, ?)',
                         (user_id, attendance_date, status))
            conn.commit()
            flash('Attendance marked successfully!', 'success')
    
    users = conn.execute('SELECT * FROM users WHERE role = "user"').fetchall()
    today_attendance = conn.execute('''
        SELECT users.username, attendance.status, attendance.date 
        FROM attendance 
        JOIN users ON attendance.user_id = users.id 
        WHERE date(attendance.date) = date('now')
    ''').fetchall()
    
    conn.close()
    return render_template('mark_attendance.html', users=users, attendance=today_attendance)

@app.route('/user/dashboard')
def user_dashboard():
    if not is_logged_in():
        flash('Please log in first', 'error')
        return redirect(url_for('login'))
    
    if is_admin():
        return redirect(url_for('admin_dashboard'))
    
    user_id = session['user_id']
    conn = get_db_connection()
    
    # Get today's attendance status
    today_status = conn.execute('''
        SELECT status FROM attendance 
        WHERE user_id = ? AND date = date('now')
    ''', (user_id,)).fetchone()
    
    # Get attendance history
    attendance_history = conn.execute('''
        SELECT date, status, timestamp FROM attendance 
        WHERE user_id = ? 
        ORDER BY date DESC
    ''', (user_id,)).fetchall()
    
    conn.close()
    
    return render_template('user_dashboard.html', 
                          today_status=today_status, 
                          attendance_history=attendance_history)

if __name__ == '__main__':
    init_db()
    app.run(debug=True)