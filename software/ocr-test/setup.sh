#!/bin/bash
# Setup script for OCR Test PoC
# Creates virtual environment and installs dependencies
#
# Usage: ./setup.sh  (not sh setup.sh)

set -e

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

echo "==================================="
echo "A.B.C. OCR Test - Setup"
echo "==================================="
echo

# Create virtual environment
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
    echo "Virtual environment created."
else
    echo "Virtual environment already exists."
fi

# Activate venv
echo "Activating virtual environment..."
. venv/bin/activate

# Upgrade pip
echo "Upgrading pip..."
pip install --upgrade pip

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt

# Create .env if not exists
if [ ! -f ".env" ]; then
    if [ -f "../voyager-sdk/.env" ]; then
        echo "Copying .env from voyager-sdk..."
        grep "^RTSP_" ../voyager-sdk/.env > .env
        echo "" >> .env
        echo "# OCR Settings" >> .env
        echo "OCR_MODEL=ppocr_v3" >> .env
        echo "OCR_LANG=latin" >> .env
        echo "DEBUG=false" >> .env
    else
        echo "Creating .env from template..."
        cp .env.example .env
        echo "Please edit .env with your camera credentials."
    fi
fi

echo
echo "==================================="
echo "Setup complete!"
echo "==================================="
echo
echo "To activate the environment:"
echo "  cd $SCRIPT_DIR"
echo "  . venv/bin/activate"
echo
echo "To download OCR models:"
echo "  cd models && ./download_models.sh"
echo
echo "To run:"
echo "  python main.py"
