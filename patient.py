import streamlit as st
import database
import pandas as pd
from datetime import datetime
import time
import audit

def get_patient_count():
    """Get the total number of patients."""
    result = database.fetch_one("SELECT COUNT(*) FROM Patients WHERE status = 'active'")
    return result[0] if result else 0

def patient_management():
    """Patient management page."""
    st.header("Patient Management")
    
    tab1, tab2, tab3 = st.tabs(["Patient List", "Add Patient", "Medical Records"])
    
    with tab1:
        st.subheader("Patient List")
        
        # Search filters
        col1, col2, col3 = st.columns(3)
        
        with col1:
            search_term = st.text_input("Search by name or ID")
        
        with col2:
            status_filter = st.selectbox("Status", ["All", "Active", "Inactive", "Discharged"])
        
        with col3:
            sort_by = st.selectbox("Sort by", ["Registration Date", "Last Name", "First Name", "ID"])
        
        # Prepare query
        query = """
        SELECT 
            patient_id, 
            first_name, 
            last_name, 
            date_of_birth, 
            gender, 
            contact_number, 
            registration_date, 
            status
        FROM Patients
        """
        
        params = []
        where_clauses = []
        
        if search_term:
            where_clauses.append("(first_name LIKE ? OR last_name LIKE ? OR patient_id LIKE ?)")
            params.extend([f"%{search_term}%", f"%{search_term}%", f"%{search_term}%"])
        
        if status_filter != "All":
            where_clauses.append("status = ?")
            params.append(status_filter.lower())
        
        if where_clauses:
            query += " WHERE " + " AND ".join(where_clauses)
        
        # Add sorting
        if sort_by == "Registration Date":
            query += " ORDER BY registration_date DESC"
        elif sort_by == "Last Name":
            query += " ORDER BY last_name ASC"
        elif sort_by == "First Name":
            query += " ORDER BY first_name ASC"
        elif sort_by == "ID":
            query += " ORDER BY patient_id ASC"
        
        # Execute query
        patients_df = database.query_to_dataframe(query, params)
        
        if patients_df.empty:
            st.info("No patients found matching your criteria.")
        else:
            # Format dates
            patients_df['date_of_birth'] = pd.to_datetime(patients_df['date_of_birth']).dt.strftime('%Y-%m-%d')
            patients_df['registration_date'] = pd.to_datetime(patients_df['registration_date']).dt.strftime('%Y-%m-%d')
            
            # Add a full name column
            patients_df['full_name'] = patients_df['first_name'] + ' ' + patients_df['last_name']
            
            # Reorder columns
            display_df = patients_df[['patient_id', 'full_name', 'gender', 'date_of_birth', 'contact_number', 'registration_date', 'status']]
            
            # Rename columns for display
            display_df.columns = ['ID', 'Name', 'Gender', 'Date of Birth', 'Contact', 'Registration Date', 'Status']
            
            st.dataframe(display_df, use_container_width=True)
        
        # Patient details section
        st.subheader("Patient Details")
        
        if not patients_df.empty:
            patient_ids = patients_df['patient_id'].tolist()
            patient_names = [f"{row['first_name']} {row['last_name']} (ID: {row['patient_id']})" for _, row in patients_df.iterrows()]
            
            selected_index = st.selectbox(
                "Select Patient", 
                range(len(patient_ids)),
                format_func=lambda i: patient_names[i] if i < len(patient_names) else ""
            )
            
            if selected_index is not None and selected_index < len(patient_ids):
                selected_patient_id = patient_ids[selected_index]
                
                # Get detailed patient info
                patient_details = database.fetch_one(
                    """
                    SELECT * FROM Patients WHERE patient_id = ?
                    """,
                    (selected_patient_id,)
                )
                
                if patient_details:
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.write(f"**ID:** {patient_details[0]}")
                        st.write(f"**Name:** {patient_details[1]} {patient_details[2]}")
                        st.write(f"**Date of Birth:** {patient_details[3]}")
                        st.write(f"**Gender:** {patient_details[4]}")
                        st.write(f"**Blood Group:** {patient_details[5] or 'Not specified'}")
                    
                    with col2:
                        st.write(f"**Contact:** {patient_details[7]}")
                        st.write(f"**Email:** {patient_details[8] or 'Not specified'}")
                        st.write(f"**Emergency Contact:** {patient_details[9] or 'Not specified'} ({patient_details[10] or 'No number'})")
                        st.write(f"**Registration Date:** {patient_details[11]}")
                        st.write(f"**Status:** {patient_details[13]}")
                    
                    st.write(f"**Address:** {patient_details[6] or 'Not specified'}")
                    st.write(f"**Notes:** {patient_details[12] or 'No notes'}")
                    
                    # Patient actions
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        if st.button("Update Patient"):
                            st.session_state.update_patient = selected_patient_id
                            st.rerun()
                    
                    with col2:
                        if st.button("View Medical History"):
                            st.session_state.view_history = selected_patient_id
                            st.rerun()
                    
                    with col3:
                        if st.button("Schedule Appointment"):
                            st.session_state.schedule_appointment = selected_patient_id
                            st.rerun()
                
                # Check if we should display the update form
                if hasattr(st.session_state, 'update_patient') and st.session_state.update_patient == selected_patient_id:
                    st.subheader("Update Patient Information")
                    
                    with st.form("update_patient_form"):
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            updated_first_name = st.text_input("First Name", patient_details[1])
                            updated_last_name = st.text_input("Last Name", patient_details[2])
                            updated_dob = st.date_input("Date of Birth", datetime.strptime(patient_details[3], '%Y-%m-%d'))
                            updated_gender = st.selectbox("Gender", ["Male", "Female", "Other"], index=["Male", "Female", "Other"].index(patient_details[4]))
                            updated_blood_group = st.text_input("Blood Group", patient_details[5] or "")
                        
                        with col2:
                            updated_address = st.text_area("Address", patient_details[6] or "")
                            updated_contact = st.text_input("Contact Number", patient_details[7])
                            updated_email = st.text_input("Email", patient_details[8] or "")
                            updated_emergency_contact = st.text_input("Emergency Contact", patient_details[9] or "")
                            updated_emergency_number = st.text_input("Emergency Contact Number", patient_details[10] or "")
                        
                        updated_notes = st.text_area("Notes", patient_details[12] or "")
                        updated_status = st.selectbox("Status", ["active", "inactive", "discharged"], index=["active", "inactive", "discharged"].index(patient_details[13]))
                        
                        update_submitted = st.form_submit_button("Update Patient")
                        
                        if update_submitted:
                            # Animation
                            with st.spinner("Updating patient information..."):
                                time.sleep(1)  # Simple animation delay
                            
                            # Update patient record
                            database.update_record(
                                "Patients",
                                {
                                    "first_name": updated_first_name,
                                    "last_name": updated_last_name,
                                    "date_of_birth": updated_dob,
                                    "gender": updated_gender,
                                    "blood_group": updated_blood_group,
                                    "address": updated_address,
                                    "contact_number": updated_contact,
                                    "email": updated_email,
                                    "emergency_contact": updated_emergency_contact,
                                    "emergency_contact_number": updated_emergency_number,
                                    "notes": updated_notes,
                                    "status": updated_status
                                },
                                {"patient_id": selected_patient_id}
                            )
                            
                            # Record in audit log
                            audit.record_activity(
                                st.session_state.user_id,
                                "Patient Updated",
                                f"Updated information for patient ID {selected_patient_id}"
                            )
                            
                            st.success("Patient information updated successfully!")
                            
                            # Clear the session state and rerun
                            del st.session_state.update_patient
                            time.sleep(1)
                            st.rerun()
    
    with tab2:
        st.subheader("Add New Patient")
        
        with st.form("add_patient_form"):
            col1, col2 = st.columns(2)
            
            with col1:
                first_name = st.text_input("First Name*")
                last_name = st.text_input("Last Name*")
                dob = st.date_input("Date of Birth*")
                gender = st.selectbox("Gender*", ["Male", "Female", "Other"])
                blood_group = st.text_input("Blood Group")
            
            with col2:
                address = st.text_area("Address")
                contact_number = st.text_input("Contact Number*")
                email = st.text_input("Email")
                emergency_contact = st.text_input("Emergency Contact")
                emergency_number = st.text_input("Emergency Contact Number")
            
            notes = st.text_area("Notes")
            
            add_patient_submitted = st.form_submit_button("Add Patient")
            
            if add_patient_submitted:
                if not first_name or not last_name or not contact_number:
                    st.error("Please fill in all required fields.")
                else:
                    # Animation
                    with st.spinner("Adding new patient..."):
                        time.sleep(1)  # Simple animation delay
                    
                    # Insert patient record
                    patient_id = database.insert_record(
                        "Patients",
                        {
                            "first_name": first_name,
                            "last_name": last_name,
                            "date_of_birth": dob,
                            "gender": gender,
                            "blood_group": blood_group,
                            "address": address,
                            "contact_number": contact_number,
                            "email": email,
                            "emergency_contact": emergency_contact,
                            "emergency_contact_number": emergency_number,
                            "registration_date": datetime.now(),
                            "notes": notes,
                            "status": "active"
                        }
                    )
                    
                    # Record in audit log
                    audit.record_activity(
                        st.session_state.user_id,
                        "Patient Added",
                        f"Added new patient: {first_name} {last_name} (ID: {patient_id})"
                    )
                    
                    st.success(f"Patient added successfully! Patient ID: {patient_id}")
                    time.sleep(1)
                    st.rerun()
    
    with tab3:
        medical_records()

