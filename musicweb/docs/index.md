# MusicWeb Documentation

Welcome to MusicWeb, the professional music library management suite that helps you compare, analyze, and manage music libraries across multiple streaming platforms.

## What is MusicWeb?

MusicWeb is a comprehensive tool designed for music enthusiasts, librarians, and professionals who need to:

- **Compare** music libraries across different platforms (Spotify, Apple Music, YouTube Music)
- **Analyze** library statistics, overlaps, and gaps
- **Manage** playlists and remove duplicates
- **Migrate** libraries between streaming services

## Key Features

### 🔍 Library Comparison
Advanced comparison algorithms that can match tracks across platforms using multiple criteria including titles, artists, albums, duration, and ISRC codes.

### 📊 Analytics & Insights
Detailed analytics showing library statistics, artist distributions, genre breakdowns, and overlap analysis between different libraries.

### 🎵 Playlist Management
Create playlists on YouTube Music from missing tracks, manage existing playlists, and export results in various formats.

### 🧹 Library Cleanup
Remove duplicates, clean metadata inconsistencies, and validate library integrity with smart detection algorithms.

## Getting Started

Choose your preferred interface:

- **[Web Interface](user-guide/web-interface.md)** - User-friendly Streamlit app
- **[Command Line](user-guide/cli.md)** - Powerful CLI for batch operations
- **[Python API](api-reference/)** - Integrate into your own applications

## Quick Links

- [Installation Guide](installation.md)
- [User Guide](user-guide/)
- [API Reference](api-reference/)
- [Troubleshooting](user-guide/troubleshooting.md)
- [Contributing](../CONTRIBUTING.md)

## Platform Support

| Platform | Import | Export | API Integration |
|----------|--------|--------|-----------------|
| Spotify | ✅ CSV, JSON | ✅ CSV, JSON | ❌ |
| Apple Music | ✅ CSV, XML | ✅ CSV | ❌ |
| YouTube Music | ✅ JSON, CSV | ✅ CSV, JSON | ✅ API |

## Community

- **GitHub**: [Issues and discussions](https://github.com/your-username/musicweb)
- **Discord**: [Join our community](https://discord.gg/musicweb)
- **Email**: support@musicweb.app

## License

MusicWeb is open source software licensed under the [MIT License](https://opensource.org/licenses/MIT).