#!/usr/bin/env powershell
<#
.SYNOPSIS
    Enhanced Deployment Script for BTC Forecast Application
.DESCRIPTION
    Deploys the enhanced BTC Forecast application with background processing,
    advanced monitoring, security, and multi-region support.
.PARAMETER Environment
    Deployment environment (development, staging, production)
.PARAMETER Region
    AWS region for deployment
.PARAMETER SkipTests
    Skip running tests before deployment
#>

param(
    [Parameter(Mandatory=$false)]
    [ValidateSet("development", "staging", "production")]
    [string]$Environment = "development",
    
    [Parameter(Mandatory=$false)]
    [string]$Region = "us-east-1",
    
    [Parameter(Mandatory=$false)]
    [switch]$SkipTests
)

# Set error action preference
$ErrorActionPreference = "Stop"

# Configuration
$ProjectName = "btcforecast"
$Version = "3.0.0"
$DockerImage = "btcforecast-api"
$DockerTag = "latest"

# Color functions for output
function Write-ColorOutput($ForegroundColor) {
    $fc = $host.UI.RawUI.ForegroundColor
    $host.UI.RawUI.ForegroundColor = $ForegroundColor
    if ($args) {
        Write-Output $args
    }
    $host.UI.RawUI.ForegroundColor = $fc
}

function Write-Success { Write-ColorOutput Green $args }
function Write-Warning { Write-ColorOutput Yellow $args }
function Write-Error { Write-ColorOutput Red $args }
function Write-Info { Write-ColorOutput Cyan $args }

# Header
Write-Info "=========================================="
Write-Info "BTC Forecast Enhanced Deployment Script"
Write-Info "Version: $Version"
Write-Info "Environment: $Environment"
Write-Info "Region: $Region"
Write-Info "=========================================="

# Function to check prerequisites
function Test-Prerequisites {
    Write-Info "Checking prerequisites..."
    
    # Check Docker
    try {
        $dockerVersion = docker --version
        Write-Success "Docker: $dockerVersion"
    }
    catch {
        Write-Error "Docker is not installed or not in PATH"
        exit 1
    }
    
    # Check Docker Compose
    try {
        $composeVersion = docker-compose --version
        Write-Success "Docker Compose: $composeVersion"
    }
    catch {
        Write-Error "Docker Compose is not installed or not in PATH"
        exit 1
    }
    
    # Check Python
    try {
        $pythonVersion = python --version
        Write-Success "Python: $pythonVersion"
    }
    catch {
        Write-Error "Python is not installed or not in PATH"
        exit 1
    }
    
    # Check if .env file exists
    if (Test-Path ".env") {
        Write-Success "Environment file found"
    }
    else {
        Write-Warning "No .env file found, creating from template"
        Copy-Item ".env.example" ".env" -ErrorAction SilentlyContinue
    }
}

# Function to run tests
function Invoke-Tests {
    if ($SkipTests) {
        Write-Warning "Skipping tests as requested"
        return
    }
    
    Write-Info "Running tests..."
    
    try {
        # Run unit tests
        python -m pytest tests/ -v --tb=short
        if ($LASTEXITCODE -ne 0) {
            Write-Error "Unit tests failed"
            exit 1
        }
        
        # Run integration tests
        python -m pytest tests/integration/ -v --tb=short
        if ($LASTEXITCODE -ne 0) {
            Write-Error "Integration tests failed"
            exit 1
        }
        
        Write-Success "All tests passed"
    }
    catch {
        Write-Error "Test execution failed: $_"
        exit 1
    }
}

# Function to build Docker images
function Build-DockerImages {
    Write-Info "Building Docker images..."
    
    try {
        # Build API image
        Write-Info "Building API image..."
        docker build -t "$DockerImage:$DockerTag" -f Dockerfile.api .
        if ($LASTEXITCODE -ne 0) {
            Write-Error "Failed to build API image"
            exit 1
        }
        
        # Build web image
        Write-Info "Building web image..."
        docker build -t "$ProjectName-web:$DockerTag" -f Dockerfile.web .
        if ($LASTEXITCODE -ne 0) {
            Write-Error "Failed to build web image"
            exit 1
        }
        
        Write-Success "Docker images built successfully"
    }
    catch {
        Write-Error "Docker build failed: $_"
        exit 1
    }
}

# Function to setup environment
function Setup-Environment {
    Write-Info "Setting up environment..."
    
    try {
        # Create necessary directories
        $directories = @(
            "logs",
            "data",
            "cache",
            "ssl",
            "security",
            "monitoring",
            "haproxy",
            "nginx"
        )
        
        foreach ($dir in $directories) {
            if (!(Test-Path $dir)) {
                New-Item -ItemType Directory -Path $dir -Force | Out-Null
                Write-Info "Created directory: $dir"
            }
        }
        
        # Generate SSL certificates for development
        if ($Environment -eq "development") {
            if (!(Test-Path "ssl/cert.pem")) {
                Write-Info "Generating SSL certificates for development..."
                openssl req -x509 -newkey rsa:4096 -keyout ssl/key.pem -out ssl/cert.pem -days 365 -nodes -subj "/C=US/ST=State/L=City/O=Organization/CN=localhost"
            }
        }
        
        # Generate encryption key
        if (!(Test-Path "security/encryption.key")) {
            Write-Info "Generating encryption key..."
            $encryptionKey = [System.Convert]::ToBase64String([System.Security.Cryptography.RandomNumberGenerator]::GetBytes(32))
            Set-Content -Path "security/encryption.key" -Value $encryptionKey -Encoding ASCII
        }
        
        Write-Success "Environment setup completed"
    }
    catch {
        Write-Error "Environment setup failed: $_"
        exit 1
    }
}

