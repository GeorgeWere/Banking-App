# forms/transaction_forms.py
from flask_wtf import FlaskForm
from wtforms import SelectField, StringField, DecimalField, TextAreaField
from wtforms.validators import DataRequired, NumberRange, Optional, ValidationError
from extensions import mysql

class TransferForm(FlaskForm):
    """Transfer funds form"""
    from_account = SelectField('From Account', coerce=int, validators=[DataRequired()])
    to_account = StringField('To Account Number', validators=[DataRequired()])
    amount = DecimalField('Amount', validators=[
        DataRequired(),
        NumberRange(min=0.01, message='Amount must be greater than 0')
    ])
    description = StringField('Description', validators=[Optional()])
    
    def validate_amount(self, amount):
        """Validate sufficient funds"""
        if self.from_account.data:
            cursor = mysql.connection.cursor()
            cursor.execute("SELECT balance FROM accounts WHERE account_id = %s", (self.from_account.data,))
            account = cursor.fetchone()
            cursor.close()
            if account and account['balance'] < amount.data:
                raise ValidationError('Insufficient funds in selected account')

class DepositForm(FlaskForm):
    """Deposit form"""
    account_id = SelectField('Select Account', coerce=int, validators=[DataRequired()])
    amount = DecimalField('Amount', validators=[
        DataRequired(),
        NumberRange(min=0.01, message='Amount must be greater than 0')
    ])
    description = StringField('Description', validators=[Optional()])

class PayBillForm(FlaskForm):
    """Pay bill form"""
    from_account = SelectField('From Account', coerce=int, validators=[DataRequired()])
    biller = SelectField('Biller', choices=[
        ('electric', 'Electric Company'),
        ('water', 'Water Utility'),
        ('internet', 'Internet Provider'),
        ('phone', 'Phone Company'),
        ('credit', 'Credit Card'),
        ('insurance', 'Insurance'),
        ('rent', 'Rent'),
        ('other', 'Other')
    ], validators=[DataRequired()])
    account_number = StringField('Account Number', validators=[DataRequired()])
    amount = DecimalField('Amount', validators=[
        DataRequired(),
        NumberRange(min=0.01, message='Amount must be greater than 0')
    ])
    description = StringField('Description', validators=[Optional()])
    
    def validate_amount(self, amount):
        """Validate sufficient funds"""
        if self.from_account.data:
            cursor = mysql.connection.cursor()
            cursor.execute("SELECT balance FROM accounts WHERE account_id = %s", (self.from_account.data,))
            account = cursor.fetchone()
            cursor.close()
            if account and account['balance'] < amount.data:
                raise ValidationError('Insufficient funds in selected account')

class AddBeneficiaryForm(FlaskForm):
    """Add beneficiary form"""
    account_number = StringField('Account Number', validators=[DataRequired()])
    nickname = StringField('Nickname', validators=[Optional()])
    
    def validate_account_number(self, account_number):
        """Validate account exists"""
        cursor = mysql.connection.cursor()
        cursor.execute("SELECT account_id FROM accounts WHERE account_number = %s", (account_number.data,))
        account = cursor.fetchone()
        cursor.close()
        if not account:
            raise ValidationError('Account not found')