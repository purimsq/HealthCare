import streamlit as st
import database
import pandas as pd
from datetime import datetime, timedelta
import time
import audit

def get_active_staff_count():
    """Get the count of active staff members."""
    result = database.fetch_one(
        """
        SELECT COUNT(*) FROM Staff s
        JOIN Users u ON s.user_id = u.user_id
        WHERE s.status = 'active' AND u.status = 'active'
        """
    )
    return result[0] if result else 0

def get_total_staff_count():
    """Get the total count of staff members."""
    result = database.fetch_one("SELECT COUNT(*) FROM Staff")
    return result[0] if result else 0

def staff_management():
    """Staff management page."""
    st.header("Staff Management")
    
    tab1, tab2, tab3 = st.tabs(["Staff Directory", "Add Staff", "Staff Scheduling"])
    
    with tab1:
        st.subheader("Staff Directory")
        
        # Filters
        col1, col2, col3 = st.columns(3)
        
        with col1:
            search_term = st.text_input("Search by name or department")
        
        with col2:
            department_filter = st.selectbox(
                "Department", 
                ["All"] + sorted(set([row[0] for row in database.fetch_all(
                    "SELECT DISTINCT department FROM Staff ORDER BY department"
                ) or []])),
            )
        
        with col3:
            status_filter = st.selectbox("Status", ["All", "Active", "Inactive", "On Leave"])
        
        # Build query
        query = """
        SELECT 
            s.staff_id, 
            u.full_name, 
            s.department, 
            s.position, 
            s.hire_date, 
            s.salary,
            s.status,
            u.email,
            u.last_login
        FROM Staff s
        JOIN Users u ON s.user_id = u.user_id
        """
        
        params = []
        where_clauses = []
        
        if search_term:
            where_clauses.append("(u.full_name LIKE ? OR s.department LIKE ? OR s.position LIKE ?)")
            params.extend([f"%{search_term}%", f"%{search_term}%", f"%{search_term}%"])
        
        if department_filter != "All":
            where_clauses.append("s.department = ?")
            params.append(department_filter)
        
        if status_filter != "All":
            where_clauses.append("s.status = ?")
            params.append(status_filter.lower())
        
        # Finalize query
        if where_clauses:
            query += " WHERE " + " AND ".join(where_clauses)
        
        query += " ORDER BY u.full_name"
        
        # Execute query
        staff_df = database.query_to_dataframe(query, params)
        
        if staff_df.empty:
            st.info("No staff members found matching your criteria.")
        else:
            # Format dates and currency
            staff_df['hire_date'] = pd.to_datetime(staff_df['hire_date']).dt.strftime('%Y-%m-%d')
            staff_df['last_login'] = pd.to_datetime(staff_df['last_login']).dt.strftime('%Y-%m-%d %H:%M')
            staff_df['salary'] = staff_df['salary'].apply(lambda x: f"${x:,.2f}" if x else "Not specified")
            
            # Reorder and rename columns for display
            display_df = staff_df[[
                'staff_id', 'full_name', 'department', 'position', 'hire_date', 'status'
            ]]
            
            display_df.columns = [
                'ID', 'Name', 'Department', 'Position', 'Hire Date', 'Status'
            ]
            
            st.dataframe(display_df, use_container_width=True)
            
            # Summary by department
            st.write("### Staff by Department")
            
            dept_summary = staff_df.groupby('department')['staff_id'].count().reset_index()
            dept_summary.columns = ['Department', 'Count']
            
            col1, col2 = st.columns([3, 1])
            
            with col1:
                st.bar_chart(dept_summary.set_index('Department'))
            
            with col2:
                st.dataframe(dept_summary, use_container_width=True)
        
        # Staff details and actions
        if not staff_df.empty:
            st.subheader("Staff Details")
            
            staff_options = [f"{row['full_name']} - {row['position']} (ID: {row['staff_id']})" for _, row in staff_df.iterrows()]
            selected_staff = st.selectbox("Select Staff Member", ["Select a staff member"] + staff_options)
            
            if selected_staff != "Select a staff member":
                staff_id = int(selected_staff.split("ID: ")[1].rstrip(')'))
                
                # Get staff details
                staff = database.fetch_one(
                    """
                    SELECT 
                        s.staff_id, 
                        s.user_id,
                        u.full_name,
                        u.username,
                        u.email,
                        s.department,
                        s.position,
                        s.hire_date,
                        s.salary,
                        s.contact_number,
                        s.emergency_contact,
                        s.status,
                        u.last_login,
                        u.status as user_status
                    FROM Staff s
                    JOIN Users u ON s.user_id = u.user_id
                    WHERE s.staff_id = ?
                    """,
                    (staff_id,)
                )
                
                if staff:
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.write(f"**ID:** {staff[0]}")
                        st.write(f"**Name:** {staff[2]}")
                        st.write(f"**Username:** {staff[3]}")
                        st.write(f"**Email:** {staff[4]}")
                        st.write(f"**Department:** {staff[5]}")
                        st.write(f"**Position:** {staff[6]}")
                    
                    with col2:
                        st.write(f"**Hire Date:** {staff[7]}")
                        st.write(f"**Salary:** {f'${staff[8]:,.2f}' if staff[8] else 'Not specified'}")
                        st.write(f"**Contact:** {staff[9] or 'Not specified'}")
                        st.write(f"**Emergency Contact:** {staff[10] or 'Not specified'}")
                        st.write(f"**Status:** {staff[11]}")
                        st.write(f"**Last Login:** {staff[12] or 'Never logged in'}")
                    
                    # Action buttons
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        if st.button("Edit Staff Info"):
                            st.session_state.edit_staff = staff_id
                            st.rerun()
                    
                    with col2:
                        if staff[11] == 'active':
                            if st.button("Mark as Inactive"):
                                # Animation
                                with st.spinner("Updating staff status..."):
                                    time.sleep(1)  # Simple animation delay
                                
                                # Update staff status
                                database.update_record(
                                    "Staff",
                                    {"status": "inactive"},
                                    {"staff_id": staff_id}
                                )
                                
                                # Record in audit log
                                audit.record_activity(
                                    st.session_state.user_id,
                                    "Staff Status Changed",
                                    f"Changed status of staff ID {staff_id} to inactive"
                                )
                                
                                st.success("Staff marked as inactive successfully!")
                                time.sleep(1)
                                st.rerun()
                        else:
                            if st.button("Mark as Active"):
                                # Animation
                                with st.spinner("Updating staff status..."):
                                    time.sleep(1)  # Simple animation delay
                                
                                # Update staff status
                                database.update_record(
                                    "Staff",
                                    {"status": "active"},
                                    {"staff_id": staff_id}
                                )
                                
                                # Record in audit log
                                audit.record_activity(
                                    st.session_state.user_id,
                                    "Staff Status Changed",
                                    f"Changed status of staff ID {staff_id} to active"
                                )
                                
                                st.success("Staff marked as active successfully!")
                                time.sleep(1)
                                st.rerun()
                    
                    with col3:
                        if st.button("View Activity"):
                            st.session_state.view_staff_activity = staff[1]  # user_id
                            st.rerun()
                    
                    # Handle staff edit
                    if hasattr(st.session_state, 'edit_staff') and st.session_state.edit_staff == staff_id:
                        with st.form("edit_staff_form"):
                            st.subheader(f"Edit Staff: {staff[2]}")
                            
                            col1, col2 = st.columns(2)
                            
                            with col1:
                                department = st.text_input("Department", staff[5])
                                position = st.text_input("Position", staff[6])
                                hire_date = st.date_input(
                                    "Hire Date", 
                                    datetime.strptime(staff[7], '%Y-%m-%d')
                                )
                            
                            with col2:
                                salary = st.number_input(
                                    "Salary ($)", 
                                    min_value=0.0, 
                                    value=float(staff[8]) if staff[8] else 0.0, 
                                    step=1000.0
                                )
                                contact = st.text_input("Contact Number", staff[9] or "")
                                emergency = st.text_input("Emergency Contact", staff[10] or "")
                            
                            status = st.selectbox(
                                "Status",
                                ["active", "inactive", "on leave"],
                                index=["active", "inactive", "on leave"].index(staff[11])
                            )
                            
                            update_staff_submitted = st.form_submit_button("Update Staff")
                            
                            if update_staff_submitted:
                                # Animation
                                with st.spinner("Updating staff information..."):
                                    time.sleep(1)  # Simple animation delay
                                
                                # Update staff
                                database.update_record(
                                    "Staff",
                                    {
                                        "department": department,
                                        "position": position,
                                        "hire_date": hire_date.strftime('%Y-%m-%d'),
                                        "salary": salary if salary > 0 else None,
                                        "contact_number": contact,
                                        "emergency_contact": emergency,
                                        "status": status
                                    },
                                    {"staff_id": staff_id}
                                )
                                
                                # Record in audit log
                                audit.record_activity(
                                    st.session_state.user_id,
                                    "Staff Updated",
                                    f"Updated staff ID {staff_id} ({staff[2]})"
                                )
                                
                                st.success("Staff information updated successfully!")
                                
                                # Clear the session state and rerun
                                del st.session_state.edit_staff
                                time.sleep(1)
                                st.rerun()
                    
                    # Handle staff activity view
                    if hasattr(st.session_state, 'view_staff_activity') and st.session_state.view_staff_activity == staff[1]:
                        st.subheader(f"Activity Log for {staff[2]}")
                        
                        # Get user activity
                        activity_df = database.query_to_dataframe(
                            """
                            SELECT activity, details, timestamp
                            FROM AuditLogs
                            WHERE user_id = ?
                            ORDER BY timestamp DESC
                            LIMIT 50
                            """,
                            (staff[1],)
                        )
                        
                        if activity_df.empty:
                            st.info("No activity recorded for this staff member.")
                        else:
                            # Format dates
                            activity_df['timestamp'] = pd.to_datetime(activity_df['timestamp']).dt.strftime('%Y-%m-%d %H:%M:%S')
                            
                            # Rename columns for display
                            activity_df.columns = ['Activity', 'Details', 'Timestamp']
                            
                            st.dataframe(activity_df, use_container_width=True)
                        
                        if st.button("Close Activity View"):
                            del st.session_state.view_staff_activity
                            st.rerun()
    
    with tab2:
        st.subheader("Add New Staff Member")
        
        st.write("To add a new staff member, first create a user account, then add the staff details.")
        
        # First step: Check if there are any users without staff records
        users_without_staff = database.query_to_dataframe(
            """
            SELECT u.user_id, u.username, u.full_name, u.email, u.role
            FROM Users u
            LEFT JOIN Staff s ON u.user_id = s.user_id
            WHERE s.staff_id IS NULL AND u.role != 'admin'
            ORDER BY u.full_name
            """
        )
        
        if users_without_staff.empty:
            st.info("All users have staff records. Create a new user first.")
        else:
            with st.form("add_staff_form"):
                # User selection
                user_options = {row['user_id']: f"{row['full_name']} ({row['role']})" for _, row in users_without_staff.iterrows()}
                user_options[0] = "Select a user"
                
                selected_user = st.selectbox(
                    "Select User*",
                    options=list(user_options.keys()),
                    format_func=lambda x: user_options[x],
                    index=0
                )
                
                col1, col2 = st.columns(2)
                
                with col1:
                    department = st.text_input("Department*")
                    position = st.text_input("Position*")
                    hire_date = st.date_input("Hire Date*", datetime.now().date())
                
                with col2:
                    salary = st.number_input("Salary ($)", min_value=0.0, step=1000.0)
                    contact = st.text_input("Contact Number")
                    emergency = st.text_input("Emergency Contact")
                
                add_staff_submitted = st.form_submit_button("Add Staff")
                
                if add_staff_submitted:
                    if selected_user == 0 or not department or not position:
                        st.error("Please fill in all required fields.")
                    else:
                        # Animation
                        with st.spinner("Adding staff record..."):
                            time.sleep(1)  # Simple animation delay
                        
                        # Add staff record
                        staff_id = database.insert_record(
                            "Staff",
                            {
                                "user_id": selected_user,
                                "department": department,
                                "position": position,
                                "hire_date": hire_date.strftime('%Y-%m-%d'),
                                "salary": salary if salary > 0 else None,
                                "contact_number": contact,
                                "emergency_contact": emergency,
                                "status": "active"
                            }
                        )
                        
                        # Get user info for the audit log
                        user_info = users_without_staff[users_without_staff['user_id'] == selected_user].iloc[0]
                        
                        # Record in audit log
                        audit.record_activity(
                            st.session_state.user_id,
                            "Staff Added",
                            f"Added staff record for {user_info['full_name']} (ID: {staff_id})"
                        )
                        
                        st.success(f"Staff added successfully! Staff ID: {staff_id}")
                        time.sleep(1)
                        st.rerun()
    
    with tab3:
        st.subheader("Staff Scheduling")
        
        st.info("Staff scheduling functionality will be implemented in future updates. This would include shift management, time off requests, and staff availability tracking.")
        
        # Placeholder for staff scheduling
        st.write("### Current Staff Availability")
        
        # Get active staff
        active_staff = database.query_to_dataframe(
            """
            SELECT 
                s.staff_id, 
                u.full_name, 
                s.department, 
                s.position
            FROM Staff s
            JOIN Users u ON s.user_id = u.user_id
            WHERE s.status = 'active'
            ORDER BY s.department, u.full_name
            """
        )
        
        if not active_staff.empty:
            # Group by department
            departments = active_staff['department'].unique()
            
            for dept in departments:
                st.write(f"#### {dept}")
                
                dept_staff = active_staff[active_staff['department'] == dept]
                
                # Display as a simple table
                dept_display = dept_staff[['full_name', 'position']]
                dept_display.columns = ['Name', 'Position']
                
                st.dataframe(dept_display, use_container_width=True)
        else:
            st.warning("No active staff members found.")
        
        # Placeholder for schedule creator
        st.write("### Schedule Creator")
        st.write("This feature would allow creating and managing staff schedules.")
        
        # Simple date selection
        schedule_date = st.date_input("Select Date", datetime.now().date())
        
        # In a real implementation, this would show a week or month view,
        # allow assigning shifts to staff, etc.
        st.write(f"Selected date: {schedule_date.strftime('%A, %B %d, %Y')}")
        
        if st.button("Create Schedule (placeholder)"):
            st.success("This is a placeholder for the scheduling functionality that will be implemented in future updates.")
