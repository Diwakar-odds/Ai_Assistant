# install.ps1 - PULSAR AI Assistant Setup Script (Windows)
#
# Usage: .\install.ps1
#
# This script sets up the development environment:
#   - Creates a Python virtual environment
#   - Installs Python dependencies
#   - Installs Node.js frontend dependencies
#   - Creates .env from .env.example if not present

$ErrorActionPreference = "Stop"

Write-Host "===================================================" -ForegroundColor Cyan
Write-Host "    PULSAR AI Assistant - Setup" -ForegroundColor Cyan
Write-Host "===================================================" -ForegroundColor Cyan
Write-Host ""

# Change to the directory of this script
Set-Location -Path $PSScriptRoot

# --- Check for Python ---
Write-Host "[1/5] Checking Python..." -ForegroundColor Yellow
$pythonCmd = $null
if (Get-Command python -ErrorAction SilentlyContinue) {
    $pythonCmd = "python"
} elseif (Get-Command python3 -ErrorAction SilentlyContinue) {
    $pythonCmd = "python3"
} else {
    Write-Host "[ERROR] Python is not installed or not in PATH." -ForegroundColor Red
    exit 1
}
$pyVersion = & $pythonCmd --version 2>&1
Write-Host "  Found: $pyVersion"

# --- Check for Node.js ---
Write-Host "[2/5] Checking Node.js..." -ForegroundColor Yellow
if (-not (Get-Command node -ErrorAction SilentlyContinue)) {
    Write-Host "[ERROR] Node.js is not installed or not in PATH." -ForegroundColor Red
    exit 1
}
$nodeVersion = node --version 2>&1
Write-Host "  Found: $nodeVersion"

# --- Create virtual environment ---
Write-Host "[3/5] Setting up Python virtual environment..." -ForegroundColor Yellow
if (-not (Test-Path ".venv\Scripts\activate.bat")) {
    Write-Host "  Creating .venv..."
    & $pythonCmd -m venv .venv
} else {
    Write-Host "  Virtual environment already exists."
}

# Activate the virtual environment
& .\.venv\Scripts\Activate.ps1

# --- Install Python dependencies ---
Write-Host "[4/5] Installing Python dependencies..." -ForegroundColor Yellow
$requirementsPath = "config\requirements\requirements.txt"
if (Test-Path $requirementsPath) {
    pip install -r $requirementsPath --quiet
    Write-Host "  Python dependencies installed."
} else {
    Write-Host "  [WARN] requirements.txt not found at $requirementsPath" -ForegroundColor DarkYellow
}

# --- Install frontend dependencies ---
Write-Host "[5/5] Installing frontend dependencies..." -ForegroundColor Yellow
$frontendPath = "frontend\web-app"
if (Test-Path "$frontendPath\package.json") {
    Push-Location $frontendPath
    npm install --silent
    Pop-Location
    Write-Host "  Frontend dependencies installed."
} else {
    Write-Host "  [WARN] Frontend package.json not found at $frontendPath" -ForegroundColor DarkYellow
}

# --- Create .env if not present ---
if (-not (Test-Path ".env")) {
    Write-Host ""
    Write-Host "Creating .env from .env.example..." -ForegroundColor Yellow
    if (Test-Path "config\.env.example") {
        Copy-Item "config\.env.example" ".env"
        Write-Host "  .env created. Edit it to set your API keys and admin password."
    }
}

Write-Host ""
Write-Host "===================================================" -ForegroundColor Green
Write-Host "    Setup Complete!" -ForegroundColor Green
Write-Host "===================================================" -ForegroundColor Green
Write-Host ""
Write-Host "To start the assistant, run: .\start.bat"
Write-Host ""
