import streamlit as st
import database
import pandas as pd
from datetime import datetime, timedelta
import time
import audit
import utils

def get_revenue_for_today():
    """Get the total revenue for today."""
    today = datetime.now().strftime('%Y-%m-%d')
    result = database.fetch_one(
        """
        SELECT COALESCE(SUM(amount), 0) FROM Billing 
        WHERE bill_date LIKE ? || '%' AND status = 'paid'
        """,
        (today,)
    )
    return result[0] if result else 0

def billing_management():
    """Billing management page."""
    st.header("Billing Management")
    
    tab1, tab2, tab3 = st.tabs(["Billing List", "Create Bill", "Payment Processing"])
    
    with tab1:
        st.subheader("Billing List")
        
        # Filters
        col1, col2, col3 = st.columns(3)
        
        with col1:
            date_range = st.selectbox(
                "Date Range",
                ["Today", "Last 7 Days", "Last 30 Days", "All Time"]
            )
        
        with col2:
            status_filter = st.selectbox(
                "Status",
                ["All", "Paid", "Unpaid", "Partial", "Overdue"]
            )
        
        with col3:
            sort_by = st.selectbox(
                "Sort By",
                ["Newest First", "Oldest First", "Amount (High to Low)", "Amount (Low to High)"]
            )
        
        # Build query
        query = """
        SELECT 
            b.bill_id, 
            p.first_name || ' ' || p.last_name as patient_name,
            b.service_description,
            b.amount,
            b.bill_date,
            b.due_date,
            b.status,
            b.insurance_provider
        FROM Billing b
        JOIN Patients p ON b.patient_id = p.patient_id
        """
        
        params = []
        where_clauses = []
        
        # Date range filter
        if date_range == "Today":
            today = datetime.now().strftime('%Y-%m-%d')
            where_clauses.append("b.bill_date LIKE ? || '%'")
            params.append(today)
        elif date_range == "Last 7 Days":
            seven_days_ago = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
            where_clauses.append("b.bill_date >= ?")
            params.append(seven_days_ago)
        elif date_range == "Last 30 Days":
            thirty_days_ago = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
            where_clauses.append("b.bill_date >= ?")
            params.append(thirty_days_ago)
        
        # Status filter
        if status_filter != "All":
            where_clauses.append("b.status = ?")
            params.append(status_filter.lower())
        
        # Finalize query
        if where_clauses:
            query += " WHERE " + " AND ".join(where_clauses)
        
        # Sort order
        if sort_by == "Newest First":
            query += " ORDER BY b.bill_date DESC"
        elif sort_by == "Oldest First":
            query += " ORDER BY b.bill_date ASC"
        elif sort_by == "Amount (High to Low)":
            query += " ORDER BY b.amount DESC"
        elif sort_by == "Amount (Low to High)":
            query += " ORDER BY b.amount ASC"
        
        # Execute query
        bills_df = database.query_to_dataframe(query, params)
        
        if bills_df.empty:
            st.info("No bills found matching your criteria.")
        else:
            # Format dates and amounts
            bills_df['bill_date'] = pd.to_datetime(bills_df['bill_date']).dt.strftime('%Y-%m-%d')
            bills_df['due_date'] = pd.to_datetime(bills_df['due_date']).dt.strftime('%Y-%m-%d')
            bills_df['amount'] = bills_df['amount'].apply(utils.format_currency)
            
            # Rename columns for display
            display_df = bills_df.rename(columns={
                'bill_id': 'ID',
                'patient_name': 'Patient',
                'service_description': 'Service',
                'amount': 'Amount',
                'bill_date': 'Bill Date',
                'due_date': 'Due Date',
                'status': 'Status',
                'insurance_provider': 'Insurance'
            })
            
            st.dataframe(display_df, use_container_width=True)
        
        # Bill details and actions
        if not bills_df.empty:
            st.subheader("Bill Details")
            
            bill_options = [f"Bill #{row['bill_id']} - {row['patient_name']} - {utils.format_currency(row['amount'])}" 
                           for _, row in bills_df.iterrows()]
            
            selected_bill = st.selectbox("Select Bill", ["Select a bill"] + bill_options)
            
            if selected_bill != "Select a bill":
                bill_id = int(selected_bill.split("#")[1].split(" -")[0])
                
                # Get bill details
                bill = database.fetch_one(
                    """
                    SELECT 
                        b.bill_id, 
                        b.patient_id,
                        p.first_name || ' ' || p.last_name as patient_name,
                        b.service_description,
                        b.amount,
                        b.bill_date,
                        b.due_date,
                        b.status,
                        b.insurance_provider,
                        b.insurance_policy_number
                    FROM Billing b
                    JOIN Patients p ON b.patient_id = p.patient_id
                    WHERE b.bill_id = ?
                    """,
                    (bill_id,)
                )
                
                if bill:
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.write(f"**Bill ID:** {bill[0]}")
                        st.write(f"**Patient:** {bill[2]}")
                        st.write(f"**Service:** {bill[3]}")
                        st.write(f"**Amount:** {utils.format_currency(bill[4])}")
                    
                    with col2:
                        st.write(f"**Bill Date:** {bill[5]}")
                        st.write(f"**Due Date:** {bill[6]}")
                        st.write(f"**Status:** {bill[7]}")
                        st.write(f"**Insurance:** {bill[8] or 'None'}")
                        if bill[8]:
                            st.write(f"**Policy Number:** {bill[9]}")
                    
                    # Action buttons
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        if bill[7] != "paid":
                            if st.button("Mark as Paid"):
                                # Animation
                                with st.spinner("Processing payment..."):
                                    time.sleep(1)  # Simple animation delay
                                
                                # Update bill status
                                database.update_record(
                                    "Billing",
                                    {"status": "paid"},
                                    {"bill_id": bill_id}
                                )
                                
                                # Record in audit log
                                audit.record_activity(
                                    st.session_state.user_id,
                                    "Bill Payment",
                                    f"Marked Bill #{bill_id} as paid"
                                )
                                
                                st.success("Bill marked as paid successfully!")
                                time.sleep(1)
                                st.rerun()
                    
                    with col2:
                        if st.button("Edit Bill"):
                            st.session_state.edit_bill = bill_id
                            st.rerun()
                    
                    with col3:
                        if st.button("Print / Download"):
                            st.info("Printing/downloading functionality will be implemented in future updates.")
                    
                    # Handle bill editing
                    if hasattr(st.session_state, 'edit_bill') and st.session_state.edit_bill == bill_id:
                        st.subheader("Edit Bill")
                        
                        with st.form("edit_bill_form"):
                            col1, col2 = st.columns(2)
                            
                            with col1:
                                service_description = st.text_input("Service Description", bill[3])
                                amount = st.number_input("Amount (KSh)", min_value=0.0, value=float(bill[4]), step=10.0)
                                due_date = st.date_input("Due Date", datetime.strptime(bill[6], '%Y-%m-%d'))
                            
                            with col2:
                                status = st.selectbox(
                                    "Status", 
                                    ["unpaid", "paid", "partial", "overdue"],
                                    index=["unpaid", "paid", "partial", "overdue"].index(bill[7])
                                )
                                insurance_provider = st.text_input("Insurance Provider", bill[8] or "")
                                insurance_policy = st.text_input("Policy Number", bill[9] or "")
                            
                            update_bill_submitted = st.form_submit_button("Update Bill")
                            
                            if update_bill_submitted:
                                # Animation
                                with st.spinner("Updating bill..."):
                                    time.sleep(1)  # Simple animation delay
                                
                                # Update bill
                                database.update_record(
                                    "Billing",
                                    {
                                        "service_description": service_description,
                                        "amount": amount,
                                        "due_date": due_date.strftime('%Y-%m-%d'),
                                        "status": status,
                                        "insurance_provider": insurance_provider,
                                        "insurance_policy_number": insurance_policy
                                    },
                                    {"bill_id": bill_id}
                                )
                                
                                # Record in audit log
                                audit.record_activity(
                                    st.session_state.user_id,
                                    "Bill Updated",
                                    f"Updated Bill #{bill_id}"
                                )
                                
                                st.success("Bill updated successfully!")
                                
                                # Clear the session state and rerun
                                del st.session_state.edit_bill
                                time.sleep(1)
                                st.rerun()
    
    with tab2:
        st.subheader("Create New Bill")
        
        with st.form("create_bill_form"):
            # Get patient list
            patients_df = database.query_to_dataframe(
                "SELECT patient_id, first_name || ' ' || last_name as patient_name FROM Patients WHERE status = 'active'"
            )
            patient_options = {row['patient_id']: row['patient_name'] for _, row in patients_df.iterrows()}
            
            # Add a placeholder
            patient_options[0] = "Select a patient"
            
            col1, col2 = st.columns(2)
            
            with col1:
                selected_patient = st.selectbox(
                    "Patient*",
                    options=list(patient_options.keys()),
                    format_func=lambda x: patient_options[x],
                    index=0
                )
                
                service_description = st.text_input("Service Description*")
                amount = st.number_input("Amount (KSh)*", min_value=0.0, step=10.0)
            
            with col2:
                bill_date = st.date_input("Bill Date", datetime.now().date())
                due_date = st.date_input("Due Date", datetime.now().date() + timedelta(days=30))
                status = st.selectbox("Status", ["unpaid", "paid", "partial"])
            
            col1, col2 = st.columns(2)
            
            with col1:
                insurance_provider = st.text_input("Insurance Provider")
            
            with col2:
                insurance_policy = st.text_input("Policy Number")
            
            create_bill_submitted = st.form_submit_button("Create Bill")
            
            if create_bill_submitted:
                if selected_patient == 0 or not service_description or amount <= 0:
                    st.error("Please fill in all required fields.")
                else:
                    # Animation
                    with st.spinner("Creating bill..."):
                        time.sleep(1)  # Simple animation delay
                    
                    # Create bill
                    bill_id = database.insert_record(
                        "Billing",
                        {
                            "patient_id": selected_patient,
                            "service_description": service_description,
                            "amount": amount,
                            "bill_date": bill_date.strftime('%Y-%m-%d'),
                            "due_date": due_date.strftime('%Y-%m-%d'),
                            "status": status,
                            "insurance_provider": insurance_provider,
                            "insurance_policy_number": insurance_policy
                        }
                    )
                    
                    # Record in audit log
                    audit.record_activity(
                        st.session_state.user_id,
                        "Bill Created",
                        f"Created new bill (ID: {bill_id}) for patient ID {selected_patient}"
                    )
                    
                    st.success(f"Bill created successfully! Bill ID: {bill_id}")
                    time.sleep(1)
                    st.rerun()
    
    with tab3:
        st.subheader("Payment Processing")
        
        # Get unpaid bills
        unpaid_bills_df = database.query_to_dataframe(
            """
            SELECT 
                b.bill_id, 
                p.first_name || ' ' || p.last_name as patient_name,
                b.service_description,
                b.amount,
                b.bill_date,
                b.due_date,
                b.status
            FROM Billing b
            JOIN Patients p ON b.patient_id = p.patient_id
            WHERE b.status IN ('unpaid', 'partial', 'overdue')
            ORDER BY b.due_date ASC
            """
        )
        
        if unpaid_bills_df.empty:
            st.info("No unpaid bills to process.")
        else:
            # Format dates and amounts
            unpaid_bills_df['bill_date'] = pd.to_datetime(unpaid_bills_df['bill_date']).dt.strftime('%Y-%m-%d')
            unpaid_bills_df['due_date'] = pd.to_datetime(unpaid_bills_df['due_date']).dt.strftime('%Y-%m-%d')
            
            # Calculate days overdue
            today = datetime.now().date()
            unpaid_bills_df['days_overdue'] = unpaid_bills_df['due_date'].apply(
                lambda x: max(0, (today - datetime.strptime(x, '%Y-%m-%d').date()).days)
            )
            
            # Add formatting for display
            unpaid_bills_df['display_amount'] = unpaid_bills_df['amount'].apply(utils.format_currency)
            
            # Highlight overdue bills
            unpaid_bills_df['status_display'] = unpaid_bills_df.apply(
                lambda row: f"⚠️ OVERDUE ({row['days_overdue']} days)" if row['days_overdue'] > 0 else row['status'],
                axis=1
            )
            
            # Select columns for display
            display_df = unpaid_bills_df[['bill_id', 'patient_name', 'service_description', 'display_amount', 'due_date', 'status_display']]
            display_df.columns = ['ID', 'Patient', 'Service', 'Amount', 'Due Date', 'Status']
            
            st.dataframe(display_df, use_container_width=True)
            
            # Payment processing
            st.subheader("Process Payment")
            
            bill_options = [f"Bill #{row['bill_id']} - {row['patient_name']} - {utils.format_currency(row['amount'])}" 
                           for _, row in unpaid_bills_df.iterrows()]
            
            selected_payment_bill = st.selectbox("Select Bill", ["Select a bill"] + bill_options, key="payment_bill")
            
            if selected_payment_bill != "Select a bill":
                payment_bill_id = int(selected_payment_bill.split("#")[1].split(" -")[0])
                
                # Get the bill details
                bill_details = unpaid_bills_df[unpaid_bills_df['bill_id'] == payment_bill_id].iloc[0]
                
                with st.form("process_payment_form"):
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        payment_amount = st.number_input(
                            "Payment Amount (KSh)",
                            min_value=0.0,
                            max_value=float(bill_details['amount']),
                            value=float(bill_details['amount']),
                            step=10.0
                        )
                        
                        payment_method = st.selectbox(
                            "Payment Method",
                            ["Cash", "Credit Card", "Debit Card", "Insurance", "Bank Transfer", "Check"]
                        )
                    
                    with col2:
                        payment_date = st.date_input("Payment Date", datetime.now().date())
                        payment_reference = st.text_input("Reference/Receipt Number")
                    
                    payment_notes = st.text_area("Payment Notes")
                    
                    process_payment_submitted = st.form_submit_button("Process Payment")
                    
                    if process_payment_submitted:
                        if payment_amount <= 0:
                            st.error("Payment amount must be greater than zero.")
                        else:
                            # Animation
                            with st.spinner("Processing payment..."):
                                time.sleep(1.5)  # Simple animation delay
                            
                            # Determine new status
                            new_status = "paid"
                            if payment_amount < bill_details['amount']:
                                new_status = "partial"
                            
                            # Update bill status
                            database.update_record(
                                "Billing",
                                {"status": new_status},
                                {"bill_id": payment_bill_id}
                            )
                            
                            # Construct payment details for audit
                            payment_details = (
                                f"Amount: {utils.format_currency(payment_amount)}, Method: {payment_method}, "
                                f"Reference: {payment_reference}, Notes: {payment_notes}"
                            )
                            
                            # Record in audit log
                            audit.record_activity(
                                st.session_state.user_id,
                                "Payment Processed",
                                f"Processed payment for Bill #{payment_bill_id}. {payment_details}"
                            )
                            
                            st.success("Payment processed successfully!")
                            time.sleep(1)
                            st.rerun()
