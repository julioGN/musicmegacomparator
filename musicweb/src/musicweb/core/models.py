"""
Core data structures and matching algorithms for music library management.
"""

import re
import math
import hashlib
from typing import Dict, List, Optional, Set, Tuple, Any
from dataclasses import dataclass, asdict
from collections import defaultdict

# Optional dependencies with fallbacks
try:
    from rapidfuzz import fuzz, process
    HAVE_RAPIDFUZZ = True
except ImportError:
    HAVE_RAPIDFUZZ = False


@dataclass
class Track:
    """Represents a music track with metadata and comparison methods."""
    
    title: str
    artist: str
    album: Optional[str] = None
    duration: Optional[int] = None  # in seconds
    isrc: Optional[str] = None
    platform: Optional[str] = None
    track_id: Optional[str] = None
    url: Optional[str] = None
    year: Optional[int] = None
    genre: Optional[str] = None
    track_number: Optional[int] = None
    
    # Computed fields
    normalized_title: Optional[str] = None
    normalized_artist: Optional[str] = None
    artist_tokens: Optional[Set[str]] = None
    is_music: Optional[bool] = None
    
    def __post_init__(self):
        """Initialize computed fields after creation."""
        if self.normalized_title is None:
            self.normalized_title = TrackNormalizer.normalize_title(self.title)
        if self.normalized_artist is None:
            self.normalized_artist = TrackNormalizer.normalize_artist(self.artist)
        if self.artist_tokens is None:
            self.artist_tokens = TrackNormalizer.extract_artist_tokens(self.artist)
        if self.is_music is None:
            self.is_music = ContentFilter.is_music_content(self.title, self.artist)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert track to dictionary format."""
        return asdict(self)
    
    def __hash__(self) -> int:
        """Make tracks hashable for use in sets."""
        return hash((self.normalized_title, self.normalized_artist, self.duration))


class Library:
    """Collection of tracks with metadata and analysis capabilities."""
    
    def __init__(self, name: str, platform: str = "unknown"):
        self.name = name
        self.platform = platform
        self.tracks: List[Track] = []
        self._music_tracks: Optional[List[Track]] = None
        self._artist_counts: Optional[Dict[str, int]] = None
    
    def add_track(self, track: Track) -> None:
        """Add a track to the library."""
        track.platform = self.platform
        self.tracks.append(track)
        # Invalidate cached computations
        self._music_tracks = None
        self._artist_counts = None
    
    def add_tracks(self, tracks: List[Track]) -> None:
        """Add multiple tracks to the library."""
        for track in tracks:
            self.add_track(track)
    
    @property
    def music_tracks(self) -> List[Track]:
        """Get only music tracks (filtered content)."""
        if self._music_tracks is None:
            self._music_tracks = [t for t in self.tracks if t.is_music]
        return self._music_tracks
    
    @property
    def total_tracks(self) -> int:
        """Total number of tracks in library."""
        return len(self.tracks)
    
    @property
    def music_count(self) -> int:
        """Number of music tracks (excluding podcasts, etc.)."""
        return len(self.music_tracks)
    
    @property
    def non_music_count(self) -> int:
        """Number of non-music tracks."""
        return self.total_tracks - self.music_count
    
    @property
    def artist_counts(self) -> Dict[str, int]:
        """Count tracks by artist."""
        if self._artist_counts is None:
            self._artist_counts = defaultdict(int)
            for track in self.music_tracks:
                self._artist_counts[track.normalized_artist] += 1
        return dict(self._artist_counts)
    
    @property
    def top_artists(self) -> List[Tuple[str, int]]:
        """Get top artists by track count."""
        return sorted(self.artist_counts.items(), key=lambda x: x[1], reverse=True)[:10]
    
    def get_stats(self) -> Dict[str, Any]:
        """Get library statistics."""
        return {
            'name': self.name,
            'platform': self.platform,
            'total_tracks': self.total_tracks,
            'music_tracks': self.music_count,
            'non_music_tracks': self.non_music_count,
            'unique_artists': len(self.artist_counts),
            'top_artists': self.top_artists[:5]
        }


class TrackNormalizer:
    """Utilities for normalizing track metadata for comparison."""
    
    # Patterns for cleaning track titles
    FEATURING_PATTERNS = [
        r'\s*\(\s*[Ff]eat\.?\s+.*?\)',
        r'\s*\(\s*[Ff]t\.?\s+.*?\)',
        r'\s*\(\s*[Ww]ith\s+.*?\)',
        r'\s*\(\s*&\s+.*?\)',
        r'\s*[Ff]eat\.?\s+.*',
        r'\s*[Ff]t\.?\s+.*',
    ]
    
    # Version/remix indicators to preserve
    VERSION_PATTERNS = [
        r'\([^)]*[Rr]emix[^)]*\)',
        r'\([^)]*[Vv]ersion[^)]*\)',
        r'\([^)]*[Rr]emaster[^)]*\)',
        r'\([^)]*[Ll]ive[^)]*\)',
        r'\([^)]*[Aa]coustic[^)]*\)',
        r'\([^)]*[Ii]nstrumental[^)]*\)',
        r'\([^)]*[Dd]eluxe[^)]*\)',
        r'\([^)]*[Ee]xtended[^)]*\)',
    ]
    
    @staticmethod
    def normalize_title(title: str) -> str:
        """Normalize track title for comparison."""
        if not title:
            return ""
        
        # Basic cleaning
        normalized = title.strip().lower()
        
        # Remove extra whitespace
        normalized = re.sub(r'\s+', ' ', normalized)
        
        # Preserve version info but remove other parentheses
        versions = []
        for pattern in TrackNormalizer.VERSION_PATTERNS:
            matches = re.findall(pattern, normalized, re.IGNORECASE)
            versions.extend(matches)
            normalized = re.sub(pattern, '', normalized, flags=re.IGNORECASE)
        
        # Remove other parentheses content
        normalized = re.sub(r'\([^)]*\)', '', normalized)
        normalized = re.sub(r'\[[^\]]*\]', '', normalized)
        
        # Add back version info
        if versions:
            normalized += ' ' + ' '.join(versions)
        
        # Remove common prefixes/suffixes
        normalized = re.sub(r'^(the\s+)', '', normalized)
        normalized = re.sub(r'\s+(the)$', '', normalized)
        
        # Remove punctuation
        normalized = re.sub(r'[^\w\s]', ' ', normalized)
        normalized = re.sub(r'\s+', ' ', normalized).strip()
        
        return normalized
    
    @staticmethod
    def normalize_artist(artist: str) -> str:
        """Normalize artist name for comparison."""
        if not artist:
            return ""
        
        normalized = artist.strip().lower()
        
        # Remove featuring artists
        for pattern in TrackNormalizer.FEATURING_PATTERNS:
            normalized = re.sub(pattern, '', normalized, flags=re.IGNORECASE)
        
        # Remove common suffixes
        normalized = re.sub(r'\s+(jr\.?|sr\.?|iii?|iv)$', '', normalized, flags=re.IGNORECASE)
        
        # Remove extra whitespace
        normalized = re.sub(r'\s+', ' ', normalized).strip()
        
        return normalized
    
    @staticmethod
    def extract_artist_tokens(artist: str) -> Set[str]:
        """Extract individual artist tokens for matching."""
        if not artist:
            return set()
        
        # Normalize first
        normalized = TrackNormalizer.normalize_artist(artist)
        
        # Split on common separators
        separators = [',', '&', ' and ', ' with ', ' feat ', ' ft ', ' featuring ']
        tokens = [normalized]
        
        for sep in separators:
            new_tokens = []
            for token in tokens:
                new_tokens.extend([t.strip() for t in token.split(sep)])
            tokens = new_tokens
        
        # Clean each token
        clean_tokens = set()
        for token in tokens:
            token = token.strip()
            if token and len(token) > 1:
                # Remove common words
                if token not in {'various artists', 'ost', 'soundtrack', 'va'}:
                    clean_tokens.add(token)
        
        return clean_tokens
    
    @staticmethod
    def parse_duration(duration_str: str) -> Optional[int]:
        """Parse duration string to seconds."""
        if not duration_str:
            return None
        
        try:
            # Handle milliseconds (Spotify format)
            if isinstance(duration_str, (int, float)) or duration_str.isdigit():
                ms = int(float(duration_str))
                return ms // 1000 if ms > 1000 else ms
            
            # Handle MM:SS format
            if ':' in str(duration_str):
                parts = str(duration_str).split(':')
                if len(parts) == 2:
                    minutes, seconds = int(parts[0]), int(parts[1])
                    return minutes * 60 + seconds
                elif len(parts) == 3:
                    hours, minutes, seconds = int(parts[0]), int(parts[1]), int(parts[2])
                    return hours * 3600 + minutes * 60 + seconds
            
            # Try direct conversion
            return int(float(duration_str))
        
        except (ValueError, AttributeError):
            return None


class ContentFilter:
    """Filter non-music content from libraries."""
    
    NON_MUSIC_PATTERNS = [
        # Podcasts and interviews
        r'\b(podcast|interview|talk|discussion)\b',
        r'\b(episode|ep\.|chapter)\s*\d+',
        
        # YouTube specific content
        r'\b(youtube\s+shorts?|shorts?)\b',
        r'\b(vlog|tutorial|review|reaction)\b',
        r'\b(behind\s+the\s+scenes|making\s+of)\b',
        
        # Non-music audio
        r'\b(audiobook|meditation|sleep|rain|nature)\b',
        r'\b(comedy|stand\-?up|funny)\b',
        
        # Live/performance indicators (often lower quality)
        r'\b(live\s+from|recorded\s+live)\b',
        r'\b(concert\s+recording|bootleg)\b',
        
        # Inappropriate content
        r'\b(explicit|nsfw|adult)\b'
    ]
    
    @staticmethod
    def is_music_content(title: str, artist: str) -> bool:
        """Determine if track is likely music content."""
        if not title and not artist:
            return False
        
        # Combine title and artist for checking
        combined = f"{title} {artist}".lower()
        
        # Check against non-music patterns
        for pattern in ContentFilter.NON_MUSIC_PATTERNS:
            if re.search(pattern, combined, re.IGNORECASE):
                return False
        
        # Additional heuristics
        if len(title) > 150:  # Very long titles often non-music
            return False
        
        if 'various artists' in artist.lower() and any(word in title.lower() 
                                                      for word in ['mix', 'compilation', 'collection']):
            return True  # Compilations are still music
        
        return True


class TrackMatcher:
    """Advanced track matching with configurable algorithms and performance optimizations."""
    
    def __init__(self, strict_mode: bool = True, enable_duration: bool = True, 
                 enable_album: bool = False):
        self.strict_mode = strict_mode
        self.enable_duration = enable_duration
        self.enable_album = enable_album
        
        # Confidence thresholds
        if strict_mode:
            self.title_threshold = 0.90
            self.artist_overlap_threshold = 0.45
            self.duration_tolerance = 7  # seconds (slightly more lenient cross-platform)
        else:
            self.title_threshold = 0.85
            self.artist_overlap_threshold = 0.30
            self.duration_tolerance = 9
        
        # Performance optimization indices
        self._exact_hash_index: Dict[str, List[Track]] = defaultdict(list)
        self._isrc_index: Dict[str, Track] = {}
        self._artist_word_index: Dict[str, List[Track]] = defaultdict(list)
        self._title_word_index: Dict[str, List[Track]] = defaultdict(list)
        self._indexed_candidates: Set[int] = set()
        
        # Memoization cache for expensive similarity calculations
        self._similarity_cache: Dict[Tuple[str, str], float] = {}
    
    def _cached_string_similarity(self, str1: str, str2: str) -> float:
        """Cached string similarity calculation for performance."""
        if not str1 or not str2:
            return 0.0
        
        # Normalize and create cache key
        str1_norm = str1.strip().lower()
        str2_norm = str2.strip().lower()
        
        if str1_norm == str2_norm:
            return 1.0
        
        # Create deterministic cache key
        cache_key = (str1_norm, str2_norm) if str1_norm < str2_norm else (str2_norm, str1_norm)
        
        if cache_key in self._similarity_cache:
            return self._similarity_cache[cache_key]
        
        # Calculate similarity
        if HAVE_RAPIDFUZZ:
            similarity = fuzz.ratio(str1_norm, str2_norm) / 100.0
        else:
            # Simple fallback similarity
            similarity = 1.0 if str1_norm == str2_norm else 0.0
        
        # Cache the result
        self._similarity_cache[cache_key] = similarity
        return similarity
    
    def _create_exact_hash(self, track: Track) -> str:
        """Create a hash for exact matching based on normalized title and artist."""
        if not track.normalized_title or not track.normalized_artist:
            return ""
        
        # Create deterministic hash from normalized content
        content = f"{track.normalized_title.lower()}|{track.normalized_artist.lower()}"
        return hashlib.md5(content.encode('utf-8')).hexdigest()
    
    def _build_optimization_indices(self, tracks: List[Track]) -> None:
        """Build performance optimization indices for tracks."""
        # Clear existing indices
        self._exact_hash_index.clear()
        self._isrc_index.clear()
        self._artist_word_index.clear()
        self._title_word_index.clear()
        self._indexed_candidates.clear()
        
        for track in tracks:
            if not track.is_music:  # Skip non-music content
                continue
                
            track_id = id(track)
            if track_id in self._indexed_candidates:
                continue
                
            self._indexed_candidates.add(track_id)
            
            # Exact hash index for fast exact matches
            exact_hash = self._create_exact_hash(track)
            if exact_hash:
                self._exact_hash_index[exact_hash].append(track)
            
            # ISRC index for instant ISRC matches
            if track.isrc:
                isrc_key = track.isrc.strip().upper()
                if isrc_key not in self._isrc_index:  # Avoid duplicates
                    self._isrc_index[isrc_key] = track
            
            # Word-based indices for pre-filtering
            if track.normalized_artist:
                artist_words = track.normalized_artist.lower().split()
                for word in artist_words:
                    if len(word) > 2:  # Skip very short words
                        self._artist_word_index[word].append(track)
            
            if track.normalized_title:
                title_words = track.normalized_title.lower().split()
                for word in title_words:
                    if len(word) > 2:  # Skip very short words
                        self._title_word_index[word].append(track)
    
    def _get_candidate_subset(self, target_track: Track, all_candidates: List[Track]) -> List[Track]:
        """Get a filtered subset of candidates for performance optimization."""
        # 1. Try exact hash match first
        exact_hash = self._create_exact_hash(target_track)
        if exact_hash and exact_hash in self._exact_hash_index:
            return self._exact_hash_index[exact_hash]
        
        # 2. Try ISRC match
        if target_track.isrc:
            isrc_key = target_track.isrc.strip().upper()
            if isrc_key in self._isrc_index:
                return [self._isrc_index[isrc_key]]
        
        # 3. Get candidates based on word overlap
        potential_matches = set()
        
        # Check title words
        if target_track.normalized_title:
            title_words = target_track.normalized_title.lower().split()
            for word in title_words:
                if len(word) > 2 and word in self._title_word_index:
                    potential_matches.update(self._title_word_index[word])
        
        # Check artist words
        if target_track.normalized_artist:
            artist_words = target_track.normalized_artist.lower().split()
            for word in artist_words:
                if len(word) > 2 and word in self._artist_word_index:
                    potential_matches.update(self._artist_word_index[word])
        
        # Return filtered candidates or limited fallback
        if potential_matches:
            filtered = [track for track in all_candidates if track in potential_matches]
            return filtered if filtered else all_candidates[:min(100, len(all_candidates))]
        
        # If no word matches, limit search for performance
        return all_candidates[:min(50, len(all_candidates))]
    
    def calculate_match_confidence(self, track1: Track, track2: Track) -> float:
        """Calculate overall match confidence between two tracks."""
        
        # ISRC exact match - instant 100% confidence
        if (track1.isrc and track2.isrc and 
            track1.isrc.strip().lower() == track2.isrc.strip().lower()):
            return 1.0
        
        scores = {}
        
        # Title similarity (45% weight)
        title_score = self._calculate_title_similarity(track1.normalized_title, track2.normalized_title)
        scores['title'] = (title_score, 0.45)
        
        # Artist similarity (35% weight)  
        artist_score = self._calculate_artist_similarity(track1, track2)
        scores['artist'] = (artist_score, 0.35)
        
        # Album similarity (10% weight)
        if self.enable_album and track1.album and track2.album:
            album_score = self._calculate_album_similarity(track1.album, track2.album)
            scores['album'] = (album_score, 0.10)
        else:
            scores['album'] = (0.5, 0.10)  # Neutral score when no album
        
        # Duration similarity (10% weight)
        if self.enable_duration and track1.duration and track2.duration:
            duration_score = self._calculate_duration_similarity(track1.duration, track2.duration)
            scores['duration'] = (duration_score, 0.05)
        else:
            scores['duration'] = (0.5, 0.05)  # Neutral score when no duration
        
        # Calculate weighted average
        total_score = 0
        total_weight = 0
        for score, weight in scores.values():
            total_score += score * weight
            total_weight += weight
        
        return total_score / total_weight if total_weight > 0 else 0.0
    
    def _calculate_title_similarity(self, title1: str, title2: str) -> float:
        """Calculate title similarity with dynamic thresholds."""
        if not title1 or not title2:
            return 0.0
        
        if not HAVE_RAPIDFUZZ:
            # Fallback to simple comparison
            return 1.0 if title1.lower() == title2.lower() else 0.0
        
        # Use multiple fuzzy matching methods
        token_set = fuzz.token_set_ratio(title1, title2) / 100.0
        token_sort = fuzz.token_sort_ratio(title1, title2) / 100.0
        partial = fuzz.partial_ratio(title1, title2) / 100.0
        
        # Weight the methods
        combined_score = (token_set * 0.4 + token_sort * 0.4 + partial * 0.2)
        
        # Apply dynamic thresholds as soft minimums (do not hard-zero)
        word_count = max(len(title1.split()), len(title2.split()))
        if word_count < 3:
            # Stricter for short titles
            threshold = 0.96 if self.strict_mode else 0.92
        else:
            # More lenient for longer titles
            threshold = 0.92 if self.strict_mode else 0.85

        # Scale up scores above threshold slightly; keep sub-threshold scores instead of zeroing
        if combined_score >= threshold:
            # Small boost to emphasize strong matches
            return min(1.0, combined_score * 1.02)
        return combined_score
    
    def _calculate_artist_similarity(self, track1: Track, track2: Track) -> float:
        """Calculate artist similarity using token analysis."""
        tokens1 = track1.artist_tokens
        tokens2 = track2.artist_tokens
        
        if not tokens1 or not tokens2:
            # Fallback to cached string similarity when tokenization fails
            return self._cached_string_similarity(track1.normalized_artist, track2.normalized_artist)
        
        # Jaccard similarity (intersection over union)
        intersection = tokens1.intersection(tokens2)
        union = tokens1.union(tokens2)
        jaccard = len(intersection) / len(union) if union else 0.0
        
        # Check for subset relationships (bonus scoring)
        containment = 0.0
        if tokens1.issubset(tokens2) or tokens2.issubset(tokens1):
            containment = 0.3
        
        # Combined score
        combined_score = jaccard + containment
        # Do not hard-zero; return graded similarity but note threshold later
        return min(1.0, combined_score)
    
    def _calculate_album_similarity(self, album1: str, album2: str) -> float:
        """Calculate album similarity."""
        if not album1 or not album2:
            return 0.5  # Neutral when missing
        
        if not HAVE_RAPIDFUZZ:
            return 1.0 if album1.lower() == album2.lower() else 0.0
        
        similarity = fuzz.token_sort_ratio(album1.lower(), album2.lower()) / 100.0
        return similarity if similarity >= 0.8 else 0.0
    
    def _calculate_duration_similarity(self, duration1: int, duration2: int) -> float:
        """Calculate duration similarity."""
        if not duration1 or not duration2:
            return 0.5  # Neutral when missing
        
        diff = abs(duration1 - duration2)
        
        # Check absolute difference
        if diff <= self.duration_tolerance:
            return 1.0
        
        # Check percentage difference
        longer = max(duration1, duration2)
        percentage_diff = diff / longer
        # Provide a graded score rather than binary cutoff
        soft_limit = 0.08 if self.strict_mode else 0.12
        if percentage_diff <= soft_limit:
            # Linearly decay from 1.0 at tolerance to 0.6 at soft_limit
            return max(0.6, 1.0 - (percentage_diff / soft_limit) * 0.4)
        return 0.0
    
    def find_best_match(self, target_track: Track, candidate_tracks: List[Track]) -> Optional[Tuple[Track, float]]:
        """Find the best matching track from candidates with performance optimizations."""
        if not candidate_tracks:
            return None
        
        # Build indices if not already done or if candidates changed
        if not self._indexed_candidates:
            self._build_optimization_indices(candidate_tracks)
        
        # Get optimized subset of candidates
        candidates_to_check = self._get_candidate_subset(target_track, candidate_tracks)
        
        best_match = None
        best_confidence = 0.0
        
        for candidate in candidates_to_check:
            if not candidate.is_music:  # Skip non-music content
                continue
            
            confidence = self.calculate_match_confidence(target_track, candidate)
            
            if confidence > best_confidence:
                best_match = candidate
                best_confidence = confidence
                
                # Early termination for high confidence matches
                if confidence >= 0.98:
                    break
        
        # Require a minimum confidence that varies with strictness
        min_conf = 0.80 if self.strict_mode else 0.72
        return (best_match, best_confidence) if best_match and best_confidence >= min_conf else None
