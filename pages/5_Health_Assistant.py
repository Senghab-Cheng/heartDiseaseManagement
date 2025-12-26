import streamlit as st
import pandas as pd
import re
from datetime import datetime
from utils.database import get_connection

# --- Authentication Check ---
if 'logged_in' not in st.session_state or not st.session_state.logged_in:
    st.error("Please log in first!")
    st.stop()

# --- Database Helper Functions ---

def ensure_tables_exist():
    """Ensure all required tables exist in Supabase/Postgres"""
    try:
        conn = get_connection()
        c = conn.cursor()
        
        tables = {
            "blood_pressure": "(id SERIAL PRIMARY KEY, user_id TEXT NOT NULL, systolic INTEGER NOT NULL, diastolic INTEGER NOT NULL, heart_rate INTEGER, timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP, notes TEXT)",
            "activities": "(id SERIAL PRIMARY KEY, user_id TEXT NOT NULL, activity_type TEXT NOT NULL, duration REAL NOT NULL, intensity TEXT NOT NULL, calories REAL NOT NULL, timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP, notes TEXT)",
            "chat_history": "(id SERIAL PRIMARY KEY, user_id TEXT NOT NULL, role TEXT NOT NULL, message TEXT NOT NULL, timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP)",
            "cholesterol_readings": "(id SERIAL PRIMARY KEY, user_id TEXT NOT NULL, total_cholesterol INTEGER, ldl INTEGER, hdl INTEGER, triglycerides INTEGER, timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP, notes TEXT)"
        }
        
        for table_name, schema in tables.items():
            c.execute(f"CREATE TABLE IF NOT EXISTS {table_name} {schema}")
        
        conn.commit()
        c.close()
        conn.close()
    except Exception as e:
        st.error(f"Table Creation Error: {e}")

# --- Data Saving Functions ---

def save_blood_pressure(user_id, systolic, diastolic, heart_rate=None, notes=''):
    try:
        conn = get_connection()
        c = conn.cursor()
        c.execute("INSERT INTO blood_pressure (user_id, systolic, diastolic, heart_rate, notes) VALUES (%s, %s, %s, %s, %s)",
                  (str(user_id), systolic, diastolic, heart_rate, notes))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        st.error(f"Save BP Error: {e}")
        return False

def save_activity(user_id, activity_type, duration, intensity, calories=None, notes=''):
    try:
        if calories is None:
            mult = {'Light': 3, 'Moderate': 5, 'Vigorous': 8}
            calories = duration * mult.get(intensity, 5)
        conn = get_connection()
        c = conn.cursor()
        c.execute("INSERT INTO activities (user_id, activity_type, duration, intensity, calories, notes) VALUES (%s, %s, %s, %s, %s, %s)",
                  (str(user_id), activity_type, duration, intensity, calories, notes))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        st.error(f"Save Activity Error: {e}")
        return False

def save_cholesterol(user_id, total_chol, ldl=None, hdl=None, triglycerides=None, notes=''):
    try:
        conn = get_connection()
        c = conn.cursor()
        c.execute("INSERT INTO cholesterol_readings (user_id, total_cholesterol, ldl, hdl, triglycerides, notes) VALUES (%s, %s, %s, %s, %s, %s)",
                  (str(user_id), total_chol, ldl, hdl, triglycerides, notes))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        st.error(f"Save Cholesterol Error: {e}")
        return False

def save_chat_message(user_id, role, message):
    try:
        conn = get_connection()
        c = conn.cursor()
        c.execute("INSERT INTO chat_history (user_id, role, message) VALUES (%s, %s, %s)", (str(user_id), role, message))
        conn.commit()
        conn.close()
    except: pass

# --- Logic Processing Functions ---

def process_blood_pressure(user_input, user_id):
    bp_match = re.search(r'(\d{2,3})\s*(?:/|over)\s*(\d{2,3})', user_input.lower())
    if bp_match:
        sys, dia = int(bp_match.group(1)), int(bp_match.group(2))
        if save_blood_pressure(user_id, sys, dia):
            return f"Logged BP: **{sys}/{dia} mmHg**. Great job tracking your levels!"
    return "Could not parse BP. Try: 'My BP is 120/80'"

