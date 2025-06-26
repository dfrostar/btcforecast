# Load Testing Script for BTC Forecast
# Runs different load test scenarios using Locust

param(
    [Parameter(Mandatory=$false)]
    [ValidateSet("light", "medium", "heavy", "stress", "spike")]
    [string]$Scenario = "medium",
    
    [Parameter(Mandatory=$false)]
    [string]$TargetHost = "http://localhost:8000",
    
    [Parameter(Mandatory=$false)]
    [int]$Users = 0,
    
    [Parameter(Mandatory=$false)]
    [int]$SpawnRate = 0,
    
    [Parameter(Mandatory=$false)]
    [string]$RunTime = "",
    
    [Parameter(Mandatory=$false)]
    [switch]$Headless,
    
    [Parameter(Mandatory=$false)]
    [switch]$Help
)

# Load test scenarios configuration
$Scenarios = @{
    "light" = @{
        Users = 10
        SpawnRate = 2
        RunTime = "5m"
        Description = "Light load - 10 users over 5 minutes"
    }
    "medium" = @{
        Users = 50
        SpawnRate = 5
        RunTime = "10m"
        Description = "Medium load - 50 users over 10 minutes"
    }
    "heavy" = @{
        Users = 100
        SpawnRate = 10
        RunTime = "15m"
        Description = "Heavy load - 100 users over 15 minutes"
    }
    "stress" = @{
        Users = 200
        SpawnRate = 20
        RunTime = "20m"
        Description = "Stress test - 200 users over 20 minutes"
    }
    "spike" = @{
        Users = 500
        SpawnRate = 50
        RunTime = "5m"
        Description = "Spike test - 500 users over 5 minutes"
    }
}

function Show-Help {
    Write-Host "BTC Forecast Load Testing Script" -ForegroundColor Green
    Write-Host "=================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "Usage:" -ForegroundColor Yellow
    Write-Host "  .\run_load_test.ps1 [Parameters]" -ForegroundColor White
    Write-Host ""
    Write-Host "Parameters:" -ForegroundColor Yellow
    Write-Host "  -Scenario <light|medium|heavy|stress|spike>" -ForegroundColor White
    Write-Host "    Predefined load test scenario (default: medium)" -ForegroundColor Gray
    Write-Host ""
    Write-Host "  -TargetHost <url>" -ForegroundColor White
    Write-Host "    Target host URL (default: http://localhost:8000)" -ForegroundColor Gray
    Write-Host ""
    Write-Host "  -Users <number>" -ForegroundColor White
    Write-Host "    Number of users (overrides scenario)" -ForegroundColor Gray
    Write-Host ""
    Write-Host "  -SpawnRate <number>" -ForegroundColor White
    Write-Host "    Users spawned per second (overrides scenario)" -ForegroundColor Gray
    Write-Host ""
    Write-Host "  -RunTime <duration>" -ForegroundColor White
    Write-Host "    Test duration (overrides scenario, e.g., 5m, 1h)" -ForegroundColor Gray
    Write-Host ""
    Write-Host "  -Headless" -ForegroundColor White
    Write-Host "    Run in headless mode without web UI" -ForegroundColor Gray
    Write-Host ""
    Write-Host "  -Help" -ForegroundColor White
    Write-Host "    Show this help message" -ForegroundColor Gray
    Write-Host ""
    Write-Host "Examples:" -ForegroundColor Yellow
    Write-Host "  .\run_load_test.ps1 -Scenario light" -ForegroundColor White
    Write-Host "  .\run_load_test.ps1 -Scenario heavy -TargetHost http://api.example.com" -ForegroundColor White
    Write-Host "  .\run_load_test.ps1 -Users 25 -SpawnRate 5 -RunTime 10m -Headless" -ForegroundColor White
    Write-Host ""
    Write-Host "Scenarios:" -ForegroundColor Yellow
    foreach ($scenario in $Scenarios.Keys) {
        $config = $Scenarios[$scenario]
        Write-Host "  $scenario`: $($config.Description)" -ForegroundColor White
    }
}

function Test-Prerequisites {
    Write-Host "Checking prerequisites..." -ForegroundColor Yellow
    
    # Check if Python is installed
    try {
        $pythonVersion = python --version 2>&1
        Write-Host "✓ Python found: $pythonVersion" -ForegroundColor Green
    }
    catch {
        Write-Host "✗ Python not found. Please install Python 3.8+" -ForegroundColor Red
        return $false
    }
    
    # Check if Locust is installed
    try {
        $locustVersion = locust --version 2>&1
        Write-Host "✓ Locust found: $locustVersion" -ForegroundColor Green
    }
    catch {
        Write-Host "✗ Locust not found. Installing..." -ForegroundColor Yellow
        try {
            pip install locust
            Write-Host "✓ Locust installed successfully" -ForegroundColor Green
        }
        catch {
            Write-Host "✗ Failed to install Locust" -ForegroundColor Red
            return $false
        }
    }
    
    # Check if load testing files exist
    if (-not (Test-Path "load_testing/locustfile.py")) {
        Write-Host "✗ Load testing file not found: load_testing/locustfile.py" -ForegroundColor Red
        return $false
    }
    
    Write-Host "✓ All prerequisites met" -ForegroundColor Green
    return $true
}

