<#
.SYNOPSIS
    SecureBank - Complete Setup Script for Windows
.DESCRIPTION
    This script automates the setup of SecureBank banking application
    It installs dependencies, sets up database using existing schema.sql,
    and configures the environment
.NOTES
    Version: 2.0.0
    Author: SecureBank Team
#>

# =============================================
# CONFIGURATION - EDIT THESE VALUES
# =============================================

$config = @{
    ProjectPath = "C:\SecureBank"
    MySQLRootPassword = ""  # Leave empty to enter during setup
    MySQLUser = "root"
    MySQLHost = "localhost"
    MySQLPort = 3306
    MySQLDB = "banking_system"
    AdminUser = "admin"
    AdminPassword = "admin123"
}

# =============================================
# FUNCTIONS
# =============================================

function Write-ColorOutput {
    param(
        [string]$Message,
        [string]$Type = "INFO"
    )
    
    $timestamp = Get-Date -Format "HH:mm:ss"
    
    switch ($Type) {
        "SUCCESS" { $color = "Green"; $prefix = "[OK]" }
        "ERROR"   { $color = "Red"; $prefix = "[ERROR]" }
        "WARNING" { $color = "Yellow"; $prefix = "[WARNING]" }
        "PROGRESS" { $color = "Cyan"; $prefix = "[...]" }
        "INPUT"   { $color = "Magenta"; $prefix = "[INPUT]" }
        default   { $color = "White"; $prefix = "[INFO]" }
    }
    
    Write-Host "$timestamp $prefix " -NoNewline
    Write-Host $Message -ForegroundColor $color
}

function Test-Command {
    param($Command)
    
    try {
        if (Get-Command $Command -ErrorAction SilentlyContinue) {
            return $true
        }
        return $false
    } catch {
        return $false
    }
}

function Generate-RandomPassword {
    $length = 16
    $characters = 'abcdefghkmnpqrstuvwxyzABCDEFGHKLMNPQRSTUVWXYZ23456789!@#$%'
    $password = -join ((1..$length) | ForEach-Object { Get-Random -Maximum $characters.Length | ForEach-Object { $characters[$_] } })
    return $password
}

# =============================================
# MAIN SCRIPT
# =============================================

Clear-Host
Write-Host @"

================================================
      SECUREBANK - Complete Setup Wizard
================================================

This script will set up your entire environment
using your existing database\schema.sql file

================================================

"@ -ForegroundColor Cyan

# =============================================
# STEP 0: CHECK ADMIN RIGHTS
# =============================================

Write-ColorOutput "Checking administrator privileges..." -Type "PROGRESS"

$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole] "Administrator")
if (-not $isAdmin) {
    Write-ColorOutput "This script needs administrator privileges to install software." -Type "WARNING"
    Write-ColorOutput "Please right-click PowerShell and select 'Run as Administrator'" -Type "ERROR"
    pause
    exit 1
}

Write-ColorOutput "Administrator privileges confirmed" -Type "SUCCESS"

# =============================================
# STEP 1: SET PROJECT PATH
# =============================================

Write-ColorOutput "Setting up project directory..." -Type "PROGRESS"

# Check if project directory exists
if (-not (Test-Path $config.ProjectPath)) {
    Write-ColorOutput "Project directory not found: $($config.ProjectPath)" -Type "ERROR"
    Write-ColorOutput "Please create the directory and place your files there first" -Type "WARNING"
    pause
    exit 1
}

Set-Location $config.ProjectPath
Write-ColorOutput "Working directory: $(Get-Location)" -Type "SUCCESS"

# =============================================
# STEP 2: CHECK FOR SCHEMA FILE
# =============================================

Write-ColorOutput "Looking for database schema..." -Type "PROGRESS"

$schemaPath = Join-Path $config.ProjectPath "database\schema.sql"

if (Test-Path $schemaPath) {
    $schemaSize = (Get-Item $schemaPath).Length
    Write-ColorOutput "Found schema.sql at: $schemaPath" -Type "SUCCESS"
    Write-ColorOutput "Schema file size: $([math]::Round($schemaSize/1KB, 2)) KB" -Type "INFO"
} else {
    Write-ColorOutput "Schema file NOT found at: $schemaPath" -Type "ERROR"
    Write-ColorOutput "Please ensure your schema.sql is in the database folder" -Type "WARNING"
    
    # List contents of database folder if it exists
    $dbPath = Join-Path $config.ProjectPath "database"
    if (Test-Path $dbPath) {
        Write-ColorOutput "Contents of database folder:" -Type "INFO"
        Get-ChildItem $dbPath | ForEach-Object {
            Write-ColorOutput "  - $($_.Name)" -Type "INFO"
        }
    }
    
    pause
    exit 1
}