def process_activity(user_input, user_id):
    duration_match = re.search(r'(\d+)\s*(min|minute)', user_input.lower())
    duration = int(duration_match.group(1)) if duration_match else 30
    if save_activity(user_id, "Exercise", duration, "Moderate"):
        return f"Logged **{duration} mins** of activity! Keep moving!"
    return "Error logging activity."

def process_cholesterol(user_input, user_id):
    numbers = re.findall(r'\d+', user_input)
    if numbers:
        val = int(numbers[0])
        if 'ldl' in user_input.lower():
            save_cholesterol(user_id, None, ldl=val)
            return f"Logged LDL Cholesterol: **{val} mg/dL**."
        else:
            save_cholesterol(user_id, total_chol=val)
            return f"Logged Total Cholesterol: **{val} mg/dL**."
    return "Please provide a number for your cholesterol."

def process_status_check(user_id):
    try:
        conn = get_connection()
        df = pd.read_sql_query("""
            SELECT AVG(systolic) as s, AVG(diastolic) as d 
            FROM blood_pressure 
            WHERE user_id = %s AND timestamp >= CURRENT_TIMESTAMP - INTERVAL '7 days'
        """, conn, params=(str(user_id),))
        conn.close()
        if not df.empty and df['s'].iloc[0]:
            return f"**Weekly Summary:** Your average BP is **{df['s'].iloc[0]:.0f}/{df['d'].iloc[0]:.0f} mmHg**."
        return "No data found for the last 7 days. Start logging to see your summary!"
    except Exception as e: 
        return f"Error fetching status: {e}"

def process_user_input(user_input, user_id):
    inp = user_input.lower()
    if 'bp' in inp or '/' in inp or 'pressure' in inp: 
        return process_blood_pressure(user_input, user_id)
    if any(word in inp for word in ['walk', 'run', 'swim', 'min', 'exercise', 'activity']): 
        return process_activity(user_input, user_id)
    if any(word in inp for word in ['cholesterol', 'ldl', 'hdl']):
        return process_cholesterol(user_input, user_id)
    if any(word in inp for word in ['status', 'how', 'summary', 'doing', 'report']): 
        return process_status_check(user_id)
    
    return "I can log your BP (120/80), activities (walked 20 min), or cholesterol. How can I help?"

def load_chat_history(user_id):
    try:
        conn = get_connection()
        df = pd.read_sql_query("SELECT role, message as content FROM chat_history WHERE user_id = %s ORDER BY timestamp ASC LIMIT 20", conn, params=(str(user_id),))
        conn.close()
        return df.to_dict('records')
    except: return []

# --- UI Helper ---

def display_guide():
    with st.expander("**How to use the Health Assistant**", expanded=True):
        st.markdown("""
        I can help you track your heart health automatically. Try typing these:
        
        1. **Log Blood Pressure:** *'My BP is 120/80'* or *'BP 130 over 85'*
        2. **Log Activity:** *'I walked for 30 minutes'* or *'I swam for 45 minutes'*
        3. **Log Cholesterol:** *'My cholesterol is 190'* or *'My LDL is 110'*
        4. **Get Summary:** *'How am I doing?'* or *'Weekly summary'*
        """)

# --- Main Page Render ---

def render():
    st.title("Smart Health Assistant")
    ensure_tables_exist()
    
    display_guide()
    
    if 'chat_history' not in st.session_state:
        st.session_state.chat_history = load_chat_history(st.session_state.user_id)
        if not st.session_state.chat_history:
            st.session_state.chat_history = [{"role": "assistant", "content": "Hi! I'm your Heart Assistant. How can I help you track your health today?"}]

    for msg in st.session_state.chat_history:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    user_input = st.chat_input("Enter your health data...")
    if user_input:
        st.session_state.chat_history.append({"role": "user", "content": user_input})
        save_chat_message(st.session_state.user_id, "user", user_input)
        
        with st.chat_message("user"):
            st.markdown(user_input)
            
        response = process_user_input(user_input, st.session_state.user_id)
        
        with st.chat_message("assistant"):
            st.markdown(response)
            
        st.session_state.chat_history.append({"role": "assistant", "content": response})
        save_chat_message(st.session_state.user_id, "assistant", response)
        st.rerun()

if __name__ == "__main__":
    render()