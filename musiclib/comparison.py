"""
Library comparison functionality for finding matches and differences between platforms.
"""

import json
import csv
from typing import Dict, List, Optional, Set, Tuple, Any
from dataclasses import dataclass, asdict
from pathlib import Path
from collections import defaultdict
import time

from .core import Track, Library, TrackMatcher


@dataclass
class MatchResult:
    """Represents a match between two tracks."""
    source_track: Track
    target_track: Track
    confidence: float
    match_type: str  # 'exact', 'fuzzy', 'isrc'
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format."""
        return {
            'source_track': self.source_track.to_dict(),
            'target_track': self.target_track.to_dict(),
            'confidence': self.confidence,
            'match_type': self.match_type
        }


@dataclass
class ComparisonResult:
    """Results from comparing two libraries."""
    source_library: str
    target_library: str
    total_source_tracks: int
    total_target_tracks: int
    music_source_tracks: int
    music_target_tracks: int
    
    matches: List[MatchResult]
    missing_tracks: List[Track]  # Tracks in source but not in target
    
    # Statistics
    exact_matches: int = 0
    fuzzy_matches: int = 0
    isrc_matches: int = 0
    total_matches: int = 0
    match_rate: float = 0.0
    avg_confidence: float = 0.0
    
    def __post_init__(self):
        """Calculate statistics after initialization."""
        self.total_matches = len(self.matches)
        
        if self.matches:
            # Count match types
            for match in self.matches:
                if match.match_type == 'exact':
                    self.exact_matches += 1
                elif match.match_type == 'fuzzy':
                    self.fuzzy_matches += 1
                elif match.match_type == 'isrc':
                    self.isrc_matches += 1
            
            # Calculate averages
            self.avg_confidence = sum(m.confidence for m in self.matches) / len(self.matches)
        
        # Calculate match rate
        if self.music_source_tracks > 0:
            self.match_rate = self.total_matches / self.music_source_tracks
    
    def get_stats(self) -> Dict[str, Any]:
        """Get comparison statistics."""
        return {
            'source_library': self.source_library,
            'target_library': self.target_library,
            'total_source_tracks': self.total_source_tracks,
            'total_target_tracks': self.total_target_tracks,
            'music_source_tracks': self.music_source_tracks,
            'music_target_tracks': self.music_target_tracks,
            'total_matches': self.total_matches,
            'exact_matches': self.exact_matches,
            'fuzzy_matches': self.fuzzy_matches,
            'isrc_matches': self.isrc_matches,
            'missing_tracks': len(self.missing_tracks),
            'match_rate': round(self.match_rate * 100, 2),
            'avg_confidence': round(self.avg_confidence * 100, 2)
        }
    
    def save_results(self, output_dir: str, base_filename: str = None) -> Dict[str, str]:
        """Save comparison results to files."""
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        if not base_filename:
            source_clean = self.source_library.lower().replace(' ', '_').replace('-', '_')
            target_clean = self.target_library.lower().replace(' ', '_').replace('-', '_')
            base_filename = f"{source_clean}_vs_{target_clean}"
        
        files_created = {}
        
        # Save matches
        if self.matches:
            matches_file = output_path / f"{base_filename}_matched.csv"
            self._save_matches_csv(matches_file)
            files_created['matches'] = str(matches_file)
        
        # Save missing tracks
        if self.missing_tracks:
            missing_file = output_path / f"{base_filename}_missing_from_{target_clean}.csv"
            self._save_missing_csv(missing_file)
            files_created['missing'] = str(missing_file)
        
        # Save summary
        summary_file = output_path / f"{base_filename}_summary.json"
        self._save_summary_json(summary_file)
        files_created['summary'] = str(summary_file)
        
        return files_created
    
    def _save_matches_csv(self, file_path: Path) -> None:
        """Save matched tracks to CSV."""
        with open(file_path, 'w', newline='', encoding='utf-8') as f:
            fieldnames = [
                'source_title', 'source_artist', 'source_album', 'source_duration',
                'target_title', 'target_artist', 'target_album', 'target_duration',
                'confidence', 'match_type', 'source_platform', 'target_platform'
            ]
            
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            
            for match in self.matches:
                writer.writerow({
                    'source_title': match.source_track.title,
                    'source_artist': match.source_track.artist,
                    'source_album': match.source_track.album or '',
                    'source_duration': match.source_track.duration or '',
                    'target_title': match.target_track.title,
                    'target_artist': match.target_track.artist,
                    'target_album': match.target_track.album or '',
                    'target_duration': match.target_track.duration or '',
                    'confidence': round(match.confidence * 100, 2),
                    'match_type': match.match_type,
                    'source_platform': match.source_track.platform or '',
                    'target_platform': match.target_track.platform or ''
                })
    
    def _save_missing_csv(self, file_path: Path) -> None:
        """Save missing tracks to CSV."""
        with open(file_path, 'w', newline='', encoding='utf-8') as f:
            fieldnames = [
                'title', 'artist', 'album', 'duration', 'isrc', 
                'platform', 'track_id', 'url', 'year', 'genre'
            ]
            
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            
            for track in self.missing_tracks:
                writer.writerow({
                    'title': track.title,
                    'artist': track.artist,
                    'album': track.album or '',
                    'duration': track.duration or '',
                    'isrc': track.isrc or '',
                    'platform': track.platform or '',
                    'track_id': track.track_id or '',
                    'url': track.url or '',
                    'year': track.year or '',
                    'genre': track.genre or ''
                })
    
    def _save_summary_json(self, file_path: Path) -> None:
        """Save summary statistics to JSON."""
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(self.get_stats(), f, indent=2, ensure_ascii=False)


class LibraryComparator:
    """Main class for comparing music libraries."""
    
    def __init__(self, strict_mode: bool = True, enable_duration: bool = True, 
                 enable_album: bool = False, progress_callback: Optional[callable] = None):
        self.matcher = TrackMatcher(strict_mode, enable_duration, enable_album)
        self.progress_callback = progress_callback
    
    def compare_libraries(self, source_library: Library, target_library: Library) -> ComparisonResult:
        """Compare two libraries and return detailed results."""
        
        # Filter to music tracks only
        source_music = source_library.music_tracks
        target_music = target_library.music_tracks
        
        matches = []
        missing_tracks = []
        processed = 0
        
        # Create lookup indices for faster matching
        target_by_isrc = {}
        target_by_normalized = {}
        
        for track in target_music:
            if track.isrc:
                target_by_isrc[track.isrc.lower()] = track
            
            key = (track.normalized_title, track.normalized_artist)
            if key not in target_by_normalized:
                target_by_normalized[key] = []
            target_by_normalized[key].append(track)
        
        # Process each source track
        for source_track in source_music:
            if self.progress_callback:
                self.progress_callback(processed, len(source_music), f"Processing: {source_track.title}")
            
            match_result = self._find_match(source_track, target_music, target_by_isrc, target_by_normalized)
            
            if match_result:
                matches.append(match_result)
            else:
                missing_tracks.append(source_track)
            
            processed += 1
        
        if self.progress_callback:
            self.progress_callback(processed, len(source_music), "Comparison complete")
        
        return ComparisonResult(
            source_library=source_library.name,
            target_library=target_library.name,
            total_source_tracks=source_library.total_tracks,
            total_target_tracks=target_library.total_tracks,
            music_source_tracks=len(source_music),
            music_target_tracks=len(target_music),
            matches=matches,
            missing_tracks=missing_tracks
        )
    
    def _find_match(self, source_track: Track, target_tracks: List[Track], 
                   target_by_isrc: Dict[str, Track], 
                   target_by_normalized: Dict[Tuple[str, str], List[Track]]) -> Optional[MatchResult]:
        """Find the best match for a source track."""
        
        # 1. Try ISRC exact match first
        if source_track.isrc:
            isrc_match = target_by_isrc.get(source_track.isrc.lower())
            if isrc_match:
                return MatchResult(
                    source_track=source_track,
                    target_track=isrc_match,
                    confidence=1.0,
                    match_type='isrc'
                )
        
        # 2. Try exact normalized match
        exact_key = (source_track.normalized_title, source_track.normalized_artist)
        exact_candidates = target_by_normalized.get(exact_key, [])
        
        if exact_candidates:
            # If multiple exact matches, pick the best one based on other factors
            best_candidate = exact_candidates[0]
            best_confidence = 0.95  # High confidence for exact normalized match
            
            if len(exact_candidates) > 1:
                # Use additional factors to pick the best
                for candidate in exact_candidates:
                    candidate_confidence = self.matcher.calculate_match_confidence(source_track, candidate)
                    if candidate_confidence > best_confidence:
                        best_candidate = candidate
                        best_confidence = candidate_confidence
            
            return MatchResult(
                source_track=source_track,
                target_track=best_candidate,
                confidence=best_confidence,
                match_type='exact'
            )
        
        # 3. Try fuzzy matching
        match_result = self.matcher.find_best_match(source_track, target_tracks)
        if match_result:
            matched_track, confidence = match_result
            return MatchResult(
                source_track=source_track,
                target_track=matched_track,
                confidence=confidence,
                match_type='fuzzy'
            )
        
        return None
    
    def analyze_libraries(self, libraries: List[Library]) -> Dict[str, Any]:
        """Analyze multiple libraries for overlap and statistics."""
        if len(libraries) < 2:
            raise ValueError("Need at least 2 libraries to analyze")
        
        analysis = {
            'libraries': [],
            'pairwise_comparisons': [],
            'overlap_analysis': {},
            'universal_tracks': [],
            'unique_tracks': {},
            'artist_analysis': {}
        }
        
        # Basic library stats
        for library in libraries:
            analysis['libraries'].append(library.get_stats())
        
        # Pairwise comparisons
        for i in range(len(libraries)):
            for j in range(i + 1, len(libraries)):
                comparison = self.compare_libraries(libraries[i], libraries[j])
                analysis['pairwise_comparisons'].append({
                    'source': libraries[i].name,
                    'target': libraries[j].name,
                    'stats': comparison.get_stats()
                })
        
        # Find universal tracks (appear in all libraries)
        if len(libraries) >= 2:
            analysis['universal_tracks'] = self._find_universal_tracks(libraries)
        
        # Find unique tracks per library
        analysis['unique_tracks'] = self._find_unique_tracks(libraries)
        
        # Artist overlap analysis
        analysis['artist_analysis'] = self._analyze_artists(libraries)
        
        return analysis
    
    def _find_universal_tracks(self, libraries: List[Library]) -> List[Dict[str, Any]]:
        """Find tracks that appear in all libraries."""
        if not libraries:
            return []
        
        # Start with the first library's tracks
        universal_candidates = set()
        for track in libraries[0].music_tracks:
            universal_candidates.add((track.normalized_title, track.normalized_artist))
        
        # Check each subsequent library
        for library in libraries[1:]:
            library_tracks = set()
            for track in library.music_tracks:
                library_tracks.add((track.normalized_title, track.normalized_artist))
            
            universal_candidates &= library_tracks
        
        # Convert back to track info
        universal_tracks = []
        for title, artist in universal_candidates:
            # Find a representative track from the first library
            for track in libraries[0].music_tracks:
                if (track.normalized_title, track.normalized_artist) == (title, artist):
                    universal_tracks.append({
                        'title': track.title,
                        'artist': track.artist,
                        'album': track.album,
                        'appears_in': len(libraries)
                    })
                    break
        
        return sorted(universal_tracks, key=lambda x: (x['artist'], x['title']))
    
    def _find_unique_tracks(self, libraries: List[Library]) -> Dict[str, List[Dict[str, Any]]]:
        """Find tracks unique to each library."""
        unique_tracks = {}
        
        for i, library in enumerate(libraries):
            library_unique = []
            library_tracks = set()
            
            for track in library.music_tracks:
                library_tracks.add((track.normalized_title, track.normalized_artist))
            
            # Check against all other libraries
            for track in library.music_tracks:
                track_key = (track.normalized_title, track.normalized_artist)
                is_unique = True
                
                for j, other_library in enumerate(libraries):
                    if i == j:
                        continue
                    
                    for other_track in other_library.music_tracks:
                        other_key = (other_track.normalized_title, other_track.normalized_artist)
                        if track_key == other_key:
                            is_unique = False
                            break
                    
                    if not is_unique:
                        break
                
                if is_unique:
                    library_unique.append({
                        'title': track.title,
                        'artist': track.artist,
                        'album': track.album
                    })
            
            unique_tracks[library.name] = sorted(library_unique, key=lambda x: (x['artist'], x['title']))
        
        return unique_tracks
    
    def _analyze_artists(self, libraries: List[Library]) -> Dict[str, Any]:
        """Analyze artist overlap between libraries."""
        artist_analysis = {
            'total_unique_artists': 0,
            'universal_artists': [],
            'library_artists': {},
            'top_overlap_artists': []
        }
        
        # Collect artists from all libraries
        all_artists = set()
        library_artists = {}
        
        for library in libraries:
            library_artist_set = set(library.artist_counts.keys())
            library_artists[library.name] = library_artist_set
            all_artists.update(library_artist_set)
        
        artist_analysis['total_unique_artists'] = len(all_artists)
        artist_analysis['library_artists'] = {name: len(artists) for name, artists in library_artists.items()}
        
        # Find universal artists
        if libraries:
            universal_artists = library_artists[libraries[0].name]
            for library in libraries[1:]:
                universal_artists &= library_artists[library.name]
            
            artist_analysis['universal_artists'] = sorted(list(universal_artists))
        
        # Find top artists by total tracks across libraries
        artist_totals = defaultdict(int)
        for library in libraries:
            for artist, count in library.artist_counts.items():
                artist_totals[artist] += count
        
        artist_analysis['top_overlap_artists'] = sorted(
            artist_totals.items(), 
            key=lambda x: x[1], 
            reverse=True
        )[:20]
        
        return artist_analysis