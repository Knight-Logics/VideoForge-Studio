$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot

$venvPython = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
if (-not (Test-Path $venvPython)) {
    Write-Host 'Missing .venv. Run .\install_local_user.ps1 first.' -ForegroundColor Yellow
    exit 1
}

Write-Host 'Starting VideoForge Studio in local user mode...' -ForegroundColor Cyan
& $venvPython .\launcher.py
