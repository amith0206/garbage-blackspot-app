import os
import uuid
from flask import Flask, render_template, request, jsonify
from werkzeug.utils import secure_filename
import psycopg

app = Flask(__name__)

UPLOAD_FOLDER = "static/uploads"
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024  # 5MB

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

DATABASE_URL = os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL not set")

def get_db():
    return psycopg.connect(DATABASE_URL)

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/issues", methods=["GET"])
def get_issues():
    try:
        with get_db() as conn:
            rows = conn.execute("""
                SELECT id, issue_type, description, image_path,
                       latitude, longitude, status, created_at
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
                "created_at": r[7].isoformat()
            } for r in rows
        ])

    except Exception as e:
        app.logger.error(f"Fetch error: {e}")
        return jsonify({"error": "Failed to fetch issues"}), 500

@app.route("/api/issues", methods=["POST"])
def add_issue():
    try:
        image = request.files.get("image")
        if not image or image.filename == "":
            return jsonify({"error": "Image required"}), 400

        issue_type = request.form.get("issue_type")
        if not issue_type:
            return jsonify({"error": "Issue type required"}), 400

        description = request.form.get("description", "")

        latitude = float(request.form["latitude"])
        longitude = float(request.form["longitude"])

        filename = secure_filename(image.filename)
        unique_name = f"{uuid.uuid4().hex}_{filename}"
        save_path = os.path.join(app.config["UPLOAD_FOLDER"], unique_name)
        image.save(save_path)

        with get_db() as conn:
            conn.execute("""
                INSERT INTO issues
                (issue_type, description, image_path, latitude, longitude, status)
                VALUES (%s, %s, %s, %s, %s, 'open')
            """, (issue_type, description, save_path, latitude, longitude))
            conn.commit()

        return jsonify({"success": True})

    except Exception as e:
        app.logger.error(f"Upload error: {e}")
        return jsonify({"error": "Upload failed"}), 500

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
        app.logger.error(e)
        return jsonify({"error": "Resolve failed"}), 500

if __name__ == "__main__":
    app.run(debug=True)
