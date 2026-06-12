#!/usr/bin/env bash
# Dev environment setup for sahiixx-agency.
# Installs Python formatter/linter/test tools and Node dashboard dependencies.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"

PYTHON_CMD="${PYTHON_CMD:-python3}"
if ! command -v "$PYTHON_CMD" >/dev/null 2>&1; then
    PYTHON_CMD="python"
fi

if ! command -v "$PYTHON_CMD" >/dev/null 2>&1; then
    echo "Error: Python is not installed or not on PATH." >&2
    echo "Install Python 3.12+ and ensure 'python' or 'python3' works in Git Bash." >&2
    exit 1
fi

PYTHON_VERSION_OUTPUT="$($PYTHON_CMD --version 2>&1 || true)"
PYTHON_VERSION="$(echo "$PYTHON_VERSION_OUTPUT" | awk '/^Python [0-9]+\.[0-9]+/ {print $2}')"

if [ -z "$PYTHON_VERSION" ]; then
    echo "Error: '$PYTHON_CMD' is on PATH but does not run correctly." >&2
    echo "Output was: $PYTHON_VERSION_OUTPUT" >&2
    echo "On Windows, disable the 'App Execution Alias' for python/python3 in Settings > Apps > Advanced app settings > App execution aliases," >&2
    echo "or install a real Python (e.g., from python.org or via winget install Python.Python.3.12)." >&2
    exit 1
fi

echo "Using Python $PYTHON_VERSION ($PYTHON_CMD)"

# --- Python tooling ---------------------------------------------------------
echo ""
echo "Installing Python dev tools..."
$PYTHON_CMD -m pip install --upgrade pip
$PYTHON_CMD -m pip install \
    black \
    ruff \
    mypy \
    pytest \
    pytest-asyncio \
    pytest-cov

# --- Node / dashboard tooling ----------------------------------------------
echo ""
if command -v npm >/dev/null 2>&1; then
    NPM_CMD="npm"
elif command -v pnpm >/dev/null 2>&1; then
    NPM_CMD="pnpm"
elif command -v yarn >/dev/null 2>&1; then
    NPM_CMD="yarn"
else
    echo "Error: npm/pnpm/yarn is not installed or not on PATH." >&2
    echo "Install Node.js LTS to get npm." >&2
    exit 1
fi

echo "Using Node package manager: $NPM_CMD"

DASHBOARD_DIR="$REPO_ROOT/dashboard"
if [ -d "$DASHBOARD_DIR" ]; then
    echo "Installing dashboard dependencies..."
    cd "$DASHBOARD_DIR"
    $NPM_CMD install
else
    echo "Warning: dashboard/ directory not found at $DASHBOARD_DIR" >&2
fi

# --- Verify -----------------------------------------------------------------
echo ""
echo "Verifying tools..."
command -v black >/dev/null && echo "  ✓ black"
command -v ruff >/dev/null && echo "  ✓ ruff"
command -v mypy >/dev/null && echo "  ✓ mypy"
command -v pytest >/dev/null && echo "  ✓ pytest"
command -v npm >/dev/null && echo "  ✓ npm"

echo ""
echo "Dev environment setup complete."
echo "You can now run: kimi"
echo "And in a kimi session:"
echo "  project-info"
echo "  echo '{\"path\":\"sahiixx_agency\"}' | run-formatter"
echo "  echo '{\"path\":\"sahiixx_agency\"}' | run-linter"
echo "  echo '{\"scope\":\"tests\"}' | run-tests"
