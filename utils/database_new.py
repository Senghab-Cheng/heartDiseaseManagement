import psycopg2
import streamlit as st
import hashlib

# HELPER: Connection
def get_connection():
    try:
        return psycopg2.connect(st.secrets["db_url"])
    except Exception as e:
        st.error(f"Database Connection Error: {e}")
        return None

# ALIAS for old pages
connect_db = get_connection

def hash_password(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

def init_db():
    conn = get_connection()
    if conn:
        try:
            cur = conn.cursor()
            # USE 'SERIAL' - NEVER USE 'AUTOINCREMENT'
            cur.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id SERIAL PRIMARY KEY,
                    username TEXT UNIQUE NOT NULL,
                    password TEXT NOT NULL
                )
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS history (
                    id SERIAL PRIMARY KEY,
                    username TEXT NOT NULL,
                    prediction TEXT NOT NULL,
                    details TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.commit()
            cur.close()
            conn.close()
        except Exception as e:
            st.error(f"Error creating tables: {e}")

def create_user(username, password):
    conn = get_connection()
    if conn:
        try:
            cur = conn.cursor()
            hashed_pw = hash_password(password)
            cur.execute("INSERT INTO users (username, password) VALUES (%s, %s) RETURNING id", (username, hashed_pw))
            res = cur.fetchone()
            conn.commit()
            cur.close()
            conn.close()
            return True, res[0]
        except Exception as e:
            return False, str(e)
    return False, "No connection"

def verify_user(username, password):
    conn = get_connection()
    if conn:
        cur = conn.cursor()
        hashed_pw = hash_password(password)
        cur.execute("SELECT id FROM users WHERE username = %s AND password = %s", (username, hashed_pw))
        user = cur.fetchone()
        cur.close()
        conn.close()
        if user:
            return True, user[0]
    return False, None

def save_prediction(username, prediction, details):
    conn = get_connection()
    if conn:
        cur = conn.cursor()
        cur.execute("INSERT INTO history (username, prediction, details) VALUES (%s, %s, %s)", (username, prediction, details))
        conn.commit()
        cur.close()
        conn.close()

def get_prediction_history(user_id):
    """Fetches history for the dashboard chart specifically for Postgres/Supabase"""
    try:
        conn = get_connection()
        # Ensure we convert user_id to string to match the TEXT column type
        user_id_str = str(user_id)
        
        # We select timestamp last so it maps correctly to our DataFrame in app.py
        query = """
            SELECT predicted_target, probability, timestamp 
            FROM predictions_history 
            WHERE user_id = %s 
            ORDER BY timestamp ASC
        """
        
        # Using a standard cursor to be safe
        cur = conn.cursor()
        cur.execute(query, (user_id_str,))
        rows = cur.fetchall()
        
        cur.close()
        conn.close()
        return rows
    except Exception as e:
        print(f"Database Fetch Error: {e}")
        return []