# =============================================
# STEP 3: CHECK PYTHON
# =============================================

Write-ColorOutput "Checking Python installation..." -Type "PROGRESS"

if (-not (Test-Command "python")) {
    Write-ColorOutput "Python not found! Installing Python 3.11..." -Type "WARNING"
    
    try {
        $pythonUrl = "https://www.python.org/ftp/python/3.11.5/python-3.11.5-amd64.exe"
        $pythonInstaller = "$env:TEMP\python-installer.exe"
        
        Write-ColorOutput "Downloading Python installer..." -Type "PROGRESS"
        Invoke-WebRequest -Uri $pythonUrl -OutFile $pythonInstaller
        
        Write-ColorOutput "Installing Python (this may take a few minutes)..." -Type "PROGRESS"
        Start-Process -FilePath $pythonInstaller -ArgumentList "/quiet", "InstallAllUsers=1", "PrependPath=1" -Wait
        
        # Refresh PATH
        $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
        
        if (Test-Command "python") {
            Write-ColorOutput "Python installed successfully" -Type "SUCCESS"
        } else {
            throw "Python installation verification failed"
        }
    } catch {
        Write-ColorOutput "Failed to install Python: $_" -Type "ERROR"
        Write-ColorOutput "Please install Python 3.11 manually from python.org" -Type "WARNING"
        pause
        exit 1
    }
} else {
    $pythonVersion = python --version
    Write-ColorOutput "Python found: $pythonVersion" -Type "SUCCESS"
}

# =============================================
# STEP 4: CHECK MYSQL
# =============================================

Write-ColorOutput "Checking MySQL installation..." -Type "PROGRESS"

$mysqlFound = $false
$mysqlPath = ""

# Check if mysql command works
if (Test-Command "mysql") {
    $mysqlFound = $true
    $mysqlPath = "mysql"
    Write-ColorOutput "MySQL found in PATH" -Type "SUCCESS"
} else {
    # Look in common locations
    $mysqlLocations = @(
        "C:\Program Files\MySQL\MySQL Server 8.0\bin\mysql.exe",
        "C:\Program Files\MySQL\MySQL Server 5.7\bin\mysql.exe",
        "C:\xampp\mysql\bin\mysql.exe",
        "C:\wamp64\bin\mysql\mysql5.7.31\bin\mysql.exe",
        "C:\MySQL\bin\mysql.exe"
    )
    
    foreach ($location in $mysqlLocations) {
        if (Test-Path $location) {
            $mysqlFound = $true
            $mysqlPath = $location
            Write-ColorOutput "MySQL found at: $location" -Type "SUCCESS"
            break
        }
    }
}

if (-not $mysqlFound) {
    Write-ColorOutput "MySQL not found!" -Type "ERROR"
    Write-ColorOutput "Please install MySQL Community Server from: https://dev.mysql.com/downloads/installer/" -Type "WARNING"
    Write-ColorOutput "After installation, run this script again." -Type "WARNING"
    pause
    exit 1
}

# =============================================
# STEP 5: CREATE VIRTUAL ENVIRONMENT
# =============================================

Write-ColorOutput "Setting up Python virtual environment..." -Type "PROGRESS"

if (Test-Path "venv") {
    Write-ColorOutput "Virtual environment already exists" -Type "SUCCESS"
} else {
    try {
        python -m venv venv
        Write-ColorOutput "Virtual environment created" -Type "SUCCESS"
    } catch {
        Write-ColorOutput "Failed to create virtual environment: $_" -Type "ERROR"
        pause
        exit 1
    }
}

# Activate virtual environment
try {
    $activateScript = Join-Path $config.ProjectPath "venv\Scripts\Activate.ps1"
    if (Test-Path $activateScript) {
        & $activateScript
        Write-ColorOutput "Virtual environment activated" -Type "SUCCESS"
    } else {
        throw "Activation script not found"
    }
} catch {
    Write-ColorOutput "Failed to activate virtual environment: $_" -Type "ERROR"
}

# =============================================
# STEP 6: INSTALL PYTHON PACKAGES
# =============================================

Write-ColorOutput "Installing Python packages..." -Type "PROGRESS"

