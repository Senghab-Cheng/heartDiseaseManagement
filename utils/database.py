import psycopg2
import streamlit as st
import hashlib
import os

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
            # USE 'SERIAL' for PostgreSQL
            cur.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id SERIAL PRIMARY KEY,
                    username TEXT UNIQUE NOT NULL,
                    password TEXT NOT NULL
                )
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS blood_pressure (
                    id SERIAL PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    systolic INTEGER NOT NULL,
                    diastolic INTEGER NOT NULL,
                    heart_rate INTEGER,
                    notes TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS activities (
                    id SERIAL PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    activity_type TEXT NOT NULL,
                    duration REAL NOT NULL,
                    intensity TEXT NOT NULL,
                    calories REAL NOT NULL,
                    notes TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS predictions_history (
                    id SERIAL PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    age INTEGER,
                    cholesterol INTEGER,
                    resting_bp_s INTEGER,
                    predicted_target INTEGER,
                    probability REAL,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS chat_history (
                    id SERIAL PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    message TEXT NOT NULL,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS cholesterol_readings (
                    id SERIAL PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    total_cholesterol INTEGER,
                    ldl INTEGER,
                    hdl INTEGER,
                    triglycerides INTEGER,
                    notes TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.commit()
            cur.close()
            conn.close()
            print("Database tables initialized successfully")
        except Exception as e:
            print(f"Error creating tables: {e}")
            st.error(f"Error creating tables: {e}")

def create_user(username, password):
    conn = get_connection()
    if conn:
        try:
            cur = conn.cursor()
            hashed_pw = hash_password(password)
            cur.execute("INSERT INTO users (username, password) VALUES (%s, %s) RETURNING id", (username, hashed_pw))
            user_id = cur.fetchone()[0]
            conn.commit()
            cur.close()
            conn.close()
            return True, user_id
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

def get_activity_data(user_id, limit=None):
    try:
        conn = get_connection()
        if conn:
            import pandas as pd
            query = "SELECT * FROM activities WHERE user_id = %s ORDER BY timestamp DESC"
            if limit:
                query += f" LIMIT {limit}"
            df = pd.read_sql_query(query, conn, params=(str(user_id),))
            conn.close()
            if not df.empty:
                df['timestamp'] = pd.to_datetime(df['timestamp'], utc=True).dt.tz_localize(None)
            return df
    except Exception:
        pass
    return pd.DataFrame()

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

def save_blood_pressure(user_id, systolic, diastolic, heart_rate=None, notes=None):
    if not user_id:
        print("Error: user_id is None or empty")
        return False
    
    if systolic is None or diastolic is None:
        print(f"Error: systolic or diastolic is None. systolic={systolic}, diastolic={diastolic}")
        return False
    
    try:
        conn = get_connection()
        if conn:
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO blood_pressure (user_id, systolic, diastolic, heart_rate, notes)
                VALUES (%s, %s, %s, %s, %s)
            """, (str(user_id), systolic, diastolic, heart_rate, notes))
            conn.commit()
            cur.close()
            conn.close()
            print("Blood pressure saved successfully")
            return True
        else:
            print("Failed to get database connection")
            return False
    except Exception as e:
        print(f"Error saving blood pressure: {e}")
        print(f"Parameters: user_id={user_id}, systolic={systolic}, diastolic={diastolic}, heart_rate={heart_rate}, notes={notes}")
        return False

def get_blood_pressure_data(user_id, limit=None):
    try:
        conn = get_connection()
        if conn:
            import pandas as pd
            query = "SELECT * FROM blood_pressure WHERE user_id = %s ORDER BY timestamp DESC"
            if limit:
                query += f" LIMIT {limit}"
            df = pd.read_sql_query(query, conn, params=(str(user_id),))
            conn.close()
            if not df.empty:
                df['timestamp'] = pd.to_datetime(df['timestamp'], utc=True).dt.tz_localize(None)
            return df
    except Exception as e:
        print(f"Error fetching blood pressure data: {e}")
    return pd.DataFrame()

def save_activity(user_id, activity_type, duration, intensity, calories, notes=None):
    if not user_id:
        print("Error: user_id is None or empty")
        return False
    
    if not activity_type or duration is None or not intensity or calories is None:
        print(f"Error: required fields are None. activity_type={activity_type}, duration={duration}, intensity={intensity}, calories={calories}")
        return False
    
    try:
        conn = get_connection()
        if conn:
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO activities (user_id, activity_type, duration, intensity, calories, notes)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (str(user_id), activity_type, duration, intensity, calories, notes))
            conn.commit()
            cur.close()
            conn.close()
            print("Activity saved successfully")
            return True
        else:
            print("Failed to get database connection")
            return False
    except Exception as e:
        print(f"Error saving activity: {e}")
        print(f"Parameters: user_id={user_id}, activity_type={activity_type}, duration={duration}, intensity={intensity}, calories={calories}, notes={notes}")
        return False

def log_prediction_to_db(user_id, age, chol, bp, prediction, probability):
    conn = get_connection()
    if conn:
        try:
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO predictions_history (user_id, age, cholesterol, resting_bp_s, predicted_target, probability)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (str(user_id), age, chol, bp, prediction, probability))
            conn.commit()
            cur.close()
            conn.close()
            return True
        except Exception as e:
            print(f"Error logging prediction: {e}")
            return False
    return False

def save_cholesterol(user_id, total_chol=None, ldl=None, hdl=None, triglycerides=None, notes=None):
    conn = get_connection()
    if conn:
        try:
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO cholesterol_readings (user_id, total_cholesterol, ldl, hdl, triglycerides, notes)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (str(user_id), total_chol, ldl, hdl, triglycerides, notes))
            conn.commit()
            cur.close()
            conn.close()
            return True
        except Exception as e:
            print(f"Error saving cholesterol: {e}")
            return False
    return False

def save_chat_message(user_id, role, message):
    conn = get_connection()
    if conn:
        try:
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO chat_history (user_id, role, message)
                VALUES (%s, %s, %s)
            """, (str(user_id), role, message))
            conn.commit()
            cur.close()
            conn.close()
            return True
        except Exception as e:
            print(f"Error saving chat message: {e}")
            return False
    return False

def load_chat_history(user_id):
    try:
        conn = get_connection()
        if conn:
            import pandas as pd
            query = "SELECT role, message, timestamp FROM chat_history WHERE user_id = %s ORDER BY timestamp ASC"
            df = pd.read_sql_query(query, conn, params=(str(user_id),))
            conn.close()
            if not df.empty:
                df['timestamp'] = pd.to_datetime(df['timestamp'], utc=True).dt.tz_localize(None)
                # Convert DataFrame to list of dicts with 'content' instead of 'message'
                chat_list = df[['role', 'message']].rename(columns={'message': 'content'}).to_dict('records')
                print(f"Loaded {len(chat_list)} chat messages for user {user_id}")
                return chat_list
            return []
    except Exception as e:
        print(f"Error loading chat history: {e}")
    return []

def get_weekly_bp_summary(user_id):
    try:
        conn = get_connection()
        if conn:
            import pandas as pd
            query = """
                SELECT 
                    DATE(timestamp) as date,
                    AVG(systolic) as avg_systolic,
                    AVG(diastolic) as avg_diastolic,
                    MIN(systolic) as min_systolic,
                    MAX(systolic) as max_systolic,
                    MIN(diastolic) as min_diastolic,
                    MAX(diastolic) as max_diastolic,
                    COUNT(*) as readings_count
                FROM blood_pressure 
                WHERE user_id = %s AND timestamp >= CURRENT_DATE - INTERVAL '7 days'
                GROUP BY DATE(timestamp)
                ORDER BY date ASC
            """
            df = pd.read_sql_query(query, conn, params=(str(user_id),))
            conn.close()
            if not df.empty:
                df['date'] = pd.to_datetime(df['date'], utc=True).dt.tz_localize(None)
            return df
    except Exception as e:
        print(f"Error getting weekly BP summary: {e}")
    return pd.DataFrame()