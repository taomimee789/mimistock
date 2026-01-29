$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $root

# read version from app_version.py
$line = (Select-String -Path .\app_version.py -Pattern '^APP_VERSION\s*=') | Select-Object -First 1
if (-not $line) { throw 'APP_VERSION not found' }
$ver = ($line.Line -split '"')[1]

$zip = Join-Path $root ("MimiStock-$ver-win64.zip")
if (Test-Path $zip) { Remove-Item $zip -Force }

# zip contents of dist\MimiStock
$src = Join-Path $root 'dist\MimiStock\*'
Compress-Archive -Path $src -DestinationPath $zip

Write-Host "OK: $zip" -ForegroundColor Green