def medical_records(patient_id=None):
    """Medical records page."""
    st.subheader("Medical Records")
    
    # If a specific patient_id was passed, use that
    if patient_id:
        patient_to_view = patient_id
    else:
        # Get all patients
        patients_df = database.query_to_dataframe(
            """
            SELECT patient_id, first_name, last_name
            FROM Patients
            WHERE status = 'active'
            ORDER BY last_name, first_name
            """
        )
        
        if patients_df.empty:
            st.info("No patients found.")
            return
        
        # Create selection options
        patient_options = [f"{row['first_name']} {row['last_name']} (ID: {row['patient_id']})" for _, row in patients_df.iterrows()]
        
        # Add a "Select patient" option at the beginning
        patient_options.insert(0, "Select patient")
        
        selected_option = st.selectbox("Select Patient", patient_options)
        
        if selected_option == "Select patient":
            st.info("Please select a patient to view their medical records.")
            return
        
        # Extract patient_id from selection
        patient_to_view = int(selected_option.split("ID: ")[1].rstrip(')'))
    
    # Get patient details
    patient = database.fetch_one(
        "SELECT first_name, last_name FROM Patients WHERE patient_id = ?",
        (patient_to_view,)
    )
    
    if patient:
        patient_name = f"{patient[0]} {patient[1]}"
        st.write(f"**Medical Records for:** {patient_name} (ID: {patient_to_view})")
        
        # Get medical history
        medical_history_df = database.query_to_dataframe(
            """
            SELECT m.record_id, m.diagnosis, m.treatment, u.full_name as doctor, m.date, m.notes
            FROM MedicalHistory m
            JOIN Users u ON m.doctor_id = u.user_id
            WHERE m.patient_id = ?
            ORDER BY m.date DESC
            """,
            (patient_to_view,)
        )
        
        if medical_history_df.empty:
            st.info("No medical records found for this patient.")
        else:
            # Format dates
            medical_history_df['date'] = pd.to_datetime(medical_history_df['date']).dt.strftime('%Y-%m-%d %H:%M')
            
            # Rename columns for display
            display_df = medical_history_df.rename(columns={
                'record_id': 'ID',
                'diagnosis': 'Diagnosis',
                'treatment': 'Treatment',
                'doctor': 'Doctor',
                'date': 'Date',
                'notes': 'Notes'
            })
            
            st.dataframe(display_df, use_container_width=True)
        
        # Add new medical record form
        if st.session_state.role in ['admin', 'doctor']:
            st.subheader("Add New Medical Record")
            
            with st.form("add_medical_record_form"):
                diagnosis = st.text_input("Diagnosis*")
                treatment = st.text_area("Treatment")
                notes = st.text_area("Notes")
                
                add_record_submitted = st.form_submit_button("Add Record")
                
                if add_record_submitted:
                    if not diagnosis:
                        st.error("Please enter a diagnosis.")
                    else:
                        # Animation
                        with st.spinner("Adding medical record..."):
                            time.sleep(1)  # Simple animation delay
                        
                        # Insert medical record
                        record_id = database.insert_record(
                            "MedicalHistory",
                            {
                                "patient_id": patient_to_view,
                                "diagnosis": diagnosis,
                                "treatment": treatment,
                                "doctor_id": st.session_state.user_id,
                                "date": datetime.now(),
                                "notes": notes
                            }
                        )
                        
                        # Record in audit log
                        audit.record_activity(
                            st.session_state.user_id,
                            "Medical Record Added",
                            f"Added medical record for patient ID {patient_to_view}"
                        )
                        
                        st.success("Medical record added successfully!")
                        time.sleep(1)
                        st.rerun()

