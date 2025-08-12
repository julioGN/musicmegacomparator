#!/usr/bin/env python3
"""
Remove tracks from "Missing Tracks" playlist that already exist in your library.
"""

import json
import logging
import time
from pathlib import Path
from typing import List, Set, Dict, Any
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


def normalize_text(text: str) -> str:
    """Normalize text for comparison."""
    if not text:
        return ""
    
    # Remove version indicators
    text = re.sub(r'\s*\([^)]*(?:remaster|mix|version|edit|live|acoustic|demo|feat|featuring|explicit|clean)[^)]*\)', '', text, flags=re.IGNORECASE)
    text = re.sub(r'\s*\[[^\]]*(?:remaster|mix|version|edit|live|acoustic|demo|feat|featuring|explicit|clean)[^\]]*\]', '', text, flags=re.IGNORECASE)
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


def find_library_matches(playlist_tracks: List[Dict], library_tracks: List[Dict], logger, similarity_threshold: float = 0.85):
    """Find playlist tracks that match tracks in the library."""
    
    logger.info(f"Comparing {len(playlist_tracks)} playlist tracks against {len(library_tracks)} library tracks...")
    
    # Create lookup structures for library tracks
    library_video_ids = {track.get('videoId') for track in library_tracks if track.get('videoId')}
    
    # Create normalized lookup for similarity matching
    library_normalized = {}
    for track in library_tracks:
        title = normalize_text(track.get('title', ''))
        artists = get_artist_names(track.get('artists', []))
        
        if title and artists:
            for artist in artists:
                artist_norm = normalize_text(artist)
                key = f"{title}|{artist_norm}"
                if key not in library_normalized:
                    library_normalized[key] = []
                library_normalized[key].append(track)
    
    logger.info(f"Created lookup index for {len(library_normalized)} unique title-artist combinations")
    
    matches = []
    processed = 0
    
    for playlist_track in playlist_tracks:
        processed += 1
        if processed % 100 == 0:
            logger.info(f"Processed {processed}/{len(playlist_tracks)} tracks...")
        
        video_id = playlist_track.get('videoId')
        
        # Strategy 1: Exact video ID match
        if video_id and video_id in library_video_ids:
            matches.append({
                'playlist_track': playlist_track,
                'match_type': 'exact_video_id',
                'confidence': 1.0,
                'library_matches': [{'videoId': video_id, 'match_reason': 'Exact video ID match'}]
            })
            continue
        
        # Strategy 2: Similarity matching
        playlist_title = normalize_text(playlist_track.get('title', ''))
        playlist_artists = get_artist_names(playlist_track.get('artists', []))
        
        if not playlist_title or not playlist_artists:
            continue
        
        best_matches = []
        
        for playlist_artist in playlist_artists:
            playlist_artist_norm = normalize_text(playlist_artist)
            lookup_key = f"{playlist_title}|{playlist_artist_norm}"
            
            # Direct lookup first
            if lookup_key in library_normalized:
                for lib_track in library_normalized[lookup_key]:
                    best_matches.append({
                        'library_track': lib_track,
                        'similarity': 1.0,
                        'match_reason': 'Exact normalized match'
                    })
            
            # Fuzzy matching for close matches
            else:
                for lib_key, lib_tracks in library_normalized.items():
                    similarity = similarity_score(lookup_key, lib_key)
                    if similarity >= similarity_threshold:
                        for lib_track in lib_tracks:
                            best_matches.append({
                                'library_track': lib_track,
                                'similarity': similarity,
                                'match_reason': f'Similarity match ({similarity:.1%})'
                            })
        
        if best_matches:
            # Sort by similarity and take best matches
            best_matches.sort(key=lambda x: x['similarity'], reverse=True)
            top_matches = best_matches[:3]  # Top 3 matches
            
            confidence = top_matches[0]['similarity'] * 0.9  # Slight confidence reduction for similarity matches
            
            matches.append({
                'playlist_track': playlist_track,
                'match_type': 'similarity',
                'confidence': confidence,
                'library_matches': top_matches
            })
    
    logger.info(f"Found {len(matches)} playlist tracks that exist in your library")
    return matches


