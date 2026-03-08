param(
    [switch]$SkipInstaller
)

$ErrorActionPreference = "Stop"

if (-not $IsWindows) {
    throw "build_windows.ps1 must be run on Windows. Building on Linux/macOS will produce binaries that cannot run on Windows."
}

Write-Host "[1/5] Creating virtual environment (optional)"
if (-not (Test-Path ".venv")) {
    py -3 -m venv .venv
}

$pythonExe = ".\.venv\Scripts\python.exe"
$pyInstallerExe = ".\.venv\Scripts\pyinstaller.exe"

Write-Host "[2/5] Installing build dependencies"
& $pythonExe -m pip install --upgrade pip
& $pythonExe -m pip install pyinstaller

Write-Host "[3/5] Building single-file app EXE"
& $pyInstallerExe --noconfirm --clean --onefile --windowed --name HyperSearch app.py

if (-not (Test-Path "dist\HyperSearch.exe")) {
    throw "Build failed: dist\\HyperSearch.exe was not created."
}

if ($SkipInstaller) {
    Write-Host "SkipInstaller specified. EXE available at dist\\HyperSearch.exe"
    $hash = (Get-FileHash "dist\HyperSearch.exe" -Algorithm SHA256).Hash
    Write-Host "SHA256 dist\\HyperSearch.exe: $hash"
    exit 0
}

Write-Host "[4/5] Building installer EXE with Inno Setup"
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

if (-not (Test-Path "dist_installer\HyperSearchInstaller.exe")) {
    throw "Installer build failed: dist_installer\\HyperSearchInstaller.exe was not created."
}

Write-Host "[5/5] Build complete"
Write-Host "Installer created at dist_installer\\HyperSearchInstaller.exe"
$installerHash = (Get-FileHash "dist_installer\HyperSearchInstaller.exe" -Algorithm SHA256).Hash
Write-Host "SHA256 dist_installer\\HyperSearchInstaller.exe: $installerHash"
Write-Host "Share only this installer with end users. They do NOT need Python installed."
