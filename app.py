from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_socketio import SocketIO
from sqlalchemy.orm import DeclarativeBase
import os
from werkzeug.middleware.proxy_fix import ProxyFix
import logging

# Configure logging
logging.basicConfig(level=logging.DEBUG)

class Base(DeclarativeBase):
    pass

# Initialize Flask app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET")
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1) # needed for url_for to generate with https

# Database configuration with enhanced stability
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    'pool_pre_ping': True,          # Verify connections before use
    'pool_recycle': 300,            # Recycle connections every 5 minutes
    'pool_size': 10,                # Maintain 10 connections in pool
    'max_overflow': 20,             # Allow up to 20 additional connections
    'pool_timeout': 30,             # Timeout after 30 seconds
    'pool_reset_on_return': 'commit',  # Reset connections on return
    'connect_args': {
        'connect_timeout': 10,      # Connection timeout
        'application_name': 'food_exhibition_app',
        'sslmode': 'prefer'         # Handle SSL gracefully
    }
}

# Initialize extensions
db = SQLAlchemy(app, model_class=Base)
socketio = SocketIO(app, cors_allowed_origins="*")

# Create tables
with app.app_context():
    import models  # noqa: F401
    db.create_all()
    logging.info("Database tables created")