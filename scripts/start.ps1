param([switch]$Dev)
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath (Split-Path -Parent $PSScriptRoot)
$sipakPython = Join-Path (Get-Location) '.venv-win\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $sipakPython)) { $sipakPython = Join-Path (Get-Location) '.venv\Scripts\python.exe' }
if (-not (Test-Path -LiteralPath $sipakPython)) { throw 'Buat virtual environment dan instal backend/requirements.txt terlebih dahulu. Lihat README.md.' }
if ($Dev) {
  & $sipakPython -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload
} else {
  if (-not (Test-Path -LiteralPath 'dist\index.html')) { throw 'Jalankan npm.cmd run build terlebih dahulu.' }
  & $sipakPython -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
}
