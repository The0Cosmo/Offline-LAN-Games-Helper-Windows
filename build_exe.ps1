<#
.SYNOPSIS
    Build Offline LAN Games Helper as a Windows .exe.

.DESCRIPTION
    Creates/uses a local virtual environment, installs build dependencies,
    generates the app icon, runs PyInstaller, and copies editable runtime
    data files beside the final executable in dist.
#>

[CmdletBinding()]
param(
    [switch]$Clean
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Venv = Join-Path $Root '.venv'
$Python = Join-Path $Venv 'Scripts\python.exe'
$Dist = Join-Path $Root 'dist'
$Build = Join-Path $Root 'build'
$Spec = Join-Path $Root 'Offline LAN Games Helper.spec'
$Icon = Join-Path $Root 'assets\offline_lan_helper.ico'

Set-Location $Root

if ($Clean) {
    if (Test-Path -LiteralPath $Build) {
        Remove-Item -LiteralPath $Build -Recurse -Force
    }
    if (Test-Path -LiteralPath $Dist) {
        Remove-Item -LiteralPath $Dist -Recurse -Force
    }
    if (Test-Path -LiteralPath $Spec) {
        Remove-Item -LiteralPath $Spec -Force
    }
}

if (-not (Test-Path -LiteralPath $Python)) {
    python -m venv $Venv
}

& $Python -m pip install --upgrade pip
& $Python -m pip install pyinstaller pillow

& $Python .\make_icon.py

if (-not (Test-Path -LiteralPath $Icon)) {
    throw "Icon was not generated: $Icon"
}

& $Python -m PyInstaller `
    --onefile `
    --windowed `
    --noconsole `
    --name "Offline LAN Games Helper" `
    --icon "assets\offline_lan_helper.ico" `
    --add-data "games.json;." `
    .\lan_games_helper.py

if (Test-Path -LiteralPath $Spec) {
    $specText = Get-Content -LiteralPath $Spec -Raw
    if ($specText -notmatch 'console=False') {
        throw 'PyInstaller spec check failed: console=False was not found.'
    }
}

if (-not (Test-Path -LiteralPath $Dist)) {
    New-Item -ItemType Directory -Path $Dist | Out-Null
}

Copy-Item -LiteralPath .\games.json -Destination (Join-Path $Dist 'games.json') -Force
Copy-Item -LiteralPath .\user_config.json -Destination (Join-Path $Dist 'user_config.json') -Force
foreach ($File in @('README.md', 'PRIVACY.md', 'LICENSE')) {
    if (Test-Path -LiteralPath $File) {
        Copy-Item -LiteralPath $File -Destination (Join-Path $Dist $File) -Force
    }
}

Write-Host ''
Write-Host 'Build complete.'
Write-Host "Executable: $(Join-Path $Dist 'Offline LAN Games Helper.exe')"
Write-Host 'Editable data files copied beside the executable: games.json, user_config.json'
Write-Host 'Documentation copied beside the executable: README.md, PRIVACY.md, LICENSE'
