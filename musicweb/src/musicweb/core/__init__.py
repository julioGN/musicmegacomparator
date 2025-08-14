"""
Core business logic for MusicWeb.

This module contains the fundamental data models and algorithms
for music library management and comparison.
"""

from .models import Track, Library, TrackNormalizer
from .comparison import LibraryComparator, ComparisonResult
from .matching import TrackMatcher
from .enrichment import EnrichmentManager

__all__ = [
    "Track",
    "Library", 
    "TrackNormalizer",
    "LibraryComparator",
    "ComparisonResult", 
    "TrackMatcher",
    "EnrichmentManager"
]