#!/usr/bin/env python3
"""
Test script to verify pagination issues with large playlists.
"""

import logging
from ytmusicapi import YTMusic

def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    return logging.getLogger(__name__)

def test_playlist_pagination():
    logger = setup_logging()
    
    # Test the specific playlist
    headers_path = "/Users/guerrero/Documents/musiccode/headers_auth.json"
    ytmusic = YTMusic(headers_path)
    
    playlist_id = "PL1LO5jourf4MqCSX94juP7bWk2eYTMCQ2"
    
    logger.info("=== TESTING PLAYLIST PAGINATION ===")
    
    # Test different limits to see pagination behavior
    test_limits = [1, 10, 50, 100, 200, 500, 1000, None]
    
    for limit in test_limits:
        try:
            logger.info(f"\n--- Testing with limit={limit} ---")
            result = ytmusic.get_playlist(playlist_id, limit=limit)
            
            track_count = len(result.get('tracks', []))
            reported_count = result.get('trackCount', 'Unknown')
            duration = result.get('duration', 'Unknown')
            title = result.get('title', 'Unknown')
            
            logger.info(f"Title: {title}")
            logger.info(f"Reported count: {reported_count}")
            logger.info(f"Actual tracks returned: {track_count}")
            logger.info(f"Duration: {duration}")
            
            # Check if we got a different number than the limit
            if limit is not None and track_count != min(limit, track_count):
                logger.warning(f"Expected up to {limit} tracks, got {track_count}")
            
        except Exception as e:
            logger.error(f"Failed with limit={limit}: {e}")
    
    logger.info("\n=== TESTING LIKED SONGS ===")
    
    # Test liked songs pagination
    for limit in [None, 1000, 500, 100]:
        try:
            logger.info(f"\n--- Testing liked songs with limit={limit} ---")
            result = ytmusic.get_liked_songs(limit=limit)
            
            track_count = len(result.get('tracks', []))
            logger.info(f"Liked songs returned: {track_count}")
            
        except Exception as e:
            logger.error(f"Failed liked songs with limit={limit}: {e}")

if __name__ == "__main__":
    test_playlist_pagination()