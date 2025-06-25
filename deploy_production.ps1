# Production Deployment Script for BTC Forecasting API
# This script sets up the application for production deployment with security and monitoring

param(
    [string]$Environment = "production",
    [string]$Domain = "",
    [string]$SSL_Cert_Path = "",
    [string]$SSL_Key_Path = "",
    [switch]$SkipSecurityChecks = $false,
    [switch]$Force = $false
)

Write-Host "🚀 BTC Forecasting API - Production Deployment" -ForegroundColor Green
Write-Host "================================================" -ForegroundColor Green

# Check if running as administrator
if (-NOT ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole] "Administrator")) {
    Write-Host "❌ This script requires administrator privileges for production deployment." -ForegroundColor Red
    Write-Host "Please run PowerShell as Administrator and try again." -ForegroundColor Yellow
    exit 1
}

# Configuration
$APP_NAME = "btcforecast"
$API_PORT = 8000
$FRONTEND_PORT = 8501
$LOG_DIR = "logs"
$BACKUP_DIR = "backups"
$ENV_FILE = ".env.production"

# Create necessary directories
Write-Host "📁 Creating necessary directories..." -ForegroundColor Blue
$directories = @($LOG_DIR, $BACKUP_DIR, "ssl", "config")
foreach ($dir in $directories) {
    if (-not (Test-Path $dir)) {
        New-Item -ItemType Directory -Path $dir -Force | Out-Null
        Write-Host "  ✓ Created directory: $dir" -ForegroundColor Green
    }
}

# Security checks
if (-not $SkipSecurityChecks) {
    Write-Host "🔒 Running security checks..." -ForegroundColor Blue
    
    # Check for default passwords
    $configFile = "config.py"
    if (Test-Path $configFile) {
        $configContent = Get-Content $configFile -Raw
        if ($configContent -match "admin123" -or $configContent -match "demo123") {
            Write-Host "  ⚠️  Warning: Default passwords detected in config.py" -ForegroundColor Yellow
            Write-Host "     Please change default passwords before production deployment" -ForegroundColor Yellow
            if (-not $Force) {
                Write-Host "     Use -Force to continue anyway" -ForegroundColor Yellow
                exit 1
            }
        }
    }
    
    # Check for JWT secret key
    if ($configContent -match "your-secret-key-change-in-production") {
        Write-Host "  ⚠️  Warning: Default JWT secret key detected" -ForegroundColor Yellow
        Write-Host "     Please change JWT_SECRET_KEY in config.py" -ForegroundColor Yellow
        if (-not $Force) {
            Write-Host "     Use -Force to continue anyway" -ForegroundColor Yellow
            exit 1
        }
    }
    
    # Check for CORS settings
    if ($configContent -match 'allow_origins=\["\*"\]') {
        Write-Host "  ⚠️  Warning: CORS is set to allow all origins" -ForegroundColor Yellow
        Write-Host "     Consider restricting CORS for production" -ForegroundColor Yellow
    }
    
    Write-Host "  ✓ Security checks completed" -ForegroundColor Green
}

# Environment setup
Write-Host "⚙️  Setting up production environment..." -ForegroundColor Blue

# Create production environment file
$envContent = @"
# Production Environment Configuration
ENVIRONMENT=production
API_HOST=0.0.0.0
API_PORT=$API_PORT
FRONTEND_PORT=$FRONTEND_PORT
LOG_LEVEL=INFO
ENABLE_DOCS=false
CORS_ORIGINS=["https://$Domain"]
JWT_SECRET_KEY=$(New-Guid)
DATABASE_URL=sqlite:///btcforecast_production.db
RATE_LIMIT_ENABLED=true
AUDIT_LOGGING_ENABLED=true
SSL_ENABLED=true
DOMAIN=$Domain
"@

Set-Content -Path $ENV_FILE -Value $envContent
Write-Host "  ✓ Created production environment file" -ForegroundColor Green