# Upgrade pip
try {
    python -m pip install --upgrade pip
    Write-ColorOutput "Pip upgraded" -Type "SUCCESS"
} catch {
    Write-ColorOutput "Failed to upgrade pip: $_" -Type "WARNING"
}

# Install packages one by one
$packages = @(
    "flask==2.3.3",
    "flask-mysqldb==1.0.1",
    "flask-bcrypt==1.0.1",
    "mysqlclient==2.2.0",
    "python-dotenv==1.0.0"
)

foreach ($package in $packages) {
    Write-ColorOutput "Installing $package..." -Type "PROGRESS"
    try {
        pip install $package
        Write-ColorOutput "Installed: $package" -Type "SUCCESS"
    } catch {
        Write-ColorOutput "Failed to install $package : $_" -Type "ERROR"
        Write-ColorOutput "Trying alternative installation method..." -Type "WARNING"
        try {
            python -m pip install $package
            Write-ColorOutput "Installed: $package (alternative method)" -Type "SUCCESS"
        } catch {
            Write-ColorOutput "Failed to install $package with both methods" -Type "ERROR"
        }
    }
}

Write-ColorOutput "Python package installation complete" -Type "SUCCESS"

# =============================================
# STEP 7: CONFIGURE MYSQL
# =============================================

Write-ColorOutput "Configuring MySQL database..." -Type "PROGRESS"

# Get MySQL root password
if ([string]::IsNullOrEmpty($config.MySQLRootPassword)) {
    Write-ColorOutput "Please enter your MySQL root password" -Type "INPUT"
    $securePassword = Read-Host -AsSecureString "MySQL root password"
    $BSTR = [System.Runtime.InteropServices.Marshal]::SecureStringToBSTR($securePassword)
    $config.MySQLRootPassword = [System.Runtime.InteropServices.Marshal]::PtrToStringAuto($BSTR)
}

# Test MySQL connection
Write-ColorOutput "Testing MySQL connection..." -Type "PROGRESS"

$testQuery = "SELECT 1"
if ($mysqlPath -eq "mysql") {
    $mysqlCommand = "mysql -u $($config.MySQLUser) -p$($config.MySQLRootPassword) -e `"$testQuery`" 2>`$null"
} else {
    $mysqlCommand = "`"$mysqlPath`" -u $($config.MySQLUser) -p$($config.MySQLRootPassword) -e `"$testQuery`" 2>`$null"
}

$result = Invoke-Expression $mysqlCommand

if ($LASTEXITCODE -ne 0) {
    Write-ColorOutput "Cannot connect to MySQL. Please check your password." -Type "ERROR"
    Write-ColorOutput "If you forgot your password, you may need to reset MySQL." -Type "WARNING"
    
    $retry = Read-Host "Would you like to try again? (y/n)"
    if ($retry -eq 'y') {
        $securePassword = Read-Host -AsSecureString "Enter MySQL root password"
        $BSTR = [System.Runtime.InteropServices.Marshal]::SecureStringToBSTR($securePassword)
        $config.MySQLRootPassword = [System.Runtime.InteropServices.Marshal]::PtrToStringAuto($BSTR)
        
        # Test again with new password
        if ($mysqlPath -eq "mysql") {
            $mysqlCommand = "mysql -u $($config.MySQLUser) -p$($config.MySQLRootPassword) -e `"$testQuery`" 2>`$null"
        } else {
            $mysqlCommand = "`"$mysqlPath`" -u $($config.MySQLUser) -p$($config.MySQLRootPassword) -e `"$testQuery`" 2>`$null"
        }
        $result = Invoke-Expression $mysqlCommand
        if ($LASTEXITCODE -ne 0) {
            Write-ColorOutput "Still cannot connect. Exiting." -Type "ERROR"
            pause
            exit 1
        }
    } else {
        pause
        exit 1
    }
}

Write-ColorOutput "MySQL connection successful" -Type "SUCCESS"

# Create database if not exists
Write-ColorOutput "Creating database $($config.MySQLDB) if not exists..." -Type "PROGRESS"

