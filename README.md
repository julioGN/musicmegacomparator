# 🎵 MusicLib - Music Library Management Toolkit

A comprehensive toolkit for comparing and managing music libraries across multiple streaming platforms (Apple Music, Spotify, YouTube Music). Features advanced matching algorithms, playlist creation, and metadata enrichment.

## 🚀 Features

- **🔍 Smart Library Comparison** - Advanced fuzzy matching with confidence scoring
- **🎵 YouTube Music Integration** - Create playlists directly from comparison results
- **📊 Multi-Platform Support** - Apple Music, Spotify, YouTube Music with auto-detection
- **🌐 Web Interface** - Beautiful Streamlit app with drag-and-drop uploads
- **💻 Command Line Tools** - Powerful CLI for automation and scripting
- **🔍 Metadata Enrichment** - Enhance your library with MusicBrainz data
- **📈 Visual Analytics** - Interactive charts and detailed reporting

## 🎯 Quick Start

### 1. Installation
```bash
pip install -r requirements.txt
```

### 2. Web Interface (Recommended)
```bash
python musiclib.py web
```
- Upload your library files (CSV/JSON) with drag-and-drop
- Compare libraries with real-time visual feedback
- Create YouTube Music playlists from missing tracks
- Export results as CSV files

### 3. Command Line Interface
```bash
# Compare two libraries
python musiclib-cli.py compare --source apple_music.csv --target youtube_music.json

# Create YouTube Music playlist from missing tracks  
python musiclib-cli.py create-playlist --tracks missing_tracks.csv --name "Missing Songs" --headers headers_auth.json

# Analyze multiple libraries
python musiclib-cli.py analyze --libraries apple_music.csv spotify.csv youtube_music.json

# Enrich metadata with MusicBrainz
python musiclib-cli.py enrich --library apple_music.csv --output-dir enriched/
```

### 4. Python Library Usage
```python
from musiclib import Library, LibraryComparator, create_parser

# Load libraries
apple_parser = create_parser('apple_music')
apple_lib = apple_parser.parse_file('apple_music.csv')

spotify_parser = create_parser('spotify') 
spotify_lib = spotify_parser.parse_file('spotify.csv')

# Compare libraries
comparator = LibraryComparator(strict_mode=True)
result = comparator.compare_libraries(apple_lib, spotify_lib)

# View results
print(f"Match rate: {result.match_rate:.1%}")
print(f"Missing tracks: {len(result.missing_tracks)}")
```

## 🎵 Supported Platforms & Formats

### Apple Music
Export your library as CSV with columns:
- `title`, `artist`, `album`, `duration`, `isrc`, `year`, `genre`

### Spotify
Use tools like Exportify to get CSV with:
- `Track Name`, `Artist Name(s)`, `Album Name`, `Duration (ms)`

### YouTube Music
Export from Google Takeout (JSON format) or CSV with:
- `title`, `artist`, `album`, `duration`

**Auto-Detection**: File formats are automatically detected based on content.

## 🔍 Advanced Matching Algorithm

### Multi-Factor Confidence Scoring
- **Title Similarity** (45%): Fuzzy matching with dynamic thresholds
- **Artist Similarity** (35%): Token-based analysis handling collaborations
- **Album Similarity** (10%): Optional album matching
- **Duration Matching** (10%): Validates track length
- **ISRC Exact Match**: 100% confidence for perfect matches

### Smart Features
- **Dynamic thresholds**: Stricter matching for short titles
- **Artist token analysis**: Handles "feat.", collaborations, aliases
- **Content filtering**: Removes podcasts, YouTube Shorts, interviews
- **Version preservation**: Keeps remix, live, acoustic indicators

## 🎵 YouTube Music Integration

### Setup
1. Install YouTube Music API: `pip install ytmusicapi`
2. Generate headers file: `ytmusicapi setup`
3. Upload the `headers_auth.json` file in the web interface

### Features
- **Batch playlist creation** from missing tracks (50 tracks per batch)
- **Smart search fallback** with confidence scoring
- **Rate limiting** to respect API limits
- **Progress tracking** for large playlists
- **Detailed failure reporting** for tracks not found

## 🔍 Metadata Enrichment

Enhance your library with **MusicBrainz** data:
- **ISRC codes** for exact track identification
- **Missing duration** information
- **Genre tags** from community data
- **Album information** and release dates
- **Multiple search strategies** for best matches

**Note**: Enrichment is rate-limited (1 request per 1.2 seconds) to respect MusicBrainz API guidelines.

## 📊 Configuration Options

### Matching Modes
- **Strict Mode** (default): Higher precision, fewer false positives
  - Title similarity ≥ 92%, Artist overlap ≥ 50%, Duration within 5s
- **Relaxed Mode**: Higher recall, more matches found  
  - Title similarity ≥ 88%, Artist overlap ≥ 33%, Duration within 7s

### Content Filtering
Automatically removes non-music content:
- Podcasts, interviews, audiobooks
- YouTube Shorts and video clips
- Meditation, sleep sounds, nature sounds
- Comedy and spoken word content

## 📈 Performance & Scalability

- **Large libraries**: Handles 100K+ track libraries efficiently
- **Memory efficient**: Streaming processing, minimal footprint
- **Fast matching**: Optimized algorithms with lookup indices
- **Progress tracking**: Real-time feedback for long operations
- **Batch processing**: Handles large datasets without memory issues

## 📁 Project Structure
```
musiclib/
├── musiclib/                 # Core library
│   ├── core.py              # Track, Library, matching algorithms
│   ├── platforms.py         # Platform-specific parsers  
│   ├── comparison.py        # Library comparison logic
│   ├── playlist.py          # YouTube Music integration
│   └── enrichment.py        # MusicBrainz enrichment
├── musiclib-cli.py          # Command line interface
├── musiclib-web.py          # Streamlit web interface  
├── musiclib.py              # Simple launcher
├── requirements.txt         # Dependencies
└── README.md                # This file
```

## 🛠️ Use Cases

### Find Missing Tracks
Compare your Apple Music library against Spotify to find tracks available on one platform but not the other.

### Create Discovery Playlists
Generate YouTube Music playlists from tracks missing in your current library.

### Library Migration
When switching between streaming platforms, identify which tracks you need to find or re-add.

### Metadata Cleanup
Enhance your library with missing information like ISRC codes, proper genres, and accurate durations.

### Multi-Platform Analysis
Analyze overlap between multiple streaming services to optimize your subscriptions.

## 💡 Tips & Troubleshooting

### CSV Issues
- Ensure UTF-8 encoding for international characters
- Check column headers match expected format
- Handle special characters in track titles properly

### Large Libraries
- Use "Strict Matching" for better performance on large datasets
- Consider processing in smaller batches (10K-20K tracks)
- Allow extra time for MusicBrainz enrichment

### YouTube Music Setup
- Headers file expires periodically - regenerate with `ytmusicapi setup`
- Ensure you have proper permissions for playlist creation
- Some tracks may not be available on YouTube Music

## 🔧 Development

### Running Tests
```bash
pip install pytest pytest-cov
pytest tests/ -v --cov=musiclib
```

### Contributing
This project follows modular design principles:
- Clear separation of concerns between modules
- Comprehensive error handling with helpful messages
- Progress feedback for long-running operations
- Configurable algorithms for different use cases

## 📄 License

This project is provided as-is for personal use. Please respect streaming platform terms of service when using their APIs.

---

🎵 **Enjoy managing your music libraries!** 🎵