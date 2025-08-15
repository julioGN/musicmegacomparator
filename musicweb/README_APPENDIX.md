## 🔧 Advanced Configuration

### Environment Variables

```bash
# Production settings
export ENVIRONMENT=production
export LOG_LEVEL=INFO
export REDIS_URL=redis://localhost:6379

# API Keys (optional)
export SPOTIFY_CLIENT_ID=your_spotify_client_id
export SPOTIFY_CLIENT_SECRET=your_spotify_client_secret
export YOUTUBE_API_KEY=your_youtube_api_key
```

### Configuration Files

Create `config/musicweb.yaml`:

```yaml
# MusicWeb Configuration
app:
  name: "MusicWeb"
  version: "1.0.0"
  debug: false

comparison:
  similarity_threshold: 0.85
  duration_tolerance: 5  # seconds
  enable_fuzzy_matching: true
  enable_isrc_matching: true

platforms:
  spotify:
    enabled: true
    rate_limit: 100  # requests per minute
  apple_music:
    enabled: true
  youtube_music:
    enabled: true
    rate_limit: 1000

logging:
  level: INFO
  format: json
  file_rotation: true
  max_file_size: 10MB
  backup_count: 5

monitoring:
  enable_metrics: true
  prometheus_port: 9090
  health_check_interval: 30
```

## 🚀 Production Deployment

### Streamlit Cloud (Easiest)

1. Fork this repository
2. Connect to [Streamlit Cloud](https://share.streamlit.io)
3. Deploy from `src/musicweb/web/app.py`
4. Set secrets in Streamlit Cloud dashboard

### Heroku

```bash
# Install Heroku CLI
heroku create your-musicweb-app
heroku config:set ENVIRONMENT=production
git push heroku main
```

### AWS/GCP/Azure

Use the provided Docker configuration:

```bash
# Build and tag
docker build -t musicweb:latest .
docker tag musicweb:latest your-registry/musicweb:latest

# Push to container registry
docker push your-registry/musicweb:latest

# Deploy to cloud service
kubectl apply -f k8s/deployment.yaml  # Kubernetes
# or use cloud-specific deployment tools
```

### Docker Compose (Self-hosted)

```bash
# Production deployment with monitoring
docker-compose --profile monitoring up -d

# Access services:
# - App: http://localhost:8501
# - Grafana: http://localhost:3000 (admin/admin)
# - Prometheus: http://localhost:9090
```

## 📊 Monitoring & Analytics

### Built-in Metrics

MusicWeb automatically tracks:
- Request counts and response times
- Feature usage statistics
- Platform usage distribution
- Error rates and types
- Memory and CPU usage

### Prometheus Integration

```yaml
# Add to prometheus.yml
scrape_configs:
  - job_name: 'musicweb'
    static_configs:
      - targets: ['musicweb:8501']
    metrics_path: '/metrics'
```

### Grafana Dashboards

Pre-built dashboards available in `config/grafana/`:
- Application Overview
- Performance Metrics
- User Analytics
- System Health

## 🔒 Security

### Best Practices

- Never commit API keys or credentials
- Use environment variables for secrets
- Enable HTTPS in production
- Regularly update dependencies
- Monitor for vulnerabilities

### Security Scanning

```bash
# Run security scans
make security           # Bandit + Safety
make security-full     # Full vulnerability scan
```

### Authentication (Optional)

For private deployments, add authentication:

```python
# In config/auth.py
STREAMLIT_AUTH = {
    "usernames": {
        "admin": {
            "name": "Administrator",
            "password": "hashed_password",
            "roles": ["admin"]
        }
    }
}
```

## 🧪 Development

### Development Setup

```bash
# Clone and setup
git clone https://github.com/your-username/musicweb.git
cd musicweb
make env-dev           # Setup development environment
make install-dev       # Install dependencies
make pre-commit        # Setup git hooks
```

### Testing

```bash
# Run tests
make test              # Basic tests
make test-cov          # With coverage
make test-watch        # Watch mode

# Specific test types
pytest tests/unit/     # Unit tests only
pytest tests/integration/ # Integration tests
pytest -m slow         # Long-running tests
```

### Code Quality

```bash
make format            # Format code (black, isort)
make lint             # Lint code (flake8)
make type-check       # Type checking (mypy)
make check            # Run all quality checks
```

### Building

```bash
make build            # Build Python package
make build-docker     # Build Docker image
make docs             # Build documentation
```

## 📈 Performance Optimization

### Large Libraries

For libraries with 50,000+ tracks:

```python
# Use batch processing
musicweb compare large_lib1.csv large_lib2.csv \
  --batch-size 1000 \
  --parallel-workers 4 \
  --memory-efficient
```

### Caching

Enable Redis caching for better performance:

```yaml
# docker-compose.yml
services:
  redis:
    image: redis:7-alpine
  musicweb:
    environment:
      - REDIS_URL=redis://redis:6379
```

### Database Backend

For persistent storage:

```python
# Optional: Use PostgreSQL for large deployments
pip install musicweb[postgres]
export DATABASE_URL=postgresql://user:pass@localhost/musicweb
```

## 🔌 API Integration

### REST API

Access MusicWeb programmatically:

```python
import requests

# Upload library
files = {'file': open('spotify_library.csv', 'rb')}
response = requests.post('http://localhost:8501/api/upload', files=files)

# Compare libraries
data = {
    'library1_id': 'lib1',
    'library2_id': 'lib2',
    'options': {'fuzzy_matching': True}
}
response = requests.post('http://localhost:8501/api/compare', json=data)
```

### Webhooks

Set up webhooks for automation:

```bash
# Configure webhook endpoint
export WEBHOOK_URL=https://your-service.com/webhook
export WEBHOOK_SECRET=your_secret_key

# Webhook events: comparison_complete, playlist_created, error_occurred
```

## 🛠️ Troubleshooting

### Common Issues

**Issue**: "Module not found" errors
```bash
# Solution: Install in development mode
pip install -e .
```

**Issue**: Streamlit port already in use
```bash
# Solution: Use different port
streamlit run app.py --server.port 8502
```

**Issue**: Memory issues with large files
```bash
# Solution: Increase memory limits
docker run -m 4g musicweb:latest
```

**Issue**: YouTube Music authentication
```bash
# Solution: Generate fresh headers
python scripts/setup_youtube_auth.py
```

### Debug Mode

```bash
# Enable debug logging
export LOG_LEVEL=DEBUG
export STREAMLIT_DEBUG=true

# Run with debug info
musicweb --debug compare file1.csv file2.csv
```

### Performance Profiling

```bash
# Profile application
make profile           # Generate performance profile
make benchmark         # Run benchmarks
```

## 🏆 Enterprise Features

Contact us for enterprise features:
- Single Sign-On (SSO) integration
- Advanced analytics and reporting
- Custom platform integrations
- Priority support
- On-premises deployment
- Advanced security features

Email: enterprise@musicweb.app

## 📋 Changelog

See [CHANGELOG.md](CHANGELOG.md) for detailed version history.

## 🤝 Community

- **GitHub Discussions**: Ask questions and share ideas
- **Discord**: Real-time chat with the community
- **Stack Overflow**: Tag questions with `musicweb`
- **Twitter**: Follow [@MusicWebApp](https://twitter.com/MusicWebApp)

## 📝 License

MusicWeb is released under the MIT License. See [LICENSE](LICENSE) for details.

---

<div align="center">

**⭐ Star us on GitHub** • **🍴 Fork and contribute** • **🐛 Report issues**

Made with ❤️ by the MusicWeb Team

</div>