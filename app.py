import os
from flask import Flask, render_template, request, redirect, url_for, flash, session
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from flask_mail import Mail, Message
import random

app = Flask(__name__, static_folder='assets')
app.secret_key = os.environ.get('SECRET_KEY', 'fallback_dev_secret_key')

# --- EMAIL CONFIGURATION ---
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 465
app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME', '')
app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD', '')
app.config['MAIL_USE_TLS'] = False
app.config['MAIL_USE_SSL'] = True
mail = Mail(app)

# --- CONFIGURATION ---
# Use /tmp for uploads so it works on Render (ephemeral but functional)
UPLOAD_FOLDER = '/tmp/uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# --- DATABASE ---
# Use /tmp/fixify.db so Render can write to it
DB_PATH = '/tmp/fixify.db'

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS issues (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            description TEXT,
            location TEXT,
            photo_filename TEXT,
            status TEXT DEFAULT 'Pending',
            priority TEXT DEFAULT 'Medium',
            user_id INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

# Initialize DB on startup
init_db()

# --- AI DETECTION (Smart Demo Mode) ---
print("\n--- INITIALIZING AI SYSTEMS ---")
print("Running in SMART DEMO MODE")
print("-------------------------------\n")

ISSUE_CATEGORIES = {
    'pothole': ('Pothole', 'High'),
    'garbage': ('Garbage / Waste', 'Medium'),
    'flood': ('Flooding / Waterlogging', 'High'),
    'crack': ('Road Crack', 'Medium'),
    'graffiti': ('Graffiti / Vandalism', 'Low'),
    'broken': ('Broken Infrastructure', 'High'),
    'light': ('Street Light Issue', 'Medium'),
    'drain': ('Blocked Drain', 'High'),
    'tree': ('Fallen Tree', 'Medium'),
    'default': ('General Civic Issue', 'Medium'),
}

def analyze_image_with_ai(image_path, description=''):
    """Smart demo: tries to guess category from filename/description."""
    desc_lower = (description + ' ' + os.path.basename(image_path)).lower()
    for keyword, (category, priority) in ISSUE_CATEGORIES.items():
        if keyword in desc_lower:
            return category, priority, 0
    # Random realistic result for demo
    options = list(ISSUE_CATEGORIES.values())[:-1]
    category, priority = random.choice(options)
    return category, priority, 0

# --- ROUTES ---

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form.get("name")
        email = request.form.get("email")
        password = request.form.get("password")
        hashed_password = generate_password_hash(password)
        try:
            conn = get_db()
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO users (name, email, password) VALUES (?, ?, ?)",
                (name, email, hashed_password)
            )
            conn.commit()
        except sqlite3.IntegrityError:
            flash("Email already registered.", "danger")
            return redirect(url_for('register'))
        finally:
            conn.close()
        flash("Registration successful! Please login.", "success")
        return redirect(url_for('login'))
    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
        user = cursor.fetchone()
        conn.close()
        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['id']
            session['user_name'] = user['name']
            return redirect(url_for('dashboard'))
        else:
            flash("Invalid email or password.", "danger")
    return render_template("login.html")

@app.route("/dashboard")
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM issues ORDER BY id DESC")
    issues = cursor.fetchall()
    conn.close()
    return render_template("dashboard.html", issues=issues)

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for('home'))

# --- REPORT ISSUE ---
@app.route('/report_issue', methods=['GET', 'POST'])
def report_issue():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    if request.method == 'POST':
        description = request.form.get('description', '')
        location = request.form.get('location', '')
        photo = request.files.get('photo')
        user_id = session['user_id']

        filename = None
        detected_category = 'General Civic Issue'
        priority = 'Medium'

        if photo and photo.filename != '':
            filename = secure_filename(photo.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            photo.save(filepath)
            detected_category, priority, is_spam = analyze_image_with_ai(filepath, description)

        conn = get_db()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO issues (title, description, location, photo_filename, priority, user_id) VALUES (?, ?, ?, ?, ?, ?)",
            (detected_category, description, location, filename, priority, user_id)
        )
        conn.commit()
        conn.close()
        flash(f"Issue reported! Detected: {detected_category} (Priority: {priority})", "success")
        return redirect(url_for('dashboard'))
    return render_template('report_issue.html')

# --- ADMIN ---
@app.route('/admin', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        admin_password = os.environ.get('ADMIN_PASSWORD', 'admin123')
        if request.form.get('password') == admin_password:
            session['admin'] = True
            return redirect(url_for('admin_dashboard'))
        else:
            flash("Wrong password", "danger")
    return render_template("admin_login.html")

@app.route('/admin/dashboard')
def admin_dashboard():
    if not session.get('admin'):
        return redirect(url_for('admin_login'))
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT issues.*, users.name as reporter FROM issues LEFT JOIN users ON issues.user_id = users.id ORDER BY issues.id DESC")
    issues = cursor.fetchall()
    conn.close()
    return render_template("admin.html", issues=issues)

@app.route('/admin/update_status/<int:issue_id>', methods=['POST'])
def update_status(issue_id):
    if not session.get('admin'):
        return redirect(url_for('admin_login'))
    new_status = request.form.get('status')
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("UPDATE issues SET status = ? WHERE id = ?", (new_status, issue_id))
    conn.commit()
    conn.close()
    flash("Status updated!", "success")
    return redirect(url_for('admin_dashboard'))

# --- RUN ---
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
