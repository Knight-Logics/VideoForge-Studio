$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot

$pythonExe = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
if (-not (Test-Path $pythonExe)) {
    Write-Host 'Missing .venv. Create it first:' -ForegroundColor Yellow
    Write-Host '  py -3.12 -m venv .venv' -ForegroundColor Yellow
    Write-Host '  .\.venv\Scripts\python.exe -m pip install -r requirements.txt' -ForegroundColor Yellow
    exit 1
}

$cloudflaredCmd = Get-Command cloudflared -ErrorAction SilentlyContinue
$cloudflaredExe = if ($cloudflaredCmd) {
    $cloudflaredCmd.Source
} elseif (Test-Path 'C:\Program Files (x86)\cloudflared\cloudflared.exe') {
    'C:\Program Files (x86)\cloudflared\cloudflared.exe'
} else {
    $null
}

if (-not $cloudflaredExe) {
    Write-Host 'cloudflared is not installed or not on PATH.' -ForegroundColor Yellow
    Write-Host 'Install from: https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/downloads/' -ForegroundColor Yellow
    exit 1
}

Write-Host 'Starting VideoForge Studio locally on http://127.0.0.1:5050 ...' -ForegroundColor Cyan
$server = Start-Process -FilePath $pythonExe -ArgumentList '-m','waitress','--listen=127.0.0.1:5050','--max-request-body-size=4294967296','wsgi:app' -WorkingDirectory $PSScriptRoot -PassThru

Start-Sleep -Seconds 3

if ($server.HasExited) {
    Write-Host 'VideoForge server failed to start.' -ForegroundColor Red
    exit 1
}

Write-Host 'Starting free Cloudflare tunnel (temporary URL)...' -ForegroundColor Cyan
Write-Host 'Press Ctrl+C to stop the tunnel. Then stop the app process if needed.' -ForegroundColor Cyan

try {
    & $cloudflaredExe tunnel --url http://127.0.0.1:5050
}
finally {
    if (-not $server.HasExited) {
        Stop-Process -Id $server.Id -Force
    }
}
