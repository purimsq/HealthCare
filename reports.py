import streamlit as st
import database
import pandas as pd
from datetime import datetime, timedelta
import plotly.express as px
import plotly.graph_objects as go
import utils

def reports_management():
    """Reports and analytics page."""
    st.header("Reports & Analytics")
    
    tab1, tab2, tab3, tab4 = st.tabs(["Patient Statistics", "Financial Reports", "Inventory Reports", "Custom Reports"])
    
    with tab1:
        st.subheader("Patient Statistics")
        
        # Time period selection
        time_period = st.selectbox(
            "Time Period",
            ["Last 30 Days", "Last 3 Months", "Last 6 Months", "Last Year", "All Time"],
            key="patient_time_period"
        )
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Calculate date range based on selection
            end_date = datetime.now().date()
            if time_period == "Last 30 Days":
                start_date = end_date - timedelta(days=30)
            elif time_period == "Last 3 Months":
                start_date = end_date - timedelta(days=90)
            elif time_period == "Last 6 Months":
                start_date = end_date - timedelta(days=180)
            elif time_period == "Last Year":
                start_date = end_date - timedelta(days=365)
            else:  # All Time
                start_date = datetime(2000, 1, 1).date()
            
            # New patient registrations over time
            st.write("#### New Patient Registrations")
            
            patients_over_time = database.query_to_dataframe(
                """
                SELECT date(registration_date) as date, COUNT(*) as count
                FROM Patients
                WHERE registration_date BETWEEN ? AND ?
                GROUP BY date(registration_date)
                ORDER BY date
                """,
                (start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d'))
            )
            
            if patients_over_time.empty:
                st.info("No patient registrations in the selected time period.")
            else:
                # Fill in missing dates with zero counts
                date_range = pd.date_range(start=start_date, end=end_date)
                full_date_df = pd.DataFrame({'date': date_range})
                full_date_df['date'] = full_date_df['date'].dt.strftime('%Y-%m-%d')
                
                patients_over_time['date'] = patients_over_time['date'].astype(str)
                
                merged_df = pd.merge(full_date_df, patients_over_time, on='date', how='left')
                merged_df['count'] = merged_df['count'].fillna(0)
                
                # For longer time periods, resample to avoid overcrowded x-axis
                if time_period in ["Last 6 Months", "Last Year", "All Time"]:
                    merged_df['date'] = pd.to_datetime(merged_df['date'])
                    if time_period == "Last 6 Months":
                        resampled = merged_df.set_index('date').resample('W').sum().reset_index()
                    else:  # Last Year or All Time
                        resampled = merged_df.set_index('date').resample('M').sum().reset_index()
                    
                    fig = px.line(
                        resampled, 
                        x='date', 
                        y='count',
                        title='New Patient Registrations Over Time',
                        labels={'date': 'Date', 'count': 'Number of Registrations'}
                    )
                else:
                    fig = px.line(
                        merged_df, 
                        x='date', 
                        y='count',
                        title='New Patient Registrations Over Time',
                        labels={'date': 'Date', 'count': 'Number of Registrations'}
                    )
                
                st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            # Patient demographics
            st.write("#### Patient Demographics")
            
            patient_demographics = database.query_to_dataframe(
                """
                SELECT gender, COUNT(*) as count
                FROM Patients
                GROUP BY gender
                """
            )
            
            if patient_demographics.empty:
                st.info("No patient demographic data available.")
            else:
                fig = px.pie(
                    patient_demographics, 
                    values='count', 
                    names='gender',
                    title='Patients by Gender',
                    color_discrete_sequence=px.colors.sequential.Teal
                )
                st.plotly_chart(fig, use_container_width=True)
        
        # Age distribution
        st.write("#### Patient Age Distribution")
        
        age_distribution = database.query_to_dataframe(
            """
            SELECT 
                CASE 
                    WHEN (julianday('now') - julianday(date_of_birth)) / 365.25 < 18 THEN 'Under 18'
                    WHEN (julianday('now') - julianday(date_of_birth)) / 365.25 BETWEEN 18 AND 30 THEN '18-30'
                    WHEN (julianday('now') - julianday(date_of_birth)) / 365.25 BETWEEN 31 AND 45 THEN '31-45'
                    WHEN (julianday('now') - julianday(date_of_birth)) / 365.25 BETWEEN 46 AND 60 THEN '46-60'
                    WHEN (julianday('now') - julianday(date_of_birth)) / 365.25 BETWEEN 61 AND 75 THEN '61-75'
                    ELSE 'Over 75'
                END as age_group,
                COUNT(*) as count
            FROM Patients
            GROUP BY age_group
            ORDER BY 
                CASE age_group
                    WHEN 'Under 18' THEN 1
                    WHEN '18-30' THEN 2
                    WHEN '31-45' THEN 3
                    WHEN '46-60' THEN 4
                    WHEN '61-75' THEN 5
                    ELSE 6
                END
            """
        )
        
        if age_distribution.empty:
            st.info("No patient age data available.")
        else:
            fig = px.bar(
                age_distribution, 
                x='age_group', 
                y='count',
                title='Patient Age Distribution',
                labels={'age_group': 'Age Group', 'count': 'Number of Patients'},
                color_discrete_sequence=['#f0e6d2']
            )
            st.plotly_chart(fig, use_container_width=True)
        
        # Appointment statistics
        st.write("#### Appointment Statistics")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Appointments by status
            appointment_status = database.query_to_dataframe(
                """
                SELECT status, COUNT(*) as count
                FROM Appointments
                WHERE appointment_date BETWEEN ? AND ?
                GROUP BY status
                """,
                (start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d'))
            )
            
            if appointment_status.empty:
                st.info("No appointment data available for the selected period.")
            else:
                fig = px.pie(
                    appointment_status, 
                    values='count', 
                    names='status',
                    title='Appointments by Status',
                    color_discrete_sequence=px.colors.qualitative.Pastel
                )
                st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            # Appointments by day of week
            appointments_by_day = database.query_to_dataframe(
                """
                SELECT 
                    CASE cast(strftime('%w', appointment_date) as integer)
                        WHEN 0 THEN 'Sunday'
                        WHEN 1 THEN 'Monday'
                        WHEN 2 THEN 'Tuesday'
                        WHEN 3 THEN 'Wednesday'
                        WHEN 4 THEN 'Thursday'
                        WHEN 5 THEN 'Friday'
                        WHEN 6 THEN 'Saturday'
                    END as day_of_week,
                    COUNT(*) as count
                FROM Appointments
                WHERE appointment_date BETWEEN ? AND ?
                GROUP BY day_of_week
                ORDER BY cast(strftime('%w', appointment_date) as integer)
                """,
                (start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d'))
            )
            
            if appointments_by_day.empty:
                st.info("No appointment data available for the selected period.")
            else:
                # Ensure all days of week are included
                all_days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
                day_df = pd.DataFrame({'day_of_week': all_days})
                
                merged_days = pd.merge(day_df, appointments_by_day, on='day_of_week', how='left')
                merged_days['count'] = merged_days['count'].fillna(0)
                
                # Create ordered categorical type for proper sorting
                merged_days['day_of_week'] = pd.Categorical(
                    merged_days['day_of_week'], 
                    categories=all_days, 
                    ordered=True
                )
                merged_days = merged_days.sort_values('day_of_week')
                
                fig = px.bar(
                    merged_days, 
                    x='day_of_week', 
                    y='count',
                    title='Appointments by Day of Week',
                    labels={'day_of_week': 'Day', 'count': 'Number of Appointments'},
                    color_discrete_sequence=['#f0e6d2']
                )
                st.plotly_chart(fig, use_container_width=True)
    
    with tab2:
        st.subheader("Financial Reports")
        
        # Time period selection
        financial_period = st.selectbox(
            "Time Period",
            ["Last 30 Days", "Last 3 Months", "Last 6 Months", "Last Year", "All Time"],
            key="financial_time_period"
        )
        
        # Calculate date range based on selection
        end_date = datetime.now().date()
        if financial_period == "Last 30 Days":
            start_date = end_date - timedelta(days=30)
        elif financial_period == "Last 3 Months":
            start_date = end_date - timedelta(days=90)
        elif financial_period == "Last 6 Months":
            start_date = end_date - timedelta(days=180)
        elif financial_period == "Last Year":
            start_date = end_date - timedelta(days=365)
        else:  # All Time
            start_date = datetime(2000, 1, 1).date()
        
        # Revenue summary
        st.write("#### Revenue Summary")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            # Total revenue
            total_revenue = database.fetch_one(
                """
                SELECT COALESCE(SUM(amount), 0) FROM Billing 
                WHERE bill_date BETWEEN ? AND ? AND status = 'paid'
                """,
                (start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d'))
            )[0]
            
            st.metric("Total Revenue", utils.format_currency(total_revenue))
        
        with col2:
            # Pending payments
            pending_amount = database.fetch_one(
                """
                SELECT COALESCE(SUM(amount), 0) FROM Billing 
                WHERE bill_date BETWEEN ? AND ? AND status != 'paid'
                """,
                (start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d'))
            )[0]
            
            st.metric("Pending Payments", utils.format_currency(pending_amount))
        
        with col3:
            # Average bill amount
            avg_bill = database.fetch_one(
                """
                SELECT COALESCE(AVG(amount), 0) FROM Billing 
                WHERE bill_date BETWEEN ? AND ?
                """,
                (start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d'))
            )[0]
            
            st.metric("Average Bill", utils.format_currency(avg_bill))
        
        # Revenue over time
        st.write("#### Revenue Over Time")
        
        revenue_over_time = database.query_to_dataframe(
            """
            SELECT 
                date(bill_date) as date, 
                SUM(amount) as revenue
            FROM Billing
            WHERE bill_date BETWEEN ? AND ? AND status = 'paid'
            GROUP BY date(bill_date)
            ORDER BY date
            """,
            (start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d'))
        )
        
        if revenue_over_time.empty:
            st.info("No revenue data available for the selected period.")
        else:
            # Fill in missing dates with zero revenue
            date_range = pd.date_range(start=start_date, end=end_date)
            full_date_df = pd.DataFrame({'date': date_range})
            full_date_df['date'] = full_date_df['date'].dt.strftime('%Y-%m-%d')
            
            revenue_over_time['date'] = revenue_over_time['date'].astype(str)
            
            merged_df = pd.merge(full_date_df, revenue_over_time, on='date', how='left')
            merged_df['revenue'] = merged_df['revenue'].fillna(0)
            
            # For longer time periods, resample to avoid overcrowded x-axis
            if financial_period in ["Last 6 Months", "Last Year", "All Time"]:
                merged_df['date'] = pd.to_datetime(merged_df['date'])
                if financial_period == "Last 6 Months":
                    resampled = merged_df.set_index('date').resample('W').sum().reset_index()
                else:  # Last Year or All Time
                    resampled = merged_df.set_index('date').resample('M').sum().reset_index()
                
                fig = px.line(
                    resampled, 
                    x='date', 
                    y='revenue',
                    title='Revenue Over Time',
                    labels={'date': 'Date', 'revenue': 'Revenue (KSh)'}
                )
            else:
                fig = px.line(
                    merged_df, 
                    x='date', 
                    y='revenue',
                    title='Revenue Over Time',
                    labels={'date': 'Date', 'revenue': 'Revenue (KSh)'}
                )
            
            fig.update_traces(line_color='#4c9085')
            st.plotly_chart(fig, use_container_width=True)
        
        # Revenue by service
        st.write("#### Revenue by Service Type")
        
        revenue_by_service = database.query_to_dataframe(
            """
            SELECT 
                service_description,
                COUNT(*) as count,
                SUM(amount) as total_amount,
                AVG(amount) as avg_amount
            FROM Billing
            WHERE bill_date BETWEEN ? AND ?
            GROUP BY service_description
            ORDER BY total_amount DESC
            LIMIT 10
            """,
            (start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d'))
        )
        
        if revenue_by_service.empty:
            st.info("No revenue by service data available for the selected period.")
        else:
            # Format currency columns
            revenue_by_service['total_amount'] = revenue_by_service['total_amount'].apply(utils.format_currency)
            revenue_by_service['avg_amount'] = revenue_by_service['avg_amount'].apply(utils.format_currency)
            
            # Display as table
            st.dataframe(revenue_by_service, use_container_width=True)
        
        # Payment status distribution
        st.write("#### Payment Status Distribution")
        
        payment_status = database.query_to_dataframe(
            """
            SELECT 
                status,
                COUNT(*) as count,
                SUM(amount) as total_amount
            FROM Billing
            WHERE bill_date BETWEEN ? AND ?
            GROUP BY status
            """,
            (start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d'))
        )
        
        if payment_status.empty:
            st.info("No payment status data available for the selected period.")
        else:
            fig = px.pie(
                payment_status, 
                values='total_amount', 
                names='status',
                title='Total Amount by Payment Status',
                color_discrete_sequence=px.colors.sequential.Viridis
            )
            st.plotly_chart(fig, use_container_width=True)
    
    with tab3:
        st.subheader("Inventory Reports")
        
        # Inventory summary
        st.write("#### Inventory Summary")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            # Total inventory value
            total_inventory_value = database.fetch_one(
                """
                SELECT COALESCE(SUM(quantity * unit_price), 0) FROM Inventory
                """
            )[0]
            
            st.metric("Total Inventory Value", utils.format_currency(total_inventory_value))
        
        with col2:
            # Low stock items
            low_stock_count = database.fetch_one(
                """
                SELECT COUNT(*) FROM Inventory 
                WHERE quantity <= reorder_level AND status = 'available'
                """
            )[0]
            
            st.metric("Low Stock Items", low_stock_count)
        
        with col3:
            # Out of stock items
            out_of_stock_count = database.fetch_one(
                """
                SELECT COUNT(*) FROM Inventory 
                WHERE quantity = 0 OR status = 'out of stock'
                """
            )[0]
            
            st.metric("Out of Stock Items", out_of_stock_count)
        
        # Inventory by category
        st.write("#### Inventory by Category")
        
        inventory_by_category = database.query_to_dataframe(
            """
            SELECT 
                category,
                COUNT(*) as item_count,
                SUM(quantity) as total_quantity,
                SUM(quantity * unit_price) as total_value
            FROM Inventory
            GROUP BY category
            ORDER BY total_value DESC
            """
        )
        
        if inventory_by_category.empty:
            st.info("No inventory data available.")
        else:
            # Store numeric values for chart before formatting
            inventory_by_category['value_numeric'] = inventory_by_category['total_value']
            
            # Format currency column for display
            inventory_by_category['total_value'] = inventory_by_category['total_value'].apply(utils.format_currency)
            
            # Display as table and chart
            st.dataframe(
                inventory_by_category[['category', 'item_count', 'total_quantity', 'total_value']], 
                use_container_width=True
            )
            
            fig = px.bar(
                inventory_by_category, 
                x='category', 
                y='value_numeric',
                title='Inventory Value by Category',
                labels={'category': 'Category', 'value_numeric': 'Total Value (KSh)'},
                color_discrete_sequence=['#f0e6d2']
            )
            st.plotly_chart(fig, use_container_width=True)
        
        # Top items by value
        st.write("#### Top Items by Value")
        
        top_items = database.query_to_dataframe(
            """
            SELECT 
                item_name,
                category,
                quantity,
                unit_price,
                quantity * unit_price as total_value
            FROM Inventory
            ORDER BY total_value DESC
            LIMIT 10
            """
        )
        
        if top_items.empty:
            st.info("No inventory data available.")
        else:
            # Format currency columns
            top_items['unit_price'] = top_items['unit_price'].apply(utils.format_currency)
            top_items['total_value'] = top_items['total_value'].apply(utils.format_currency)
            
            # Display as table
            st.dataframe(top_items, use_container_width=True)
        
        # Pharmacy inventory
        st.write("#### Pharmacy Inventory")
        
        pharmacy_inventory = database.query_to_dataframe(
            """
            SELECT 
                category,
                COUNT(*) as med_count,
                SUM(stock_quantity) as total_quantity,
                SUM(stock_quantity * unit_price) as total_value
            FROM Pharmacy
            GROUP BY category
            ORDER BY total_value DESC
            """
        )
        
        if pharmacy_inventory.empty:
            st.info("No pharmacy inventory data available.")
        else:
            # Store numeric values for chart before formatting
            pharmacy_inventory['value_numeric'] = pharmacy_inventory['total_value']
            
            # Format currency column for display
            pharmacy_inventory['total_value'] = pharmacy_inventory['total_value'].apply(utils.format_currency)
            
            # Display as chart
            fig = px.pie(
                pharmacy_inventory, 
                values='value_numeric', 
                names='category',
                title='Pharmacy Inventory Value by Category',
                color_discrete_sequence=px.colors.sequential.Teal
            )
            st.plotly_chart(fig, use_container_width=True)
    
    with tab4:
        st.subheader("Custom Reports")
        
        st.write("Create custom reports by specifying your own SQL query.")
        
        custom_query = st.text_area(
            "Enter SQL Query",
            """
            -- Example: Get count of appointments by doctor
            SELECT 
                u.full_name as doctor_name,
                COUNT(*) as appointment_count
            FROM Appointments a
            JOIN Users u ON a.doctor_id = u.user_id
            GROUP BY doctor_name
            ORDER BY appointment_count DESC
            """,
            height=200
        )
        
        if st.button("Run Query"):
            try:
                # Execute the custom query
                result_df = database.query_to_dataframe(custom_query)
                
                if result_df.empty:
                    st.info("Query returned no results.")
                else:
                    # Display results
                    st.write("#### Query Results")
                    st.dataframe(result_df, use_container_width=True)
                    
                    # Attempt to create a basic visualization if there are 2-3 columns
                    if len(result_df.columns) == 2:
                        numeric_cols = result_df.select_dtypes(include=['number']).columns
                        if len(numeric_cols) == 1:
                            category_col = [col for col in result_df.columns if col not in numeric_cols][0]
                            value_col = numeric_cols[0]
                            
                            st.write("#### Visualization")
                            
                            # Limit to top 10 if there are many rows
                            if len(result_df) > 10:
                                chart_df = result_df.sort_values(value_col, ascending=False).head(10)
                                st.info("Showing visualization for top 10 results only.")
                            else:
                                chart_df = result_df
                            
                            fig = px.bar(
                                chart_df, 
                                x=category_col, 
                                y=value_col,
                                title=f"{value_col} by {category_col}",
                                color_discrete_sequence=['#f0e6d2']
                            )
                            st.plotly_chart(fig, use_container_width=True)
            
            except Exception as e:
                st.error(f"Error executing query: {str(e)}")
        
        # Saved report templates
        st.write("#### Saved Report Templates")
        
        report_templates = {
            "Patient Visits by Month": """
                SELECT 
                    strftime('%Y-%m', appointment_date) as month,
                    COUNT(*) as visit_count
                FROM Appointments
                WHERE status != 'cancelled'
                GROUP BY month
                ORDER BY month
            """,
            "Top Doctors by Appointments": """
                SELECT 
                    u.full_name as doctor_name,
                    COUNT(*) as appointment_count
                FROM Appointments a
                JOIN Users u ON a.doctor_id = u.user_id
                WHERE a.status = 'completed'
                GROUP BY doctor_name
                ORDER BY appointment_count DESC
            """,
            "Revenue by Insurance Provider": """
                SELECT 
                    COALESCE(insurance_provider, 'Self-Pay') as provider,
                    COUNT(*) as bill_count,
                    SUM(amount) as total_amount
                FROM Billing
                GROUP BY provider
                ORDER BY total_amount DESC
            """
        }
        
        selected_template = st.selectbox(
            "Load Template", 
            ["Select a template..."] + list(report_templates.keys())
        )
        
        if selected_template != "Select a template...":
            if st.button("Load Template"):
                st.session_state.custom_query = report_templates[selected_template]
                st.rerun()
