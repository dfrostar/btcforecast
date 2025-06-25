# This script automates the setup and launch of the BTC Forecast application.

# Stop script on any error
$ErrorActionPreference = "Stop"

# 1. Change to the script's directory to ensure paths are correct
Push-Location (Split-Path -Path $MyInvocation.MyCommand.Path -Parent)
Write-Host "Changed directory to $(Get-Location)" -ForegroundColor Green

# [1] Check if conda is available
if (-not (Get-Command conda -ErrorAction SilentlyContinue)) {
    Write-Host "❌ Conda is not installed or not in PATH." -ForegroundColor Red
    exit 1
}

# [2] Activate environment if not already active
$envName = "btcforecast"
if ($env:CONDA_DEFAULT_ENV -ne $envName) {
    Write-Host "🔧 Activating conda environment: $envName" -ForegroundColor Yellow
    conda activate $envName
}

# 3. Upgrade pip and pre-install build dependencies
Write-Host "Upgrading pip and installing build tools..." -ForegroundColor Cyan
python -m pip install --upgrade pip
pip install wheel setuptools cython "numpy<2.0"
Write-Host "Build tools installed successfully." -ForegroundColor Green

# 4. Install dependencies from requirements.txt
Write-Host "Installing required packages from requirements.txt. This might take a few minutes..." -ForegroundColor Cyan
pip install -r requirements.txt
Write-Host "Dependencies installed successfully." -ForegroundColor Green

# 5. Kill any existing processes on ports 8000 and 8501
Write-Host "🔧 Checking and clearing ports..." -ForegroundColor Yellow

# Function to kill processes on a specific port
function Kill-ProcessOnPort {
    param([int]$Port)
    
    $connections = Get-NetTCPConnection -LocalPort $Port -ErrorAction SilentlyContinue
    if ($connections) {
        Write-Host "   ⚠️  Found processes on port $Port, killing them..." -ForegroundColor Yellow
        foreach ($connection in $connections) {
            try {
                $process = Get-Process -Id $connection.OwningProcess -ErrorAction SilentlyContinue
                if ($process) {
                    Write-Host "     🗑️  Killing process: $($process.ProcessName) (PID: $($process.Id))" -ForegroundColor Red
                    Stop-Process -Id $connection.OwningProcess -Force -ErrorAction SilentlyContinue
                }
            }
            catch {
                Write-Host "     ⚠️  Could not kill process on port $Port" -ForegroundColor Yellow
            }
        }
        Start-Sleep -Seconds 2
    } else {
        Write-Host "   ✅ Port $Port is free" -ForegroundColor Green
    }
}

# Kill processes on both ports
Kill-ProcessOnPort -Port 8000
Kill-ProcessOnPort -Port 8501

# 6. Check for model/scaler files (support both .pkl and .h5/.gz)
$hasPkl = (Test-Path "btc_model.pkl") -and (Test-Path "btc_scaler.pkl")
$hasH5 = (Test-Path "btc_model.h5") -and (Test-Path "btc_scaler.gz")
if (-not ($hasPkl -or $hasH5)) {
    Write-Host "❌ Model or scaler not found. Please run the training script first (train_agent.py or train_agent_enhanced.py)." -ForegroundColor Red
    exit 1
}

# Ensure logs and training_plots directories exist
if (!(Test-Path "logs")) {
    New-Item -ItemType Directory -Path "logs" | Out-Null
    Write-Host "📁 Created logs directory" -ForegroundColor Green
}
if (!(Test-Path "training_plots")) {
    New-Item -ItemType Directory -Path "training_plots" | Out-Null
    Write-Host "📁 Created training_plots directory" -ForegroundColor Green
}

# 7. Start the FastAPI backend server in a separate background process
Write-Host "\n🚀 Starting API on http://127.0.0.1:8000 ..." -ForegroundColor Green
$apiJob = Start-Job -ScriptBlock {
    Set-Location $using:PWD
    conda activate btcforecast
    python -m uvicorn api.main:app --host 127.0.0.1 --port 8000
}

# Wait a moment for the API to start
Start-Sleep -Seconds 3

# Check if API started successfully
$apiStatus = Get-Job -Id $apiJob.Id
if ($apiStatus.State -eq "Failed") {
    Write-Host "❌ API failed to start. Check the logs for details." -ForegroundColor Red
    Receive-Job -Id $apiJob.Id
    exit 1
}

Write-Host "✅ API server started successfully" -ForegroundColor Green

# 8. Start the Streamlit frontend application
Write-Host "\n🚀 Starting Streamlit frontend on http://localhost:8501" -ForegroundColor Green
Write-Host "Your application should open in your web browser shortly." -ForegroundColor Cyan

# Start Streamlit in a separate job
$streamlitJob = Start-Job -ScriptBlock {
    Set-Location $using:PWD
    conda activate btcforecast
    streamlit run app.py --server.port 8501 --server.address localhost
}

