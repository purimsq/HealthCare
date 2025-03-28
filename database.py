import sqlite3
import streamlit as st
import pandas as pd
import os
from datetime import datetime

# Database initialization
def init_db():
    conn = get_connection()
    
    # Create Users table
    conn.execute('''
    CREATE TABLE IF NOT EXISTS Users (
        user_id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        full_name TEXT NOT NULL,
        role TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        last_login TIMESTAMP,
        status TEXT DEFAULT 'active'
    )
    ''')
    
    # Create Patients table
    conn.execute('''
    CREATE TABLE IF NOT EXISTS Patients (
        patient_id INTEGER PRIMARY KEY AUTOINCREMENT,
        first_name TEXT NOT NULL,
        last_name TEXT NOT NULL,
        date_of_birth DATE NOT NULL,
        gender TEXT NOT NULL,
        blood_group TEXT,
        address TEXT,
        contact_number TEXT NOT NULL,
        email TEXT,
        emergency_contact TEXT,
        emergency_contact_number TEXT,
        registration_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        notes TEXT,
        status TEXT DEFAULT 'active'
    )
    ''')
    
    # Create MedicalHistory table
    conn.execute('''
    CREATE TABLE IF NOT EXISTS MedicalHistory (
        record_id INTEGER PRIMARY KEY AUTOINCREMENT,
        patient_id INTEGER NOT NULL,
        diagnosis TEXT NOT NULL,
        treatment TEXT,
        doctor_id INTEGER NOT NULL,
        date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        notes TEXT,
        FOREIGN KEY (patient_id) REFERENCES Patients(patient_id),
        FOREIGN KEY (doctor_id) REFERENCES Users(user_id)
    )
    ''')
    
    # Create Appointments table
    conn.execute('''
    CREATE TABLE IF NOT EXISTS Appointments (
        appointment_id INTEGER PRIMARY KEY AUTOINCREMENT,
        patient_id INTEGER NOT NULL,
        doctor_id INTEGER NOT NULL,
        appointment_date DATE NOT NULL,
        appointment_time TIME NOT NULL,
        status TEXT DEFAULT 'scheduled',
        reason TEXT,
        notes TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (patient_id) REFERENCES Patients(patient_id),
        FOREIGN KEY (doctor_id) REFERENCES Users(user_id)
    )
    ''')
    
    # Create Billing table
    conn.execute('''
    CREATE TABLE IF NOT EXISTS Billing (
        bill_id INTEGER PRIMARY KEY AUTOINCREMENT,
        patient_id INTEGER NOT NULL,
        service_description TEXT NOT NULL,
        amount REAL NOT NULL,
        insurance_provider TEXT,
        insurance_policy_number TEXT,
        bill_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        due_date DATE,
        status TEXT DEFAULT 'unpaid',
        FOREIGN KEY (patient_id) REFERENCES Patients(patient_id)
    )
    ''')
    
    # Create Inventory table
    conn.execute('''
    CREATE TABLE IF NOT EXISTS Inventory (
        item_id INTEGER PRIMARY KEY AUTOINCREMENT,
        item_name TEXT NOT NULL,
        category TEXT NOT NULL,
        quantity INTEGER NOT NULL,
        unit TEXT,
        unit_price REAL NOT NULL,
        supplier TEXT,
        reorder_level INTEGER,
        expiry_date DATE,
        last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        status TEXT DEFAULT 'available'
    )
    ''')
    
    # Create Pharmacy table
    conn.execute('''
    CREATE TABLE IF NOT EXISTS Pharmacy (
        medication_id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        generic_name TEXT,
        category TEXT,
        dosage TEXT,
        stock_quantity INTEGER NOT NULL,
        unit_price REAL NOT NULL,
        supplier TEXT,
        reorder_level INTEGER,
        expiry_date DATE,
        status TEXT DEFAULT 'available'
    )
    ''')
    
    # Create Prescriptions table
    conn.execute('''
    CREATE TABLE IF NOT EXISTS Prescriptions (
        prescription_id INTEGER PRIMARY KEY AUTOINCREMENT,
        patient_id INTEGER NOT NULL,
        doctor_id INTEGER NOT NULL,
        medication_id INTEGER NOT NULL,
        dosage TEXT NOT NULL,
        frequency TEXT NOT NULL,
        duration TEXT NOT NULL,
        notes TEXT,
        status TEXT DEFAULT 'pending',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (patient_id) REFERENCES Patients(patient_id),
        FOREIGN KEY (doctor_id) REFERENCES Users(user_id),
        FOREIGN KEY (medication_id) REFERENCES Pharmacy(medication_id)
    )
    ''')
    
    # Create AuditLogs table
    conn.execute('''
    CREATE TABLE IF NOT EXISTS AuditLogs (
        log_id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        activity TEXT NOT NULL,
        details TEXT,
        ip_address TEXT,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES Users(user_id)
    )
    ''')
    
    # Create Staff table
    conn.execute('''
    CREATE TABLE IF NOT EXISTS Staff (
        staff_id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        department TEXT NOT NULL,
        position TEXT NOT NULL,
        hire_date DATE NOT NULL,
        salary REAL,
        contact_number TEXT,
        emergency_contact TEXT,
        status TEXT DEFAULT 'active',
        FOREIGN KEY (user_id) REFERENCES Users(user_id)
    )
    ''')
    
    # Create UserSessions table
    conn.execute('''
    CREATE TABLE IF NOT EXISTS UserSessions (
        session_id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        login_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        logout_time TIMESTAMP,
        ip_address TEXT,
        status TEXT DEFAULT 'active',
        FOREIGN KEY (user_id) REFERENCES Users(user_id)
    )
    ''')
    
    conn.commit()
    conn.close()

