import streamlit as st
from datetime import datetime, timedelta

def format_time_difference(start_time, end_time):
    """
    Format the time difference between two datetime objects in a human-readable format.
    
    Args:
        start_time (datetime): The starting time
        end_time (datetime): The ending time
    
    Returns:
        str: Formatted time difference string
    """
    if not start_time or not end_time:
        return "Unknown"
    
    # Calculate time difference
    diff = end_time - start_time
    
    # Extract days, hours, minutes, seconds
    days = diff.days
    seconds = diff.seconds
    hours, remainder = divmod(seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    
    # Format the time difference
    if days > 0:
        return f"{days}d {hours}h {minutes}m"
    elif hours > 0:
        return f"{hours}h {minutes}m"
    elif minutes > 0:
        return f"{minutes}m {seconds}s"
    else:
        return f"{seconds}s"

def get_date_range_from_selection(selection):
    """
    Get start and end dates based on a time period selection.
    
    Args:
        selection (str): Time period selection string
    
    Returns:
        tuple: (start_date, end_date) as datetime.date objects
    """
    end_date = datetime.now().date()
    
    if selection == "Today":
        start_date = end_date
    elif selection == "Yesterday":
        start_date = end_date - timedelta(days=1)
        end_date = start_date
    elif selection == "Last 7 Days":
        start_date = end_date - timedelta(days=6)
    elif selection == "Last 30 Days":
        start_date = end_date - timedelta(days=29)
    elif selection == "This Month":
        start_date = end_date.replace(day=1)
    elif selection == "Last Month":
        last_month = end_date.month - 1 if end_date.month > 1 else 12
        last_month_year = end_date.year if end_date.month > 1 else end_date.year - 1
        last_month_last_day = (datetime(last_month_year, last_month + 1, 1) - timedelta(days=1)).day
        
        start_date = datetime(last_month_year, last_month, 1).date()
        end_date = datetime(last_month_year, last_month, last_month_last_day).date()
    elif selection == "This Year":
        start_date = datetime(end_date.year, 1, 1).date()
    else:  # All Time
        start_date = datetime(2000, 1, 1).date()
    
    return start_date, end_date

def status_color(status):
    """
    Return a color based on a status string.
    
    Args:
        status (str): Status string
    
    Returns:
        str: CSS color code
    """
    status = status.lower() if status else ""
    
    if "active" in status or "available" in status or "completed" in status or "paid" in status:
        return "green"
    elif "pending" in status or "scheduled" in status or "partial" in status:
        return "orange"
    elif "inactive" in status or "cancelled" in status or "discontinued" in status:
        return "red"
    elif "low" in status:
        return "orange"
    elif "out" in status or "expired" in status:
        return "red"
    else:
        return "gray"

def format_currency(amount):
    """
    Format a number as currency.
    
    Args:
        amount (float): The amount to format
    
    Returns:
        str: Formatted currency string
    """
    if amount is None:
        return "$0.00"
    
    return f"${amount:,.2f}"

def calculate_age(birth_date):
    """
    Calculate age from birth date.
    
    Args:
        birth_date (str or datetime): Birth date
    
    Returns:
        int: Age in years
    """
    if not birth_date:
        return None
    
    if isinstance(birth_date, str):
        try:
            birth_date = datetime.strptime(birth_date, '%Y-%m-%d').date()
        except ValueError:
            return None
    
    today = datetime.now().date()
    
    age = today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))
    
    return age

def generate_patient_id(first_name, last_name):
    """
    Generate a patient ID based on name and current timestamp.
    
    Args:
        first_name (str): Patient's first name
        last_name (str): Patient's last name
    
    Returns:
        str: Generated patient ID
    """
    # Get first letter of first name, first 3 letters of last name, and current timestamp
    name_part = (first_name[0] + last_name[:3]).upper()
    time_part = datetime.now().strftime("%m%d%y%H%M")
    
    return f"{name_part}{time_part}"

def mask_pii(text, mask_char='*'):
    """
    Mask personally identifiable information in text.
    
    Args:
        text (str): Text containing PII
        mask_char (str): Character to use for masking
    
    Returns:
        str: Text with PII masked
    """
    if not text:
        return ""
    
    # For simple implementation, just mask middle characters
    if len(text) <= 4:
        return text
    
    visible_chars = len(text) // 4
    return text[:visible_chars] + mask_char * (len(text) - 2 * visible_chars) + text[-visible_chars:]
