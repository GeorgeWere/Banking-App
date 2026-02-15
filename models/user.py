# models/user.py
class User:
    """User model - handles all user-related database operations"""
    
    @staticmethod
    def get_by_id(cursor, user_id):
        """Get user by ID"""
        cursor.execute("SELECT * FROM users WHERE user_id = %s", (user_id,))
        return cursor.fetchone()
    
    @staticmethod
    def get_by_username_or_email(cursor, username):
        """Get user by username or email"""
        cursor.execute("SELECT * FROM users WHERE username = %s OR email = %s", (username, username))
        return cursor.fetchone()
    
    @staticmethod
    def create(cursor, user_data):
        """Create a new user"""
        query = """
            INSERT INTO users (username, email, password_hash, first_name, last_name, phone, address)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """
        cursor.execute(query, (
            user_data['username'],
            user_data['email'],
            user_data['password_hash'],
            user_data.get('first_name', ''),
            user_data.get('last_name', ''),
            user_data.get('phone', ''),
            user_data.get('address', '')
        ))
        return cursor.lastrowid
    
    @staticmethod
    def update_last_login(cursor, user_id):
        """Update user's last login timestamp"""
        cursor.execute("UPDATE users SET last_login = NOW() WHERE user_id = %s", (user_id,))
    
    @staticmethod
    def update_profile(cursor, user_id, profile_data):
        """Update user profile"""
        query = """
            UPDATE users 
            SET first_name = %s, last_name = %s, phone = %s, address = %s
            WHERE user_id = %s
        """
        cursor.execute(query, (
            profile_data.get('first_name', ''),
            profile_data.get('last_name', ''),
            profile_data.get('phone', ''),
            profile_data.get('address', ''),
            user_id
        ))
    
    @staticmethod
    def get_all_customers(cursor, limit=None):
        """Get all customer users"""
        query = "SELECT * FROM users WHERE role = 'customer' ORDER BY created_at DESC"
        if limit:
            query += f" LIMIT {limit}"
        cursor.execute(query)
        return cursor.fetchall()
    
    @staticmethod
    def toggle_active(cursor, user_id):
        """Toggle user active status"""
        cursor.execute("SELECT is_active FROM users WHERE user_id = %s", (user_id,))
        user = cursor.fetchone()
        if user:
            new_status = not user['is_active']
            cursor.execute("UPDATE users SET is_active = %s WHERE user_id = %s", (new_status, user_id))
            return new_status
        return None
    
    @staticmethod
    def update_password(cursor, user_id, password_hash):
        """Update user password"""
        cursor.execute("UPDATE users SET password_hash = %s, last_password_change = NOW() WHERE user_id = %s", 
                      (password_hash, user_id))
    
    @staticmethod
    def get_stats(cursor):
        """Get user statistics"""
        cursor.execute("SELECT COUNT(*) as total FROM users WHERE role = 'customer'")
        total = cursor.fetchone()['total']
        
        cursor.execute("SELECT COUNT(*) as total FROM users WHERE role = 'customer' AND is_active = TRUE")
        active = cursor.fetchone()['total']
        
        return {'total': total, 'active': active}