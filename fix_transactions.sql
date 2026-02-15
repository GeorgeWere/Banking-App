-- fix_transactions.sql
USE banking_system;

-- 1. Check current balances
SELECT 'Current Account Balances' as '';
SELECT account_id, account_number, user_id, balance 
FROM accounts 
ORDER BY user_id, account_type;

-- 2. Check recent transactions
SELECT 'Recent Transactions' as '';
SELECT transaction_id, transaction_uid, from_account_id, to_account_id, 
       transaction_type, amount, status, initiated_at
FROM transactions 
ORDER BY initiated_at DESC 
LIMIT 10;

-- 3. Fix any potential issues with the accounts table
ALTER TABLE accounts MODIFY balance DECIMAL(15,2) DEFAULT 0.00;
ALTER TABLE accounts MODIFY available_balance DECIMAL(15,2) DEFAULT 0.00;

-- 4. Fix any potential issues with the transactions table
ALTER TABLE transactions MODIFY amount DECIMAL(15,2) NOT NULL;
ALTER TABLE transactions MODIFY status ENUM('pending','completed','failed','reversed','cancelled') DEFAULT 'pending';

-- 5. Ensure foreign keys are correct
SELECT 'Foreign Key Constraints' as '';
SELECT 
    CONSTRAINT_NAME, 
    TABLE_NAME,
    REFERENCED_TABLE_NAME
FROM INFORMATION_SCHEMA.REFERENTIAL_CONSTRAINTS
WHERE CONSTRAINT_SCHEMA = 'banking_system';