# SSL Certificate setup
if ($Domain -and $SSL_Cert_Path -and $SSL_Key_Path) {
    Write-Host "🔐 Setting up SSL certificates..." -ForegroundColor Blue
    
    if (Test-Path $SSL_Cert_Path) {
        Copy-Item $SSL_Cert_Path "ssl/cert.pem" -Force
        Write-Host "  ✓ SSL certificate copied" -ForegroundColor Green
    } else {
        Write-Host "  ⚠️  SSL certificate not found at: $SSL_Cert_Path" -ForegroundColor Yellow
    }
    
    if (Test-Path $SSL_Key_Path) {
        Copy-Item $SSL_Key_Path "ssl/key.pem" -Force
        Write-Host "  ✓ SSL private key copied" -ForegroundColor Green
    } else {
        Write-Host "  ⚠️  SSL private key not found at: $SSL_Key_Path" -ForegroundColor Yellow
    }
}

# Database initialization
Write-Host "🗄️  Initializing production database..." -ForegroundColor Blue
try {
    python -c "
from api.database import db_manager, UserRepository
from api.auth import hash_password
import os

# Create admin user for production
admin_password = os.environ.get('ADMIN_PASSWORD', 'ChangeMe123!')
hashed_password = hash_password(admin_password)

try:
    UserRepository.create_user(
        username='admin',
        email='admin@$Domain',
        hashed_password=hashed_password,
        role='admin'
    )
    print('Production admin user created')
except Exception as e:
    print(f'Admin user already exists or error: {e}')
"
    Write-Host "  ✓ Database initialized" -ForegroundColor Green
} catch {
    Write-Host "  ⚠️  Database initialization warning: $_" -ForegroundColor Yellow
}

# Install dependencies
Write-Host "📦 Installing production dependencies..." -ForegroundColor Blue
try {
    pip install -r requirements.txt --upgrade
    Write-Host "  ✓ Dependencies installed" -ForegroundColor Green
} catch {
    Write-Host "  ❌ Failed to install dependencies: $_" -ForegroundColor Red
    exit 1
}

# Create production startup script
$productionStartScript = @"
# Production Startup Script
Write-Host "Starting BTC Forecasting API in production mode..." -ForegroundColor Green

# Set environment variables
`$env:ENVIRONMENT = "production"
`$env:LOG_LEVEL = "INFO"

# Start API with production settings
Start-Process -FilePath "python" -ArgumentList "-m", "uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "$API_PORT", "--workers", "4" -WindowStyle Hidden

# Start frontend with production settings
Start-Process -FilePath "streamlit" -ArgumentList "run", "app.py", "--server.port", "$FRONTEND_PORT", "--server.address", "0.0.0.0" -WindowStyle Hidden

Write-Host "Production services started on ports $API_PORT (API) and $FRONTEND_PORT (Frontend)" -ForegroundColor Green
"@

Set-Content -Path "start_production.ps1" -Value $productionStartScript
Write-Host "  ✓ Created production startup script" -ForegroundColor Green

# Create monitoring script
$monitoringScript = @"
# Production Monitoring Script
Write-Host "Monitoring BTC Forecasting API..." -ForegroundColor Blue

while (`$true) {
    try {
        # Check API health
        `$apiResponse = Invoke-RestMethod -Uri "http://localhost:$API_PORT/health/detailed" -Method Get -TimeoutSec 5
        Write-Host "API Status: ✓ Healthy" -ForegroundColor Green
        
        # Check frontend
        `$frontendResponse = Invoke-WebRequest -Uri "http://localhost:$FRONTEND_PORT" -Method Get -TimeoutSec 5
        Write-Host "Frontend Status: ✓ Running" -ForegroundColor Green
        
        # Log system metrics
        `$cpu = (Get-Counter "\Processor(_Total)\% Processor Time").CounterSamples.CookedValue
        `$memory = (Get-Counter "\Memory\Available MBytes").CounterSamples.CookedValue
        Write-Host "System: CPU: `$(`$cpu.ToString('F1'))% | Memory: `$(`$memory.ToString('F0')) MB available" -ForegroundColor Cyan
        
    } catch {
        Write-Host "❌ Service check failed: `$_" -ForegroundColor Red
    }
    
    Start-Sleep -Seconds 30
}
"@

Set-Content -Path "monitor_production.ps1" -Value $monitoringScript
Write-Host "  ✓ Created monitoring script" -ForegroundColor Green

# Create backup script
$backupScript = @"
# Production Backup Script
Write-Host "Creating production backup..." -ForegroundColor Blue

`$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
`$backupDir = "backups/backup_`$timestamp"

New-Item -ItemType Directory -Path `$backupDir -Force | Out-Null

# Backup database
if (Test-Path "btcforecast_production.db") {
    Copy-Item "btcforecast_production.db" "`$backupDir/" -Force
    Write-Host "  ✓ Database backed up" -ForegroundColor Green
}

