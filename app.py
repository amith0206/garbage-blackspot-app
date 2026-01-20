from flask import Flask, render_template, request, jsonify
from datetime import datetime
import os
import uuid
from werkzeug.utils import secure_filename

app = Flask(__name__)

# Config
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

UPLOAD_FOLDER = os.path.join(app.root_path, 'static', 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

DATABASE_URL = os.environ.get('DATABASE_URL')
USE_SQLITE = DATABASE_URL is None

# ---------------- DB ---------------- #

def get_db():
    if USE_SQLITE:
        import sqlite3
        conn = sqlite3.connect('database.db')
        conn.row_factory = sqlite3.Row
        return conn
    else:
        import psycopg
        from psycopg.rows import dict_row
        return psycopg.connect(DATABASE_URL, row_factory=dict_row)

def init_db():
    with get_db() as db:
        cur = db.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS issues (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT,
                issue_type TEXT NOT NULL,
                latitude REAL NOT NULL,
                longitude REAL NOT NULL,
                image_filename TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        """)
        db.commit()

# ---------------- Utils ---------------- #

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

# ---------------- Routes ---------------- #

@app.route('/')
def index():
    return render_template('main.html')

@app.route('/api/issues', methods=['GET'])
def get_issues():
    with get_db() as db:
        cur = db.cursor()
        cur.execute("SELECT * FROM issues ORDER BY created_at DESC")
        rows = cur.fetchall()
    return jsonify([dict(r) for r in rows])

@app.route('/api/issues', methods=['POST'])
def add_issue():
    try:
        file = request.files.get('image')
        if not file or not allowed_file(file.filename):
            return jsonify({'error': 'Invalid image'}), 400

        issue_type = request.form.get('issue_type')
        if issue_type not in ['garbage', 'broken_footpath', 'blocked_footpath']:
            return jsonify({'error': 'Invalid issue type'}), 400

        lat = float(request.form['latitude'])
        lng = float(request.form['longitude'])
        title = request.form.get('title', '').strip()

        filename = secure_filename(file.filename)
        unique = f"{uuid.uuid4().hex}_{filename}"
        file.save(os.path.join(UPLOAD_FOLDER, unique))

        created_at = datetime.utcnow().isoformat()

        with get_db() as db:
            cur = db.cursor()
            cur.execute("""
                INSERT INTO issues
                (title, issue_type, latitude, longitude, image_filename, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (title, issue_type, lat, lng, unique, created_at))
            db.commit()

        return jsonify({'success': True}), 201

    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=5000)
