import os
import uuid
import random
import smtplib
from datetime import datetime, timedelta
from email.message import EmailMessage

from flask import Flask, render_template, request, jsonify
from werkzeug.utils import secure_filename
import psycopg

# ---------------- APP SETUP ----------------

app = Flask(__name__)

UPLOAD_FOLDER = "static/uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

DATABASE_URL = os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL not set")

SMTP_EMAIL = os.environ.get("SMTP_EMAIL")
SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD")
if not SMTP_EMAIL or not SMTP_PASSWORD:
    raise RuntimeError("SMTP credentials not set")

def get_db():
    return psycopg.connect(DATABASE_URL)

# ---------------- EMAIL OTP ----------------

def send_email_otp(to_email, otp):
    msg = EmailMessage()
    msg["Subject"] = "Your Civic Issue Mapper OTP"
    msg["From"] = SMTP_EMAIL
    msg["To"] = to_email
    msg.set_content(
        f"Your OTP is {otp}.\n\n"
        "This OTP is valid for 5 minutes.\n"
        "Please do not share it with anyone."
    )

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(SMTP_EMAIL, SMTP_PASSWORD)
        server.send_message(msg)

# ---------------- ROUTES ----------------

@app.route("/")
def index():
    return render_template("index.html")

# ---------- AUTH: SEND OTP ----------

@app.route("/api/send-otp", methods=["POST"])
def send_otp():
    email = request.json.get("email")
    if not email:
        return jsonify({"error": "Email required"}), 400

    otp = str(random.randint(100000, 999999))  # 6-digit OTP
    expires_at = datetime.utcnow() + timedelta(minutes=5)

    with get_db() as conn:
        conn.execute("""
            INSERT INTO email_otps (email, otp, expires_at)
            VALUES (%s, %s, %s)
            ON CONFLICT (email)
            DO UPDATE SET otp=%s, expires_at=%s
        """, (email, otp, expires_at, otp, expires_at))
        conn.commit()

    send_email_otp(email, otp)

    return jsonify({"success": True})

# ---------- AUTH: VERIFY OTP ----------

@app.route("/api/verify-otp", methods=["POST"])
def verify_otp():
    email = request.json.get("email")
    otp = request.json.get("otp")

    if not email or not otp:
        return jsonify({"error": "Invalid request"}), 400

    with get_db() as conn:
        row = conn.execute("""
            SELECT otp, expires_at FROM email_otps
            WHERE email = %s
        """, (email,)).fetchone()

        if not row:
            return jsonify({"error": "OTP not found"}), 400

        db_otp, expires_at = row

        if db_otp != otp or expires_at < datetime.utcnow():
            return jsonify({"error": "Invalid or expired OTP"}), 400

        user = conn.execute("""
            INSERT INTO users (email)
            VALUES (%s)
            ON CONFLICT (email)
            DO UPDATE SET email = EXCLUDED.email
            RETURNING id
        """, (email,)).fetchone()

        conn.execute("DELETE FROM email_otps WHERE email = %s", (email,))
        conn.commit()

    return jsonify({
        "user_id": user[0],
        "email": email
    })

# ---------- GET ALL ISSUES ----------

@app.route("/api/issues", methods=["GET"])
def get_issues():
    with get_db() as conn:
        rows = conn.execute("""
            SELECT
                id,
                issue_type,
                description,
                image_path,
                latitude,
                longitude,
                status,
                user_id,
                created_at
            FROM issues
            ORDER BY created_at DESC
        """).fetchall()

    return jsonify([
        {
            "id": r[0],
            "type": r[1],
            "description": r[2] or "",
            "image_path": r[3],
            "latitude": r[4],
            "longitude": r[5],
            "status": r[6],
            "user_id": r[7],
            "created_at": r[8].isoformat()
        } for r in rows
    ])

# ---------- ADD ISSUE ----------

@app.route("/api/issues", methods=["POST"])
def add_issue():
    user_id = request.headers.get("X-User-Id")
    if not user_id:
        return jsonify({"error": "Unauthorized"}), 401

    image = request.files.get("image")
    if not image:
        return jsonify({"error": "Image required"}), 400

    filename = secure_filename(image.filename)
    unique_name = f"{uuid.uuid4().hex}_{filename}"
    image_path = os.path.join(UPLOAD_FOLDER, unique_name)
    image.save(image_path)

    issue_type = request.form.get("issue_type")
    description = request.form.get("description", "")
    latitude = float(request.form.get("latitude"))
    longitude = float(request.form.get("longitude"))

    with get_db() as conn:
        conn.execute("""
            INSERT INTO issues
            (issue_type, description, image_path,
             latitude, longitude, status, user_id)
            VALUES (%s, %s, %s, %s, %s, 'open', %s)
        """, (
            issue_type,
            description,
            image_path,
            latitude,
            longitude,
            user_id
        ))
        conn.commit()

    return jsonify({"success": True})

# ---------- RESOLVE ISSUE (OWNER ONLY) ----------

@app.route("/api/issues/<int:issue_id>/resolve", methods=["POST"])
def resolve_issue(issue_id):
    user_id = request.headers.get("X-User-Id")
    if not user_id:
        return jsonify({"error": "Unauthorized"}), 401

    with get_db() as conn:
        result = conn.execute("""
            UPDATE issues
            SET status = 'resolved'
            WHERE id = %s AND user_id = %s
        """, (issue_id, user_id))

        if result.rowcount == 0:
            return jsonify({"error": "Forbidden"}), 403

        conn.commit()

    return jsonify({"success": True})

# ---------------- MAIN ----------------

if __name__ == "__main__":
    app.run(debug=True)
