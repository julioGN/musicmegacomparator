"""
Track matching algorithms for music library comparison.

This module contains the core matching logic for identifying
similar tracks across different music platforms.
"""

import re
import math
import hashlib
from typing import Dict, List, Optional, Set, Tuple, Any
from dataclasses import dataclass
from collections import defaultdict

# Optional dependencies with fallbacks
try:
    from rapidfuzz import fuzz, process
    HAVE_RAPIDFUZZ = True
except ImportError:
    HAVE_RAPIDFUZZ = False

from .models import Track


@dataclass
class MatchResult:
    """Result of a track matching operation."""
    source_track: Track
    target_track: Track
    confidence: float
    match_type: str  # 'exact', 'fuzzy', 'isrc'
    similarity_scores: Dict[str, float]


class TrackMatcher:
    """Advanced track matching with multiple algorithms and performance optimizations."""
    
    def __init__(self, strict_mode: bool = True, enable_duration: bool = True, 
                 enable_album: bool = False, enable_isrc: bool = True):
        self.strict_mode = strict_mode
        self.enable_duration = enable_duration
        self.enable_album = enable_album
        self.enable_isrc = enable_isrc
        
        # Thresholds
        self.exact_threshold = 0.98
        self.fuzzy_threshold = 0.85 if strict_mode else 0.75
        self.duration_tolerance = 5  # seconds
        
        # Performance optimization indices
        self._exact_hash_index: Dict[str, List[Track]] = defaultdict(list)
        self._isrc_index: Dict[str, Track] = {}
        self._artist_index: Dict[str, List[Track]] = defaultdict(list)
        self._title_index: Dict[str, List[Track]] = defaultdict(list)
        self._indexed_tracks: Set[int] = set()
    
    def _create_exact_hash(self, track: Track) -> str:
        """Create a hash for exact matching based on normalized title and artist."""
        if not track.normalized_title or not track.normalized_artist:
            return ""
        
        # Create deterministic hash from normalized content
        content = f"{track.normalized_title.lower()}|{track.normalized_artist.lower()}"
        return hashlib.md5(content.encode('utf-8')).hexdigest()
    
    def _build_indices(self, tracks: List[Track]) -> None:
        """Build performance optimization indices for tracks."""
        self._exact_hash_index.clear()
        self._isrc_index.clear()
        self._artist_index.clear()
        self._title_index.clear()
        self._indexed_tracks.clear()
        
        for track in tracks:
            track_id = id(track)
            if track_id in self._indexed_tracks:
                continue
                
            self._indexed_tracks.add(track_id)
            
            # Exact hash index
            exact_hash = self._create_exact_hash(track)
            if exact_hash:
                self._exact_hash_index[exact_hash].append(track)
            
            # ISRC index
            if track.isrc:
                isrc_key = track.isrc.strip().upper()
                self._isrc_index[isrc_key] = track
            
            # Artist index for pre-filtering
            if track.normalized_artist:
                artist_words = track.normalized_artist.lower().split()
                for word in artist_words:
                    if len(word) > 2:  # Skip very short words
                        self._artist_index[word].append(track)
            
            # Title index for pre-filtering
            if track.normalized_title:
                title_words = track.normalized_title.lower().split()
                for word in title_words:
                    if len(word) > 2:  # Skip very short words
                        self._title_index[word].append(track)
    
    def find_best_match_optimized(self, source_track: Track, candidates: List[Track]) -> Optional[MatchResult]:
        """Optimized version of find_best_match using indices."""
        if not candidates:
            return None
        
        # Build indices if not already done
        if not self._indexed_tracks:
            self._build_indices(candidates)
        
        # 1. Try exact hash match first (fastest)
        exact_hash = self._create_exact_hash(source_track)
        if exact_hash and exact_hash in self._exact_hash_index:
            for candidate in self._exact_hash_index[exact_hash]:
                match_result = self.calculate_match(source_track, candidate)
                if match_result and match_result.confidence >= self.exact_threshold:
                    return match_result
        
        # 2. Try ISRC match (very fast)
        if self.enable_isrc and source_track.isrc:
            isrc_key = source_track.isrc.strip().upper()
            if isrc_key in self._isrc_index:
                candidate = self._isrc_index[isrc_key]
                match_result = self.calculate_match(source_track, candidate)
                if match_result:
                    return match_result
        
        # 3. Pre-filter candidates using word overlap
        filtered_candidates = self._filter_candidates_by_words(source_track, candidates)
        
        # 4. Fallback to standard matching on filtered set
        return self.find_best_match(source_track, filtered_candidates)
    
    def _filter_candidates_by_words(self, source_track: Track, candidates: List[Track]) -> List[Track]:
        """Filter candidates using word-based pre-filtering for performance."""
        if not source_track.normalized_title or not source_track.normalized_artist:
            return candidates
        
        # Get potential matches based on word overlap
        potential_matches = set()
        
        # Check title words
        title_words = source_track.normalized_title.lower().split()
        for word in title_words:
            if len(word) > 2 and word in self._title_index:
                potential_matches.update(self._title_index[word])
        
        # Check artist words
        artist_words = source_track.normalized_artist.lower().split()
        for word in artist_words:
            if len(word) > 2 and word in self._artist_index:
                potential_matches.update(self._artist_index[word])
        
        # If we found potential matches, use them; otherwise fall back to all candidates
        if potential_matches:
            # Convert to list and ensure we're working with the original candidates
            filtered = [track for track in candidates if track in potential_matches]
            return filtered if filtered else candidates[:min(100, len(candidates))]  # Limit fallback
        
        # If no word matches, limit the search to first N candidates for performance
        return candidates[:min(50, len(candidates))]
        
    def find_best_match(self, source_track: Track, candidates: List[Track]) -> Optional[MatchResult]:
        """Find the best matching track from candidates."""
        if not candidates:
            return None
        
        best_match = None
        best_score = 0.0
        
        for candidate in candidates:
            match_result = self.calculate_match(source_track, candidate)
            if match_result and match_result.confidence > best_score:
                best_score = match_result.confidence
                best_match = match_result
        
        # Only return if above threshold
        if best_match and best_match.confidence >= self.fuzzy_threshold:
            return best_match
        
        return None
    
    def calculate_match(self, track1: Track, track2: Track) -> Optional[MatchResult]:
        """Calculate match score between two tracks."""
        # ISRC exact match (highest priority)
        if (self.enable_isrc and track1.isrc and track2.isrc and 
            track1.isrc.strip().upper() == track2.isrc.strip().upper()):
            return MatchResult(
                source_track=track1,
                target_track=track2,
                confidence=1.0,
                match_type='isrc',
                similarity_scores={'isrc': 1.0}
            )
        
        # Title and artist similarity
        title_sim = self._calculate_similarity(track1.normalized_title, track2.normalized_title)
        artist_sim = self._calculate_artist_similarity(track1, track2)
        
        if title_sim < 0.6 or artist_sim < 0.5:
            return None
        
        # Base score from title and artist
        base_score = (title_sim * 0.6) + (artist_sim * 0.4)
        
        similarity_scores = {
            'title': title_sim,
            'artist': artist_sim,
            'base': base_score
        }
        
        # Duration boost
        duration_boost = 0.0
        if self.enable_duration and track1.duration and track2.duration:
            duration_diff = abs(track1.duration - track2.duration)
            if duration_diff <= self.duration_tolerance:
                duration_boost = 0.1 * (1 - duration_diff / self.duration_tolerance)
                similarity_scores['duration'] = 1 - (duration_diff / self.duration_tolerance)
        
        # Album boost
        album_boost = 0.0
        if self.enable_album and track1.album and track2.album:
            album_sim = self._calculate_similarity(track1.album, track2.album)
            if album_sim > 0.7:
                album_boost = 0.05 * album_sim
                similarity_scores['album'] = album_sim
        
        final_score = min(1.0, base_score + duration_boost + album_boost)
        
        # Determine match type
        match_type = 'exact' if final_score >= self.exact_threshold else 'fuzzy'
        
        return MatchResult(
            source_track=track1,
            target_track=track2,
            confidence=final_score,
            match_type=match_type,
            similarity_scores=similarity_scores
        )
    
    def _calculate_similarity(self, str1: Optional[str], str2: Optional[str]) -> float:
        """Calculate string similarity using available algorithms."""
        if not str1 or not str2:
            return 0.0
        
        str1 = str1.lower().strip()
        str2 = str2.lower().strip()
        
        if str1 == str2:
            return 1.0
        
        if HAVE_RAPIDFUZZ:
            return fuzz.ratio(str1, str2) / 100.0
        else:
            # Fallback to simple similarity
            return self._simple_similarity(str1, str2)
    
    def _calculate_artist_similarity(self, track1: Track, track2: Track) -> float:
        """Calculate artist similarity with token matching."""
        if not track1.artist_tokens or not track2.artist_tokens:
            return self._calculate_similarity(track1.normalized_artist, track2.normalized_artist)
        
        # Token-based matching for multi-artist tracks
        common_tokens = track1.artist_tokens.intersection(track2.artist_tokens)
        total_tokens = track1.artist_tokens.union(track2.artist_tokens)
        
        if not total_tokens:
            return 0.0
        
        token_similarity = len(common_tokens) / len(total_tokens)
        
        # Combine with string similarity
        string_similarity = self._calculate_similarity(track1.normalized_artist, track2.normalized_artist)
        
        return max(token_similarity, string_similarity)
    
    def _simple_similarity(self, str1: str, str2: str) -> float:
        """Simple similarity fallback when rapidfuzz is not available."""
        if str1 == str2:
            return 1.0
        
        # Longest common subsequence ratio
        def lcs_length(s1, s2):
            m, n = len(s1), len(s2)
            dp = [[0] * (n + 1) for _ in range(m + 1)]
            
            for i in range(1, m + 1):
                for j in range(1, n + 1):
                    if s1[i-1] == s2[j-1]:
                        dp[i][j] = dp[i-1][j-1] + 1
                    else:
                        dp[i][j] = max(dp[i-1][j], dp[i][j-1])
            
            return dp[m][n]
        
        lcs_len = lcs_length(str1, str2)
        max_len = max(len(str1), len(str2))
        
        return lcs_len / max_len if max_len > 0 else 0.0