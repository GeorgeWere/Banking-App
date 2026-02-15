# routes/customer.py (COMPLETE VERSION)
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from extensions import mysql, bcrypt
from utils.decorators import login_required
from utils.logger import bank_logger
from utils.helpers import get_client_ip, format_currency, write_to_audit_table, generate_account_number
from models.user import User
from models.account import Account
from models.transaction import Transaction
import uuid
from datetime import datetime, timedelta

customer_bp = Blueprint('customer', __name__)

# =============================================
# DASHBOARD
# =============================================
@customer_bp.route('/dashboard')
@login_required
def dashboard():
    """Customer dashboard"""
    user_id = session['user_id']
    cursor = mysql.connection.cursor()
    
    try:
        # Get user details
        user = User.get_by_id(cursor, user_id)
        
        # Get accounts
        accounts = Account.get_user_accounts(cursor, user_id, active_only=True)
        
        # Get recent transactions
        transactions = []
        if accounts:
            account_ids = [acc['account_id'] for acc in accounts]
            placeholders = ','.join(['%s'] * len(account_ids))
            cursor.execute(f"""
                SELECT t.*, 
                       a_from.account_number as from_account_number,
                       a_to.account_number as to_account_number
                FROM transactions t
                LEFT JOIN accounts a_from ON t.from_account_id = a_from.account_id
                LEFT JOIN accounts a_to ON t.to_account_id = a_to.account_id
                WHERE t.from_account_id IN ({placeholders}) OR t.to_account_id IN ({placeholders})
                ORDER BY t.initiated_at DESC
                LIMIT 10
            """, account_ids * 2)
            transactions = cursor.fetchall()
            
            total_balance = sum(acc['balance'] for acc in accounts)
        else:
            total_balance = 0
        
        bank_logger.log_app('info', f"Dashboard accessed", user_id=user_id)
        
        return render_template('dashboard.html', 
                             user=user, 
                             accounts=accounts, 
                             transactions=transactions,
                             total_balance=total_balance)
    
    except Exception as e:
        bank_logger.log_error(e, context="dashboard", user_id=user_id)
        flash('Error loading dashboard. Please try again.', 'danger')
        return render_template('dashboard.html')
    finally:
        cursor.close()

