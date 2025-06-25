# PowerShell Script to fully rebuild the environment and run the application
# This is a destructive operation that deletes the .venv folder.

# 1. Set script to exit on any error
$ErrorActionPreference = "Stop"

Write-Host "--- Starting Project Rebuild ---"

# 2. Check if a virtual environment directory exists
if (Test-Path -Path ".venv") {
    Write-Host "Existing virtual environment found. Removing it to ensure a clean slate..."
    try {
        Remove-Item -Path ".venv" -Recurse -Force
        Write-Host "Virtual environment removed successfully."
    } catch {
        Write-Error "Could not remove the .venv directory. Please close any terminals using it and delete it manually."
        exit 1
    }
}

# 3. Create a new virtual environment
Write-Host "Creating a new Python virtual environment..."
try {
    python -m venv .venv
    Write-Host "Virtual environment created."
} catch {
    Write-Error "Failed to create virtual environment. Make sure Python 3.7+ is installed and in your PATH."
    exit 1
}

# 4. Activate the virtual environment and install dependencies
Write-Host "Activating environment and installing dependencies from requirements.txt..."
try {
    # Activate and install in one block
    & .\.venv\Scripts\python.exe -m pip install -r requirements.txt
    Write-Host "Dependencies installed successfully."
} catch {
    Write-Error "Failed to install dependencies. Check requirements.txt and your internet connection."
    exit 1
}

# 5. Stop any existing process on port 8000
Write-Host "Checking for and stopping any process on port 8000..."
try {
    $process = Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($process) {
        Write-Host "Stopping existing process (ID: $($process.OwningProcess)) on port 8000."
        Stop-Process -Id $process.OwningProcess -Force
    }
} catch {
    # Non-critical, just warn
    Write-Warning "Could not check for processes on port 8000. This may be due to permissions."
}

# 6. Start the FastAPI backend in a new window
Write-Host "Starting FastAPI backend server in a new window..."
$backendCommand = ". .\.venv\Scripts\Activate.ps1; uvicorn api.main:app --host 127.0.0.1 --port 8000"
Start-Process powershell -ArgumentList "-NoExit", "-Command", $backendCommand

# Give the backend a moment to start
Start-Sleep -Seconds 5

# 7. Start the Streamlit frontend
Write-Host "Starting Streamlit frontend application..."
Write-Host "Your browser should open shortly."
& .\.venv\Scripts\streamlit.exe run app.py

Write-Host "--- Script Finished ---" 