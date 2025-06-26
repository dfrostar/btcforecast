#!/usr/bin/env pwsh

<#
.SYNOPSIS
    Deploy BTC Forecasting application to multi-region environment

.DESCRIPTION
    This script deploys the BTC Forecasting application across multiple regions
    with load balancing, monitoring, and health checks.

.PARAMETER Environment
    Target environment (dev, staging, production)

.PARAMETER Region
    Target region (us-east-1, us-west-2, eu-west-1, all)

.PARAMETER Action
    Deployment action (deploy, update, rollback, health-check, monitor)

.PARAMETER SkipHealthCheck
    Skip health checks during deployment

.PARAMETER Force
    Force deployment without confirmation

.EXAMPLE
    .\deploy_multi_region.ps1 -Environment production -Region all -Action deploy

.EXAMPLE
    .\deploy_multi_region.ps1 -Environment staging -Region us-east-1 -Action health-check
#>

param(
    [Parameter(Mandatory = $true)]
    [ValidateSet("dev", "staging", "production")]
    [string]$Environment,

    [Parameter(Mandatory = $true)]
    [ValidateSet("us-east-1", "us-west-2", "eu-west-1", "all")]
    [string]$Region,

    [Parameter(Mandatory = $true)]
    [ValidateSet("deploy", "update", "rollback", "health-check", "monitor", "backup", "restore")]
    [string]$Action,

    [switch]$SkipHealthCheck,
    [switch]$Force
)

# Configuration
$Config = @{
    Dev = @{
        DockerComposeFile = "deployment/multi_region.yml"
        EnvironmentFile = ".env.dev"
        Replicas = @{
            "api-server-us-east" = 1
            "api-server-us-west" = 1
            "api-server-eu-west" = 1
            "celery-worker-us-east" = 1
            "celery-worker-us-west" = 1
        }
    }
    Staging = @{
        DockerComposeFile = "deployment/multi_region.yml"
        EnvironmentFile = ".env.staging"
        Replicas = @{
            "api-server-us-east" = 2
            "api-server-us-west" = 1
            "api-server-eu-west" = 1
            "celery-worker-us-east" = 2
            "celery-worker-us-west" = 1
        }
    }
    Production = @{
        DockerComposeFile = "deployment/multi_region.yml"
        EnvironmentFile = ".env.production"
        Replicas = @{
            "api-server-us-east" = 3
            "api-server-us-west" = 2
            "api-server-eu-west" = 2
            "celery-worker-us-east" = 2
            "celery-worker-us-west" = 1
        }
    }
}

# Colors for output
$Colors = @{
    Info = "Cyan"
    Success = "Green"
    Warning = "Yellow"
    Error = "Red"
}

# Logging function
function Write-Log {
    param(
        [string]$Message,
        [string]$Level = "Info",
        [switch]$NoNewline
    )
    
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $color = $Colors[$Level]
    $prefix = "[$timestamp] [$Level]"
    
    if ($NoNewline) {
        Write-Host "$prefix $Message" -ForegroundColor $color -NoNewline
    } else {
        Write-Host "$prefix $Message" -ForegroundColor $color
    }
}

# Error handling
function Handle-Error {
    param(
        [string]$ErrorMessage,
        [int]$ExitCode = 1
    )
    
    Write-Log $ErrorMessage "Error"
    Write-Log "Deployment failed. Rolling back changes..." "Warning"
    
    # Rollback logic here
    if ($Action -eq "deploy" -or $Action -eq "update") {
        Invoke-Rollback
    }
    
    exit $ExitCode
}

# Health check function
function Test-HealthCheck {
    param(
        [string]$Service,
        [string]$Region,
        [int]$Timeout = 300
    )
    
    Write-Log "Performing health check for $Service in $Region..." "Info"
    
    $startTime = Get-Date
    $healthUrl = "http://localhost:8001/health"
    
    if ($Region -eq "us-west-2") {
        $healthUrl = "http://localhost:8002/health"
    } elseif ($Region -eq "eu-west-1") {
        $healthUrl = "http://localhost:8003/health"
    }
    
    do {
        try {
            $response = Invoke-WebRequest -Uri $healthUrl -TimeoutSec 10 -ErrorAction Stop
            if ($response.StatusCode -eq 200) {
                Write-Log "Health check passed for $Service in $Region" "Success"
                return $true
            }
        } catch {
            Write-Log "Health check failed for $Service in $Region. Retrying..." "Warning"
        }
        
        Start-Sleep -Seconds 5
        $elapsed = (Get-Date) - $startTime
    } while ($elapsed.TotalSeconds -lt $Timeout)
    
    Write-Log "Health check timeout for $Service in $Region" "Error"
    return $false
}

