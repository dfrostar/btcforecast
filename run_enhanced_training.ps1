# Enhanced BTC Training Runner with Monitoring
# ============================================
# This script runs the enhanced training agent with comprehensive monitoring

# Stop script on any error
$ErrorActionPreference = "Stop"

# Change to the script's directory
Push-Location (Split-Path -Path $MyInvocation.MyCommand.Path -Parent)
Write-Host "Changed directory to $(Get-Location)" -ForegroundColor Green

# Check if conda is available
if (-not (Get-Command conda -ErrorAction SilentlyContinue)) {
    Write-Host "❌ Conda is not installed or not in PATH." -ForegroundColor Red
    exit 1
}

# Activate environment
$envName = "btcforecast"
if ($env:CONDA_DEFAULT_ENV -ne $envName) {
    Write-Host "🔧 Activating conda environment: $envName" -ForegroundColor Yellow
    conda activate $envName
}

# Check system resources before training
Write-Host "📊 Checking system resources..." -ForegroundColor Cyan
$cpuUsage = Get-Counter "\Processor(_Total)\% Processor Time" | Select-Object -ExpandProperty CounterSamples | Select-Object -ExpandProperty CookedValue
$memory = Get-Counter "\Memory\Available MBytes" | Select-Object -ExpandProperty CounterSamples | Select-Object -ExpandProperty CookedValue
$totalMemory = Get-Counter "\Memory\Committed Bytes" | Select-Object -ExpandProperty CounterSamples | Select-Object -ExpandProperty CookedValue

Write-Host "   CPU Usage: $([math]::Round($cpuUsage, 1))%" -ForegroundColor White
Write-Host "   Available Memory: $([math]::Round($memory, 0)) MB" -ForegroundColor White
Write-Host "   Total Committed Memory: $([math]::Round($totalMemory/1MB, 0)) MB" -ForegroundColor White

# Check if required packages are installed
Write-Host "🔍 Checking required packages..." -ForegroundColor Cyan
$requiredPackages = @("tensorflow", "pandas", "numpy", "scikit-learn", "ta", "matplotlib", "seaborn", "tqdm", "psutil")
$missingPackages = @()

foreach ($package in $requiredPackages) {
    try {
        python -c "import $package" 2>$null
        Write-Host "   ✅ $package" -ForegroundColor Green
    }
    catch {
        Write-Host "   ❌ $package" -ForegroundColor Red
        $missingPackages += $package
    }
}

if ($missingPackages.Count -gt 0) {
    Write-Host "⚠️  Missing packages: $($missingPackages -join ', ')" -ForegroundColor Yellow
    Write-Host "Installing missing packages..." -ForegroundColor Yellow
    pip install $missingPackages
}

# Install additional dependencies
pip install -r requirements.txt

# Create logs directory if it doesn't exist
if (!(Test-Path "logs")) {
    New-Item -ItemType Directory -Path "logs" | Out-Null
    Write-Host "📁 Created logs directory" -ForegroundColor Green
}

# Create training_plots directory if it doesn't exist
if (!(Test-Path "training_plots")) {
    New-Item -ItemType Directory -Path "training_plots" | Out-Null
    Write-Host "📁 Created training_plots directory" -ForegroundColor Green
}

# Display training configuration
Write-Host "`n🎯 Training Configuration:" -ForegroundColor Cyan
Write-Host "   Lookback Period: 30 days" -ForegroundColor White
Write-Host "   Training Epochs: 20" -ForegroundColor White
Write-Host "   Batch Size: 32" -ForegroundColor White
Write-Host "   Forecast Period: 30 days" -ForegroundColor White
Write-Host "   Technical Indicators: RSI, MACD, Bollinger Bands, OBV, Ichimoku Cloud" -ForegroundColor White

