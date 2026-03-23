$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot

$venvPython = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
if (-not (Test-Path $venvPython)) {
    Write-Host 'Missing .venv. Run .\install_local_user.ps1 first.' -ForegroundColor Yellow
    exit 1
}

& $venvPython -m pip install --upgrade pip
& $venvPython -m pip install -r requirements.txt
& $venvPython -m pip install pyinstaller

& $venvPython .\generate_app_icon.py

$ffmpegCmd = Get-Command ffmpeg -ErrorAction SilentlyContinue
$ffprobeCmd = Get-Command ffprobe -ErrorAction SilentlyContinue
if (-not $ffmpegCmd -or -not $ffprobeCmd) {
    Write-Host 'FFmpeg and ffprobe must be installed and available on PATH to build the exe package.' -ForegroundColor Yellow
    exit 1
}

if (Test-Path '.\build') { Remove-Item '.\build' -Recurse -Force }
if (Test-Path '.\dist') { Remove-Item '.\dist' -Recurse -Force }

& $venvPython -m PyInstaller --noconfirm --clean --windowed --onedir --name VideoForge-Studio --icon "static\app-icon.ico" --add-data "templates;templates" --add-data "static;static" --collect-all webview --hidden-import PySide6.QtWebEngineCore --hidden-import PySide6.QtWebEngineWidgets launcher.py

$distRoot = Join-Path $PSScriptRoot 'dist\VideoForge-Studio'
Copy-Item $ffmpegCmd.Source (Join-Path $distRoot 'ffmpeg.exe') -Force
Copy-Item $ffprobeCmd.Source (Join-Path $distRoot 'ffprobe.exe') -Force

foreach ($dir in @('workspace', 'workspace\uploads', 'workspace\jobs', 'workspace\outputs')) {
    New-Item -ItemType Directory -Path (Join-Path $distRoot $dir) -Force | Out-Null
}

$historyFile = Join-Path $distRoot 'workspace\render_history.json'
if (-not (Test-Path $historyFile)) {
    Set-Content -Path $historyFile -Value '{}' -Encoding UTF8
}

foreach ($file in @('.env.example', 'README.md', 'DOWNLOAD_AND_RUN.md')) {
    if (Test-Path $file) {
        Copy-Item $file $distRoot -Force
    }
}

Write-Host ''
Write-Host 'Executable build complete.' -ForegroundColor Green
Write-Host "Run: $distRoot\VideoForge-Studio.exe" -ForegroundColor Green
