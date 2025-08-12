#!/usr/bin/env python3
"""
Advanced playlist cleaner with similarity detection and manual review.
"""

import json
import logging
import time
from pathlib import Path
from typing import List, Set, Dict, Any, Tuple
import sys
from difflib import SequenceMatcher
import re

try:
    from ytmusicapi import YTMusic
except ImportError:
    print("ytmusicapi not installed. Run: pip install ytmusicapi")
    sys.exit(1)


def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    return logging.getLogger(__name__)


def extract_playlist_id(url_or_id: str) -> str:
    """Extract playlist ID from URL."""
    if url_or_id.startswith('PL'):
        return url_or_id
    
    if 'list=' in url_or_id:
        return url_or_id.split('list=')[1].split('&')[0]
    
    raise ValueError(f"Could not extract playlist ID from: {url_or_id}")


def normalize_text(text: str) -> str:
    """Normalize text for comparison by removing extra characters and converting to lowercase."""
    if not text:
        return ""
    
    # Remove common parenthetical content that differs between versions
    text = re.sub(r'\s*\([^)]*(?:remaster|mix|version|edit|live|acoustic|demo|feat|featuring)[^)]*\)', '', text, flags=re.IGNORECASE)
    text = re.sub(r'\s*\[[^\]]*(?:remaster|mix|version|edit|live|acoustic|demo|feat|featuring)[^\]]*\]', '', text, flags=re.IGNORECASE)
    
    # Remove year indicators
    text = re.sub(r'\s*\(?\d{4}\)?', '', text)
    
    # Remove special characters and extra spaces
    text = re.sub(r'[^\w\s]', '', text)
    text = re.sub(r'\s+', ' ', text)
    
    return text.lower().strip()


def similarity_score(text1: str, text2: str) -> float:
    """Calculate similarity between two strings (0-1, where 1 is identical)."""
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
                    'reason': 'Similar title and artist'
                })
    
    return similar_tracks


