# Setup Script for Telemetry-Aware Model Monitoring System
# Run this script to set up the entire system

Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "  Telemetry-Aware Model Monitoring System - Setup" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

# Check Python installation
Write-Host "[1/6] Checking Python installation..." -ForegroundColor Yellow
try {
    $pythonVersion = python --version 2>&1
    Write-Host "  ✓ Found: $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "  ✗ Python not found! Please install Python 3.8 or higher." -ForegroundColor Red
    Write-Host "    Download from: https://www.python.org/downloads/" -ForegroundColor Red
    exit 1
}

# Create virtual environment
Write-Host ""
Write-Host "[2/6] Creating virtual environment..." -ForegroundColor Yellow
if (Test-Path "venv") {
    Write-Host "  ⚠ Virtual environment already exists. Skipping..." -ForegroundColor Yellow
} else {
    python -m venv venv
    if ($?) {
        Write-Host "  ✓ Virtual environment created" -ForegroundColor Green
    } else {
        Write-Host "  ✗ Failed to create virtual environment" -ForegroundColor Red
        exit 1
    }
}

# Activate virtual environment
Write-Host ""
Write-Host "[3/6] Activating virtual environment..." -ForegroundColor Yellow
& ".\venv\Scripts\Activate.ps1"
if ($?) {
    Write-Host "  ✓ Virtual environment activated" -ForegroundColor Green
} else {
    Write-Host "  ⚠ Note: If you get execution policy errors, run:" -ForegroundColor Yellow
    Write-Host "    Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser" -ForegroundColor Yellow
}

# Install dependencies
Write-Host ""
Write-Host "[4/6] Installing dependencies..." -ForegroundColor Yellow
Write-Host "  This may take 2-3 minutes..." -ForegroundColor Cyan
pip install -r requirements.txt --quiet
if ($?) {
    Write-Host "  ✓ All dependencies installed" -ForegroundColor Green
} else {
    Write-Host "  ✗ Failed to install dependencies" -ForegroundColor Red
    exit 1
}

# Setup environment file
Write-Host ""
Write-Host "[5/6] Setting up environment file..." -ForegroundColor Yellow
if (Test-Path ".env") {
    Write-Host "  ⚠ .env file already exists. Skipping..." -ForegroundColor Yellow
} else {
    Copy-Item ".env.example" ".env"
    Write-Host "  ✓ .env file created from template" -ForegroundColor Green
    Write-Host "  ⓘ Edit .env to add your OpenAI API key (optional for demo)" -ForegroundColor Cyan
}

# Initialize database
Write-Host ""
Write-Host "[6/6] Initializing database..." -ForegroundColor Yellow
python -c "from src.database import init_database; init_database()"
if ($?) {
    Write-Host "  ✓ Database initialized" -ForegroundColor Green
} else {
    Write-Host "  ✗ Failed to initialize database" -ForegroundColor Red
    exit 1
}

# Success message
Write-Host ""
Write-Host "============================================================" -ForegroundColor Green
Write-Host "  ✓ Setup completed successfully!" -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Green
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Cyan
Write-Host ""
Write-Host "  1. Run the demo:" -ForegroundColor White
Write-Host "     python examples\demo.py" -ForegroundColor Yellow
Write-Host ""
Write-Host "  2. Launch the dashboard:" -ForegroundColor White
Write-Host "     streamlit run dashboard\app.py" -ForegroundColor Yellow
Write-Host ""
Write-Host "  3. Explore the tutorial:" -ForegroundColor White
Write-Host "     jupyter notebook examples\tutorial.ipynb" -ForegroundColor Yellow
Write-Host ""
Write-Host "  4. Read the documentation:" -ForegroundColor White
Write-Host "     • README.md - Complete guide" -ForegroundColor Yellow
Write-Host "     • QUICKSTART.md - Quick start guide" -ForegroundColor Yellow
Write-Host "     • docs\ARCHITECTURE.md - Technical details" -ForegroundColor Yellow
Write-Host "     • docs\FAQ.md - Common questions" -ForegroundColor Yellow
Write-Host ""
Write-Host "For help: See README.md or QUICKSTART.md" -ForegroundColor Cyan
Write-Host ""
Write-Host "Good luck with your project! 🚀" -ForegroundColor Green
Write-Host ""
