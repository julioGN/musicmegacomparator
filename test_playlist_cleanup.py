#!/usr/bin/env python3
"""
Test script for the playlist cleanup functionality.

This script allows you to test the playlist cleanup system with the provided
YouTube Music playlist URL.
"""

import argparse
import logging
import sys
from pathlib import Path

# Add the project root to the path so we can import musiclib
sys.path.insert(0, str(Path(__file__).parent))

from musiclib.playlist_cleaner import PlaylistCleaner


def setup_logging(verbose: bool = False):
    """Setup logging configuration."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )


def main():
    """Main function to test playlist cleanup."""
    parser = argparse.ArgumentParser(description='Test YouTube Music Playlist Cleanup')
    parser.add_argument('--headers', required=True, help='Path to headers_auth.json file')
    parser.add_argument('--playlist', required=True, help='Playlist URL or ID to clean')
    parser.add_argument('--remove-liked', action='store_true', help='Remove liked songs')
    parser.add_argument('--dedupe-library', action='store_true', help='Remove songs already in library')
    parser.add_argument('--dry-run', action='store_true', help='Preview only, don\'t modify playlist')
    parser.add_argument('--verbose', '-v', action='store_true', help='Enable verbose logging')
    
    args = parser.parse_args()
    
    setup_logging(args.verbose)
    logger = logging.getLogger(__name__)
    
    # Validate headers file exists
    headers_path = Path(args.headers)
    if not headers_path.exists():
        logger.error(f"Headers file not found: {headers_path}")
        sys.exit(1)
    
    # Validate at least one cleanup option is selected
    if not (args.remove_liked or args.dedupe_library):
        logger.error("Please specify at least one cleanup option: --remove-liked or --dedupe-library")
        sys.exit(1)
    
    try:
        logger.info("Initializing playlist cleaner...")
        cleaner = PlaylistCleaner(headers_path=str(headers_path))
        
        logger.info(f"Playlist URL: {args.playlist}")
        logger.info(f"Remove liked songs: {args.remove_liked}")
        logger.info(f"Deduplicate against library: {args.dedupe_library}")
        logger.info(f"Dry run mode: {args.dry_run}")
        
        if args.dry_run:
            logger.info("=== DRY RUN MODE - PREVIEW ONLY ===")
            
            # Extract playlist ID
            playlist_id = cleaner.extract_playlist_id(args.playlist)
            if not playlist_id:
                logger.error(f"Could not extract playlist ID from: {args.playlist}")
                sys.exit(1)
            
            logger.info(f"Extracted playlist ID: {playlist_id}")
            
            # Get playlist tracks
            logger.info("Fetching playlist tracks...")
            tracks = cleaner.get_playlist_tracks_robust(playlist_id)
            logger.info(f"Found {len(tracks)} tracks in playlist")
            
            if not tracks:
                logger.error("No tracks found in playlist")
                sys.exit(1)
            
            # Get comparison data
            liked_songs = set()
            library_video_ids = set()
            
            if args.remove_liked:
                logger.info("Fetching liked songs...")
                liked_songs = cleaner.get_liked_songs_cached()
                logger.info(f"Found {len(liked_songs)} liked songs")
            
            if args.dedupe_library:
                logger.info("Fetching library songs...")
                library_songs = cleaner.get_library_songs_cached()
                library_video_ids = {song.get('videoId') for song in library_songs if song.get('videoId')}
                logger.info(f"Found {len(library_video_ids)} songs in library")
            
            # Analyze what would be removed
            tracks_to_remove_liked = []
            tracks_to_remove_library = []
            
            for track in tracks:
                if args.remove_liked and track.video_id in liked_songs:
                    tracks_to_remove_liked.append(track)
                elif args.dedupe_library and track.video_id in library_video_ids:
                    tracks_to_remove_library.append(track)
            
            # Show results
            print("\n" + "="*50)
            print("CLEANUP PREVIEW RESULTS")
            print("="*50)
            print(f"Original tracks: {len(tracks)}")
            print(f"Liked songs to remove: {len(tracks_to_remove_liked)}")
            print(f"Library duplicates to remove: {len(tracks_to_remove_library)}")
            print(f"Final track count: {len(tracks) - len(tracks_to_remove_liked) - len(tracks_to_remove_library)}")
            
            if tracks_to_remove_liked:
                print(f"\nLiked songs to remove ({len(tracks_to_remove_liked)}):")
                for i, track in enumerate(tracks_to_remove_liked[:10], 1):
                    print(f"  {i}. {track.title} - {', '.join(track.artists)}")
                if len(tracks_to_remove_liked) > 10:
                    print(f"  ... and {len(tracks_to_remove_liked) - 10} more")
            
            if tracks_to_remove_library:
                print(f"\nLibrary duplicates to remove ({len(tracks_to_remove_library)}):")
                for i, track in enumerate(tracks_to_remove_library[:10], 1):
                    print(f"  {i}. {track.title} - {', '.join(track.artists)}")
                if len(tracks_to_remove_library) > 10:
                    print(f"  ... and {len(tracks_to_remove_library) - 10} more")
            
            print("\nTo apply these changes, run again without --dry-run")
        
        else:
            logger.info("=== EXECUTING CLEANUP ===")
            
            result = cleaner.clean_playlist(
                args.playlist,
                remove_liked=args.remove_liked,
                deduplicate_against_library=args.dedupe_library
            )
            
            # Show results
            print("\n" + "="*50)
            print("CLEANUP RESULTS")
            print("="*50)
            print(f"Playlist: {result.playlist_name}")
            print(f"Original tracks: {result.original_count}")
            print(f"Removed liked songs: {result.removed_liked}")
            print(f"Removed library duplicates: {result.removed_duplicates}")
            print(f"Final track count: {result.final_count}")
            print(f"Processing time: {result.processing_time:.2f} seconds")
            
            if result.errors:
                print(f"\nErrors encountered:")
                for error in result.errors:
                    print(f"  - {error}")
            
            print(f"\nCleaned playlist: https://music.youtube.com/playlist?list={result.playlist_id}")
    
    except KeyboardInterrupt:
        logger.info("Operation cancelled by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Cleanup failed: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()