def save_matches_for_review(matches: List[Dict], output_file: str, logger):
    """Save matches for review."""
    
    high_confidence = [m for m in matches if m['confidence'] >= 0.95]
    needs_review = [m for m in matches if m['confidence'] < 0.95]
    
    review_data = {
        'summary': {
            'total_matches': len(matches),
            'high_confidence': len(high_confidence),
            'needs_review': len(needs_review),
            'generated_at': time.strftime('%Y-%m-%d %H:%M:%S')
        },
        'high_confidence_removals': [
            {
                'playlist_track': {
                    'videoId': match['playlist_track'].get('videoId'),
                    'setVideoId': match['playlist_track'].get('setVideoId'),
                    'title': match['playlist_track'].get('title'),
                    'artists': [a.get('name') for a in match['playlist_track'].get('artists', [])],
                    'duration': match['playlist_track'].get('duration')
                },
                'match_type': match['match_type'],
                'confidence': match['confidence'],
                'reason': 'Already in library - not missing'
            }
            for match in high_confidence
        ],
        'needs_review': [
            {
                'playlist_track': {
                    'videoId': match['playlist_track'].get('videoId'),
                    'setVideoId': match['playlist_track'].get('setVideoId'),
                    'title': match['playlist_track'].get('title'),
                    'artists': [a.get('name') for a in match['playlist_track'].get('artists', [])],
                    'duration': match['playlist_track'].get('duration')
                },
                'match_type': match['match_type'],
                'confidence': match['confidence'],
                'library_matches': [
                    {
                        'title': lib_match.get('library_track', {}).get('title'),
                        'artists': [a.get('name') for a in lib_match.get('library_track', {}).get('artists', [])],
                        'similarity': lib_match.get('similarity'),
                        'reason': lib_match.get('match_reason')
                    }
                    for lib_match in match['library_matches']
                ]
            }
            for match in needs_review
        ]
    }
    
    with open(output_file, 'w') as f:
        json.dump(review_data, f, indent=2)
    
    logger.info(f"Review data saved to {output_file}")
    logger.info(f"High confidence removals: {len(high_confidence)} tracks")
    logger.info(f"Needs manual review: {len(needs_review)} tracks")


def remove_library_duplicates(ytmusic: YTMusic, playlist_id: str, logger, auto_remove: bool = False, review_file: str = None):
    """Remove tracks from playlist that already exist in library."""
    
    logger.info("Finding tracks in playlist that already exist in your library...")
    
    # Fetch data
    logger.info("Fetching playlist tracks...")
    playlist_data = ytmusic.get_playlist(playlist_id, limit=None)
    playlist_tracks = playlist_data.get('tracks', [])
    playlist_title = playlist_data.get('title', 'Unknown Playlist')
    
    logger.info(f"Playlist: '{playlist_title}' with {len(playlist_tracks)} tracks")
    
    logger.info("Fetching library tracks...")
    library_tracks = ytmusic.get_library_songs(limit=None)
    logger.info(f"Library has {len(library_tracks)} tracks")
    
    # Find matches
    matches = find_library_matches(playlist_tracks, library_tracks, logger)
    
    if not matches:
        logger.info("🎉 No library duplicates found! All playlist tracks are truly missing from your library.")
        return
    
    # Save for review
    if review_file:
        save_matches_for_review(matches, review_file, logger)
    
    # Auto-remove high confidence matches
    if auto_remove:
        high_confidence = [m for m in matches if m['confidence'] >= 0.95]
        
        if high_confidence:
            logger.info(f"Auto-removing {len(high_confidence)} tracks that are already in your library...")
            
            tracks_to_remove = []
            for match in high_confidence:
                track = match['playlist_track']
                if track.get('videoId') and track.get('setVideoId'):
                    tracks_to_remove.append({
                        'videoId': track['videoId'],
                        'setVideoId': track['setVideoId']
                    })
                    title = track.get('title', 'Unknown')
                    artists = ', '.join([a.get('name', '') for a in track.get('artists', [])])
                    logger.info(f"REMOVING: {title} by {artists} (already in library)")
            
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
                
                logger.info(f"✅ Removed {len(tracks_to_remove)} tracks that were already in your library!")
                logger.info(f"Your 'Missing Tracks' playlist now only contains truly missing tracks.")
        else:
            logger.info("No high-confidence matches found for auto-removal")


def main():
    logger = setup_logging()
    
    # Configuration
    headers_path = "/Users/guerrero/Documents/musiccode/headers_auth.json"
    if not Path(headers_path).exists():
        logger.error(f"Headers file not found: {headers_path}")
        return
    
    playlist_url = "https://music.youtube.com/playlist?list=PL1LO5jourf4MqCSX94juP7bWk2eYTMCQ2&si=gSS-xtZtM7xT-j4l"
    playlist_id = playlist_url.split('list=')[1].split('&')[0]
    
    # Options
    review_file = "/Users/guerrero/Documents/musiccode/library_duplicates_review.json"
    auto_remove = True  # Set to True to automatically remove tracks that are already in library
    
    # Authenticate
    logger.info("Authenticating...")
    ytmusic = YTMusic(headers_path)
    
    # Run cleanup
    remove_library_duplicates(ytmusic, playlist_id, logger, auto_remove=auto_remove, review_file=review_file)


if __name__ == "__main__":
    main()