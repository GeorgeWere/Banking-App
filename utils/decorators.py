# utils/decorators.py
from functools import wraps
from flask import session, flash, redirect, url_for, request
from utils.logger import bank_logger
from utils.helpers import get_client_ip
from datetime import datetime

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('auth.login'))
        if session.get('role') != 'admin':
            bank_logger.log_audit(
                session.get('user_id'),
                get_client_ip(),
                'UNAUTHORIZED_ACCESS',
                {'attempted_url': request.url, 'user_role': session.get('role')}
            )
            flash('Access denied. Admin privileges required.', 'danger')
            return redirect(url_for('customer.dashboard'))
        return f(*args, **kwargs)
    return decorated_function

def log_performance(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        start = datetime.now()
        response = f(*args, **kwargs)
        duration = (datetime.now() - start).total_seconds() * 1000
        # Log performance (you can implement this)
        return response
    return decorated_function