def my_patients(doctor_id):
    """View patients assigned to a specific doctor."""
    st.header("My Patients")
    
    # Get all patients who have appointments with this doctor
    patients_df = database.query_to_dataframe(
        """
        SELECT DISTINCT p.patient_id, p.first_name, p.last_name, p.gender, p.date_of_birth, p.contact_number, p.status
        FROM Patients p
        JOIN Appointments a ON p.patient_id = a.patient_id
        WHERE a.doctor_id = ? AND p.status = 'active'
        ORDER BY p.last_name, p.first_name
        """,
        (doctor_id,)
    )
    
    if patients_df.empty:
        st.info("You have no patients assigned to you.")
    else:
        # Format dates
        patients_df['date_of_birth'] = pd.to_datetime(patients_df['date_of_birth']).dt.strftime('%Y-%m-%d')
        
        # Add a full name column
        patients_df['full_name'] = patients_df['first_name'] + ' ' + patients_df['last_name']
        
        # Reorder columns
        display_df = patients_df[['patient_id', 'full_name', 'gender', 'date_of_birth', 'contact_number', 'status']]
        
        # Rename columns for display
        display_df.columns = ['ID', 'Name', 'Gender', 'Date of Birth', 'Contact', 'Status']
        
        st.dataframe(display_df, use_container_width=True)
    
    # Patient details and actions
    if not patients_df.empty:
        st.subheader("Patient Actions")
        
        patient_options = [f"{row['first_name']} {row['last_name']} (ID: {row['patient_id']})" for _, row in patients_df.iterrows()]
        selected_patient = st.selectbox("Select Patient", ["Select a patient"] + patient_options)
        
        if selected_patient != "Select a patient":
            patient_id = int(selected_patient.split("ID: ")[1].rstrip(')'))
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                if st.button("View Patient Details"):
                    st.session_state.view_patient = patient_id
                    st.rerun()
            
            with col2:
                if st.button("View Medical History"):
                    st.session_state.view_history = patient_id
                    st.rerun()
            
            with col3:
                if st.button("Add Medical Record"):
                    st.session_state.add_medical_record = patient_id
                    st.rerun()
            
            # Handle viewing medical history
            if hasattr(st.session_state, 'view_history') and st.session_state.view_history == patient_id:
                medical_records(patient_id)
            
            # Handle adding medical record
            if hasattr(st.session_state, 'add_medical_record') and st.session_state.add_medical_record == patient_id:
                st.subheader(f"Add Medical Record for Patient ID: {patient_id}")
                
                with st.form("doctor_add_record_form"):
                    diagnosis = st.text_input("Diagnosis*")
                    treatment = st.text_area("Treatment")
                    notes = st.text_area("Notes")
                    
                    add_record_submitted = st.form_submit_button("Add Record")
                    
                    if add_record_submitted:
                        if not diagnosis:
                            st.error("Please enter a diagnosis.")
                        else:
                            # Animation
                            with st.spinner("Adding medical record..."):
                                time.sleep(1)  # Simple animation delay
                            
                            # Insert medical record
                            record_id = database.insert_record(
                                "MedicalHistory",
                                {
                                    "patient_id": patient_id,
                                    "diagnosis": diagnosis,
                                    "treatment": treatment,
                                    "doctor_id": doctor_id,
                                    "date": datetime.now(),
                                    "notes": notes
                                }
                            )
                            
                            # Record in audit log
                            audit.record_activity(
                                doctor_id,
                                "Medical Record Added",
                                f"Doctor added medical record for patient ID {patient_id}"
                            )
                            
                            st.success("Medical record added successfully!")
                            
                            # Clear the session state and rerun
                            del st.session_state.add_medical_record
                            time.sleep(1)
                            st.rerun()

