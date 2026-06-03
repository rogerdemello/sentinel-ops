# Run SentinelOps backend + frontend for local development (Windows / PowerShell).
# Backend: uvicorn on :8000   Frontend: vite on :5173 (proxies /api -> :8000)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot

Write-Host "Starting SentinelOps backend (http://localhost:8000) ..." -ForegroundColor Cyan
$backend = Start-Process -PassThru -NoNewWindow -WorkingDirectory "$root\backend" `
    -FilePath "$root\backend\.venv\Scripts\python.exe" `
    -ArgumentList "-m", "uvicorn", "app.main:app", "--reload", "--port", "8000"

Write-Host "Starting SentinelOps frontend (http://localhost:5173) ..." -ForegroundColor Cyan
$frontend = Start-Process -PassThru -NoNewWindow -WorkingDirectory "$root\frontend" `
    -FilePath "npm" -ArgumentList "run", "dev"

Write-Host "`nSentinelOps running. Press Ctrl+C to stop both." -ForegroundColor Green
try {
    Wait-Process -Id $backend.Id, $frontend.Id
} finally {
    if (-not $backend.HasExited) { Stop-Process -Id $backend.Id -Force }
    if (-not $frontend.HasExited) { Stop-Process -Id $frontend.Id -Force }
}
