import os
from flask import Blueprint, render_template, request, session, redirect, url_for, jsonify
from werkzeug.security import check_password_hash
from services.news_service import get_news
from config import Config
import database

# Define the modular Blueprint for routes
news_bp = Blueprint("news", __name__)

@news_bp.route("/")
def home():
    """Renders the Daily News homepage with category filtering, keyword searches, language, and country filters."""
    category = request.args.get("category")
    search = request.args.get("search")
    
    # 1. Resolve Language setting
    lang = request.args.get("lang")
    if lang:
        session["lang"] = lang
    else:
        lang = session.get("lang", "en")

    # 2. Resolve Country locale (Defaulting to 'us,in' to mix Indian and global newspapers by default)
    country = request.args.get("country")
    if country:
        if country.lower() == "global":
            session["country"] = "global"
            api_country = "us,in"
        else:
            session["country"] = country
            api_country = country
    else:
        session_country = session.get("country", "us,in")
        if session_country == "global":
            api_country = "us,in"
            country = "global"
        else:
            api_country = session_country
            country = session_country

    # 3. Fetch news articles and verify count
    articles, results_count = get_news(
        category=category,
        country=api_country,
        search=search,
        language=lang
    )

    # 4. Sync user details
    user_id = session.get("user_id")
    user = None
    if user_id:
        user = database.get_user_by_id(user_id)
        if user:
            session["user_role"] = user["role"]
            session["subscribed"] = user["subscribed_status"]

    return render_template(
        "index.html",
        articles=articles,
        search=search,
        category=category,
        country=country,
        lang=lang,
        results_count=results_count,
        user=user
    )

# ==========================================================================
# AUTHENTICATION ENDPOINTS
# ==========================================================================
@news_bp.route("/register", methods=["POST"])
def register():
    """Registers a new user account."""
    data = request.get_json() or {}
    name = data.get("name", "").strip()
    email = data.get("email", "").strip()
    password = data.get("password", "").strip()

    if not name or not email or not password:
        return jsonify({"success": False, "message": "All fields are required."}), 400

    user = database.create_user(name, email, password)
    if user:
        # Establish session keys on registration success
        session["user_id"] = user["id"]
        session["user_name"] = user["name"]
        session["user_email"] = user["email"]
        session["user_role"] = user["role"]
        session["subscribed"] = user["subscribed_status"]
        return jsonify({"success": True, "message": f"Welcome, {name}!"})
    
    return jsonify({"success": False, "message": "Email is already registered."}), 400

@news_bp.route("/login", methods=["POST"])
def login():
    """Authenticates existing user credentials."""
    data = request.get_json() or {}
    email = data.get("email", "").strip()
    password = data.get("password", "").strip()

    if not email or not password:
        return jsonify({"success": False, "message": "Email and password are required."}), 400

    user = database.get_user_by_email(email)
    if user and check_password_hash(user["password_hash"], password):
        # Establish session keys on authentication success
        session["user_id"] = user["id"]
        session["user_name"] = user["name"]
        session["user_email"] = user["email"]
        session["user_role"] = user["role"]
        session["subscribed"] = user["subscribed_status"]
        return jsonify({"success": True, "message": f"Welcome back, {user['name']}!"})

    return jsonify({"success": False, "message": "Invalid email or password."}), 400

@news_bp.route("/logout")
def logout():
    """Clears user session credentials and returns home."""
    session.clear()
    return redirect(url_for("news.home"))

@news_bp.route("/subscribe", methods=["POST"])
def subscribe():
    """Subscribes the active user."""
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"success": False, "message": "Please sign in to subscribe."}), 401

    database.toggle_subscription(user_id)
    # Re-sync active session state
    user = database.get_user_by_id(user_id)
    if user:
        session["subscribed"] = user["subscribed_status"]
        return jsonify({
            "success": True, 
            "subscribed": user["subscribed_status"],
            "message": "Subscription updated successfully!"
        })
        
    return jsonify({"success": False, "message": "User not found."}), 404

