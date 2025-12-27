import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import plotly.graph_objects as go
import plotly.express as px
from utils.database import init_db, save_blood_pressure, get_blood_pressure_data
import warnings

# Check if user is logged in
if 'logged_in' not in st.session_state or not st.session_state.logged_in:
    st.error("Please log in first!")
    st.stop()

# Check if user_id exists
if 'user_id' not in st.session_state or st.session_state.user_id is None:
    st.error("User session expired. Please log in again.")
    st.stop()

st.markdown('<h1 style="text-align: center; color: #1f77b4;">Blood Pressure Monitor</h1>', unsafe_allow_html=True)

# Initialize database
init_db()

def classify_bp(systolic, diastolic):
    """Classify BP according to AHA guidelines"""
    if systolic < 120 and diastolic < 80:
        return {
            "category": "Normal",
            "color": "success",
            "advice": "Excellent! Your blood pressure is in the normal range. Keep up the healthy lifestyle!"
        }
    elif systolic < 130 and diastolic < 80:
        return {
            "category": "Elevated",
            "color": "warning",
            "advice": "Your BP is elevated. Focus on diet, exercise, and stress management.",
        }
    elif systolic < 140 or diastolic < 90:
        return {
            "category": "High BP - Stage 1",
            "color": "warning",
            "advice": "Stage 1 hypertension detected. Consult your doctor about lifestyle changes and possible medication."
        }
    elif systolic < 180 and diastolic < 120:
        return {
            "category": "High BP - Stage 2",
            "color": "error",
            "advice": "Stage 2 hypertension. Medical attention is needed. Contact your healthcare provider."
        }
    else:
        return {
            "category": "Hypertensive Crisis",
            "color": "error",
            "advice": "EMERGENCY! Seek immediate medical care. Call emergency services if experiencing symptoms."
        }

def get_bp_data(user_id, limit=None):
    """Retrieve BP data from database"""
    return get_blood_pressure_data(user_id, limit)

def calculate_bp_trends(bp_df):
    """Calculate BP trends and statistics"""
    if bp_df.empty or len(bp_df) < 2:
        return None
    
    now = datetime.now()
    last_7_days = bp_df[bp_df['timestamp'] >= now - timedelta(days=7)]
    prev_7_days = bp_df[(bp_df['timestamp'] >= now - timedelta(days=14)) & 
                        (bp_df['timestamp'] < now - timedelta(days=7))]
    
    trends = {
        'current_avg_systolic': last_7_days['systolic'].mean() if not last_7_days.empty else 0,
        'current_avg_diastolic': last_7_days['diastolic'].mean() if not last_7_days.empty else 0,
        'prev_avg_systolic': prev_7_days['systolic'].mean() if not prev_7_days.empty else 0,
        'prev_avg_diastolic': prev_7_days['diastolic'].mean() if not prev_7_days.empty else 0,
        'total_readings': len(bp_df),
        'readings_this_week': len(last_7_days),
        'morning_avg': bp_df[bp_df['timestamp'].dt.hour < 12]['systolic'].mean() if not bp_df.empty else 0,
        'evening_avg': bp_df[bp_df['timestamp'].dt.hour >= 18]['systolic'].mean() if not bp_df.empty else 0
    }
    
    if trends['prev_avg_systolic'] > 0:
        trends['systolic_change'] = trends['current_avg_systolic'] - trends['prev_avg_systolic']
        trends['diastolic_change'] = trends['current_avg_diastolic'] - trends['prev_avg_diastolic']
    else:
        trends['systolic_change'] = 0
        trends['diastolic_change'] = 0
    
    return trends

# Create tabs
tab1, tab2, tab3, tab4 = st.tabs(["Log Reading", "Dashboard", "History & Trends", "Insights"])

# TAB 1: LOG READING
with tab1:
    st.subheader("Log Blood Pressure Reading")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        systolic = st.number_input("Systolic (mmHg)", 80, 250, 120, help="Upper number")
    with col2:
        diastolic = st.number_input("Diastolic (mmHg)", 40, 150, 80, help="Lower number")
    with col3:
        heart_rate = st.number_input("Heart Rate (bpm)", 40, 200, 72, help="Pulse rate")
    
    col1, col2 = st.columns(2)
    with col1:
        reading_date = st.date_input("Date", datetime.now())
    with col2:
        reading_time = st.time_input("Time", datetime.now().time())
    
    notes = st.text_area("Notes (optional)", placeholder="E.g., After exercise, took medication...")
    
    if st.button("Save Reading", type="primary", use_container_width=True):
        reading_datetime = datetime.combine(reading_date, reading_time)
        classification = classify_bp(systolic, diastolic)
        
        # Save to database
        if save_blood_pressure(st.session_state.user_id, systolic, diastolic, heart_rate, notes):
            st.success("Blood pressure reading saved successfully!")
        else:
            st.error("Failed to save reading.")
            st.stop()
        
        st.markdown("---")
        st.markdown(f"### Result: {classification['category']}")
        
        if classification['color'] == 'success':
            st.success(classification['advice'])
        elif classification['color'] == 'warning':
            st.warning(classification['advice'])
        else:
            st.error(classification['advice'])
        st.rerun()