# Service discovery check
function Test-ServiceDiscovery {
    Write-Log "Checking service discovery..." "Info"
    
    try {
        $consulUrl = "http://localhost:8500/v1/agent/services"
        $response = Invoke-WebRequest -Uri $consulUrl -TimeoutSec 10
        $services = $response.Content | ConvertFrom-Json
        
        $expectedServices = @("api-server-us-east", "api-server-us-west", "api-server-eu-west")
        $missingServices = @()
        
        foreach ($service in $expectedServices) {
            if (-not $services.PSObject.Properties.Name.Contains($service)) {
                $missingServices += $service
            }
        }
        
        if ($missingServices.Count -gt 0) {
            Write-Log "Missing services in Consul: $($missingServices -join ', ')" "Warning"
            return $false
        }
        
        Write-Log "Service discovery check passed" "Success"
        return $true
    } catch {
        Write-Log "Service discovery check failed: $($_.Exception.Message)" "Error"
        return $false
    }
}

# Load balancer check
function Test-LoadBalancer {
    Write-Log "Checking load balancer health..." "Info"
    
    try {
        # Check Nginx
        $nginxUrl = "http://localhost/health"
        $response = Invoke-WebRequest -Uri $nginxUrl -TimeoutSec 10
        if ($response.StatusCode -eq 200) {
            Write-Log "Nginx load balancer is healthy" "Success"
        }
        
        # Check HAProxy
        $haproxyUrl = "http://localhost:8404/stats"
        $response = Invoke-WebRequest -Uri $haproxyUrl -TimeoutSec 10
        if ($response.StatusCode -eq 200) {
            Write-Log "HAProxy load balancer is healthy" "Success"
        }
        
        return $true
    } catch {
        Write-Log "Load balancer health check failed: $($_.Exception.Message)" "Error"
        return $false
    }
}

# Monitoring check
function Test-Monitoring {
    Write-Log "Checking monitoring stack..." "Info"
    
    $monitoringServices = @(
        @{Name = "Prometheus"; Url = "http://localhost:9090/-/healthy"},
        @{Name = "Grafana"; Url = "http://localhost:3000/api/health"},
        @{Name = "Jaeger"; Url = "http://localhost:16686/api/services"},
        @{Name = "Elasticsearch"; Url = "http://localhost:9200/_cluster/health"},
        @{Name = "Kibana"; Url = "http://localhost:5601/api/status"}
    )
    
    $failedServices = @()
    
    foreach ($service in $monitoringServices) {
        try {
            $response = Invoke-WebRequest -Uri $service.Url -TimeoutSec 10
            if ($response.StatusCode -eq 200) {
                Write-Log "$($service.Name) is healthy" "Success"
            } else {
                $failedServices += $service.Name
            }
        } catch {
            $failedServices += $service.Name
            Write-Log "$($service.Name) health check failed" "Warning"
        }
    }
    
    if ($failedServices.Count -gt 0) {
        Write-Log "Failed monitoring services: $($failedServices -join ', ')" "Warning"
        return $false
    }
    
    Write-Log "All monitoring services are healthy" "Success"
    return $true
}

# Database backup
function Invoke-Backup {
    Write-Log "Creating database backup..." "Info"
    
    try {
        $backupDir = "backups/$(Get-Date -Format 'yyyy-MM-dd_HH-mm-ss')"
        New-Item -ItemType Directory -Path $backupDir -Force | Out-Null
        
        # Backup PostgreSQL
        docker exec postgres-primary pg_dump -U btcforecast -d btcforecast > "$backupDir/database.sql"
        
        # Backup Redis
        docker exec redis-primary redis-cli --rdb /data/dump.rdb
        docker cp redis-primary:/data/dump.rdb "$backupDir/redis.rdb"
        
        # Backup configuration files
        Copy-Item "deployment/" "$backupDir/config/" -Recurse -Force
        
        Write-Log "Backup completed: $backupDir" "Success"
        return $backupDir
    } catch {
        Write-Log "Backup failed: $($_.Exception.Message)" "Error"
        return $null
    }
}

