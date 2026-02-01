<#
.SYNOPSIS
    Launch Asymmetric Dashboard

.DESCRIPTION
    PowerShell launcher for the Asymmetric Investment Workstation dashboard.
    Designed for both human use and automation (Claude).

.PARAMETER Quiet
    Suppress status output (for automation/Claude usage)

.PARAMETER NoBrowser
    Don't open browser automatically

.PARAMETER Background
    Start dashboard in background, return immediately with PID

.EXAMPLE
    .\start.ps1
    # Normal launch with browser

.EXAMPLE
    .\start.ps1 -Quiet -NoBrowser -Background
    # Claude-friendly: quiet, no browser, returns immediately
#>

param(
    [switch]$Quiet,
    [switch]$NoBrowser,
    [switch]$Background
)

$ErrorActionPreference = "Stop"

# Change to script directory
Set-Location $PSScriptRoot

function Write-Log {
    param([string]$Message)
    if (-not $Quiet) {
        Write-Host $Message
    }
}

# Banner
if (-not $Quiet) {
    Write-Host "========================================"
    Write-Host "  Asymmetric Investment Workstation"
    Write-Host "========================================"
    Write-Host ""
}

# Validate Python
try {
    $null = python --version 2>&1
    Write-Log "[OK] Python found"
} catch {
    Write-Error "Python not found. Install Python 3.10+"
    exit 1
}

# Validate Poetry
try {
    $null = poetry --version 2>&1
    Write-Log "[OK] Poetry found"
} catch {
    Write-Error "Poetry not found. Run: pip install poetry"
    exit 1
}

# Check .env
if (-not (Test-Path ".env")) {
    Write-Log "[WARN] .env file not found - some features may not work"
}

# Build arguments
$launchArgs = @("run", "asymmetric", "launch")
if ($Quiet) { $launchArgs += "--quiet" }
if ($NoBrowser) { $launchArgs += "--no-browser" }
if ($Background) { $launchArgs += "--background" }

Write-Log ""
Write-Log "Starting dashboard..."
Write-Log ""

# Launch
& poetry @launchArgs
$exitCode = $LASTEXITCODE

if ($exitCode -ne 0) {
    Write-Error "Dashboard failed to start (exit code: $exitCode)"
    exit $exitCode
}

exit 0
