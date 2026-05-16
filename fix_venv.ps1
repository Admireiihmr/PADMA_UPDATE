# PowerShell script to fix broken virtual environment and install dependencies

Write-Host "🔧 Fixing Virtual Environment..." -ForegroundColor Green
Write-Host ""

# Change to project directory
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptDir

# Deactivate current venv if active
if ($env:VIRTUAL_ENV) {
    Write-Host "Deactivating current virtual environment..." -ForegroundColor Cyan
    deactivate
}

# Remove broken .venv if it exists
if (Test-Path ".venv") {
    Write-Host "Removing broken virtual environment..." -ForegroundColor Yellow
    Remove-Item -Recurse -Force ".venv"
    Write-Host "✅ Removed broken .venv" -ForegroundColor Green
}

# Find Python executable
$pythonCmd = $null

# Try different Python locations
$pythonPaths = @(
    "C:\Users\Vinay\python",
    "python",
    "py",
    "python3"
)

foreach ($path in $pythonPaths) {
    try {
        if ($path -eq "C:\Users\Vinay\python") {
            if (Test-Path $path) {
                $version = & $path --version 2>&1
                if ($LASTEXITCODE -eq 0) {
                    $pythonCmd = $path
                    Write-Host "✅ Found Python at: $path ($version)" -ForegroundColor Green
                    break
                }
            }
        } else {
            $version = & $path --version 2>&1
            if ($LASTEXITCODE -eq 0) {
                $pythonCmd = $path
                Write-Host "✅ Found Python: $path ($version)" -ForegroundColor Green
                break
            }
        }
    } catch {
        # Continue to next option
    }
}

if (-not $pythonCmd) {
    Write-Host "❌ Could not find Python. Please install Python first." -ForegroundColor Red
    exit 1
}

# Create new virtual environment
Write-Host ""
Write-Host "Creating new virtual environment..." -ForegroundColor Cyan
& $pythonCmd -m venv .venv

if (-not (Test-Path ".venv\Scripts\Activate.ps1")) {
    Write-Host "❌ Failed to create virtual environment" -ForegroundColor Red
    exit 1
}

Write-Host "✅ Virtual environment created" -ForegroundColor Green

# Activate virtual environment
Write-Host ""
Write-Host "Activating virtual environment..." -ForegroundColor Cyan
& ".venv\Scripts\Activate.ps1"

# Upgrade pip
Write-Host ""
Write-Host "Upgrading pip..." -ForegroundColor Cyan
& $pythonCmd -m pip install --upgrade pip

# Install requirements
Write-Host ""
Write-Host "Installing requirements..." -ForegroundColor Cyan
& $pythonCmd -m pip install -r requirements.txt

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "✅ All dependencies installed successfully!" -ForegroundColor Green
    Write-Host ""
    Write-Host "You can now run: python api.py" -ForegroundColor Cyan
} else {
    Write-Host ""
    Write-Host "❌ Some packages failed to install. Check the errors above." -ForegroundColor Red
}

