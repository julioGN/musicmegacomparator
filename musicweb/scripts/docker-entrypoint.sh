#!/bin/bash
set -e

# Docker entrypoint script for MusicWeb
echo "Starting MusicWeb..."

# Set default environment if not provided
export ENVIRONMENT=${ENVIRONMENT:-production}
export LOG_LEVEL=${LOG_LEVEL:-INFO}

# Create logs directory if it doesn't exist
mkdir -p logs

# Initialize logging
echo "$(date): MusicWeb container starting" >> logs/container.log

# Set up Streamlit configuration
mkdir -p ~/.streamlit
cat > ~/.streamlit/config.toml << EOF
[server]
port = ${STREAMLIT_SERVER_PORT:-8501}
address = "${STREAMLIT_SERVER_ADDRESS:-0.0.0.0}"
enableCORS = false
enableXsrfProtection = true

[browser]
gatherUsageStats = false

[theme]
primaryColor = "#667eea"
backgroundColor = "#ffffff"
secondaryBackgroundColor = "#f0f2f6"
textColor = "#262730"

[logger]
level = "${LOG_LEVEL}"
EOF

# Wait for any dependencies (if needed)
echo "Checking system health..."

# Verify Python environment
python -c "import musicweb; print(f'MusicWeb version: {musicweb.__version__ if hasattr(musicweb, \"__version__\") else \"development\"}')" || {
    echo "Error: MusicWeb package not properly installed"
    exit 1
}

# Run any initialization scripts
if [ -f scripts/init-container.py ]; then
    echo "Running container initialization..."
    python scripts/init-container.py
fi

# Start the application
echo "Starting MusicWeb web interface..."
echo "Environment: $ENVIRONMENT"
echo "Log Level: $LOG_LEVEL"
echo "Port: ${STREAMLIT_SERVER_PORT:-8501}"

# Execute the command passed to the container
exec "$@"