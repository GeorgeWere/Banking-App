# extensions.py
from flask_mysqldb import MySQL
from flask_bcrypt import Bcrypt

mysql = MySQL()
bcrypt = Bcrypt()

# Add this to ensure proper transaction handling
def init_mysql(app):
    mysql.init_app(app)
    # Ensure autocommit is False so transactions work properly
    app.config['MYSQL_AUTOCOMMIT'] = False