def get_connection():
    """Create or get existing SQLite database connection"""
    return sqlite3.connect('hospital_management.db', detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES)

def execute_query(query, params=None):
    """Execute a query with optional parameters"""
    conn = get_connection()
    
    if params:
        conn.execute(query, params)
    else:
        conn.execute(query)
    
    conn.commit()
    conn.close()

def fetch_one(query, params=None):
    """Fetch one row from a query"""
    conn = get_connection()
    
    if params:
        result = conn.execute(query, params).fetchone()
    else:
        result = conn.execute(query).fetchone()
    
    conn.close()
    return result

def fetch_all(query, params=None):
    """Fetch all rows from a query"""
    conn = get_connection()
    
    if params:
        results = conn.execute(query, params).fetchall()
    else:
        results = conn.execute(query).fetchall()
    
    conn.close()
    return results

def query_to_dataframe(query, params=None):
    """Execute a query and return results as a pandas DataFrame"""
    conn = get_connection()
    
    try:
        if params:
            df = pd.read_sql_query(query, conn, params=params)
        else:
            df = pd.read_sql_query(query, conn)
        
        # Handle date columns gracefully
        for col in df.columns:
            if col.endswith('_date') or col in ['created_at', 'last_login', 'bill_date', 'due_date', 'date']:
                try:
                    df[col] = pd.to_datetime(df[col], errors='coerce')
                except:
                    pass  # Keep as is if conversion fails
        
        return df
    except Exception as e:
        print(f"Error in query_to_dataframe: {e}")
        # Return empty dataframe with expected columns if possible
        return pd.DataFrame()
    finally:
        conn.close()

def insert_record(table, data):
    """Insert a record into a table and return the ID"""
    conn = None
    retries = 3
    retry_delay = 0.5
    last_id = None
    
    # Try multiple times to handle potential database locks
    for attempt in range(retries):
        try:
            conn = get_connection()
            
            columns = ', '.join(data.keys())
            placeholders = ', '.join(['?' for _ in data])
            values = tuple(data.values())
            
            query = f"INSERT INTO {table} ({columns}) VALUES ({placeholders})"
            
            cursor = conn.cursor()
            cursor.execute(query, values)
            last_id = cursor.lastrowid
            
            conn.commit()
            break  # Success, exit the retry loop
        except sqlite3.OperationalError as e:
            # If database is locked, retry after a delay
            if "database is locked" in str(e) and attempt < retries - 1:
                if conn:
                    conn.close()
                import time
                time.sleep(retry_delay)
                print(f"Database locked, retrying... (attempt {attempt+1})")
            else:
                # Re-raise the exception if it's not a locking issue or we've exhausted retries
                if conn:
                    conn.close()
                print(f"Database error: {e}")
                return None
        except Exception as e:
            # Handle any other exceptions
            if conn:
                conn.close()
            print(f"Error inserting record: {e}")
            return None
        finally:
            if conn:
                conn.close()
    
    return last_id

def update_record(table, data, condition):
    """Update a record in a table"""
    conn = None
    retries = 3
    retry_delay = 0.5
    
    # Try multiple times to handle potential database locks
    for attempt in range(retries):
        try:
            conn = get_connection()
            
            set_clause = ', '.join([f"{key} = ?" for key in data.keys()])
            values = list(data.values())
            
            where_clause = ' AND '.join([f"{key} = ?" for key in condition.keys()])
            values.extend(condition.values())
            
            query = f"UPDATE {table} SET {set_clause} WHERE {where_clause}"
            
            conn.execute(query, values)
            conn.commit()
            break  # Success, exit the retry loop
        except sqlite3.OperationalError as e:
            # If database is locked, retry after a delay
            if "database is locked" in str(e) and attempt < retries - 1:
                if conn:
                    conn.close()
                import time
                time.sleep(retry_delay)
                print(f"Database locked during update, retrying... (attempt {attempt+1})")
            else:
                # Re-raise the exception if it's not a locking issue or we've exhausted retries
                if conn:
                    conn.close()
                print(f"Database error during update: {e}")
                return False
        except Exception as e:
            # Handle any other exceptions
            if conn:
                conn.close()
            print(f"Error updating record: {e}")
            return False
        finally:
            if conn:
                conn.close()
    
    return True

def delete_record(table, condition):
    """Delete a record from a table"""
    conn = None
    retries = 3
    retry_delay = 0.5
    
    # Try multiple times to handle potential database locks
    for attempt in range(retries):
        try:
            conn = get_connection()
            
            where_clause = ' AND '.join([f"{key} = ?" for key in condition.keys()])
            values = list(condition.values())
            
            query = f"DELETE FROM {table} WHERE {where_clause}"
            
            conn.execute(query, values)
            conn.commit()
            break  # Success, exit the retry loop
        except sqlite3.OperationalError as e:
            # If database is locked, retry after a delay
            if "database is locked" in str(e) and attempt < retries - 1:
                if conn:
                    conn.close()
                import time
                time.sleep(retry_delay)
                print(f"Database locked during delete, retrying... (attempt {attempt+1})")
            else:
                # Re-raise the exception if it's not a locking issue or we've exhausted retries
                if conn:
                    conn.close()
                print(f"Database error during delete: {e}")
                return False
        except Exception as e:
            # Handle any other exceptions
            if conn:
                conn.close()
            print(f"Error deleting record: {e}")
            return False
        finally:
            if conn:
                conn.close()
    
    return True
