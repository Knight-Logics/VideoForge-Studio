$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot

$innoCompiler = 'C:\Program Files (x86)\Inno Setup 6\ISCC.exe'
if (-not (Test-Path $innoCompiler)) {
    Write-Host 'ISCC.exe not found. Install Inno Setup 6 first.' -ForegroundColor Yellow
    exit 1
}

$distExe = Join-Path $PSScriptRoot 'dist\VideoForge-Studio\VideoForge-Studio.exe'
if (-not (Test-Path $distExe)) {
    Write-Host 'EXE build not found. Building exe package first...' -ForegroundColor Cyan
    & .\package_windows_exe_release.ps1
}

& $innoCompiler 'VideoForge-Studio.iss'
Write-Host 'Inno Setup installer build complete.' -ForegroundColor Green