if ($mysqlPath -eq "mysql") {
    $createDbCommand = "mysql -u $($config.MySQLUser) -p$($config.MySQLRootPassword) -e `"CREATE DATABASE IF NOT EXISTS $($config.MySQLDB);`" 2>`$null"
} else {
    $createDbCommand = "`"$mysqlPath`" -u $($config.MySQLUser) -p$($config.MySQLRootPassword) -e `"CREATE DATABASE IF NOT EXISTS $($config.MySQLDB);`" 2>`$null"
}

Invoke-Expression $createDbCommand

if ($LASTEXITCODE -eq 0) {
    Write-ColorOutput "Database created/verified: $($config.MySQLDB)" -Type "SUCCESS"
} else {
    Write-ColorOutput "Failed to create database" -Type "ERROR"
}

# =============================================
# STEP 8: IMPORT SCHEMA FROM database\schema.sql
# =============================================

Write-ColorOutput "Importing database schema from database\schema.sql..." -Type "PROGRESS"

$schemaPath = Join-Path $config.ProjectPath "database\schema.sql"

if (Test-Path $schemaPath) {
    try {
        Write-ColorOutput "Found schema file: $schemaPath" -Type "SUCCESS"
        
        # Count lines in schema file
        $lineCount = (Get-Content $schemaPath | Measure-Object -Line).Lines
        Write-ColorOutput "Schema contains $lineCount lines of SQL" -Type "INFO"
        
        # Method 1: Using mysql command line with input redirection
        Write-ColorOutput "Importing schema using mysql command..." -Type "PROGRESS"
        
        if ($mysqlPath -eq "mysql") {
            $importCommand = "mysql -u $($config.MySQLUser) -p$($config.MySQLRootPassword) $($config.MySQLDB) < `"$schemaPath`""
        } else {
            $importCommand = "`"$mysqlPath`" -u $($config.MySQLUser) -p$($config.MySQLRootPassword) $($config.MySQLDB) < `"$schemaPath`""
        }
        
        # Execute the import
        cmd /c $importCommand 2>$null
        
        if ($LASTEXITCODE -eq 0) {
            Write-ColorOutput "Schema imported successfully using mysql command" -Type "SUCCESS"
        } else {
            Write-ColorOutput "First import method failed, trying alternative..." -Type "WARNING"
            
            # Method 2: Read file and execute line by line (for large schemas)
            Write-ColorOutput "Reading schema file and executing..." -Type "PROGRESS"
            
            # Create a temporary file with USE statement
            $tempFile = "$env:TEMP\import_schema.sql"
            "USE $($config.MySQLDB);" | Out-File -FilePath $tempFile -Encoding UTF8
            Get-Content $schemaPath | Out-File -FilePath $tempFile -Encoding UTF8 -Append
            
            if ($mysqlPath -eq "mysql") {
                $importCommand = "mysql -u $($config.MySQLUser) -p$($config.MySQLRootPassword) < `"$tempFile`""
            } else {
                $importCommand = "`"$mysqlPath`" -u $($config.MySQLUser) -p$($config.MySQLRootPassword) < `"$tempFile`""
            }
            
            cmd /c $importCommand 2>$null
            
            if ($LASTEXITCODE -eq 0) {
                Write-ColorOutput "Schema imported successfully using alternative method" -Type "SUCCESS"
            } else {
                Write-ColorOutput "Both import methods failed" -Type "ERROR"
                Write-ColorOutput "You may need to import the schema manually using:" -Type "WARNING"
                Write-ColorOutput "  $mysqlPath -u $($config.MySQLUser) -p $($config.MySQLDB) < `"$schemaPath`"" -Type "INFO"
            }
            
            Remove-Item $tempFile -Force -ErrorAction SilentlyContinue
        }
        
        # Verify import by checking tables
        Write-ColorOutput "Verifying schema import..." -Type "PROGRESS"
        
        if ($mysqlPath -eq "mysql") {
            $verifyCommand = "mysql -u $($config.MySQLUser) -p$($config.MySQLRootPassword) -e `"USE $($config.MySQLDB); SHOW TABLES;`" 2>`$null"
        } else {
            $verifyCommand = "`"$mysqlPath`" -u $($config.MySQLUser) -p$($config.MySQLRootPassword) -e `"USE $($config.MySQLDB); SHOW TABLES;`" 2>`$null"
        }
        
        $tables = Invoke-Expression $verifyCommand
        
        if ($LASTEXITCODE -eq 0) {
            $tableCount = ($tables | Measure-Object -Line).Lines - 1  # Subtract header
            Write-ColorOutput "Schema verification successful! Found $tableCount tables." -Type "SUCCESS"
        }
        
    } catch {
        Write-ColorOutput "Failed to import schema: $_" -Type "ERROR"
        Write-ColorOutput "You may need to import the schema manually" -Type "WARNING"
    }
} else {
    Write-ColorOutput "Schema file not found at: $schemaPath" -Type "ERROR"
    Write-ColorOutput "Please ensure your schema.sql is in the database folder" -Type "WARNING"
}

