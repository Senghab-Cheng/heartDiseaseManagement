# pages/activity_tracker.py
import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import plotly.express as px
import plotly.graph_objects as go
from utils.database import init_db, save_activity, get_activity_data

# Check if user is logged in
if 'logged_in' not in st.session_state or not st.session_state.logged_in:
    st.error("Please log in first!")
    st.stop()

# Check if user_id exists
if 'user_id' not in st.session_state or st.session_state.user_id is None:
    st.error("User session expired. Please log in again.")
    st.stop()

st.markdown('<h1 style="text-align: center; color: #1f77b4;">Physical Activity Tracker</h1>', unsafe_allow_html=True)

# Initialize database
init_db()

# MET (Metabolic Equivalent) values for different activities
MET_VALUES = {
    "Walking (Casual)": 3.5,
    "Walking (Brisk)": 4.5,
    "Running (Light)": 8.0,
    "Running (Fast)": 11.0,
    "Cycling (Casual)": 6.0,
    "Cycling (Vigorous)": 10.0,
    "Swimming": 7.0,
    "Yoga": 2.5,
    "Gym (Weight Training)": 5.0,
    "Gym (Cardio)": 7.0,
    "Dancing": 5.5,
    "Hiking": 6.5,
    "Basketball": 8.0,
    "Football/Soccer": 10.0,
    "Tennis": 7.0,
    "Golf": 4.3,
    "Gardening": 4.0,
    "Cleaning": 3.5,
    "Stairs": 8.0,
    "Jump Rope": 12.0,
    "Other": 5.0
}

# Intensity indicators without emojis
INTENSITY_INDICATORS = {
    "Light": "[L]",
    "Moderate": "[M]",
    "Vigorous": "[V]"
}

def estimate_calories(activity, duration_min, weight_kg):
    """Calculate calories burned using MET formula"""
    met = MET_VALUES.get(activity, 5.0)
    # Formula: Calories = (MET * weight_kg * duration_hours)
    calories = (met * weight_kg * duration_min) / 60
    return round(calories, 1)

def get_user_activity_data(user_id):
    """Get activity data for user"""
    return get_activity_data(user_id)

def calculate_weekly_goal_progress(activity_df):
    """Calculate progress towards WHO 150min/week goal"""
    now = datetime.now()
    week_start = now - timedelta(days=now.weekday())
    # Reset time to start of day
    week_start = week_start.replace(hour=0, minute=0, second=0, microsecond=0)
    this_week = activity_df[activity_df['timestamp'] >= week_start]
    
    total_min = this_week['duration'].sum() if not this_week.empty else 0
    goal = 150  # WHO recommendation
    progress = min((total_min / goal) * 100, 100)
    
    return {
        'minutes': total_min,
        'goal': goal,
        'progress': progress,
        'remaining': max(goal - total_min, 0),
        'days_active': this_week['timestamp'].dt.date.nunique() if not this_week.empty else 0
    }

def get_user_weight():
    """Get user weight from profile or use default"""
    if 'user_weight' not in st.session_state:
        st.session_state.user_weight = 70.0  # Default weight
    return st.session_state.user_weight

# Create tabs
tab1, tab2, tab3, tab4 = st.tabs(["Log Activity", "Dashboard", "History", "Insights"])

