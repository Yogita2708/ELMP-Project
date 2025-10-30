import sqlite3
from datetime import datetime, date
from flask import Flask, render_template, request, redirect, url_for, flash, session
import uuid
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

app = Flask(__name__)
# IMPORTANT: Replace with a strong, secret key for production
app.secret_key = 'super_secret_key_for_elmp' 

# --- EMAIL CONFIGURATION (Mandatory to Update) ---
# NOTE: If using Gmail, you MUST generate an App Password:
# Google Account -> Security -> 2-Step Verification -> App passwords
SMTP_SERVER = 'smtp.gmail.com'
SMTP_PORT = 587
EMAIL_ADDRESS = 'agarwalyogita24@gmail.com'  # <--- REPLACE WITH YOUR GMAIL ADDRESS
EMAIL_PASSWORD = '1234567890yogita'          # <--- REPLACE WITH YOUR GENERATED APP PASSWORD
HR_ADMIN_EMAIL = 'Yogitaagrawal27@outlook.com' # <--- HR Admin's Email (Anya)

# --- DATABASE SETUP AND UTILITIES ---

def get_db_connection():
    conn = sqlite3.connect('leave.db')
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    # Create users and leaves tables
    conn.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            role TEXT NOT NULL,
            email TEXT NOT NULL,
            department TEXT,
            manager TEXT,
            leave_balances TEXT  -- Stored as JSON string
        )
    ''')
    conn.execute('''
        CREATE TABLE IF NOT EXISTS leaves (
            request_id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            employee_name TEXT NOT NULL,
            leave_type TEXT NOT NULL,
            start_date DATE NOT NULL,
            end_date DATE NOT NULL,
            days INTEGER NOT NULL,
            reason TEXT,
            date_submitted TEXT NOT NULL,
            status TEXT NOT NULL
        )
    ''')
    conn.commit()

    # Define initial data for the simulation (users and balances)
    initial_users = {
        'E101': {'name': 'Reeya Agrawal', 'role': 'Employee', 'email': 'reeya.ag@example.com', 'department': 'Engineering', 'manager': 'Priya Singh', 'balances': '{"Annual Leave (AL)": 15, "Sick Leave (SL)": 7, "Personal Day (PD)": 3}'},
        'E102': {'name': 'Siddharth Gupta', 'role': 'Employee', 'email': 'sid.gupta@example.com', 'department': 'Marketing', 'manager': 'Vikram Mehra', 'balances': '{"Annual Leave (AL)": 10, "Sick Leave (SL)": 5, "Personal Day (PD)": 2}'},
        'A201': {'name': 'Anya Singh', 'role': 'Admin', 'email': HR_ADMIN_EMAIL, 'department': 'HR', 'manager': 'CEO', 'balances': '{}'},
    }

    # Insert initial users if they don't exist
    for user_id, data in initial_users.items():
        existing_user = conn.execute("SELECT id FROM users WHERE id = ?", (user_id,)).fetchone()
        if not existing_user:
            conn.execute("INSERT INTO users VALUES (?, ?, ?, ?, ?, ?, ?)", 
                         (user_id, data['name'], data['role'], data['email'], data['department'], data['manager'], data['balances']))
    conn.commit()
    conn.close()

# Initialize the database when the app starts
init_db()

# Global list of all user profiles for the role switcher (simulating authentication)
ALL_PROFILES = {
    'E101': {'name': 'Reeya Agrawal', 'role': 'Employee', 'department': 'Engineering'},
    'E102': {'name': 'Siddharth Gupta', 'role': 'Employee', 'department': 'Marketing'},
    'A201': {'name': 'Anya Singh', 'role': 'Admin', 'department': 'HR'}
}

def get_current_user_data(user_id):
    """Fetches user data including balances from the database."""
    conn = get_db_connection()
    user = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    conn.close()
    if user:
        # Convert the Row object to a dictionary and parse leave_balances string
        user_data = dict(user)
        import json
        user_data['leave_balances'] = json.loads(user_data['leave_balances']) if user_data['leave_balances'] else {}
        return user_data
    return None

# --- EMAIL NOTIFICATION FUNCTION (NEW) ---

def send_notification_email(employee_name, leave_type, start_date, end_date, reason):
    """Sends an email notification to the HR Admin."""
    
    msg = MIMEMultipart()
    msg['From'] = EMAIL_ADDRESS
    msg['To'] = HR_ADMIN_EMAIL
    msg['Subject'] = f"NEW Leave Request: {employee_name} ({leave_type})"

    # Email body content
    body = f"""
    A new leave request has been submitted and requires your review.

    Employee: {employee_name}
    Leave Type: {leave_type}
    Start Date: {start_date}
    End Date: {end_date}
    Reason: {reason}

    Please log into the ELMP Dashboard to approve or reject the request.
    """
    
    msg.attach(MIMEText(body, 'plain'))
    
    try:
        # Connect to the SMTP server
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()  # Upgrade connection to secure/encrypted
        server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
        
        # Send the email
        server.sendmail(EMAIL_ADDRESS, HR_ADMIN_EMAIL, msg.as_string())
        server.quit()
        print(f"SUCCESS: Email notification sent to {HR_ADMIN_EMAIL}")
        return True
    
    except Exception as e:
        print(f"ERROR: Failed to send email. Check your SMTP settings/App Password. Error: {e}")
        return False


# --- FLASK ROUTES ---

@app.route('/')
def index():
    """Default route redirects to the current user's dashboard."""
    # Start with a default user if none is selected
    if 'user_id' not in session:
        session['user_id'] = 'E101' # Default to Employee Reeya
    
    return redirect(url_for('dashboard'))

@app.route('/switch/<user_id>')
def switch_user(user_id):
    """Allows simulating switching between user roles."""
    if user_id in ALL_PROFILES:
        session['user_id'] = user_id
        flash(f"Switched user to {ALL_PROFILES[user_id]['name']} ({ALL_PROFILES[user_id]['role']}).", 'success')
    else:
        flash("Invalid user ID.", 'error')
    return redirect(url_for('dashboard'))


@app.route('/dashboard')
def dashboard():
    """Main dashboard showing profile, balances, and history/admin panel."""
    current_user_id = session.get('user_id', 'E101')
    user_data = get_current_user_data(current_user_id)
    
    if not user_data:
        flash("User data could not be loaded.", 'error')
        return redirect(url_for('index'))

    conn = get_db_connection()
    history = []
    
    if user_data['role'] == 'Employee':
        # Employee view: show only their own requests
        history = conn.execute("SELECT * FROM leaves WHERE user_id = ? ORDER BY date_submitted DESC", (current_user_id,)).fetchall()
    elif user_data['role'] == 'Admin':
        # Admin view: show all requests
        history = conn.execute("SELECT * FROM leaves ORDER BY date_submitted DESC").fetchall()
    
    conn.close()
    
    return render_template(
        'dashboard.html',
        user=user_data,
        balances=user_data['leave_balances'],
        history=history,
        all_profiles=ALL_PROFILES
    )

@app.route('/company_info')
def company_info():
    """Displays generic company information."""
    current_user_id = session.get('user_id', 'E101')
    user_data = get_current_user_data(current_user_id)
    
    return render_template(
        'company_info.html', 
        user=user_data,
        all_profiles=ALL_PROFILES
    )


@app.route('/apply_leave', methods=['POST'])
def apply_leave():
    """Handles the submission of a new leave request."""
    current_user_id = session.get('user_id')
    user_data = get_current_user_data(current_user_id)

    if not user_data or user_data['role'] != 'Employee':
        flash('You must be logged in as an Employee to submit a request.', 'error')
        return redirect(url_for('dashboard'))

    try:
        # Get form data
        leave_type_abbr = request.form['leave_type']
        start_date_str = request.form['start_date']
        end_date_str = request.form['end_date']
        reason = request.form['reason']
        
        # Convert date strings to date objects for calculation
        start_date_obj = datetime.strptime(start_date_str, '%Y-%m-%d').date()
        end_date_obj = datetime.strptime(end_date_str, '%Y-%m-%d').date()
        
        # Calculate number of days (inclusive)
        days = (end_date_obj - start_date_obj).days + 1
        
        if days <= 0:
            flash("End date must be on or after the start date.", 'error')
            return redirect(url_for('dashboard'))

        # Find the full leave type name (e.g., 'Sick Leave (SL)')
        full_leave_type = next((k for k, v in user_data['leave_balances'].items() if f"({leave_type_abbr})" in k), None)
        
        if not full_leave_type:
            flash("Invalid leave type selected.", 'error')
            return redirect(url_for('dashboard'))

        # Check balance (Simplified: checking total balance, not including weekends/holidays)
        current_balance = user_data['leave_balances'].get(full_leave_type, 0)
        if days > current_balance:
            flash(f"Insufficient balance: Requested {days} days, but only have {current_balance} days of {full_leave_type}.", 'error')
            return redirect(url_for('dashboard'))

        # Generate unique ID and current timestamp
        request_id = str(uuid.uuid4())[:8]
        date_submitted = datetime.now().strftime('%Y-%m-%d %H:%M')
        
        # Save request to DB
        conn = get_db_connection()
        conn.execute(
            "INSERT INTO leaves VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (request_id, current_user_id, user_data['name'], full_leave_type, start_date_str, end_date_str, days, reason, date_submitted, 'Pending')
        )
        conn.commit()
        conn.close()

        # --- EMAIL NOTIFICATION INTEGRATION (NEW) ---
        email_sent = send_notification_email(user_data['name'], full_leave_type, start_date_str, end_date_str, reason)
        
        if email_sent:
             flash('Leave request submitted successfully! HR Admin has been notified via email.', 'success')
        else:
             flash('Leave request submitted successfully, but email notification to Admin failed. Please check app.py configuration.', 'error')


    except Exception as e:
        flash(f'An unexpected error occurred during submission: {e}', 'error')
        print(f"Error submitting leave request: {e}")

    return redirect(url_for('dashboard'))


if __name__ == '__main__':
    app.run(debug=True)