# Start training with enhanced monitoring
Write-Host "`n🚀 Starting Enhanced BTC Training..." -ForegroundColor Green
Write-Host "📈 This will include:" -ForegroundColor Yellow
Write-Host "   • Real-time progress bars" -ForegroundColor White
Write-Host "   • Detailed logging to logs/ directory" -ForegroundColor White
Write-Host "   • Training visualizations in training_plots/" -ForegroundColor White
Write-Host "   • Resource usage monitoring" -ForegroundColor White
Write-Host "   • Comprehensive metrics tracking" -ForegroundColor White
Write-Host "   • Email notifications (if configured)" -ForegroundColor White

Write-Host "`n⏱️  Training started at: $(Get-Date)" -ForegroundColor Cyan
$startTime = Get-Date

# Run the enhanced training script
try {
    python train_agent_enhanced.py
    
    $endTime = Get-Date
    $duration = $endTime - $startTime
    
    Write-Host "`n✅ Training completed successfully!" -ForegroundColor Green
    Write-Host "⏱️  Total training time: $($duration.ToString('hh\:mm\:ss'))" -ForegroundColor Cyan
    
    # Check for generated files
    Write-Host "`n📁 Generated Files:" -ForegroundColor Cyan
    $files = @(
        @{Name="btc_model.pkl"; Description="Trained model"},
        @{Name="btc_scaler.pkl"; Description="Data scaler"},
        @{Name="btc_forecast.csv"; Description="Price predictions"},
        @{Name="training_results.json"; Description="Detailed results"},
        @{Name="training_metrics.csv"; Description="Training metrics"}
    )
    
    foreach ($file in $files) {
        if (Test-Path $file.Name) {
            $size = (Get-Item $file.Name).Length
            $sizeKB = [math]::Round($size / 1KB, 1)
            Write-Host "   ✅ $($file.Name) ($sizeKB KB) - $($file.Description)" -ForegroundColor Green
        } else {
            Write-Host "   ❌ $($file.Name) - $($file.Description)" -ForegroundColor Red
        }
    }
    
    # Check for log files
    $logFiles = Get-ChildItem "logs" -Filter "*.log" | Sort-Object LastWriteTime -Descending
    if ($logFiles.Count -gt 0) {
        Write-Host "`n📋 Latest Log File: $($logFiles[0].Name)" -ForegroundColor Cyan
        Write-Host "   Size: $([math]::Round($logFiles[0].Length / 1KB, 1)) KB" -ForegroundColor White
        Write-Host "   Created: $($logFiles[0].LastWriteTime)" -ForegroundColor White
    }
    
    # Check for training plots
    $plotFiles = Get-ChildItem "training_plots" -Filter "*.png" | Sort-Object LastWriteTime -Descending
    if ($plotFiles.Count -gt 0) {
        Write-Host "`n📊 Training Visualizations:" -ForegroundColor Cyan
        foreach ($plot in $plotFiles) {
            $sizeKB = [math]::Round($plot.Length / 1KB, 1)
            Write-Host "   📈 $($plot.Name) ($sizeKB KB)" -ForegroundColor Green
        }
    }
    
    # Display training summary if available
    if (Test-Path "training_results.json") {
        Write-Host "`n📊 Training Summary:" -ForegroundColor Cyan
        $results = Get-Content "training_results.json" | ConvertFrom-Json
        Write-Host "   Validation MAE: $($results.mae)" -ForegroundColor White
        Write-Host "   Validation R²: $($results.r2)" -ForegroundColor White
        Write-Host "   Training Duration: $([math]::Round($results.duration_seconds / 60, 1)) minutes" -ForegroundColor White
    }
    
    Write-Host "`n🎯 Training completed! Ready to run the application." -ForegroundColor Green
    Write-Host "💡 Run './run_app.ps1' to start the web application" -ForegroundColor Yellow
    
} catch {
    Write-Host "`n❌ Training failed with error: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host "📋 Check the logs directory for detailed error information" -ForegroundColor Yellow
    exit 1
}

# Return to original directory
Pop-Location
Write-Host "`n🏁 Script completed. Returning to original directory." -ForegroundColor Green 