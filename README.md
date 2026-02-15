# SecureBank - Banking System for Log Collection Testing

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://python.org)
[![Flask](https://img.shields.io/badge/Flask-2.3.3-green.svg)](https://flask.palletsprojects.com)
[![MySQL](https://img.shields.io/badge/MySQL-8.0-orange.svg)](https://mysql.com)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](https://makeapullrequest.com)

A full-featured banking application built with Flask and MySQL, designed specifically for testing log collection, monitoring, and auditing tools. This system generates comprehensive logs across multiple sources including application events, financial transactions, security audits, errors, and performance metrics.

## Features

### Banking Functionality
- **User Management**: Registration, login, profile management
- **Multiple Account Types**: Savings, checking accounts
- **Fund Transfers**: Transfer money between accounts
- **Transaction History**: Complete view of all transactions
- **Deposits**: Add funds to your accounts
- **Bill Payments**: Pay bills to various merchants
- **Beneficiary Management**: Save frequently used accounts
- **Account Statements**: Generate PDF-friendly statements
- **Admin Dashboard**: User management and system monitoring

### Comprehensive Logging System
- **Application Logs**: All user actions and system events
- **Transaction Logs**: Every financial transaction with details
- **Audit Logs**: Security events, failed logins, admin actions
- **Error Logs**: Exceptions, database errors, system failures
- **Performance Logs**: Response times for all endpoints
- **JSON Format**: SIEM-compatible logs for easy ingestion

###  Modern UI/UX
- Responsive Bootstrap 5 design
- Clean, professional interface
- Mobile-friendly layout
- Real-time form validation
- Interactive elements with AJAX
- Print-optimized statements

## Quick Start

### Prerequisites
- Python 3.8+
- MySQL 5.7+ (MySQL 8.0 recommended)
- Windows 10/11 (for automated setup)

### One-Click Installation (Windows)

Run PowerShell as Administrator and execute:

```powershell
# Download and run the automated installer
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser -Force
iex ((New-Object System.Net.WebClient).DownloadString('https://raw.githubusercontent.com/GeorgeWere/Banking-App/main/install.ps1'))
```
## Manual Installation
1. Clone the repository

```sh
git clone https://github.com/GeorgeWere/Banking-App.git
cd Banking-App
```
## Project Structure

```text

securebank/
├── app.py                 # Main application entry point
├── config.py              # Configuration settings
├── requirements.txt       # Python dependencies
├── .env.example          # Environment variables template
│
├── database/
│   └── schema.sql         # Complete database schema
│
├── logs/                  # Log directory (auto-created)
│   ├── application.json   # Application events (JSON)
│   ├── transactions.json  # Financial transactions (JSON)
│   ├── audit.json        # Security audit events (JSON)
│   ├── errors.json       # Error logs (JSON)
│   └── performance.json   # Performance metrics (JSON)
│
├── models/
│   ├── user.py            # User model
│   ├── account.py         # Account model
│   └── transaction.py     # Transaction model
│
├── routes/
│   ├── auth.py            # Authentication routes
│   ├── customer.py        # Customer routes
│   ├── admin.py           # Admin routes
│   └── api.py             # API routes
│
├── utils/
│   ├── logger.py          # JSON logging configuration
│   ├── helpers.py         # Helper functions
│   └── decorators.py      # Route decorators
│
├── static/
│   └── css/
│       └── style.css      # Custom styles
│
└── templates/             # HTML templates
    ├── base.html
    ├── index.html
    ├── login.html
    ├── register.html
    ├── dashboard.html
    ├── transfer.html
    ├── deposit.html
    ├── pay_bills.html
    ├── transactions.html
    ├── profile.html
    ├── statements.html
    ├── statement.html
    ├── 404.html
    ├── 500.html
    └── admin/
        ├── dashboard.html
        ├── users.html
        └── logs.html
```
