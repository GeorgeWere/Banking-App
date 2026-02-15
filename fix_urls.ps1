# fix_urls.ps1
Write-Host "Fixing URL references in templates..." -ForegroundColor Cyan

$templatesDir = "C:\SecureBank\templates"
$replacements = @{
    "url_for\('login'\)" = "url_for('auth.login')"
    "url_for\('register'\)" = "url_for('auth.register')"
    "url_for\('logout'\)" = "url_for('auth.logout')"
    "url_for\('dashboard'\)" = "url_for('customer.dashboard')"
    "url_for\('transfer'\)" = "url_for('customer.transfer')"
    "url_for\('deposit'\)" = "url_for('customer.deposit')"
    "url_for\('pay_bills'\)" = "url_for('customer.pay_bills')"
    "url_for\('transactions'\)" = "url_for('customer.transactions')"
    "url_for\('profile'\)" = "url_for('customer.profile')"
    "url_for\('statements'\)" = "url_for('customer.statements')"
    "url_for\('admin_dashboard'\)" = "url_for('admin.dashboard')"
    "url_for\('admin_users'\)" = "url_for('admin.users')"
    "url_for\('admin_logs'\)" = "url_for('admin.logs')"
}

Get-ChildItem -Path $templatesDir -Recurse -Filter "*.html" | ForEach-Object {
    $file = $_.FullName
    $content = Get-Content $file -Raw
    
    $changed = $false
    foreach ($pattern in $replacements.Keys) {
        if ($content -match $pattern) {
            $content = $content -replace $pattern, $replacements[$pattern]
            $changed = $true
        }
    }
    
    if ($changed) {
        $content | Set-Content $file -NoNewline
        Write-Host "  Updated: $($_.Name)" -ForegroundColor Green
    }
}

Write-Host "`n✅ All templates updated!" -ForegroundColor Green
Write-Host "Restart the app and it should work now." -ForegroundColor Yellow
pause