# Function to deploy with Docker Compose
function Deploy-DockerCompose {
    Write-Info "Deploying with Docker Compose..."
    
    try {
        # Set environment variables
        $env:ENVIRONMENT = $Environment
        $env:REGION = $Region
        
        # Stop existing containers
        Write-Info "Stopping existing containers..."
        docker-compose -f deployment/multi_region.yml down
        
        # Start services
        Write-Info "Starting services..."
        docker-compose -f deployment/multi_region.yml up -d
        
        # Wait for services to be ready
        Write-Info "Waiting for services to be ready..."
        Start-Sleep -Seconds 30
        
        # Check service health
        Write-Info "Checking service health..."
        $healthCheck = Invoke-RestMethod -Uri "http://localhost/health" -Method Get -ErrorAction SilentlyContinue
        if ($healthCheck.status -eq "healthy") {
            Write-Success "Services are healthy"
        }
        else {
            Write-Warning "Services may not be fully ready yet"
        }
        
        Write-Success "Docker Compose deployment completed"
    }
    catch {
        Write-Error "Docker Compose deployment failed: $_"
        exit 1
    }
}

# Function to deploy to cloud (placeholder)
function Deploy-Cloud {
    Write-Info "Cloud deployment not implemented yet"
    Write-Warning "This would deploy to AWS ECS, Kubernetes, or other cloud platforms"
}

# Function to run health checks
function Invoke-HealthChecks {
    Write-Info "Running health checks..."
    
    try {
        $endpoints = @(
            "http://localhost/health",
            "http://localhost:8001/health",
            "http://localhost:8501/",
            "http://localhost:9090/-/healthy",
            "http://localhost:3000/api/health",
            "http://localhost:16686/",
            "http://localhost:8500/v1/status/leader"
        )
        
        foreach ($endpoint in $endpoints) {
            try {
                $response = Invoke-RestMethod -Uri $endpoint -Method Get -TimeoutSec 10
                Write-Success "✓ $endpoint"
            }
            catch {
                Write-Warning "✗ $endpoint - $_"
            }
        }
        
        Write-Success "Health checks completed"
    }
    catch {
        Write-Error "Health checks failed: $_"
    }
}

# Function to show deployment status
function Show-DeploymentStatus {
    Write-Info "=========================================="
    Write-Info "Deployment Status"
    Write-Info "=========================================="
    
    try {
        # Show running containers
        Write-Info "Running containers:"
        docker ps
        
        # Show service URLs
        Write-Info "Service URLs:"
        Write-Info "API: http://localhost:8001"
        Write-Info "Dashboard: http://localhost:8501"
        Write-Info "Load Balancer: http://localhost"
        Write-Info "Prometheus: http://localhost:9090"
        Write-Info "Grafana: http://localhost:3000"
        Write-Info "Jaeger: http://localhost:16686"
        Write-Info "Consul: http://localhost:8500"
        Write-Info "Vault: http://localhost:8200"
        Write-Info "Flower: http://localhost:5555"
        Write-Info "Kibana: http://localhost:5601"
        
        Write-Success "Deployment completed successfully!"
    }
    catch {
        Write-Error "Failed to show deployment status: $_"
    }
}

# Function to cleanup
function Invoke-Cleanup {
    Write-Info "Cleaning up..."
    
    try {
        # Remove old images
        docker image prune -f
        
        # Remove old containers
        docker container prune -f
        
        # Remove old volumes
        docker volume prune -f
        
        Write-Success "Cleanup completed"
    }
    catch {
        Write-Warning "Cleanup failed: $_"
    }
}

# Main deployment process
try {
    # Check prerequisites
    Test-Prerequisites
    
    # Run tests
    Invoke-Tests
    
    # Setup environment
    Setup-Environment
    
    # Build Docker images
    Build-DockerImages
    
    # Deploy based on environment
    if ($Environment -eq "production") {
        Deploy-Cloud
    }
    else {
        Deploy-DockerCompose
    }
    
    # Run health checks
    Invoke-HealthChecks
    
    # Show deployment status
    Show-DeploymentStatus
    
    # Cleanup
    Invoke-Cleanup
    
    Write-Success "Deployment completed successfully!"
}
catch {
    Write-Error "Deployment failed: $_"
    exit 1
}
finally {
    Write-Info "Deployment script finished"
}