# =============================================
# STEP 9: CREATE .ENV FILE
# =============================================

Write-ColorOutput "Creating .env configuration file..." -Type "PROGRESS"

$secretKey = [System.Guid]::NewGuid().ToString().Replace("-","")
$sessionSecret = [System.Guid]::NewGuid().ToString()

$envContent = @"
# SecureBank Environment Configuration
# Generated on $(Get-Date)

# Flask Settings
FLASK_APP=app.py
FLASK_ENV=development
FLASK_DEBUG=1

# Database Configuration
MYSQL_HOST=$($config.MySQLHost)
MYSQL_USER=$($config.MySQLUser)
MYSQL_PASSWORD=$($config.MySQLRootPassword)
MYSQL_DB=$($config.MySQLDB)
MYSQL_PORT=$($config.MySQLPort)

# Security
SECRET_KEY=$secretKey
SESSION_SECRET=$sessionSecret

# Application
APP_NAME=SecureBank
APP_URL=http://localhost:5000
ADMIN_USER=$($config.AdminUser)
ADMIN_PASS=$($config.AdminPassword)

# Logging
LOG_LEVEL=INFO
LOG_DIR=logs
"@

try {
    $envContent | Out-File -FilePath (Join-Path $config.ProjectPath ".env") -Encoding UTF8
    Write-ColorOutput ".env file created successfully" -Type "SUCCESS"
    
    # Show masked password in .env
    $maskedPassword = $config.MySQLRootPassword.Substring(0, [Math]::Min(3, $config.MySQLRootPassword.Length)) + "..."
    Write-ColorOutput "Database password in .env: $maskedPassword" -Type "INFO"
} catch {
    Write-ColorOutput "Failed to create .env file: $_" -Type "ERROR"
}

# =============================================
# STEP 10: CREATE LOGS DIRECTORY
# =============================================

Write-ColorOutput "Creating logs directory..." -Type "PROGRESS"

$logsPath = Join-Path $config.ProjectPath "logs"
if (-not (Test-Path $logsPath)) {
    try {
        New-Item -ItemType Directory -Path $logsPath -Force | Out-Null
        Write-ColorOutput "Logs directory created: $logsPath" -Type "SUCCESS"
    } catch {
        Write-ColorOutput "Failed to create logs directory: $_" -Type "ERROR"
    }
} else {
    Write-ColorOutput "Logs directory already exists" -Type "SUCCESS"
}

# =============================================
# STEP 11: CREATE START SCRIPT
# =============================================

Write-ColorOutput "Creating start script..." -Type "PROGRESS"

$startScript = @"
@echo off
echo ============================================
echo    SECUREBANK - Banking System
echo ============================================
echo.

cd /d "%~dp0"

echo [1/3] Activating virtual environment...
call venv\Scripts\activate.bat

echo [2/3] Starting Flask application...
echo.
echo Access the app at: http://localhost:5000
echo Logs are being written to: logs\ folder
echo.

python app.py

if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Application failed to start!
    echo Please check that:
    echo   - MySQL is running
    echo   - Database credentials in .env are correct
    echo   - All Python packages are installed
    pause
)
"@

try {
    $startScript | Out-File -FilePath (Join-Path $config.ProjectPath "start.bat") -Encoding ASCII
    Write-ColorOutput "Start script created: start.bat" -Type "SUCCESS"
} catch {
    Write-ColorOutput "Failed to create start script: $_" -Type "ERROR"
}

# =============================================
# STEP 12: CREATE README FILE WITH CREDENTIALS
# =============================================

Write-ColorOutput "Creating README with credentials..." -Type "PROGRESS"

$readmeContent = @"
=============================================
SECUREBANK - INSTALLATION SUMMARY
=============================================
Generated on: $(Get-Date)

PROJECT INFORMATION
=============================================
Project Path: $($config.ProjectPath)
Schema File: database\schema.sql
Logs Directory: logs\

DATABASE CREDENTIALS (SAVE THESE!)
=============================================
Host: $($config.MySQLHost)
Port: $($config.MySQLPort)
Database: $($config.MySQLDB)
Username: $($config.MySQLUser)
Password: $($config.MySQLRootPassword)

APPLICATION LOGIN
=============================================
Admin Username: $($config.AdminUser)
Admin Password: $($config.AdminPassword)
Test User: john_doe / password123

QUICK START
=============================================
1. Double-click 'start.bat' in the project folder
2. Open browser to: http://localhost:5000
3. Login with admin credentials above