# =============================================
# TRANSFER FUNDS - COMPLETE WORKING VERSION
# =============================================
@customer_bp.route('/transfer', methods=['GET', 'POST'])
@login_required
def transfer():
    """Transfer money between accounts"""
    user_id = session.get('user_id')
    if not user_id:
        flash('Please log in to continue.', 'warning')
        return redirect(url_for('auth.login'))
    
    cursor = mysql.connection.cursor()
    
    try:
        # Get user's active accounts
        cursor.execute("""
            SELECT * FROM accounts 
            WHERE user_id = %s AND status = 'active'
        """, (user_id,))
        accounts = cursor.fetchall()
        
        # Get beneficiaries
        cursor.execute("""
            SELECT b.*, a.account_number, a.user_id, u.first_name, u.last_name
            FROM beneficiaries b
            JOIN accounts a ON b.beneficiary_account_id = a.account_id
            JOIN users u ON a.user_id = u.user_id
            WHERE b.user_id = %s AND b.is_active = TRUE
            ORDER BY b.nickname
        """, (user_id,))
        beneficiaries = cursor.fetchall()
        
        if request.method == 'POST':
            from_account_id = request.form.get('from_account')
            to_account_number = request.form.get('to_account', '').strip().upper()
            amount = request.form.get('amount', '0').replace(',', '')
            description = request.form.get('description', '').strip()[:255]
            
            # Validate inputs
            if not from_account_id or not to_account_number:
                flash('Please select source account and enter destination account.', 'danger')
                return redirect(url_for('customer.transfer'))
            
            try:
                amount = float(amount)
                if amount <= 0:
                    flash('Please enter a valid amount greater than 0.', 'danger')
                    return redirect(url_for('customer.transfer'))
            except ValueError:
                flash('Please enter a valid number for amount.', 'danger')
                return redirect(url_for('customer.transfer'))
            
            # Get source account
            cursor.execute("""
                SELECT * FROM accounts 
                WHERE account_id = %s AND user_id = %s AND status = 'active'
            """, (from_account_id, user_id))
            from_account = cursor.fetchone()
            
            if not from_account:
                flash('Invalid source account.', 'danger')
                return redirect(url_for('customer.transfer'))
            
            # Check sufficient balance
            if from_account['balance'] < amount:
                flash(f'Insufficient funds. Available balance: ${from_account["balance"]:,.2f}', 'danger')
                return redirect(url_for('customer.transfer'))
            
            # Get destination account
            cursor.execute("""
                SELECT a.*, u.first_name, u.last_name 
                FROM accounts a
                JOIN users u ON a.user_id = u.user_id
                WHERE a.account_number = %s AND a.status = 'active'
            """, (to_account_number,))
            to_account = cursor.fetchone()
            
            if not to_account:
                flash('Destination account not found or inactive.', 'danger')
                return redirect(url_for('customer.transfer'))
            
            # Prevent self-transfer
            if from_account['account_id'] == to_account['account_id']:
                flash('Cannot transfer to the same account.', 'danger')
                return redirect(url_for('customer.transfer'))
            
            # Generate transaction UID
            transaction_uid = str(uuid.uuid4())
            
            try:
                # Start transaction
                cursor.execute("START TRANSACTION")
                
                # Create transaction record
                cursor.execute("""
                    INSERT INTO transactions (
                        transaction_uid, from_account_id, to_account_id,
                        transaction_type, amount, description, status,
                        initiated_by, ip_address, user_agent
                    ) VALUES (%s, %s, %s, 'transfer', %s, %s, 'completed', %s, %s, %s)
                """, (
                    transaction_uid, from_account['account_id'], to_account['account_id'],
                    amount, description, user_id, get_client_ip(),
                    request.headers.get('User-Agent', 'Unknown')[:255]
                ))
                
                # Update source account balance
                cursor.execute("""
                    UPDATE accounts 
                    SET balance = balance - %s, 
                        available_balance = available_balance - %s,
                        last_transaction_date = NOW()
                    WHERE account_id = %s
                """, (amount, amount, from_account['account_id']))
                
                # Update destination account balance
                cursor.execute("""
                    UPDATE accounts 
                    SET balance = balance + %s, 
                        available_balance = available_balance + %s,
                        last_transaction_date = NOW()
                    WHERE account_id = %s
                """, (amount, amount, to_account['account_id']))
                
                # Commit transaction
                mysql.connection.commit()
                
                # Log the transaction
                bank_logger.log_transaction(
                    transaction_uid,
                    from_account['account_number'],
                    to_account_number,
                    amount,
                    'completed',
                    user_id=user_id
                )
                
                # Audit log
                write_to_audit_table(
                    user_id,
                    'TRANSFER',
                    'transaction',
                    cursor.lastrowid,
                    None,
                    {
                        'from': from_account['account_number'],
                        'to': to_account_number,
                        'amount': amount
                    }
                )
                
                flash(f'✅ Successfully transferred ${amount:,.2f} to account {to_account_number}', 'success')
                return redirect(url_for('customer.transactions'))
                
            except Exception as e:
                mysql.connection.rollback()
                bank_logger.log_error(e, context="transfer_execution", user_id=user_id)
                flash('Transfer failed. Please try again.', 'danger')
                return redirect(url_for('customer.transfer'))
        
        return render_template('transfer.html', accounts=accounts, beneficiaries=beneficiaries)
    
    except Exception as e:
        bank_logger.log_error(e, context="transfer_page", user_id=user_id)
        flash('Error loading transfer page. Please try again.', 'danger')
        return redirect(url_for('customer.dashboard'))
    finally:
        cursor.close()

