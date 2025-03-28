import streamlit as st
import database
import pandas as pd
from datetime import datetime, timedelta
import time
import audit

def get_appointments_count_for_today():
    """Get the count of appointments scheduled for today."""
    today = datetime.now().strftime('%Y-%m-%d')
    result = database.fetch_one(
        "SELECT COUNT(*) FROM Appointments WHERE appointment_date = ?",
        (today,)
    )
    return result[0] if result else 0

def appointment_management():
    """Appointment management page."""
    st.header("Appointment Management")
    
    tab1, tab2, tab3 = st.tabs(["Appointment List", "Schedule Appointment", "Appointment Calendar"])
    
    with tab1:
        st.subheader("Appointment List")
        
        # Filters
        col1, col2, col3 = st.columns(3)
        
        with col1:
            date_filter = st.date_input("Date", datetime.now())
        
        with col2:
            status_filter = st.selectbox("Status", ["All", "Scheduled", "Completed", "Cancelled", "No-show"])
        
        with col3:
            if st.session_state.role in ['admin', 'receptionist']:
                doctor_filter = st.selectbox(
                    "Doctor",
                    ["All"] + [row[0] for row in database.fetch_all(
                        "SELECT full_name FROM Users WHERE role = 'doctor' ORDER BY full_name"
                    )]
                )
            else:
                doctor_filter = "Current User"
        
        # Build query
        query = """
        SELECT 
            a.appointment_id, 
            p.first_name || ' ' || p.last_name as patient_name,
            u.full_name as doctor_name,
            a.appointment_date,
            a.appointment_time,
            a.status,
            a.reason
        FROM Appointments a
        JOIN Patients p ON a.patient_id = p.patient_id
        JOIN Users u ON a.doctor_id = u.user_id
        """
        
        params = []
        where_clauses = []
        
        # Add date filter
        date_str = date_filter.strftime('%Y-%m-%d')
        where_clauses.append("a.appointment_date = ?")
        params.append(date_str)
        
        # Add status filter
        if status_filter != "All":
            where_clauses.append("a.status = ?")
            params.append(status_filter.lower())
        
        # Add doctor filter
        if doctor_filter != "All" and doctor_filter != "Current User":
            doctor_id = database.fetch_one(
                "SELECT user_id FROM Users WHERE full_name = ?",
                (doctor_filter,)
            )[0]
            where_clauses.append("a.doctor_id = ?")
            params.append(doctor_id)
        elif doctor_filter == "Current User" and st.session_state.role == 'doctor':
            where_clauses.append("a.doctor_id = ?")
            params.append(st.session_state.user_id)
        
        # Finalize query
        if where_clauses:
            query += " WHERE " + " AND ".join(where_clauses)
        
        query += " ORDER BY a.appointment_date, a.appointment_time"
        
        # Execute query
        appointments_df = database.query_to_dataframe(query, params)
        
        if appointments_df.empty:
            st.info("No appointments found matching your criteria.")
        else:
            # Format dates and times
            appointments_df['appointment_date'] = pd.to_datetime(appointments_df['appointment_date']).dt.strftime('%Y-%m-%d')
            
            # Rename columns for display
            display_df = appointments_df.rename(columns={
                'appointment_id': 'ID',
                'patient_name': 'Patient',
                'doctor_name': 'Doctor',
                'appointment_date': 'Date',
                'appointment_time': 'Time',
                'status': 'Status',
                'reason': 'Reason'
            })
            
            st.dataframe(display_df, use_container_width=True)
        
        # Appointment details and actions
        if not appointments_df.empty:
            st.subheader("Appointment Actions")
            
            appointment_options = [f"ID: {row['appointment_id']} - {row['appointment_date']} {row['appointment_time']} - {row['patient_name']}" 
                                  for _, row in appointments_df.iterrows()]
            
            selected_appointment = st.selectbox("Select Appointment", ["Select an appointment"] + appointment_options)
            
            if selected_appointment != "Select an appointment":
                appointment_id = int(selected_appointment.split("ID: ")[1].split(" -")[0])
                
                # Get appointment details
                appointment = database.fetch_one(
                    """
                    SELECT 
                        a.appointment_id, 
                        a.patient_id,
                        p.first_name || ' ' || p.last_name as patient_name,
                        a.doctor_id,
                        u.full_name as doctor_name,
                        a.appointment_date,
                        a.appointment_time,
                        a.status,
                        a.reason,
                        a.notes,
                        a.created_at
                    FROM Appointments a
                    JOIN Patients p ON a.patient_id = p.patient_id
                    JOIN Users u ON a.doctor_id = u.user_id
                    WHERE a.appointment_id = ?
                    """,
                    (appointment_id,)
                )
                
                if appointment:
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.write(f"**Patient:** {appointment[2]}")
                        st.write(f"**Doctor:** {appointment[4]}")
                        st.write(f"**Date:** {appointment[5]}")
                        st.write(f"**Time:** {appointment[6]}")
                    
                    with col2:
                        st.write(f"**Status:** {appointment[7]}")
                        st.write(f"**Reason:** {appointment[8] or 'Not specified'}")
                        st.write(f"**Notes:** {appointment[9] or 'No notes'}")
                        st.write(f"**Created:** {appointment[10]}")
                    
                    # Action buttons
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        if st.button("Update Status"):
                            st.session_state.update_appointment_status = appointment_id
                            st.rerun()
                    
                    with col2:
                        if st.button("Edit Appointment"):
                            st.session_state.edit_appointment = appointment_id
                            st.rerun()
                    
                    with col3:
                        if appointment[7] != "cancelled" and appointment[7] != "completed":
                            if st.button("Cancel Appointment", type="primary"):
                                # Animation
                                with st.spinner("Cancelling appointment..."):
                                    time.sleep(1)  # Simple animation delay
                                
                                # Update appointment status
                                database.update_record(
                                    "Appointments",
                                    {"status": "cancelled"},
                                    {"appointment_id": appointment_id}
                                )
                                
                                # Record in audit log
                                audit.record_activity(
                                    st.session_state.user_id,
                                    "Appointment Cancelled",
                                    f"Cancelled appointment ID {appointment_id}"
                                )
                                
                                st.success("Appointment cancelled successfully!")
                                time.sleep(1)
                                st.rerun()
                    
                    # Handle status update
                    if hasattr(st.session_state, 'update_appointment_status') and st.session_state.update_appointment_status == appointment_id:
                        with st.form("update_appointment_status_form"):
                            new_status = st.selectbox(
                                "New Status", 
                                ["scheduled", "completed", "cancelled", "no-show"],
                                index=["scheduled", "completed", "cancelled", "no-show"].index(appointment[7])
                            )
                            
                            additional_notes = st.text_area("Additional Notes")
                            
                            update_status_submitted = st.form_submit_button("Update Status")
                            
                            if update_status_submitted:
                                # Animation
                                with st.spinner("Updating appointment status..."):
                                    time.sleep(1)  # Simple animation delay
                                
                                # Update appointment
                                database.update_record(
                                    "Appointments",
                                    {
                                        "status": new_status,
                                        "notes": (appointment[9] or "") + "\n" + additional_notes if additional_notes else appointment[9]
                                    },
                                    {"appointment_id": appointment_id}
                                )
                                
                                # Record in audit log
                                audit.record_activity(
                                    st.session_state.user_id,
                                    "Appointment Status Updated",
                                    f"Updated status of appointment ID {appointment_id} to {new_status}"
                                )
                                
                                st.success("Appointment status updated successfully!")
                                
                                # Clear the session state and rerun
                                del st.session_state.update_appointment_status
                                time.sleep(1)
                                st.rerun()
                    
                    # Handle appointment edit
                    if hasattr(st.session_state, 'edit_appointment') and st.session_state.edit_appointment == appointment_id:
                        with st.form("edit_appointment_form"):
                            # Get patient list
                            patients_df = database.query_to_dataframe(
                                "SELECT patient_id, first_name || ' ' || last_name as patient_name FROM Patients WHERE status = 'active'"
                            )
                            patient_options = {row['patient_id']: row['patient_name'] for _, row in patients_df.iterrows()}
                            
                            # Get doctor list
                            doctors_df = database.query_to_dataframe(
                                "SELECT user_id, full_name FROM Users WHERE role = 'doctor'"
                            )
                            doctor_options = {row['user_id']: row['full_name'] for _, row in doctors_df.iterrows()}
                            
                            col1, col2 = st.columns(2)
                            
                            with col1:
                                selected_patient = st.selectbox(
                                    "Patient",
                                    options=list(patient_options.keys()),
                                    format_func=lambda x: patient_options[x],
                                    index=list(patient_options.keys()).index(appointment[1]) if appointment[1] in patient_options else 0
                                )
                            
                            with col2:
                                selected_doctor = st.selectbox(
                                    "Doctor",
                                    options=list(doctor_options.keys()),
                                    format_func=lambda x: doctor_options[x],
                                    index=list(doctor_options.keys()).index(appointment[3]) if appointment[3] in doctor_options else 0
                                )
                            
                            col1, col2 = st.columns(2)
                            
                            with col1:
                                new_date = st.date_input(
                                    "Appointment Date",
                                    datetime.strptime(appointment[5], '%Y-%m-%d')
                                )
                            
                            with col2:
                                new_time = st.time_input(
                                    "Appointment Time",
                                    datetime.strptime(appointment[6], '%H:%M:%S').time()
                                )
                            
                            new_reason = st.text_input("Reason", appointment[8] or "")
                            new_notes = st.text_area("Notes", appointment[9] or "")
                            
                            edit_appointment_submitted = st.form_submit_button("Update Appointment")
                            
                            if edit_appointment_submitted:
                                # Animation
                                with st.spinner("Updating appointment..."):
                                    time.sleep(1)  # Simple animation delay
                                
                                # Update appointment
                                database.update_record(
                                    "Appointments",
                                    {
                                        "patient_id": selected_patient,
                                        "doctor_id": selected_doctor,
                                        "appointment_date": new_date.strftime('%Y-%m-%d'),
                                        "appointment_time": new_time.strftime('%H:%M:%S'),
                                        "reason": new_reason,
                                        "notes": new_notes
                                    },
                                    {"appointment_id": appointment_id}
                                )
                                
                                # Record in audit log
                                audit.record_activity(
                                    st.session_state.user_id,
                                    "Appointment Updated",
                                    f"Updated details of appointment ID {appointment_id}"
                                )
                                
                                st.success("Appointment updated successfully!")
                                
                                # Clear the session state and rerun
                                del st.session_state.edit_appointment
                                time.sleep(1)
                                st.rerun()
    
    with tab2:
        st.subheader("Schedule New Appointment")
        
        # Check if we're scheduling for a specific patient
        patient_id_to_schedule = None
        if hasattr(st.session_state, 'schedule_appointment'):
            patient_id_to_schedule = st.session_state.schedule_appointment
            patient_details = database.fetch_one(
                "SELECT first_name || ' ' || last_name FROM Patients WHERE patient_id = ?",
                (patient_id_to_schedule,)
            )
            if patient_details:
                st.info(f"Scheduling appointment for: {patient_details[0]}")
        
        with st.form("schedule_appointment_form"):
            col1, col2 = st.columns(2)
            
            with col1:
                # Patient selection (if not already selected)
                if patient_id_to_schedule is None:
                    # Get patient list
                    patients_df = database.query_to_dataframe(
                        "SELECT patient_id, first_name || ' ' || last_name as patient_name FROM Patients WHERE status = 'active'"
                    )
                    patient_options = {row['patient_id']: row['patient_name'] for _, row in patients_df.iterrows()}
                    
                    # Add a placeholder
                    patient_options[0] = "Select a patient"
                    
                    selected_patient = st.selectbox(
                        "Patient*",
                        options=list(patient_options.keys()),
                        format_func=lambda x: patient_options[x],
                        index=0
                    )
                else:
                    selected_patient = patient_id_to_schedule
            
            with col2:
                # Doctor selection
                doctors_df = database.query_to_dataframe(
                    "SELECT user_id, full_name FROM Users WHERE role = 'doctor'"
                )
                doctor_options = {row['user_id']: row['full_name'] for _, row in doctors_df.iterrows()}
                
                # Add a placeholder
                doctor_options[0] = "Select a doctor"
                
                selected_doctor = st.selectbox(
                    "Doctor*",
                    options=list(doctor_options.keys()),
                    format_func=lambda x: doctor_options[x],
                    index=0
                )
            
            col1, col2 = st.columns(2)
            
            with col1:
                appointment_date = st.date_input("Appointment Date*", min_value=datetime.now().date())
            
            with col2:
                appointment_time = st.time_input("Appointment Time*")
            
            reason = st.text_input("Reason for Visit")
            notes = st.text_area("Additional Notes")
            
            schedule_submitted = st.form_submit_button("Schedule Appointment")
            
            if schedule_submitted:
                if (patient_id_to_schedule is None and selected_patient == 0) or selected_doctor == 0:
                    st.error("Please select both a patient and a doctor.")
                else:
                    # Check for scheduling conflicts
                    appointment_datetime = datetime.combine(appointment_date, appointment_time)
                    thirty_minutes_later = appointment_datetime + timedelta(minutes=30)
                    
                    conflicts = database.fetch_all(
                        """
                        SELECT COUNT(*) FROM Appointments 
                        WHERE doctor_id = ? 
                        AND appointment_date = ? 
                        AND appointment_time BETWEEN ? AND ?
                        AND status != 'cancelled'
                        """,
                        (
                            selected_doctor, 
                            appointment_date.strftime('%Y-%m-%d'), 
                            appointment_time.strftime('%H:%M:%S'), 
                            thirty_minutes_later.strftime('%H:%M:%S')
                        )
                    )
                    
                    if conflicts[0][0] > 0:
                        st.error("This time slot is already booked for the selected doctor. Please choose a different time.")
                    else:
                        # Animation
                        with st.spinner("Scheduling appointment..."):
                            time.sleep(1)  # Simple animation delay
                        
                        # Insert appointment
                        appointment_id = database.insert_record(
                            "Appointments",
                            {
                                "patient_id": selected_patient if patient_id_to_schedule is None else patient_id_to_schedule,
                                "doctor_id": selected_doctor,
                                "appointment_date": appointment_date.strftime('%Y-%m-%d'),
                                "appointment_time": appointment_time.strftime('%H:%M:%S'),
                                "status": "scheduled",
                                "reason": reason,
                                "notes": notes,
                                "created_at": datetime.now()
                            }
                        )
                        
                        # Record in audit log
                        audit.record_activity(
                            st.session_state.user_id,
                            "Appointment Scheduled",
                            f"Scheduled new appointment (ID: {appointment_id})"
                        )
                        
                        st.success("Appointment scheduled successfully!")
                        
                        # Clear the schedule_appointment state if it exists
                        if hasattr(st.session_state, 'schedule_appointment'):
                            del st.session_state.schedule_appointment
                        
                        time.sleep(1)
                        st.rerun()
    
    with tab3:
        st.subheader("Appointment Calendar")
        
        # Date selection for calendar view
        start_date = st.date_input("Week Starting", datetime.now().date() - timedelta(days=datetime.now().weekday()))
        
        # Calculate the end of the week
        end_date = start_date + timedelta(days=6)
        
        # Get all appointments for the selected week
        appointments_df = database.query_to_dataframe(
            """
            SELECT 
                a.appointment_id, 
                p.first_name || ' ' || p.last_name as patient_name,
                u.full_name as doctor_name,
                a.appointment_date,
                a.appointment_time,
                a.status,
                a.reason
            FROM Appointments a
            JOIN Patients p ON a.patient_id = p.patient_id
            JOIN Users u ON a.doctor_id = u.user_id
            WHERE a.appointment_date BETWEEN ? AND ?
            ORDER BY a.appointment_date, a.appointment_time
            """,
            (start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d'))
        )
        
        if appointments_df.empty:
            st.info(f"No appointments scheduled for the week of {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}.")
        else:
            # Group appointments by date
            appointments_df['appointment_date'] = pd.to_datetime(appointments_df['appointment_date'])
            dates = appointments_df['appointment_date'].dt.date.unique()
            
            # Display appointments for each day
            for date in dates:
                date_str = date.strftime('%A, %B %d, %Y')
                st.write(f"### {date_str}")
                
                day_appointments = appointments_df[appointments_df['appointment_date'].dt.date == date]
                
                # Group by doctor
                doctors = day_appointments['doctor_name'].unique()
                
                for doctor in doctors:
                    st.write(f"**{doctor}**")
                    
                    doctor_appointments = day_appointments[day_appointments['doctor_name'] == doctor]
                    
                    # Create a more concise display
                    for _, row in doctor_appointments.iterrows():
                        time_str = pd.to_datetime(row['appointment_time']).strftime('%H:%M')
                        status_color = {
                            'scheduled': 'blue',
                            'completed': 'green',
                            'cancelled': 'red',
                            'no-show': 'orange'
                        }.get(row['status'], 'gray')
                        
                        st.write(f"- {time_str} - {row['patient_name']} - "
                                f"<span style='color:{status_color}'>{row['status'].upper()}</span>", 
                                unsafe_allow_html=True)
                
                st.divider()