LOG FILES LOCATION
=============================================
$($config.ProjectPath)\logs\
   - application.log : General application events
   - transactions.log : Financial transactions  
   - audit.log       : Security events
   - errors.log      : Error logs
   - performance.log : Performance metrics

USEFUL COMMANDS
=============================================
Start application:
  cd $($config.ProjectPath) && .\venv\Scripts\activate && python app.py

Access MySQL:
  $mysqlPath -u $($config.MySQLUser) -p

View application logs:
  type $($config.ProjectPath)\logs\application.log

View transaction logs:
  type $($config.ProjectPath)\logs\transactions.log

IMPORTANT NOTES
=============================================
- Save this file or note down the database password above
- You won't see this password again in plain text
- Change the admin password after first login
- Logs are automatically rotated (max 10MB per file, 5 backups)
"@

try {
    $readmeContent | Out-File -FilePath (Join-Path $config.ProjectPath "SECUREBANK_CREDENTIALS.txt") -Encoding UTF8
    Write-ColorOutput "Credentials file created: SECUREBANK_CREDENTIALS.txt" -Type "SUCCESS"
} catch {
    Write-ColorOutput "Failed to create credentials file: $_" -Type "ERROR"
}

# =============================================
# COMPLETION
# =============================================

Clear-Host
Write-Host @"

================================================
          SETUP COMPLETE!
================================================

"@ -ForegroundColor Green

Write-Host "INSTALLATION SUMMARY" -ForegroundColor Cyan
Write-Host "===============================================" -ForegroundColor Cyan

Write-Host ""
Write-Host "Project Details:" -ForegroundColor Yellow
Write-Host "  Location: $($config.ProjectPath)" -ForegroundColor White
Write-Host "  Schema: database\schema.sql (imported)" -ForegroundColor White

Write-Host ""
Write-Host "DATABASE CREDENTIALS (SAVE THESE!):" -ForegroundColor Red
Write-Host "  Username: $($config.MySQLUser)" -ForegroundColor White
Write-Host "  Password: $($config.MySQLRootPassword)" -ForegroundColor White
Write-Host "  Database: $($config.MySQLDB)" -ForegroundColor White

Write-Host ""
Write-Host "APPLICATION LOGIN:" -ForegroundColor Green
Write-Host "  Admin: $($config.AdminUser) / $($config.AdminPassword)" -ForegroundColor White
Write-Host "  Test User: john_doe / password123" -ForegroundColor White

Write-Host ""
Write-Host "QUICK START:" -ForegroundColor Cyan
Write-Host "  1. Run: $($config.ProjectPath)\start.bat" -ForegroundColor White
Write-Host "  2. Open: http://localhost:5000" -ForegroundColor White

Write-Host ""
Write-Host "LOG FILES LOCATION:" -ForegroundColor Magenta
Write-Host "  $($config.ProjectPath)\logs\" -ForegroundColor White
Write-Host "  Configure your log collector to monitor this folder" -ForegroundColor White

Write-Host ""
Write-Host "CRITICAL NEXT STEPS:" -ForegroundColor Red
Write-Host "  1. SAVE THE DATABASE PASSWORD ABOVE" -ForegroundColor Red
Write-Host "  2. Double-click 'start.bat' to launch the application" -ForegroundColor White
Write-Host "  3. Login with admin/admin123" -ForegroundColor White
Write-Host "  4. Check logs folder for log files" -ForegroundColor White

Write-Host ""
Write-Host ""

# Ask if user wants to start the app
$startChoice = Read-Host "Start SecureBank now? (y/n)"
if ($startChoice -eq 'y') {
    Write-Host ""
    Write-Host "Starting SecureBank..." -ForegroundColor Green
    Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$($config.ProjectPath)'; Write-Host 'Starting SecureBank...'; .\venv\Scripts\Activate; python app.py"
    Start-Sleep -Seconds 3
    Start-Process "http://localhost:5000"
    Write-Host "Application started! Browser opened to http://localhost:5000" -ForegroundColor Green
} else {
    Write-Host ""
    Write-Host "You can start the application later by running: $($config.ProjectPath)\start.bat" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "Setup complete! Credentials saved to: SECUREBANK_CREDENTIALS.txt" -ForegroundColor Green

# Open the credentials file
try {
    Start-Process notepad (Join-Path $config.ProjectPath "SECUREBANK_CREDENTIALS.txt")
} catch {
    Write-ColorOutput "Could not open credentials file automatically" -Type "WARNING"
}

Write-Host ""
pause