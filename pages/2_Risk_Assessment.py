import streamlit as st
import pandas as pd
import numpy as np
import os
import joblib
from datetime import datetime
from utils.database import get_connection

# --- 1. AUTHENTICATION ---
if 'logged_in' not in st.session_state or not st.session_state.logged_in:
    st.error("Please log in first!")
    st.stop()

# --- 2. DYNAMIC PATH RESOLUTION ---
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
MODEL_DIR = os.path.join(project_root, 'models')

MODEL_PATH = os.path.join(MODEL_DIR, 'heart_disease_model.pkl')
SCALER_PATH = os.path.join(MODEL_DIR, 'scaler.pkl')
FEATURE_NAMES_PATH = os.path.join(MODEL_DIR, 'feature_names.pkl')

# --- 3. DATABASE LOGIC (POSTGRES / SUPABASE COMPATIBLE) ---

def ensure_db_setup():
    """Ensures the predictions table exists in the shared database"""
    try:
        conn = get_connection()
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS predictions_history
                     (id SERIAL PRIMARY KEY,
                      user_id TEXT NOT NULL, 
                      age INTEGER, 
                      cholesterol INTEGER, 
                      resting_bp_s INTEGER,
                      predicted_target INTEGER, 
                      probability REAL,
                      timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
        conn.commit()
        c.close()
        conn.close()
    except Exception as e:
        st.error(f"Database setup error: {e}")

def log_prediction_to_db(user_id, age, chol, bp, target, prob):
    """Saves assessment results to the shared database"""
    try:
        conn = get_connection()
        c = conn.cursor()
        c.execute('''INSERT INTO predictions_history 
                     (user_id, age, cholesterol, resting_bp_s, predicted_target, probability)
                     VALUES (%s, %s, %s, %s, %s, %s)''',
                  (str(user_id), age, chol, bp, target, prob))
        conn.commit()
        c.close()
        conn.close()
    except Exception as e:
        st.error(f"Failed to save prediction: {e}")

def get_recent_logs(user_id):
    """Fetches history for the specific logged-in user"""
    try:
        conn = get_connection()
        query = """SELECT timestamp, age, resting_bp_s, cholesterol, predicted_target, probability 
                   FROM predictions_history WHERE user_id = %s ORDER BY timestamp DESC LIMIT 5"""
        df = pd.read_sql_query(query, conn, params=(str(user_id),))
        conn.close()
        return df
    except:
        return pd.DataFrame()

# --- 4. LOAD TRAINED ASSETS ---
@st.cache_resource
def load_trained_assets():
    if not os.path.exists(MODEL_PATH):
        return None
    try:
        return {
            "model": joblib.load(MODEL_PATH),
            "scaler": joblib.load(SCALER_PATH),
            "features": joblib.load(FEATURE_NAMES_PATH)
        }
    except Exception as e:
        st.error(f"Error loading model assets: {e}")
        return None

# --- 5. MAIN UI RENDERER ---
def render_risk_assessment():
    st.title("Heart Disease Risk Assessment")
    ensure_db_setup()
    
    assets = load_trained_assets()
    if not assets:
        st.error(f"Critical Error: Model files not found in {MODEL_DIR}")
        return

    with st.form("assessment_form"):
        st.subheader("Patient Vitals Input")
        col1, col2 = st.columns(2)
        
        with col1:
            age = st.number_input("Age", 18, 100, 50)
            sex = st.selectbox("Sex", [0, 1], format_func=lambda x: "Male" if x == 1 else "Female")
            cp = st.selectbox("Chest Pain Type", [0, 1, 2, 3], 
                              format_func=lambda x: ["Typical", "Atypical", "Non-Anginal", "Asymptomatic"][x])
            bp = st.number_input("Resting Blood Pressure", 80, 200, 120)
            chol = st.number_input("Cholesterol", 100, 600, 200)
            
        with col2:
            fbs = st.selectbox("Fasting Blood Sugar > 120", [0, 1], format_func=lambda x: "Yes" if x == 1 else "No")
            ecg = st.selectbox("Resting ECG", [0, 1, 2], format_func=lambda x: ["Normal", "ST-T", "LVH"][x])
            max_hr = st.number_input("Max Heart Rate", 60, 220, 150)
            exang = st.selectbox("Exercise Angina", [0, 1], format_func=lambda x: "Yes" if x == 1 else "No")
            oldpeak = st.number_input("ST Depression (Oldpeak)", 0.0, 6.0, 0.0)
            slope = st.selectbox("ST Slope", [0, 1, 2], 
                                format_func=lambda x: ["Upsloping", "Flat", "Downsloping"][x])

        if st.form_submit_button("Predict Risk", type="primary"):
            try:
                # Prepare data
                input_df = pd.DataFrame([[age, sex, cp, bp, chol, fbs, ecg, max_hr, exang, oldpeak, slope]], 
                                        columns=assets['features'])
                
                # Scale and Predict
                scaled_data = assets['scaler'].transform(input_df)
                prediction = int(assets['model'].predict(scaled_data)[0])
                probability = float(assets['model'].predict_proba(scaled_data)[0][1])
                
                # Save results to Shared Database
                log_prediction_to_db(st.session_state.user_id, age, chol, bp, prediction, probability)
                
                st.divider()
                if prediction == 1:
                    st.error(f"High Risk Detected: {probability*100:.1f}%")
                else:
                    st.success(f"Low Risk Detected: {probability*100:.1f}%")
                    
            except Exception as e:
                st.error(f"Calculation Error: {e}")

    # --- 6. QUICK OVERVIEW ---
    st.divider()
    st.subheader("Quick Overview: Recent Logs")
    history = get_recent_logs(st.session_state.user_id)
    
    if not history.empty:
        # Clean labels (no emojis)
        history['Result'] = history['predicted_target'].apply(lambda x: "High Risk" if x == 1 else "Low Risk")
        history['Risk %'] = (history['probability'] * 100).round(1).astype(str) + '%'
        st.dataframe(history[['timestamp', 'age', 'Result', 'Risk %']], use_container_width=True)
    else:
        st.info("No previous assessment data found.")

if __name__ == "__main__":
    render_risk_assessment()