import streamlit as st
import database
import pandas as pd
from datetime import datetime
import time

def record_activity(user_id, activity, details=None):
    """Record user activity in the audit log."""
    
    # Insert into AuditLogs table
    database.insert_record(
        "AuditLogs",
        {
            "user_id": user_id,
            "activity": activity,
            "details": details or "",
            "timestamp": datetime.now()
        }
    )

def get_recent_activities(limit=10):
    """Get recent activities from the audit log."""
    
    # Query recent activities
    activities = database.query_to_dataframe(
        """
        SELECT 
            a.log_id,
            COALESCE(u.username, 'System') as username,
            a.activity,
            a.details,
            a.timestamp
        FROM AuditLogs a
        LEFT JOIN Users u ON a.user_id = u.user_id
        ORDER BY a.timestamp DESC
        LIMIT ?
        """,
        (limit,)
    )
    
    # Format timestamp
    if not activities.empty:
        activities['timestamp'] = pd.to_datetime(activities['timestamp']).dt.strftime('%Y-%m-%d %H:%M:%S')
    
    return activities

def audit_logs():
    """Audit logs page."""
    st.header("Audit Logs")
    
    tab1, tab2 = st.tabs(["Activity Log", "User Sessions"])
    
    with tab1:
        st.subheader("System Activity Log")
        
        # Filters
        col1, col2, col3 = st.columns(3)
        
        with col1:
            user_filter = st.selectbox(
                "User",
                ["All Users"] + [row[0] for row in database.fetch_all(
                    "SELECT DISTINCT username FROM Users ORDER BY username"
                ) or []]
            )
        
        with col2:
            activity_filter = st.selectbox(
                "Activity Type",
                ["All Activities"] + sorted(set([row[0] for row in database.fetch_all(
                    "SELECT DISTINCT activity FROM AuditLogs ORDER BY activity"
                ) or []]))
            )
        
        with col3:
            time_filter = st.selectbox(
                "Time Period",
                ["Last 24 Hours", "Last 7 Days", "Last 30 Days", "All Time"]
            )
        
        # Build query
        query = """
        SELECT 
            a.log_id,
            COALESCE(u.username, 'System') as username,
            a.activity,
            a.details,
            a.timestamp
        FROM AuditLogs a
        LEFT JOIN Users u ON a.user_id = u.user_id
        """
        
        params = []
        where_clauses = []
        
        if user_filter != "All Users":
            where_clauses.append("u.username = ?")
            params.append(user_filter)
        
        if activity_filter != "All Activities":
            where_clauses.append("a.activity = ?")
            params.append(activity_filter)
        
        if time_filter == "Last 24 Hours":
            where_clauses.append("a.timestamp >= datetime('now', '-1 day')")
        elif time_filter == "Last 7 Days":
            where_clauses.append("a.timestamp >= datetime('now', '-7 days')")
        elif time_filter == "Last 30 Days":
            where_clauses.append("a.timestamp >= datetime('now', '-30 days')")
        
        # Finalize query
        if where_clauses:
            query += " WHERE " + " AND ".join(where_clauses)
        
        query += " ORDER BY a.timestamp DESC LIMIT 1000"
        
        # Execute query
        audit_df = database.query_to_dataframe(query, params)
        
        if audit_df.empty:
            st.info("No audit logs found matching your criteria.")
        else:
            # Format timestamp
            audit_df['timestamp'] = pd.to_datetime(audit_df['timestamp']).dt.strftime('%Y-%m-%d %H:%M:%S')
            
            # Display dataframe
            st.dataframe(audit_df, use_container_width=True)
            
            # Download option
            if st.button("Export to CSV"):
                csv = audit_df.to_csv(index=False)
                
                # Get current timestamp for filename
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                
                # Convert to CSV to download
                st.download_button(
                    label="Download CSV",
                    data=csv,
                    file_name=f"audit_log_{timestamp}.csv",
                    mime="text/csv"
                )
        
        # Activity statistics
        if not audit_df.empty:
            st.subheader("Activity Statistics")
            
            col1, col2 = st.columns(2)
            
            with col1:
                # Activity counts by type
                activity_counts = audit_df['activity'].value_counts().reset_index()
                activity_counts.columns = ['Activity', 'Count']
                
                # Create bar chart
                st.bar_chart(activity_counts.set_index('Activity'))
            
            with col2:
                # Activity by user
                user_counts = audit_df['username'].value_counts().reset_index()
                user_counts.columns = ['User', 'Count']
                
                # Create bar chart
                st.bar_chart(user_counts.set_index('User'))
    
    with tab2:
        st.subheader("User Sessions")
        
        # Get user sessions
        user_sessions = database.query_to_dataframe(
            """
            SELECT 
                s.session_id,
                u.username,
                s.login_time,
                s.logout_time,
                s.status
            FROM UserSessions s
            JOIN Users u ON s.user_id = u.user_id
            ORDER BY s.login_time DESC
            LIMIT 1000
            """
        )
        
        if user_sessions.empty:
            st.info("No user sessions recorded.")
        else:
            # Format timestamps
            user_sessions['login_time'] = pd.to_datetime(user_sessions['login_time']).dt.strftime('%Y-%m-%d %H:%M:%S')
            user_sessions['logout_time'] = pd.to_datetime(user_sessions['logout_time']).dt.strftime('%Y-%m-%d %H:%M:%S')
            
            # Calculate session duration
            def calculate_duration(row):
                if pd.isna(row['logout_time']) or row['logout_time'] == 'NaT':
                    if row['status'] == 'active':
                        return "Session active"
                    else:
                        return "Unknown"
                else:
                    login = datetime.strptime(row['login_time'], '%Y-%m-%d %H:%M:%S')
                    logout = datetime.strptime(row['logout_time'], '%Y-%m-%d %H:%M:%S')
                    
                    duration = logout - login
                    minutes, seconds = divmod(duration.seconds, 60)
                    hours, minutes = divmod(minutes, 60)
                    
                    if hours > 0:
                        return f"{hours}h {minutes}m"
                    else:
                        return f"{minutes}m {seconds}s"
            
            user_sessions['duration'] = user_sessions.apply(calculate_duration, axis=1)
            
            # Display dataframe
            st.dataframe(user_sessions, use_container_width=True)
            
            # Active sessions
            active_sessions = user_sessions[user_sessions['status'] == 'active']
            
            st.write(f"**Currently Active Sessions:** {len(active_sessions)}")
            
            if not active_sessions.empty:
                st.dataframe(active_sessions, use_container_width=True)
            
            # Force logout option for admins
            if st.session_state.role == 'admin':
                st.write("### Force Logout Users")
                
                active_users = [(s['session_id'], s['username']) for _, s in active_sessions.iterrows() 
                                if s['username'] != st.session_state.username]
                
                if active_users:
                    selected_session = st.selectbox(
                        "Select User to Log Out",
                        options=[f"{username} (Session ID: {session_id})" for session_id, username in active_users]
                    )
                    
                    if st.button("Force Logout"):
                        # Extract session ID
                        session_id = int(selected_session.split("Session ID: ")[1].rstrip(')'))
                        
                        # Animation
                        with st.spinner("Logging out user..."):
                            time.sleep(1)  # Simple animation delay
                        
                        # Update session
                        database.update_record(
                            "UserSessions",
                            {
                                "logout_time": datetime.now(),
                                "status": "inactive"
                            },
                            {"session_id": session_id}
                        )
                        
                        # Record in audit log
                        record_activity(
                            st.session_state.user_id,
                            "Forced Logout",
                            f"Admin forced logout of session ID {session_id}"
                        )
                        
                        st.success("User logged out successfully!")
                        time.sleep(1)
                        st.rerun()
                else:
                    st.info("No other active users to log out.")
