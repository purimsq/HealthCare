import streamlit as st
import database
import hashlib
import pandas as pd
import time
from datetime import datetime
import audit
import os
from PIL import Image

def hash_password(password):
    """Hash a password for storing."""
    return hashlib.sha256(password.encode()).hexdigest()

def create_admin_form():
    """Display and handle the admin creation form."""
    # Add hospital logo - check both possible locations
    logo_path = None
    if os.path.exists("hospital_logo.png"):
        logo_path = "hospital_logo.png"
    elif os.path.exists("static/hospital_logo.png"):
        logo_path = "static/hospital_logo.png"
    
    if logo_path:
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.image(logo_path, width=250)
    
    st.subheader("Create Administrator Account")
    
    with st.form("admin_creation_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            username = st.text_input("Admin Username*")
            email = st.text_input("Admin Email*")
            full_name = st.text_input("Full Name*")
        
        with col2:
            password = st.text_input("Password*", type="password")
            confirm_password = st.text_input("Confirm Password*", type="password")
        
        submitted = st.form_submit_button("Create Admin")
        
        if submitted:
            # Validate inputs
            if not username or not email or not full_name or not password:
                st.error("Please fill in all required fields.")
                return
            
            if password != confirm_password:
                st.error("Passwords do not match.")
                return
            
            # Animation
            with st.spinner("Creating admin account..."):
                time.sleep(1.5)  # Simple animation delay
            
            # Hash password
            hashed_password = hash_password(password)
            
            # Save admin to database
            admin_id = database.insert_record(
                "Users",
                {
                    "username": username,
                    "password": hashed_password,
                    "email": email,
                    "full_name": full_name,
                    "role": "admin",
                    "created_at": datetime.now(),
                    "status": "active"
                }
            )
            
            # Record in audit log
            audit.record_activity(None, "Admin Created", f"Initial admin account created: {username}")
            
            st.success("Admin account created successfully! You can now log in.")
            
            # Update session state
            st.session_state.admin_exists = True
            
            # Rerun the app to show login form
            time.sleep(1)
            st.rerun()

def admin_settings():
    """Admin settings page."""
    st.header("Admin Settings")
    
    tab1, tab2, tab3 = st.tabs(["User Management", "System Settings", "Backup & Restore"])
    
    with tab1:
        st.subheader("User Management")
        
        # Display all users
        users_df = database.query_to_dataframe(
            """
            SELECT user_id, username, email, full_name, role, created_at, last_login, status 
            FROM Users
            ORDER BY created_at DESC
            """
        )
        
        if users_df.empty:
            st.info("No users found.")
        else:
            # Format dates
            users_df['created_at'] = pd.to_datetime(users_df['created_at']).dt.strftime('%Y-%m-%d %H:%M')
            users_df['last_login'] = pd.to_datetime(users_df['last_login']).dt.strftime('%Y-%m-%d %H:%M')
            
            st.dataframe(users_df, use_container_width=True)
        
        # User actions
        st.subheader("User Actions")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Add new user
            st.write("Add New User")
            
            with st.form("add_user_form"):
                new_username = st.text_input("Username")
                new_email = st.text_input("Email")
                new_full_name = st.text_input("Full Name")
                new_password = st.text_input("Password", type="password")
                new_role = st.selectbox("Role", ['admin', 'doctor', 'nurse', 'receptionist', 'pharmacist', 'staff'])
                
                add_user_submitted = st.form_submit_button("Add User")
                
                if add_user_submitted:
                    if not new_username or not new_email or not new_full_name or not new_password:
                        st.error("Please fill in all required fields.")
                    else:
                        # Check if username or email already exists
                        username_exists = database.fetch_one(
                            "SELECT COUNT(*) FROM Users WHERE username = ?", 
                            (new_username,)
                        )[0] > 0
                        
                        email_exists = database.fetch_one(
                            "SELECT COUNT(*) FROM Users WHERE email = ?", 
                            (new_email,)
                        )[0] > 0
                        
                        if username_exists:
                            st.error("Username already exists.")
                        elif email_exists:
                            st.error("Email already registered.")
                        else:
                            # Hash password
                            hashed_password = hash_password(new_password)
                            
                            # Save user to database
                            user_id = database.insert_record(
                                "Users",
                                {
                                    "username": new_username,
                                    "password": hashed_password,
                                    "email": new_email,
                                    "full_name": new_full_name,
                                    "role": new_role,
                                    "created_at": datetime.now(),
                                    "status": "active"
                                }
                            )
                            
                            # Record in audit log
                            audit.record_activity(
                                st.session_state.user_id, 
                                "User Created", 
                                f"Admin created new user: {new_username} with role: {new_role}"
                            )
                            
                            st.success("User added successfully!")
                            time.sleep(1)
                            st.rerun()
        
        with col2:
            # Modify existing user
            st.write("Modify Existing User")
            
            with st.form("modify_user_form"):
                user_ids = users_df['user_id'].tolist()
                usernames = users_df['username'].tolist()
                
                # Create a dictionary of user_id to username for selection
                user_options = {uid: username for uid, username in zip(user_ids, usernames)}
                
                # Add a placeholder entry
                user_options[0] = "Select a user"
                
                selected_user_id = st.selectbox(
                    "Select User",
                    options=list(user_options.keys()),
                    format_func=lambda x: user_options[x]
                )
                
                action = st.selectbox(
                    "Action",
                    ["Change Status", "Reset Password", "Delete User"]
                )
                
                if action == "Change Status":
                    new_status = st.selectbox("New Status", ["active", "inactive", "suspended"])
                elif action == "Reset Password":
                    new_password = st.text_input("New Password", type="password")
                
                modify_user_submitted = st.form_submit_button("Apply Change")
                
                if modify_user_submitted:
                    if selected_user_id == 0:
                        st.error("Please select a user.")
                    else:
                        # Check if user is trying to modify themselves
                        if selected_user_id == st.session_state.user_id and (action == "Change Status" or action == "Delete User"):
                            st.error("You cannot modify your own account status or delete your own account.")
                        else:
                            # Animation
                            with st.spinner("Applying changes..."):
                                time.sleep(1)  # Simple animation delay
                            
                            if action == "Change Status":
                                database.update_record(
                                    "Users",
                                    {"status": new_status},
                                    {"user_id": selected_user_id}
                                )
                                
                                audit.record_activity(
                                    st.session_state.user_id,
                                    "User Status Changed",
                                    f"Admin changed status of user ID {selected_user_id} to {new_status}"
                                )
                                
                                st.success(f"User status updated to {new_status}!")
                            
                            elif action == "Reset Password":
                                if not new_password:
                                    st.error("Please enter a new password.")
                                else:
                                    hashed_password = hash_password(new_password)
                                    
                                    database.update_record(
                                        "Users",
                                        {"password": hashed_password},
                                        {"user_id": selected_user_id}
                                    )
                                    
                                    audit.record_activity(
                                        st.session_state.user_id,
                                        "Password Reset",
                                        f"Admin reset password for user ID {selected_user_id}"
                                    )
                                    
                                    st.success("Password reset successfully!")
                            
                            elif action == "Delete User":
                                # Check if user has associated records
                                has_records = database.fetch_one(
                                    """
                                    SELECT COUNT(*) FROM (
                                        SELECT user_id FROM Staff WHERE user_id = ?
                                        UNION ALL
                                        SELECT doctor_id FROM Appointments WHERE doctor_id = ?
                                        UNION ALL
                                        SELECT doctor_id FROM MedicalHistory WHERE doctor_id = ?
                                        UNION ALL
                                        SELECT doctor_id FROM Prescriptions WHERE doctor_id = ?
                                    )
                                    """,
                                    (selected_user_id, selected_user_id, selected_user_id, selected_user_id)
                                )[0] > 0
                                
                                if has_records:
                                    st.error("This user has associated records. Deactivate the account instead of deleting.")
                                else:
                                    # Delete user
                                    database.delete_record(
                                        "Users",
                                        {"user_id": selected_user_id}
                                    )
                                    
                                    audit.record_activity(
                                        st.session_state.user_id,
                                        "User Deleted",
                                        f"Admin deleted user ID {selected_user_id}"
                                    )
                                    
                                    st.success("User deleted successfully!")
                            
                            time.sleep(1)
                            st.rerun()
    
    with tab2:
        st.subheader("System Settings")
        st.info("System settings functionality will be implemented in future updates.")
        
    with tab3:
        st.subheader("Backup & Restore")
        st.info("Backup and restore functionality will be implemented in future updates.")
