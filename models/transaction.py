# models/transaction.py
import uuid
from datetime import datetime, timedelta

class Transaction:
    """Transaction model - handles all transaction-related database operations"""
    
    @staticmethod
    def create(cursor, transaction_data):
        """Create a new transaction"""
        if 'transaction_uid' not in transaction_data:
            transaction_data['transaction_uid'] = str(uuid.uuid4())
        
        query = """
            INSERT INTO transactions (
                transaction_uid, from_account_id, to_account_id, transaction_type,
                amount, description, status, initiated_by, ip_address, user_agent
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        cursor.execute(query, (
            transaction_data['transaction_uid'],
            transaction_data.get('from_account_id'),
            transaction_data.get('to_account_id'),
            transaction_data['transaction_type'],
            transaction_data['amount'],
            transaction_data.get('description', ''),
            transaction_data.get('status', 'pending'),
            transaction_data.get('initiated_by'),
            transaction_data.get('ip_address'),
            transaction_data.get('user_agent')
        ))
        return cursor.lastrowid, transaction_data['transaction_uid']
    
    @staticmethod
    def complete(cursor, transaction_uid):
        """Mark transaction as completed"""
        cursor.execute("""
            UPDATE transactions 
            SET status = 'completed', completed_at = NOW() 
            WHERE transaction_uid = %s
        """, (transaction_uid,))
    
    @staticmethod
    def fail(cursor, transaction_uid, reason=None):
        """Mark transaction as failed"""
        cursor.execute("""
            UPDATE transactions 
            SET status = 'failed', failure_reason = %s, completed_at = NOW() 
            WHERE transaction_uid = %s
        """, (reason, transaction_uid))
    
    @staticmethod
    def get_user_transactions(cursor, user_id, limit=50, offset=0):
        """Get transactions for a user"""
        cursor.execute("""
            SELECT t.*, 
                   a_from.account_number as from_account_number,
                   a_to.account_number as to_account_number
            FROM transactions t
            LEFT JOIN accounts a_from ON t.from_account_id = a_from.account_id
            LEFT JOIN accounts a_to ON t.to_account_id = a_to.account_id
            WHERE t.from_account_id IN (SELECT account_id FROM accounts WHERE user_id = %s)
               OR t.to_account_id IN (SELECT account_id FROM accounts WHERE user_id = %s)
            ORDER BY t.initiated_at DESC
            LIMIT %s OFFSET %s
        """, (user_id, user_id, limit, offset))
        return cursor.fetchall()
    
    @staticmethod
    def get_account_transactions(cursor, account_id, start_date=None, end_date=None):
        """Get transactions for a specific account"""
        query = """
            SELECT t.*, 
                   a_from.account_number as from_account_number,
                   a_to.account_number as to_account_number
            FROM transactions t
            LEFT JOIN accounts a_from ON t.from_account_id = a_from.account_id
            LEFT JOIN accounts a_to ON t.to_account_id = a_to.account_id
            WHERE (t.from_account_id = %s OR t.to_account_id = %s)
        """
        params = [account_id, account_id]
        
        if start_date:
            query += " AND t.initiated_at >= %s"
            params.append(start_date)
        if end_date:
            query += " AND t.initiated_at <= %s"
            params.append(end_date)
        
        query += " ORDER BY t.initiated_at ASC"
        cursor.execute(query, params)
        return cursor.fetchall()
    
    @staticmethod
    def get_recent_transactions(cursor, limit=20):
        """Get recent transactions for admin dashboard"""
        cursor.execute("""
            SELECT t.*, u.username 
            FROM transactions t
            JOIN users u ON t.initiated_by = u.user_id
            ORDER BY t.initiated_at DESC 
            LIMIT %s
        """, (limit,))
        return cursor.fetchall()
    
    @staticmethod
    def get_daily_stats(cursor, days=7):
        """Get daily transaction statistics"""
        cursor.execute("""
            SELECT DATE(initiated_at) as date, 
                   COUNT(*) as count, 
                   COALESCE(SUM(amount), 0) as volume
            FROM transactions
            WHERE initiated_at >= DATE_SUB(NOW(), INTERVAL %s DAY)
            GROUP BY DATE(initiated_at)
            ORDER BY date
        """, (days,))
        return cursor.fetchall()
    
    @staticmethod
    def get_today_count(cursor):
        """Get today's transaction count"""
        cursor.execute("SELECT COUNT(*) as total FROM transactions WHERE DATE(initiated_at) = CURDATE()")
        result = cursor.fetchone()
        return result['total']