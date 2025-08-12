#!/usr/bin/env python3
"""
Quick test of advanced duplicate detection (first 50 tracks only).
"""

import json
import logging
from pathlib import Path
from typing import List, Set, Dict, Any
from difflib import SequenceMatcher
import re

from ytmusicapi import YTMusic

def setup_logging():
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    return logging.getLogger(__name__)

def normalize_text(text: str) -> str:
    """Normalize text for comparison."""
    if not text:
        return ""
    
    # Remove version indicators
    text = re.sub(r'\s*\([^)]*(?:remaster|mix|version|edit|live|acoustic|demo|feat|featuring)[^)]*\)', '', text, flags=re.IGNORECASE)
    text = re.sub(r'\s*\[[^\]]*(?:remaster|mix|version|edit|live|acoustic|demo|feat|featuring)[^\]]*\]', '', text, flags=re.IGNORECASE)
    text = re.sub(r'\s*\(?\d{4}\)?', '', text)
    text = re.sub(r'[^\w\s]', '', text)
    text = re.sub(r'\s+', ' ', text)
    
    return text.lower().strip()

def similarity_score(text1: str, text2: str) -> float:
    """Calculate similarity between two strings."""
    return SequenceMatcher(None, text1, text2).ratio()

def get_artist_names(artists: List[Dict]) -> List[str]:
    """Extract artist names from artists list."""
    if not artists:
        return []
    return [artist.get('name', '') for artist in artists if artist.get('name')]

def find_similar_tracks(playlist_track: Dict, library_tracks: List[Dict], similarity_threshold: float = 0.8) -> List[Dict]:
    """Find tracks in library that are similar to the playlist track."""
    
    playlist_title = normalize_text(playlist_track.get('title', ''))
    playlist_artists = get_artist_names(playlist_track.get('artists', []))
    
    if not playlist_title or not playlist_artists:
        return []
    
    similar_tracks = []
    
    for lib_track in library_tracks:
        lib_title = normalize_text(lib_track.get('title', ''))
        lib_artists = get_artist_names(lib_track.get('artists', []))
        
        if not lib_title or not lib_artists:
            continue
        
        # Check if any artist matches
        artist_match = False
        for p_artist in playlist_artists:
            for l_artist in lib_artists:
                if similarity_score(normalize_text(p_artist), normalize_text(l_artist)) > 0.9:
                    artist_match = True
                    break
            if artist_match:
                break
        
        if artist_match:
            # Check title similarity
            title_similarity = similarity_score(playlist_title, lib_title)
            
            if title_similarity >= similarity_threshold:
                similar_tracks.append({
                    'library_track': lib_track,
                    'title_similarity': title_similarity,
                    'original_playlist_title': playlist_track.get('title'),
                    'original_library_title': lib_track.get('title'),
                    'normalized_playlist_title': playlist_title,
                    'normalized_library_title': lib_title
                })
    
    return similar_tracks

def main():
    logger = setup_logging()
    
    headers_path = "/Users/guerrero/Documents/musiccode/headers_auth.json"
    ytmusic = YTMusic(headers_path)
    
    playlist_id = "PL1LO5jourf4MqCSX94juP7bWk2eYTMCQ2"
    
    logger.info("Quick test: Getting first 50 playlist tracks...")
    playlist_data = ytmusic.get_playlist(playlist_id, limit=50)
    playlist_tracks = playlist_data.get('tracks', [])
    logger.info(f"Got {len(playlist_tracks)} playlist tracks")
    
    logger.info("Getting library songs...")
    library_tracks = ytmusic.get_library_songs(limit=None)
    logger.info(f"Got {len(library_tracks)} library tracks")
    
    # Quick test with different similarity thresholds
    for threshold in [0.9, 0.8, 0.7]:
        logger.info(f"\n=== Testing with similarity threshold {threshold} ===")
        
        matches_found = 0
        for i, track in enumerate(playlist_tracks):
            similar = find_similar_tracks(track, library_tracks, threshold)
            
            if similar:
                matches_found += 1
                logger.info(f"\n🎵 PLAYLIST: '{track.get('title')}' by {', '.join(get_artist_names(track.get('artists', [])))}")
                
                for sim in similar[:2]:  # Show top 2 matches
                    lib_track = sim['library_track']
                    logger.info(f"   📚 LIBRARY: '{lib_track.get('title')}' by {', '.join(get_artist_names(lib_track.get('artists', [])))} ({sim['title_similarity']:.1%} similar)")
                    logger.info(f"       Normalized: '{sim['normalized_playlist_title']}' vs '{sim['normalized_library_title']}'")
        
        logger.info(f"\nThreshold {threshold}: Found {matches_found} tracks with similar matches ({matches_found/len(playlist_tracks)*100:.1f}%)")

if __name__ == "__main__":
    main()