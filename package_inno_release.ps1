$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot

& .\package_windows_exe_release.ps1
& .\build_inno_installer.ps1

$installer = Join-Path $PSScriptRoot 'release\VideoForge-Studio-Installer.exe'
if (-not (Test-Path $installer)) {
    Write-Host 'Installer was not created.' -ForegroundColor Red
    exit 1
}

Get-Item $installer | Select-Object FullName,Length,LastWriteTime | Format-Table -AutoSize
