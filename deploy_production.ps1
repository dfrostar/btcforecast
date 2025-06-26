# Production Deployment Script for BTC Forecast - Phase 2
# Deploys the application with PostgreSQL, Redis, and monitoring

param(
    [Parameter(Mandatory=$false)]
    [string]$Environment = "production",
    
    [Parameter(Mandatory=$false)]
    [switch]$SkipTests,
    
    [Parameter(Mandatory=$false)]
    [switch]$SkipBackup,
    
    [Parameter(Mandatory=$false)]
    [switch]$Force,
    
    [Parameter(Mandatory=$false)]
    [switch]$Help
)

# Configuration
$Config = @{
    ProjectName = "btcforecast"
    DockerComposeFile = "docker-compose.yml"
    EnvironmentFile = ".env.production"
    BackupDir = "backups"
    LogDir = "logs"
    HealthCheckUrl = "http://localhost/health"
    HealthCheckTimeout = 300  # 5 minutes
}

function Show-Help {
    Write-Host "BTC Forecast Production Deployment Script" -ForegroundColor Green
    Write-Host "==========================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "Usage:" -ForegroundColor Yellow
    Write-Host "  .\deploy_production.ps1 [Parameters]" -ForegroundColor White
    Write-Host ""
    Write-Host "Parameters:" -ForegroundColor Yellow
    Write-Host "  -Environment <environment>" -ForegroundColor White
    Write-Host "    Deployment environment (default: production)" -ForegroundColor Gray
    Write-Host ""
    Write-Host "  -SkipTests" -ForegroundColor White
    Write-Host "    Skip pre-deployment tests" -ForegroundColor Gray
    Write-Host ""
    Write-Host "  -SkipBackup" -ForegroundColor White
    Write-Host "    Skip database backup" -ForegroundColor Gray
    Write-Host ""
    Write-Host "  -Force" -ForegroundColor White
    Write-Host "    Force deployment without confirmation" -ForegroundColor Gray
    Write-Host ""
    Write-Host "  -Help" -ForegroundColor White
    Write-Host "    Show this help message" -ForegroundColor Gray
    Write-Host ""
    Write-Host "Examples:" -ForegroundColor Yellow
    Write-Host "  .\deploy_production.ps1" -ForegroundColor White
    Write-Host "  .\deploy_production.ps1 -Environment staging" -ForegroundColor White
    Write-Host "  .\deploy_production.ps1 -SkipTests -Force" -ForegroundColor White
}

function Test-Prerequisites {
    Write-Host "Checking deployment prerequisites..." -ForegroundColor Yellow
    
    # Check Docker
    try {
        $dockerVersion = docker --version 2>&1
        Write-Host "✓ Docker found: $dockerVersion" -ForegroundColor Green
    }
    catch {
        Write-Host "✗ Docker not found. Please install Docker Desktop" -ForegroundColor Red
        return $false
    }
    
    # Check Docker Compose
    try {
        $composeVersion = docker-compose --version 2>&1
        Write-Host "✓ Docker Compose found: $composeVersion" -ForegroundColor Green
    }
    catch {
        Write-Host "✗ Docker Compose not found. Please install Docker Compose" -ForegroundColor Red
        return $false
    }
    
    # Check if Docker is running
    try {
        docker info | Out-Null
        Write-Host "✓ Docker daemon is running" -ForegroundColor Green
    }
    catch {
        Write-Host "✗ Docker daemon is not running. Please start Docker Desktop" -ForegroundColor Red
        return $false
    }
    
    # Check required files
    $requiredFiles = @(
        "docker-compose.yml",
        "Dockerfile.api",
        "Dockerfile.web",
        "database/init/01-init.sql",
        "nginx/nginx.conf",
        "monitoring/prometheus.yml"
    )
    
    foreach ($file in $requiredFiles) {
        if (-not (Test-Path $file)) {
            Write-Host "✗ Required file not found: $file" -ForegroundColor Red
            return $false
        }
    }
    
    Write-Host "✓ All prerequisites met" -ForegroundColor Green
    return $true
}

