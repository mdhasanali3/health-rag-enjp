# Quick start script for Healthcare RAG Assistant (Windows)

Write-Host "==================================" -ForegroundColor Cyan
Write-Host "Healthcare RAG Quick Start" -ForegroundColor Cyan
Write-Host "==================================" -ForegroundColor Cyan
Write-Host ""

# Check Python
try {
    $pythonVersion = python --version
    Write-Host "✓ Found $pythonVersion" -ForegroundColor Green
}
catch {
    Write-Host "✗ Error: Python is not installed or not in PATH" -ForegroundColor Red
    exit 1
}

# Create virtual environment
if (-not (Test-Path "venv")) {
    Write-Host "Creating virtual environment..." -ForegroundColor Yellow
    python -m venv venv
    Write-Host "✓ Virtual environment created" -ForegroundColor Green
}

# Activate virtual environment
Write-Host "Activating virtual environment..." -ForegroundColor Yellow
& "venv\Scripts\Activate.ps1"

# Install dependencies
Write-Host "Installing dependencies (this may take a few minutes)..." -ForegroundColor Yellow
python -m pip install --upgrade pip --quiet
pip install -r requirements.txt --quiet
Write-Host "✓ Dependencies installed" -ForegroundColor Green

# Create .env if it doesn't exist
if (-not (Test-Path ".env")) {
    Write-Host "Creating .env file..." -ForegroundColor Yellow
    Copy-Item ".env.example" ".env"
    Write-Host "✓ .env file created (please update API_KEY)" -ForegroundColor Green
}

# Create data directory
if (-not (Test-Path "data")) {
    New-Item -ItemType Directory -Path "data" | Out-Null
}

Write-Host ""
Write-Host "==================================" -ForegroundColor Cyan
Write-Host "Setup Complete!" -ForegroundColor Green
Write-Host "==================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "To start the server:" -ForegroundColor Yellow
Write-Host "  venv\Scripts\Activate.ps1"
Write-Host "  python app\main.py"
Write-Host ""
Write-Host "Or with uvicorn:"
Write-Host "  uvicorn app.main:app --reload"
Write-Host ""
Write-Host "API will be available at:" -ForegroundColor Yellow
Write-Host "  http://localhost:8000"
Write-Host "  http://localhost:8000/docs (Interactive API docs)"
Write-Host ""
Write-Host "Sample documents are in: sample_documents\"
Write-Host ""
Write-Host "To test the API:" -ForegroundColor Yellow
Write-Host "  .\test_api.ps1"
Write-Host ""