# =============================================
# DEPOSIT FUNDS (WITH DEBUGGING)
# =============================================
@customer_bp.route('/deposit', methods=['GET', 'POST'])
@login_required
def deposit():
    """Deposit money to account"""
    user_id = session.get('user_id')
    if not user_id:
        flash('Please log in to continue.', 'warning')
        return redirect(url_for('auth.login'))
    
    print(f"\n{'='*50}")
    print(f"DEPOSIT ROUTE ACCESSED - User ID: {user_id}")
    print(f"{'='*50}")
    
    cursor = mysql.connection.cursor()
    
    try:
        # Get user's accounts
        cursor.execute("""
            SELECT * FROM accounts 
            WHERE user_id = %s AND status = 'active'
        """, (user_id,))
        accounts = cursor.fetchall()
        print(f"Found {len(accounts)} accounts for user")
        
        if request.method == 'POST':
            print("\n--- Processing Deposit POST Request ---")
            account_id = request.form.get('account_id')
            amount = float(request.form.get('amount', 0))
            description = request.form.get('description', 'Deposit')
            
            print(f"Account ID: {account_id}")
            print(f"Amount: ${amount}")
            print(f"Description: {description}")
            
            if not account_id or amount <= 0:
                flash('Please select an account and enter a valid amount.', 'danger')
                return redirect(url_for('customer.deposit'))
            
            # Get account before update
            cursor.execute("""
                SELECT * FROM accounts 
                WHERE account_id = %s AND user_id = %s
            """, (account_id, user_id))
            account = cursor.fetchone()
            
            if not account:
                flash('Invalid account.', 'danger')
                return redirect(url_for('customer.deposit'))
            
            print(f"Account before deposit: ${account['balance']}")
            
            # Generate transaction UID
            transaction_uid = str(uuid.uuid4())
            print(f"Transaction UID: {transaction_uid}")
            
            try:
                # Start transaction
                cursor.execute("START TRANSACTION")
                print("Transaction started")
                
                # Create transaction record
                cursor.execute("""
                    INSERT INTO transactions (
                        transaction_uid, to_account_id,
                        transaction_type, amount, description, status,
                        initiated_by, ip_address, user_agent
                    ) VALUES (%s, %s, 'deposit', %s, %s, 'completed', %s, %s, %s)
                """, (
                    transaction_uid, account_id,
                    amount, description, user_id, get_client_ip(),
                    request.headers.get('User-Agent', 'Unknown')[:255]
                ))
                txn_id = cursor.lastrowid
                print(f"Transaction record created with ID: {txn_id}")
                
                # Update balance
                cursor.execute("""
                    UPDATE accounts 
                    SET balance = balance + %s, 
                        available_balance = available_balance + %s,
                        last_transaction_date = NOW()
                    WHERE account_id = %s
                """, (amount, amount, account_id))
                print(f"Account balance updated (+${amount})")
                
                # Commit the transaction
                mysql.connection.commit()
                print("Transaction COMMITTED successfully")
                
                # Verify the update
                cursor.execute("SELECT balance FROM accounts WHERE account_id = %s", (account_id,))
                new_balance = cursor.fetchone()['balance']
                print(f"New balance after deposit: ${new_balance}")
                
                # Log transaction
                bank_logger.log_transaction(
                    transaction_uid,
                    'DEPOSIT',
                    account['account_number'],
                    amount,
                    'completed',
                    user_id=user_id
                )
                
                flash(f'Successfully deposited ${amount:,.2f} to account {account["account_number"]}', 'success')
                print("Redirecting to transactions page")
                return redirect(url_for('customer.transactions'))
                
            except Exception as e:
                mysql.connection.rollback()
                print(f"ERROR: Transaction rolled back - {str(e)}")
                bank_logger.log_error(e, context="deposit", user_id=user_id)
                flash('Deposit failed. Please try again.', 'danger')
        
        return render_template('deposit.html', accounts=accounts)
    
    except Exception as e:
        print(f"ERROR in deposit route: {str(e)}")
        bank_logger.log_error(e, context="deposit_page", user_id=user_id)
        flash('Error loading deposit page. Please try again.', 'danger')
        return redirect(url_for('customer.dashboard'))
    finally:
        cursor.close()
