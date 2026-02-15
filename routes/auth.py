# routes/auth.py
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from extensions import mysql, bcrypt
from utils.logger import bank_logger
from utils.helpers import get_client_ip, validate_email, validate_phone, generate_account_number, write_to_audit_table
import re
from datetime import datetime

auth_bp = Blueprint('auth', __name__)

# routes/auth.py (FIXED LOGIN ROUTE)
@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """User login"""
    # If already logged in, redirect to appropriate dashboard
    if session.get('user_id'):
        if session.get('role') == 'admin':
            return redirect(url_for('admin.dashboard'))
        return redirect(url_for('customer.dashboard'))
    
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        remember = request.form.get('remember_me') == 'on'
        
        if not username or not password:
            flash('Please fill in all fields.', 'danger')
            return render_template('login.html')
        
        cursor = mysql.connection.cursor()
        try:
            cursor.execute("SELECT * FROM users WHERE username = %s OR email = %s", (username, username))
            user = cursor.fetchone()
            
            if user and bcrypt.check_password_hash(user['password_hash'], password):
                if not user['is_active']:
                    flash('Your account is deactivated. Contact admin.', 'danger')
                    return render_template('login.html')
                
                # Set session - EXPLICITLY set each value
                session.clear()  # Clear any existing session
                session['user_id'] = user['user_id']
                session['username'] = user['username']
                session['role'] = user['role']
                session['user_fullname'] = f"{user['first_name'] or ''} {user['last_name'] or ''}".strip()
                
                # Make session permanent if remember is checked
                session.permanent = remember
                
                # Force session to be saved
                session.modified = True
                
                # Update last login
                cursor.execute("UPDATE users SET last_login = NOW() WHERE user_id = %s", (user['user_id'],))
                mysql.connection.commit()
                
                # Log the login
                bank_logger.log_audit(user['user_id'], get_client_ip(), 'LOGIN_SUCCESS', {'username': username})
                
                flash(f'Welcome back, {session["user_fullname"] or username}!', 'success')
                
                # Redirect based on role
                if user['role'] == 'admin':
                    return redirect(url_for('admin.dashboard'))
                return redirect(url_for('customer.dashboard'))
            else:
                bank_logger.log_audit(None, get_client_ip(), 'LOGIN_FAILED', {'username': username})
                flash('Invalid username or password.', 'danger')
        except Exception as e:
            bank_logger.log_error(e, context="login")
            flash('Login error. Please try again.', 'danger')
        finally:
            cursor.close()
    
    return render_template('login.html')

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        # Get form data
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        first_name = request.form.get('first_name', '').strip()
        last_name = request.form.get('last_name', '').strip()
        phone = request.form.get('phone', '').strip()
        account_type = request.form.get('account_type', 'both')
        initial_deposit = float(request.form.get('initial_deposit', 1000))
        
        # Validation
        errors = []
        if len(username) < 3:
            errors.append("Username must be at least 3 characters.")
        if not validate_email(email):
            errors.append("Invalid email address.")
        if len(password) < 6:
            errors.append("Password must be at least 6 characters.")
        if password != confirm_password:
            errors.append("Passwords do not match.")
        if initial_deposit < 1000:
            errors.append("Initial deposit must be at least $1000.")
        
        if errors:
            for error in errors:
                flash(error, 'danger')
            return render_template('register.html')
        
        cursor = mysql.connection.cursor()
        cursor.execute("SELECT * FROM users WHERE username = %s OR email = %s", (username, email))
        if cursor.fetchone():
            cursor.close()
            flash('Username or email already exists.', 'danger')
            return render_template('register.html')
        
        try:
            cursor.execute("START TRANSACTION")
            
            password_hash = bcrypt.generate_password_hash(password).decode('utf-8')
            cursor.execute("""
                INSERT INTO users (username, email, password_hash, first_name, last_name, phone)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (username, email, password_hash, first_name, last_name, phone))
            user_id = cursor.lastrowid
            
            if account_type in ['savings', 'both']:
                acc_num = generate_account_number(user_id)
                amount = initial_deposit / 2 if account_type == 'both' else initial_deposit
                cursor.execute("""
                    INSERT INTO accounts (account_number, user_id, account_type, balance, available_balance, opened_date)
                    VALUES (%s, %s, 'savings', %s, %s, CURDATE())
                """, (acc_num, user_id, amount, amount))
            
            if account_type in ['checking', 'both']:
                acc_num = generate_account_number(user_id)
                amount = initial_deposit / 2 if account_type == 'both' else initial_deposit
                cursor.execute("""
                    INSERT INTO accounts (account_number, user_id, account_type, balance, available_balance, opened_date)
                    VALUES (%s, %s, 'checking', %s, %s, CURDATE())
                """, (acc_num, user_id, amount, amount))
            
            mysql.connection.commit()
            bank_logger.log_audit(user_id, get_client_ip(), 'REGISTER', {'username': username})
            flash('Registration successful! Please log in.', 'success')
            return redirect(url_for('auth.login'))
            
        except Exception as e:
            mysql.connection.rollback()
            bank_logger.log_error(e, context="registration")
            flash('Registration failed. Please try again.', 'danger')
        finally:
            cursor.close()
    
    return render_template('register.html')

@auth_bp.route('/logout')
def logout():
    user_id = session.get('user_id')
    if user_id:
        bank_logger.log_audit(user_id, get_client_ip(), 'LOGOUT', {})
        write_to_audit_table(user_id, 'LOGOUT', 'user', user_id)
    
    session.clear()
    flash('You have been logged out successfully.', 'info')
    return redirect(url_for('auth.login'))