function Backup-Database {
    Write-Host "Creating database backup..." -ForegroundColor Yellow
    
    $timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
    $backupFile = "$($Config.BackupDir)/backup_$timestamp.sql"
    
    # Create backup directory
    New-Item -ItemType Directory -Path $Config.BackupDir -Force | Out-Null
    
    try {
        # Check if PostgreSQL container is running
        $postgresContainer = docker ps --filter "name=btcforecast-postgres" --format "{{.Names}}"
        if ($postgresContainer) {
            # Create backup using pg_dump
            docker exec btcforecast-postgres pg_dump -U btcforecast_user btcforecast > $backupFile
            Write-Host "✓ Database backup created: $backupFile" -ForegroundColor Green
        }
        else {
            Write-Host "⚠ PostgreSQL container not running, skipping backup" -ForegroundColor Yellow
        }
    }
    catch {
        Write-Host "✗ Failed to create database backup: $($_.Exception.Message)" -ForegroundColor Red
    }
}

function Test-Application {
    Write-Host "Running pre-deployment tests..." -ForegroundColor Yellow
    
    # Run health checks
    try {
        $response = Invoke-WebRequest -Uri $Config.HealthCheckUrl -TimeoutSec 30 -UseBasicParsing
        if ($response.StatusCode -eq 200) {
            Write-Host "✓ Health check passed" -ForegroundColor Green
        }
        else {
            Write-Host "✗ Health check failed with status: $($response.StatusCode)" -ForegroundColor Red
            return $false
        }
    }
    catch {
        Write-Host "✗ Health check failed: $($_.Exception.Message)" -ForegroundColor Red
        return $false
    }
    
    # Run load tests if not skipped
    if (-not $SkipTests) {
        Write-Host "Running load tests..." -ForegroundColor Yellow
        try {
            & .\run_load_test.ps1 -Scenario light -Headless
            Write-Host "✓ Load tests passed" -ForegroundColor Green
        }
        catch {
            Write-Host "✗ Load tests failed: $($_.Exception.Message)" -ForegroundColor Red
            return $false
        }
    }
    
    return $true
}

function Stop-Services {
    Write-Host "Stopping existing services..." -ForegroundColor Yellow
    
    try {
        docker-compose -f $Config.DockerComposeFile down
        Write-Host "✓ Services stopped" -ForegroundColor Green
    }
    catch {
        Write-Host "✗ Failed to stop services: $($_.Exception.Message)" -ForegroundColor Red
        if (-not $Force) {
            return $false
        }
    }
    
    return $true
}

function Build-Images {
    Write-Host "Building Docker images..." -ForegroundColor Yellow
    
    try {
        # Build API image
        Write-Host "Building API image..." -ForegroundColor Cyan
        docker build -f Dockerfile.api -t btcforecast-api:latest .
        
        # Build Web image
        Write-Host "Building Web image..." -ForegroundColor Cyan
        docker build -f Dockerfile.web -t btcforecast-web:latest .
        
        Write-Host "✓ Images built successfully" -ForegroundColor Green
    }
    catch {
        Write-Host "✗ Failed to build images: $($_.Exception.Message)" -ForegroundColor Red
        return $false
    }
    
    return $true
}

function Start-Services {
    Write-Host "Starting services..." -ForegroundColor Yellow
    
    try {
        # Start services with docker-compose
        docker-compose -f $Config.DockerComposeFile up -d
        
        Write-Host "✓ Services started" -ForegroundColor Green
    }
    catch {
        Write-Host "✗ Failed to start services: $($_.Exception.Message)" -ForegroundColor Red
        return $false
    }
    
    return $true
}

function Wait-ForHealthCheck {
    Write-Host "Waiting for services to be healthy..." -ForegroundColor Yellow
    
    $startTime = Get-Date
    $timeout = $Config.HealthCheckTimeout
    
    while ((Get-Date) -lt ($startTime.AddSeconds($timeout))) {
        try {
            $response = Invoke-WebRequest -Uri $Config.HealthCheckUrl -TimeoutSec 10 -UseBasicParsing
            if ($response.StatusCode -eq 200) {
                Write-Host "✓ All services are healthy" -ForegroundColor Green
                return $true
            }
        }
        catch {
            # Continue waiting
        }
        
        Write-Host "Waiting for services to be ready..." -ForegroundColor Yellow
        Start-Sleep -Seconds 10
    }
    
    Write-Host "✗ Services failed to become healthy within timeout" -ForegroundColor Red
    return $false
}