# Database restore
function Invoke-Restore {
    param(
        [string]$BackupPath
    )
    
    Write-Log "Restoring from backup: $BackupPath" "Info"
    
    try {
        # Restore PostgreSQL
        Get-Content "$BackupPath/database.sql" | docker exec -i postgres-primary psql -U btcforecast -d btcforecast
        
        # Restore Redis
        docker cp "$BackupPath/redis.rdb" redis-primary:/data/dump.rdb
        docker exec redis-primary redis-cli BGREWRITEAOF
        
        Write-Log "Restore completed successfully" "Success"
        return $true
    } catch {
        Write-Log "Restore failed: $($_.Exception.Message)" "Error"
        return $false
    }
}

# Rollback function
function Invoke-Rollback {
    Write-Log "Initiating rollback..." "Warning"
    
    try {
        # Stop current deployment
        docker-compose -f $Config[$Environment].DockerComposeFile down
        
        # Restore from latest backup
        $latestBackup = Get-ChildItem "backups/" | Sort-Object LastWriteTime -Descending | Select-Object -First 1
        if ($latestBackup) {
            Invoke-Restore -BackupPath $latestBackup.FullName
        }
        
        # Restart services
        docker-compose -f $Config[$Environment].DockerComposeFile up -d
        
        Write-Log "Rollback completed" "Success"
    } catch {
        Write-Log "Rollback failed: $($_.Exception.Message)" "Error"
    }
}

# Main deployment function
function Invoke-Deploy {
    param(
        [string]$TargetRegion
    )
    
    Write-Log "Starting deployment to $TargetRegion..." "Info"
    
    # Pre-deployment checks
    if (-not $SkipHealthCheck) {
        Write-Log "Running pre-deployment health checks..." "Info"
        
        if (-not (Test-ServiceDiscovery)) {
            Handle-Error "Service discovery check failed"
        }
        
        if (-not (Test-LoadBalancer)) {
            Handle-Error "Load balancer check failed"
        }
    }
    
    # Create backup before deployment
    if ($Environment -eq "production") {
        $backupPath = Invoke-Backup
        if (-not $backupPath) {
            Handle-Error "Failed to create backup"
        }
    }
    
    try {
        # Update replica counts for target region
        $composeFile = $Config[$Environment].DockerComposeFile
        $replicas = $Config[$Environment].Replicas
        
        # Deploy infrastructure services first
        Write-Log "Deploying infrastructure services..." "Info"
        docker-compose -f $composeFile up -d redis-primary postgres-primary prometheus grafana jaeger consul-server vault elasticsearch kibana
        
        # Wait for infrastructure to be ready
        Start-Sleep -Seconds 30
        
        # Deploy API servers
        Write-Log "Deploying API servers..." "Info"
        if ($TargetRegion -eq "all" -or $TargetRegion -eq "us-east-1") {
            docker-compose -f $composeFile up -d --scale api-server-us-east=$replicas["api-server-us-east"]
        }
        if ($TargetRegion -eq "all" -or $TargetRegion -eq "us-west-2") {
            docker-compose -f $composeFile up -d --scale api-server-us-west=$replicas["api-server-us-west"]
        }
        if ($TargetRegion -eq "all" -or $TargetRegion -eq "eu-west-1") {
            docker-compose -f $composeFile up -d --scale api-server-eu-west=$replicas["api-server-eu-west"]
        }
        
        # Deploy Celery workers
        Write-Log "Deploying Celery workers..." "Info"
        if ($TargetRegion -eq "all" -or $TargetRegion -eq "us-east-1") {
            docker-compose -f $composeFile up -d --scale celery-worker-us-east=$replicas["celery-worker-us-east"]
        }
        if ($TargetRegion -eq "all" -or $TargetRegion -eq "us-west-2") {
            docker-compose -f $composeFile up -d --scale celery-worker-us-west=$replicas["celery-worker-us-west"]
        }
        
        # Deploy load balancers
        Write-Log "Deploying load balancers..." "Info"
        docker-compose -f $composeFile up -d nginx haproxy
        
        # Wait for services to start
        Start-Sleep -Seconds 60
        
        # Post-deployment health checks
        if (-not $SkipHealthCheck) {
            Write-Log "Running post-deployment health checks..." "Info"
            
            $regions = if ($TargetRegion -eq "all") { @("us-east-1", "us-west-2", "eu-west-1") } else { @($TargetRegion) }
            
            foreach ($region in $regions) {
                if (-not (Test-HealthCheck -Service "api-server" -Region $region)) {
                    Handle-Error "Health check failed for $region"
                }
            }
            
            if (-not (Test-Monitoring)) {
                Write-Log "Monitoring check failed, but continuing..." "Warning"
            }
        }
        
        Write-Log "Deployment to $TargetRegion completed successfully" "Success"
        
    } catch {
        Handle-Error "Deployment failed: $($_.Exception.Message)"
    }
}

