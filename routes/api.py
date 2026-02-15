# routes/api.py
from flask import Blueprint, jsonify, request
from extensions import mysql
from utils.decorators import login_required

api_bp = Blueprint('api', __name__)

@api_bp.route('/api/verify_account/<account_number>')
@login_required
def verify_account(account_number):
    cursor = mysql.connection.cursor()
    cursor.execute("""
        SELECT a.account_number, u.first_name, u.last_name 
        FROM accounts a
        JOIN users u ON a.user_id = u.user_id
        WHERE a.account_number = %s
    """, (account_number,))
    account = cursor.fetchone()
    cursor.close()
    
    if account:
        return jsonify({
            'success': True,
            'account_number': account['account_number'],
            'holder_name': f"{account['first_name']} {account['last_name']}".strip()
        })
    return jsonify({'success': False, 'error': 'Account not found'}), 404