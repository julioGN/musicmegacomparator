#!/usr/bin/env python3
"""
Quick library cleanup - exact matches only for immediate results.
"""

import logging
from pathlib import Path
from ytmusicapi import YTMusic
import time


def setup_logging():
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    return logging.getLogger(__name__)


def quick_library_cleanup():
    logger = setup_logging()
    
    headers_path = "/Users/guerrero/Documents/musiccode/headers_auth.json"
    ytmusic = YTMusic(headers_path)
    
    playlist_url = "https://music.youtube.com/playlist?list=PL1LO5jourf4MqCSX94juP7bWk2eYTMCQ2&si=gSS-xtZtM7xT-j4l"
    playlist_id = playlist_url.split('list=')[1].split('&')[0]
    
    logger.info("=== QUICK LIBRARY CLEANUP (EXACT MATCHES ONLY) ===")
    
    # Get playlist tracks
    logger.info("Fetching playlist tracks...")
    playlist_data = ytmusic.get_playlist(playlist_id, limit=None)
    playlist_tracks = playlist_data.get('tracks', [])
    logger.info(f"Playlist has {len(playlist_tracks)} tracks")
    
    # Get library video IDs
    logger.info("Fetching library tracks...")
    library_tracks = ytmusic.get_library_songs(limit=None)
    library_video_ids = {track.get('videoId') for track in library_tracks if track.get('videoId')}
    logger.info(f"Library has {len(library_video_ids)} tracks")
    
    # Find exact matches
    exact_matches = []
    for track in playlist_tracks:
        video_id = track.get('videoId')
        set_video_id = track.get('setVideoId')
        
        if video_id and video_id in library_video_ids and set_video_id:
            exact_matches.append({
                'videoId': video_id,
                'setVideoId': set_video_id
            })
            title = track.get('title', 'Unknown')
            artists = ', '.join([a.get('name', '') for a in track.get('artists', [])])
            logger.info(f"EXACT MATCH: {title} by {artists}")
    
    logger.info(f"\n📊 SUMMARY:")
    logger.info(f"Playlist tracks: {len(playlist_tracks)}")
    logger.info(f"Exact library matches: {len(exact_matches)}")
    logger.info(f"Match rate: {len(exact_matches)/len(playlist_tracks)*100:.1f}%")
    
    if exact_matches:
        logger.info(f"\n🗑️ REMOVING {len(exact_matches)} EXACT MATCHES...")
        
        # Remove in batches
        batch_size = 50
        for i in range(0, len(exact_matches), batch_size):
            batch = exact_matches[i:i + batch_size]
            try:
                ytmusic.remove_playlist_items(playlist_id, batch)
                logger.info(f"✅ Removed batch {i//batch_size + 1} ({len(batch)} tracks)")
                time.sleep(1)
            except Exception as e:
                logger.error(f"❌ Failed to remove batch {i//batch_size + 1}: {e}")
        
        logger.info(f"\n🎉 SUCCESS! Removed {len(exact_matches)} tracks that were already in your library.")
        logger.info(f"Your playlist now has {len(playlist_tracks) - len(exact_matches)} tracks remaining.")
    else:
        logger.info("\n✅ No exact matches found - all tracks are truly missing from your library!")
    
    logger.info(f"\n💡 NEXT STEPS:")
    logger.info(f"Run the full similarity analysis script to find similar tracks with different video IDs")


if __name__ == "__main__":
    quick_library_cleanup()