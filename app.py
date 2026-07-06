import logging
from logging.handlers import RotatingFileHandler
from flask import Flask, render_template
from dotenv import load_dotenv

# Load env file variables
load_dotenv()

from config import Config
from routes import news_bp
from database import init_db

# Set up Config and validate directories
Config.validate_and_setup()

# Setup SQLite Database tables and admin seeding
init_db()

# ==========================================================================
# LOGGING SETUP (ROTATING FILES AND CONSOLE)
# ==========================================================================
def configure_logging(app):
    """Sets up rolling log files and standard output streams."""
    log_formatter = logging.Formatter(
        "[%(asctime)s] %(levelname)s in %(module)s [%(pathname)s:%(lineno)d]: %(message)s"
    )
    
    # 1. Rolling file handler (1MB cap, keeping 5 backup logs)
    file_handler = RotatingFileHandler(
        Config.LOG_FILE, maxBytes=1024 * 1024, backupCount=5, encoding="utf-8"
    )
    file_handler.setFormatter(log_formatter)
    file_handler.setLevel(logging.INFO)
    
    # 2. Console stream handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(log_formatter)
    console_handler.setLevel(logging.INFO)
    
    # Attach handlers to root logger so all files can use logging
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)
    
    app.logger.info("Logging infrastructure successfully configured.")

# ==========================================================================
# APP FACTORY INITIALIZER
# ==========================================================================
def create_app():
    """Initializes the Flask application with blueprinted routes and errors."""
    app = Flask(__name__)
    
    # Set config parameters
    app.config.from_object(Config)
    
    # Secure session parameters using environment variable with fallback
    import os
    app.secret_key = os.getenv("SECRET_KEY", "dailynews_secret_key_1298457")
    
    # Enhance Cookie security settings
    app.config.update(
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE='Lax',
    )
    
    # Configure logs
    configure_logging(app)
    
    # Register blueprints
    app.register_blueprint(news_bp)
    
    # Register error code routing
    register_error_handlers(app)
    
    return app

# ==========================================================================
# ERROR CODE HANDLERS
# ==========================================================================
def register_error_handlers(app):
    """Binds handlers for standard HTTP error statuses."""
    
    @app.errorhandler(404)
    def page_not_found(error):
        app.logger.warning(f"404 Warning triggered: {error}")
        return render_template("404.html"), 404

    @app.errorhandler(500)
    def internal_server_error(error):
        app.logger.error(f"500 Internal Error triggered: {error}")
        return render_template("500.html"), 500

app = create_app()

if __name__ == "__main__":
    app.logger.info(f"Starting server on port {Config.PORT} (Debug={Config.DEBUG})...")
    app.run(debug=Config.DEBUG, port=Config.PORT)