# Backup logs
if (Test-Path "logs") {
    Copy-Item "logs" "`$backupDir/" -Recurse -Force
    Write-Host "  ✓ Logs backed up" -ForegroundColor Green
}

# Backup configuration
Copy-Item "config.py" "`$backupDir/" -Force
Copy-Item ".env.production" "`$backupDir/" -Force
Write-Host "  ✓ Configuration backed up" -ForegroundColor Green

Write-Host "Backup completed: `$backupDir" -ForegroundColor Green
"@

Set-Content -Path "backup_production.ps1" -Value $backupScript
Write-Host "  ✓ Created backup script" -ForegroundColor Green

# Create Windows Service (optional)
Write-Host "🔧 Creating Windows Service configuration..." -ForegroundColor Blue
$serviceScript = @"
# Windows Service Configuration
# Run as Administrator to install the service

`$serviceName = "BTCForecastAPI"
`$serviceDisplayName = "BTC Forecasting API"
`$serviceDescription = "Bitcoin Price Forecasting API Service"

# Create service
New-Service -Name `$serviceName -DisplayName `$serviceDisplayName -Description `$serviceDescription -StartupType Automatic -BinaryPathName "python.exe -m uvicorn api.main:app --host 0.0.0.0 --port $API_PORT"

Write-Host "Service '$serviceName' created successfully" -ForegroundColor Green
Write-Host "To start the service: Start-Service -Name '$serviceName'" -ForegroundColor Yellow
Write-Host "To stop the service: Stop-Service -Name '$serviceName'" -ForegroundColor Yellow
"@

Set-Content -Path "install_service.ps1" -Value $serviceScript
Write-Host "  ✓ Created service installation script" -ForegroundColor Green

# Final instructions
Write-Host ""
Write-Host "🎉 Production deployment completed!" -ForegroundColor Green
Write-Host "=====================================" -ForegroundColor Green
Write-Host ""
Write-Host "📋 Next steps:" -ForegroundColor Yellow
Write-Host "1. Review and update .env.production with your settings" -ForegroundColor White
Write-Host "2. Change default passwords in the database" -ForegroundColor White
Write-Host "3. Configure SSL certificates if using HTTPS" -ForegroundColor White
Write-Host "4. Set up firewall rules for ports $API_PORT and $FRONTEND_PORT" -ForegroundColor White
Write-Host "5. Configure monitoring and alerting" -ForegroundColor White
Write-Host ""
Write-Host "🚀 To start production services:" -ForegroundColor Yellow
Write-Host "   .\start_production.ps1" -ForegroundColor White
Write-Host ""
Write-Host "📊 To monitor the application:" -ForegroundColor Yellow
Write-Host "   .\monitor_production.ps1" -ForegroundColor White
Write-Host ""
Write-Host "💾 To create backups:" -ForegroundColor Yellow
Write-Host "   .\backup_production.ps1" -ForegroundColor White
Write-Host ""
Write-Host "🔧 To install as Windows Service (run as Administrator):" -ForegroundColor Yellow
Write-Host "   .\install_service.ps1" -ForegroundColor White
Write-Host ""
Write-Host "⚠️  Security reminders:" -ForegroundColor Red
Write-Host "- Change default admin password" -ForegroundColor White
Write-Host "- Update JWT secret key" -ForegroundColor White
Write-Host "- Configure proper CORS origins" -ForegroundColor White
Write-Host "- Set up SSL certificates" -ForegroundColor White
Write-Host "- Configure firewall rules" -ForegroundColor White
Write-Host ""
Write-Host "📞 For support, check the documentation or contact the development team." -ForegroundColor Cyan 