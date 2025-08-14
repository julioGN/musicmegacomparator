#!/bin/bash
# Development environment setup script for MusicWeb

set -e

echo "🎵 Setting up MusicWeb development environment..."

# Check Python version
python_version=$(python3 --version 2>&1 | awk '{print $2}' | cut -d. -f1,2)
required_version="3.8"

if [ "$(printf '%s\n' "$required_version" "$python_version" | sort -V | head -n1)" != "$required_version" ]; then
    echo "❌ Python 3.8+ required, found $python_version"
    exit 1
fi

echo "✅ Python version check passed: $python_version"

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "🔄 Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo "⬆️ Upgrading pip..."
pip install --upgrade pip

# Install dependencies
echo "📋 Installing dependencies..."
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Install package in development mode
echo "🔧 Installing MusicWeb in development mode..."
pip install -e .

# Set up pre-commit hooks
echo "🪝 Setting up pre-commit hooks..."
pre-commit install

# Create necessary directories
echo "📁 Creating directories..."
mkdir -p data logs config

# Create .env file if it doesn't exist
if [ ! -f ".env" ]; then
    echo "🔧 Creating .env file..."
    cp .env.example .env 2>/dev/null || echo "# MusicWeb Environment Variables
LOG_LEVEL=INFO
MAX_FILE_SIZE_MB=100
CACHE_TTL=3600
# YOUTUBE_MUSIC_HEADERS_FILE=./config/headers_auth.json" > .env
fi

# Run initial tests to verify setup
echo "🧪 Running initial tests..."
python -m pytest tests/unit/test_core/test_models.py -v

echo ""
echo "🎉 Development environment setup complete!"
echo ""
echo "Next steps:"
echo "1. Activate the environment: source venv/bin/activate"
echo "2. Start the web app: streamlit run src/musicweb/web/app.py"
echo "3. Run tests: pytest"
echo "4. Check code quality: black . && isort . && flake8"
echo ""
echo "For YouTube Music integration:"
echo "1. Export your headers to config/headers_auth.json"
echo "2. Update .env file with the path"
echo ""