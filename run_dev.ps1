$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot

# Resolve Python: prefer local .venv, then system PATH
$localPython = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
if (Test-Path $localPython) {
	$pythonExe = $localPython
} else {
	$pythonExe = 'python'
}

Write-Host "Starting VideoForge Studio (dev) ..."
& $pythonExe app.py
