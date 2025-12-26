import sqlite3
import os
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv
from datetime import datetime
import pandas as pd

# Load environment variables
load_dotenv()

def get_connection():
    """Get database connection - tries PostgreSQL first, falls back to SQLite"""
    try:
        # Try PostgreSQL first
        conn = psycopg2.connect(
            host=os.getenv('DB_HOST', 'localhost'),
            database=os.getenv('DB_NAME', 'heart_disease'),
            user=os.getenv('DB_USER', 'postgres'),
            password=os.getenv('DB_PASSWORD', 'password'),
            port=os.getenv('DB_PORT', '5432')
        )
        print("Connected to PostgreSQL")
        return conn
    except Exception as e:
        print(f"PostgreSQL connection failed: {e}, falling back to SQLite")
        # Fallback to SQLite
        try:
            conn = sqlite3.connect('Heart_Disease_Manager.db')
            print("Connected to SQLite")
            return conn
        except Exception as e2:
            print(f"SQLite connection also failed: {e2}")
            return None

def init_db():
    """Initialize SQLite database for local user data"""
    try:
        print("Initializing database...")
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
                      user_id TEXT NOT NULL,
                      systolic INTEGER NOT NULL,
                      diastolic INTEGER NOT NULL,
                      heart_rate INTEGER,
                      timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                      notes TEXT)''')

        # Create activities table
        c.execute('''CREATE TABLE IF NOT EXISTS activities
                     (id INTEGER PRIMARY KEY AUTOINCREMENT,
                      user_id TEXT NOT NULL,
                      activity_type TEXT NOT NULL,
                      duration INTEGER NOT NULL,
                      intensity TEXT DEFAULT 'Moderate',
                      calories INTEGER,
                      timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                      notes TEXT)''')

        # Create predictions_history table
        c.execute('''CREATE TABLE IF NOT EXISTS predictions_history
                     (id INTEGER PRIMARY KEY AUTOINCREMENT,
                      user_id TEXT NOT NULL,
                      age INTEGER,
                      cholesterol INTEGER,
                      resting_bp_s INTEGER,
                      predicted_target INTEGER,
                      probability REAL,
                      timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')

        # Create chat_history table for health assistant
        c.execute('''CREATE TABLE IF NOT EXISTS chat_history
                     (id INTEGER PRIMARY KEY AUTOINCREMENT,
                      user_id TEXT NOT NULL,
                      role TEXT NOT NULL,
                      message TEXT NOT NULL,
                      timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')

        # Create cholesterol_readings table
        c.execute('''CREATE TABLE IF NOT EXISTS cholesterol_readings
                     (id INTEGER PRIMARY KEY AUTOINCREMENT,
                      user_id TEXT NOT NULL,
                      total_cholesterol INTEGER,
                      ldl INTEGER,
                      hdl INTEGER,
                      triglycerides INTEGER,
                      timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                      notes TEXT)''')

        conn.commit()
        conn.close()
        print("Database initialized successfully")
    except Exception as e:
        print(f"Error initializing database: {e}")
        import traceback
        traceback.print_exc()

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

def save_blood_pressure(user_id, systolic, diastolic, heart_rate=None, notes=''):
    """Save blood pressure reading - works with both SQLite and PostgreSQL"""
    try:
        print(f"Attempting to save BP: {systolic}/{diastolic} for user {user_id}")
        conn = get_connection()
        if conn is None:
            print("Database connection failed")
            return False

        if isinstance(conn, sqlite3.Connection):
            # SQLite
            print("Using SQLite for BP save")
            c = conn.cursor()
            c.execute("INSERT INTO blood_pressure (user_id, systolic, diastolic, heart_rate, timestamp, notes) VALUES (?, ?, ?, ?, ?, ?)",
                      (str(user_id), systolic, diastolic, heart_rate, datetime.now(), notes))
            conn.commit()
            conn.close()
            print("BP saved successfully to SQLite")
        else:
            # PostgreSQL
            print("Using PostgreSQL for BP save")
            c = conn.cursor()
            # Add 'timestamp' to the columns and 'now()' to the values
            c.execute("""
                INSERT INTO blood_pressure (user_id, systolic, diastolic, heart_rate, notes, timestamp) 
                VALUES (%s, %s, %s, %s, %s, NOW())
            """, (str(user_id), systolic, diastolic, heart_rate, notes))
            conn.commit()
            conn.close()
            print("BP saved successfully to PostgreSQL")
        return True
    except Exception as e:
        print(f"Error saving blood pressure: {e}")
        import traceback
        traceback.print_exc()
        return False

def save_activity(user_id, activity_type, duration, intensity, calories=None, notes=''):
    """Save activity data - works with both SQLite and PostgreSQL"""
    try:
        if calories is None:
            mult = {'Light': 3, 'Moderate': 5, 'Vigorous': 8}
            calories = duration * mult.get(intensity, 5)

        conn = get_connection()
        if isinstance(conn, sqlite3.Connection):
            # SQLite
            c = conn.cursor()
            c.execute("INSERT INTO activities (user_id, activity_type, duration, intensity, calories, timestamp, notes) VALUES (?, ?, ?, ?, ?, ?, ?)",
                      (str(user_id), activity_type, duration, intensity, calories, datetime.now(), notes))
            conn.commit()
            conn.close()
        else:
            # PostgreSQL
            c = conn.cursor()
            c.execute("INSERT INTO activities (user_id, activity_type, duration, intensity, calories, notes) VALUES (%s, %s, %s, %s, %s, %s)",
                      (str(user_id), activity_type, duration, intensity, calories, notes))
            conn.commit()
            conn.close()
        return True
    except Exception as e:
        print(f"Error saving activity: {e}")
        return False

def save_cholesterol(user_id, total_chol=None, ldl=None, hdl=None, triglycerides=None, notes=''):
    """Save cholesterol reading - works with both SQLite and PostgreSQL"""
    try:
        conn = get_connection()
        if isinstance(conn, sqlite3.Connection):
            # SQLite - need to create table first if it doesn't exist
            c = conn.cursor()
            c.execute('''CREATE TABLE IF NOT EXISTS cholesterol_readings
                         (id INTEGER PRIMARY KEY AUTOINCREMENT,
                          user_id TEXT NOT NULL,
                          total_cholesterol INTEGER,
                          ldl INTEGER,
                          hdl INTEGER,
                          triglycerides INTEGER,
                          timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                          notes TEXT)''')
            c.execute("INSERT INTO cholesterol_readings (user_id, total_cholesterol, ldl, hdl, triglycerides, timestamp, notes) VALUES (?, ?, ?, ?, ?, ?, ?)",
                      (str(user_id), total_chol, ldl, hdl, triglycerides, datetime.now(), notes))
            conn.commit()
            conn.close()
        else:
            # PostgreSQL
            c = conn.cursor()
            c.execute("INSERT INTO cholesterol_readings (user_id, total_cholesterol, ldl, hdl, triglycerides, notes) VALUES (%s, %s, %s, %s, %s, %s)",
                      (str(user_id), total_chol, ldl, hdl, triglycerides, notes))
            conn.commit()
            conn.close()
        return True
    except Exception as e:
        print(f"Error saving cholesterol: {e}")
        return False

def save_chat_message(user_id, role, message):
    """Save chat message - works with both SQLite and PostgreSQL"""
    try:
        conn = get_connection()
        if isinstance(conn, sqlite3.Connection):
            # SQLite
            c = conn.cursor()
            c.execute("INSERT INTO chat_history (user_id, role, message, timestamp) VALUES (?, ?, ?, ?)",
                      (str(user_id), role, message, datetime.now()))
            conn.commit()
            conn.close()
        else:
            # PostgreSQL
            c = conn.cursor()
            c.execute("INSERT INTO chat_history (user_id, role, message) VALUES (%s, %s, %s)",
                      (str(user_id), role, message))
            conn.commit()
            conn.close()
    except Exception as e:
        print(f"Error saving chat message: {e}")

def get_weekly_bp_summary(user_id):
    """Get weekly blood pressure summary - works with both databases"""
    try:
        conn = get_connection()
        if isinstance(conn, sqlite3.Connection):
            # SQLite - use datetime function
            query = """
                SELECT AVG(systolic) as systolic_avg, AVG(diastolic) as diastolic_avg
                FROM blood_pressure
                WHERE user_id = ? AND timestamp >= datetime('now', '-7 days')
            """
            df = pd.read_sql_query(query, conn, params=(str(user_id),))
        else:
            # PostgreSQL
            query = """
                SELECT AVG(systolic) as systolic_avg, AVG(diastolic) as diastolic_avg
                FROM blood_pressure
                WHERE user_id = %s AND timestamp >= CURRENT_TIMESTAMP - INTERVAL '7 days'
            """
            df = pd.read_sql_query(query, conn, params=(str(user_id),))

        conn.close()
        return df
    except Exception as e:
        print(f"Error getting BP summary: {e}")
        return pd.DataFrame()

def load_chat_history(user_id, limit=20):
    """Load chat history - works with both databases"""
    try:
        conn = get_connection()
        if isinstance(conn, sqlite3.Connection):
            # SQLite
            query = "SELECT role, message as content FROM chat_history WHERE user_id = ? ORDER BY timestamp ASC LIMIT ?"
            df = pd.read_sql_query(query, conn, params=(str(user_id), limit))
        else:
            # PostgreSQL
            query = "SELECT role, message as content FROM chat_history WHERE user_id = %s ORDER BY timestamp ASC LIMIT %s"
            df = pd.read_sql_query(query, conn, params=(str(user_id), limit))

        conn.close()
        return df
    except Exception as e:
        print(f"Error loading chat history: {e}")
        return pd.DataFrame()

def get_prediction_history(user_id):
    """Get prediction history - returns data in format expected by app.py"""
    try:
        conn = get_connection()
        if isinstance(conn, sqlite3.Connection):
            # SQLite
            query = "SELECT predicted_target, probability, timestamp FROM predictions_history WHERE user_id = ? ORDER BY timestamp DESC"
            df = pd.read_sql_query(query, conn, params=(str(user_id),))
        else:
            # PostgreSQL
            query = "SELECT predicted_target, probability, timestamp FROM predictions_history WHERE user_id = %s ORDER BY timestamp DESC"
            df = pd.read_sql_query(query, conn, params=(str(user_id),))

        conn.close()
        # Return as list of tuples for compatibility with existing app.py code
        if not df.empty:
            return list(df.itertuples(index=False, name=None))
        return []
    except Exception as e:
        print(f"Error getting prediction history: {e}")
        return []

def log_prediction_to_db(user_id, age, chol, bp, target, prob):
    """Save prediction to database - works with both SQLite and PostgreSQL"""
    try:
        conn = get_connection()
        if isinstance(conn, sqlite3.Connection):
            # SQLite
            c = conn.cursor()
            c.execute("INSERT INTO predictions_history (user_id, age, cholesterol, resting_bp_s, predicted_target, probability, timestamp) VALUES (?, ?, ?, ?, ?, ?, ?)",
                      (str(user_id), age, chol, bp, target, prob, datetime.now()))
            conn.commit()
            conn.close()
        else:
            # PostgreSQL
            c = conn.cursor()
            c.execute("INSERT INTO predictions_history (user_id, age, cholesterol, resting_bp_s, predicted_target, probability) VALUES (%s, %s, %s, %s, %s, %s)",
                      (str(user_id), age, chol, bp, target, prob))
            conn.commit()
            conn.close()
        return True
    except Exception as e:
        print(f"Error saving prediction: {e}")
        return False