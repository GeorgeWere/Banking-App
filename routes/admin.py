# routes/admin.py
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from extensions import mysql
from utils.decorators import admin_required
from utils.logger import bank_logger
from utils.helpers import get_client_ip, write_to_audit_table
import os
import json
from datetime import datetime

admin_bp = Blueprint('admin', __name__)

@admin_bp.route('/admin/dashboard')
@admin_required
def dashboard():
    """Admin dashboard"""
    cursor = mysql.connection.cursor()
    
    try:
        # Get stats
        cursor.execute("SELECT COUNT(*) as total FROM users WHERE role = 'customer'")
        total_users = cursor.fetchone()['total']
        
        cursor.execute("SELECT COUNT(*) as total FROM users WHERE role = 'customer' AND is_active = TRUE")
        active_users = cursor.fetchone()['total']
        
        cursor.execute("SELECT COUNT(*) as total FROM accounts")
        total_accounts = cursor.fetchone()['total']
        
        cursor.execute("SELECT COUNT(*) as total FROM transactions WHERE DATE(initiated_at) = CURDATE()")
        today_transactions = cursor.fetchone()['total']
        
        cursor.execute("SELECT SUM(balance) as total FROM accounts")
        total_balance = cursor.fetchone()['total'] or 0
        
        # Get recent users
        cursor.execute("""
            SELECT * FROM users 
            WHERE role = 'customer' 
            ORDER BY created_at DESC 
            LIMIT 10
        """)
        recent_users = cursor.fetchall()
        
        # Get recent transactions
        cursor.execute("""
            SELECT t.*, u.username 
            FROM transactions t
            JOIN users u ON t.initiated_by = u.user_id
            ORDER BY t.initiated_at DESC 
            LIMIT 20
        """)
        recent_transactions = cursor.fetchall()
        
        # Log admin access
        bank_logger.log_audit(
            session['user_id'],
            get_client_ip(),
            'ADMIN_DASHBOARD_VIEW',
            {}
        )
        
        return render_template('admin/dashboard.html',
                              total_users=total_users,
                              active_users=active_users,
                              total_accounts=total_accounts,
                              today_transactions=today_transactions,
                              total_balance=total_balance,
                              recent_users=recent_users,
                              recent_transactions=recent_transactions)
    
    except Exception as e:
        bank_logger.log_error(e, context="admin_dashboard")
        flash('Error loading admin dashboard.', 'danger')
        return render_template('admin/dashboard.html',
                              total_users=0,
                              active_users=0,
                              total_accounts=0,
                              today_transactions=0,
                              total_balance=0,
                              recent_users=[],
                              recent_transactions=[])
    finally:
        cursor.close()

@admin_bp.route('/admin/users')
@admin_required
def users():
    """User management"""
    cursor = mysql.connection.cursor()
    
    try:
        cursor.execute("""
            SELECT u.*, 
                   COUNT(DISTINCT a.account_id) as account_count,
                   COALESCE(SUM(a.balance), 0) as total_balance
            FROM users u
            LEFT JOIN accounts a ON u.user_id = a.user_id
            GROUP BY u.user_id
            ORDER BY u.created_at DESC
        """)
        users = cursor.fetchall()
        
        return render_template('admin/users.html', users=users)
    
    except Exception as e:
        bank_logger.log_error(e, context="admin_users")
        flash('Error loading users.', 'danger')
        return render_template('admin/users.html', users=[])
    finally:
        cursor.close()

@admin_bp.route('/admin/user/<int:user_id>/toggle')
@admin_required
def toggle_user(user_id):
    """Activate/deactivate user"""
    admin_id = session['user_id']
    
    cursor = mysql.connection.cursor()
    
    try:
        if user_id == admin_id:
            flash('You cannot deactivate your own account.', 'danger')
            return redirect(url_for('admin.users'))
        
        cursor.execute("SELECT is_active, username FROM users WHERE user_id = %s", (user_id,))
        user = cursor.fetchone()
        
        if user:
            new_status = not user['is_active']
            cursor.execute("UPDATE users SET is_active = %s WHERE user_id = %s", (new_status, user_id))
            mysql.connection.commit()
            
            bank_logger.log_audit(
                admin_id,
                get_client_ip(),
                'TOGGLE_USER_STATUS',
                {'target_user': user_id, 'new_status': new_status}
            )
            
            flash(f'User {"activated" if new_status else "deactivated"} successfully.', 'success')
        else:
            flash('User not found.', 'danger')
    
    except Exception as e:
        mysql.connection.rollback()
        bank_logger.log_error(e, context="toggle_user")
        flash('Error updating user status.', 'danger')
    finally:
        cursor.close()
    
    return redirect(url_for('admin.users'))

@admin_bp.route('/admin/logs')
@admin_required
def logs():
    """View system logs"""
    log_type = request.args.get('type', 'application')
    lines = int(request.args.get('lines', 100))
    
    log_files = {
        'application': 'logs/application.json',
        'transactions': 'logs/transactions.json',
        'audit': 'logs/audit.json',
        'errors': 'logs/errors.json',
        'performance': 'logs/performance.json'
    }
    
    log_content = ""
    log_size = 0
    log_modified = None
    
    file_path = log_files.get(log_type)
    if file_path and os.path.exists(file_path):
        try:
            stats = os.stat(file_path)
            log_size = stats.st_size
            log_modified = datetime.fromtimestamp(stats.st_mtime).strftime('%Y-%m-%d %H:%M:%S')
            
            with open(file_path, 'r', encoding='utf-8') as f:
                all_lines = f.readlines()
                # Get last N lines
                start_line = max(0, len(all_lines) - lines)
                log_content = ''.join(all_lines[start_line:])
                
                # If empty, show message
                if not log_content:
                    log_content = "# No logs found\n"
        except Exception as e:
            bank_logger.log_error(e, context="admin_logs")
            log_content = f"# Error reading log file: {str(e)}"
    else:
        log_content = f"# Log file not found: {file_path}"
    
    # Log admin action
    bank_logger.log_audit(
        session['user_id'],
        get_client_ip(),
        'ADMIN_LOGS_VIEW',
        {'log_type': log_type, 'lines': lines}
    )
    
    return render_template('admin/logs.html',
                          log_content=log_content,
                          log_type=log_type,
                          log_files=log_files.keys(),
                          log_size=log_size,
                          log_modified=log_modified)

@admin_bp.route('/admin/json-logs')
@admin_required
def json_logs():
    """Get JSON logs for AJAX display"""
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
    
    return jsonify({'logs': logs, 'count': len(logs)})
