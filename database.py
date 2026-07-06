import os
import sqlite3
from werkzeug.security import generate_password_hash

DATABASE_PATH = os.path.join(os.path.abspath(os.path.dirname(__file__)), "database.db")

def get_db_connection():
    """Establishes sqlite3 connection yielding dictionary-like rows."""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Creates database tables and seeds the default administrator account."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 1. Create users table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT DEFAULT 'user',
            subscribed_status INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # 2. Create custom articles table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS articles_custom (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT NOT NULL,
            image_url TEXT,
            category TEXT,
            pubDate TEXT,
            link TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    conn.commit()
    
    # 3. Seed default admin if missing
    cursor.execute("SELECT * FROM users WHERE email = 'admin@dailynews.com'")
    if not cursor.fetchone():
        admin_pass_hash = generate_password_hash("admin123")
        cursor.execute("""
            INSERT INTO users (name, email, password_hash, role, subscribed_status)
            VALUES (?, ?, ?, ?, ?)
        """, ("System Admin", "admin@dailynews.com", admin_pass_hash, "admin", 1))
        conn.commit()
        print("Database seeded: Default Administrator registered successfully (admin@dailynews.com / admin123).")
        
    conn.close()

# ==========================================================================
# USER OPERATIONS HELPERS
# ==========================================================================
def create_user(name, email, password):
    """Registers a new user in the database. Returns user row or None if email exists."""
    conn = get_db_connection()
    cursor = conn.cursor()
    pass_hash = generate_password_hash(password)
    try:
        cursor.execute("""
            INSERT INTO users (name, email, password_hash, role, subscribed_status)
            VALUES (?, ?, ?, ?, ?)
        """, (name, email, pass_hash, "user", 0))
        conn.commit()
        user_id = cursor.lastrowid
        cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        user = cursor.fetchone()
        return dict(user) if user else None
    except sqlite3.IntegrityError:
        return None  # Email duplication
    finally:
        conn.close()

def get_user_by_email(email):
    """Retrieves user details by email address."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
    user = cursor.fetchone()
    conn.close()
    return dict(user) if user else None

def get_user_by_id(user_id):
    """Retrieves user details by numeric ID."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    user = cursor.fetchone()
    conn.close()
    return dict(user) if user else None

def toggle_subscription(user_id):
    """Toggles active subscription state for a user."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT subscribed_status FROM users WHERE id = ?", (user_id,))
    row = cursor.fetchone()
    if row:
        new_val = 1 if row["subscribed_status"] == 0 else 0
        cursor.execute("UPDATE users SET subscribed_status = ? WHERE id = ?", (new_val, user_id))
        conn.commit()
    conn.close()

def toggle_role(user_id):
    """Toggles administrator / user roles."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT role FROM users WHERE id = ?", (user_id,))
    row = cursor.fetchone()
    if row:
        new_role = "admin" if row["role"] == "user" else "user"
        cursor.execute("UPDATE users SET role = ? WHERE id = ?", (new_role, user_id))
        conn.commit()
    conn.close()

def get_all_users():
    """Lists all registered users in descending order of creation."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users ORDER BY created_at DESC")
    rows = cursor.fetchall()
    users = [dict(r) for r in rows]
    conn.close()
    return users

# ==========================================================================
# CUSTOM ARTICLES HELPERS
# ==========================================================================
def add_custom_article(title, description, image_url, category, link=None):
    """Inserts a custom news article created in the admin panel."""
    import datetime
    conn = get_db_connection()
    cursor = conn.cursor()
    pub_date = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    target_link = link if link else "#"
    cursor.execute("""
        INSERT INTO articles_custom (title, description, image_url, category, pubDate, link)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (title, description, image_url, category, pub_date, target_link))
    conn.commit()
    conn.close()

def get_custom_articles(category=None, search=None):
    """Fetches custom articles, applying optional category and search filters."""
    conn = get_db_connection()
    cursor = conn.cursor()
    query = "SELECT * FROM articles_custom WHERE 1=1"
    params = []
    
    if category:
        query += " AND LOWER(category) = ?"
        params.append(category.lower())
    if search:
        query += " AND (LOWER(title) LIKE ? OR LOWER(description) LIKE ?)"
        search_param = f"%{search.lower()}%"
        params.extend([search_param, search_param])
        
    query += " ORDER BY created_at DESC"
    cursor.execute(query, params)
    rows = cursor.fetchall()
    articles = []
    for r in rows:
        d = dict(r)
        # Ensure category is formatted as a list of strings
        d["category"] = [d["category"]] if d["category"] else ["General"]
        articles.append(d)
    conn.close()
    return articles

def delete_custom_article(article_id):
    """Deletes a custom article by ID."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM articles_custom WHERE id = ?", (article_id,))
    conn.commit()
    conn.close()

# ==========================================================================
# STATS GATHERER
# ==========================================================================
def get_db_stats():
    """Gathers summary statistics for the admin dashboard."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 1. Total users
    cursor.execute("SELECT COUNT(*) FROM users")
    total_users = cursor.fetchone()[0]
    
    # 2. Total subscribers
    cursor.execute("SELECT COUNT(*) FROM users WHERE subscribed_status = 1")
    total_subscribers = cursor.fetchone()[0]
    
    # 3. Total custom articles
    cursor.execute("SELECT COUNT(*) FROM articles_custom")
    total_custom_articles = cursor.fetchone()[0]
    
    conn.close()
    return {
        "total_users": total_users,
        "total_subscribers": total_subscribers,
        "total_custom_articles": total_custom_articles
    }
