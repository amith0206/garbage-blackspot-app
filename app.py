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
    """Initialize or update database schema"""
    with get_db() as conn:
        # Create table if it doesn't exist
        conn.execute("""
            CREATE TABLE IF NOT EXISTS issues (
                id SERIAL PRIMARY KEY,
                issue_type VARCHAR(50) NOT NULL,
                image_path TEXT NOT NULL,
                latitude DOUBLE PRECISION NOT NULL,
                longitude DOUBLE PRECISION NOT NULL
            );
        """)
        
        # Add columns if they don't exist (for existing tables)
        try:
            conn.execute("ALTER TABLE issues ADD COLUMN IF NOT EXISTS description TEXT;")
            conn.execute("ALTER TABLE issues ADD COLUMN IF NOT EXISTS status VARCHAR(20) DEFAULT 'open';")
            conn.execute("ALTER TABLE issues ADD COLUMN IF NOT EXISTS created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;")
            conn.commit()
            app.logger.info("Database schema updated successfully")
        except Exception as e:
            app.logger.warning(f"Schema update note: {e}")
            conn.rollback()

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/issues", methods=["GET"])
def get_issues():
    try:
        with get_db() as conn:
            # First check what columns exist
            cursor = conn.execute("""
                SELECT column_name FROM information_schema.columns 
                WHERE table_name = 'issues'
            """)
            available_columns = [row[0] for row in cursor.fetchall()]
            
            # Build SELECT query based on available columns
            base_columns = ["id", "issue_type", "image_path", "latitude", "longitude"]
            optional_columns = []
            
            if "description" in available_columns:
                optional_columns.append("description")
            if "status" in available_columns:
                optional_columns.append("status")
            if "created_at" in available_columns:
                optional_columns.append("created_at")
            
            select_columns = base_columns + optional_columns
            query = f"SELECT {', '.join(select_columns)} FROM issues ORDER BY id DESC"
            
            cursor = conn.execute(query)
            rows = cursor.fetchall()
            
            # Convert to list of dicts
            issues = []
            for row in rows:
                issue = {
                    "id": row[0],
                    "type": row[1],
                    "image_path": row[2],
                    "latitude": row[3],
                    "longitude": row[4],
                    "description": row[5] if len(row) > 5 and "description" in optional_columns else "",
                    "status": row[6] if len(row) > 6 and "status" in optional_columns else "open",
                    "created_at": row[7].isoformat() if len(row) > 7 and "created_at" in optional_columns and row[7] else None
                }
                issues.append(issue)
            
            return jsonify(issues)
    except Exception as e:
        app.logger.error(f"Error fetching issues: {str(e)}")
        return jsonify({"error": "Failed to fetch issues"}), 500

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
        issue_type = request.form.get("issue_type")
        if not issue_type:
            return jsonify({"error": "Issue type is required"}), 400

        # Save image
        filename = secure_filename(image.filename)
        unique_filename = f"{uuid.uuid4()}_{filename}"
        image_path = os.path.join(UPLOAD_FOLDER, unique_filename)
        image.save(image_path)

        # Check what columns exist
        with get_db() as conn:
            cursor = conn.execute("""
                SELECT column_name FROM information_schema.columns 
                WHERE table_name = 'issues'
            """)
            available_columns = [row[0] for row in cursor.fetchall()]
            
            # Build INSERT query based on available columns
            columns = ["issue_type", "image_path", "latitude", "longitude"]
            values = [issue_type, image_path, latitude, longitude]
            placeholders = ["%s", "%s", "%s", "%s"]
            
            # Add optional columns if they exist
            if "description" in available_columns:
                columns.append("description")
                values.append(request.form.get("description", ""))
                placeholders.append("%s")
            
            if "status" in available_columns:
                columns.append("status")
                values.append("open")
                placeholders.append("%s")
            
            query = f"""
                INSERT INTO issues ({', '.join(columns)})
                VALUES ({', '.join(placeholders)})
            """
            
            conn.execute(query, values)
            conn.commit()

        return jsonify({"success": True, "message": "Issue reported successfully"})

    except Exception as e:
        app.logger.error(f"Error adding issue: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

@app.route("/api/issues/<int:issue_id>/resolve", methods=["POST"])
def resolve_issue(issue_id):
    try:
        with get_db() as conn:
            # Check if status column exists
            cursor = conn.execute("""
                SELECT column_name FROM information_schema.columns 
                WHERE table_name = 'issues' AND column_name = 'status'
            """)
            
            if cursor.fetchone():
                conn.execute(
                    "UPDATE issues SET status='resolved' WHERE id=%s",
                    (issue_id,)
                )
                conn.commit()
                return jsonify({"success": True})
            else:
                return jsonify({"error": "Status column not available"}), 400
                
    except Exception as e:
        app.logger.error(f"Error resolving issue: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

if __name__ == "__main__":
    init_db()
    app.run(debug=True)
