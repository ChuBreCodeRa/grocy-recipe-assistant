import os
import psycopg2
import logging

logger = logging.getLogger(__name__)

DB_NAME = os.getenv("POSTGRES_DB", "grocy_assistant")
DB_USER = os.getenv("POSTGRES_USER", "grocy_user")
DB_PASSWORD = os.getenv("POSTGRES_PASSWORD", "grocy_pass")
DB_HOST = os.getenv("POSTGRES_HOST", "db")
DB_PORT = os.getenv("POSTGRES_PORT", "5432")

def get_db_connection():
    return psycopg2.connect(
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        host=DB_HOST,
        port=DB_PORT
    )

def init_db():
    conn = get_db_connection()
    cur = conn.cursor()
    # Users table
    cur.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,
            created_at TIMESTAMP DEFAULT NOW()
        )
    ''')
    # User preferences table
    cur.execute('''
        CREATE TABLE IF NOT EXISTS user_preferences (
            user_id TEXT PRIMARY KEY REFERENCES users(id),
            liked_ingredients JSON,
            disliked_ingredients JSON,
            taste_profile JSON, -- Added: Stores avg numeric taste profile
            effort_tolerance TEXT,
            preferred_dish_types JSON,
            dietary_restrictions JSON, -- Added: Stores dietary restrictions
            last_updated TIMESTAMP
        )
    ''')
    
    # --- Add ALTER TABLE statement here ---
    # Add the dietary_restrictions column if it doesn't exist (for backward compatibility)
    try:
        cur.execute("ALTER TABLE user_preferences ADD COLUMN IF NOT EXISTS dietary_restrictions JSON")
        logger.info("Ensured 'dietary_restrictions' column exists in 'user_preferences' table.")
    except Exception as e:
        # Log potential errors but don't crash startup if ALTER fails (e.g., permissions)
        logger.error(f"Could not ensure 'dietary_restrictions' column exists: {e}")
        conn.rollback() # Rollback the failed ALTER attempt
    # --- End of addition ---
    
    # Inventory table (minimal for MVP)
    cur.execute('''
        CREATE TABLE IF NOT EXISTS inventory (
            product_id INTEGER PRIMARY KEY,
            name TEXT,
            amount INTEGER,
            best_before_date DATE,
            last_updated TIMESTAMP DEFAULT NOW()
        )
    ''')
    # Inventory sync metadata table
    cur.execute('''
        CREATE TABLE IF NOT EXISTS inventory_sync_metadata (
            id SERIAL PRIMARY KEY,
            last_changed_time TIMESTAMP
        )
    ''')
    # User ratings table for feedback
    cur.execute('''
        CREATE TABLE IF NOT EXISTS user_ratings (
            id SERIAL PRIMARY KEY,
            user_id TEXT,
            recipe_id TEXT,
            rating INTEGER,
            review_text TEXT,
            effort_tag TEXT,
            sentiment TEXT,
            sweetness INTEGER,
            saltiness INTEGER,
            sourness INTEGER,
            bitterness INTEGER,
            savoriness INTEGER,
            fattiness INTEGER,
            timestamp TIMESTAMP DEFAULT NOW()
        )
    ''')
    
    # Create default users if they don't exist
    create_default_users(cur)
    
    conn.commit()
    cur.close()
    conn.close()

def create_user(user_id, default_preferences=None):
    """
    Create a new user in the system with optional default preferences.
    
    Args:
        user_id: Unique identifier for the user
        default_preferences: Optional dictionary with initial preference values
        
    Returns:
        bool: True if user was created, False if user already exists
    """
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Check if user already exists
        cur.execute("SELECT id FROM users WHERE id = %s", (user_id,))
        if cur.fetchone():
            logger.info(f"User '{user_id}' already exists")
            return False
            
        # Create the user
        cur.execute("INSERT INTO users (id) VALUES (%s)", (user_id,))
        
        # Set default preferences if provided
        if default_preferences:
            # Extract preference values
            taste_profile = default_preferences.get('taste_profile', {})
            effort_tolerance = default_preferences.get('effort_tolerance', 'moderate')
            liked_ingredients = default_preferences.get('liked_ingredients', [])
            disliked_ingredients = default_preferences.get('disliked_ingredients', [])
            preferred_dish_types = default_preferences.get('preferred_dish_types', [])
            dietary_restrictions = default_preferences.get('dietary_restrictions', {})
            
            # Set initial preferences
            import json
            from datetime import datetime
            cur.execute("""
                INSERT INTO user_preferences 
                (user_id, taste_profile, effort_tolerance, liked_ingredients, 
                disliked_ingredients, preferred_dish_types, dietary_restrictions, last_updated)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                user_id, 
                json.dumps(taste_profile), 
                effort_tolerance,
                json.dumps(liked_ingredients),
                json.dumps(disliked_ingredients),
                json.dumps(preferred_dish_types),
                json.dumps(dietary_restrictions),
                datetime.now()
            ))
        
        conn.commit()
        logger.info(f"Created new user '{user_id}'")
        return True
        
    except Exception as e:
        logger.error(f"Error creating user: {e}")
        if conn:
            conn.rollback()
        return False
        
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

def create_default_users(cur):
    """Create default users during initialization if they don't exist."""
    import json
    from datetime import datetime
    
    # Check if users already exist
    cur.execute("SELECT COUNT(*) FROM users")
    user_count = cur.fetchone()[0]
    
    if user_count == 0:
        # Create default users
        default_users = ['alyssa', 'brendan']
        for user_id in default_users:
            # Insert user
            cur.execute("INSERT INTO users (id) VALUES (%s)", (user_id,))
            
            # Set default preferences
            default_taste = {
                "sweetness": 50,
                "saltiness": 50,
                "sourness": 50,
                "bitterness": 20,
                "savoriness": 70,
                "fattiness": 50
            }
            
            # Different default effort levels
            effort = "easy" if user_id == "alyssa" else "moderate"
            
            # --- Remove default dietary restrictions --- 
            # Set dietary restrictions to empty for all default users
            dietary_restrictions = {}
            # --- End of change ---
            
            # Insert preferences
            cur.execute("""
                INSERT INTO user_preferences 
                (user_id, taste_profile, effort_tolerance, liked_ingredients, 
                disliked_ingredients, preferred_dish_types, dietary_restrictions, last_updated)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                user_id,
                json.dumps(default_taste),
                effort,
                json.dumps([]),  # liked_ingredients
                json.dumps([]),  # disliked_ingredients
                json.dumps([]),  # preferred_dish_types
                json.dumps(dietary_restrictions),  # Use the now empty dietary restrictions
                datetime.now()
            ))
            
        logger.info(f"Created {len(default_users)} default users during initialization")