# =============================================
# PAY BILLS (WITH DEBUGGING)
# =============================================
@customer_bp.route('/pay-bills', methods=['GET', 'POST'])
@login_required
def pay_bills():
    """Pay bills from account"""
    user_id = session.get('user_id')
    if not user_id:
        flash('Please log in to continue.', 'warning')
        return redirect(url_for('auth.login'))
    
    print(f"\n{'='*50}")
    print(f"PAY BILLS ROUTE ACCESSED - User ID: {user_id}")
    print(f"{'='*50}")
    
    cursor = mysql.connection.cursor()
    
    try:
        # Get user's accounts
        cursor.execute("""
            SELECT * FROM accounts 
            WHERE user_id = %s AND status = 'active'
        """, (user_id,))
        accounts = cursor.fetchall()
        print(f"Found {len(accounts)} accounts for user")
        
        # Billers list
        billers = [
            {'id': 'electric', 'name': 'Electric Company'},
            {'id': 'water', 'name': 'Water Utility'},
            {'id': 'internet', 'name': 'Internet Provider'},
            {'id': 'phone', 'name': 'Phone Company'},
            {'id': 'credit', 'name': 'Credit Card'},
            {'id': 'insurance', 'name': 'Insurance'},
            {'id': 'rent', 'name': 'Rent'},
            {'id': 'other', 'name': 'Other'}
        ]
        
        if request.method == 'POST':
            print("\n--- Processing Pay Bill POST Request ---")
            account_id = request.form.get('account_id')
            biller = request.form.get('biller')
            account_number = request.form.get('account_number', '').strip()
            amount = float(request.form.get('amount', 0))
            description = request.form.get('description', f'Bill payment - {biller}')
            
            print(f"Account ID: {account_id}")
            print(f"Biller: {biller}")
            print(f"Account Number: {account_number}")
            print(f"Amount: ${amount}")
            print(f"Description: {description}")
            
            if not all([account_id, biller, account_number, amount > 0]):
                flash('Please fill in all required fields.', 'danger')
                return redirect(url_for('customer.pay_bills'))
            
            # Get account before update
            cursor.execute("""
                SELECT * FROM accounts 
                WHERE account_id = %s AND user_id = %s
            """, (account_id, user_id))
            from_account = cursor.fetchone()
            
            if not from_account:
                flash('Invalid source account.', 'danger')
                return redirect(url_for('customer.pay_bills'))
            
            print(f"Account before payment: ${from_account['balance']}")
            
            # Check sufficient balance
            if from_account['balance'] < amount:
                flash(f'Insufficient funds. Available balance: ${from_account["balance"]:,.2f}', 'danger')
                return redirect(url_for('customer.pay_bills'))
            
            # Generate transaction UID
            transaction_uid = str(uuid.uuid4())
            print(f"Transaction UID: {transaction_uid}")
            
            try:
                # Start transaction
                cursor.execute("START TRANSACTION")
                print("Transaction started")
                
                # Create transaction record
                cursor.execute("""
                    INSERT INTO transactions (
                        transaction_uid, from_account_id,
                        transaction_type, amount, description, status,
                        initiated_by, ip_address, user_agent
                    ) VALUES (%s, %s, 'payment', %s, %s, 'completed', %s, %s, %s)
                """, (
                    transaction_uid, account_id,
                    amount, f"{description} - Acc: {account_number}", user_id, get_client_ip(),
                    request.headers.get('User-Agent', 'Unknown')[:255]
                ))
                txn_id = cursor.lastrowid
                print(f"Transaction record created with ID: {txn_id}")
                
                # Update balance
                cursor.execute("""
                    UPDATE accounts 
                    SET balance = balance - %s, 
                        available_balance = available_balance - %s,
                        last_transaction_date = NOW()
                    WHERE account_id = %s
                """, (amount, amount, account_id))
                print(f"Account balance updated (-${amount})")
                
                # Commit the transaction
                mysql.connection.commit()
                print("Transaction COMMITTED successfully")
                
                # Verify the update
                cursor.execute("SELECT balance FROM accounts WHERE account_id = %s", (account_id,))
                new_balance = cursor.fetchone()['balance']
                print(f"New balance after payment: ${new_balance}")
                
                # Log transaction
                bank_logger.log_transaction(
                    transaction_uid,
                    from_account['account_number'],
                    biller,
                    amount,
                    'completed',
                    user_id=user_id
                )
                
                flash(f'Successfully paid ${amount:,.2f} to {biller}', 'success')
                print("Redirecting to transactions page")
                return redirect(url_for('customer.transactions'))
                
            except Exception as e:
                mysql.connection.rollback()
                print(f"ERROR: Transaction rolled back - {str(e)}")
                bank_logger.log_error(e, context="pay_bills", user_id=user_id)
                flash('Payment failed. Please try again.', 'danger')
        
        return render_template('pay_bills.html', accounts=accounts, billers=billers)
    
    except Exception as e:
        print(f"ERROR in pay_bills route: {str(e)}")
        bank_logger.log_error(e, context="pay_bills_page", user_id=user_id)
        flash('Error loading bill payment page. Please try again.', 'danger')
        return redirect(url_for('customer.dashboard'))
    finally:
        cursor.close()

