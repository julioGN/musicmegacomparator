"""
Unit tests for LibraryComparator functionality.
"""

import pytest
from unittest.mock import Mock, patch
import pandas as pd

from musicweb.core.comparison import LibraryComparator
from musicweb.core.models import Track, Library, ComparisonResult


class TestLibraryComparator:
    """Test the LibraryComparator class."""
    
    def test_init(self):
        """Test comparator initialization."""
        comparator = LibraryComparator()
        assert comparator is not None
        assert hasattr(comparator, 'compare_libraries')
    
    def test_compare_empty_libraries(self, comparator):
        """Test comparison of empty libraries."""
        lib1 = Library("Empty 1", "spotify")
        lib2 = Library("Empty 2", "apple_music")
        
        result = comparator.compare_libraries(lib1, lib2)
        
        assert isinstance(result, ComparisonResult)
        assert len(result.shared_tracks) == 0
        assert len(result.unique_to_first) == 0
        assert len(result.unique_to_second) == 0
    
    def test_compare_identical_libraries(self, sample_tracks):
        """Test comparison of identical libraries."""
        lib1 = Library("Library 1", "spotify")
        lib2 = Library("Library 2", "apple_music")
        
        for track in sample_tracks:
            lib1.add_track(track)
            lib2.add_track(track)
        
        comparator = LibraryComparator()
        result = comparator.compare_libraries(lib1, lib2)
        
        assert len(result.shared_tracks) == len(sample_tracks)
        assert len(result.unique_to_first) == 0
        assert len(result.unique_to_second) == 0
    
    def test_compare_different_libraries(self, sample_tracks):
        """Test comparison of different libraries."""
        lib1 = Library("Library 1", "spotify")
        lib2 = Library("Library 2", "apple_music")
        
        # Add different tracks to each library
        lib1.add_track(sample_tracks[0])
        lib1.add_track(sample_tracks[1])
        
        lib2.add_track(sample_tracks[1])
        lib2.add_track(sample_tracks[2])
        
        comparator = LibraryComparator()
        result = comparator.compare_libraries(lib1, lib2)
        
        assert len(result.shared_tracks) == 1  # sample_tracks[1]
        assert len(result.unique_to_first) == 1  # sample_tracks[0]
        assert len(result.unique_to_second) == 1  # sample_tracks[2]
    
    def test_fuzzy_matching(self):
        """Test fuzzy matching functionality."""
        lib1 = Library("Library 1", "spotify")
        lib2 = Library("Library 2", "apple_music")
        
        # Add similar but not identical tracks
        track1 = Track("Test Song", "Test Artist", "Test Album", 180, platform="spotify")
        track2 = Track("Test Song (Remix)", "Test Artist", "Test Album", 185, platform="apple_music")
        
        lib1.add_track(track1)
        lib2.add_track(track2)
        
        comparator = LibraryComparator(similarity_threshold=0.8)
        result = comparator.compare_libraries(lib1, lib2, use_fuzzy_matching=True)
        
        # Should match due to high similarity
        assert len(result.shared_tracks) == 1
    
    def test_isrc_matching(self):
        """Test ISRC-based exact matching."""
        lib1 = Library("Library 1", "spotify")
        lib2 = Library("Library 2", "apple_music")
        
        # Add tracks with same ISRC but different metadata
        track1 = Track("Song Title", "Artist Name", "Album", 180, isrc="TEST123", platform="spotify")
        track2 = Track("Different Title", "Different Artist", "Different Album", 200, isrc="TEST123", platform="apple_music")
        
        lib1.add_track(track1)
        lib2.add_track(track2)
        
        comparator = LibraryComparator()
        result = comparator.compare_libraries(lib1, lib2, use_isrc_matching=True)
        
        # Should match due to same ISRC
        assert len(result.shared_tracks) == 1
    
    def test_duration_tolerance(self):
        """Test duration-based matching with tolerance."""
        lib1 = Library("Library 1", "spotify")
        lib2 = Library("Library 2", "apple_music")
        
        # Add tracks with similar duration
        track1 = Track("Test Song", "Test Artist", "Test Album", 180, platform="spotify")
        track2 = Track("Test Song", "Test Artist", "Test Album", 185, platform="apple_music")
        
        lib1.add_track(track1)
        lib2.add_track(track2)
        
        comparator = LibraryComparator(duration_tolerance=10)
        result = comparator.compare_libraries(lib1, lib2)
        
        # Should match due to duration tolerance
        assert len(result.shared_tracks) == 1
    
    @pytest.mark.slow
    def test_large_library_performance(self, performance_timer):
        """Test performance with large libraries."""
        lib1 = Library("Large Library 1", "spotify")
        lib2 = Library("Large Library 2", "apple_music")
        
        # Create large libraries
        for i in range(1000):
            track1 = Track(f"Song {i}", f"Artist {i}", f"Album {i}", 180 + i, platform="spotify")
            track2 = Track(f"Song {i}", f"Artist {i}", f"Album {i}", 180 + i, platform="apple_music")
            lib1.add_track(track1)
            lib2.add_track(track2)
        
        comparator = LibraryComparator()
        
        performance_timer.start()
        result = comparator.compare_libraries(lib1, lib2)
        performance_timer.stop()
        
        assert performance_timer.elapsed < 10.0  # Should complete in under 10 seconds
        assert len(result.shared_tracks) == 1000
    
    def test_comparison_statistics(self, sample_tracks):
        """Test comparison result statistics."""
        lib1 = Library("Library 1", "spotify")
        lib2 = Library("Library 2", "apple_music")
        
        # Add overlapping tracks
        for i, track in enumerate(sample_tracks):
            lib1.add_track(track)
            if i > 0:  # Skip first track for lib2
                lib2.add_track(track)
        
        # Add extra track to lib2
        extra_track = Track("Extra Song", "Extra Artist", "Extra Album", 200, platform="apple_music")
        lib2.add_track(extra_track)
        
        comparator = LibraryComparator()
        result = comparator.compare_libraries(lib1, lib2)
        
        stats = result.get_statistics()
        
        assert stats['total_tracks_lib1'] == len(sample_tracks)
        assert stats['total_tracks_lib2'] == len(sample_tracks)
        assert stats['shared_tracks'] == len(sample_tracks) - 1
        assert stats['overlap_percentage'] > 0
    
    def test_export_results(self, sample_tracks, temp_dir):
        """Test exporting comparison results."""
        lib1 = Library("Library 1", "spotify")
        lib2 = Library("Library 2", "apple_music")
        
        for track in sample_tracks:
            lib1.add_track(track)
            lib2.add_track(track)
        
        comparator = LibraryComparator()
        result = comparator.compare_libraries(lib1, lib2)
        
        # Test CSV export
        csv_path = temp_dir / "comparison_result.csv"
        result.export_to_csv(str(csv_path))
        assert csv_path.exists()
        
        # Test JSON export
        json_path = temp_dir / "comparison_result.json"
        result.export_to_json(str(json_path))
        assert json_path.exists()
    
    def test_custom_matching_algorithm(self):
        """Test custom matching algorithm."""
        def custom_matcher(track1, track2):
            # Custom logic: match only if artists are identical
            return track1.artist.lower() == track2.artist.lower()
        
        lib1 = Library("Library 1", "spotify")
        lib2 = Library("Library 2", "apple_music")
        
        track1 = Track("Song 1", "Same Artist", "Album 1", 180, platform="spotify")
        track2 = Track("Song 2", "Same Artist", "Album 2", 200, platform="apple_music")
        track3 = Track("Song 3", "Different Artist", "Album 3", 220, platform="apple_music")
        
        lib1.add_track(track1)
        lib2.add_track(track2)
        lib2.add_track(track3)
        
        comparator = LibraryComparator(custom_matcher=custom_matcher)
        result = comparator.compare_libraries(lib1, lib2)
        
        # Should match track1 and track2 due to same artist
        assert len(result.shared_tracks) == 1
    
    def test_error_handling(self):
        """Test error handling in comparison."""
        comparator = LibraryComparator()
        
        # Test with None libraries
        with pytest.raises(ValueError):
            comparator.compare_libraries(None, None)
        
        # Test with invalid parameters
        lib1 = Library("Library 1", "spotify")
        lib2 = Library("Library 2", "apple_music")
        
        with pytest.raises(ValueError):
            LibraryComparator(similarity_threshold=1.5)  # Invalid threshold
        
        with pytest.raises(ValueError):
            LibraryComparator(duration_tolerance=-10)  # Invalid tolerance