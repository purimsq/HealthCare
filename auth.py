import streamlit as st
import hashlib
import re
import database
from datetime import datetime
import audit
import time
import os
from PIL import Image
import base64

def hash_password(password):
    """Hash a password for storing."""
    return hashlib.sha256(password.encode()).hexdigest()

def check_admin_exists():
    """Check if at least one admin user exists in the database."""
    result = database.fetch_one("SELECT COUNT(*) FROM Users WHERE role = 'admin'")
    return result[0] > 0

def validate_password(password):
    """Validate password strength."""
    if len(password) < 8:
        return False, "Password must be at least 8 characters long."
    
    if not any(char.isdigit() for char in password):
        return False, "Password must contain at least one digit."
    
    if not any(char.isupper() for char in password):
        return False, "Password must contain at least one uppercase letter."
    
    if not any(char.islower() for char in password):
        return False, "Password must contain at least one lowercase letter."
    
    if not any(char in "!@#$%^&*()-_=+[]{}|;:,.<>?/" for char in password):
        return False, "Password must contain at least one special character."
    
    return True, "Password is strong."

def validate_email(email):
    """Validate email format."""
    pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    if re.match(pattern, email):
        return True
    return False

def get_base64_encoded_image(image_path):
    """Get base64 encoded image for background styling"""
    with open(image_path, "rb") as img_file:
        return base64.b64encode(img_file.read()).decode()

def set_background_image(image_path):
    """Set background image using CSS"""
    encoded_image = get_base64_encoded_image(image_path)
    background_image = f"""
    <style>
    .stApp {{
        background-image: url("data:image/jpg;base64,{encoded_image}");
        background-size: cover;
        background-repeat: no-repeat;
        background-attachment: fixed;
    }}
    .block-container {{
        background-color: rgba(255, 255, 255, 0.85);
        padding: 2rem;
        border-radius: 10px;
    }}
    </style>
    """
    st.markdown(background_image, unsafe_allow_html=True)

def login_form():
    """Display and handle login form."""
    # Add hospital background - check both possible locations
    if os.path.exists("hospital_background.jpg"):
        set_background_image("hospital_background.jpg")
    elif os.path.exists("static/hospital_background.jpg"):
        set_background_image("static/hospital_background.jpg")
    
    st.subheader("Login")
    
    # Create form
    with st.form("login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Login")
        
        if submitted:
            if not username or not password:
                st.error("Please enter both username and password.")
                return
            
            # Check if user exists
            hashed_password = hash_password(password)
            user = database.fetch_one(
                "SELECT user_id, username, role, status FROM Users WHERE username = ? AND password = ?",
                (username, hashed_password)
            )
            
            if user:
                user_id, username, role, status = user
                
                if status != 'active':
                    st.error("Your account is not active. Please contact an administrator.")
                    return
                
                # Animation
                with st.spinner("Logging in..."):
                    time.sleep(1)  # Simple animation delay
                
                # Update last login time
                database.update_record(
                    "Users",
                    {"last_login": datetime.now()},
                    {"user_id": user_id}
                )
                
                # Set session state
                st.session_state.logged_in = True
                st.session_state.user_id = user_id
                st.session_state.username = username
                st.session_state.role = role
                st.session_state.login_time = datetime.now()
                
                # Record login in audit log
                audit.record_activity(user_id, "Logged In", f"User {username} logged in")
                
                # Create user session
                database.insert_record(
                    "UserSessions",
                    {
                        "user_id": user_id,
                        "login_time": datetime.now(),
                        "status": "active"
                    }
                )
                
                st.success("Login successful!")
                st.rerun()
            else:
                st.error("Invalid username or password.")

def register_form():
    """Display and handle user registration form."""
    # Add hospital background if not already done in login_form
    if not any('background-image' in s for s in st.session_state.get('_custom_css', [])):
        if os.path.exists("hospital_background.jpg"):
            set_background_image("hospital_background.jpg")
        elif os.path.exists("static/hospital_background.jpg"):
            set_background_image("static/hospital_background.jpg")
    
    st.subheader("Register")
    
    # Get roles for dropdown (excluding admin role)
    roles = ['doctor', 'nurse', 'receptionist', 'pharmacist', 'staff']
    
    # Create form
    with st.form("register_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            username = st.text_input("Username*")
            email = st.text_input("Email*")
            full_name = st.text_input("Full Name*")
        
        with col2:
            password = st.text_input("Password*", type="password")
            confirm_password = st.text_input("Confirm Password*", type="password")
            role = st.selectbox("Role*", roles)
        
        submitted = st.form_submit_button("Register")
        
        if submitted:
            # Validate inputs
            if not username or not email or not full_name or not password or not confirm_password:
                st.error("Please fill in all required fields.")
                return
            
            if not validate_email(email):
                st.error("Please enter a valid email address.")
                return
            
            if password != confirm_password:
                st.error("Passwords do not match.")
                return
            
            is_valid, password_message = validate_password(password)
            if not is_valid:
                st.error(password_message)
                return
            
            # Check if username or email already exists
            username_exists = database.fetch_one(
                "SELECT COUNT(*) FROM Users WHERE username = ?", 
                (username,)
            )[0] > 0
            
            email_exists = database.fetch_one(
                "SELECT COUNT(*) FROM Users WHERE email = ?", 
                (email,)
            )[0] > 0
            
            if username_exists:
                st.error("Username already exists. Please choose a different one.")
                return
            
            if email_exists:
                st.error("Email already registered. Please use a different email.")
                return
            
            # Animation
            with st.spinner("Creating your account..."):
                time.sleep(1.5)  # Simple animation delay
            
            # Hash password
            hashed_password = hash_password(password)
            
            # Save user to database
            user_id = database.insert_record(
                "Users",
                {
                    "username": username,
                    "password": hashed_password,
                    "email": email,
                    "full_name": full_name,
                    "role": role,
                    "created_at": datetime.now(),
                    "status": "active"
                }
            )
            
            # Record in audit log
            audit.record_activity(None, "User Registered", f"New user {username} registered with role: {role}")
            
            st.success("Registration successful! You can now log in.")

def logout():
    """Log out the current user."""
    if st.session_state.logged_in and st.session_state.user_id:
        # Update user session to inactive
        database.update_record(
            "UserSessions",
            {
                "logout_time": datetime.now(),
                "status": "inactive"
            },
            {
                "user_id": st.session_state.user_id,
                "status": "active"
            }
        )
    
    # Clear session state
    st.session_state.logged_in = False
    st.session_state.user_id = None
    st.session_state.username = None
    st.session_state.role = None
    st.session_state.login_time = None
