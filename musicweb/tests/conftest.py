"""
Pytest configuration and shared fixtures for MusicWeb tests.
"""

import os
import tempfile
import shutil
from pathlib import Path
from typing import Dict, List, Any
import json
import pytest
import pandas as pd
from unittest.mock import Mock, patch

# Set test environment
os.environ['ENVIRONMENT'] = 'testing'
os.environ['LOG_LEVEL'] = 'WARNING'

# Import after setting environment
from musicweb.core.models import Track, Library
from musicweb.core.comparison import LibraryComparator
from musicweb.platforms.detection import detect_platform


@pytest.fixture(scope="session")
def temp_dir():
    """Create a temporary directory for test files."""
    temp_dir = tempfile.mkdtemp()
    yield Path(temp_dir)
    shutil.rmtree(temp_dir)


@pytest.fixture
def sample_tracks() -> List[Track]:
    """Create sample track data for testing."""
    return [
        Track(
            title="Test Song 1",
            artist="Test Artist 1",
            album="Test Album 1",
            duration=180,
            isrc="TEST123456789",
            platform="spotify"
        ),
        Track(
            title="Test Song 2",
            artist="Test Artist 2",
            album="Test Album 2",
            duration=210,
            isrc="TEST987654321",
            platform="apple_music"
        ),
        Track(
            title="Shared Song",
            artist="Shared Artist",
            album="Shared Album",
            duration=195,
            isrc="SHARED12345678",
            platform="youtube_music"
        ),
    ]


@pytest.fixture
def sample_library(sample_tracks) -> Library:
    """Create a sample library for testing."""
    library = Library(name="Test Library", platform="spotify")
    for track in sample_tracks:
        library.add_track(track)
    return library


@pytest.fixture
def spotify_csv_data() -> str:
    """Sample Spotify CSV data."""
    return """Track Name,Artist Name(s),Album Name,Duration (ms),ISRC
Test Song 1,Test Artist 1,Test Album 1,180000,TEST123456789
Test Song 2,Test Artist 2,Test Album 2,210000,TEST987654321
Shared Song,Shared Artist,Shared Album,195000,SHARED12345678"""


@pytest.fixture
def apple_csv_data() -> str:
    """Sample Apple Music CSV data."""
    return """Name,Artist,Album,Time,Composer
Test Song 1,Test Artist 1,Test Album 1,3:00,
Different Song,Different Artist,Different Album,2:45,
Shared Song,Shared Artist,Shared Album,3:15,"""


@pytest.fixture
def youtube_json_data() -> Dict[str, Any]:
    """Sample YouTube Music JSON data."""
    return {
        "playlists": [
            {
                "title": "Liked Music",
                "tracks": [
                    {
                        "title": "Test Song 1",
                        "artist": "Test Artist 1",
                        "album": "Test Album 1",
                        "duration": "3:00"
                    },
                    {
                        "title": "YouTube Exclusive",
                        "artist": "YouTube Artist",
                        "album": "YouTube Album",
                        "duration": "4:30"
                    },
                    {
                        "title": "Shared Song",
                        "artist": "Shared Artist",
                        "album": "Shared Album",
                        "duration": "3:15"
                    }
                ]
            }
        ]
    }


@pytest.fixture
def spotify_csv_file(temp_dir, spotify_csv_data) -> Path:
    """Create a temporary Spotify CSV file."""
    file_path = temp_dir / "spotify_library.csv"
    file_path.write_text(spotify_csv_data)
    return file_path


@pytest.fixture
def apple_csv_file(temp_dir, apple_csv_data) -> Path:
    """Create a temporary Apple Music CSV file."""
    file_path = temp_dir / "apple_library.csv"
    file_path.write_text(apple_csv_data)
    return file_path


@pytest.fixture
def youtube_json_file(temp_dir, youtube_json_data) -> Path:
    """Create a temporary YouTube Music JSON file."""
    file_path = temp_dir / "youtube_library.json"
    file_path.write_text(json.dumps(youtube_json_data, indent=2))
    return file_path


@pytest.fixture
def mock_streamlit():
    """Mock Streamlit components for web interface testing."""
    with patch('streamlit.write') as mock_write, \
         patch('streamlit.sidebar') as mock_sidebar, \
         patch('streamlit.file_uploader') as mock_uploader, \
         patch('streamlit.button') as mock_button, \
         patch('streamlit.selectbox') as mock_selectbox:
        
        mock_sidebar.write = Mock()
        mock_sidebar.button = Mock(return_value=False)
        mock_sidebar.selectbox = Mock(return_value="Option 1")
        mock_uploader.return_value = None
        mock_button.return_value = False
        mock_selectbox.return_value = "Option 1"
        
        yield {
            'write': mock_write,
            'sidebar': mock_sidebar,
            'file_uploader': mock_uploader,
            'button': mock_button,
            'selectbox': mock_selectbox
        }


