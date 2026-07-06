import os
from app import create_app

# Create Flask application instance
app = create_app()

if __name__ == "__main__":
    from waitress import serve
    
    port = int(os.getenv("PORT", "5000"))
    print(f"Starting production server (Waitress) on port {port}...")
    serve(app, host="0.0.0.0", port=port)
