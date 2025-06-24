from flask import Flask, render_template, request, redirect, url_for, flash, session
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'your_secret_key'

DATABASE = 'slot_booking.db'

def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        employee_id = request.form['employee_id']
        name = request.form['name']
        phnumber = request.form['phnumber']
        email = request.form['email']
        password = generate_password_hash(request.form['password'])

        conn = get_db_connection()
        try:
            conn.execute('INSERT INTO users (employee_id, name, phnumber, email, password) VALUES (?, ?, ?, ?, ?)',
                         (employee_id, name, phnumber, email, password))
            conn.commit()
        except sqlite3.IntegrityError:
            flash('Employee ID or Email already exists!')
            return redirect(url_for('register'))
        finally:
            conn.close()
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        conn = get_db_connection()
        user = conn.execute('SELECT * FROM users WHERE email = ?', (email,)).fetchone()
        conn.close()

        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['id']
            session['name'] = user['name']
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid email or password')
    return render_template('login.html')

@app.route('/admin_login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        if email == 'mahesh@example.com' and password == '123':
            session['admin'] = True
            return redirect(url_for('admin_dashboard'))
        else:
            flash('Invalid admin credentials')
    return render_template('admin_login.html')

@app.route('/admin_dashboard', methods=['GET', 'POST'])
def admin_dashboard():
    if not session.get('admin'):
        return redirect(url_for('admin_login'))
    
    conn = get_db_connection()
    if request.method == 'POST':
        selected_date = request.form['date']
        bookings = conn.execute('''
            SELECT bookings.id, users.name, bookings.slot_id, bookings.date, bookings.in_time, bookings.out_time, 
                   bookings.vehicle_number, bookings.mobile_number, bookings.status
            FROM bookings
            JOIN users ON bookings.user_id = users.id
            WHERE bookings.date = ?
        ''', (selected_date,)).fetchall()
    else:
        bookings = []
    conn.close()
    
    return render_template('admin_dashboard.html', bookings=bookings)

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template('dashboard.html', name=session['name'])

@app.route('/book_slot', methods=['GET', 'POST'])
def book_slot():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        slot_id = request.form['slot_id']
        in_time = request.form['in_time']
        out_time = request.form['out_time']
        date = request.form['date']
        vehicle_number = request.form['vehicle_number']
        mobile_number = request.form['mobile_number']

        conn = get_db_connection()
        try:
            existing_booking = conn.execute('''
                SELECT * FROM bookings 
                WHERE slot_id = ? AND date = ? AND status = "booked" 
                AND ((in_time <= ? AND out_time >= ?) OR (in_time <= ? AND out_time >= ?))
            ''', (slot_id, date, in_time, in_time, out_time, out_time)).fetchone()
            
            if existing_booking:
                flash('Slot already booked for the selected date and time!')
                return redirect(url_for('book_slot'))
            
            conn.execute('''
                INSERT INTO bookings (user_id, slot_id, date, in_time, out_time, vehicle_number, mobile_number, status) 
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (session['user_id'], slot_id, date, in_time, out_time, vehicle_number, mobile_number, 'booked'))
            conn.commit()
            flash('Slot booked successfully!')
        finally:
            conn.close()
        return redirect(url_for('dashboard'))
    
    conn = get_db_connection()
    booked_slots = conn.execute('SELECT slot_id FROM bookings WHERE status = "booked"').fetchall()
    conn.close()

    booked_slot_ids = [slot['slot_id'] for slot in booked_slots]
    return render_template('book_slot.html', booked_slots=booked_slot_ids)

@app.route('/history')
def history():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    bookings = conn.execute('''
        SELECT id, vehicle_number, slot_id, date, in_time, out_time, status 
        FROM bookings 
        WHERE user_id = ?
    ''', (session['user_id'],)).fetchall()
    conn.close()
    
    return render_template('history.html', bookings=bookings)

@app.route('/cancel_slot', methods=['GET', 'POST'])
def cancel_slot():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    today = datetime.today().strftime('%Y-%m-%d')
    
    active_bookings = conn.execute('''
        SELECT id, slot_id, date, in_time, out_time 
        FROM bookings 
        WHERE user_id = ? AND date >= ? AND status = "booked"
    ''', (session['user_id'], today)).fetchall()
    
    if request.method == 'POST':
        booking_id = request.form.get('booking_id')
        if booking_id:
            conn.execute('DELETE FROM bookings WHERE id = ?', (booking_id,))
            conn.commit()
            flash('Booking canceled successfully!')
            return redirect(url_for('dashboard'))
    
    conn.close()
    return render_template('cancel_slot.html', active_bookings=active_bookings)

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    session.pop('name', None)
    session.pop('admin', None)
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)