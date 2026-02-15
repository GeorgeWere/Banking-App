# models/account.py
class Account:
    """Account model - handles all account-related database operations"""
    
    @staticmethod
    def get_by_id(cursor, account_id, user_id=None):
        """Get account by ID (optionally filtered by user_id)"""
        if user_id:
            cursor.execute("SELECT * FROM accounts WHERE account_id = %s AND user_id = %s", (account_id, user_id))
        else:
            cursor.execute("SELECT * FROM accounts WHERE account_id = %s", (account_id,))
        return cursor.fetchone()
    
    @staticmethod
    def get_by_number(cursor, account_number):
        """Get account by account number"""
        cursor.execute("""
            SELECT a.*, u.first_name, u.last_name, u.email 
            FROM accounts a
            JOIN users u ON a.user_id = u.user_id
            WHERE a.account_number = %s
        """, (account_number,))
        return cursor.fetchone()
    
    @staticmethod
    def get_user_accounts(cursor, user_id, active_only=True):
        """Get all accounts for a user"""
        if active_only:
            cursor.execute("SELECT * FROM accounts WHERE user_id = %s AND status = 'active' ORDER BY account_type", (user_id,))
        else:
            cursor.execute("SELECT * FROM accounts WHERE user_id = %s ORDER BY account_type", (user_id,))
        return cursor.fetchall()
    
    @staticmethod
    def create(cursor, account_data):
        """Create a new account"""
        query = """
            INSERT INTO accounts (account_number, user_id, account_type, balance, available_balance, opened_date)
            VALUES (%s, %s, %s, %s, %s, %s)
        """
        cursor.execute(query, (
            account_data['account_number'],
            account_data['user_id'],
            account_data['account_type'],
            account_data['balance'],
            account_data['available_balance'],
            account_data.get('opened_date', 'CURDATE()')
        ))
        return cursor.lastrowid
    
    @staticmethod
    def update_balance(cursor, account_id, amount, is_deposit=True):
        """Update account balance"""
        if is_deposit:
            cursor.execute("""
                UPDATE accounts 
                SET balance = balance + %s, available_balance = available_balance + %s, last_transaction_date = NOW()
                WHERE account_id = %s
            """, (amount, amount, account_id))
        else:
            cursor.execute("""
                UPDATE accounts 
                SET balance = balance - %s, available_balance = available_balance - %s, last_transaction_date = NOW()
                WHERE account_id = %s
            """, (amount, amount, account_id))
    
    @staticmethod
    def transfer(cursor, from_account_id, to_account_id, amount):
        """Transfer money between accounts"""
        # Deduct from source
        cursor.execute("""
            UPDATE accounts 
            SET balance = balance - %s, available_balance = available_balance - %s, last_transaction_date = NOW()
            WHERE account_id = %s
        """, (amount, amount, from_account_id))
        
        # Add to destination
        cursor.execute("""
            UPDATE accounts 
            SET balance = balance + %s, available_balance = available_balance + %s, last_transaction_date = NOW()
            WHERE account_id = %s
        """, (amount, amount, to_account_id))
    
    @staticmethod
    def check_sufficient_balance(cursor, account_id, amount):
        """Check if account has sufficient balance"""
        cursor.execute("SELECT balance FROM accounts WHERE account_id = %s", (account_id,))
        account = cursor.fetchone()
        return account and account['balance'] >= amount
    
    @staticmethod
    def get_total_balance(cursor):
        """Get total balance of all accounts"""
        cursor.execute("SELECT SUM(balance) as total FROM accounts")
        result = cursor.fetchone()
        return result['total'] or 0
    
    @staticmethod
    def get_stats(cursor):
        """Get account statistics"""
        cursor.execute("SELECT COUNT(*) as total FROM accounts")
        total = cursor.fetchone()['total']
        
        cursor.execute("""
            SELECT account_type, COUNT(*) as count, SUM(balance) as total_balance
            FROM accounts
            GROUP BY account_type
        """)
        by_type = cursor.fetchall()
        
        return {'total': total, 'by_type': by_type}