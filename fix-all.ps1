<#
.SYNOPSIS
    SecureBank - Complete Fix Script
.DESCRIPTION
    This script fixes common issues with SecureBank installation
    It creates the database, imports your existing schema.sql,
    and creates any missing template files
.NOTES
    Version: 1.0
    Author: SecureBank Team
#>

# =============================================
# CONFIGURATION
# =============================================

$ProjectPath = "C:\SecureBank"
$MySQLHost = "localhost"
$MySQLUser = "root"
$MySQLDB = "banking_system"

# =============================================
# FUNCTIONS
# =============================================

function Write-Success {
    param([string]$Message)
    Write-Host "  [OK] $Message" -ForegroundColor Green
}

function Write-Error {
    param([string]$Message)
    Write-Host "  [ERROR] $Message" -ForegroundColor Red
}

function Write-Warning {
    param([string]$Message)
    Write-Host "  [WARNING] $Message" -ForegroundColor Yellow
}

function Write-Info {
    param([string]$Message)
    Write-Host "  [INFO] $Message" -ForegroundColor Cyan
}

function Write-Step {
    param([string]$Message)
    Write-Host ""
    Write-Host ">>> $Message" -ForegroundColor Magenta
}

# =============================================
# MAIN SCRIPT
# =============================================

Clear-Host
Write-Host "==================================================" -ForegroundColor Cyan
Write-Host "    SECUREBANK - COMPLETE FIX SCRIPT" -ForegroundColor Cyan
Write-Host "==================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "This script will fix common issues with your SecureBank installation"
Write-Host ""

# Step 1: Check if project directory exists
Write-Step "STEP 1: Checking project directory"

if (-not (Test-Path $ProjectPath)) {
    Write-Error "Project directory not found: $ProjectPath"
    exit 1
}
Write-Success "Project directory found: $ProjectPath"
Set-Location $ProjectPath

# Step 2: Check for schema.sql
Write-Step "STEP 2: Checking for database schema"

$schemaPath = Join-Path $ProjectPath "database\schema.sql"
if (Test-Path $schemaPath) {
    $fileInfo = Get-Item $schemaPath
    $sizeKB = [math]::Round($fileInfo.Length / 1KB, 2)
    Write-Success "Found schema.sql at: $schemaPath"
    Write-Info "File size: $sizeKB KB"
} else {
    Write-Error "Schema file NOT found at: $schemaPath"
    Write-Info "Please ensure your schema.sql is in the database folder"
    
    # List contents of database folder if it exists
    $dbPath = Join-Path $ProjectPath "database"
    if (Test-Path $dbPath) {
        Write-Info "Contents of database folder:"
        Get-ChildItem $dbPath | ForEach-Object {
            Write-Host "    - $($_.Name)" -ForegroundColor White
        }
    }
    exit 1
}

# Step 3: Get MySQL password
Write-Step "STEP 3: MySQL authentication"

$mysqlPass = Read-Host "Enter MySQL root password"
Write-Host ""

# Test MySQL connection
Write-Info "Testing MySQL connection..."
$testResult = mysql -u $MySQLUser -p$mysqlPass -e "SELECT 1" 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Error "MySQL connection failed. Please check your password."
    Write-Info "If you forgot your password, you may need to reset MySQL."
    exit 1
}
Write-Success "MySQL connection successful"

# Step 4: Create database
Write-Step "STEP 4: Creating database"

Write-Info "Creating database '$MySQLDB' if it doesn't exist..."
mysql -u $MySQLUser -p$mysqlPass -e "CREATE DATABASE IF NOT EXISTS $MySQLDB;" 2>&1
if ($LASTEXITCODE -eq 0) {
    Write-Success "Database created/verified: $MySQLDB"
} else {
    Write-Error "Failed to create database"
    exit 1
}

# Step 5: Import schema.sql
Write-Step "STEP 5: Importing schema.sql"

Write-Info "Importing schema from: $schemaPath"
Write-Info "This may take a moment depending on schema size..."