# TAB 2: DASHBOARD
with tab2:
    st.subheader("Your BP Dashboard")
    bp_df = get_bp_data(st.session_state.user_id, limit=30)
    
    if not bp_df.empty:
        trends = calculate_bp_trends(bp_df)
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Avg Systolic", f"{bp_df['systolic'].mean():.0f} mmHg", 
                      f"{trends['systolic_change']:+.1f}" if trends else None, delta_color="inverse")
        with col2:
            st.metric("Avg Diastolic", f"{bp_df['diastolic'].mean():.0f} mmHg", 
                      f"{trends['diastolic_change']:+.1f}" if trends else None, delta_color="inverse")
        with col3:
            heart_rate_mean = bp_df['heart_rate'].dropna().mean()
            avg_hr_display = f"{heart_rate_mean:.0f} bpm" if not pd.isna(heart_rate_mean) else "N/A"
            st.metric("Avg Heart Rate", avg_hr_display)
        with col4:
            st.metric("Total Readings", len(bp_df))
        
        st.markdown("---")
        latest = bp_df.iloc[0]
        classification = classify_bp(latest['systolic'], latest['diastolic'])
        # Convert UTC timestamp to local time for display
        utc_timestamp = latest['timestamp']
        local_timestamp = utc_timestamp  # For now, keep as UTC since we can't determine user's timezone server-side
        
        st.markdown(f"""
        ### Latest Reading - <span id="timestamp-display" data-utc="{utc_timestamp.strftime('%Y-%m-%dT%H:%M:%S')}Z">{utc_timestamp.strftime('%b %d, %Y at %I:%M %p')}</span>
        """, unsafe_allow_html=True)
        
        heart_rate_display = f"{latest['heart_rate']:.0f} bpm" if latest['heart_rate'] is not None else "Not recorded"
        
        st.markdown(f"""
            <div style="background: linear-gradient(135deg, #1f77b4 0%, #124e78 100%); 
                        padding: 2rem; border-radius: 15px; color: white;">
                <h2 style="margin:0;">{latest['systolic']:.0f}/{latest['diastolic']:.0f} mmHg</h2>
                <p style="margin:0.5rem 0 0 0; font-size: 1.2rem;">{classification['category']}</p>
                <p style="margin:0.5rem 0 0 0;">Heart Rate: {heart_rate_display}</p>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.info("No readings yet. Start by logging your first reading in the 'Log Reading' tab.")

# TAB 3: HISTORY & TRENDS
with tab3:
    st.subheader("Blood Pressure History & Trends")
    bp_df = get_bp_data(st.session_state.user_id)
    if not bp_df.empty:
        period = st.selectbox("Time Period", ["Last 7 Days", "Last 30 Days", "Last 3 Months", "All Time"])
        
        # Filtering logic
        now = datetime.now()
        if period == "Last 7 Days":
            filtered_df = bp_df[bp_df['timestamp'] >= now - timedelta(days=7)]
        elif period == "Last 30 Days":
            filtered_df = bp_df[bp_df['timestamp'] >= now - timedelta(days=30)]
        else:
            filtered_df = bp_df
        
        if not filtered_df.empty:
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=filtered_df['timestamp'], y=filtered_df['systolic'], name='Systolic', line=dict(color='#e74c3c')))
            fig.add_trace(go.Scatter(x=filtered_df['timestamp'], y=filtered_df['diastolic'], name='Diastolic', line=dict(color='#3498db')))
            st.plotly_chart(fig, use_container_width=True)
            
            st.subheader("Detailed Records")
            st.dataframe(filtered_df[['timestamp', 'systolic', 'diastolic', 'heart_rate', 'category', 'notes']], use_container_width=True)
    else:
        st.info("No data available yet.")

# TAB 4: INSIGHTS
with tab4:
    st.subheader("Personalized Insights")
    bp_df = get_bp_data(st.session_state.user_id)
    
    if not bp_df.empty and len(bp_df) >= 3:
        trends = calculate_bp_trends(bp_df)
        if trends:
            if trends['systolic_change'] < -3:
                st.success(f"### Great Progress!\nYour average systolic BP has decreased by {abs(trends['systolic_change']):.1f} mmHg this week.")
            elif trends['systolic_change'] > 3:
                st.warning(f"### BP Rising\nYour systolic BP increased by {trends['systolic_change']:.1f} mmHg. Review your diet and stress.")
            
            if trends['readings_this_week'] >= 5:
                st.success("### Consistency Streak!\nYou are doing a great job monitoring your health regularly.")
        
        st.markdown("---")
        st.subheader("Tips for Managing Blood Pressure")
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("**Dietary Changes:**\n- Reduce sodium salt intake\n- Eat more fruits and vegetables\n- Choose whole grains")
        with col2:
            st.markdown("**Lifestyle Habits:**\n- 150 min/week moderate activity\n- Maintain healthy weight\n- Manage stress levels")
    else:
        st.info("Log at least 3 readings to see personalized insights.")

# JavaScript to convert UTC timestamps to local time
st.markdown("""
<script>
// Convert UTC timestamp in the latest reading header
document.addEventListener('DOMContentLoaded', function() {
    const timestampElement = document.getElementById('timestamp-display');
    if (timestampElement) {
        const utcString = timestampElement.getAttribute('data-utc');
        if (utcString) {
            const utcDate = new Date(utcString);
            const localDate = new Date(utcDate.getTime() - utcDate.getTimezoneOffset() * 60000);
            timestampElement.textContent = localDate.toLocaleDateString('en-US', {
                year: 'numeric',
                month: 'short', 
                day: 'numeric'
            }) + ' at ' + localDate.toLocaleTimeString('en-US', {
                hour: 'numeric',
                minute: '2-digit',
                hour12: true
            });
        }
    }
});
</script>
""", unsafe_allow_html=True)