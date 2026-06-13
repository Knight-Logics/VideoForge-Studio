$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot

$maxUploadMb = 4096
$appHost = '127.0.0.1'
$appPort = 5055
$envFile = Join-Path $PSScriptRoot '.env'
if (Test-Path $envFile) {
	Get-Content $envFile | ForEach-Object {
		$line = $_.Trim()
		if (-not $line -or $line.StartsWith('#')) {
			return
		}
		$parts = $line -split '=', 2
		if ($parts.Length -eq 2) {
			$key = $parts[0].Trim()
			$value = $parts[1].Trim()

			if ($key -eq 'MAX_UPLOAD_MB') {
				$parsed = 0
				if ([int]::TryParse($value, [ref]$parsed) -and $parsed -gt 0) {
					$maxUploadMb = $parsed
				}
			}

			if ($key -eq 'APP_HOST' -and $value) {
				$appHost = $value
			}

			if (($key -eq 'APP_PORT' -or $key -eq 'PORT') -and $value) {
				$parsedPort = 0
				if ([int]::TryParse($value, [ref]$parsedPort) -and $parsedPort -gt 0) {
					$appPort = $parsedPort
				}
			}
		}
	}
}

$maxRequestBodySize = $maxUploadMb * 1024 * 1024

# Resolve Python: prefer local .venv → shared dev venv → system PATH
$localPython = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
if (Test-Path $localPython) {
	$pythonExe = $localPython
} else {
	$pythonExe = 'python'
}

Write-Host "Starting VideoForge Studio on http://${appHost}:${appPort} ..."
& $pythonExe -m waitress --listen=${appHost}:${appPort} --max-request-body-size=$maxRequestBodySize wsgi:app
