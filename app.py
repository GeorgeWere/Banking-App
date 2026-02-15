# app.py - Main entry point (very small!)
from flask import Flask, render_template
from config import Config
from extensions import mysql, bcrypt
from utils.logger import bank_logger

# Import blueprints
from routes.auth import auth_bp
from routes.customer import customer_bp
from routes.admin import admin_bp
from routes.api import api_bp

def create_app():
    """Application factory"""
    app = Flask(__name__)
    app.config.from_object(Config)
    
    # Initialize extensions
    mysql.init_app(app)
    bcrypt.init_app(app)
    
    # Register blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(customer_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(api_bp)
    

    # Home route
    @app.route('/')
    def index():
        return render_template('index.html')
    
    # Error handlers
    @app.errorhandler(404)
    def not_found(e):
        return render_template('404.html'), 404
    
    @app.errorhandler(500)
    def internal_error(e):
        bank_logger.log_error(e)
        return render_template('500.html'), 500
    
    return app

if __name__ == '__main__':
    app = create_app()
    print("\n" + "="*50)
    print("🚀 Starting SecureBank Application")
    print("="*50 + "\n")
    app.run(debug=True, host='0.0.0.0', port=5000)