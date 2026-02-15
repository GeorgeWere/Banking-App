# add_admin.py
import mysql.connector
import bcrypt
from dotenv import load_dotenv
import os

load_dotenv()

# Database configuration
db_config = {
    'host': os.getenv('MYSQL_HOST', 'localhost'),
    'user': os.getenv('MYSQL_USER', 'root'),
    'password': os.getenv('MYSQL_PASSWORD', ''),
    'database': os.getenv('MYSQL_DB', 'banking_system')
}

try:
    # Connect to database
    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor()
    
    # Generate bcrypt hash for 'admin123'
    password = 'admin123'
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    
    # Insert admin user
    query = """
        INSERT INTO users (
            username, email, password_hash, first_name, last_name, role, is_active, created_at
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, NOW())
    """
    values = ('admin', 'admin@securebank.com', hashed.decode('utf-8'), 
              'System', 'Administrator', 'admin', True)
    
    cursor.execute(query, values)
    conn.commit()
    
    print("✅ Admin user created successfully!")
    print("   Username: admin")
    print("   Password: admin123")
    print("   Email: admin@securebank.com")
    
    cursor.close()
    conn.close()
    
except mysql.connector.Error as err:
    print(f"❌ MySQL Error: {err}")
except Exception as e:
    print(f"❌ Error: {e}")