# Wait for Streamlit to start
Start-Sleep -Seconds 5

# Check if Streamlit started successfully
$streamlitStatus = Get-Job -Id $streamlitJob.Id
if ($streamlitStatus.State -eq "Failed") {
    Write-Host "❌ Streamlit failed to start. Check the logs for details." -ForegroundColor Red
    Receive-Job -Id $streamlitJob.Id
    exit 1
}

Write-Host "✅ Streamlit frontend started successfully" -ForegroundColor Green

# 9. Display application status
Write-Host "\n🎉 BTC Forecast Application is Running!" -ForegroundColor Green
Write-Host "📱 Frontend: http://localhost:8501" -ForegroundColor Cyan
Write-Host "🔧 Backend API: http://127.0.0.1:8000" -ForegroundColor Cyan
Write-Host "📊 API Docs: http://127.0.0.1:8000/docs" -ForegroundColor Cyan

# 10. Show summary of artifacts and logs
Write-Host "\n📦 Application Artifacts and Logs:" -ForegroundColor Cyan
$files = @(
    @{Name="btc_model.pkl"; Description="Trained model (fallback)"},
    @{Name="btc_model.h5"; Description="Trained model (Keras)"},
    @{Name="btc_scaler.pkl"; Description="Data scaler (fallback)"},
    @{Name="btc_scaler.gz"; Description="Data scaler (Keras)"},
    @{Name="btc_forecast.csv"; Description="Forecast predictions"},
    @{Name="training_results.json"; Description="Detailed results"},
    @{Name="training_metrics.csv"; Description="Training metrics"}
)
foreach ($file in $files) {
    if (Test-Path $file.Name) {
        $size = (Get-Item $file.Name).Length
        $sizeKB = [math]::Round($size / 1KB, 1)
        Write-Host "   ✅ $($file.Name) ($sizeKB KB) - $($file.Description)" -ForegroundColor Green
    } else {
        Write-Host "   ❌ $($file.Name) - $($file.Description)" -ForegroundColor Yellow
    }
}

# Show latest log file
$logFiles = Get-ChildItem "logs" -Filter "*.log" | Sort-Object LastWriteTime -Descending
if ($logFiles.Count -gt 0) {
    Write-Host "\n📋 Latest Log File: $($logFiles[0].Name)" -ForegroundColor Cyan
    Write-Host "   Size: $([math]::Round($logFiles[0].Length / 1KB, 1)) KB" -ForegroundColor White
    Write-Host "   Created: $($logFiles[0].LastWriteTime)" -ForegroundColor White
}

# Show available training plots
$plotFiles = Get-ChildItem "training_plots" -Filter "*.png" | Sort-Object LastWriteTime -Descending
if ($plotFiles.Count -gt 0) {
    Write-Host "\n📊 Training Visualizations:" -ForegroundColor Cyan
    foreach ($plot in $plotFiles) {
        $sizeKB = [math]::Round($plot.Length / 1KB, 1)
        Write-Host "   [PLOT] $($plot.Name) ($sizeKB KB)" -ForegroundColor Green
    }
}

Write-Host "\n[READY] Application is ready! Open http://localhost:8501 in your browser." -ForegroundColor Green
Write-Host "[TIP] Press Ctrl+C to stop the application when you're done." -ForegroundColor Yellow

# 11. Keep the script running and monitor the jobs
try {
    while ($true) {
        $apiStatus = Get-Job -Id $apiJob.Id -ErrorAction SilentlyContinue
        $streamlitStatus = Get-Job -Id $streamlitJob.Id -ErrorAction SilentlyContinue
        
        if (-not $apiStatus -or $apiStatus.State -eq "Failed") {
            Write-Host "❌ API server stopped unexpectedly" -ForegroundColor Red
            break
        }
        
        if (-not $streamlitStatus -or $streamlitStatus.State -eq "Failed") {
            Write-Host "❌ Streamlit frontend stopped unexpectedly" -ForegroundColor Red
            break
        }
        
        Start-Sleep -Seconds 10
    }
}
catch {
    Write-Host "\n[STOP] Application stopped by user" -ForegroundColor Yellow
}
finally {
    # Clean up jobs
    if ($apiJob) {
        Stop-Job -Id $apiJob.Id -ErrorAction SilentlyContinue
        Remove-Job -Id $apiJob.Id -ErrorAction SilentlyContinue
    }
    if ($streamlitJob) {
        Stop-Job -Id $streamlitJob.Id -ErrorAction SilentlyContinue
        Remove-Job -Id $streamlitJob.Id -ErrorAction SilentlyContinue
    }
    
    # Return to original directory
    Pop-Location
    Write-Host "\n🏁 Script completed. Returning to original directory." -ForegroundColor Green
} 