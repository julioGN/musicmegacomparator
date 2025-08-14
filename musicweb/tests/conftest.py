"""
Pytest configuration and shared fixtures for MusicWeb tests.
"""

import pytest
import tempfile
import json
import csv
from pathlib import Path
from typing import Dict, Any

from musicweb.core.models import Track, Library


@pytest.fixture
def sample_track() -> Track:
    """Create a sample track for testing."""
    return Track(
        title="Test Song",
        artist="Test Artist",
        album="Test Album",
        duration=180,
        isrc="TEST1234567",
        platform="spotify",
        track_id="test123",
        year=2023,
        genre="Rock"
    )


@pytest.fixture
def sample_library(sample_track) -> Library:
    """Create a sample library for testing."""
    library = Library("Test Library", "spotify")
    
    # Add various tracks
    tracks = [
        Track("Song One", "Artist A", "Album X", 200, "ISRC001", "spotify"),
        Track("Song Two", "Artist B", "Album Y", 180, "ISRC002", "spotify"),
        Track("Song Three", "Artist A", "Album Z", 240, "ISRC003", "spotify"),
        sample_track,
    ]
    
    for track in tracks:
        library.add_track(track)
    
    return library


@pytest.fixture
def spotify_json_data() -> Dict[str, Any]:
    """Sample Spotify JSON data for testing."""
    return [
        {
            "platform": "spotify",
            "type": "track",
            "id": "spotify123",
            "title": "Test Song",
            "artist": "Test Artist",
            "album": "Test Album",
            "isrc": "TEST1234567",
            "duration": "180",
            "trackLink": "https://open.spotify.com/track/spotify123"
        },
        {
            "platform": "spotify",
            "type": "track", 
            "id": "spotify456",
            "title": "Another Song",
            "artist": "Another Artist",
            "album": "Another Album",
            "isrc": "TEST7654321",
            "duration": "200",
            "trackLink": "https://open.spotify.com/track/spotify456"
        }
    ]


@pytest.fixture
def apple_csv_data() -> str:
    """Sample Apple Music CSV data for testing."""
    return """Title,Artist,Album,Duration,ISRC,Year,Genre
Test Song,Test Artist,Test Album,3:00,TEST1234567,2023,Rock
Another Song,Another Artist,Another Album,3:20,TEST7654321,2023,Pop
"""


@pytest.fixture
def temp_spotify_file(spotify_json_data) -> str:
    """Create a temporary Spotify JSON file."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(spotify_json_data, f)
        return f.name


@pytest.fixture
def temp_apple_file(apple_csv_data) -> str:
    """Create a temporary Apple Music CSV file."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
        f.write(apple_csv_data)
        return f.name


@pytest.fixture
def temp_dir() -> str:
    """Create a temporary directory."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield temp_dir


@pytest.fixture
def mock_ytmusic_headers() -> Dict[str, str]:
    """Mock YouTube Music headers for testing."""
    return {
        "User-Agent": "Mozilla/5.0 Test Browser",
        "Accept": "*/*",
        "Authorization": "SAPISIDHASH test_hash",
        "Cookie": "test_cookie=test_value",
        "X-Goog-Visitor-Id": "test_visitor_id"
    }


@pytest.fixture
def mock_headers_file(mock_ytmusic_headers, temp_dir) -> str:
    """Create a mock headers file."""
    headers_file = Path(temp_dir) / "headers_auth.json"
    with open(headers_file, 'w') as f:
        json.dump(mock_ytmusic_headers, f)
    return str(headers_file)


@pytest.fixture(autouse=True)
def cleanup_temp_files():
    """Cleanup temporary files after each test."""
    yield
    # Cleanup happens automatically with tempfile