# =============================================
# TRANSACTION HISTORY
# =============================================
@customer_bp.route('/transactions')
@login_required
def transactions():
    """View transaction history"""
    user_id = session['user_id']
    page = int(request.args.get('page', 1))
    per_page = 20
    offset = (page - 1) * per_page
    
    cursor = mysql.connection.cursor()
    
    try:
        # Get user's accounts
        accounts = Account.get_user_accounts(cursor, user_id, active_only=False)
        account_ids = [acc['account_id'] for acc in accounts]
        
        # Get filter parameters
        account_filter = request.args.get('account', 'all')
        type_filter = request.args.get('type', 'all')
        status_filter = request.args.get('status', 'all')
        date_range = request.args.get('date', '30')
        
        # Build query conditions
        conditions = []
        params = []
        
        if account_ids:
            if account_filter != 'all':
                conditions.append("(t.from_account_id = %s OR t.to_account_id = %s)")
                params.extend([account_filter, account_filter])
            else:
                placeholders = ','.join(['%s'] * len(account_ids))
                conditions.append(f"(t.from_account_id IN ({placeholders}) OR t.to_account_id IN ({placeholders}))")
                params.extend(account_ids * 2)
        
        if type_filter != 'all':
            conditions.append("t.transaction_type = %s")
            params.append(type_filter)
        
        if status_filter != 'all':
            conditions.append("t.status = %s")
            params.append(status_filter)
        
        if date_range != 'all':
            days = int(date_range)
            conditions.append("t.initiated_at >= DATE_SUB(NOW(), INTERVAL %s DAY)")
            params.append(days)
        
        where_clause = " AND ".join(conditions) if conditions else "1=1"
        
        # Get total count
        count_query = f"""
            SELECT COUNT(*) as total 
            FROM transactions t
            WHERE {where_clause}
        """
        cursor.execute(count_query, params)
        total = cursor.fetchone()['total']
        total_pages = (total + per_page - 1) // per_page
        
        # Get transactions
        query = f"""
            SELECT t.*, 
                   a_from.account_number as from_account_number,
                   a_to.account_number as to_account_number
            FROM transactions t
            LEFT JOIN accounts a_from ON t.from_account_id = a_from.account_id
            LEFT JOIN accounts a_to ON t.to_account_id = a_to.account_id
            WHERE {where_clause}
            ORDER BY t.initiated_at DESC
            LIMIT %s OFFSET %s
        """
        cursor.execute(query, params + [per_page, offset])
        transactions = cursor.fetchall()
        
        # Calculate totals
        total_credits = sum(t['amount'] for t in transactions 
                           if t['to_account_id'] in account_ids)
        total_debits = sum(t['amount'] for t in transactions 
                          if t['from_account_id'] in account_ids)
        pending_count = sum(1 for t in transactions if t['status'] == 'pending')
        
        return render_template('transactions.html',
                             transactions=transactions,
                             accounts=accounts,
                             total_credits=total_credits,
                             total_debits=total_debits,
                             pending_count=pending_count,
                             page=page,
                             total_pages=total_pages,
                             per_page=per_page)
    
    except Exception as e:
        bank_logger.log_error(e, context="transactions_page", user_id=user_id)
        flash('Error loading transactions. Please try again.', 'danger')
        return render_template('transactions.html', transactions=[])
    finally:
        cursor.close()

# =============================================
# PROFILE MANAGEMENT
# =============================================
@customer_bp.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    """View and edit user profile"""
    user_id = session['user_id']
    cursor = mysql.connection.cursor()
    
    try:
        if request.method == 'POST':
            first_name = request.form.get('first_name', '').strip()
            last_name = request.form.get('last_name', '').strip()
            phone = request.form.get('phone', '').strip()
            address = request.form.get('address', '').strip()
            
            # Get old values for audit
            cursor.execute("SELECT * FROM users WHERE user_id = %s", (user_id,))
            old_user = cursor.fetchone()
            
            # Update profile
            User.update_profile(cursor, user_id, {
                'first_name': first_name,
                'last_name': last_name,
                'phone': phone,
                'address': address
            })
            mysql.connection.commit()
            
            # Update session
            session['user_fullname'] = f"{first_name} {last_name}".strip()
            
            # Audit log
            write_to_audit_table(
                user_id,
                'PROFILE_UPDATE',
                'user',
                user_id,
                old_user,
                {'first_name': first_name, 'last_name': last_name, 'phone': phone, 'address': address}
            )
            
            flash('Profile updated successfully!', 'success')
        
        # Get user data
        user = User.get_by_id(cursor, user_id)
        
        # Get accounts
        accounts = Account.get_user_accounts(cursor, user_id, active_only=False)
        
        return render_template('profile.html', user=user, accounts=accounts)
    
    except Exception as e:
        bank_logger.log_error(e, context="profile_page", user_id=user_id)
        flash('Error loading profile. Please try again.', 'danger')
        return redirect(url_for('customer.dashboard'))
    finally:
        cursor.close()