function Start-LoadTest {
    param(
        [string]$Scenario,
        [string]$TargetHost,
        [int]$Users,
        [int]$SpawnRate,
        [string]$RunTime,
        [bool]$Headless
    )
    
    # Get scenario configuration
    $config = $Scenarios[$Scenario]
    
    # Override with custom parameters if provided
    if ($Users -gt 0) { $config.Users = $Users }
    if ($SpawnRate -gt 0) { $config.SpawnRate = $SpawnRate }
    if ($RunTime -ne "") { $config.RunTime = $RunTime }
    
    Write-Host "Starting load test..." -ForegroundColor Green
    Write-Host "Scenario: $Scenario" -ForegroundColor Yellow
    Write-Host "Target: $TargetHost" -ForegroundColor Yellow
    Write-Host "Users: $($config.Users)" -ForegroundColor Yellow
    Write-Host "Spawn Rate: $($config.SpawnRate) users/sec" -ForegroundColor Yellow
    Write-Host "Duration: $($config.RunTime)" -ForegroundColor Yellow
    Write-Host "Headless: $Headless" -ForegroundColor Yellow
    Write-Host ""
    
    # Build Locust command
    $locustArgs = @(
        "--locustfile", "load_testing/locustfile.py",
        "--host", $TargetHost,
        "--users", $config.Users.ToString(),
        "--spawn-rate", $config.SpawnRate.ToString(),
        "--run-time", $config.RunTime
    )
    
    if ($Headless) {
        $locustArgs += @("--headless")
    }
    
    # Create results directory
    $timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
    $resultsDir = "load_testing/results/$timestamp"
    New-Item -ItemType Directory -Path $resultsDir -Force | Out-Null
    
    # Run the load test
    try {
        Write-Host "Running Locust with arguments: $($locustArgs -join ' ')" -ForegroundColor Cyan
        
        if ($Headless) {
            # Run in headless mode and save results
            $locustArgs += @("--csv", "$resultsDir/results")
            $process = Start-Process -FilePath "locust" -ArgumentList $locustArgs -Wait -PassThru -NoNewWindow
            
            if ($process.ExitCode -eq 0) {
                Write-Host "✓ Load test completed successfully" -ForegroundColor Green
                Write-Host "Results saved to: $resultsDir" -ForegroundColor Green
            }
            else {
                Write-Host "✗ Load test failed with exit code: $($process.ExitCode)" -ForegroundColor Red
            }
        }
        else {
            # Run with web UI
            Write-Host "Starting Locust web UI..." -ForegroundColor Cyan
            Write-Host "Open http://localhost:8089 in your browser" -ForegroundColor Yellow
            Write-Host "Press Ctrl+C to stop the test" -ForegroundColor Yellow
            Write-Host ""
            
            & locust @locustArgs
        }
    }
    catch {
        Write-Host "✗ Error running load test: $($_.Exception.Message)" -ForegroundColor Red
    }
}

function Show-PerformanceReport {
    param([string]$ResultsDir)
    
    if (-not (Test-Path $ResultsDir)) {
        Write-Host "No results found in: $ResultsDir" -ForegroundColor Yellow
        return
    }
    
    Write-Host "Performance Report" -ForegroundColor Green
    Write-Host "==================" -ForegroundColor Green
    Write-Host ""
    
    # Read CSV results
    $statsFile = Get-ChildItem -Path $ResultsDir -Filter "*.csv" | Select-Object -First 1
    if ($statsFile) {
        $stats = Import-Csv $statsFile.FullName
        $lastRow = $stats | Select-Object -Last 1
        
        Write-Host "Test Duration: $($lastRow.timestamp)" -ForegroundColor Yellow
        Write-Host "Total Requests: $($lastRow.num_requests)" -ForegroundColor Yellow
        Write-Host "Failed Requests: $($lastRow.num_failures)" -ForegroundColor Yellow
        Write-Host "Average Response Time: $([math]::Round($lastRow.avg_response_time, 2))ms" -ForegroundColor Yellow
        Write-Host "95th Percentile: $([math]::Round($lastRow.response_time_percentile_95, 2))ms" -ForegroundColor Yellow
        Write-Host "99th Percentile: $([math]::Round($lastRow.response_time_percentile_99, 2))ms" -ForegroundColor Yellow
        Write-Host "Requests/Second: $([math]::Round($lastRow.current_rps, 2))" -ForegroundColor Yellow
        Write-Host ""
        
        # Calculate error rate
        $errorRate = if ($lastRow.num_requests -gt 0) { 
            [math]::Round(($lastRow.num_failures / $lastRow.num_requests) * 100, 2) 
        } else { 0 }
        Write-Host "Error Rate: $errorRate%" -ForegroundColor $(if ($errorRate -gt 1) { "Red" } else { "Green" })
    }
}

# Main execution
if ($Help) {
    Show-Help
    exit 0
}

# Validate scenario
if (-not $Scenarios.ContainsKey($Scenario)) {
    Write-Host "✗ Invalid scenario: $Scenario" -ForegroundColor Red
    Write-Host "Valid scenarios: $($Scenarios.Keys -join ', ')" -ForegroundColor Yellow
    exit 1
}

# Check prerequisites
if (-not (Test-Prerequisites)) {
    Write-Host "✗ Prerequisites check failed" -ForegroundColor Red
    exit 1
}

# Start the load test
Start-LoadTest -Scenario $Scenario -TargetHost $TargetHost -Users $Users -SpawnRate $SpawnRate -RunTime $RunTime -Headless $Headless

# Show performance report if running in headless mode
if ($Headless) {
    $timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
    $resultsDir = "load_testing/results/$timestamp"
    Show-PerformanceReport -ResultsDir $resultsDir
} 