# TAB 1: LOG ACTIVITY
with tab1:
    st.subheader("Log Physical Activity")
    
    # User weight setting (for calorie calculation)
    with st.expander("Profile Settings"):
        weight = st.number_input(
            "Your Weight (kg)",
            min_value=30.0,
            max_value=200.0,
            value=get_user_weight(),
            step=0.5,
            help="Used for calorie calculation"
        )
        if st.button("Save Weight"):
            st.session_state.user_weight = weight
            st.success("Weight updated successfully!")
    
    st.markdown("---")
    
    col1, col2 = st.columns(2)
    
    with col1:
        activity_type = st.selectbox(
            "Activity Type",
            list(MET_VALUES.keys()),
            help="Select the activity you performed"
        )
        
        duration = st.number_input(
            "Duration (minutes)",
            min_value=1,
            max_value=300,
            value=30,
            step=5
        )
        
        activity_date = st.date_input("Date", datetime.now())
    
    with col2:
        intensity = st.select_slider(
            "Intensity Level",
            options=["Light", "Moderate", "Vigorous"],
            value="Moderate",
            help="How hard did you work?"
        )
        
        # Auto-calculate calories
        estimated_cal = estimate_calories(activity_type, duration, get_user_weight())
        calories = st.number_input(
            "Calories Burned",
            min_value=0,
            max_value=2000,
            value=int(estimated_cal),
            help=f"Auto-calculated: {estimated_cal:.0f} cal"
        )
        
        activity_time = st.time_input("Time", datetime.now().time())
    
    notes = st.text_area(
        "Notes (optional)",
        placeholder="How did you feel? Any observations..."
    )
    
    # Show MET info
    st.info(f"INFO: **{activity_type}** has a MET value of {MET_VALUES[activity_type]} (Energy expenditure rate)")
    
    if st.button("Save Activity", type="primary", use_container_width=True):
        try:
            # Save using database function
            if save_activity(st.session_state.user_id, activity_type, duration, intensity, calories, notes):
                st.success(f"Activity logged: {duration} minutes of {activity_type}!")
                st.balloons()
                st.rerun()
            else:
                st.error("Failed to save activity.")
        except Exception as e:
            st.error(f"Error saving activity: {str(e)}")

# TAB 2: DASHBOARD
with tab2:
    st.subheader("Your Activity Dashboard")
    
    activity_df = get_user_activity_data(st.session_state.user_id)
    
    if not activity_df.empty:
        # Weekly goal progress
        weekly_stats = calculate_weekly_goal_progress(activity_df)
        
        st.markdown("### This Week's Progress")
        
        # Progress bar
        st.progress(weekly_stats['progress'] / 100)
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(
                "Minutes This Week",
                f"{weekly_stats['minutes']:.0f}",
                f"{weekly_stats['minutes'] - weekly_stats['goal']:+.0f} vs goal"
            )
        
        with col2:
            st.metric(
                "Weekly Goal",
                f"{weekly_stats['goal']} min",
                f"{weekly_stats['progress']:.0f}% complete"
            )
        
        with col3:
            st.metric(
                "Days Active",
                f"{weekly_stats['days_active']} days"
            )
        
        with col4:
            remaining = weekly_stats['remaining']
            if remaining > 0:
                st.metric("Remaining", f"{remaining:.0f} min")
            else:
                st.metric("Goal Status", "Achieved!")
        
        # Achievement messages
        if weekly_stats['progress'] >= 100:
            st.success("**Goal Achieved!** You met the WHO recommendation of 150 min/week!")
        elif weekly_stats['progress'] >= 50:
            st.info("**Halfway There!** Keep up the great work!")
        elif weekly_stats['days_active'] >= 5:
            st.success("**5-Day Streak!** Consistency is key!")
        
        st.markdown("---")
        
        # Overall statistics
        st.markdown("### Overall Statistics")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            total_activities = len(activity_df)
            st.metric("Total Activities", total_activities)
        
        with col2:
            total_minutes = activity_df['duration'].sum()
            st.metric("Total Time", f"{total_minutes:.0f} min")
        
        with col3:
            total_calories = activity_df['calories'].sum()
            st.metric("Total Calories", f"{total_calories:,.0f}")
        
        with col4:
            avg_duration = activity_df['duration'].mean()
            st.metric("Avg Duration", f"{avg_duration:.0f} min")
        
        st.markdown("---")
        
        # Recent activities
        st.markdown("### Recent Activities")
        
        recent_df = activity_df.head(5)
        for idx, row in recent_df.iterrows():
            with st.container():
                col1, col2, col3, col4 = st.columns([3, 2, 2, 1])
                
                with col1:
                    st.markdown(f"**{row['activity_type']}**")
                    utc_timestamp = row['timestamp']
                    st.caption(f"""
                    <span class="timestamp-display" data-utc="{utc_timestamp.strftime('%Y-%m-%dT%H:%M:%S')}Z">{utc_timestamp.strftime('%b %d, %Y at %I:%M %p')} UTC</span>
                    """, unsafe_allow_html=True)
                
                with col2:
                    st.markdown(f"Duration: {row['duration']:.0f} min")
                
                with col3:
                    st.markdown(f"Calories: {row['calories']:.0f}")
                
                with col4:
                    st.markdown(INTENSITY_INDICATORS.get(row['intensity'], "[?]"))
                
                if row['notes']:
                    st.caption(f"Notes: {row['notes']}")
                
                st.divider()
        
    else:
        st.info("No activities logged yet. Start by logging your first activity!")
        
        st.markdown("""
        ### Why Track Physical Activity?
        
        - **Heart Health:** Regular exercise reduces heart disease risk by 30-40%
        - **Blood Pressure:** Physical activity can lower BP by 5-10 mmHg
        - **Weight Management:** Track calories burned to maintain healthy weight
        - **Mental Health:** Exercise reduces stress, anxiety, and depression
        - **WHO Recommendation:** 150 minutes of moderate activity per week
        
        **Start today!** Even 10 minutes of activity counts!
        """)

