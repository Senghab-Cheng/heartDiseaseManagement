# pages/dashboard.py
import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import plotly.graph_objects as go
from utils.database import init_db, get_blood_pressure_data, get_activity_data

# Check if user is logged in
if 'logged_in' not in st.session_state or not st.session_state.logged_in:
    st.error("Please log in first!")
    st.stop()

st.title("Health Dashboard")
st.write(f"Welcome back, {st.session_state.username}!")

# Initialize database
init_db()

def get_bp_data(user_id, days=30):
    """Get BP data from database"""
    df = get_blood_pressure_data(user_id)
    if not df.empty:
        cutoff = datetime.now() - timedelta(days=days)
        df = df[df['timestamp'] >= cutoff]
    return df

def get_activity_data(user_id, days=30):
    """Get activity data from database"""
    # Import the database function to avoid recursion
    from utils.database import get_activity_data as db_get_activity_data
    df = db_get_activity_data(user_id)
    if not df.empty:
        cutoff = datetime.now() - timedelta(days=days)
        df = df[df['timestamp'] >= cutoff]
    return df

# Load data
bp_df = get_bp_data(st.session_state.user_id)
activity_df = get_activity_data(st.session_state.user_id)

# Main metrics
st.subheader("Overview")

col1, col2, col3 = st.columns(3)

with col1:
    if not bp_df.empty:
        latest_bp = bp_df.iloc[0]
        st.metric("Latest BP", f"{latest_bp['systolic']:.0f}/{latest_bp['diastolic']:.0f}")
    else:
        st.metric("Latest BP", "No data")

with col2:
    if not activity_df.empty:
        week_activity = activity_df[activity_df['timestamp'] >= datetime.now() - timedelta(days=7)]
        weekly_min = week_activity['duration'].sum() if not week_activity.empty else 0
        st.metric("Weekly Activity", f"{weekly_min:.0f} min")
    else:
        st.metric("Weekly Activity", "No data")

with col3:
    total_records = len(bp_df) + len(activity_df)
    st.metric("Total Records", total_records)

# Charts section
st.subheader("Trends")

if not bp_df.empty or not activity_df.empty:
    fig = go.Figure()
    
    # Add BP trend
    if not bp_df.empty:
        bp_daily = bp_df.groupby(bp_df['timestamp'].dt.date)['systolic'].mean().reset_index()
        fig.add_trace(go.Scatter(
            x=bp_daily['timestamp'],
            y=bp_daily['systolic'],
            name='Blood Pressure',
            line=dict(color='red', width=2)
        ))
    
    # Add activity trend
    if not activity_df.empty:
        activity_daily = activity_df.groupby(activity_df['timestamp'].dt.date)['duration'].sum().reset_index()
        fig.add_trace(go.Bar(
            x=activity_daily['timestamp'],
            y=activity_daily['duration'],
            name='Activity (min)',
            marker_color='green',
            opacity=0.6
        ))
    
    fig.update_layout(
        title="Health Trends (Last 30 Days)",
        xaxis_title="Date",
        height=400
    )
    
    st.plotly_chart(fig, use_container_width=True)

# Recent data
st.subheader("Recent Data")

tab1, tab2 = st.tabs(["Blood Pressure", "Activity"])

with tab1:
    if not bp_df.empty:
        st.dataframe(bp_df.head(10)[['timestamp', 'systolic', 'diastolic', 'heart_rate']])
    else:
        st.info("No blood pressure data available")

with tab2:
    if not activity_df.empty:
        st.dataframe(activity_df.head(10)[['timestamp', 'activity_type', 'duration', 'calories']])
    else:
        st.info("No activity data available")

# Quick actions
st.subheader("Quick Actions")
col1, col2 = st.columns(2)

with col1:
    if st.button("Add Blood Pressure Reading"):
        st.switch_page("pages/3_BP_Monitoring.py")

with col2:
    if st.button("Log Activity"):
        st.switch_page("pages/4_Activity_Tracker.py")