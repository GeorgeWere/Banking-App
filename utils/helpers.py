# utils/helpers.py
import re
import random
import time
import json
from datetime import datetime
from flask import request
from extensions import mysql
from utils.logger import bank_logger

def get_client_ip():
    """Get client IP address"""
    if request.headers.get('X-Forwarded-For'):
        return request.headers.get('X-Forwarded-For').split(',')[0]
    return request.remote_addr or '127.0.0.1'

def generate_account_number(user_id=None):
    """Generate unique account number"""
    time_part = str(int(time.time() * 1000))[-8:]
    random_part = str(random.randint(1000, 9999))
    
    if user_id:
        user_part = str(user_id)[-3:].zfill(3)
    else:
        user_part = str(random.randint(100, 999))
    
    account_number = f"ACC{time_part}{random_part}{user_part}"
    return account_number[:20]

def write_to_audit_table(user_id, action, entity_type=None, entity_id=None, old_values=None, new_values=None):
    """Write to database audit table"""
    try:
        cursor = mysql.connection.cursor()
        query = """
            INSERT INTO audit_log 
            (user_id, action, entity_type, entity_id, old_values, new_values, ip_address, user_agent)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """
        cursor.execute(query, (
            user_id, action, entity_type, entity_id,
            json.dumps(old_values, default=str) if old_values else None,
            json.dumps(new_values, default=str) if new_values else None,
            get_client_ip(),
            request.headers.get('User-Agent', 'Unknown')
        ))
        mysql.connection.commit()
        cursor.close()
        
        bank_logger.log_audit(
            user_id,
            get_client_ip(),
            action,
            {'entity_type': entity_type, 'entity_id': entity_id}
        )
    except Exception as e:
        bank_logger.log_error(e, context="write_to_audit_table")

def validate_email(email):
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def validate_phone(phone):
    if not phone:
        return True
    pattern = r'^[\d\s\+\-\(\)]{10,}$'
    return re.match(pattern, phone) is not None

def format_currency(amount):
    return f"${amount:,.2f}"