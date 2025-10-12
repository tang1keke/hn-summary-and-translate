#!/bin/bash

# HN RSS Translator Setup Script
# This script helps set up the project for first-time users

set -e

echo "🚀 HN RSS Translator Setup"
echo "=========================="
echo ""

# Check Python version
echo "Checking Python version..."
python_version=$(python3 --version 2>&1 | grep -oE '[0-9]+\.[0-9]+')
required_version="3.9"

if [ "$(printf '%s\n' "$required_version" "$python_version" | sort -V | head -n1)" = "$required_version" ]; then
    echo "✅ Python $python_version (OK)"
else
    echo "❌ Python $python_version is too old. Please install Python 3.9 or later."
    exit 1
fi

# Create virtual environment
echo ""
echo "Creating virtual environment..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo "✅ Virtual environment created"
else
    echo "✅ Virtual environment already exists"
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
echo "✅ Dependencies installed"

# Create necessary directories
echo ""
echo "Creating directories..."
mkdir -p cache output
echo "✅ Directories created"

# Check config file
echo ""
if [ ! -f "config.yaml" ]; then
    echo "⚠️  No config.yaml found. Using default configuration."
    echo "   Please edit config.yaml to customize your settings."
else
    echo "✅ Configuration file found"
fi

# Run test to verify installation
echo ""
echo "Running verification test..."
if python3 -c "
from src.fetcher import RSSFetcher
from src.scraper import WebScraper
from src.summarizer import LightweightSummarizer
from src.translator import MultiTranslator
from src.generator import RSSGenerator
print('✅ All modules imported successfully')
" 2>/dev/null; then
    echo ""
else
    echo "⚠️  Some modules failed to import. Check error messages above."
fi

echo ""
echo "Setup complete! 🎉"
echo ""
echo "Next steps:"
echo "1. Edit config.yaml to set your desired languages"
echo "2. Run 'python main.py --test' to test with 3 items"
echo "3. Run 'python main.py' for full processing"
echo ""
echo "For GitHub Actions deployment:"
echo "1. Push to GitHub"
echo "2. Enable Actions in repository settings"
echo "3. Enable Pages in repository settings"
echo "4. The workflow will run automatically"