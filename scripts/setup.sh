#!/bin/bash
# OneDrive Organizer - Setup Script
# Automates initial setup steps

set -e  # Exit on error

echo "============================================================"
echo "OneDrive Organizer - Setup Script"
echo "============================================================"
echo ""

# Check Python version
echo "Checking Python version..."
python3 --version || {
    echo "Error: Python 3 is not installed"
    echo "Please install Python 3.8 or higher"
    exit 1
}

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo ""
    echo "Creating virtual environment..."
    python3 -m venv venv
    echo "✓ Virtual environment created"
else
    echo "✓ Virtual environment already exists"
fi

# Activate virtual environment
echo ""
echo "Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo ""
echo "Upgrading pip..."
pip install --upgrade pip --quiet

# Install dependencies
echo ""
echo "Installing dependencies..."
pip install -r requirements.txt --quiet
echo "✓ Dependencies installed"

# Set up configuration files
echo ""
echo "Setting up configuration files..."

if [ ! -f ".env" ]; then
    cp config/.env.example .env
    echo "✓ Created .env file"
    echo "  → Please edit .env and add your CLIENT_ID"
else
    echo "✓ .env file already exists"
fi

# Create data directories
echo ""
echo "Creating data directories..."
mkdir -p data/tokens data/logs data/history
chmod 700 data/tokens
echo "✓ Data directories created"

# Check if config.yaml needs setup
if [ ! -f "config/config.yaml" ]; then
    echo ""
    echo "Warning: config/config.yaml not found"
    echo "Please ensure the configuration file exists"
fi

echo ""
echo "============================================================"
echo "Setup Complete!"
echo "============================================================"
echo ""
echo "Next steps:"
echo "  1. Edit .env and add your Azure AD CLIENT_ID"
echo "     nano .env"
echo ""
echo "  2. Customize config/config.yaml if needed"
echo "     nano config/config.yaml"
echo ""
echo "  3. Activate virtual environment (if not already active):"
echo "     source venv/bin/activate"
echo ""
echo "  4. Authenticate with OneDrive:"
echo "     python src/main.py --authenticate"
echo ""
echo "  5. Test with dry-run:"
echo "     python src/main.py --dry-run"
echo ""
echo "For detailed instructions, see docs/SETUP.md"
echo "============================================================"
