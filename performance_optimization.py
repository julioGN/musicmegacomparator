#!/usr/bin/env python3
"""
Performance optimization utilities for MusicLib.

This module provides enhanced algorithms and caching mechanisms
to improve performance on large libraries.
"""

import os
import hashlib
import pickle
import time
from functools import lru_cache
from typing import Dict, List, Optional, Set, Tuple, Any
from pathlib import Path

# Enhanced caching for comparison results
class ComparisonCache:
    """Cache for comparison results to avoid recomputation."""
    
    def __init__(self, cache_dir: str = ".musiclib_cache"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
    
    def _get_library_hash(self, library_path: str) -> str:
        """Generate a hash for a library file."""
        with open(library_path, 'rb') as f:
            file_hash = hashlib.md5(f.read()).hexdigest()
        return file_hash
    
    def _get_cache_key(self, source_path: str, target_path: str, params: Dict[str, Any]) -> str:
        """Generate cache key for comparison."""
        source_hash = self._get_library_hash(source_path)
        target_hash = self._get_library_hash(target_path)
        param_str = str(sorted(params.items()))
        return f"{source_hash}_{target_hash}_{hashlib.md5(param_str.encode()).hexdigest()}"
    
    def get_cached_result(self, source_path: str, target_path: str, params: Dict[str, Any]) -> Optional[Any]:
        """Get cached comparison result."""
        cache_key = self._get_cache_key(source_path, target_path, params)
        cache_file = self.cache_dir / f"{cache_key}.pkl"
        
        if cache_file.exists():
            try:
                with open(cache_file, 'rb') as f:
                    return pickle.load(f)
            except Exception:
                # Cache corrupted, remove it
                cache_file.unlink(missing_ok=True)
        
        return None
    
    def cache_result(self, source_path: str, target_path: str, params: Dict[str, Any], result: Any) -> None:
        """Cache comparison result."""
        cache_key = self._get_cache_key(source_path, target_path, params)
        cache_file = self.cache_dir / f"{cache_key}.pkl"
        
        try:
            with open(cache_file, 'wb') as f:
                pickle.dump(result, f)
        except Exception:
            pass  # Cache write failed, continue without caching


class PerformanceOptimizer:
    """Performance optimization utilities."""
    
    @staticmethod
    def chunk_tracks(tracks: List[Any], chunk_size: int = 1000) -> List[List[Any]]:
        """Split tracks into smaller chunks for batch processing."""
        chunks = []
        for i in range(0, len(tracks), chunk_size):
            chunks.append(tracks[i:i + chunk_size])
        return chunks
    
    @staticmethod
    @lru_cache(maxsize=10000)
    def cached_normalize_title(title: str) -> str:
        """Cached version of title normalization."""
        from musiclib.core import TrackNormalizer
        return TrackNormalizer.normalize_title(title)
    
    @staticmethod
    @lru_cache(maxsize=10000)
    def cached_normalize_artist(artist: str) -> str:
        """Cached version of artist normalization."""
        from musiclib.core import TrackNormalizer
        return TrackNormalizer.normalize_artist(artist)
    
    @staticmethod
    @lru_cache(maxsize=5000)
    def cached_extract_artist_tokens(artist: str) -> Set[str]:
        """Cached version of artist token extraction."""
        from musiclib.core import TrackNormalizer
        return TrackNormalizer.extract_artist_tokens(artist)
    
    @staticmethod
    def build_artist_index(tracks: List[Any]) -> Dict[str, List[Any]]:
        """Build an index of tracks by artist for faster lookup."""
        artist_index = {}
        for track in tracks:
            artist = track.normalized_artist.lower()
            if artist not in artist_index:
                artist_index[artist] = []
            artist_index[artist].append(track)
        return artist_index
    
    @staticmethod
    def build_title_index(tracks: List[Any]) -> Dict[str, List[Any]]:
        """Build an index of tracks by title for faster lookup."""
        title_index = {}
        for track in tracks:
            title = track.normalized_title.lower()
            if title not in title_index:
                title_index[title] = []
            title_index[title].append(track)
        return title_index
    
    @staticmethod
    def memory_efficient_comparison(source_tracks: List[Any], target_tracks: List[Any], 
                                  matcher, chunk_size: int = 1000) -> Tuple[List[Any], List[Any]]:
        """Memory-efficient comparison for very large libraries."""
        matches = []
        missing = []
        
        # Build indices for target tracks
        target_by_isrc = {}
        target_by_normalized = {}
        target_by_artist = PerformanceOptimizer.build_artist_index(target_tracks)
        
        for track in target_tracks:
            if track.isrc:
                target_by_isrc[track.isrc.lower()] = track
            
            key = (track.normalized_title, track.normalized_artist)
            if key not in target_by_normalized:
                target_by_normalized[key] = []
            target_by_normalized[key].append(track)
        
        # Process source tracks in chunks
        chunks = PerformanceOptimizer.chunk_tracks(source_tracks, chunk_size)
        
        for chunk_idx, chunk in enumerate(chunks):
            print(f"Processing chunk {chunk_idx + 1}/{len(chunks)}")
            
            for source_track in chunk:
                # Try exact matches first (fastest)
                match_found = False
                
                # ISRC match
                if source_track.isrc and source_track.isrc.lower() in target_by_isrc:
                    match = target_by_isrc[source_track.isrc.lower()]
                    matches.append((source_track, match, 1.0, 'isrc'))
                    match_found = True
                    continue
                
                # Exact normalized match
                exact_key = (source_track.normalized_title, source_track.normalized_artist)
                if exact_key in target_by_normalized:
                    match = target_by_normalized[exact_key][0]
                    matches.append((source_track, match, 0.95, 'exact'))
                    match_found = True
                    continue
                
                # Fuzzy match within artist group (more efficient than full library scan)
                artist_candidates = target_by_artist.get(source_track.normalized_artist.lower(), [])
                if artist_candidates:
                    best_match = matcher.find_best_match(source_track, artist_candidates)
                    if best_match:
                        match, confidence = best_match
                        matches.append((source_track, match, confidence, 'fuzzy'))
                        match_found = True
                        continue
                
                # If no match in same artist, try broader search (limited)
                if not match_found:
                    # Only search a subset for performance
                    limited_targets = target_tracks[:min(5000, len(target_tracks))]
                    best_match = matcher.find_best_match(source_track, limited_targets)
                    if best_match:
                        match, confidence = best_match
                        matches.append((source_track, match, confidence, 'fuzzy'))
                    else:
                        missing.append(source_track)
        
        return matches, missing


class StreamingProcessor:
    """Process large files in streaming fashion to reduce memory usage."""
    
    @staticmethod
    def process_large_csv(file_path: str, processor_func, chunk_size: int = 10000):
        """Process large CSV files in chunks."""
        import pandas as pd
        
        chunks = []
        chunk_iter = pd.read_csv(file_path, chunksize=chunk_size)
        
        for chunk in chunk_iter:
            processed_chunk = processor_func(chunk)
            chunks.append(processed_chunk)
        
        return pd.concat(chunks, ignore_index=True) if chunks else pd.DataFrame()
    
    @staticmethod
    def process_large_xml(file_path: str, processor_func, batch_size: int = 1000):
        """Process large XML files in batches."""
        import xml.etree.ElementTree as ET
        
        # For very large XML files, consider using iterparse
        tree = ET.parse(file_path)
        root = tree.getroot()
        
        # Find tracks section
        tracks_dict = None
        for child in root:
            if child.tag == 'dict':
                for subchild in child:
                    if subchild.tag == 'key' and subchild.text == 'Tracks':
                        tracks_dict = subchild.getnext()
                        break
                if tracks_dict is not None:
                    break
        
        if tracks_dict is None:
            return []
        
        # Process tracks in batches
        results = []
        batch = []
        
        for i, child in enumerate(tracks_dict):
            if child.tag == 'dict':
                batch.append(child)
                
                if len(batch) >= batch_size:
                    processed_batch = processor_func(batch)
                    results.extend(processed_batch)
                    batch = []
        
        # Process remaining batch
        if batch:
            processed_batch = processor_func(batch)
            results.extend(processed_batch)
        
        return results


def optimize_library_loading():
    """Apply optimizations to library loading process."""
    # Monkey patch normalization functions with cached versions
    from musiclib import core
    
    core.TrackNormalizer.normalize_title = PerformanceOptimizer.cached_normalize_title
    core.TrackNormalizer.normalize_artist = PerformanceOptimizer.cached_normalize_artist
    core.TrackNormalizer.extract_artist_tokens = PerformanceOptimizer.cached_extract_artist_tokens


def benchmark_comparison(source_lib, target_lib, matcher):
    """Benchmark comparison performance."""
    start_time = time.time()
    
    # Standard comparison
    print("Running standard comparison...")
    std_start = time.time()
    matches, missing = PerformanceOptimizer.memory_efficient_comparison(
        source_lib.music_tracks[:1000], 
        target_lib.music_tracks[:1000], 
        matcher
    )
    std_time = time.time() - std_start
    
    total_time = time.time() - start_time
    
    print(f"Standard comparison: {std_time:.2f}s")
    print(f"Total time: {total_time:.2f}s")
    print(f"Matches found: {len(matches)}")
    print(f"Missing tracks: {len(missing)}")
    
    return {
        'standard_time': std_time,
        'total_time': total_time,
        'matches': len(matches),
        'missing': len(missing)
    }


if __name__ == "__main__":
    print("MusicLib Performance Optimization Module")
    print("This module provides caching and optimization utilities.")