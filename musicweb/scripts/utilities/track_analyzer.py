#!/usr/bin/env python3
"""
Analyze missing tracks from playlist creation to understand why tracks couldn't be added.
"""

import json
import pandas as pd
from collections import Counter
from pathlib import Path
from musicweb import Library, Track, PlaylistManager

def analyze_missing_tracks_patterns(failed_tracks):
    """Analyze patterns in failed tracks to understand common issues."""
    if not failed_tracks:
        print("No failed tracks to analyze.")
        return
    
    print(f"\n📊 ANALYSIS OF {len(failed_tracks)} FAILED TRACKS")
    print("=" * 60)
    
    # Count reasons for failure
    reasons = [track.get('reason', 'Unknown') for track in failed_tracks]
    reason_counts = Counter(reasons)
    
    print("\n🔍 FAILURE REASONS:")
    for reason, count in reason_counts.most_common():
        percentage = (count / len(failed_tracks)) * 100
        print(f"  • {reason}: {count} tracks ({percentage:.1f}%)")
    
    # Analyze track characteristics
    artists = []
    titles = []
    durations = []
    has_album = 0
    has_isrc = 0
    
    print("\n🎵 FAILED TRACK CHARACTERISTICS:")
    for track_data in failed_tracks:
        track = track_data.get('track', {})
        
        artist = track.get('artist', '')
        title = track.get('title', '')
        duration = track.get('duration')
        album = track.get('album')
        isrc = track.get('isrc')
        
        if artist:
            artists.append(artist)
        if title:
            titles.append(title)
        if duration:
            durations.append(duration)
        if album:
            has_album += 1
        if isrc:
            has_isrc += 1
    
    print(f"  • Tracks with album info: {has_album}/{len(failed_tracks)} ({(has_album/len(failed_tracks)*100):.1f}%)")
    print(f"  • Tracks with ISRC: {has_isrc}/{len(failed_tracks)} ({(has_isrc/len(failed_tracks)*100):.1f}%)")
    
    if durations:
        avg_duration = sum(durations) / len(durations)
        print(f"  • Average duration: {avg_duration:.0f} seconds ({avg_duration/60:.1f} minutes)")
    
    # Show most common artists that failed
    if artists:
        artist_counts = Counter(artists)
        print(f"\n🎤 ARTISTS WITH MOST FAILED TRACKS:")
        for artist, count in artist_counts.most_common(10):
            print(f"  • {artist}: {count} tracks")
    
    # Show sample failed tracks
    print(f"\n📋 SAMPLE FAILED TRACKS:")
    for i, track_data in enumerate(failed_tracks[:10]):
        track = track_data.get('track', {})
        reason = track_data.get('reason', 'Unknown')
        title = track.get('title', 'Unknown Title')
        artist = track.get('artist', 'Unknown Artist')
        album = track.get('album', 'No Album')
        
        print(f"  {i+1:2d}. \"{title}\" by {artist}")
        print(f"      Album: {album}")
        print(f"      Reason: {reason}")
        print()
    
    if len(failed_tracks) > 10:
        print(f"  ... and {len(failed_tracks) - 10} more tracks")

def simulate_comparison_and_playlist_creation():
    """Simulate the comparison and playlist creation to show what data would be available."""
    print("🔄 SIMULATING COMPARISON PROCESS...")
    print("=" * 60)
    
    # Check if spot.json exists
    spot_file = Path("spot.json")
    if not spot_file.exists():
        print("❌ spot.json file not found in current directory")
        return
    
    # Load Spotify library
    print("📱 Loading Spotify library...")
    from musicweb.platforms import create_parser, detect_platform
    
    platform = detect_platform(str(spot_file))
    print(f"Detected platform: {platform}")
    
    parser = create_parser(platform)
    spotify_lib = parser.parse_file(str(spot_file))
    
    print(f"✅ Loaded {spotify_lib.music_count:,} music tracks from Spotify")
    
    # Check for music library songs.csv (if it exists)
    music_csv = Path("music library songs.csv")
    if music_csv.exists():
        print("📚 Loading comparison library...")
        try:
            other_platform = detect_platform(str(music_csv))
            other_parser = create_parser(other_platform)
            other_lib = other_parser.parse_file(str(music_csv))
            print(f"✅ Loaded {other_lib.music_count:,} music tracks from {other_platform}")
            
            # Simulate comparison
            print("\n🔍 SIMULATING LIBRARY COMPARISON...")
            from musiclib.comparison import LibraryComparator
            
            comparator = LibraryComparator(strict_mode=True)
            result = comparator.compare_libraries(spotify_lib, other_lib)
            
            stats = result.get_stats()
            print(f"📊 Comparison Results:")
            print(f"  • Total matches: {stats['total_matches']:,}")
            print(f"  • Missing tracks: {stats['missing_tracks']:,}")
            print(f"  • Match rate: {stats['match_rate']:.1f}%")
            
            if result.missing_tracks:
                print(f"\n🎵 SAMPLE MISSING TRACKS (would be sent to playlist creation):")
                for i, track in enumerate(result.missing_tracks[:5]):
                    print(f"  {i+1}. \"{track.title}\" by {track.artist}")
                    if track.album:
                        print(f"     Album: {track.album}")
                
                # Simulate what might fail
                print(f"\n💡 POTENTIAL REASONS FOR FAILED PLAYLIST ADDITIONS:")
                print(f"  • Regional availability issues")
                print(f"  • Artist/title variations between platforms")
                print(f"  • Tracks not available on YouTube Music")
                print(f"  • Search algorithm limitations")
                
        except Exception as e:
            print(f"❌ Error loading comparison library: {e}")
    else:
        print("📝 No comparison library found (music library songs.csv)")
        print("   To analyze missing tracks, you need two libraries to compare")

def main():
    print("🎵 MISSING TRACKS ANALYZER")
    print("=" * 60)
    print("This tool helps analyze why tracks couldn't be added to YouTube Music playlists")
    
    # Check if we have access to any failed tracks data
    # In a real scenario, this would come from the playlist creation result
    
    # For now, let's simulate the process to show what analysis would look like
    simulate_comparison_and_playlist_creation()
    
    print("\n" + "=" * 60)
    print("💡 TO GET ACTUAL FAILED TRACKS DATA:")
    print("1. After playlist creation in MusicWeb, download the 'Missing Tracks CSV'")
    print("2. Or check the browser console for detailed error logs")
    print("3. The app stores failed tracks with specific reasons for each failure")

if __name__ == "__main__":
    main()