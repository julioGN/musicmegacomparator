# Installation Guide

This guide covers different ways to install and run MusicWeb.

## Requirements

- Python 3.8 or higher
- 4GB RAM minimum (8GB recommended for large libraries)
- 1GB disk space for installation and temporary files

## Installation Methods

### Method 1: Package Installation (Recommended)

```bash
# Install from PyPI (when available)
pip install musicweb

# Or install from source
git clone https://github.com/your-username/musicweb.git
cd musicweb
pip install -e .
```

### Method 2: Docker Installation

```bash
# Pull and run the official image
docker pull musicweb/musicweb:latest
docker run -p 8501:8501 musicweb/musicweb:latest

# Or use docker-compose
git clone https://github.com/your-username/musicweb.git
cd musicweb
docker-compose up -d
```

### Method 3: Development Installation

```bash
# Clone the repository
git clone https://github.com/your-username/musicweb.git
cd musicweb

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Install in development mode
pip install -e .
```

## Verification

After installation, verify that MusicWeb is working:

```bash
# Check CLI installation
musicweb --version

# Start web interface
musicweb-web
# or
streamlit run src/musicweb/web/app.py
```

The web interface should open in your browser at `http://localhost:8501`.

## Optional Dependencies

### YouTube Music Integration

For YouTube Music API integration, you'll need authentication headers:

1. Install browser extension like "Get cookies.txt" or use developer tools
2. Export YouTube Music authentication headers
3. Save as `headers_auth.json`
4. Configure path in MusicWeb settings

See [YouTube Music Setup Guide](user-guide/youtube-music-setup.md) for detailed instructions.

### Visualization Dependencies

Some visualizations require additional packages:

```bash
pip install matplotlib-venn plotly
```

## Configuration

### Environment Variables

Create a `.env` file in your project root:

```env
# Optional: YouTube Music headers file path
YOUTUBE_MUSIC_HEADERS_FILE=/path/to/headers_auth.json

# Optional: Logging level
LOG_LEVEL=INFO

# Optional: Maximum file size for uploads (MB)
MAX_FILE_SIZE_MB=100

# Optional: Cache TTL (seconds)
CACHE_TTL=3600
```

### Configuration Files

MusicWeb uses YAML configuration files in the `config/` directory:

- `app-config.yaml` - Main application settings
- `logging.yaml` - Logging configuration
- `development.yaml` - Development overrides

## Troubleshooting

### Common Issues

#### Import Errors
```bash
# Ensure you're in the right environment
which python
pip list | grep musicweb
```

#### Port Already in Use
```bash
# Use a different port
streamlit run src/musicweb/web/app.py --server.port 8502
```

#### Memory Issues with Large Libraries
```bash
# Increase memory limits
export PYTHONHASHSEED=0
ulimit -v 8388608  # 8GB virtual memory limit
```

### Getting Help

If you encounter issues:

1. Check the [troubleshooting guide](user-guide/troubleshooting.md)
2. Search [GitHub issues](https://github.com/your-username/musicweb/issues)
3. Create a new issue with:
   - Operating system and Python version
   - Installation method used
   - Complete error message
   - Steps to reproduce

## Next Steps

After installation:

1. [Quick Start Guide](user-guide/getting-started.md)
2. [Web Interface Tutorial](user-guide/web-interface.md)
3. [CLI Usage Examples](user-guide/cli.md)