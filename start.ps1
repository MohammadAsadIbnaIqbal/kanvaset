$ErrorActionPreference = 'Stop'

# Get the absolute path to the kanvaset directory
$ProjectRoot = $PSScriptRoot
if (-not $ProjectRoot) {
    $ProjectRoot = (Get-Item .).FullName
}

Write-Host "Starting Kanvaset Project Servers..." -ForegroundColor Cyan

# 1. Start Backend
$BackendArgs = "-NoExit", "-Command", "uvicorn backend.app.main:app --reload --port 8080"
Start-Process powershell -ArgumentList $BackendArgs -WorkingDirectory $ProjectRoot
Write-Host "Started Backend on Port 8080" -ForegroundColor Green

# 2. Start Frontend
$FrontendArgs = "-NoExit", "-Command", "npm run dev"
Start-Process powershell -ArgumentList $FrontendArgs -WorkingDirectory "$ProjectRoot\frontend"
Write-Host "Started Frontend on Port 5173" -ForegroundColor Green

Write-Host "Both servers are running in separate windows!" -ForegroundColor Yellow