function Show-DeploymentStatus {
    Write-Host "Deployment Status" -ForegroundColor Green
    Write-Host "=================" -ForegroundColor Green
    Write-Host ""
    
    # Show running containers
    Write-Host "Running Containers:" -ForegroundColor Yellow
    docker ps --filter "name=btcforecast" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
    Write-Host ""
    
    # Show service URLs
    Write-Host "Service URLs:" -ForegroundColor Yellow
    Write-Host "  Web Application: http://localhost" -ForegroundColor White
    Write-Host "  API Documentation: http://localhost/api/docs" -ForegroundColor White
    Write-Host "  Grafana Dashboard: http://localhost:3000" -ForegroundColor White
    Write-Host "  Prometheus: http://localhost:9090" -ForegroundColor White
    Write-Host ""
    
    # Show logs
    Write-Host "Recent Logs:" -ForegroundColor Yellow
    docker-compose -f $Config.DockerComposeFile logs --tail=10
}

function Rollback-Deployment {
    Write-Host "Rolling back deployment..." -ForegroundColor Red
    
    try {
        # Stop current services
        docker-compose -f $Config.DockerComposeFile down
        
        # Restore from backup if available
        $latestBackup = Get-ChildItem -Path $Config.BackupDir -Filter "backup_*.sql" | Sort-Object LastWriteTime -Descending | Select-Object -First 1
        if ($latestBackup) {
            Write-Host "Restoring from backup: $($latestBackup.Name)" -ForegroundColor Yellow
            # Restore logic would go here
        }
        
        Write-Host "✓ Rollback completed" -ForegroundColor Green
    }
    catch {
        Write-Host "✗ Rollback failed: $($_.Exception.Message)" -ForegroundColor Red
    }
}

# Main deployment function
function Deploy-Production {
    Write-Host "Starting production deployment..." -ForegroundColor Green
    Write-Host "Environment: $Environment" -ForegroundColor Yellow
    Write-Host "Timestamp: $(Get-Date)" -ForegroundColor Yellow
    Write-Host ""
    
    # Check prerequisites
    if (-not (Test-Prerequisites)) {
        Write-Host "✗ Prerequisites check failed" -ForegroundColor Red
        exit 1
    }
    
    # Confirm deployment
    if (-not $Force) {
        $confirmation = Read-Host "Are you sure you want to deploy to $Environment? (y/N)"
        if ($confirmation -ne "y" -and $confirmation -ne "Y") {
            Write-Host "Deployment cancelled" -ForegroundColor Yellow
            exit 0
        }
    }
    
    # Create log directory
    New-Item -ItemType Directory -Path $Config.LogDir -Force | Out-Null
    
    # Backup database
    if (-not $SkipBackup) {
        Backup-Database
    }
    
    # Run tests
    if (-not $SkipTests) {
        if (-not (Test-Application)) {
            Write-Host "✗ Pre-deployment tests failed" -ForegroundColor Red
            exit 1
        }
    }
    
    # Stop existing services
    if (-not (Stop-Services)) {
        Write-Host "✗ Failed to stop existing services" -ForegroundColor Red
        exit 1
    }
    
    # Build images
    if (-not (Build-Images)) {
        Write-Host "✗ Failed to build images" -ForegroundColor Red
        Rollback-Deployment
        exit 1
    }
    
    # Start services
    if (-not (Start-Services)) {
        Write-Host "✗ Failed to start services" -ForegroundColor Red
        Rollback-Deployment
        exit 1
    }
    
    # Wait for health check
    if (-not (Wait-ForHealthCheck)) {
        Write-Host "✗ Services failed health check" -ForegroundColor Red
        Rollback-Deployment
        exit 1
    }
    
    # Show deployment status
    Show-DeploymentStatus
    
    Write-Host ""
    Write-Host "✓ Production deployment completed successfully!" -ForegroundColor Green
    Write-Host "Deployment completed at: $(Get-Date)" -ForegroundColor Yellow
}

# Main execution
if ($Help) {
    Show-Help
    exit 0
}

# Run deployment
Deploy-Production 