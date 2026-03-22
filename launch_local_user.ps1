$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot

$venvPython = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
if (-not (Test-Path $venvPython)) {
    Write-Host 'Missing .venv. Run .\install_local_user.ps1 first.' -ForegroundColor Yellow
    exit 1
}

$url = 'http://127.0.0.1:5050'
Write-Host "Starting VideoForge Studio in local user mode at $url" -ForegroundColor Cyan
Start-Process $url | Out-Null

& $venvPython -m waitress --listen=127.0.0.1:5050 --max-request-body-size=4294967296 wsgi:app
