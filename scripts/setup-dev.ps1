# Dev environment setup for sahiixx-agency (Windows PowerShell).
# Installs Python formatter/linter/test tools and Node dashboard dependencies.

$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent $PSScriptRoot

# --- Python tooling ---------------------------------------------------------
$PythonCmd = if (Get-Command python -ErrorAction SilentlyContinue) { "python" }
             elseif (Get-Command python3 -ErrorAction SilentlyContinue) { "python3" }
             else { $null }

if (-not $PythonCmd) {
    Write-Error "Python is not installed or not on PATH. Install Python 3.12+ and try again."
    exit 1
}

$PythonVersionOutput = & $PythonCmd --version 2>&1
if ($PythonVersionOutput -notmatch "^Python \d+\.\d+") {
    Write-Error "'$PythonCmd' is on PATH but does not run correctly. Output was: $PythonVersionOutput"
    Write-Host "On Windows, disable the 'App Execution Alias' for python/python3 in Settings > Apps > Advanced app settings > App execution aliases,"
    Write-Host "or install a real Python (e.g., from python.org or via winget install Python.Python.3.12)."
    exit 1
}

Write-Host "Using $PythonVersionOutput ($PythonCmd)"

Write-Host ""
Write-Host "Installing Python dev tools..."
& $PythonCmd -m pip install --upgrade pip
& $PythonCmd -m pip install black ruff mypy pytest pytest-asyncio pytest-cov

# --- Node / dashboard tooling ----------------------------------------------
$NpmCmd = if (Get-Command pnpm -ErrorAction SilentlyContinue) { "pnpm" }
          elseif (Get-Command yarn -ErrorAction SilentlyContinue) { "yarn" }
          elseif (Get-Command npm -ErrorAction SilentlyContinue) { "npm" }
          else { $null }

if (-not $NpmCmd) {
    Write-Error "npm/pnpm/yarn is not installed or not on PATH. Install Node.js LTS to get npm."
    exit 1
}

Write-Host ""
Write-Host "Using Node package manager: $NpmCmd"

$DashboardDir = Join-Path $RepoRoot "dashboard"
if (Test-Path $DashboardDir) {
    Write-Host "Installing dashboard dependencies..."
    Push-Location $DashboardDir
    & $NpmCmd install
    Pop-Location
} else {
    Write-Warning "dashboard/ directory not found at $DashboardDir"
}

# --- Verify -----------------------------------------------------------------
Write-Host ""
Write-Host "Verifying tools..."
$tools = @("black", "ruff", "mypy", "pytest", "npm")
foreach ($tool in $tools) {
    if (Get-Command $tool -ErrorAction SilentlyContinue) {
        Write-Host "  ✓ $tool"
    } else {
        Write-Warning "  ✗ $tool not found on PATH"
    }
}

Write-Host ""
Write-Host "Dev environment setup complete."
Write-Host "You can now run: kimi"
Write-Host "And in a kimi session:"
Write-Host "  project-info"
Write-Host '  echo \'{"path":"sahiixx_agency"}\' | run-formatter'
Write-Host '  echo \'{"path":"sahiixx_agency"}\' | run-linter'
Write-Host '  echo \'{"scope":"tests"}\' | run-tests'