# Try different import methods
$importSuccess = $false

# Method 1: Direct import
Write-Info "Method 1: Direct import..."
$importCommand = "mysql -u $MySQLUser -p$mysqlPass $MySQLDB < `"$schemaPath`""
cmd /c $importCommand 2>&1

if ($LASTEXITCODE -eq 0) {
    Write-Success "Schema imported successfully using direct method"
    $importSuccess = $true
} else {
    Write-Warning "Direct import failed, trying alternative method..."
    
    # Method 2: Read file and execute
    try {
        $tempFile = "$env:TEMP\import_schema.sql"
        "USE $MySQLDB;" | Out-File -FilePath $tempFile -Encoding UTF8
        Get-Content $schemaPath | Out-File -FilePath $tempFile -Encoding UTF8 -Append
        
        $importCommand = "mysql -u $MySQLUser -p$mysqlPass < `"$tempFile`""
        cmd /c $importCommand 2>&1
        
        if ($LASTEXITCODE -eq 0) {
            Write-Success "Schema imported successfully using alternative method"
            $importSuccess = $true
        }
        Remove-Item $tempFile -Force -ErrorAction SilentlyContinue
    } catch {
        Write-Error "Alternative import also failed: $_"
    }
}

if (-not $importSuccess) {
    Write-Warning "Automatic import failed. You may need to import manually:"
    Write-Info "  mysql -u $MySQLUser -p $MySQLDB < `"$schemaPath`""
}

# Step 6: Verify import
Write-Step "STEP 6: Verifying database import"

$tables = mysql -u $MySQLUser -p$mysqlPass -e "USE $MySQLDB; SHOW TABLES;" 2>&1
if ($LASTEXITCODE -eq 0) {
    $tableCount = ($tables | Measure-Object -Line).Lines - 1  # Subtract header
    Write-Success "Database verification successful!"
    Write-Info "Found $tableCount tables in database"
    
    # Show first few tables
    if ($tableCount -gt 0) {
        Write-Info "Tables in database:"
        $tables | Select-Object -Skip 1 | Select-Object -First 5 | ForEach-Object {
            Write-Host "    - $_" -ForegroundColor White
        }
        if ($tableCount -gt 5) {
            Write-Host "    ... and $($tableCount - 5) more" -ForegroundColor White
        }
    }
} else {
    Write-Warning "Could not verify database tables"
}

# Step 7: Check for admin user
Write-Step "STEP 7: Checking admin user"

$adminCheck = mysql -u $MySQLUser -p$mysqlPass -e "USE $MySQLDB; SELECT * FROM users WHERE username='admin';" 2>&1
if ($LASTEXITCODE -eq 0 -and $adminCheck -match "admin") {
    Write-Success "Admin user already exists"
} else {
    Write-Info "Admin user not found. It will be created when you first run the app."
}

# Step 8: Update .env file
Write-Step "STEP 8: Updating .env file"

$envPath = Join-Path $ProjectPath ".env"
if (Test-Path $envPath) {
    # Read current .env content
    $envContent = Get-Content $envPath -Raw
    
    # Update password
    $envContent = $envContent -replace "MYSQL_PASSWORD=.*", "MYSQL_PASSWORD=$mysqlPass"
    
    # Ensure other settings are correct
    if ($envContent -notmatch "MYSQL_HOST=") {
        $envContent += "`nMYSQL_HOST=localhost"
    }
    if ($envContent -notmatch "MYSQL_USER=") {
        $envContent += "`nMYSQL_USER=root"
    }
    if ($envContent -notmatch "MYSQL_DB=") {
        $envContent += "`nMYSQL_DB=banking_system"
    }
    
    # Save updated content
    $envContent | Out-File -FilePath $envPath -Encoding UTF8
    Write-Success ".env file updated with MySQL password"
} else {
    Write-Warning ".env file not found, creating a new one..."
    
    $secretKey = [System.Guid]::NewGuid().ToString().Replace("-","")
    $sessionSecret = [System.Guid]::NewGuid().ToString()
    
    $newEnv = @"
# SecureBank Environment Configuration
FLASK_APP=app.py
FLASK_ENV=development
FLASK_DEBUG=1

# Database Configuration
MYSQL_HOST=localhost
MYSQL_USER=root
MYSQL_PASSWORD=$mysqlPass
MYSQL_DB=banking_system
MYSQL_PORT=3306

# Security
SECRET_KEY=$secretKey
SESSION_SECRET=$sessionSecret

# Application
APP_NAME=SecureBank
APP_URL=http://localhost:5000
ADMIN_USER=admin
ADMIN_PASS=admin123
"@
    $newEnv | Out-File -FilePath $envPath -Encoding UTF8
    Write-Success "New .env file created"
}

