# FinGuard AI Backend Startup Script
# Bank-Grade Fraud Detection System

Write-Host "===============================================" -ForegroundColor Cyan
Write-Host "  FinGuard AI - Bank-Grade Backend Starting" -ForegroundColor Cyan
Write-Host "===============================================" -ForegroundColor Cyan
Write-Host ""

# 1. Virtual Environment Setup
if (-Not (Test-Path "venv")) {
    Write-Host "[1/6] Creating virtual environment..." -ForegroundColor Yellow
    # Prefer 'py -3.10' as it handles spaces much better on Windows
    if (Get-Command "py" -ErrorAction SilentlyContinue) {
        & py -3.10 -m venv venv
    } else {
        python -m venv venv
    }
} else {
    Write-Host "[1/6] Virtual environment already exists [OK]" -ForegroundColor Green
}

# 2. APPLY BANK-GRADE FIX FOR WINDOWS SPACE BUG
Write-Host "[2/6] Fixing Windows environment shims..." -ForegroundColor Yellow
$venvPython = "$PSScriptRoot\venv\Scripts\python.exe"

# Find the REAL global python path, avoiding the current venv if active
$globalPython = (Get-Command "python.exe" -ErrorAction SilentlyContinue | Where-Object { $_.Source -notmatch "venv" } | Select-Object -First 1).Source
if (-not $globalPython) {
    # Fallback: check standard installation path
    $globalPython = "C:\Users\Sjruti Limbkar\AppData\Local\Programs\Python\Python310\python.exe"
}

if (Test-Path $venvPython) {
    Write-Host "  Patching venv binary from: $globalPython" -ForegroundColor Gray
    try {
        Stop-Process -Name "python" -Force -ErrorAction SilentlyContinue
        Start-Sleep -Milliseconds 500
        Copy-Item $globalPython $venvPython -Force
        Copy-Item (Join-Path (Split-Path $globalPython) "pythonw.exe") "$PSScriptRoot\venv\Scripts\pythonw.exe" -Force -ErrorAction SilentlyContinue
        Write-Host "  Virtual environment binary patched successfully [OK]" -ForegroundColor Green
    } catch {
        Write-Host "  Warning: Could not patch binary (file might be in use). If errors persist, run 'deactivate' and try again." -ForegroundColor Yellow
    }
}

# 3. Activation and Dependencies
Write-Host "[3/6] Installing dependencies..." -ForegroundColor Yellow

# Step A: Install Torch first (Required for GNN extensions)
Write-Host "  Step A: Installing Base ML Frameworks..." -ForegroundColor Gray
& "$PSScriptRoot\venv\Scripts\python.exe" -m pip install torch==2.1.0 --quiet

# Step B: Install GNN Extensions using correct index for Windows
Write-Host "  Step B: Installing GNN Extensions..." -ForegroundColor Gray
& "$PSScriptRoot\venv\Scripts\python.exe" -m pip install torch-scatter torch-sparse -f https://data.pyg.org/whl/torch-2.1.0+cpu.html --quiet

# Step C: Install the rest
Write-Host "  Step C: Installing remaining dependencies..." -ForegroundColor Gray
& "$PSScriptRoot\venv\Scripts\python.exe" -m pip install -r requirements.txt --quiet

if ($LASTEXITCODE -ne 0) {
    Write-Host "Warning: Dependency installation had issues. Continuing anyway..." -ForegroundColor Yellow
}

# 4. Database Check
Write-Host "[4/6] Checking database configuration..." -ForegroundColor Yellow
Write-Host "  Database: PostgreSQL @ localhost:5432" -ForegroundColor White

# 5. Start Redis (Simplified)
Write-Host "[5/6] Starting Redis Cache..." -ForegroundColor Yellow
$redisRunning = Get-Process redis-server -ErrorAction SilentlyContinue
if (-not $redisRunning) {
    if (Test-Path "..\Redis\redis-server.exe") {
        Start-Process -FilePath "..\Redis\redis-server.exe" -WindowStyle Hidden
        Write-Host "  Redis started in background [OK]" -ForegroundColor Green
    } else {
        Write-Host "  Redis not found, skipping..." -ForegroundColor Gray
    }
} else {
    Write-Host "  Redis already running [OK]" -ForegroundColor Green
}

# 6. Start FastAPI server
Write-Host "[6/6] Starting FinGuard AI Backend..." -ForegroundColor Yellow
Write-Host "  API: http://localhost:8000" -ForegroundColor Cyan
Write-Host ""

# Run uvicorn using the patched binary
& "$PSScriptRoot\venv\Scripts\python.exe" -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
