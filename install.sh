#!/bin/bash
set -e

echo "Installing grummage..."

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 is required but not installed."
    echo "Please install Python 3.8 or later and try again."
    exit 1
fi

# Check Python version
python_version=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
required_version="3.8"

if ! python3 -c "import sys; exit(0 if sys.version_info >= (3, 8) else 1)"; then
    echo "Error: Python $required_version or later is required (found $python_version)"
    exit 1
fi

# Install via pip
echo "Installing grummage from PyPI..."
python3 -m pip install --user grummage

echo ""
echo "Installation complete!"
echo "You can now run: grummage <path-to-sbom-file>"
echo ""
echo "Make sure ~/.local/bin is in your PATH to use the grummage command."