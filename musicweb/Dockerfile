# Multi-stage build for MusicWeb
FROM python:3.11-slim as builder

# Set environment variables for build optimization
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    DEBIAN_FRONTEND=noninteractive

# Install system dependencies for building
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    git \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Create virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy and install dependencies
COPY pyproject.toml requirements.txt ./
RUN pip install --upgrade pip setuptools wheel && \
    pip install -r requirements.txt

# Production stage
FROM python:3.11-slim as production

# Metadata
LABEL maintainer="MusicWeb Team <contact@musicweb.app>" \
      version="1.0.0" \
      description="Professional Music Library Management Suite"

# Set production environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH" \
    ENVIRONMENT=production \
    STREAMLIT_SERVER_PORT=8501 \
    STREAMLIT_SERVER_ADDRESS=0.0.0.0 \
    STREAMLIT_BROWSER_GATHER_USAGE_STATS=false \
    STREAMLIT_SERVER_ENABLE_CORS=false \
    STREAMLIT_SERVER_ENABLE_XSRF_PROTECTION=true

# Install runtime dependencies only
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Copy virtual environment from builder stage
COPY --from=builder /opt/venv /opt/venv

# Create non-root user for security
RUN groupadd --gid 1000 musicweb && \
    useradd --uid 1000 --gid 1000 --create-home --shell /bin/bash musicweb

# Switch to non-root user
USER musicweb
WORKDIR /home/musicweb

# Copy application code with proper ownership
COPY --chown=musicweb:musicweb . /home/musicweb/app
WORKDIR /home/musicweb/app

# Install the package in editable mode
RUN pip install --no-deps -e .

# Create necessary directories with proper permissions
RUN mkdir -p logs data config uploads temp && \
    chmod 755 logs data config uploads temp

# Create streamlit config directory
RUN mkdir -p ~/.streamlit

# Copy streamlit configuration
COPY --chown=musicweb:musicweb config/.streamlit/ ~/.streamlit/

# Expose port
EXPOSE 8501

# Health check with more comprehensive checks
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8501/_stcore/health && \
        curl -f http://localhost:8501/ || exit 1

# Add startup script for initialization
COPY --chown=musicweb:musicweb scripts/docker-entrypoint.sh /home/musicweb/
RUN chmod +x /home/musicweb/docker-entrypoint.sh

# Use entrypoint script for proper initialization
ENTRYPOINT ["/home/musicweb/docker-entrypoint.sh"]

# Default command (can be overridden)
CMD ["streamlit", "run", "src/musicweb/web/app.py", \
     "--server.port=${STREAMLIT_SERVER_PORT}", \
     "--server.address=${STREAMLIT_SERVER_ADDRESS}", \
     "--server.enableCORS=false", \
     "--server.enableXsrfProtection=true", \
     "--browser.gatherUsageStats=false"]