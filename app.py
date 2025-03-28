import streamlit as st
import sqlite3
import pandas as pd
import time
from datetime import datetime
import os

# Import modules
import database
import auth
import admin
import patient
import appointment
import billing
import inventory
import pharmacy
import staff
import reports
import audit
import utils

# Initialize database
database.init_db()

# Set page config
st.set_page_config(
    page_title="Hospital Management System",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize session state variables if they don't exist
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'user_id' not in st.session_state:
    st.session_state.user_id = None
if 'username' not in st.session_state:
    st.session_state.username = None
if 'role' not in st.session_state:
    st.session_state.role = None
if 'admin_exists' not in st.session_state:
    st.session_state.admin_exists = False
if 'login_time' not in st.session_state:
    st.session_state.login_time = None

# Check if admin exists
st.session_state.admin_exists = auth.check_admin_exists()

# Title
st.title("🏥 Hospital Management System")

# If user is not logged in
if not st.session_state.logged_in:
    # Check if admin exists
    if not st.session_state.admin_exists:
        st.warning("No admin account exists. You must create an admin account first.")
        admin.create_admin_form()
    else:
        # Login/Register tabs
        tab1, tab2 = st.tabs(["Login", "Register"])
        
        with tab1:
            auth.login_form()
            
        with tab2:
            auth.register_form()
else:
    # Record user activity
    if st.session_state.login_time:
        audit.record_activity(st.session_state.user_id, "Active", f"Session duration: {utils.format_time_difference(st.session_state.login_time, datetime.now())}")
    
    # Sidebar with navigation
    with st.sidebar:
        # Apply beige background to sidebar
        st.markdown("""
        <style>
        [data-testid="stSidebar"] {
            background-color: #f0e6d2;
        }
        </style>
        """, unsafe_allow_html=True)
        
        st.write(f"Welcome, **{st.session_state.username}** ({st.session_state.role})")
        st.write(f"Login time: {st.session_state.login_time.strftime('%Y-%m-%d %H:%M:%S')}")
        
        st.divider()
        
        # Navigation based on role
        if st.session_state.role == "admin":
            selected = st.radio(
                "Navigation", 
                ["Dashboard", "Patients", "Appointments", "Billing", "Inventory", 
                 "Pharmacy", "Staff Management", "Reports", "Audit Logs", "Admin Settings"]
            )
        elif st.session_state.role == "doctor":
            selected = st.radio(
                "Navigation", 
                ["Dashboard", "My Patients", "Appointments", "Medical Records"]
            )
        elif st.session_state.role == "nurse":
            selected = st.radio(
                "Navigation", 
                ["Dashboard", "Patients", "Appointments"]
            )
        elif st.session_state.role == "receptionist":
            selected = st.radio(
                "Navigation", 
                ["Dashboard", "Patient Registration", "Appointments", "Billing"]
            )
        elif st.session_state.role == "pharmacist":
            selected = st.radio(
                "Navigation", 
                ["Dashboard", "Pharmacy", "Inventory"]
            )
        else:
            selected = st.radio(
                "Navigation", 
                ["Dashboard"]
            )
        
        st.divider()
        
        # Logout button
        if st.button("Logout"):
            audit.record_activity(st.session_state.user_id, "Logged Out", "User logged out")
            auth.logout()
            st.rerun()
    
    # Main content based on navigation
    if selected == "Dashboard":
        st.header("Dashboard")
        
        # Create dashboard layout
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.subheader("Patient Statistics")
            patient_count = patient.get_patient_count()
            st.metric("Total Patients", patient_count)
            
            # Today's appointments
            today_appointments = appointment.get_appointments_count_for_today()
            st.metric("Today's Appointments", today_appointments)
        
        with col2:
            st.subheader("Inventory Status")
            low_stock_count = inventory.get_low_stock_count()
            st.metric("Low Stock Items", low_stock_count)
            
            # Today's revenue
            today_revenue = billing.get_revenue_for_today()
            st.metric("Today's Revenue", utils.format_currency(today_revenue))
        
        with col3:
            st.subheader("Staff Status")
            active_staff = staff.get_active_staff_count()
            total_staff = staff.get_total_staff_count()
            st.metric("Active Staff", f"{active_staff}/{total_staff}")
            
            # Pending prescriptions
            pending_prescriptions = pharmacy.get_pending_prescriptions_count()
            st.metric("Pending Prescriptions", pending_prescriptions)
        
        # Recent activities - Only visible to admin users
        if st.session_state.role == "admin":
            st.subheader("Recent Activities")
            recent_activities = audit.get_recent_activities(limit=10)
            
            if recent_activities.empty:
                st.info("No recent activities found.")
            else:
                st.dataframe(recent_activities, use_container_width=True)
            
    elif selected == "Patients":
        patient.patient_management()
        
    elif selected == "My Patients":
        patient.my_patients(st.session_state.user_id)
        
    elif selected == "Patient Registration":
        patient.patient_registration()
        
    elif selected == "Appointments":
        appointment.appointment_management()
        
    elif selected == "Medical Records":
        patient.medical_records()
        
    elif selected == "Billing":
        billing.billing_management()
        
    elif selected == "Inventory":
        inventory.inventory_management()
        
    elif selected == "Pharmacy":
        pharmacy.pharmacy_management()
        
    elif selected == "Staff Management":
        staff.staff_management()
        
    elif selected == "Reports":
        reports.reports_management()
        
    elif selected == "Audit Logs":
        audit.audit_logs()
        
    elif selected == "Admin Settings":
        admin.admin_settings()

# Add footer
st.markdown("---")
st.markdown("<div style='text-align: center'>© 2025 Hospital Management System</div>", unsafe_allow_html=True)
