from flask import Flask, render_template, request, jsonify, send_from_directory
import os
import uuid
from datetime import datetime
import psycopg
from psycopg.rows import dict_row
from werkzeug.utils import secure_filename

app = Flask(__name__)

# ---------------- CONFIG ----------------
UPLOAD_FOLDER = os.path.join(os.getcwd(), "uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

DATABASE_URL = os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL not set")

# ---------------- DB ----------------
def get_db_connection():
    return psycopg.connect(DATABASE_URL, row_factory=dict_row)

def init_db():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS issues (
            id SERIAL PRIMARY KEY,
            issue_type TEXT NOT NULL,
            title TEXT,
            latitude DOUBLE PRECISION NOT NULL,
            longitude DOUBLE PRECISION NOT NULL,
            image_filename TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    cur.close()
    conn.close()

init_db()

# ---------------- ROUTES ----------------
@app.route("/")
def index():
    return render_template("index.html")

@app.route("/uploads/<filename>")
def uploaded_file(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)

@app.route("/api/issues", methods=["GET"])
def get_issues():
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT * FROM issues ORDER BY created_at DESC")
        rows = cur.fetchall()
        cur.close()
        conn.close()
        return jsonify(rows)
    except Exception as e:
        return jsonify([]), 200  # fail-safe: frontend must not crash

@app.route("/api/issues", methods=["POST"])
def add_issue():
    file = request.files.get("image")
    if not file:
        return jsonify({"error": "Image required"}), 400

    issue_type = request.form.get("issue_type")
    title = request.form.get("title", "")
    latitude = request.form.get("latitude")
    longitude = request.form.get("longitude")

    if not all([issue_type, latitude, longitude]):
        return jsonify({"error": "Missing data"}), 400

    filename = secure_filename(file.filename)
    unique_name = f"{uuid.uuid4().hex}_{filename}"
    file.save(os.path.join(UPLOAD_FOLDER, unique_name))

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO issues (issue_type, title, latitude, longitude, image_filename)
        VALUES (%s, %s, %s, %s, %s)
    """, (issue_type, title, latitude, longitude, unique_name))
    conn.commit()
    cur.close()
    conn.close()

    return jsonify({"success": True}), 201

# ---------------- RUN ----------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
