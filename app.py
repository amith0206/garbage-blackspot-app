import os, uuid, random
from datetime import datetime, timedelta
from flask import Flask, render_template, request, jsonify
from werkzeug.utils import secure_filename
import psycopg

app = Flask(__name__)

UPLOAD_FOLDER = "static/uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

DATABASE_URL = os.environ["DATABASE_URL"]

def get_db():
    return psycopg.connect(DATABASE_URL)

@app.route("/")
def index():
    return render_template("index.html")

# ---------------- OTP AUTH ----------------

@app.route("/api/send-otp", methods=["POST"])
def send_otp():
    email = request.json.get("email")
    otp = str(random.randint(100000, 999999))
    expiry = datetime.utcnow() + timedelta(minutes=5)

    with get_db() as conn:
        conn.execute("""
            INSERT INTO email_otps (email, otp, expires_at)
            VALUES (%s, %s, %s)
            ON CONFLICT (email)
            DO UPDATE SET otp=%s, expires_at=%s
        """, (email, otp, expiry, otp, expiry))
        conn.commit()

    # TEMP: log OTP (replace with email service)
    app.logger.info(f"OTP for {email}: {otp}")

    return jsonify({"success": True})

@app.route("/api/verify-otp", methods=["POST"])
def verify_otp():
    email = request.json.get("email")
    otp = request.json.get("otp")

    with get_db() as conn:
        row = conn.execute("""
            SELECT otp, expires_at FROM email_otps WHERE email=%s
        """, (email,)).fetchone()

        if not row or row[0] != otp or row[1] < datetime.utcnow():
            return jsonify({"error": "Invalid OTP"}), 400

        user = conn.execute("""
            INSERT INTO users (email)
            VALUES (%s)
            ON CONFLICT (email) DO UPDATE SET email=EXCLUDED.email
            RETURNING id
        """, (email,)).fetchone()

        conn.execute("DELETE FROM email_otps WHERE email=%s", (email,))
        conn.commit()

    return jsonify({"user_id": user[0], "email": email})

# ---------------- ISSUES ----------------

@app.route("/api/issues", methods=["GET"])
def get_issues():
    with get_db() as conn:
        rows = conn.execute("""
            SELECT id, issue_type, description, image_path,
                   latitude, longitude, status, user_id, created_at
            FROM issues
            ORDER BY created_at DESC
        """).fetchall()

    return jsonify([
        {
            "id": r[0],
            "type": r[1],
            "description": r[2],
            "image_path": r[3],
            "latitude": r[4],
            "longitude": r[5],
            "status": r[6],
            "user_id": r[7],
            "created_at": r[8].isoformat()
        } for r in rows
    ])

@app.route("/api/issues", methods=["POST"])
def add_issue():
    user_id = request.headers.get("X-User-Id")
    if not user_id:
        return jsonify({"error": "Unauthorized"}), 401

    image = request.files["image"]
    filename = secure_filename(image.filename)
    unique = f"{uuid.uuid4().hex}_{filename}"
    path = os.path.join(UPLOAD_FOLDER, unique)
    image.save(path)

    with get_db() as conn:
        conn.execute("""
            INSERT INTO issues
            (issue_type, description, image_path,
             latitude, longitude, status, user_id)
            VALUES (%s, %s, %s, %s, %s, 'open', %s)
        """, (
            request.form["issue_type"],
            request.form.get("description", ""),
            path,
            float(request.form["latitude"]),
            float(request.form["longitude"]),
            user_id
        ))
        conn.commit()

    return jsonify({"success": True})

@app.route("/api/issues/<int:issue_id>/resolve", methods=["POST"])
def resolve_issue(issue_id):
    user_id = request.headers.get("X-User-Id")

    with get_db() as conn:
        res = conn.execute("""
            UPDATE issues
            SET status='resolved'
            WHERE id=%s AND user_id=%s
        """, (issue_id, user_id))

        if res.rowcount == 0:
            return jsonify({"error": "Forbidden"}), 403

        conn.commit()

    return jsonify({"success": True})
