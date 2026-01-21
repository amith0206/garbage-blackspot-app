import os
import uuid
from datetime import datetime
from flask import Flask, render_template, request, jsonify, send_from_directory
import psycopg
from werkzeug.utils import secure_filename

app = Flask(__name__)

UPLOAD_FOLDER = "static/uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

DATABASE_URL = os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL not set")

def get_db_connection():
    return psycopg.connect(DATABASE_URL)

# 🔧 AUTO INIT DB (VERY IMPORTANT)
def init_db():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS issues (
            id SERIAL PRIMARY KEY,
            issue_type VARCHAR(50) NOT NULL,
            description TEXT,
            image_path TEXT NOT NULL,
            latitude DOUBLE PRECISION NOT NULL,
            longitude DOUBLE PRECISION NOT NULL,
            status VARCHAR(20) DEFAULT 'open',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)
    conn.commit()
    cur.close()
    conn.close()

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/issues", methods=["GET"])
def get_issues():
    conn = get_db_connection()
    cur = conn.cursor(row_factory=psycopg.rows.dict_row)
    cur.execute("SELECT * FROM issues ORDER BY created_at DESC")
    data = cur.fetchall()
    cur.close()
    conn.close()
    return jsonify(data)

@app.route("/api/issues", methods=["POST"])
def add_issue():
    image = request.files.get("image")
    if not image:
        return jsonify({"error": "Image required"}), 400

    filename = secure_filename(image.filename)
    unique_name = f"{uuid.uuid4()}_{filename}"
    image_path = os.path.join(UPLOAD_FOLDER, unique_name)
    image.save(image_path)

    issue_type = request.form.get("issue_type")
    description = request.form.get("description", "")
    latitude = float(request.form.get("latitude"))
    longitude = float(request.form.get("longitude"))

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO issues (issue_type, description, image_path, latitude, longitude)
        VALUES (%s, %s, %s, %s, %s)
    """, (issue_type, description, image_path, latitude, longitude))
    conn.commit()
    cur.close()
    conn.close()

    return jsonify({"success": True})

@app.route("/api/issues/<int:issue_id>/resolve", methods=["POST"])
def resolve_issue(issue_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("UPDATE issues SET status='resolved' WHERE id=%s", (issue_id,))
    conn.commit()
    cur.close()
    conn.close()
    return jsonify({"success": True})

if __name__ == "__main__":
    init_db()
    app.run()
