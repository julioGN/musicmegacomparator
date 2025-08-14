# MusicWeb - Professional Music Library Management Suite

<div align="center">

![MusicWeb Logo](https://via.placeholder.com/150x150/667eea/FFFFFF?text=🎵)

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

*A comprehensive tool for comparing, analyzing, and managing music libraries across multiple streaming platforms*

</div>

## ✨ Features

### 🔍 **Library Comparison**
- Compare music libraries across Spotify, Apple Music, and YouTube Music
- Advanced fuzzy matching algorithms with configurable strictness
- ISRC-based exact matching for precision
- Duration and album-based validation

### 📊 **Analytics & Insights**
- Detailed library statistics and overlap analysis
- Artist and genre distribution charts
- Missing tracks identification and analysis
- Duplicate detection and cleanup recommendations

### 🎵 **Playlist Management**
- Create YouTube Music playlists from missing tracks
- Automated search and matching with fallback options
- Batch playlist operations with progress tracking
- Export results in multiple formats (CSV, JSON)

### 🧹 **Library Cleanup**
- Remove duplicates with smart detection
- Clean up metadata inconsistencies
- Merge similar artists and albums
- Validate library integrity

### 🌐 **Multi-Platform Support**
- **Spotify**: CSV exports and JSON data
- **Apple Music**: CSV exports and iTunes XML libraries
- **YouTube Music**: JSON exports and API integration
- **Extensible**: Easy to add new platforms

## 🚀 Quick Start

### Installation

```bash
# Clone the repository
git clone https://github.com/your-username/musicweb.git
cd musicweb

# Install dependencies
pip install -r requirements.txt

# Install in development mode
pip install -e .
```

### Web Interface

```bash
# Start the web application
streamlit run src/musicweb/web/app.py
```

Open your browser to `http://localhost:8501` and start managing your music libraries!

### Command Line Interface

```bash
# Compare two libraries
musicweb compare spotify_library.json apple_library.csv --output comparison_result.json

# Create a playlist from missing tracks
musicweb playlist create --source spotify_library.json --target youtube_library.json --name "Missing from YouTube"

# Analyze library statistics
musicweb analyze spotify_library.json --detailed
```

## 📖 Documentation

- [Installation Guide](docs/installation.md)
- [User Guide](docs/user-guide/)
- [API Reference](docs/api-reference/)
- [Deployment Guide](docs/deployment/)

## 🏗️ Architecture

```
musicweb/
├── src/musicweb/           # Core application
│   ├── core/              # Business logic
│   ├── platforms/         # Platform parsers
│   ├── integrations/      # External APIs
│   ├── web/               # Web interface
│   ├── cli/               # Command line
│   └── utils/             # Utilities
├── tests/                 # Test suite
├── docs/                  # Documentation
├── scripts/               # Utility scripts
└── config/                # Configuration
```

## 🧪 Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src/musicweb --cov-report=html

# Run specific test category
pytest tests/unit/
pytest tests/integration/
```

## 🐳 Docker Deployment

```bash
# Build the container
docker build -t musicweb .

# Run with docker-compose
docker-compose up -d
```

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guide](CONTRIBUTING.md) for details.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- [Streamlit](https://streamlit.io/) for the amazing web framework
- [YTMusicAPI](https://github.com/sigma67/ytmusicapi) for YouTube Music integration
- [RapidFuzz](https://github.com/maxbachmann/RapidFuzz) for fast string matching
- [Pandas](https://pandas.pydata.org/) for data processing

## 📞 Support

- 📧 Email: support@musicweb.app
- 💬 Discord: [Join our community](https://discord.gg/musicweb)
- 🐛 Issues: [GitHub Issues](https://github.com/your-username/musicweb/issues)
- 📖 Wiki: [GitHub Wiki](https://github.com/your-username/musicweb/wiki)

---

<div align="center">
Made with ❤️ by the MusicWeb Team
</div>