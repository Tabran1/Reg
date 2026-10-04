import random
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from flask import Flask, render_template, request, jsonify
import mysql.connector

app = Flask(__name__)

# Database Configuration
db_config = {
    'host': 'localhost',
    'user': 'root',
    'password': 'Tabran@007',  # Update with your MySQL password
    'database': 'college_db'
}

# Email Configuration
SENDER_EMAIL = "mohamedtabran123@gmail.com"          # Update with your Gmail
SENDER_PASSWORD = "evel mwfh chjk hppt"     # Update with your 16-character Google App Password

def get_db_connection():
    return mysql.connector.connect(**db_config)

import traceback

def send_email_otp(receiver_email, otp, name):
    try:
        msg = MIMEMultipart()
        msg['From'] = SENDER_EMAIL
        msg['To'] = receiver_email
        msg['Subject'] = "Your College Project Verification Code"

        body = f"Hello {name},\n\nYour OTP for registration is: {otp}\nThis code is valid for 5 minutes."
        msg.attach(MIMEText(body, 'plain'))

        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        server.sendmail(SENDER_EMAIL, receiver_email, msg.as_string())
        server.quit()
        return True
    except Exception as e:
        print("--- EMAIL ERROR TRACEBACK ---")
        traceback.print_exc()  # This will print the exact error line in your terminal
        return False

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/register', methods=['POST'])
def register():
    data = request.json
    name = data.get('name')
    email = data.get('email')
    password = data.get('password')

    otp = str(random.randint(100000, 999999))

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Check if email exists
        cursor.execute("SELECT id FROM users WHERE email = %s", (email,))
        if cursor.fetchone():
            return jsonify({'success': False, 'error': 'Email already registered.'}), 400

        # Insert user data and OTP
        query = "INSERT INTO users (name, email, password, otp, is_verified) VALUES (%s, %s, %s, %s, FALSE)"
        cursor.execute(query, (name, email, password, otp))
        conn.commit()
        cursor.close()
        conn.close()

        # Send email
        email_sent = send_email_otp(email, otp, name)
        if not email_sent:
            return jsonify({'success': False, 'error': 'Failed to send OTP email. Check server logs.'}), 500

        return jsonify({'success': True})

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/verify-otp', methods=['POST'])
def verify_otp():
    data = request.json
    email = data.get('email')
    user_otp = data.get('otp')

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT otp, is_verified FROM users WHERE email = %s", (email,))
    user = cursor.fetchone()

    if not user:
        cursor.close()
        conn.close()
        return jsonify({'success': False, 'error': 'User not found.'}), 404

    if user['otp'] == user_otp:
        cursor.execute("UPDATE users SET is_verified = TRUE, otp = NULL WHERE email = %s", (email,))
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({'success': True})
    else:
        cursor.close()
        conn.close()
        return jsonify({'success': False, 'error': 'Invalid OTP. Please try again.'}), 400

if __name__ == '__main__':
    app.run(debug=True, port=5000)