# ==========================================================================
# ADMIN DASHBOARD & CONTROLLERS
# ==========================================================================
@news_bp.route("/admin")
def admin_dashboard():
    """Renders the administrator panel."""
    # Ensure active session belongs to an admin
    if session.get("user_role") != "admin":
        return redirect(url_for("news.home"))

    # Load statistics
    stats = database.get_db_stats()
    
    # Load folders count
    try:
        cache_files = len([f for f in os.listdir(Config.CACHE_DIR) if f.endswith(".json")])
    except Exception:
        cache_files = 0
    stats["total_cache_files"] = cache_files

    # Load users details
    users = database.get_all_users()
    
    # Load custom news list
    custom_articles = database.get_custom_articles()

    # Load logs contents (last 50 lines)
    log_lines = []
    if os.path.exists(Config.LOG_FILE):
        try:
            with open(Config.LOG_FILE, "r", encoding="utf-8") as f:
                log_lines = f.readlines()[-50:]
        except Exception as e:
            log_lines = [f"Failed to read logs: {e}"]
    else:
        log_lines = ["Log file app.log does not exist yet."]
    log_content = "".join(log_lines)

    return render_template(
        "admin.html",
        stats=stats,
        users=users,
        custom_articles=custom_articles,
        log_content=log_content
    )

@news_bp.route("/admin/article/add", methods=["POST"])
def admin_add_article():
    """Creates a custom article in the SQLite database."""
    if session.get("user_role") != "admin":
        return jsonify({"success": False, "message": "Unauthorized access."}), 403

    data = request.get_json() or {}
    title = data.get("title", "").strip()
    description = data.get("description", "").strip()
    image_url = data.get("image_url", "").strip()
    category = data.get("category", "General").strip()
    link = data.get("link", "").strip()

    if not title or not description:
        return jsonify({"success": False, "message": "Title and description are required."}), 400

    database.add_custom_article(title, description, image_url, category, link)
    return jsonify({"success": True, "message": "Custom article published successfully!"})

@news_bp.route("/admin/article/delete/<int:article_id>", methods=["POST"])
def admin_delete_article(article_id):
    """Deletes custom article records from database."""
    if session.get("user_role") != "admin":
        return jsonify({"success": False, "message": "Unauthorized access."}), 403

    database.delete_custom_article(article_id)
    return jsonify({"success": True, "message": "Article deleted successfully."})

@news_bp.route("/admin/cache/clear", methods=["POST"])
def admin_clear_cache():
    """Removes cached response files from server."""
    if session.get("user_role") != "admin":
        return jsonify({"success": False, "message": "Unauthorized access."}), 403

    cleared_count = 0
    try:
        for f in os.listdir(Config.CACHE_DIR):
            if f.endswith(".json"):
                os.remove(os.path.join(Config.CACHE_DIR, f))
                cleared_count += 1
        return jsonify({"success": True, "message": f"Successfully cleared cache! ({cleared_count} files removed)"})
    except Exception as e:
        return jsonify({"success": False, "message": f"Error clearing cache directory: {e}"}), 500

@news_bp.route("/admin/user/toggle/<int:user_id>", methods=["POST"])
def admin_toggle_user(user_id):
    """Toggles user status parameters (role / subscription)."""
    if session.get("user_role") != "admin":
        return jsonify({"success": False, "message": "Unauthorized access."}), 403

    action = request.args.get("action")
    if action == "role":
        # Prevent self-demotion from admin
        if user_id == session.get("user_id"):
            return jsonify({"success": False, "message": "Self-demotion is not allowed."}), 400
        database.toggle_role(user_id)
        return jsonify({"success": True, "message": "User role toggled successfully."})
    elif action == "subscription":
        database.toggle_subscription(user_id)
        return jsonify({"success": True, "message": "User subscription toggled successfully."})
    
    return jsonify({"success": False, "message": "Invalid action parameter."}), 400
