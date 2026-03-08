param(
    [switch]$SkipInstaller
)

$ErrorActionPreference = "Stop"

Write-Host "[1/4] Creating virtual environment (optional)"
if (-not (Test-Path ".venv")) {
    python -m venv .venv
}

Write-Host "[2/4] Installing build dependencies"
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install pyinstaller

Write-Host "[3/4] Building single-file app EXE"
.\.venv\Scripts\pyinstaller.exe --noconfirm --clean --onefile --windowed --name HyperSearch app.py

if ($SkipInstaller) {
    Write-Host "SkipInstaller specified. EXE available at dist\\HyperSearch.exe"
    exit 0
}

Write-Host "[4/4] Building installer EXE with Inno Setup"
$inno = "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe"
if (-not (Test-Path $inno)) {
    $inno = "${env:ProgramFiles}\Inno Setup 6\ISCC.exe"
}

if (-not (Test-Path $inno)) {
    Write-Warning "Inno Setup not found. Install from https://jrsoftware.org/isdl.php and rerun this script."
    Write-Host "Single-file app EXE is still ready at dist\\HyperSearch.exe"
    exit 0
}

& $inno installer\HyperSearch.iss
Write-Host "Installer created at dist_installer\\HyperSearchInstaller.exe"
