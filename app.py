from flask import Flask, session, request
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect
import os
from werkzeug.middleware.proxy_fix import ProxyFix
import logging
from extensions import db, migrate, socketio
from flask_migrate import Migrate
import socket_handlers  # Import socket handlers
from dotenv import load_dotenv  # Load environment variables from .env file
import socket

# Load environment variables from .env file
load_dotenv()

# Initialize CSRF protection
csrf = CSRFProtect()

# Configure logging
logging.basicConfig(level=logging.DEBUG)

def create_app():
    # Initialize Flask app
    app = Flask(__name__)
    app.secret_key = os.environ.get("SESSION_SECRET", "dev_secret_key")
    app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)
    
    # Initialize CSRF protection
    csrf.init_app(app)
    
    # Set up database configuration
    db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "instance", "food_exhibit.db")
    app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{db_path}"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
        "pool_pre_ping": True,
        "pool_recycle": 300,
        "pool_timeout": 30,
        "pool_size": 10,
        "max_overflow": 20
    }

    # Initialize extensions with app
    db.init_app(app)
    migrate.init_app(app, db)
    socketio.init_app(app)

    # Create database directory if it doesn't exist
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    
    # Create database and tables if they don't exist
    with app.app_context():
        try:
            if not os.path.exists(db_path):
                db.create_all()
                app.logger.info("Database created successfully!")
            else:
                # Verify database connection and create tables if needed
                db.engine.connect()
                db.create_all()
                app.logger.info("Database verified and tables updated if needed!")
        except Exception as e:
            app.logger.error(f"Error initializing database: {str(e)}")

    # Initialize LoginManager
    login_manager = LoginManager()
    login_manager.login_view = "auth.login"
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        from models import User
        return User.query.get(int(user_id))

    # Register blueprints
    with app.app_context():
        from admin_routes import admin as admin_blueprint
        from exhibitor_routes import exhibitor as exhibitor_blueprint
        from auth import auth as auth_blueprint
        from chatbot_routes import register_chatbot_routes
        
        app.register_blueprint(admin_blueprint)
        app.register_blueprint(exhibitor_blueprint)
        app.register_blueprint(auth_blueprint)
        
        # Register chatbot routes
        register_chatbot_routes(app)

    # Language settings
    @app.before_request
    def before_request():
        if "language" not in session:
            session["language"] = request.accept_languages.best_match(["en", "ar", "fr"]) or "en"

    @app.context_processor
    def inject_language():
        return {"current_language": session.get("language", "en")}

    return app

# Create the app instance
app = create_app()

# Import routes AFTER app is created to avoid circular imports
import routes  # noqa: F401

def get_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # نتصل بعنوان خارجي عشان يجيب الـ IP الصحيح
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
    except Exception:
        ip = "127.0.0.1"
    finally:
        s.close()
    return ip

if __name__ == "__main__":
    host = "0.0.0.0"
    port = 5000
    print(f"\n✅ Server running at: http://{get_ip()}:{port}\n")
    socketio.run(app, host=host, port=port, debug=True)