# =============================================
# STATEMENTS LIST - COMPLETE WORKING VERSION
# =============================================
@customer_bp.route('/statements')
@login_required
def statements():
    """View account statements"""
    user_id = session.get('user_id')
    if not user_id:
        flash('Please log in to continue.', 'warning')
        return redirect(url_for('auth.login'))
    
    cursor = mysql.connection.cursor()
    
    try:
        # Get user's accounts
        cursor.execute("""
            SELECT * FROM accounts 
            WHERE user_id = %s
            ORDER BY account_type
        """, (user_id,))
        accounts = cursor.fetchall()
        
        return render_template('statements.html', accounts=accounts)
    
    except Exception as e:
        bank_logger.log_error(e, context="statements_page", user_id=user_id)
        flash('Error loading statements page. Please try again.', 'danger')
        return redirect(url_for('customer.dashboard'))
    finally:
        cursor.close()


# =============================================
# GENERATE STATEMENT - COMPLETE WORKING VERSION
# =============================================
@customer_bp.route('/generate-statement/<int:account_id>')
@login_required
def generate_statement(account_id):
    """Generate statement for an account"""
    user_id = session.get('user_id')
    if not user_id:
        flash('Please log in to continue.', 'warning')
        return redirect(url_for('auth.login'))
    
    months = int(request.args.get('months', 3))
    
    cursor = mysql.connection.cursor()
    
    try:
        # Verify account belongs to user
        cursor.execute("""
            SELECT a.*, u.first_name, u.last_name, u.email
            FROM accounts a
            JOIN users u ON a.user_id = u.user_id
            WHERE a.account_id = %s AND a.user_id = %s
        """, (account_id, user_id))
        account = cursor.fetchone()
        
        if not account:
            flash('Account not found.', 'danger')
            return redirect(url_for('customer.statements'))
        
        # Calculate date range
        end_date = datetime.now()
        start_date = end_date - timedelta(days=30 * months)
        
        # Get transactions
        cursor.execute("""
            SELECT t.*, 
                   a_from.account_number as from_account_number,
                   a_to.account_number as to_account_number
            FROM transactions t
            LEFT JOIN accounts a_from ON t.from_account_id = a_from.account_id
            LEFT JOIN accounts a_to ON t.to_account_id = a_to.account_id
            WHERE (t.from_account_id = %s OR t.to_account_id = %s)
              AND t.initiated_at BETWEEN %s AND %s
              AND t.status = 'completed'
            ORDER BY t.initiated_at ASC
        """, (account_id, account_id, start_date, end_date))
        
        transactions = cursor.fetchall()
        
        # Calculate running balance
        running_balance = account['balance']
        for txn in reversed(transactions):
            if txn['to_account_id'] == account_id:
                running_balance -= txn['amount']
            else:
                running_balance += txn['amount']
            txn['running_balance'] = running_balance
        
        # Calculate totals
        total_credits = sum(t['amount'] for t in transactions if t['to_account_id'] == account_id)
        total_debits = sum(t['amount'] for t in transactions if t['from_account_id'] == account_id)
        
        return render_template('statement.html',
                             account=account,
                             transactions=transactions,
                             start_date=start_date.strftime('%B %d, %Y'),
                             end_date=end_date.strftime('%B %d, %Y'),
                             opening_balance=running_balance,
                             closing_balance=account['balance'],
                             total_credits=total_credits,
                             total_debits=total_debits,
                             months=months)
    
    except Exception as e:
        bank_logger.log_error(e, context="generate_statement", user_id=user_id)
        flash('Error generating statement. Please try again.', 'danger')
        return redirect(url_for('customer.statements'))
    finally:
        cursor.close()
