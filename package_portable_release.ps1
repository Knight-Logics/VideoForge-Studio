$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot

$releaseRoot = Join-Path $PSScriptRoot 'release'
$stageDir = Join-Path $releaseRoot 'VideoForge-Studio-Portable'
$zipPath = Join-Path $releaseRoot 'VideoForge-Studio-Portable.zip'

if (Test-Path $stageDir) {
    Remove-Item $stageDir -Recurse -Force
}
if (Test-Path $zipPath) {
    Remove-Item $zipPath -Force
}

New-Item -ItemType Directory -Path $stageDir -Force | Out-Null

$itemsToCopy = @(
    'app.py',
    'wsgi.py',
    'requirements.txt',
    '.env.example',
    'README.md',
    'DOWNLOAD_AND_RUN.md',
    'USER_LOCAL_MODE.md',
    'install_local_user.ps1',
    'launch_local_user.ps1',
    'install_videoforge.bat',
    'start_videoforge.bat',
    'src',
    'static',
    'templates'
)

foreach ($item in $itemsToCopy) {
    if (Test-Path $item) {
        Copy-Item $item $stageDir -Recurse -Force
    }
}

if (-not (Test-Path $releaseRoot)) {
    New-Item -ItemType Directory -Path $releaseRoot -Force | Out-Null
}

Compress-Archive -Path (Join-Path $stageDir '*') -DestinationPath $zipPath -Force
Write-Host "Portable package created: $zipPath" -ForegroundColor Green
