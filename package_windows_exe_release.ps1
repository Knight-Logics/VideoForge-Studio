$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot

& .\build_windows_exe.ps1

$releaseRoot = Join-Path $PSScriptRoot 'release'
$exeZip = Join-Path $releaseRoot 'VideoForge-Studio-Windows-Exe.zip'
$distRoot = Join-Path $PSScriptRoot 'dist\VideoForge-Studio'

Start-Sleep -Seconds 3

if (-not (Test-Path $releaseRoot)) {
    New-Item -ItemType Directory -Path $releaseRoot -Force | Out-Null
}
if (Test-Path $exeZip) {
    Remove-Item $exeZip -Force
}

Compress-Archive -Path (Join-Path $distRoot '*') -DestinationPath $exeZip -Force
Write-Host "EXE release package created: $exeZip" -ForegroundColor Green
