import sqlite3
import os
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def get_connection():
    """Get PostgreSQL connection for shared data"""
    try:
        # Default to local PostgreSQL if no env vars
        conn = psycopg2.connect(
            host=os.getenv('DB_HOST', 'localhost'),
            database=os.getenv('DB_NAME', 'heart_disease'),
            user=os.getenv('DB_USER', 'postgres'),
            password=os.getenv('DB_PASSWORD', 'password'),
            port=os.getenv('DB_PORT', '5432')
        )
        return conn
    except Exception as e:
        print(f"Database connection error: {e}")
        # Fallback to SQLite if PostgreSQL fails
        return sqlite3.connect('Heart_Disease_Manager.db')

def init_db():
    """Initialize SQLite database for local user data"""
    conn = sqlite3.connect('Heart_Disease_Manager.db')
    c = conn.cursor()

    # Create users table
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  username TEXT UNIQUE NOT NULL,
                  password TEXT NOT NULL,
                  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')

    # Create blood_pressure table
    c.execute('''CREATE TABLE IF NOT EXISTS blood_pressure
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  user_id INTEGER NOT NULL,
                  systolic INTEGER NOT NULL,
                  diastolic INTEGER NOT NULL,
                  timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                  FOREIGN KEY (user_id) REFERENCES users (id))''')

    # Create activities table
    c.execute('''CREATE TABLE IF NOT EXISTS activities
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  user_id INTEGER NOT NULL,
                  activity_type TEXT NOT NULL,
                  duration INTEGER NOT NULL,
                  calories INTEGER,
                  timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                  FOREIGN KEY (user_id) REFERENCES users (id))''')

    conn.commit()
    conn.close()

def verify_user(username, password):
    """Verify user credentials"""
    try:
        conn = sqlite3.connect('Heart_Disease_Manager.db')
        c = conn.cursor()
        c.execute("SELECT id FROM users WHERE username = ? AND password = ?",
                  (username, password))
        result = c.fetchone()
        conn.close()
        if result:
            return True, result[0]
        return False, None
    except Exception as e:
        print(f"Error verifying user: {e}")
        return False, None

def create_user(username, password):
    """Create new user"""
    try:
        conn = sqlite3.connect('Heart_Disease_Manager.db')
        c = conn.cursor()
        c.execute("INSERT INTO users (username, password) VALUES (?, ?)",
                  (username, password))
        user_id = c.lastrowid
        conn.commit()
        conn.close()
        return True, user_id
    except sqlite3.IntegrityError:
        return False, "Username already exists"
    except Exception as e:
        print(f"Error creating user: {e}")
        return False, str(e)

def get_prediction_history(user_id):
    """Get prediction history from PostgreSQL"""
    try:
        conn = get_connection()
        if isinstance(conn, sqlite3.Connection):
            # Fallback to SQLite if PostgreSQL not available
            c = conn.cursor()
            c.execute("SELECT * FROM predictions_history WHERE user_id = ? ORDER BY timestamp DESC",
                      (str(user_id),))
            results = c.fetchall()
            conn.close()
            return results
        else:
            # PostgreSQL
            c = conn.cursor(cursor_factory=RealDictCursor)
            c.execute("SELECT * FROM predictions_history WHERE user_id = %s ORDER BY timestamp DESC",
                      (str(user_id),))
            results = c.fetchall()
            conn.close()
            return results
    except Exception as e:
        print(f"Error getting prediction history: {e}")
        return []