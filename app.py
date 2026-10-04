import os
import random
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import traceback
from flask import Flask, render_template, request, jsonify
import psycopg2
import psycopg2.extras

app = Flask(__name__)

# Fetch database configuration from environment variables (Cloud Render URL)
# Fallback to local testing connection string if running locally
DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://reg_hn9o_user:5SEJm5jNEbdsDyGo31SYgnhOGOuv3UVi@dpg-db19ach42hec73eklm9g-a.oregon-postgres.render.com/reg_hn9o")

# Email Configuration (Reads from environment variables for security in production)
SENDER_EMAIL = os.environ.get("SENDER_EMAIL", "mohamedtabran123@gmail.com")
SENDER_PASSWORD = os.environ.get("SENDER_PASSWORD", "evel mwfh chjk hppt")

def get_db_connection():
    # sslmode='require' is usually required for cloud PostgreSQL instances like Render/Aiven
    return psycopg2.connect(DATABASE_URL, sslmode='require')

# Automatically initialize the users table on app startup if it doesn't exist
def init_db():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                name VARCHAR(100) NOT NULL,
                email VARCHAR(100) UNIQUE NOT NULL,
                password VARCHAR(255) NOT NULL,
                otp VARCHAR(6) DEFAULT NULL,
                is_verified BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        ''')
        conn.commit()
        cursor.close()
        conn.close()
    except Exception as e:
        print("Database Initialization Error:")
        traceback.print_exc()

init_db()

def send_email_otp(receiver_email, otp, name):
    try:
        msg = MIMEMultipart()
        msg['From'] = SENDER_EMAIL
        msg['To'] = receiver_email
        msg['Subject'] = "Your College Project Verification Code"

        body = f"Hello {name},\n\nYour OTP for registration is: {otp}\nThis code is valid for 5 minutes."
        msg.attach(MIMEText(body, 'plain'))

        # Connect to Gmail's SMTP server securely
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        server.sendmail(SENDER_EMAIL, receiver_email, msg.as_string())
        server.quit()
        return True
    except Exception as e:
        print("--- EMAIL ERROR TRACEBACK ---")
        traceback.print_exc()
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
        
        # Check if email already exists
        cursor.execute("SELECT id FROM users WHERE email = %s", (email,))
        if cursor.fetchone():
            cursor.close()
            conn.close()
            return jsonify({'success': False, 'error': 'Email already registered.'}), 400

        # Insert user data and temporary OTP into PostgreSQL
        query = "INSERT INTO users (name, email, password, otp, is_verified) VALUES (%s, %s, %s, %s, FALSE)"
        cursor.execute(query, (name, email, password, otp))
        conn.commit()
        cursor.close()
        conn.close()

        # Send email OTP
        email_sent = send_email_otp(email, otp, name)
        if not email_sent:
            return jsonify({'success': False, 'error': 'Failed to send OTP email. Check server logs.'}), 500

        return jsonify({'success': True})

    except Exception as e:
        print("--- REGISTRATION ERROR TRACEBACK ---")
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/verify-otp', methods=['POST'])
def verify_otp():
    data = request.json
    email = data.get('email')
    user_otp = data.get('otp')

    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
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
            
    except Exception as e:
        print("--- VERIFICATION ERROR TRACEBACK ---")
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=True)