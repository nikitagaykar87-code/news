import os

class Config:
    """Application configuration manager."""
    
    # Core API settings
    API_KEY = os.getenv("API_KEY")
    BASE_URL = "https://newsdata.io/api/1/latest"
    
    # Caching configuration
    CACHE_EXPIRY = int(os.getenv("CACHE_EXPIRY", "600"))  # 10 minutes in seconds
    CACHE_DIR = os.path.join(os.path.abspath(os.path.dirname(__file__)), ".cache")
    
    # Logging configuration
    LOG_DIR = os.path.join(os.path.abspath(os.path.dirname(__file__)), "logs")
    LOG_FILE = os.path.join(LOG_DIR, "app.log")
    
    # Server configuration
    DEBUG = os.getenv("FLASK_DEBUG", "False").lower() in ("true", "1", "yes")
    PORT = int(os.getenv("PORT", "5000"))
    
    @classmethod
    def validate_and_setup(cls):
        """Validates configuration parameters and sets up folders."""
        # Check API Key
        if not cls.API_KEY or cls.API_KEY == "placeholder" or len(cls.API_KEY.strip()) < 5:
            print("WARNING: API_KEY is missing or invalid in environment variables. Application will run strictly on mock fallbacks.")
            
        # Ensure directories exist
        os.makedirs(cls.CACHE_DIR, exist_ok=True)
        os.makedirs(cls.LOG_DIR, exist_ok=True)