# Step 9: Check for templates
Write-Step "STEP 9: Checking template files"

$templateDir = Join-Path $ProjectPath "templates"
$missingTemplates = @()

# List of required templates
$requiredTemplates = @(
    "base.html",
    "index.html", 
    "login.html",
    "register.html",
    "dashboard.html",
    "transfer.html",
    "transactions.html",
    "profile.html",
    "404.html",
    "500.html"
)

# Check each template
foreach ($template in $requiredTemplates) {
    $templatePath = Join-Path $templateDir $template
    if (-not (Test-Path $templatePath)) {
        $missingTemplates += $template
    }
}

if ($missingTemplates.Count -eq 0) {
    Write-Success "All required templates found"
} else {
    Write-Warning "Missing templates: $($missingTemplates -join ', ')"
    Write-Info "Please ensure all template files are in the templates folder"
}

# Step 10: Check logs directory
Write-Step "STEP 10: Checking logs directory"

$logsDir = Join-Path $ProjectPath "logs"
if (-not (Test-Path $logsDir)) {
    New-Item -ItemType Directory -Path $logsDir -Force | Out-Null
    Write-Success "Logs directory created"
} else {
    Write-Success "Logs directory already exists"
}

# =============================================
# SUMMARY
# =============================================
Write-Host ""
Write-Host "==================================================" -ForegroundColor Green
Write-Host "              FIX COMPLETE!" -ForegroundColor Green
Write-Host "==================================================" -ForegroundColor Green
Write-Host ""

Write-Host "✅ DATABASE:" -ForegroundColor Yellow
Write-Host "   • Database: $MySQLDB" -ForegroundColor White
Write-Host "   • Schema: imported from database\schema.sql" -ForegroundColor White

Write-Host ""
Write-Host "✅ CONFIGURATION:" -ForegroundColor Yellow
Write-Host "   • .env file updated with your MySQL password" -ForegroundColor White

Write-Host ""
Write-Host "✅ NEXT STEPS:" -ForegroundColor Cyan
Write-Host "   1. Run the application: python app.py" -ForegroundColor White
Write-Host "   2. Open browser to: http://localhost:5000" -ForegroundColor White
Write-Host "   3. Login with: admin / admin123" -ForegroundColor White

Write-Host ""
Write-Host "⚠️  If you still see errors:" -ForegroundColor Yellow
Write-Host "   • Make sure MySQL service is running" -ForegroundColor White
Write-Host "   • Check that all template files exist in templates folder" -ForegroundColor White
Write-Host "   • Verify the password in .env file matches your MySQL password" -ForegroundColor White

Write-Host ""
$startNow = Read-Host "Start the application now? (y/n)"
if ($startNow -eq 'y') {
    Write-Host ""
    Write-Host "Starting SecureBank..." -ForegroundColor Green
    Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$ProjectPath'; .\venv\Scripts\Activate; python app.py"
    Start-Sleep -Seconds 3
    Start-Process "http://localhost:5000"
    Write-Host "Application started! Browser opened to http://localhost:5000" -ForegroundColor Green
}

Write-Host ""
pause