# TAB 3: HISTORY
with tab3:
    st.subheader("Activity History & Trends")
    
    activity_df = get_user_activity_data(st.session_state.user_id)
    
    if not activity_df.empty:
        # Time period selector
        period = st.selectbox(
            "Time Period",
            ["Last 7 Days", "Last 30 Days", "Last 3 Months", "All Time"]
        )
        
        # Filter data
        now = datetime.now()
        if period == "Last 7 Days":
            filtered_df = activity_df[activity_df['timestamp'] >= now - timedelta(days=7)]
        elif period == "Last 30 Days":
            filtered_df = activity_df[activity_df['timestamp'] >= now - timedelta(days=30)]
        elif period == "Last 3 Months":
            filtered_df = activity_df[activity_df['timestamp'] >= now - timedelta(days=90)]
        else:
            filtered_df = activity_df
        
        if not filtered_df.empty:
            # Activity over time
            daily_df = filtered_df.groupby(filtered_df['timestamp'].dt.date).agg({
                'duration': 'sum',
                'calories': 'sum'
            }).reset_index()
            daily_df.columns = ['date', 'duration', 'calories']
            
            fig = go.Figure()
            
            fig.add_trace(go.Bar(
                x=daily_df['date'],
                y=daily_df['duration'],
                name='Duration (min)',
                marker_color='#3498db'
            ))
            
            fig.add_hline(
                y=22,  # 150/7 ≈ 22 min/day
                line_dash="dash",
                line_color="green",
                annotation_text="Daily Goal (22 min)"
            )
            
            fig.update_layout(
                title="Daily Activity Duration",
                xaxis_title="Date",
                yaxis_title="Minutes",
                height=400
            )
            
            st.plotly_chart(fig, use_container_width=True)
            
            # Charts row
            col1, col2 = st.columns(2)
            
            with col1:
                # Activity type distribution
                activity_counts = filtered_df['activity_type'].value_counts()
                fig_pie = px.pie(
                    values=activity_counts.values,
                    names=activity_counts.index,
                    title='Activity Type Distribution',
                    hole=0.4
                )
                st.plotly_chart(fig_pie, use_container_width=True)
            
            with col2:
                # Intensity distribution
                intensity_df = filtered_df.groupby('intensity')['duration'].sum().reset_index()
                fig_bar = px.bar(
                    intensity_df,
                    x='intensity',
                    y='duration',
                    title='Total Duration by Intensity',
                    color='intensity',
                    color_discrete_map={
                        'Light': '#90EE90',
                        'Moderate': '#FFD700',
                        'Vigorous': '#FF6347'
                    }
                )
                st.plotly_chart(fig_bar, use_container_width=True)
            
            # Weekly comparison
            st.markdown("### Weekly Comparison")
            
            filtered_df['week'] = filtered_df['timestamp'].dt.to_period('W').astype(str)
            weekly_df = filtered_df.groupby('week').agg({
                'duration': 'sum',
                'calories': 'sum',
                'activity_type': 'count'
            }).reset_index()
            weekly_df.columns = ['week', 'duration', 'calories', 'count']
            
            col1, col2 = st.columns(2)
            
            with col1:
                fig_line = px.line(
                    weekly_df,
                    x='week',
                    y='duration',
                    title='Weekly Activity Minutes',
                    markers=True
                )
                fig_line.add_hline(y=150, line_dash="dash", line_color="green")
                st.plotly_chart(fig_line, use_container_width=True)
            
            with col2:
                fig_line2 = px.line(
                    weekly_df,
                    x='week',
                    y='calories',
                    title='Weekly Calories Burned',
                    markers=True,
                    line_shape='spline'
                )
                st.plotly_chart(fig_line2, use_container_width=True)
            
            # Detailed records
            st.markdown("### Detailed Activity Log")
            
            display_df = filtered_df[['timestamp', 'activity_type', 'duration', 'intensity', 'calories', 'notes']].copy()
            display_df['timestamp'] = display_df['timestamp'].dt.strftime('%Y-%m-%d %I:%M %p')
            
            st.dataframe(display_df, use_container_width=True)
            
            # Export button
            csv = filtered_df.to_csv(index=False)
            st.download_button(
                label="Download Activity Log (CSV)",
                data=csv,
                file_name=f"activities_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv"
            )
        else:
            st.info(f"No activities found for {period}")
    else:
        st.info("No data available yet. Start logging activities!")