# Update function
function Invoke-Update {
    param(
        [string]$TargetRegion
    )
    
    Write-Log "Starting rolling update for $TargetRegion..." "Info"
    
    try {
        # Perform rolling update
        docker-compose -f $Config[$Environment].DockerComposeFile up -d --no-deps --build
        
        # Wait for update to complete
        Start-Sleep -Seconds 30
        
        # Health checks
        if (-not $SkipHealthCheck) {
            $regions = if ($TargetRegion -eq "all") { @("us-east-1", "us-west-2", "eu-west-1") } else { @($TargetRegion) }
            
            foreach ($region in $regions) {
                if (-not (Test-HealthCheck -Service "api-server" -Region $region)) {
                    Handle-Error "Health check failed after update for $region"
                }
            }
        }
        
        Write-Log "Update for $TargetRegion completed successfully" "Success"
        
    } catch {
        Handle-Error "Update failed: $($_.Exception.Message)"
    }
}

# Main execution
try {
    Write-Log "BTC Forecasting Multi-Region Deployment Script" "Info"
    Write-Log "Environment: $Environment" "Info"
    Write-Log "Region: $Region" "Info"
    Write-Log "Action: $Action" "Info"
    
    # Confirmation for production deployments
    if ($Environment -eq "production" -and -not $Force) {
        $confirmation = Read-Host "Are you sure you want to deploy to PRODUCTION? (yes/no)"
        if ($confirmation -ne "yes") {
            Write-Log "Deployment cancelled by user" "Warning"
            exit 0
        }
    }
    
    # Execute requested action
    switch ($Action) {
        "deploy" {
            Invoke-Deploy -TargetRegion $Region
        }
        "update" {
            Invoke-Update -TargetRegion $Region
        }
        "rollback" {
            Invoke-Rollback
        }
        "health-check" {
            $regions = if ($Region -eq "all") { @("us-east-1", "us-west-2", "eu-west-1") } else { @($Region) }
            foreach ($region in $regions) {
                Test-HealthCheck -Service "api-server" -Region $region
            }
            Test-ServiceDiscovery
            Test-LoadBalancer
            Test-Monitoring
        }
        "monitor" {
            Write-Log "Opening monitoring dashboards..." "Info"
            Start-Process "http://localhost:3000"  # Grafana
            Start-Process "http://localhost:16686" # Jaeger
            Write-Log "Monitoring dashboards opened" "Success"
        }
        "backup" {
            Invoke-Backup
        }
        "restore" {
            $backupPath = Read-Host "Enter backup path to restore from"
            if (Test-Path $backupPath) {
                Invoke-Restore -BackupPath $backupPath
            } else {
                Write-Log "Backup path not found: $backupPath" "Error"
            }
        }
    }
    
    Write-Log "Script execution completed successfully" "Success"
    
} catch {
    Write-Log "Script execution failed: $($_.Exception.Message)" "Error"
    exit 1
} 