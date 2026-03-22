$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot

$pythonCmd = 'py -3.12'
$venvPython = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'

if (-not (Test-Path $venvPython)) {
    Write-Host 'Creating local virtual environment...' -ForegroundColor Cyan
    Invoke-Expression "$pythonCmd -m venv .venv"
}

Write-Host 'Installing Python dependencies...' -ForegroundColor Cyan
& $venvPython -m pip install --upgrade pip
& $venvPython -m pip install -r requirements.txt

Write-Host 'Checking FFmpeg availability...' -ForegroundColor Cyan
$ffmpeg = Get-Command ffmpeg -ErrorAction SilentlyContinue
if (-not $ffmpeg) {
    Write-Host 'FFmpeg was not found on PATH.' -ForegroundColor Yellow
    Write-Host 'Install FFmpeg and add it to PATH before rendering videos.' -ForegroundColor Yellow
    Write-Host 'Download: https://ffmpeg.org/download.html' -ForegroundColor Yellow
} else {
    Write-Host "FFmpeg found at: $($ffmpeg.Source)" -ForegroundColor Green
}

if (-not (Test-Path '.env') -and (Test-Path '.env.example')) {
    Copy-Item '.env.example' '.env'
    Write-Host 'Created .env from .env.example. Review settings before production use.' -ForegroundColor Cyan
}

Write-Host ''
Write-Host 'Local user mode setup complete.' -ForegroundColor Green
Write-Host 'Next step: run .\launch_local_user.ps1' -ForegroundColor Green
