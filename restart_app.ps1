# restart_app.ps1
# PowerShell script to restart the BTC Forecasting API

Write-Host "🔄 Restarting BTC Forecasting API..." -ForegroundColor Yellow

# Function to check if port is in use
function Test-Port {
    param([int]$Port)
    try {
        $connection = New-Object System.Net.Sockets.TcpClient
        $connection.Connect("127.0.0.1", $Port)
        $connection.Close()
        return $true
    }
    catch {
        return $false
    }
}

# Function to kill process using specific port
function Stop-ProcessOnPort {
    param([int]$Port)
    try {
        $processes = Get-NetTCPConnection -LocalPort $Port -ErrorAction SilentlyContinue | 
                    Where-Object {$_.State -eq "Listen"} | 
                    Select-Object -ExpandProperty OwningProcess
        foreach ($processId in $processes) {
            Stop-Process -Id $processId -Force -ErrorAction SilentlyContinue
            Write-Host "Killed process $processId using port $Port" -ForegroundColor Red
        }
    }
    catch {
        Write-Host "No processes found on port $Port" -ForegroundColor Yellow
    }
}

# Kill any existing uvicorn processes
Write-Host "Stopping existing processes..." -ForegroundColor Cyan
Get-Process -Name "python" -ErrorAction SilentlyContinue | Where-Object {$_.ProcessName -eq "python"} | Stop-Process -Force -ErrorAction SilentlyContinue

# Check and free port 8000
if (Test-Port -Port 8000) {
    Write-Host "Port 8000 is in use. Attempting to free it..." -ForegroundColor Yellow
    Stop-ProcessOnPort -Port 8000
    Start-Sleep -Seconds 3
}

# Wait a moment for processes to stop
Start-Sleep -Seconds 2

# Verify port is free
if (Test-Port -Port 8000) {
    Write-Host "❌ Port 8000 is still in use. Please manually stop the process using this port." -ForegroundColor Red
    Write-Host "You can use: netstat -ano | findstr :8000" -ForegroundColor Cyan
    exit 1
}

# Start the API server
Write-Host "Starting API server..." -ForegroundColor Green
try {
    python -m uvicorn api.main:app --host 127.0.0.1 --port 8000 --reload
}
catch {
    Write-Host "❌ Failed to start API server: $_" -ForegroundColor Red
    exit 1
}

Write-Host "✅ API server started successfully!" -ForegroundColor Green
Write-Host "🌐 API available at: http://127.0.0.1:8000" -ForegroundColor Cyan
Write-Host "📊 API Documentation at: http://127.0.0.1:8000/docs" -ForegroundColor Cyan 