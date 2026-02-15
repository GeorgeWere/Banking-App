-- =============================================
-- SECUREBANK - COMPLETE DATABASE SCHEMA
-- Banking System with Comprehensive Audit Logging
-- Version: 3.0.0
-- =============================================

-- Drop database if exists (comment out if you don't want to drop)
DROP DATABASE IF EXISTS banking_system;

-- Create database
CREATE DATABASE IF NOT EXISTS banking_system
CHARACTER SET utf8mb4
COLLATE utf8mb4_unicode_ci;

USE banking_system;

-- =============================================
-- 1. USERS TABLE
-- =============================================
CREATE TABLE users (
    user_id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    first_name VARCHAR(50),
    last_name VARCHAR(50),
    phone VARCHAR(20),
    address TEXT,
    date_of_birth DATE,
    id_type ENUM('PASSPORT', 'DRIVERS_LICENSE', 'NATIONAL_ID') NULL,
    id_number VARCHAR(50) UNIQUE NULL,
    kyc_status ENUM('PENDING', 'VERIFIED', 'REJECTED') DEFAULT 'PENDING',
    role ENUM('customer', 'admin') DEFAULT 'customer',
    is_active BOOLEAN DEFAULT TRUE,
    two_factor_enabled BOOLEAN DEFAULT FALSE,
    email_notifications BOOLEAN DEFAULT TRUE,
    sms_alerts BOOLEAN DEFAULT FALSE,
    marketing_emails BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    last_login TIMESTAMP NULL,
    last_password_change TIMESTAMP NULL,
    password_reset_token VARCHAR(100) NULL,
    password_reset_expires TIMESTAMP NULL,
    login_attempts INT DEFAULT 0,
    locked_until TIMESTAMP NULL,
    
    INDEX idx_email (email),
    INDEX idx_username (username),
    INDEX idx_status (is_active),
    INDEX idx_role (role),
    INDEX idx_kyc (kyc_status),
    INDEX idx_created (created_at),
    FULLTEXT idx_search (username, email, first_name, last_name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- =============================================
-- 2. ACCOUNTS TABLE (Fixed account_number length to 30)
-- =============================================
CREATE TABLE accounts (
    account_id INT AUTO_INCREMENT PRIMARY KEY,
    account_number VARCHAR(30) UNIQUE NOT NULL,  -- Increased from 20 to 30
    user_id INT NOT NULL,
    account_type ENUM('savings', 'checking', 'fixed_deposit', 'loan', 'credit_card') DEFAULT 'savings',
    currency VARCHAR(3) DEFAULT 'USD',
    balance DECIMAL(15,2) DEFAULT 0.00,
    available_balance DECIMAL(15,2) DEFAULT 0.00,
    interest_rate DECIMAL(5,2) DEFAULT 0.00,
    overdraft_limit DECIMAL(15,2) DEFAULT 0.00,
    status ENUM('active', 'dormant', 'frozen', 'closed') DEFAULT 'active',
    opened_date DATE NOT NULL,
    closed_date DATE NULL,
    last_transaction_date TIMESTAMP NULL,
    monthly_fee DECIMAL(10,2) DEFAULT 0.00,
    minimum_balance DECIMAL(15,2) DEFAULT 0.00,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    INDEX idx_user (user_id),
    INDEX idx_account_number (account_number),
    INDEX idx_status (status),
    INDEX idx_type (account_type),
    INDEX idx_balance (balance)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- =============================================
-- 3. TRANSACTIONS TABLE
-- =============================================
CREATE TABLE transactions (
    transaction_id INT AUTO_INCREMENT PRIMARY KEY,
    transaction_uid VARCHAR(36) UNIQUE NOT NULL,
    from_account_id INT NULL,
    to_account_id INT NULL,
    transaction_type ENUM(
        'deposit', 'withdrawal', 'transfer', 'payment', 
        'fee', 'interest', 'refund', 'chargeback'
    ) NOT NULL,
    amount DECIMAL(15,2) NOT NULL,
    currency VARCHAR(3) DEFAULT 'USD',
    exchange_rate DECIMAL(10,6) DEFAULT 1.000000,
    description VARCHAR(255),
    reference_number VARCHAR(50) UNIQUE NULL,
    status ENUM('pending', 'completed', 'failed', 'reversed', 'cancelled') DEFAULT 'pending',
    failure_reason TEXT NULL,
    initiated_by INT NULL,
    approved_by INT NULL,
    initiated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP NULL,
    ip_address VARCHAR(45),
    user_agent TEXT,
    latitude DECIMAL(10,8) NULL,
    longitude DECIMAL(11,8) NULL,
    device_info VARCHAR(255) NULL,
    
    FOREIGN KEY (from_account_id) REFERENCES accounts(account_id) ON DELETE SET NULL,
    FOREIGN KEY (to_account_id) REFERENCES accounts(account_id) ON DELETE SET NULL,
    FOREIGN KEY (initiated_by) REFERENCES users(user_id) ON DELETE SET NULL,
    FOREIGN KEY (approved_by) REFERENCES users(user_id) ON DELETE SET NULL,
    
    INDEX idx_from_account (from_account_id),
    INDEX idx_to_account (to_account_id),
    INDEX idx_status (status),
    INDEX idx_initiated_at (initiated_at),
    INDEX idx_completed_at (completed_at),
    INDEX idx_type (transaction_type),
    INDEX idx_uid (transaction_uid),
    INDEX idx_reference (reference_number)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- =============================================
-- 4. AUDIT LOG TABLE
-- =============================================
CREATE TABLE audit_log (
    log_id BIGINT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NULL,
    action VARCHAR(100) NOT NULL,
    entity_type VARCHAR(50),
    entity_id INT,
    old_values JSON,
    new_values JSON,
    ip_address VARCHAR(45),
    user_agent TEXT,
    session_id VARCHAR(100),
    request_method VARCHAR(10),
    request_url VARCHAR(500),
    response_status INT,
    execution_time_ms INT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE SET NULL,
    
    INDEX idx_user (user_id),
    INDEX idx_action (action),
    INDEX idx_created_at (created_at),
    INDEX idx_entity (entity_type, entity_id),
    INDEX idx_ip (ip_address)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- =============================================
-- 5. BENEFICIARIES TABLE
-- =============================================
CREATE TABLE beneficiaries (
    beneficiary_id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    beneficiary_account_id INT NOT NULL,
    beneficiary_name VARCHAR(100),
    nickname VARCHAR(50),
    is_active BOOLEAN DEFAULT TRUE,
    transfer_limit DECIMAL(15,2) NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    FOREIGN KEY (beneficiary_account_id) REFERENCES accounts(account_id) ON DELETE CASCADE,
    
    UNIQUE KEY unique_beneficiary (user_id, beneficiary_account_id),
    INDEX idx_user (user_id),
    INDEX idx_active (is_active)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- =============================================
-- 6. LOANS TABLE
-- =============================================
CREATE TABLE loans (
    loan_id INT AUTO_INCREMENT PRIMARY KEY,
    loan_uid VARCHAR(36) UNIQUE NOT NULL,
    account_id INT NOT NULL,
    loan_type ENUM('personal', 'mortgage', 'auto', 'business', 'education') NOT NULL,
    principal_amount DECIMAL(15,2) NOT NULL,
    interest_rate DECIMAL(5,2) NOT NULL,
    tenure_months INT NOT NULL,
    disbursed_amount DECIMAL(15,2),
    outstanding_amount DECIMAL(15,2),
    emi_amount DECIMAL(15,2),
    disbursement_date DATE,
    first_payment_date DATE,
    last_payment_date DATE,
    next_payment_date DATE,
    loan_status ENUM('pending', 'approved', 'disbursed', 'active', 'closed', 'defaulted') DEFAULT 'pending',
    approved_by INT NULL,
    approved_date DATE NULL,
    purpose TEXT,
    collateral_info JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    FOREIGN KEY (account_id) REFERENCES accounts(account_id) ON DELETE CASCADE,
    FOREIGN KEY (approved_by) REFERENCES users(user_id) ON DELETE SET NULL,
    
    INDEX idx_account (account_id),
    INDEX idx_status (loan_status),
    INDEX idx_uid (loan_uid)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- =============================================
-- 7. CREDIT CARDS TABLE
-- =============================================
CREATE TABLE credit_cards (
    card_id INT AUTO_INCREMENT PRIMARY KEY,
    card_number VARCHAR(16) UNIQUE NOT NULL,
    card_holder_name VARCHAR(100) NOT NULL,
    account_id INT NOT NULL,
    card_type ENUM('visa', 'mastercard', 'amex', 'discover') NOT NULL,
    credit_limit DECIMAL(15,2) NOT NULL,
    available_credit DECIMAL(15,2) NOT NULL,
    outstanding_balance DECIMAL(15,2) DEFAULT 0.00,
    interest_rate DECIMAL(5,2) DEFAULT 0.00,
    annual_fee DECIMAL(10,2) DEFAULT 0.00,
    billing_cycle_day INT DEFAULT 1,
    expiry_date DATE NOT NULL,
    cvv VARCHAR(4),
    card_status ENUM('active', 'blocked', 'expired', 'cancelled') DEFAULT 'active',
    issued_date DATE NOT NULL,
    last_transaction_date TIMESTAMP NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    FOREIGN KEY (account_id) REFERENCES accounts(account_id) ON DELETE CASCADE,
    
    INDEX idx_account (account_id),
    INDEX idx_status (card_status),
    INDEX idx_expiry (expiry_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- =============================================
-- 8. NOTIFICATIONS TABLE
-- =============================================
CREATE TABLE notifications (
    notification_id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    type ENUM('email', 'sms', 'push', 'in_app') NOT NULL,
    title VARCHAR(255) NOT NULL,
    message TEXT NOT NULL,
    data JSON NULL,
    is_read BOOLEAN DEFAULT FALSE,
    sent_at TIMESTAMP NULL,
    read_at TIMESTAMP NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    
    INDEX idx_user (user_id),
    INDEX idx_read (is_read),
    INDEX idx_created (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- =============================================
-- 9. SESSIONS TABLE
-- =============================================
CREATE TABLE user_sessions (
    session_id VARCHAR(128) PRIMARY KEY,
    user_id INT NOT NULL,
    ip_address VARCHAR(45),
    user_agent TEXT,
    login_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    logout_time TIMESTAMP NULL,
    is_active BOOLEAN DEFAULT TRUE,
    
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    
    INDEX idx_user (user_id),
    INDEX idx_active (is_active)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- =============================================
-- 10. TRANSACTION_DISPUTES TABLE
-- =============================================
CREATE TABLE transaction_disputes (
    dispute_id INT AUTO_INCREMENT PRIMARY KEY,
    transaction_id INT NOT NULL,
    user_id INT NOT NULL,
    dispute_type ENUM('unauthorized', 'incorrect_amount', 'duplicate', 'not_received', 'other') NOT NULL,
    description TEXT NOT NULL,
    evidence JSON NULL,
    status ENUM('pending', 'investigating', 'resolved', 'rejected') DEFAULT 'pending',
    resolution_notes TEXT,
    resolved_by INT NULL,
    resolved_at TIMESTAMP NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    FOREIGN KEY (transaction_id) REFERENCES transactions(transaction_id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    FOREIGN KEY (resolved_by) REFERENCES users(user_id) ON DELETE SET NULL,
    
    INDEX idx_transaction (transaction_id),
    INDEX idx_user (user_id),
    INDEX idx_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- =============================================
-- INSERT SAMPLE DATA
-- =============================================

-- Insert admin user (password: admin123 - you'll need to hash this in the app)
INSERT INTO users (username, email, password_hash, first_name, last_name, role, is_active) VALUES
('admin', 'admin@securebank.com', 'admin123_hash_will_be_replaced_by_app', 'System', 'Administrator', 'admin', TRUE);

-- Insert sample customers
INSERT INTO users (username, email, password_hash, first_name, last_name, phone, address, role, is_active) VALUES
('john_doe', 'john.doe@email.com', 'password123_hash_will_be_replaced', 'John', 'Doe', '+1-555-0101', '123 Main St, New York, NY 10001', 'customer', TRUE),
('jane_smith', 'jane.smith@email.com', 'password123_hash_will_be_replaced', 'Jane', 'Smith', '+1-555-0102', '456 Oak Ave, Los Angeles, CA 90001', 'customer', TRUE),
('bob_wilson', 'bob.wilson@email.com', 'password123_hash_will_be_replaced', 'Bob', 'Wilson', '+1-555-0103', '789 Pine St, Chicago, IL 60601', 'customer', TRUE);

-- Insert accounts for customers (using shorter account numbers)
INSERT INTO accounts (account_number, user_id, account_type, balance, available_balance, interest_rate, opened_date) VALUES
('ACC10000001', 2, 'savings', 25000.00, 25000.00, 1.5, '2024-01-15'),
('ACC10000002', 2, 'checking', 5000.00, 5000.00, 0.0, '2024-01-15'),
('ACC10000003', 3, 'savings', 15000.00, 15000.00, 1.5, '2024-02-01'),
('ACC10000004', 3, 'checking', 3000.00, 3000.00, 0.0, '2024-02-01'),
('ACC10000005', 4, 'savings', 50000.00, 50000.00, 2.0, '2024-01-20');

-- Insert sample transactions
INSERT INTO transactions (transaction_uid, from_account_id, to_account_id, transaction_type, amount, description, status, initiated_by, initiated_at, completed_at, ip_address) VALUES
(UUID(), 1, 3, 'transfer', 500.00, 'Rent payment', 'completed', 2, DATE_SUB(NOW(), INTERVAL 5 DAY), DATE_SUB(NOW(), INTERVAL 5 DAY), '192.168.1.100'),
(UUID(), 3, 5, 'transfer', 200.00, 'Dinner split', 'completed', 3, DATE_SUB(NOW(), INTERVAL 3 DAY), DATE_SUB(NOW(), INTERVAL 3 DAY), '192.168.1.101'),
(UUID(), 5, 1, 'transfer', 1000.00, 'Loan repayment', 'completed', 4, DATE_SUB(NOW(), INTERVAL 2 DAY), DATE_SUB(NOW(), INTERVAL 2 DAY), '192.168.1.102'),
(UUID(), 2, 4, 'transfer', 150.00, 'Gift', 'completed', 2, DATE_SUB(NOW(), INTERVAL 1 DAY), DATE_SUB(NOW(), INTERVAL 1 DAY), '192.168.1.103'),
(UUID(), 4, 2, 'transfer', 75.00, 'Coffee shop', 'completed', 3, DATE_SUB(NOW(), INTERVAL 12 HOUR), DATE_SUB(NOW(), INTERVAL 12 HOUR), '192.168.1.104');

-- Insert beneficiaries
INSERT INTO beneficiaries (user_id, beneficiary_account_id, beneficiary_name, nickname) VALUES
(2, 3, 'Jane Smith', 'Jane'),
(2, 5, 'Bob Wilson', 'Bob'),
(3, 1, 'John Doe', 'John'),
(4, 2, 'Jane Smith', 'Jane');

-- Insert sample notifications
INSERT INTO notifications (user_id, type, title, message, is_read) VALUES
(2, 'email', 'Welcome to SecureBank', 'Thank you for joining SecureBank!', TRUE),
(2, 'sms', 'Large Transaction Alert', 'A transaction of $500 was made from your account', FALSE),
(3, 'in_app', 'Statement Available', 'Your monthly statement is now available', FALSE);

-- =============================================
-- CREATE INDEXES FOR PERFORMANCE
-- =============================================

CREATE INDEX idx_transactions_composite ON transactions(initiated_at, status, transaction_type);
CREATE INDEX idx_transactions_account_date ON transactions(from_account_id, initiated_at);
CREATE INDEX idx_transactions_recipient_date ON transactions(to_account_id, initiated_at);
CREATE INDEX idx_audit_log_composite ON audit_log(created_at, action, user_id);
CREATE INDEX idx_notifications_user_read ON notifications(user_id, is_read, created_at);
CREATE INDEX idx_accounts_user_status ON accounts(user_id, status, account_type);

-- =============================================
-- VERIFICATION QUERY
-- =============================================
SELECT 'Users' as table_name, COUNT(*) as record_count FROM users
UNION ALL
SELECT 'Accounts', COUNT(*) FROM accounts
UNION ALL
SELECT 'Transactions', COUNT(*) FROM transactions
UNION ALL
SELECT 'Beneficiaries', COUNT(*) FROM beneficiaries
UNION ALL
SELECT 'Notifications', COUNT(*) FROM notifications;

-- Show completion message
SELECT '✅ SecureBank database schema created successfully!' as Status;