class DuplicateCandidate:
    def __init__(self, playlist_track: Dict, similar_tracks: List[Dict], match_type: str):
        self.playlist_track = playlist_track
        self.similar_tracks = similar_tracks
        self.match_type = match_type  # 'exact', 'similar', 'liked'
        self.confidence = self._calculate_confidence()
        self.review_needed = self._needs_review()
    
    def _calculate_confidence(self) -> float:
        """Calculate confidence score for automatic removal (0-1)."""
        if self.match_type == 'exact':
            return 1.0
        elif self.match_type == 'liked':
            return 0.9
        elif self.match_type == 'similar':
            if not self.similar_tracks:
                return 0.0
            # Use highest similarity score
            max_similarity = max(track['title_similarity'] for track in self.similar_tracks)
            return max_similarity * 0.8  # Reduce confidence for similarity matches
        return 0.0
    
    def _needs_review(self) -> bool:
        """Determine if this candidate needs manual review."""
        # Always review if confidence is below threshold
        if self.confidence < 0.95:
            return True
        
        # Review if there are multiple similar tracks
        if len(self.similar_tracks) > 1:
            return True
        
        return False
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization."""
        return {
            'playlist_track': {
                'videoId': self.playlist_track.get('videoId'),
                'setVideoId': self.playlist_track.get('setVideoId'),
                'title': self.playlist_track.get('title'),
                'artists': [a.get('name') for a in self.playlist_track.get('artists', [])],
                'duration': self.playlist_track.get('duration')
            },
            'similar_tracks': [
                {
                    'title': track['library_track'].get('title'),
                    'artists': [a.get('name') for a in track['library_track'].get('artists', [])],
                    'similarity': track['title_similarity'],
                    'reason': track['reason']
                }
                for track in self.similar_tracks
            ],
            'match_type': self.match_type,
            'confidence': self.confidence,
            'review_needed': self.review_needed
        }


def find_all_duplicates(playlist_tracks: List[Dict], library_tracks: List[Dict], liked_video_ids: Set[str], logger) -> List[DuplicateCandidate]:
    """Find all potential duplicates with different matching strategies."""
    
    logger.info(f"Analyzing {len(playlist_tracks)} playlist tracks against {len(library_tracks)} library tracks...")
    
    # Create lookup sets for fast exact matching
    library_video_ids = {track.get('videoId') for track in library_tracks if track.get('videoId')}
    
    duplicates = []
    processed = 0
    
    for track in playlist_tracks:
        processed += 1
        if processed % 100 == 0:
            logger.info(f"Processed {processed}/{len(playlist_tracks)} tracks...")
        
        video_id = track.get('videoId')
        if not video_id:
            continue
        
        # Strategy 1: Exact library match
        if video_id in library_video_ids:
            duplicates.append(DuplicateCandidate(track, [], 'exact'))
            continue
        
        # Strategy 2: Exact liked songs match
        if video_id in liked_video_ids:
            duplicates.append(DuplicateCandidate(track, [], 'liked'))
            continue
        
        # Strategy 3: Similar track detection
        similar_tracks = find_similar_tracks(track, library_tracks)
        if similar_tracks:
            duplicates.append(DuplicateCandidate(track, similar_tracks, 'similar'))
    
    logger.info(f"Found {len(duplicates)} potential duplicates")
    return duplicates


def save_review_data(duplicates: List[DuplicateCandidate], output_file: str, logger):
    """Save duplicates that need review to JSON file."""
    
    review_needed = [dup for dup in duplicates if dup.review_needed]
    auto_remove = [dup for dup in duplicates if not dup.review_needed]
    
    review_data = {
        'summary': {
            'total_duplicates': len(duplicates),
            'auto_remove': len(auto_remove),
            'needs_review': len(review_needed),
            'generated_at': time.strftime('%Y-%m-%d %H:%M:%S')
        },
        'auto_remove': [dup.to_dict() for dup in auto_remove],
        'needs_review': [dup.to_dict() for dup in review_needed]
    }
    
    with open(output_file, 'w') as f:
        json.dump(review_data, f, indent=2)
    
    logger.info(f"Review data saved to {output_file}")
    logger.info(f"Auto-remove candidates: {len(auto_remove)}")
    logger.info(f"Manual review needed: {len(review_needed)}")


def clean_playlist_advanced(ytmusic: YTMusic, playlist_id: str, logger, auto_remove: bool = False, review_file: str = None):
    """Advanced playlist cleaning with similarity detection and manual review."""
    
    logger.info(f"Starting advanced playlist cleanup")
    
    # Fetch all data
    logger.info("Fetching playlist tracks...")
    playlist_data = ytmusic.get_playlist(playlist_id, limit=None)
    playlist_tracks = playlist_data.get('tracks', [])
    logger.info(f"Got {len(playlist_tracks)} playlist tracks")
    
    logger.info("Fetching library songs...")
    library_tracks = ytmusic.get_library_songs(limit=None)
    logger.info(f"Got {len(library_tracks)} library tracks")
    
    logger.info("Fetching liked songs...")
    liked_data = ytmusic.get_liked_songs(limit=None)
    liked_video_ids = {track.get('videoId') for track in liked_data.get('tracks', []) if track.get('videoId')}
    logger.info(f"Got {len(liked_video_ids)} liked songs")
    
    # Find duplicates
    duplicates = find_all_duplicates(playlist_tracks, library_tracks, liked_video_ids, logger)
    
    # Save review data
    if review_file:
        save_review_data(duplicates, review_file, logger)
    
    # Auto-remove high confidence duplicates if requested
    if auto_remove:
        auto_candidates = [dup for dup in duplicates if not dup.review_needed]
        
        if auto_candidates:
            logger.info(f"Auto-removing {len(auto_candidates)} high-confidence duplicates...")
            
            tracks_to_remove = []
            for candidate in auto_candidates:
                track = candidate.playlist_track
                if track.get('videoId') and track.get('setVideoId'):
                    tracks_to_remove.append({
                        'videoId': track['videoId'],
                        'setVideoId': track['setVideoId']
                    })
                    logger.info(f"REMOVING: {track.get('title')} by {', '.join([a.get('name', '') for a in track.get('artists', [])])}")
            
            # Remove in batches
            if tracks_to_remove:
                batch_size = 50
                for i in range(0, len(tracks_to_remove), batch_size):
                    batch = tracks_to_remove[i:i + batch_size]
                    try:
                        ytmusic.remove_playlist_items(playlist_id, batch)
                        logger.info(f"Removed batch {i//batch_size + 1} ({len(batch)} tracks)")
                        time.sleep(1)  # Rate limiting
                    except Exception as e:
                        logger.error(f"Failed to remove batch {i//batch_size + 1}: {e}")
                
                logger.info(f"Auto-removal complete! Removed {len(tracks_to_remove)} tracks")
        else:
            logger.info("No high-confidence duplicates found for auto-removal")


def main():
    logger = setup_logging()
    
    # Configuration
    headers_path = "/Users/guerrero/Documents/musiccode/headers_auth.json"
    if not Path(headers_path).exists():
        logger.error(f"Headers file not found: {headers_path}")
        return
    
    playlist_url = "https://music.youtube.com/playlist?list=PL1LO5jourf4MqCSX94juP7bWk2eYTMCQ2&si=gSS-xtZtM7xT-j4l"
    playlist_id = extract_playlist_id(playlist_url)
    
    # Options
    review_file = "/Users/guerrero/Documents/musiccode/duplicate_review.json"
    auto_remove = False  # Set to True to automatically remove high-confidence duplicates
    
    # Authenticate
    logger.info("Authenticating...")
    ytmusic = YTMusic(headers_path)
    
    # Run advanced cleanup
    clean_playlist_advanced(ytmusic, playlist_id, logger, auto_remove=auto_remove, review_file=review_file)
    
    logger.info(f"\nNext steps:")
    logger.info(f"1. Review the duplicates in: {review_file}")
    logger.info(f"2. Use the web app to manually review uncertain cases")
    logger.info(f"3. Re-run with auto_remove=True to automatically remove confirmed duplicates")


if __name__ == "__main__":
    main()