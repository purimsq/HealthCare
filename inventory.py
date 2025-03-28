import streamlit as st
import database
import pandas as pd
import time
from datetime import datetime, timedelta
import audit

def get_low_stock_count():
    """Get count of items with stock below reorder level."""
    result = database.fetch_one(
        """
        SELECT COUNT(*) FROM Inventory 
        WHERE quantity <= reorder_level AND status = 'available'
        """
    )
    return result[0] if result else 0

def inventory_management():
    """Inventory management page."""
    st.header("Inventory Management")
    
    tab1, tab2, tab3 = st.tabs(["Inventory List", "Add Item", "Stock Management"])
    
    with tab1:
        st.subheader("Inventory List")
        
        # Filters
        col1, col2, col3 = st.columns(3)
        
        with col1:
            search_term = st.text_input("Search by name or category")
        
        with col2:
            category_filter = st.selectbox(
                "Category", 
                ["All"] + sorted(set([row[0] for row in database.fetch_all(
                    "SELECT DISTINCT category FROM Inventory ORDER BY category"
                ) or []])),
            )
        
        with col3:
            status_filter = st.selectbox(
                "Status", 
                ["All", "Available", "Low Stock", "Out of Stock", "Expired", "Discontinued"]
            )
        
        # Build query
        query = """
        SELECT 
            item_id, 
            item_name, 
            category, 
            quantity, 
            unit, 
            unit_price, 
            reorder_level, 
            expiry_date, 
            status,
            last_updated
        FROM Inventory
        """
        
        params = []
        where_clauses = []
        
        if search_term:
            where_clauses.append("(item_name LIKE ? OR category LIKE ?)")
            params.extend([f"%{search_term}%", f"%{search_term}%"])
        
        if category_filter != "All":
            where_clauses.append("category = ?")
            params.append(category_filter)
        
        if status_filter != "All":
            if status_filter == "Low Stock":
                where_clauses.append("quantity <= reorder_level AND quantity > 0 AND status = 'available'")
            elif status_filter == "Out of Stock":
                where_clauses.append("quantity = 0 AND status = 'available'")
            else:
                where_clauses.append("status = ?")
                params.append(status_filter.lower())
        
        # Finalize query
        if where_clauses:
            query += " WHERE " + " AND ".join(where_clauses)
        
        query += " ORDER BY category, item_name"
        
        # Execute query
        inventory_df = database.query_to_dataframe(query, params)
        
        if inventory_df.empty:
            st.info("No inventory items found matching your criteria.")
        else:
            # Add a total value column
            inventory_df['total_value'] = inventory_df['quantity'] * inventory_df['unit_price']
            
            # Format dates and currency
            inventory_df['expiry_date'] = pd.to_datetime(inventory_df['expiry_date']).dt.strftime('%Y-%m-%d')
            inventory_df['last_updated'] = pd.to_datetime(inventory_df['last_updated']).dt.strftime('%Y-%m-%d')
            inventory_df['unit_price'] = inventory_df['unit_price'].apply(lambda x: f"${x:.2f}")
            inventory_df['total_value'] = inventory_df['total_value'].apply(lambda x: f"${x:.2f}")
            
            # Add stock status indicator
            def get_stock_status(row):
                if row['quantity'] == 0:
                    return "⚠️ Out of Stock"
                elif row['quantity'] <= row['reorder_level']:
                    return "⚠️ Low Stock"
                return "✅ In Stock"
            
            inventory_df['stock_status'] = inventory_df.apply(get_stock_status, axis=1)
            
            # Reorder and rename columns for display
            display_df = inventory_df[[
                'item_id', 'item_name', 'category', 'quantity', 'unit', 
                'unit_price', 'total_value', 'stock_status', 'expiry_date'
            ]]
            
            display_df.columns = [
                'ID', 'Item Name', 'Category', 'Quantity', 'Unit', 
                'Unit Price', 'Total Value', 'Status', 'Expiry Date'
            ]
            
            st.dataframe(display_df, use_container_width=True)
            
            # Summary statistics
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                total_items = len(inventory_df)
                st.metric("Total Items", total_items)
            
            with col2:
                total_quantity = inventory_df['quantity'].sum()
                st.metric("Total Quantity", total_quantity)
            
            with col3:
                low_stock_items = len(inventory_df[inventory_df['quantity'] <= inventory_df['reorder_level']])
                st.metric("Low Stock Items", low_stock_items)
            
            with col4:
                total_value = inventory_df['quantity'] * pd.to_numeric(inventory_df['unit_price'].str.replace('$', ''))
                st.metric("Total Inventory Value", f"${total_value.sum():.2f}")
        
        # Item details and actions
        if not inventory_df.empty:
            st.subheader("Item Details")
            
            item_options = [f"{row['item_name']} (ID: {row['item_id']})" for _, row in inventory_df.iterrows()]
            selected_item = st.selectbox("Select Item", ["Select an item"] + item_options)
            
            if selected_item != "Select an item":
                item_id = int(selected_item.split("ID: ")[1].rstrip(')'))
                
                # Get item details
                item = database.fetch_one(
                    "SELECT * FROM Inventory WHERE item_id = ?",
                    (item_id,)
                )
                
                if item:
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.write(f"**ID:** {item[0]}")
                        st.write(f"**Name:** {item[1]}")
                        st.write(f"**Category:** {item[2]}")
                        st.write(f"**Quantity:** {item[3]} {item[4] or ''}")
                        st.write(f"**Unit Price:** ${item[5]:.2f}")
                    
                    with col2:
                        st.write(f"**Reorder Level:** {item[6]}")
                        st.write(f"**Supplier:** {item[7] or 'Not specified'}")
                        st.write(f"**Expiry Date:** {item[8] or 'Not applicable'}")
                        st.write(f"**Last Updated:** {item[9]}")
                        st.write(f"**Status:** {item[10]}")
                    
                    # Action buttons
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        if st.button("Update Stock"):
                            st.session_state.update_stock = item_id
                            st.rerun()
                    
                    with col2:
                        if st.button("Edit Item"):
                            st.session_state.edit_item = item_id
                            st.rerun()
                    
                    with col3:
                        if st.button("Delete Item"):
                            st.session_state.delete_item = item_id
                            st.rerun()
                    
                    # Handle stock update
                    if hasattr(st.session_state, 'update_stock') and st.session_state.update_stock == item_id:
                        with st.form("update_stock_form"):
                            st.subheader(f"Update Stock for: {item[1]}")
                            
                            col1, col2 = st.columns(2)
                            
                            with col1:
                                transaction_type = st.selectbox(
                                    "Transaction Type",
                                    ["Add Stock", "Remove Stock", "Set Stock Level"]
                                )
                            
                            with col2:
                                quantity = st.number_input(
                                    "Quantity",
                                    min_value=1,
                                    step=1,
                                    value=1
                                )
                            
                            reason = st.text_input("Reason for Update")
                            
                            update_stock_submitted = st.form_submit_button("Update Stock")
                            
                            if update_stock_submitted:
                                # Animation
                                with st.spinner("Updating stock..."):
                                    time.sleep(1)  # Simple animation delay
                                
                                # Calculate new quantity
                                new_quantity = item[3]
                                if transaction_type == "Add Stock":
                                    new_quantity += quantity
                                elif transaction_type == "Remove Stock":
                                    new_quantity = max(0, new_quantity - quantity)
                                else:  # Set Stock Level
                                    new_quantity = quantity
                                
                                # Determine new status
                                new_status = item[10]
                                if new_quantity == 0:
                                    new_status = "out of stock"
                                elif new_quantity <= item[6]:
                                    new_status = "low stock"
                                else:
                                    new_status = "available"
                                
                                # Update inventory
                                database.update_record(
                                    "Inventory",
                                    {
                                        "quantity": new_quantity,
                                        "status": new_status,
                                        "last_updated": datetime.now()
                                    },
                                    {"item_id": item_id}
                                )
                                
                                # Record in audit log
                                audit.record_activity(
                                    st.session_state.user_id,
                                    "Inventory Stock Update",
                                    f"{transaction_type}: {item[1]} (ID: {item_id}), Quantity: {quantity}, Reason: {reason}"
                                )
                                
                                st.success("Stock updated successfully!")
                                
                                # Clear the session state and rerun
                                del st.session_state.update_stock
                                time.sleep(1)
                                st.rerun()
                    
                    # Handle item edit
                    if hasattr(st.session_state, 'edit_item') and st.session_state.edit_item == item_id:
                        with st.form("edit_item_form"):
                            st.subheader(f"Edit Item: {item[1]}")
                            
                            col1, col2 = st.columns(2)
                            
                            with col1:
                                item_name = st.text_input("Item Name", item[1])
                                category = st.text_input("Category", item[2])
                                unit = st.text_input("Unit", item[4] or "")
                                unit_price = st.number_input("Unit Price ($)", min_value=0.0, value=float(item[5]), step=0.01)
                            
                            with col2:
                                reorder_level = st.number_input("Reorder Level", min_value=0, value=int(item[6]), step=1)
                                supplier = st.text_input("Supplier", item[7] or "")
                                expiry_date = st.date_input(
                                    "Expiry Date", 
                                    datetime.strptime(item[8], '%Y-%m-%d') if item[8] else None
                                )
                                status = st.selectbox(
                                    "Status",
                                    ["available", "low stock", "out of stock", "expired", "discontinued"],
                                    index=["available", "low stock", "out of stock", "expired", "discontinued"].index(item[10])
                                )
                            
                            edit_item_submitted = st.form_submit_button("Update Item")
                            
                            if edit_item_submitted:
                                # Animation
                                with st.spinner("Updating item..."):
                                    time.sleep(1)  # Simple animation delay
                                
                                # Update item
                                database.update_record(
                                    "Inventory",
                                    {
                                        "item_name": item_name,
                                        "category": category,
                                        "unit": unit,
                                        "unit_price": unit_price,
                                        "reorder_level": reorder_level,
                                        "supplier": supplier,
                                        "expiry_date": expiry_date.strftime('%Y-%m-%d') if expiry_date else None,
                                        "status": status,
                                        "last_updated": datetime.now()
                                    },
                                    {"item_id": item_id}
                                )
                                
                                # Record in audit log
                                audit.record_activity(
                                    st.session_state.user_id,
                                    "Inventory Item Updated",
                                    f"Updated item: {item_name} (ID: {item_id})"
                                )
                                
                                st.success("Item updated successfully!")
                                
                                # Clear the session state and rerun
                                del st.session_state.edit_item
                                time.sleep(1)
                                st.rerun()
                    
                    # Handle item delete
                    if hasattr(st.session_state, 'delete_item') and st.session_state.delete_item == item_id:
                        st.warning(f"Are you sure you want to delete {item[1]}?")
                        st.write("This action cannot be undone.")
                        
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            if st.button("Yes, Delete"):
                                # Animation
                                with st.spinner("Deleting item..."):
                                    time.sleep(1.5)  # Simple animation delay
                                
                                # Check if item is used in any prescriptions
                                used_in_prescriptions = database.fetch_one(
                                    "SELECT COUNT(*) FROM Prescriptions WHERE medication_id = ?",
                                    (item_id,)
                                )[0] > 0
                                
                                if used_in_prescriptions:
                                    st.error("This item cannot be deleted as it is referenced in prescriptions. Consider marking it as discontinued instead.")
                                else:
                                    # Delete item
                                    database.delete_record(
                                        "Inventory",
                                        {"item_id": item_id}
                                    )
                                    
                                    # Record in audit log
                                    audit.record_activity(
                                        st.session_state.user_id,
                                        "Inventory Item Deleted",
                                        f"Deleted item: {item[1]} (ID: {item_id})"
                                    )
                                    
                                    st.success("Item deleted successfully!")
                                    
                                    # Clear the session state and rerun
                                    del st.session_state.delete_item
                                    time.sleep(1)
                                    st.rerun()
                        
                        with col2:
                            if st.button("No, Cancel"):
                                del st.session_state.delete_item
                                st.rerun()
    
    with tab2:
        st.subheader("Add New Inventory Item")
        
        with st.form("add_item_form"):
            col1, col2 = st.columns(2)
            
            with col1:
                new_item_name = st.text_input("Item Name*")
                new_category = st.text_input("Category*")
                new_quantity = st.number_input("Initial Quantity*", min_value=0, step=1)
                new_unit = st.text_input("Unit (e.g., box, pack, bottle)")
                new_unit_price = st.number_input("Unit Price ($)*", min_value=0.0, step=0.01)
            
            with col2:
                new_reorder_level = st.number_input("Reorder Level*", min_value=0, step=1)
                new_supplier = st.text_input("Supplier")
                new_expiry_date = st.date_input("Expiry Date (if applicable)", min_value=datetime.now().date())
                new_status = st.selectbox(
                    "Status",
                    ["available", "low stock", "out of stock", "expired", "discontinued"],
                    index=0
                )
            
            add_item_submitted = st.form_submit_button("Add Item")
            
            if add_item_submitted:
                if not new_item_name or not new_category:
                    st.error("Please fill in all required fields.")
                else:
                    # Animation
                    with st.spinner("Adding new item..."):
                        time.sleep(1)  # Simple animation delay
                    
                    # Determine initial status based on quantity and reorder level
                    initial_status = new_status
                    if new_quantity == 0:
                        initial_status = "out of stock"
                    elif new_quantity <= new_reorder_level:
                        initial_status = "low stock"
                    
                    # Add item
                    item_id = database.insert_record(
                        "Inventory",
                        {
                            "item_name": new_item_name,
                            "category": new_category,
                            "quantity": new_quantity,
                            "unit": new_unit,
                            "unit_price": new_unit_price,
                            "supplier": new_supplier,
                            "reorder_level": new_reorder_level,
                            "expiry_date": new_expiry_date.strftime('%Y-%m-%d') if new_expiry_date else None,
                            "last_updated": datetime.now(),
                            "status": initial_status
                        }
                    )
                    
                    # Record in audit log
                    audit.record_activity(
                        st.session_state.user_id,
                        "Inventory Item Added",
                        f"Added new item: {new_item_name} (ID: {item_id})"
                    )
                    
                    st.success(f"Item added successfully! Item ID: {item_id}")
                    time.sleep(1)
                    st.rerun()
    
    with tab3:
        st.subheader("Stock Management")
        
        # Low stock alert
        low_stock_items = database.query_to_dataframe(
            """
            SELECT 
                item_id, 
                item_name, 
                category, 
                quantity, 
                reorder_level,
                unit_price,
                supplier
            FROM Inventory
            WHERE quantity <= reorder_level AND status = 'available'
            ORDER BY (quantity / reorder_level) ASC
            """
        )
        
        st.write("### Low Stock Alerts")
        
        if low_stock_items.empty:
            st.success("No items are currently low on stock.")
        else:
            # Calculate percentage of stock remaining
            low_stock_items['stock_percentage'] = (low_stock_items['quantity'] / low_stock_items['reorder_level'] * 100).round(1)
            
            # Format for display
            low_stock_items['unit_price'] = low_stock_items['unit_price'].apply(lambda x: f"${x:.2f}")
            
            # Add reorder amount suggestion (to reach 150% of reorder level)
            low_stock_items['suggested_reorder'] = ((low_stock_items['reorder_level'] * 1.5) - low_stock_items['quantity']).astype(int)
            
            # Display dataframe
            display_df = low_stock_items[[
                'item_id', 'item_name', 'category', 'quantity', 'reorder_level', 
                'stock_percentage', 'suggested_reorder', 'supplier'
            ]]
            
            display_df.columns = [
                'ID', 'Item Name', 'Category', 'Current Stock', 'Reorder Level', 
                'Stock %', 'Suggested Order', 'Supplier'
            ]
            
            st.dataframe(display_df, use_container_width=True)
            
            # Quick reorder form
            st.write("### Quick Reorder")
            
            with st.form("reorder_form"):
                item_options = [f"{row['item_name']} (ID: {row['item_id']})" for _, row in low_stock_items.iterrows()]
                
                col1, col2 = st.columns(2)
                
                with col1:
                    selected_reorder_item = st.selectbox(
                        "Select Item to Reorder",
                        item_options
                    )
                
                with col2:
                    reorder_amount = st.number_input(
                        "Order Quantity",
                        min_value=1,
                        step=1,
                        value=int(low_stock_items[
                            low_stock_items['item_id'] == int(selected_reorder_item.split("ID: ")[1].rstrip(')'))
                        ]['suggested_reorder'].values[0])
                    )
                
                reorder_notes = st.text_area("Order Notes")
                
                reorder_submitted = st.form_submit_button("Place Order")
                
                if reorder_submitted:
                    # Animation
                    with st.spinner("Processing order..."):
                        time.sleep(1.5)  # Simple animation delay
                    
                    # Get item ID
                    reorder_item_id = int(selected_reorder_item.split("ID: ")[1].rstrip(')'))
                    
                    # Get current quantity
                    current_quantity = database.fetch_one(
                        "SELECT quantity FROM Inventory WHERE item_id = ?",
                        (reorder_item_id,)
                    )[0]
                    
                    # Update inventory
                    new_quantity = current_quantity + reorder_amount
                    
                    database.update_record(
                        "Inventory",
                        {
                            "quantity": new_quantity,
                            "status": "available",
                            "last_updated": datetime.now()
                        },
                        {"item_id": reorder_item_id}
                    )
                    
                    # Record in audit log
                    audit.record_activity(
                        st.session_state.user_id,
                        "Inventory Reorder",
                        f"Reordered {reorder_amount} units of item ID {reorder_item_id}. Notes: {reorder_notes}"
                    )
                    
                    st.success(f"Order placed successfully! New stock level: {new_quantity}")
                    time.sleep(1)
                    st.rerun()
        
        # Expiring items
        st.write("### Expiring Items")
        
        # Get items expiring in the next 30 days
        thirty_days_later = (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d')
        today = datetime.now().strftime('%Y-%m-%d')
        
        expiring_items = database.query_to_dataframe(
            """
            SELECT 
                item_id, 
                item_name, 
                category, 
                quantity, 
                expiry_date,
                unit_price
            FROM Inventory
            WHERE expiry_date BETWEEN ? AND ? AND status != 'expired' AND quantity > 0
            ORDER BY expiry_date ASC
            """,
            (today, thirty_days_later)
        )
        
        if expiring_items.empty:
            st.info("No items are due to expire in the next 30 days.")
        else:
            # Calculate days until expiry
            expiring_items['expiry_date'] = pd.to_datetime(expiring_items['expiry_date'])
            expiring_items['days_until_expiry'] = (expiring_items['expiry_date'] - pd.to_datetime(today)).dt.days
            
            # Format for display
            expiring_items['expiry_date'] = expiring_items['expiry_date'].dt.strftime('%Y-%m-%d')
            expiring_items['unit_price'] = expiring_items['unit_price'].apply(lambda x: f"${x:.2f}")
            expiring_items['value'] = (expiring_items['quantity'] * pd.to_numeric(expiring_items['unit_price'].str.replace('$', ''))).apply(lambda x: f"${x:.2f}")
            
            # Display dataframe
            display_df = expiring_items[[
                'item_id', 'item_name', 'category', 'quantity', 'expiry_date', 
                'days_until_expiry', 'value'
            ]]
            
            display_df.columns = [
                'ID', 'Item Name', 'Category', 'Quantity', 'Expiry Date', 
                'Days Left', 'Value'
            ]
            
            st.dataframe(display_df, use_container_width=True)
