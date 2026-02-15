# forms/auth_forms.py
import re
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SelectField, DecimalField
from wtforms.validators import DataRequired, Email, Length, EqualTo, ValidationError
from extensions import mysql

class LoginForm(FlaskForm):
    """Login form"""
    username = StringField('Username or Email', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember_me = BooleanField('Remember Me')

class RegistrationForm(FlaskForm):
    """Registration form"""
    username = StringField('Username', validators=[
        DataRequired(),
        Length(min=3, max=50, message='Username must be between 3 and 50 characters')
    ])
    email = StringField('Email', validators=[
        DataRequired(),
        Email(message='Please enter a valid email address')
    ])
    password = PasswordField('Password', validators=[
        DataRequired(),
        Length(min=6, message='Password must be at least 6 characters')
    ])
    confirm_password = PasswordField('Confirm Password', validators=[
        DataRequired(),
        EqualTo('password', message='Passwords must match')
    ])
    first_name = StringField('First Name')
    last_name = StringField('Last Name')
    phone = StringField('Phone Number')
    account_type = SelectField('Account Type', choices=[
        ('savings', 'Savings Only'),
        ('checking', 'Checking Only'),
        ('both', 'Both Savings & Checking')
    ], default='both')
    initial_deposit = DecimalField('Initial Deposit', default=1000.00)
    
    def validate_username(self, username):
        """Check if username already exists"""
        cursor = mysql.connection.cursor()
        cursor.execute("SELECT user_id FROM users WHERE username = %s", (username.data,))
        user = cursor.fetchone()
        cursor.close()
        if user:
            raise ValidationError('Username already taken. Please choose another.')
    
    def validate_email(self, email):
        """Check if email already exists"""
        cursor = mysql.connection.cursor()
        cursor.execute("SELECT user_id FROM users WHERE email = %s", (email.data,))
        user = cursor.fetchone()
        cursor.close()
        if user:
            raise ValidationError('Email already registered. Please use another or login.')
    
    def validate_phone(self, phone):
        """Validate phone number format"""
        if phone.data:
            pattern = r'^[\d\s\+\-\(\)]{10,}$'
            if not re.match(pattern, phone.data):
                raise ValidationError('Please enter a valid phone number')