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
    raise RuntimeError("DATABASE_URL environment variable not set")

def get_db():
    return psycopg.connect(DATABASE_URL)

def init_db():
    with get_db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS issues (
                id SERIAL PRIMARY KEY,
                type VARCHAR(50) NOT NULL,
                description TEXT,
                image_path TEXT NOT NULL,
                latitude DOUBLE PRECISION NOT NULL,
                longitude DOUBLE PRECISION NOT NULL,
                status VARCHAR(20) DEFAULT 'open',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        conn.commit()

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/issues", methods=["GET"])
def get_issues():
    with get_db() as conn:
        cursor = conn.execute(
            "SELECT id, type, description, image_path, latitude, longitude, status, created_at FROM issues ORDER BY created_at DESC"
        )
        rows = cursor.fetchall()
        
        # Convert to list of dicts
        issues = []
        for row in rows:
            issues.append({
                "id": row[0],
                "type": row[1],
                "description": row[2],
                "image_path": row[3],
                "latitude": row[4],
                "longitude": row[5],
                "status": row[6],
                "created_at": row[7].isoformat() if row[7] else None
            })
        
        return jsonify(issues)

@app.route("/api/issues", methods=["POST"])
def add_issue():
    try:
        # Validate image
        image = request.files.get("image")
        if not image:
            return jsonify({"error": "Image is required"}), 400

        # Validate coordinates
        try:
            latitude = float(request.form.get("latitude"))
            longitude = float(request.form.get("longitude"))
        except (TypeError, ValueError):
            return jsonify({"error": "Invalid coordinates"}), 400

        # Validate issue type
        issue_type = request.form.get("type")
        if not issue_type:
            return jsonify({"error": "Issue type is required"}), 400

        # Save image
        filename = secure_filename(image.filename)
        unique_filename = f"{uuid.uuid4()}_{filename}"
        image_path = os.path.join(UPLOAD_FOLDER, unique_filename)
        image.save(image_path)

        # Insert into database
        with get_db() as conn:
            conn.execute("""
                INSERT INTO issues (type, description, image_path, latitude, longitude)
                VALUES (%s, %s, %s, %s, %s)
            """, (
                issue_type,
                request.form.get("description", ""),
                image_path,
                latitude,
                longitude
            ))
            conn.commit()

        return jsonify({"success": True, "message": "Issue reported successfully"})

    except Exception as e:
        app.logger.error(f"Error adding issue: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

@app.route("/api/issues/<int:issue_id>/resolve", methods=["POST"])
def resolve_issue(issue_id):
    try:
        with get_db() as conn:
            conn.execute(
                "UPDATE issues SET status='resolved' WHERE id=%s",
                (issue_id,)
            )
            conn.commit()
        return jsonify({"success": True})
    except Exception as e:
        app.logger.error(f"Error resolving issue: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

if __name__ == "__main__":
    init_db()
    app.run(debug=True)
