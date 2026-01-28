$ErrorActionPreference = 'Stop'

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $root

if (!(Test-Path .\.venv\Scripts\python.exe)) {
  Write-Host "[ERROR] missing .venv" -ForegroundColor Red
  exit 1
}

.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements-exe.txt
.\.venv\Scripts\python.exe -m pip install pyinstaller

$dist = Join-Path $root 'dist'
$build = Join-Path $root 'build'
if (Test-Path $dist) { Remove-Item -Recurse -Force $dist }
if (Test-Path $build) { Remove-Item -Recurse -Force $build }

.\.venv\Scripts\pyinstaller.exe --noconfirm --clean --windowed `
  --name MimiStock `
  --icon assets\icon.ico `
  --add-data "THSarabunNew.ttf;." `
  --add-data "assets\db;assets\db" `
  --collect-all PyQt5 `
  --collect-submodules PyQt5 `
  main.py

Write-Host "OK: built dist\\MimiStock" -ForegroundColor Green
