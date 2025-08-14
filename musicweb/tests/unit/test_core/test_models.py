"""
Unit tests for core models.
"""

import pytest
from musicweb.core.models import Track, Library, TrackNormalizer


class TestTrack:
    """Test Track model functionality."""
    
    def test_track_creation(self):
        """Test basic track creation."""
        track = Track(
            title="Test Song",
            artist="Test Artist",
            album="Test Album",
            duration=180
        )
        
        assert track.title == "Test Song"
        assert track.artist == "Test Artist"
        assert track.album == "Test Album"
        assert track.duration == 180
        assert track.platform is None
    
    def test_track_normalization(self):
        """Test track normalization on creation."""
        track = Track(
            title="Test Song (feat. Another Artist)",
            artist="Test Artist & Friends"
        )
        
        assert track.normalized_title is not None
        assert track.normalized_artist is not None
        assert track.artist_tokens is not None
        assert track.is_music is not None
    
    def test_track_equality(self):
        """Test track equality comparison."""
        track1 = Track("Song", "Artist", "Album")
        track2 = Track("Song", "Artist", "Album") 
        track3 = Track("Different", "Artist", "Album")
        
        assert track1 == track2
        assert track1 != track3
    
    def test_track_to_dict(self):
        """Test track serialization."""
        track = Track(
            title="Test Song",
            artist="Test Artist",
            album="Test Album",
            duration=180,
            isrc="TEST123"
        )
        
        data = track.to_dict()
        assert isinstance(data, dict)
        assert data['title'] == "Test Song"
        assert data['artist'] == "Test Artist"
        assert data['duration'] == 180


class TestLibrary:
    """Test Library model functionality."""
    
    def test_library_creation(self):
        """Test basic library creation."""
        library = Library("Test Library", "spotify")
        
        assert library.name == "Test Library"
        assert library.platform == "spotify"
        assert len(library.tracks) == 0
        assert library.total_tracks == 0
    
    def test_add_track(self, sample_track):
        """Test adding tracks to library."""
        library = Library("Test Library", "spotify")
        library.add_track(sample_track)
        
        assert len(library.tracks) == 1
        assert library.total_tracks == 1
        assert library.tracks[0] == sample_track
    
    def test_library_statistics(self, sample_library):
        """Test library statistics calculation."""
        stats = sample_library.get_statistics()
        
        assert isinstance(stats, dict)
        assert 'total_tracks' in stats
        assert 'music_count' in stats
        assert 'artist_counts' in stats
        assert 'duration_stats' in stats
        assert stats['total_tracks'] > 0
    
    def test_artist_counts(self, sample_library):
        """Test artist counting functionality."""
        artist_counts = sample_library.artist_counts
        
        assert isinstance(artist_counts, dict)
        assert len(artist_counts) > 0
        assert "Artist A" in artist_counts
        assert artist_counts["Artist A"] >= 1


class TestTrackNormalizer:
    """Test TrackNormalizer utility functions."""
    
    def test_normalize_title(self):
        """Test title normalization."""
        test_cases = [
            ("Song (feat. Artist)", "song"),
            ("Song - Remastered", "song remastered"),
            ("Song [Radio Edit]", "song radio edit"),
            ("Song, Pt. 1", "song pt 1"),
        ]
        
        for input_title, expected in test_cases:
            result = TrackNormalizer.normalize_title(input_title)
            assert expected in result.lower()
    
    def test_normalize_artist(self):
        """Test artist normalization."""
        test_cases = [
            ("Artist & Friends", "artist friends"),
            ("Artist feat. Someone", "artist someone"),
            ("Artist, Someone", "artist someone"),
        ]
        
        for input_artist, expected in test_cases:
            result = TrackNormalizer.normalize_artist(input_artist)
            assert expected in result.lower()
    
    def test_parse_duration(self):
        """Test duration parsing."""
        test_cases = [
            ("3:30", 210),
            ("1:05:30", 3930),
            ("180", 180),
            ("2.5", 150),
            ("invalid", None),
        ]
        
        for input_duration, expected in test_cases:
            result = TrackNormalizer.parse_duration(input_duration)
            assert result == expected
    
    def test_extract_artist_tokens(self):
        """Test artist token extraction."""
        artist = "Artist One & Artist Two feat. Artist Three"
        tokens = TrackNormalizer.extract_artist_tokens(artist)
        
        assert isinstance(tokens, set)
        assert "artist" in tokens
        assert "one" in tokens
        assert "two" in tokens
        assert "three" in tokens