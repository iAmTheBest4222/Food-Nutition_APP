from flask import Flask
import os
from datetime import timedelta
from modules import db
from flask_caching import Cache

app = Flask(__name__)

# Cache configuration
cache = Cache(app, config={
    'CACHE_TYPE': 'SimpleCache',  # Use SimpleCache since we don't need Redis server setup
    'CACHE_DEFAULT_TIMEOUT': 300  # Cache timeout in seconds (5 minutes)
})

# Database configuration - Use PostgreSQL in production if available
database_url = os.environ.get('DATABASE_URL')
if database_url and database_url.startswith('postgres://'):
    # Heroku-style DATABASE_URL to SQLAlchemy format
    database_url = database_url.replace('postgres://', 'postgresql://', 1)
    app.config['SQLALCHEMY_DATABASE_URI'] = database_url
else:
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///foodscan.db'

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# Session configuration
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'your-default-secret-key')
app.config['SESSION_TYPE'] = 'filesystem'
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=30)

# OAuth Configuration
app.config['GOOGLE_CLIENT_ID'] = os.environ.get('GOOGLE_CLIENT_ID')
app.config['GOOGLE_CLIENT_SECRET'] = os.environ.get('GOOGLE_CLIENT_SECRET')
app.config['GITHUB_CLIENT_ID'] = os.environ.get('GITHUB_CLIENT_ID')
app.config['GITHUB_CLIENT_SECRET'] = os.environ.get('GITHUB_CLIENT_SECRET')

# Initialize database
db.init_app(app)

# Define where uploaded files will be saved - use environment variable for production
UPLOAD_FOLDER = os.environ.get('UPLOAD_FOLDER', 'uploads')
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Import routes after app is created to avoid circular imports
from routes import *

# Create database tables
with app.app_context():
    db.create_all()

if __name__ == '__main__':
    # Use production config when deploying to Render
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
