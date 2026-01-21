import os
import uuid
from flask import Flask, render_template, request, jsonify
from werkzeug.utils import secure_filename
import psycopg

app = Flask(__name__)

UPLOAD_FOLDER = "static/uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

DATABASE_URL = os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL not set")

def get_db():
    return psycopg.connect(DATABASE_URL)

def init_db():
    with get_db() as conn:
        conn.execute("""
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

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/issues", methods=["GET"])
def get_issues():
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM issues ORDER BY created_at DESC"
        ).fetchall()
        return jsonify([dict(r) for r in rows])

@app.route("/api/issues", methods=["POST"])
def add_issue():
    image = request.files.get("image")
    if not image:
        return jsonify({"error": "Image required"}), 400

    filename = secure_filename(image.filename)
    unique = f"{uuid.uuid4()}_{filename}"
    path = os.path.join(UPLOAD_FOLDER, unique)
    image.save(path)

    with get_db() as conn:
        conn.execute("""
            INSERT INTO issues (issue_type, description, image_path, latitude, longitude)
            VALUES (%s, %s, %s, %s, %s)
        """, (
            request.form["issue_type"],
            request.form.get("description", ""),
            path,
            float(request.form["latitude"]),
            float(request.form["longitude"])
        ))

    return jsonify({"success": True})

@app.route("/api/issues/<int:id>/resolve", methods=["POST"])
def resolve_issue(id):
    with get_db() as conn:
        conn.execute("UPDATE issues SET status='resolved' WHERE id=%s", (id,))
    return jsonify({"success": True})

if __name__ == "__main__":
    init_db()
    app.run()
