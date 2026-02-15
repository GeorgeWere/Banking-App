# routes/admin.py
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from extensions import mysql
from utils.decorators import admin_required
from utils.logger import bank_logger
from utils.helpers import get_client_ip, write_to_audit_table
import os
from datetime import datetime
import traceback


admin_bp = Blueprint('admin', __name__)

@admin_bp.route('/admin/dashboard')
@admin_required
def dashboard():
    cursor = mysql.connection.cursor()
    
    cursor.execute("SELECT COUNT(*) as total FROM users WHERE role = 'customer'")
    total_users = cursor.fetchone()['total']
    
    cursor.execute("SELECT COUNT(*) as total FROM accounts")
    total_accounts = cursor.fetchone()['total']
    
    cursor.execute("SELECT SUM(balance) as total FROM accounts")
    total_balance = cursor.fetchone()['total'] or 0
    
    cursor.execute("SELECT * FROM users ORDER BY created_at DESC LIMIT 10")
    recent_users = cursor.fetchall()
    
    cursor.close()
    
    bank_logger.log_audit(session['user_id'], get_client_ip(), 'ADMIN_DASHBOARD_VIEW', {})
    
    return render_template('admin/dashboard.html',
                          total_users=total_users,
                          total_accounts=total_accounts,
                          total_balance=total_balance,
                          recent_users=recent_users)

@admin_bp.route('/admin/users')
@admin_required
def users():
    cursor = mysql.connection.cursor()
    cursor.execute("SELECT * FROM users ORDER BY created_at DESC")
    users = cursor.fetchall()
    cursor.close()
    return render_template('admin/users.html', users=users)

@admin_bp.route('/admin/user/<int:user_id>/toggle')
@admin_required
def toggle_user(user_id):
    cursor = mysql.connection.cursor()
    cursor.execute("SELECT is_active FROM users WHERE user_id = %s", (user_id,))
    user = cursor.fetchone()
    
    if user:
        new_status = not user['is_active']
        cursor.execute("UPDATE users SET is_active = %s WHERE user_id = %s", (new_status, user_id))
        mysql.connection.commit()
        write_to_audit_table(session['user_id'], 'TOGGLE_USER', 'user', user_id, 
                            {'is_active': user['is_active']}, {'is_active': new_status})
        flash(f'User {"activated" if new_status else "deactivated"}', 'success')
    
    cursor.close()
    return redirect(url_for('admin.users'))

@admin_bp.route('/admin/logs')
@admin_required
def logs():
    log_type = request.args.get('type', 'application')
    lines = int(request.args.get('lines', 100))
    
    log_files = {
        'application': 'logs/application.log',
        'transactions': 'logs/transactions.log',
        'audit': 'logs/audit.log',
        'errors': 'logs/errors.log'
    }
    
    log_content = ""
    if log_type in log_files and os.path.exists(log_files[log_type]):
        with open(log_files[log_type], 'r') as f:
            log_content = ''.join(f.readlines()[-lines:])
    
    return render_template('admin/logs.html', log_content=log_content, log_type=log_type)

@admin_bp.route('/admin/json-logs')
@admin_required
def json_logs():
    """Get JSON logs for display"""
    log_type = request.args.get('type', 'application')
    lines = int(request.args.get('lines', 100))
    
    log_files = {
        'application': 'logs/application.json',
        'transactions': 'logs/transactions.json',
        'audit': 'logs/audit.json',
        'errors': 'logs/errors.json',
        'performance': 'logs/performance.json'
    }
    
    logs = []
    file_path = log_files.get(log_type)
    
    if file_path and os.path.exists(file_path):
        try:
            with open(file_path, 'r') as f:
                all_lines = f.readlines()
                for line in all_lines[-lines:]:
                    try:
                        logs.append(json.loads(line.strip()))
                    except:
                        continue
        except Exception as e:
            bank_logger.log_error(e, context="json_logs")
    
    return jsonify({'logs': logs})