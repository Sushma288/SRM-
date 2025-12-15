from flask import Flask, render_template, request, redirect, url_for, session, flash
import mysql.connector
import random
import string

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'  # Change this in production

# -------------------- DATABASE CONNECTION --------------------
def get_db_connection():
    return mysql.connector.connect(
        host='localhost',
        user='root',
        password='root',
        database='zemicon_db'
    )

# -------------------- GENERATE RANDOM CODE --------------------
def generate_code(length=10):
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))

# -------------------- HOME --------------------
@app.route('/')
def home():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return render_template('index.html')

# -------------------- REGISTER --------------------
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']  # NOT hashed yet
        role = request.form['role']

        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                "INSERT INTO users (username, password, role) VALUES (%s, %s, %s)",
                (username, password, role)
            )
            conn.commit()
            flash('Registration successful! Please log in.', 'success')
            return redirect(url_for('login'))
        except mysql.connector.Error as err:
            flash(f'Error: {err}', 'error')
        finally:
            cursor.close()
            conn.close()

    return render_template('register.html')

# -------------------- LOGIN --------------------
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            "SELECT * FROM users WHERE username = %s AND password = %s",
            (username, password)
        )
        user = cursor.fetchone()
        cursor.close()
        conn.close()

        if user:
            session['user_id'] = user['id']
            session['role'] = user['role']
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid credentials.', 'error')

    return render_template('login.html')

# -------------------- DASHBOARD --------------------
@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']
    role = session['role']

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM codes WHERE user_id = %s", (user_id,))
    codes = cursor.fetchall()
    cursor.close()
    conn.close()

    return render_template('dashboard.html', codes=codes, role=role)

# -------------------- GENERATE CODE (ONE-TIME ONLY) --------------------
@app.route('/generate_code/<code_type>')
def generate_code_route(code_type):
    if 'user_id' not in session:
        flash("You must log in first.", "error")
        return redirect(url_for('login'))

    # Prevent unauthorized role access
    if session['role'] != code_type:
        flash("Unauthorized action.", "error")
        return redirect(url_for('dashboard'))

    user_id = session['user_id']

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # 1️⃣ Check if user already has a code
    cursor.execute("SELECT * FROM codes WHERE user_id=%s LIMIT 1", (user_id,))
    existing_code = cursor.fetchone()

    if existing_code:
        flash(f"You have already generated your {session['role']} code!", "error")
        cursor.close()
        conn.close()
        return redirect(url_for('dashboard'))

    # 2️⃣ Generate NEW code
    new_code = generate_code()

    cursor.execute("""
        INSERT INTO codes (user_id, code_type, code)
        VALUES (%s, %s, %s)
    """, (user_id, code_type, new_code))

    conn.commit()
    cursor.close()
    conn.close()

    flash(f"{session['role'].capitalize()} code generated: {new_code}", "success")
    return redirect(url_for('dashboard'))

# -------------------- LOGOUT --------------------
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))

# -------------------- RUN SERVER --------------------
if __name__ == '__main__':
    app.run(debug=True)