# =============================================
# BENEFICIARIES
# =============================================
@customer_bp.route('/add_beneficiary', methods=['POST'])
@login_required
def add_beneficiary():
    """Add a beneficiary"""
    user_id = session.get('user_id')
    if not user_id:
        flash('Please log in to continue.', 'warning')
        return redirect(url_for('auth.login'))
    
    account_number = request.form.get('account_number', '').strip().upper()
    nickname = request.form.get('nickname', '').strip()[:50]
    
    if not account_number:
        flash('Please enter an account number.', 'danger')
        return redirect(url_for('customer.transfer'))
    
    cursor = mysql.connection.cursor()
    
    try:
        # Check if account exists
        cursor.execute("""
            SELECT a.*, u.first_name, u.last_name 
            FROM accounts a
            JOIN users u ON a.user_id = u.user_id
            WHERE a.account_number = %s AND a.status = 'active'
        """, (account_number,))
        account = cursor.fetchone()
        
        if not account:
            flash('Account not found or inactive.', 'danger')
            return redirect(url_for('customer.transfer'))
        
        # Check if trying to add own account
        cursor.execute("SELECT account_id FROM accounts WHERE user_id = %s", (user_id,))
        own_accounts = [acc['account_id'] for acc in cursor.fetchall()]
        if account['account_id'] in own_accounts:
            flash('You cannot add your own account as beneficiary.', 'danger')
            return redirect(url_for('customer.transfer'))
        
        # Check if already beneficiary
        cursor.execute("""
            SELECT * FROM beneficiaries 
            WHERE user_id = %s AND beneficiary_account_id = %s
        """, (user_id, account['account_id']))
        existing = cursor.fetchone()
        
        if existing:
            if not existing['is_active']:
                cursor.execute("""
                    UPDATE beneficiaries 
                    SET is_active = TRUE, nickname = %s 
                    WHERE beneficiary_id = %s
                """, (nickname or f"{account['first_name']} {account['last_name']}", existing['beneficiary_id']))
                mysql.connection.commit()
                flash('Beneficiary reactivated!', 'success')
            else:
                flash('Beneficiary already exists.', 'warning')
        else:
            beneficiary_name = f"{account['first_name']} {account['last_name']}"
            cursor.execute("""
                INSERT INTO beneficiaries (user_id, beneficiary_account_id, beneficiary_name, nickname)
                VALUES (%s, %s, %s, %s)
            """, (user_id, account['account_id'], beneficiary_name, nickname or beneficiary_name))
            mysql.connection.commit()
            flash('Beneficiary added successfully!', 'success')
        
    except Exception as e:
        mysql.connection.rollback()
        bank_logger.log_error(e, context="add_beneficiary", user_id=user_id)
        flash('Error adding beneficiary. Please try again.', 'danger')
    finally:
        cursor.close()
    
    return redirect(url_for('customer.transfer'))

@customer_bp.route('/remove_beneficiary/<int:beneficiary_id>', methods=['POST'])
@login_required
def remove_beneficiary(beneficiary_id):
    """Remove a beneficiary"""
    user_id = session['user_id']
    cursor = mysql.connection.cursor()
    
    try:
        cursor.execute("""
            UPDATE beneficiaries 
            SET is_active = FALSE 
            WHERE beneficiary_id = %s AND user_id = %s
        """, (beneficiary_id, user_id))
        mysql.connection.commit()
        
        if cursor.rowcount > 0:
            bank_logger.log_audit(
                user_id,
                get_client_ip(),
                'REMOVE_BENEFICIARY',
                {'beneficiary_id': beneficiary_id}
            )
            flash('Beneficiary removed successfully.', 'success')
        else:
            flash('Beneficiary not found.', 'danger')
    
    except Exception as e:
        mysql.connection.rollback()
        bank_logger.log_error(e, context="remove_beneficiary", user_id=user_id)
        flash('Error removing beneficiary.', 'danger')
    finally:
        cursor.close()
    
    return redirect(url_for('customer.transfer'))
@customer_bp.route('/check-session')
def check_session():
    """Debug endpoint to check session status"""
    session_data = {
        'has_session': bool(session),
        'user_id': session.get('user_id'),
        'username': session.get('username'),
        'role': session.get('role'),
        'session_keys': list(session.keys()),
        'session_permanent': session.permanent if hasattr(session, 'permanent') else None
    }
    return jsonify(session_data)