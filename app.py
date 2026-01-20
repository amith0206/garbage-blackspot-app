from flask import Flask, render_template, request, jsonify, send_from_directory
from datetime import datetime
import os
import uuid
from werkzeug.utils import secure_filename
import psycopg
from psycopg.rows import dict_row

app = Flask(__name__)

app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

# Upload folder (INSIDE static)
UPLOAD_FOLDER = os.path.join(app.root_path, 'static', 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Database
DATABASE_URL = os.environ.get('DATABASE_URL')
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL not set")

def get_db_connection():
    return psycopg.connect(DATABASE_URL, row_factory=dict_row)

def init_db():
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS blackspots (
                    id SERIAL PRIMARY KEY,
                    title TEXT,
                    latitude DOUBLE PRECISION NOT NULL,
                    longitude DOUBLE PRECISION NOT NULL,
                    image_filename TEXT NOT NULL,
                    created_at TIMESTAMP NOT NULL
                )
            """)
            conn.commit()
    print("✓ Database ready")

def allowed_file(filename):
    return '.' in filename and \
        filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

@app.route('/')
def index():
    return render_template('main.html')

@app.route('/health')
def health():
    return jsonify({'status': 'ok'})

@app.route('/api/spots', methods=['GET'])
def get_spots():
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM blackspots ORDER BY created_at DESC")
                spots = cur.fetchall()

        for s in spots:
            s['created_at'] = s['created_at'].isoformat()

        return jsonify(spots)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/spots', methods=['POST'])
def add_spot():
    try:
        if 'image' not in request.files:
            return jsonify({'error': 'Image required'}), 400

        file = request.files['image']
        if file.filename == '' or not allowed_file(file.filename):
            return jsonify({'error': 'Invalid image'}), 400

        latitude = float(request.form['latitude'])
        longitude = float(request.form['longitude'])
        title = request.form.get('title', '').strip()

        filename = secure_filename(file.filename)
        unique_name = f"{datetime.now():%Y%m%d_%H%M%S}_{uuid.uuid4().hex[:8]}_{filename}"
        file.save(os.path.join(UPLOAD_FOLDER, unique_name))

        created_at = datetime.utcnow()

        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO blackspots
                    (title, latitude, longitude, image_filename, created_at)
                    VALUES (%s, %s, %s, %s, %s)
                    RETURNING id
                """, (title, latitude, longitude, unique_name, created_at))
                spot_id = cur.fetchone()['id']
                conn.commit()

        return jsonify({
            'id': spot_id,
            'title': title,
            'latitude': latitude,
            'longitude': longitude,
            'image_filename': unique_name,
            'created_at': created_at.isoformat()
        }), 201

    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