def patient_registration():
    """Receptionist view for patient registration."""
    st.header("Patient Registration")
    
    with st.form("receptionist_add_patient_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            first_name = st.text_input("First Name*")
            last_name = st.text_input("Last Name*")
            dob = st.date_input("Date of Birth*")
            gender = st.selectbox("Gender*", ["Male", "Female", "Other"])
            blood_group = st.text_input("Blood Group")
        
        with col2:
            address = st.text_area("Address")
            contact_number = st.text_input("Contact Number*")
            email = st.text_input("Email")
            emergency_contact = st.text_input("Emergency Contact")
            emergency_number = st.text_input("Emergency Contact Number")
        
        notes = st.text_area("Notes")
        
        add_patient_submitted = st.form_submit_button("Register Patient")
        
        if add_patient_submitted:
            if not first_name or not last_name or not contact_number:
                st.error("Please fill in all required fields.")
            else:
                # Animation
                with st.spinner("Registering new patient..."):
                    time.sleep(1)  # Simple animation delay
                
                # Insert patient record
                patient_id = database.insert_record(
                    "Patients",
                    {
                        "first_name": first_name,
                        "last_name": last_name,
                        "date_of_birth": dob,
                        "gender": gender,
                        "blood_group": blood_group,
                        "address": address,
                        "contact_number": contact_number,
                        "email": email,
                        "emergency_contact": emergency_contact,
                        "emergency_contact_number": emergency_number,
                        "registration_date": datetime.now(),
                        "notes": notes,
                        "status": "active"
                    }
                )
                
                # Record in audit log
                audit.record_activity(
                    st.session_state.user_id,
                    "Patient Registered",
                    f"Receptionist registered new patient: {first_name} {last_name} (ID: {patient_id})"
                )
                
                st.success(f"Patient registered successfully! Patient ID: {patient_id}")
                
                # Option to schedule appointment
                if st.button("Schedule Appointment for This Patient"):
                    st.session_state.schedule_appointment = patient_id
                    st.rerun()
