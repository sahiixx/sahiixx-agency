#!/usr/bin/env bash
set -e

echo "=== One Person Agency Setup ==="

# Create data dir
mkdir -p data

# Install Python package
echo "Installing Python package..."
pip install -e "."

# Install dashboard deps
echo "Installing dashboard dependencies..."
cd dashboard
npm install
cd ..

# Sync repos
echo "Syncing GitHub repos..."
opa sync

echo ""
echo "Setup complete!"
echo ""
echo "Next steps:"
echo "  opa stats          # View agency stats"
echo "  opa registry       # View all modules"
echo "  opa serve          # Start API server"
echo "  cd dashboard && npm run dev  # Start dashboard"
