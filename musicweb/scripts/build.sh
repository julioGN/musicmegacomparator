#!/bin/bash
# Build script for MusicWeb

set -e

echo "🏗️ Building MusicWeb..."

# Clean previous builds
echo "🧹 Cleaning previous builds..."
rm -rf build/ dist/ *.egg-info/

# Run code quality checks
echo "🔍 Running code quality checks..."

# Format code
echo "  📝 Formatting code with black..."
black src/ tests/ --check

echo "  📦 Sorting imports with isort..."
isort src/ tests/ --check-only

echo "  🔍 Linting with flake8..."
flake8 src/ tests/

# Type checking
echo "  🏷️ Type checking with mypy..."
mypy src/

# Run tests
echo "🧪 Running test suite..."
python -m pytest tests/ --cov=src/musicweb --cov-report=html --cov-report=term

# Build the package
echo "📦 Building package..."
python -m build

# Verify the build
echo "✅ Verifying build..."
python -m twine check dist/*

echo ""
echo "🎉 Build completed successfully!"
echo ""
echo "Build artifacts:"
ls -la dist/
echo ""
echo "Coverage report: htmlcov/index.html"
echo ""
echo "To publish:"
echo "  twine upload dist/*"
echo ""