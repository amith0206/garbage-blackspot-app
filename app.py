from flask import Flask, render_template, request, jsonify, send_from_directory
from datetime import datetime
import os
import psycopg2
import psycopg2.extras
from werkzeug.utils import secure_filename
import uuid

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

# Storage paths
if os.environ.get('RENDER'):
    # Production on Render
    UPLOAD_FOLDER = '/opt/render/project/src/uploads'
else:
    # Local development
    UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'uploads')

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Database URL
DATABASE_URL = os.environ.get('DATABASE_URL')

def get_db_connection():
    """Get PostgreSQL connection"""
    if DATABASE_URL:
        conn = psycopg2.connect(DATABASE_URL)
        return conn
    else:
        raise Exception("DATABASE_URL not configured")

def init_db():
    """Initialize the database"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS blackspots (
                id SERIAL PRIMARY KEY,
                title TEXT,
                latitude DOUBLE PRECISION NOT NULL,
                longitude DOUBLE PRECISION NOT NULL,
                image_filename TEXT NOT NULL,
                created_at TIMESTAMP NOT NULL
            )
        ''')
        conn.commit()
        conn.close()
        print("✓ Database initialized successfully")
    except Exception as e:
        print(f"⚠ Database initialization error: {e}")

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/health')
def health():
    return jsonify({'status': 'healthy'}), 200

@app.route('/uploads/<filename>')
def serve_upload(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)

@app.route('/api/spots', methods=['GET'])
def get_spots():
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cursor.execute('SELECT * FROM blackspots ORDER BY created_at DESC')
        spots = cursor.fetchall()
        conn.close()
        
        for spot in spots:
            if isinstance(spot['created_at'], datetime):
                spot['created_at'] = spot['created_at'].isoformat()
        
        return jsonify(spots), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/spots', methods=['POST'])
def add_spot():
    try:
        if 'image' not in request.files:
            return jsonify({'error': 'No image provided'}), 400
        
        file = request.files['image']
        if file.filename == '':
            return jsonify({'error': 'No image selected'}), 400
        
        if not allowed_file(file.filename):
            return jsonify({'error': 'Invalid file type'}), 400
        
        title = request.form.get('title', '').strip()
        latitude = request.form.get('latitude')
        longitude = request.form.get('longitude')
        
        if not latitude or not longitude:
            return jsonify({'error': 'Location not provided'}), 400
        
        try:
            latitude = float(latitude)
            longitude = float(longitude)
            if not (-90 <= latitude <= 90) or not (-180 <= longitude <= 180):
                return jsonify({'error': 'Invalid coordinate values'}), 400
        except ValueError:
            return jsonify({'error': 'Invalid coordinates'}), 400
        
        # Save image
        filename = secure_filename(file.filename)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        unique_id = str(uuid.uuid4())[:8]
        unique_filename = f"{timestamp}_{unique_id}_{filename}"
        filepath = os.path.join(UPLOAD_FOLDER, unique_filename)
        file.save(filepath)
        
        # Save to database
        conn = get_db_connection()
        cursor = conn.cursor()
        created_at = datetime.now()
        cursor.execute('''
            INSERT INTO blackspots (title, latitude, longitude, image_filename, created_at)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id
        ''', (title, latitude, longitude, unique_filename, created_at))
        spot_id = cursor.fetchone()[0]
        conn.commit()
        conn.close()
        
        return jsonify({
            'id': spot_id,
            'title': title,
            'latitude': latitude,
            'longitude': longitude,
            'image_filename': unique_filename,
            'created_at': created_at.isoformat()
        }), 201
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    init_db()
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=False, host='0.0.0.0', port=port)