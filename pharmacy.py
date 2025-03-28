import streamlit as st
import database
import pandas as pd
from datetime import datetime, timedelta
import time
import audit

def get_pending_prescriptions_count():
    """Get the count of pending prescriptions."""
    result = database.fetch_one(
        "SELECT COUNT(*) FROM Prescriptions WHERE status = 'pending'"
    )
    return result[0] if result else 0

def pharmacy_management():
    """Pharmacy management page."""
    st.header("Pharmacy Management")
    
    tab1, tab2, tab3 = st.tabs(["Medications", "Prescriptions", "Drug Interactions"])
    
    with tab1:
        st.subheader("Medication Inventory")
        
        # Filters
        col1, col2, col3 = st.columns(3)
        
        with col1:
            search_term = st.text_input("Search by name or category", key="med_search")
        
        with col2:
            category_filter = st.selectbox(
                "Category", 
                ["All"] + sorted(set([row[0] for row in database.fetch_all(
                    "SELECT DISTINCT category FROM Pharmacy ORDER BY category"
                ) or []])),
                key="med_category"
            )
        
        with col3:
            status_filter = st.selectbox(
                "Status", 
                ["All", "Available", "Low Stock", "Out of Stock", "Expired"],
                key="med_status"
            )
        
        # Build query
        query = """
        SELECT 
            medication_id, 
            name, 
            generic_name,
            category, 
            dosage,
            stock_quantity, 
            unit_price, 
            reorder_level, 
            expiry_date, 
            status
        FROM Pharmacy
        """
        
        params = []
        where_clauses = []
        
        if search_term:
            where_clauses.append("(name LIKE ? OR generic_name LIKE ? OR category LIKE ?)")
            params.extend([f"%{search_term}%", f"%{search_term}%", f"%{search_term}%"])
        
        if category_filter != "All":
            where_clauses.append("category = ?")
            params.append(category_filter)
        
        if status_filter != "All":
            if status_filter == "Low Stock":
                where_clauses.append("stock_quantity <= reorder_level AND stock_quantity > 0 AND status = 'available'")
            elif status_filter == "Out of Stock":
                where_clauses.append("stock_quantity = 0 AND status = 'available'")
            else:
                where_clauses.append("status = ?")
                params.append(status_filter.lower())
        
        # Finalize query
        if where_clauses:
            query += " WHERE " + " AND ".join(where_clauses)
        
        query += " ORDER BY category, name"
        
        # Execute query
        medications_df = database.query_to_dataframe(query, params)
        
        if medications_df.empty:
            st.info("No medications found matching your criteria.")
        else:
            # Add a total value column
            medications_df['total_value'] = medications_df['stock_quantity'] * medications_df['unit_price']
            
            # Format dates and currency
            medications_df['expiry_date'] = pd.to_datetime(medications_df['expiry_date']).dt.strftime('%Y-%m-%d')
            medications_df['unit_price'] = medications_df['unit_price'].apply(lambda x: f"${x:.2f}")
            medications_df['total_value'] = medications_df['total_value'].apply(lambda x: f"${x:.2f}")
            
            # Add stock status indicator
            def get_stock_status(row):
                if row['stock_quantity'] == 0:
                    return "⚠️ Out of Stock"
                elif row['stock_quantity'] <= row['reorder_level']:
                    return "⚠️ Low Stock"
                return "✅ In Stock"
            
            medications_df['stock_status'] = medications_df.apply(get_stock_status, axis=1)
            
            # Reorder and rename columns for display
            display_df = medications_df[[
                'medication_id', 'name', 'generic_name', 'category', 'dosage', 'stock_quantity', 
                'unit_price', 'total_value', 'stock_status'
            ]]
            
            display_df.columns = [
                'ID', 'Name', 'Generic Name', 'Category', 'Dosage', 'Quantity', 
                'Unit Price', 'Total Value', 'Status'
            ]
            
            st.dataframe(display_df, use_container_width=True)
            
            # Summary statistics
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                total_meds = len(medications_df)
                st.metric("Total Medications", total_meds)
            
            with col2:
                total_quantity = medications_df['stock_quantity'].sum()
                st.metric("Total Quantity", total_quantity)
            
            with col3:
                low_stock_meds = len(medications_df[medications_df['stock_quantity'] <= medications_df['reorder_level']])
                st.metric("Low Stock Items", low_stock_meds)
            
            with col4:
                total_value = medications_df['stock_quantity'] * pd.to_numeric(medications_df['unit_price'].str.replace('$', ''))
                st.metric("Total Pharmacy Value", f"${total_value.sum():.2f}")
        
        # Medication actions section
        st.subheader("Medication Actions")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.write("#### Add New Medication")
            
            with st.form("add_medication_form"):
                new_med_name = st.text_input("Medication Name*")
                new_med_generic = st.text_input("Generic Name")
                new_med_category = st.text_input("Category*")
                new_med_dosage = st.text_input("Dosage*")
                new_med_quantity = st.number_input("Initial Quantity*", min_value=0, step=1)
                new_med_price = st.number_input("Unit Price ($)*", min_value=0.01, step=0.01)
                new_med_reorder = st.number_input("Reorder Level*", min_value=1, step=1, value=10)
                new_med_supplier = st.text_input("Supplier")
                new_med_expiry = st.date_input("Expiry Date", min_value=datetime.now().date())
                
                add_med_submitted = st.form_submit_button("Add Medication")
                
                if add_med_submitted:
                    if not new_med_name or not new_med_category or not new_med_dosage:
                        st.error("Please fill in all required fields.")
                    else:
                        # Animation
                        with st.spinner("Adding new medication..."):
                            time.sleep(1)  # Simple animation delay
                        
                        # Determine initial status based on quantity and reorder level
                        initial_status = "available"
                        if new_med_quantity == 0:
                            initial_status = "out of stock"
                        elif new_med_quantity <= new_med_reorder:
                            initial_status = "low stock"
                        
                        # Add medication
                        med_id = database.insert_record(
                            "Pharmacy",
                            {
                                "name": new_med_name,
                                "generic_name": new_med_generic,
                                "category": new_med_category,
                                "dosage": new_med_dosage,
                                "stock_quantity": new_med_quantity,
                                "unit_price": new_med_price,
                                "supplier": new_med_supplier,
                                "reorder_level": new_med_reorder,
                                "expiry_date": new_med_expiry.strftime('%Y-%m-%d'),
                                "status": initial_status
                            }
                        )
                        
                        # Record in audit log
                        audit.record_activity(
                            st.session_state.user_id,
                            "Medication Added",
                            f"Added new medication: {new_med_name} (ID: {med_id})"
                        )
                        
                        st.success(f"Medication added successfully! ID: {med_id}")
                        time.sleep(1)
                        st.rerun()
        
        with col2:
            st.write("#### Update Medication")
            
            # Only show if we have medications
            if not medications_df.empty:
                med_options = [f"{row['name']} - {row['dosage']} (ID: {row['medication_id']})" for _, row in medications_df.iterrows()]
                
                selected_med = st.selectbox(
                    "Select Medication",
                    ["Select a medication"] + med_options
                )
                
                if selected_med != "Select a medication":
                    med_id = int(selected_med.split("ID: ")[1].rstrip(')'))
                    
                    # Get medication details
                    med_details = database.fetch_one(
                        "SELECT * FROM Pharmacy WHERE medication_id = ?",
                        (med_id,)
                    )
                    
                    if med_details:
                        with st.form("update_medication_form"):
                            update_type = st.selectbox(
                                "Action",
                                ["Update Stock", "Edit Details", "Mark as Discontinued"]
                            )
                            
                            if update_type == "Update Stock":
                                transaction_type = st.selectbox(
                                    "Transaction Type",
                                    ["Add Stock", "Remove Stock", "Set Stock Level"]
                                )
                                
                                quantity = st.number_input(
                                    "Quantity",
                                    min_value=1,
                                    step=1,
                                    value=1
                                )
                                
                                reason = st.text_input("Reason")
                            
                            elif update_type == "Edit Details":
                                med_name = st.text_input("Medication Name", med_details[1])
                                med_generic = st.text_input("Generic Name", med_details[2] or "")
                                med_category = st.text_input("Category", med_details[3])
                                med_dosage = st.text_input("Dosage", med_details[4])
                                med_price = st.number_input("Unit Price ($)", min_value=0.01, value=float(med_details[6]), step=0.01)
                                med_reorder = st.number_input("Reorder Level", min_value=1, value=int(med_details[7]), step=1)
                                med_supplier = st.text_input("Supplier", med_details[8] or "")
                                med_expiry = st.date_input(
                                    "Expiry Date", 
                                    datetime.strptime(med_details[9], '%Y-%m-%d') if med_details[9] else datetime.now().date()
                                )
                            
                            update_med_submitted = st.form_submit_button("Update Medication")
                            
                            if update_med_submitted:
                                # Animation
                                with st.spinner("Updating medication..."):
                                    time.sleep(1)  # Simple animation delay
                                
                                if update_type == "Update Stock":
                                    # Calculate new quantity
                                    new_quantity = med_details[5]  # current stock
                                    if transaction_type == "Add Stock":
                                        new_quantity += quantity
                                    elif transaction_type == "Remove Stock":
                                        new_quantity = max(0, new_quantity - quantity)
                                    else:  # Set Stock Level
                                        new_quantity = quantity
                                    
                                    # Determine new status
                                    new_status = med_details[10]  # current status
                                    if new_quantity == 0:
                                        new_status = "out of stock"
                                    elif new_quantity <= med_details[7]:  # reorder level
                                        new_status = "low stock"
                                    else:
                                        new_status = "available"
                                    
                                    # Update medication
                                    database.update_record(
                                        "Pharmacy",
                                        {
                                            "stock_quantity": new_quantity,
                                            "status": new_status
                                        },
                                        {"medication_id": med_id}
                                    )
                                    
                                    # Record in audit log
                                    audit.record_activity(
                                        st.session_state.user_id,
                                        "Medication Stock Update",
                                        f"{transaction_type}: {med_details[1]} (ID: {med_id}), Quantity: {quantity}, Reason: {reason}"
                                    )
                                    
                                elif update_type == "Edit Details":
                                    # Update medication details
                                    database.update_record(
                                        "Pharmacy",
                                        {
                                            "name": med_name,
                                            "generic_name": med_generic,
                                            "category": med_category,
                                            "dosage": med_dosage,
                                            "unit_price": med_price,
                                            "supplier": med_supplier,
                                            "reorder_level": med_reorder,
                                            "expiry_date": med_expiry.strftime('%Y-%m-%d')
                                        },
                                        {"medication_id": med_id}
                                    )
                                    
                                    # Record in audit log
                                    audit.record_activity(
                                        st.session_state.user_id,
                                        "Medication Details Updated",
                                        f"Updated details for medication ID: {med_id}"
                                    )
                                
                                elif update_type == "Mark as Discontinued":
                                    # Update medication status
                                    database.update_record(
                                        "Pharmacy",
                                        {"status": "discontinued"},
                                        {"medication_id": med_id}
                                    )
                                    
                                    # Record in audit log
                                    audit.record_activity(
                                        st.session_state.user_id,
                                        "Medication Discontinued",
                                        f"Marked medication ID {med_id} as discontinued"
                                    )
                                
                                st.success("Medication updated successfully!")
                                time.sleep(1)
                                st.rerun()
            else:
                st.info("No medications available to update.")
    
    with tab2:
        st.subheader("Prescription Management")
        
        # Filters
        col1, col2 = st.columns(2)
        
        with col1:
            status_filter = st.selectbox(
                "Status",
                ["All", "Pending", "Filled", "Cancelled"]
            )
        
        with col2:
            time_filter = st.selectbox(
                "Time Period",
                ["Today", "Last 7 Days", "Last 30 Days", "All Time"]
            )
        
        # Build query
        query = """
        SELECT 
            p.prescription_id,
            pat.first_name || ' ' || pat.last_name as patient_name,
            u.full_name as doctor,
            ph.name as medication,
            p.dosage,
            p.frequency,
            p.duration,
            p.status,
            p.created_at
        FROM Prescriptions p
        JOIN Patients pat ON p.patient_id = pat.patient_id
        JOIN Users u ON p.doctor_id = u.user_id
        JOIN Pharmacy ph ON p.medication_id = ph.medication_id
        """
        
        params = []
        where_clauses = []
        
        # Status filter
        if status_filter != "All":
            where_clauses.append("p.status = ?")
            params.append(status_filter.lower())
        
        # Time filter
        if time_filter == "Today":
            where_clauses.append("DATE(p.created_at) = DATE('now')")
        elif time_filter == "Last 7 Days":
            where_clauses.append("p.created_at >= datetime('now', '-7 days')")
        elif time_filter == "Last 30 Days":
            where_clauses.append("p.created_at >= datetime('now', '-30 days')")
        
        # Finalize query
        if where_clauses:
            query += " WHERE " + " AND ".join(where_clauses)
        
        query += " ORDER BY p.created_at DESC"
        
        # Execute query
        prescriptions_df = database.query_to_dataframe(query, params)
        
        if prescriptions_df.empty:
            st.info("No prescriptions found matching your criteria.")
        else:
            # Format dates
            prescriptions_df['created_at'] = pd.to_datetime(prescriptions_df['created_at']).dt.strftime('%Y-%m-%d %H:%M')
            
            # Add status indicators
            def get_status_indicator(status):
                if status == "pending":
                    return "⏳ Pending"
                elif status == "filled":
                    return "✅ Filled"
                elif status == "cancelled":
                    return "❌ Cancelled"
                return status
            
            prescriptions_df['status_display'] = prescriptions_df['status'].apply(get_status_indicator)
            
            # Rename columns for display
            display_df = prescriptions_df[[
                'prescription_id', 'patient_name', 'doctor', 'medication', 
                'dosage', 'status_display', 'created_at'
            ]]
            
            display_df.columns = [
                'ID', 'Patient', 'Doctor', 'Medication', 
                'Dosage', 'Status', 'Created'
            ]
            
            st.dataframe(display_df, use_container_width=True)
        
        # Prescription details and actions
        if not prescriptions_df.empty:
            st.subheader("Prescription Details")
            
            prescription_options = [f"#{row['prescription_id']} - {row['patient_name']} - {row['medication']}" 
                                  for _, row in prescriptions_df.iterrows()]
            
            selected_prescription = st.selectbox(
                "Select Prescription",
                ["Select a prescription"] + prescription_options
            )
            
            if selected_prescription != "Select a prescription":
                prescription_id = int(selected_prescription.split("#")[1].split(" -")[0])
                
                # Get prescription details
                prescription = database.fetch_one(
                    """
                    SELECT 
                        p.prescription_id,
                        p.patient_id,
                        pat.first_name || ' ' || pat.last_name as patient_name,
                        p.doctor_id,
                        u.full_name as doctor,
                        p.medication_id,
                        ph.name as medication,
                        ph.dosage as med_dosage,
                        p.dosage,
                        p.frequency,
                        p.duration,
                        p.notes,
                        p.status,
                        p.created_at
                    FROM Prescriptions p
                    JOIN Patients pat ON p.patient_id = pat.patient_id
                    JOIN Users u ON p.doctor_id = u.user_id
                    JOIN Pharmacy ph ON p.medication_id = ph.medication_id
                    WHERE p.prescription_id = ?
                    """,
                    (prescription_id,)
                )
                
                if prescription:
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.write(f"**Prescription ID:** {prescription[0]}")
                        st.write(f"**Patient:** {prescription[2]}")
                        st.write(f"**Doctor:** {prescription[4]}")
                        st.write(f"**Medication:** {prescription[6]} ({prescription[7]})")
                    
                    with col2:
                        st.write(f"**Dosage:** {prescription[8]}")
                        st.write(f"**Frequency:** {prescription[9]}")
                        st.write(f"**Duration:** {prescription[10]}")
                        st.write(f"**Status:** {prescription[12]}")
                        st.write(f"**Created:** {prescription[13]}")
                    
                    st.write(f"**Notes:** {prescription[11] or 'None'}")
                    
                    # Action buttons
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        if prescription[12] == "pending":
                            if st.button("Fill Prescription"):
                                # Get medication stock
                                med_stock = database.fetch_one(
                                    "SELECT stock_quantity FROM Pharmacy WHERE medication_id = ?",
                                    (prescription[5],)
                                )[0]
                                
                                # Simple logic to determine if enough stock exists
                                # For a real system, would need more complex logic based on dosage, duration, etc.
                                if med_stock > 0:
                                    # Animation
                                    with st.spinner("Filling prescription..."):
                                        time.sleep(1.5)  # Simple animation delay
                                    
                                    # Update prescription status
                                    database.update_record(
                                        "Prescriptions",
                                        {"status": "filled"},
                                        {"prescription_id": prescription_id}
                                    )
                                    
                                    # Update medication stock (deduct 1 unit)
                                    new_stock = med_stock - 1
                                    
                                    # Determine new status
                                    med_reorder_level = database.fetch_one(
                                        "SELECT reorder_level FROM Pharmacy WHERE medication_id = ?",
                                        (prescription[5],)
                                    )[0]
                                    
                                    new_status = "available"
                                    if new_stock == 0:
                                        new_status = "out of stock"
                                    elif new_stock <= med_reorder_level:
                                        new_status = "low stock"
                                    
                                    # Update medication
                                    database.update_record(
                                        "Pharmacy",
                                        {
                                            "stock_quantity": new_stock,
                                            "status": new_status
                                        },
                                        {"medication_id": prescription[5]}
                                    )
                                    
                                    # Record in audit log
                                    audit.record_activity(
                                        st.session_state.user_id,
                                        "Prescription Filled",
                                        f"Filled prescription ID {prescription_id} for patient {prescription[2]}"
                                    )
                                    
                                    st.success("Prescription filled successfully!")
                                    time.sleep(1)
                                    st.rerun()
                                else:
                                    st.error("Cannot fill prescription. Medication is out of stock.")
                    
                    with col2:
                        if prescription[12] == "pending":
                            if st.button("Cancel Prescription"):
                                # Animation
                                with st.spinner("Cancelling prescription..."):
                                    time.sleep(1)  # Simple animation delay
                                
                                # Update prescription status
                                database.update_record(
                                    "Prescriptions",
                                    {"status": "cancelled"},
                                    {"prescription_id": prescription_id}
                                )
                                
                                # Record in audit log
                                audit.record_activity(
                                    st.session_state.user_id,
                                    "Prescription Cancelled",
                                    f"Cancelled prescription ID {prescription_id}"
                                )
                                
                                st.success("Prescription cancelled successfully!")
                                time.sleep(1)
                                st.rerun()
        
        # Add new prescription section (for doctors or admins)
        if st.session_state.role in ['admin', 'doctor', 'pharmacist']:
            st.subheader("Create New Prescription")
            
            with st.form("new_prescription_form"):
                col1, col2 = st.columns(2)
                
                with col1:
                    # Get patient list
                    patients_df = database.query_to_dataframe(
                        "SELECT patient_id, first_name || ' ' || last_name as patient_name FROM Patients WHERE status = 'active'"
                    )
                    patient_options = {row['patient_id']: row['patient_name'] for _, row in patients_df.iterrows()}
                    
                    # Add a placeholder
                    patient_options[0] = "Select a patient"
                    
                    # Get medication list
                    medications_df = database.query_to_dataframe(
                        "SELECT medication_id, name || ' (' || dosage || ')' as med_name FROM Pharmacy WHERE status = 'available'"
                    )
                    med_options = {row['medication_id']: row['med_name'] for _, row in medications_df.iterrows()}
                    
                    # Add a placeholder
                    med_options[0] = "Select a medication"
                    
                    selected_patient = st.selectbox(
                        "Patient*",
                        options=list(patient_options.keys()),
                        format_func=lambda x: patient_options[x],
                        index=0
                    )
                    
                    selected_medication = st.selectbox(
                        "Medication*",
                        options=list(med_options.keys()),
                        format_func=lambda x: med_options[x],
                        index=0
                    )
                
                with col2:
                    # Doctor is the logged-in user if a doctor, or selectable if admin/pharmacist
                    if st.session_state.role == 'doctor':
                        selected_doctor = st.session_state.user_id
                        st.write(f"**Prescribing Doctor:** {st.session_state.username}")
                    else:
                        # Get doctor list
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
                    
                    dosage = st.text_input("Dosage*", placeholder="e.g., 1 tablet")
                
                col1, col2 = st.columns(2)
                
                with col1:
                    frequency = st.text_input("Frequency*", placeholder="e.g., Twice daily")
                
                with col2:
                    duration = st.text_input("Duration*", placeholder="e.g., 7 days")
                
                notes = st.text_area("Notes", placeholder="Additional instructions...")
                
                prescription_submitted = st.form_submit_button("Create Prescription")
                
                if prescription_submitted:
                    if (selected_patient == 0 or selected_medication == 0 or 
                        (st.session_state.role != 'doctor' and selected_doctor == 0) or 
                        not dosage or not frequency or not duration):
                        st.error("Please fill in all required fields.")
                    else:
                        # Animation
                        with st.spinner("Creating prescription..."):
                            time.sleep(1)  # Simple animation delay
                        
                        # Insert prescription
                        prescription_id = database.insert_record(
                            "Prescriptions",
                            {
                                "patient_id": selected_patient,
                                "doctor_id": selected_doctor,
                                "medication_id": selected_medication,
                                "dosage": dosage,
                                "frequency": frequency,
                                "duration": duration,
                                "notes": notes,
                                "status": "pending",
                                "created_at": datetime.now()
                            }
                        )
                        
                        # Record in audit log
                        audit.record_activity(
                            st.session_state.user_id,
                            "Prescription Created",
                            f"Created prescription ID {prescription_id} for patient ID {selected_patient}"
                        )
                        
                        st.success(f"Prescription created successfully! ID: {prescription_id}")
                        time.sleep(1)
                        st.rerun()
    
    with tab3:
        st.subheader("Drug Interactions")
        
        st.info("This feature would check for potential drug interactions when prescribing multiple medications to a patient. In a production system, this would be integrated with a comprehensive drug interaction database.")
        
        # Placeholder implementation for drug interaction checker
        st.write("### Drug Interaction Checker")
        
        col1, col2 = st.columns(2)
        
        with col1:
            medications_df = database.query_to_dataframe(
                "SELECT medication_id, name FROM Pharmacy ORDER BY name"
            )
            
            if not medications_df.empty:
                medication_list = medications_df['name'].tolist()
                
                med1 = st.selectbox("First Medication", ["Select medication"] + medication_list)
                med2 = st.selectbox("Second Medication", ["Select medication"] + medication_list)
                
                check_interaction = st.button("Check Interaction")
                
                if check_interaction:
                    if med1 == "Select medication" or med2 == "Select medication":
                        st.error("Please select both medications.")
                    elif med1 == med2:
                        st.warning("You've selected the same medication twice.")
                    else:
                        # This is a placeholder. In a real system, this would query a drug interaction database
                        st.info(f"No known interactions between {med1} and {med2}.")
            else:
                st.warning("No medications in the database to check.")
        
        with col2:
            st.write("#### Patient Medication Review")
            
            patients_df = database.query_to_dataframe(
                "SELECT patient_id, first_name || ' ' || last_name as patient_name FROM Patients WHERE status = 'active'"
            )
            
            if not patients_df.empty:
                patient_options = {row['patient_id']: row['patient_name'] for _, row in patients_df.iterrows()}
                patient_options[0] = "Select a patient"
                
                selected_review_patient = st.selectbox(
                    "Select Patient",
                    options=list(patient_options.keys()),
                    format_func=lambda x: patient_options[x],
                    index=0,
                    key="review_patient"
                )
                
                if selected_review_patient != 0:
                    # Get patient's active prescriptions
                    active_prescriptions = database.query_to_dataframe(
                        """
                        SELECT 
                            p.prescription_id,
                            ph.name as medication,
                            p.dosage,
                            p.frequency,
                            p.created_at
                        FROM Prescriptions p
                        JOIN Pharmacy ph ON p.medication_id = ph.medication_id
                        WHERE p.patient_id = ? AND p.status = 'filled'
                        ORDER BY p.created_at DESC
                        """,
                        (selected_review_patient,)
                    )
                    
                    if not active_prescriptions.empty:
                        st.write("**Current Medications:**")
                        
                        for _, row in active_prescriptions.iterrows():
                            st.write(f"- {row['medication']} - {row['dosage']} - {row['frequency']}")
                        
                        st.write("**Potential Interactions:**")
                        
                        # Placeholder for interaction checking
                        # In a real system, would check all medication combinations
                        if len(active_prescriptions) > 1:
                            st.info("No significant interactions detected among current medications.")
                        else:
                            st.success("Only one medication prescribed - no interactions to check.")
                    else:
                        st.info("This patient has no active prescriptions.")
            else:
                st.warning("No patients in the database.")