# TAB 4: INSIGHTS
with tab4:
    st.subheader("Activity Insights & Recommendations")
    
    activity_df = get_user_activity_data(st.session_state.user_id)
    
    if not activity_df.empty and len(activity_df) >= 3:
        insights = []
        
        # Weekly progress
        weekly_stats = calculate_weekly_goal_progress(activity_df)
        
        if weekly_stats['progress'] >= 100:
            insights.append({
                'title': 'Goal Crusher!',
                'message': f"You've completed {weekly_stats['minutes']:.0f} minutes this week - {weekly_stats['progress']:.0f}% of your goal! Amazing work!",
                'type': 'success'
            })
        elif weekly_stats['progress'] >= 75:
            insights.append({
                'title': 'Almost There!',
                'message': f"You're at {weekly_stats['progress']:.0f}% of your weekly goal. Just {weekly_stats['remaining']:.0f} more minutes to go!",
                'type': 'info'
            })
        elif weekly_stats['progress'] < 50:
            insights.append({
                'title': 'Time to Move!',
                'message': f"You're at {weekly_stats['progress']:.0f}% of your weekly goal. Try to fit in {weekly_stats['remaining']:.0f} more minutes this week!",
                'type': 'warning'
            })
        
        # Consistency insights
        if weekly_stats['days_active'] >= 5:
            insights.append({
                'title': 'Consistency Champion!',
                'message': f"You've been active {weekly_stats['days_active']} days this week! Consistency is the key to success!",
                'type': 'success'
            })
        
        # Favorite activity
        favorite = activity_df['activity_type'].mode()[0]
        favorite_count = (activity_df['activity_type'] == favorite).sum()
        favorite_pct = (favorite_count / len(activity_df)) * 100
        
        insights.append({
            'title': 'Your Favorite Activity',
            'message': f"{favorite} is your go-to activity ({favorite_pct:.0f}% of workouts). It's great to have a favorite, but variety helps work different muscle groups!",
            'type': 'info'
        })
        
        # Intensity analysis
        intensity_counts = activity_df['intensity'].value_counts()
        if 'Vigorous' in intensity_counts and intensity_counts['Vigorous'] > len(activity_df) * 0.3:
            insights.append({
                'title': 'High Intensity Warrior!',
                'message': "You love vigorous workouts! Great for cardiovascular fitness. Don't forget rest days for recovery.",
                'type': 'info'
            })
        elif 'Light' in intensity_counts and intensity_counts['Light'] > len(activity_df) * 0.7:
            insights.append({
                'title': 'Consider Intensity Boost',
                'message': "Most of your activities are light intensity. Try gradually increasing to moderate intensity for more heart health benefits!",
                'type': 'info'
            })
        
        # Recent streak calculation
        activity_df_sorted = activity_df.sort_values('timestamp', ascending=False)
        activity_df_sorted['date'] = activity_df_sorted['timestamp'].dt.date
        unique_dates = activity_df_sorted['date'].unique()
        
        streak = 1
        for i in range(len(unique_dates) - 1):
            if (unique_dates[i] - unique_dates[i+1]).days == 1:
                streak += 1
            else:
                break
        
        if streak >= 3:
            insights.append({
                'title': f'{streak}-Day Streak!',
                'message': f"You've been active for {streak} consecutive days! Keep the momentum going!",
                'type': 'success'
            })
        
        # Display insights
        if insights:
            for insight in insights:
                if insight['type'] == 'success':
                    st.success(f"### {insight['title']}\n{insight['message']}")
                elif insight['type'] == 'warning':
                    st.warning(f"### {insight['title']}\n{insight['message']}")
                else:
                    st.info(f"### {insight['title']}\n{insight['message']}")
        
        st.markdown("---")
        
        # Recommendations
        st.markdown("### Personalized Recommendations")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**Based on Your Activity:**")
            
            # Dynamic recommendations
            total_min_this_week = weekly_stats['minutes']
            
            if total_min_this_week < 150:
                daily_goal = 22 - (total_min_this_week/7)
                st.markdown(f"""
                - Add **{weekly_stats['remaining']:.0f} more minutes** this week
                - Try {daily_goal:.0f} min/day to meet daily goal
                - Aim for at least **5 days** of activity
                """)
            else:
                st.markdown("""
                - You're meeting WHO guidelines!
                - Consider strength training 2x/week
                - Try new activities for variety
                """)
            
            # Activity suggestions based on history
            if favorite == "Walking (Casual)":
                st.markdown("""
                **Try These Next:**
                - Brisk Walking for more intensity
                - Hiking for variety
                - Light jogging intervals
                """)
            elif "Gym" in favorite:
                st.markdown("""
                **Complement Your Training:**
                - Yoga for flexibility
                - Swimming for recovery
                - Walking on rest days
                """)
        
        with col2:
            st.markdown("""
            **General Guidelines:**
            
            **WHO Recommendations:**
            - 150 min/week moderate intensity
            - OR 75 min/week vigorous intensity
            - Strength training 2+ days/week
            
            **Benefits of Regular Activity:**
            - Reduces heart disease risk 30-40%
            - Lowers blood pressure 5-10 mmHg
            - Improves mental health
            - Better sleep quality
            - Weight management
            
            **Tips for Success:**
            - Schedule workouts like appointments
            - Find an exercise buddy
            - Make it fun with music
            - Track progress (you're doing it!)
            """)
        
    else:
        st.info("Log at least 3 activities to see personalized insights!")
        
        st.markdown("""
        ### Activity & Heart Health
        
        **How Exercise Helps Your Heart:**
        
        1. **Strengthens the heart muscle** - Makes it pump more efficiently
        2. **Lowers blood pressure** - Reduces strain on arteries
        3. **Improves cholesterol** - Raises HDL (good) cholesterol
        4. **Reduces inflammation** - Decreases arterial inflammation
        5. **Weight management** - Maintains healthy body weight
        
        **Getting Started:**
        
        - **Week 1-2:** Start with 10-15 min/day walking
        - **Week 3-4:** Increase to 20-30 min/day
        - **Week 5+:** Mix in different activities, increase intensity
        
        **Remember:** Some activity is better than none. Every minute counts!
        
        ---
        
        ### Activity Intensity Guide
        
        **Light Intensity** (Can talk easily)
        - Casual walking
        - Light stretching
        - Gentle yoga
        
        **Moderate Intensity** (Can talk, but harder)
        - Brisk walking
        - Water aerobics
        - Recreational cycling
        
        **Vigorous Intensity** (Can't say much)
        - Running
        - Swimming laps
        - Fast cycling
        - Sports (basketball, soccer)
        
        Start logging to get personalized insights!
        """)

# JavaScript to convert UTC timestamps to local time
st.markdown("""
<script>
// Convert all UTC timestamps to local time
document.addEventListener('DOMContentLoaded', function() {
    const timestampElements = document.querySelectorAll('.timestamp-display');
    timestampElements.forEach(element => {
        const utcString = element.getAttribute('data-utc');
        if (utcString) {
            const utcDate = new Date(utcString);
            const localDate = new Date(utcDate.getTime() - utcDate.getTimezoneOffset() * 60000);
            element.textContent = localDate.toLocaleDateString('en-US', {
                year: 'numeric',
                month: 'short', 
                day: 'numeric'
            }) + ' at ' + localDate.toLocaleTimeString('en-US', {
                hour: 'numeric',
                minute: '2-digit',
                hour12: true
            });
        }
    });
});
</script>
""", unsafe_allow_html=True)