#!/usr/bin/env python3
"""
Basic library comparison example for MusicWeb.

This example demonstrates how to compare two music libraries
and analyze the results programmatically.
"""

from musicweb import create_parser, detect_platform, LibraryComparator


def main():
    """Run basic library comparison example."""
    print("🎵 MusicWeb - Basic Library Comparison Example")
    print("=" * 50)
    
    # Example file paths (replace with your actual files)
    spotify_file = "data/sample-libraries/spotify_library.json"
    apple_file = "data/sample-libraries/apple_library.csv"
    
    try:
        # Load first library (Spotify)
        print(f"📱 Loading Spotify library from {spotify_file}")
        spotify_platform = detect_platform(spotify_file)
        spotify_parser = create_parser(spotify_platform)
        spotify_library = spotify_parser.parse_file(spotify_file)
        
        print(f"✅ Loaded {spotify_library.music_count:,} tracks from Spotify")
        
        # Load second library (Apple Music)
        print(f"🍎 Loading Apple Music library from {apple_file}")
        apple_platform = detect_platform(apple_file)
        apple_parser = create_parser(apple_platform)
        apple_library = apple_parser.parse_file(apple_file)
        
        print(f"✅ Loaded {apple_library.music_count:,} tracks from Apple Music")
        
        # Compare libraries
        print("\n🔍 Comparing libraries...")
        comparator = LibraryComparator(
            strict_mode=True,
            enable_duration=True,
            enable_album=False
        )
        
        result = comparator.compare_libraries(spotify_library, apple_library)
        stats = result.get_stats()
        
        # Display results
        print("\n📊 Comparison Results:")
        print(f"  • Total matches: {stats['total_matches']:,}")
        print(f"  • Match rate: {stats['match_rate']:.1f}%")
        print(f"  • Average confidence: {stats['avg_confidence']:.1f}%")
        print(f"  • Missing from Apple Music: {stats['missing_tracks']:,}")
        
        # Show sample matches
        if result.matches:
            print(f"\n🎵 Sample Matches (showing first 5):")
            for i, match in enumerate(result.matches[:5]):
                source = match.source_track
                target = match.target_track
                print(f"  {i+1}. \"{source.title}\" by {source.artist}")
                print(f"     ↔ \"{target.title}\" by {target.artist}")
                print(f"     Confidence: {match.confidence:.1f}%\n")
        
        # Show sample missing tracks
        if result.missing_tracks:
            print(f"🔍 Sample Missing Tracks (showing first 5):")
            for i, track in enumerate(result.missing_tracks[:5]):
                print(f"  {i+1}. \"{track.title}\" by {track.artist}")
                if track.album:
                    print(f"     Album: {track.album}")
                print()
        
        print("✅ Comparison completed successfully!")
        
    except FileNotFoundError as e:
        print(f"❌ File not found: {e}")
        print("💡 Make sure you have sample library files in the data/ directory")
        
    except Exception as e:
        print(f"❌ Error during comparison: {e}")


if __name__ == "__main__":
    main()