@pytest.fixture
def mock_file_upload():
    """Mock file upload for testing."""
    mock_file = Mock()
    mock_file.name = "test_file.csv"
    mock_file.type = "text/csv"
    mock_file.read.return_value = b"test,data\n1,2\n3,4"
    mock_file.getvalue.return_value = b"test,data\n1,2\n3,4"
    return mock_file


@pytest.fixture
def mock_youtube_api():
    """Mock YouTube Music API for testing."""
    with patch('musicweb.integrations.youtube_music.YTMusic') as mock_ytmusic:
        mock_instance = Mock()
        mock_instance.get_library.return_value = {
            'tracks': [
                {
                    'title': 'Test Song',
                    'artists': [{'name': 'Test Artist'}],
                    'album': {'name': 'Test Album'},
                    'duration': '3:00'
                }
            ]
        }
        mock_ytmusic.return_value = mock_instance
        yield mock_instance


@pytest.fixture
def comparator(sample_library):
    """Create a LibraryComparator instance for testing."""
    return LibraryComparator()


@pytest.fixture
def mock_logger():
    """Mock logger for testing."""
    with patch('musicweb.utils.logging_config.get_logger') as mock_get_logger:
        mock_logger = Mock()
        mock_get_logger.return_value = mock_logger
        yield mock_logger


@pytest.fixture
def test_config():
    """Test configuration settings."""
    return {
        'testing': True,
        'log_level': 'WARNING',
        'disable_external_apis': True,
        'mock_file_operations': True,
        'test_data_dir': 'tests/fixtures'
    }


@pytest.fixture(autouse=True)
def cleanup_logs():
    """Automatically clean up test logs."""
    yield
    # Clean up any log files created during testing
    log_files = ['test.log', 'test_errors.log', 'musicweb.log', 'musicweb_errors.log']
    for log_file in log_files:
        if Path(log_file).exists():
            Path(log_file).unlink()


# Pytest configuration
def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line("markers", "slow: marks tests as slow")
    config.addinivalue_line("markers", "integration: marks tests as integration tests")
    config.addinivalue_line("markers", "unit: marks tests as unit tests")
    config.addinivalue_line("markers", "web: marks tests that test web interface")
    config.addinivalue_line("markers", "api: marks tests that test API integration")


def pytest_collection_modifyitems(config, items):
    """Automatically mark tests based on their location."""
    for item in items:
        # Mark tests in integration folder
        if "integration" in str(item.fspath):
            item.add_marker(pytest.mark.integration)
        
        # Mark tests in unit folder
        if "unit" in str(item.fspath):
            item.add_marker(pytest.mark.unit)
        
        # Mark web interface tests
        if "web" in str(item.fspath) or "streamlit" in str(item.fspath):
            item.add_marker(pytest.mark.web)
        
        # Mark API tests
        if "api" in str(item.fspath) or "youtube" in str(item.fspath):
            item.add_marker(pytest.mark.api)


# Custom assertion helpers
class TrackAssertions:
    """Custom assertions for Track objects."""
    
    @staticmethod
    def assert_tracks_equal(track1: Track, track2: Track, ignore_platform=False):
        """Assert that two tracks are equal."""
        assert track1.title == track2.title
        assert track1.artist == track2.artist
        assert track1.album == track2.album
        
        if not ignore_platform:
            assert track1.platform == track2.platform
    
    @staticmethod
    def assert_track_in_library(track: Track, library: Library):
        """Assert that a track exists in a library."""
        found = any(
            t.title == track.title and t.artist == track.artist
            for t in library.tracks
        )
        assert found, f"Track '{track.title}' by '{track.artist}' not found in library"


@pytest.fixture
def track_assertions():
    """Provide track assertion helpers."""
    return TrackAssertions()


# Performance testing utilities
@pytest.fixture
def performance_timer():
    """Timer utility for performance testing."""
    import time
    
    class Timer:
        def __init__(self):
            self.start_time = None
            self.end_time = None
        
        def start(self):
            self.start_time = time.time()
        
        def stop(self):
            self.end_time = time.time()
        
        @property
        def elapsed(self):
            if self.start_time and self.end_time:
                return self.end_time - self.start_time
            return None
    
    return Timer()


# Original fixtures for backward compatibility
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
def spotify_json_data_old() -> Dict[str, Any]:
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
    headers_file = temp_dir / "headers_auth.json"
    headers_file.write_text(json.dumps(mock_ytmusic_headers))
    return str(headers_file)