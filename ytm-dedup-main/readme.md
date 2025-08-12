# YouTube Music Library Deduplicator

A complete solution to find and manage duplicate songs in your YouTube Music library using the unofficial ytmusicapi.

## 📁 Complete File Structure

```
youtube-music-deduplicator/
├── youtube_music_deduplicator.py    # Main backend server
├── youtube_music_deduplicator.html  # Frontend interface  
├── setup.py                         # Setup and installation script
├── run.py                           # Quick start script (created by setup)
├── requirements.txt                 # Python dependencies
├── headers_auth_example.json        # Authentication template (created by setup)
├── AUTHENTICATION_GUIDE.md          # Detailed auth setup guide (created by setup)
└── headers_auth.json                # Your actual auth file (you create this)
```

## 🚀 Quick Start

1. **Run Setup:**
   ```bash
   python setup.py
   ```

2. **Create Authentication File:**
   - Follow the guide in `AUTHENTICATION_GUIDE.md`
   - Create `headers_auth.json` with your browser headers

3. **Start Server:**
   ```bash
   python youtube_music_deduplicator.py
   # OR
   python run.py
   ```

4. **Open Browser:**
   - Go to `http://localhost:5003`
   - Click "Check Auth" to verify connection
   - Click "Scan Library for Duplicates"

## 📋 Requirements

### Python Dependencies (requirements.txt)
```
ytmusicapi>=1.3.0
flask>=2.0.0
flask-cors>=4.0.0
```

### System Requirements
- Python 3.7+
- Web browser with developer tools
- Active YouTube Music account

## 🔧 Installation

### Option 1: Automatic Setup
```bash
# Download all files to a folder
# Run setup script
python setup.py
```

### Option 2: Manual Setup
```bash
# Install dependencies
pip install -r requirements.txt

# Create authentication file (see guide)
# Run server
python youtube_music_deduplicator.py
```

## 🔑 Authentication Setup

**Critical Step:** You must create `headers_auth.json` with your browser headers.

### Quick Steps:
1. Open YouTube Music in browser
2. Press F12 → Network tab
3. Refresh page
4. Find request to `music.youtube.com/youtubei/v1/`
5. Copy request headers
6. Create `headers_auth.json` file

### Example headers_auth.json:
```json
{
    "User-Agent": "Mozilla/5.0...",
    "Cookie": "VISITOR_INFO1_LIVE=...; [VERY LONG STRING]",
    "X-Goog-AuthUser": "0",
    "x-origin": "https://music.youtube.com"
}
```

## ✨ Features

### 🔍 Duplicate Detection
- Scans entire YouTube Music library
- Uses title and artist similarity matching
- Configurable similarity threshold (default: 85%)
- Groups duplicates by song

### 📊 Smart Ranking
- Ranks duplicates by quality and source
- Prefers album versions over singles
- Considers audio quality indicators
- Avoids radio edits and low-quality uploads

### 🎵 Playlist Management
- Create playlists from all duplicates
- Create playlists from selected groups only
- Automatic playlist naming with timestamps

### 📄 Export & Analysis
- Export results as JSON
- Detailed duplicate group information
- Quality scores and source analysis

### 🖥️ Web Interface
- Real-time scanning progress
- Interactive duplicate group management
- Mobile-responsive design
- YouTube Music-themed UI

## 🛠️ Advanced Usage

### Custom Similarity Threshold
```python
# In the scan request
{
    "similarity_threshold": 0.90  # Higher = more strict
}
```

### Scanning Subset of Library
```python
# Limit songs for testing
{
    "limit": 100  # Scan only first 100 songs
}
```

## 🔒 Security Notes

- **Never share `headers_auth.json`** - contains your login credentials
- Authentication headers expire - you may need to refresh them
- Uses unofficial API - not officially supported by Google
- Consider YouTube Terms of Service

## 🐛 Troubleshooting

### Common Issues:

**Authentication Failed:**
- Get fresh headers from browser
- Ensure you're logged into YouTube Music
- Check JSON syntax in headers_auth.json

**CORS Errors:**
- Make sure server runs on localhost
- Disable browser extensions if needed
- Use supported browsers (Chrome, Firefox, Safari)

**No Duplicates Found:**
- Lower similarity threshold
- Check if library has actual duplicates
- Ensure songs have proper metadata

**Server Won't Start:**
- Install dependencies: `pip install -r requirements.txt`
- Check Python version (3.7+ required)
- Ensure port 5003 is available

### Debug Mode:
```bash
# Run with debug logging
python youtube_music_deduplicator.py
# Check terminal output for detailed logs
```

## 📊 API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/status` | GET | Check auth and library status |
| `/api/authenticate` | POST | Test authentication |
| `/api/scan` | POST | Scan library for duplicates |
| `/api/create-playlist` | POST | Create playlist from duplicates |
| `/api/export` | GET | Export results as JSON |

## 🤝 Contributing

This is a complete working solution. Possible improvements:
- Add more audio quality detection methods
- Implement batch removal (when API supports it)
- Add more playlist customization options
- Improve duplicate detection algorithms

## ⚠️ Disclaimer

This tool uses the unofficial ytmusicapi library. Use at your own risk and in accordance with YouTube's Terms of Service. The tool does not modify your library directly - it only reads data and creates playlists.

## 📝 License

Use responsibly and in compliance with YouTube Terms of Service.