import streamlit as st
import pandas as pd
import numpy as np
import os
import base64
from datetime import datetime, timedelta
import sys

# Function to convert image to base64 for HTML display
def get_base64_image(image_path):
    """Convert image file to base64 string for HTML embedding"""
    try:
        if os.path.exists(image_path):
            with open(image_path, "rb") as image_file:
                encoded_string = base64.b64encode(image_file.read()).decode()
            return encoded_string
        return ""
    except Exception as e:
        return ""

# This tells Python to look in the current folder for the 'utils' module
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Now your existing import will work
from utils.database import init_db, verify_user, create_user, get_prediction_history

# Page configuration MUST be first
st.set_page_config(
    page_title='Heart Disease Prevention',
    page_icon="Cambodia Health Innovations Logo - Medical Cross and Circuit.png",
    layout='wide',
    initial_sidebar_state='expanded'
)

# Initialize database
init_db()

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
        margin-top: 1rem;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 0.5rem 0;
    }
    .sidebar .sidebar-content {
        padding-top: 1rem;
    }
    .stImage {
        margin-bottom: 1rem;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'user_id' not in st.session_state:
    st.session_state.user_id = None
if 'username' not in st.session_state:
    st.session_state.username = None

def login_ui():
    """Handles the Login/Signup views."""
    empty1, col1, empty2 = st.columns([1, 2, 1])
    with col1:
        logo_b64 = get_base64_image("Cambodia Health Innovations Logo - Medical Cross and Circuit.png")
        if logo_b64:
            st.markdown(f"""
            <div style="text-align: center; padding: 1rem;">
                <img src="data:image/png;base64,{logo_b64}" style="width: 130px; height: auto; display: block; margin: 0 auto;">
            </div>
            """, unsafe_allow_html=True)

    st.markdown('<p class="main-header">Welcome to Cambodia Health Innovation</p>', unsafe_allow_html=True)
    st.info("Please Log In or Sign Up to access the health management system.")

    auth_tab1, auth_tab2 = st.tabs(["Login", "Sign Up"])

    with auth_tab1:
        with st.form("login_form"):
            st.subheader("Login to Your Account")
            login_user = st.text_input("Username", placeholder="Enter your username")
            login_pass = st.text_input("Password", type="password", placeholder="Enter your password")
            submitted = st.form_submit_button("Log In", type="primary", use_container_width=True)

            if submitted:
                if not login_user or not login_pass:
                    st.error("Please fill in all fields.")
                else:
                    status, u_id = verify_user(login_user, login_pass)
                    if status:
                        st.session_state.logged_in = True
                        st.session_state.user_id = u_id
                        st.session_state.username = login_user
                        st.success(f"Welcome back, {login_user}!")
                        st.rerun()
                    else:
                        st.error("Invalid Username or Password.")

    with auth_tab2:
        with st.form("signup_form"):
            st.subheader("Create New Account")
            signup_user = st.text_input("Choose Username", placeholder="Pick a unique username")
            signup_pass = st.text_input("Choose Password", type="password", placeholder="At least 6 characters")
            signup_pass_confirm = st.text_input("Confirm Password", type="password", placeholder="Re-enter password")
            submitted_signup = st.form_submit_button("Create Account", type="primary", use_container_width=True)

            if submitted_signup:
                if not signup_user or not signup_pass or not signup_pass_confirm:
                    st.error("Please fill in all fields.")
                elif signup_pass != signup_pass_confirm:
                    st.error("Passwords do not match.")
                elif len(signup_pass) < 6:
                    st.error("Password must be at least 6 characters.")
                else:
                    success, result = create_user(signup_user, signup_pass)
                    if success:
                        st.session_state.logged_in = True
                        st.session_state.user_id = result 
                        st.session_state.username = signup_user
                        st.success("Account created successfully! You are now logged in.")
                        st.rerun()
                    else:
                        st.error(f"Sign up failed: {result}")

# Check login status
if not st.session_state.logged_in:
    login_ui()
    st.stop()

# Logout Sidebar
with st.sidebar:
    logo_b64_sidebar = get_base64_image("Cambodia Health Innovations Logo - Medical Cross and Circuit.png")
    if logo_b64_sidebar:
        st.markdown(f"""
        <div style="text-align: center; margin-bottom: 2.5rem; padding: 1rem;">
            <img src="data:image/png;base64,{logo_b64_sidebar}" style="width: 110px; height: auto; display: block; margin: 0 auto;">
        </div>
        """, unsafe_allow_html=True)

    st.title("Heart Health Management")
    st.write(f"Logged in as: **{st.session_state.username}**")
    st.markdown("---")
    if st.button("Logout", use_container_width=True):
        st.session_state.logged_in = False
        st.session_state.user_id = None
        st.session_state.username = None
        st.rerun()

# Main Dashboard
st.title("Health Management Dashboard")
st.markdown("Welcome to your personalized heart health portal.")

# Summary Metrics
col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("Latest Risk", "45%", "-5%")
with col2:
    st.metric("Blood Pressure", "120/80", "Normal")
with col3:
    st.metric("Weekly Activity", "150 min", "Goal Met")
with col4:
    st.metric("Health Score", "85/100", "+5")

st.markdown("---")

# Navigation Guide
st.subheader("System Features")
c1, c2, c3 = st.columns(3)
with c1:
    st.markdown("**Risk Assessment**\nAI-powered risk prediction")
with c2:
    st.markdown("**BP Monitoring**\nTrack and graph blood pressure")
with c3:
    st.markdown("**Activity Tracker**\nLog fitness and exercise")

st.markdown("---")

# Quick Overview (Risk History Chart)
st.subheader("Health Trend Overview")

# 1. Fetch the data
data = get_prediction_history(st.session_state.user_id)

if data:
    try:
        # 2. Convert list of tuples to DataFrame
        df = pd.DataFrame(data, columns=['Result', 'Probability', 'Date'])
        
        # 3. Clean the Date
        df['Date'] = pd.to_datetime(df['Date']).dt.tz_localize(None)
        
        # 4. Create the chart
        import plotly.express as px
        fig = px.line(
            df, 
            x='Date', 
            y='Probability',
            title='Heart Disease Risk Trend',
            markers=True,
            template="plotly_white"
        )
        
        # 5. Format the look
        fig.update_layout(
            yaxis_title="Risk Probability (0.0 - 1.0)",
            xaxis_title="Assessment Date",
            yaxis_range=[0, 1]
        )
        
        # 6. Render
        st.plotly_chart(fig, use_container_width=True)
        
    except Exception as e:
        st.error(f"Error rendering chart: {e}")
        st.table(df.tail())
else:
    st.info("No assessment history found. Please complete a Risk Assessment first.")