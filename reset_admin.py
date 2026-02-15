# reset_admin.py - Fixed version using MySQLdb
import MySQLdb
import bcrypt
from dotenv import load_dotenv
import os

load_dotenv()

# Database configuration from .env
db_config = {
    'host': os.getenv('MYSQL_HOST', 'localhost'),
    'user': os.getenv('MYSQL_USER', 'root'),
    'passwd': os.getenv('MYSQL_PASSWORD', ''),  # Note: passwd not password
    'db': os.getenv('MYSQL_DB', 'banking_system'),
    'charset': 'utf8mb4'
}

try:
    # Connect to database
    print("Connecting to database...")
    conn = MySQLdb.connect(**db_config)
    cursor = conn.cursor()
    
    # Generate proper bcrypt hash for 'admin123'
    password = 'admin123'
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    hashed_str = hashed.decode('utf-8')
    
    # Check if admin exists
    cursor.execute("SELECT user_id FROM users WHERE username = 'admin'")
    admin = cursor.fetchone()
    
    if admin:
        # Update existing admin
        cursor.execute("""
            UPDATE users 
            SET password_hash = %s 
            WHERE username = 'admin'
        """, (hashed_str,))
        print("✅ Admin password reset successfully!")
    else:
        # Create new admin
        cursor.execute("""
            INSERT INTO users (username, email, password_hash, first_name, last_name, role, is_active)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, ('admin', 'admin@securebank.com', hashed_str, 'System', 'Administrator', 'admin', True))
        print("✅ Admin user created successfully!")
    
    conn.commit()
    
    # Verify the update
    cursor.execute("SELECT username, role FROM users WHERE username = 'admin'")
    result = cursor.fetchone()
    if result:
        print(f"   Username: {result[0]}")
        print(f"   Role: {result[1]}")
        print(f"   Password: admin123")
    
    cursor.close()
    conn.close()
    print("\n🎉 Admin login fixed! You can now login with:")
    print("   Username: admin")
    print("   Password: admin123")
    
except Exception as e:
    print(f"❌ Error: {e}")
    
    # If connection fails, try without database name first
    if "Unknown database" in str(e):
        print("\n⚠️ Database doesn't exist. Creating it first...")
        try:
            # Connect without database
            db_config_no_db = db_config.copy()
            del db_config_no_db['db']
            conn = MySQLdb.connect(**db_config_no_db)
            cursor = conn.cursor()
            cursor.execute("CREATE DATABASE IF NOT EXISTS banking_system")
            print("✅ Database created. Please run the script again.")
            cursor.close()
            conn.close()
        except Exception as e2:
            print(f"❌ Could not create database: {e2}")