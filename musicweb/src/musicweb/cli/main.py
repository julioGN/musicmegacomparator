#!/usr/bin/env python3
"""
MusicTools - Unified CLI for Music Library Management

A comprehensive command-line interface for comparing and managing music libraries
across multiple streaming platforms (Apple Music, Spotify, YouTube Music).

Usage:
    python musictools.py --help
"""

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional, Any

from musicweb import (
    Library, Track, LibraryComparator, PlaylistManager,
    EnrichmentManager, YouTubeMusicDeduplicator, YTMusicCleaner, create_parser, detect_platform
)


class ProgressTracker:
    """Simple progress tracking for CLI operations."""
    
    def __init__(self, show_progress: bool = True):
        self.show_progress = show_progress
        self.last_progress = -1
    
    def __call__(self, current: int, total: int, message: str = ""):
        if not self.show_progress:
            return
        
        if total == 0:
            return
        
        progress_percent = int((current / total) * 100)
        
        # Only update if progress changed significantly
        if progress_percent != self.last_progress:
            print(f"\r[{progress_percent:3d}%] {message}", end="", flush=True)
            self.last_progress = progress_percent
        
        if current >= total:
            print()  # New line when complete


def load_library(file_path: str, platform: str = None) -> Library:
    """Load library from file with platform detection."""
    if not Path(file_path).exists():
        raise FileNotFoundError(f"Library file not found: {file_path}")
    
    # Auto-detect platform if not specified
    if not platform:
        platform = detect_platform(file_path)
        print(f"Auto-detected platform: {platform}")
    
    # Create appropriate parser
    parser = create_parser(platform)
    library = parser.parse_file(file_path)
    
    print(f"Loaded {library.name}: {library.music_count} music tracks, {library.non_music_count} non-music")
    return library


def compare_command(args):
    """Handle library comparison command."""
    print("🎵 Music Library Comparison")
    print("=" * 50)
    
    # Load libraries
    print("\nLoading libraries...")
    source_lib = load_library(args.source, args.source_platform)
    target_lib = load_library(args.target, args.target_platform)
    
    # Setup comparator
    comparator = LibraryComparator(
        strict_mode=args.strict,
        enable_duration=not args.no_duration,
        enable_album=args.use_album,
        progress_callback=ProgressTracker()
    )
    
    print(f"\nComparing '{source_lib.name}' vs '{target_lib.name}'...")
    start_time = time.time()
    
    # Perform comparison
    result = comparator.compare_libraries(source_lib, target_lib)
    
    elapsed = time.time() - start_time
    print(f"Comparison completed in {elapsed:.1f}s")
    
    # Display results
    stats = result.get_stats()
    print("\n📊 Comparison Results:")
    print(f"  Source tracks:     {stats['music_source_tracks']:,}")
    print(f"  Target tracks:     {stats['music_target_tracks']:,}")
    print(f"  Total matches:     {stats['total_matches']:,}")
    print(f"  - Exact matches:   {stats['exact_matches']:,}")
    print(f"  - Fuzzy matches:   {stats['fuzzy_matches']:,}")
    print(f"  - ISRC matches:    {stats['isrc_matches']:,}")
    print(f"  Missing tracks:    {stats['missing_tracks']:,}")
    print(f"  Match rate:        {stats['match_rate']:.1f}%")
    print(f"  Avg confidence:    {stats['avg_confidence']:.1f}%")
    
    # Save results
    if args.output_dir:
        print(f"\n💾 Saving results to {args.output_dir}...")
        files = result.save_results(args.output_dir)
        
        for file_type, file_path in files.items():
            print(f"  {file_type}: {file_path}")
    
    return result


def create_playlist_command(args):
    """Handle playlist creation command."""
    print("🎵 YouTube Music Playlist Creation")
    print("=" * 50)
    
    # Check for headers file
    if not args.headers or not Path(args.headers).exists():
        print("❌ Error: YouTube Music headers file required")
        print("   Run 'ytmusicapi setup' to generate headers_auth.json")
        return None
    
    # Load tracks from CSV
    print(f"\n📂 Loading tracks from {args.tracks}...")
    
    # Determine how to load tracks
    if args.tracks.endswith('.csv'):
        # Load from CSV (missing tracks file)
        import pandas as pd
        df = pd.read_csv(args.tracks)
        
        tracks = []
        for _, row in df.iterrows():
            track = Track(
                title=str(row.get('title', '')),
                artist=str(row.get('artist', '')),
                album=str(row.get('album', '')) or None,
                duration=row.get('duration') if pd.notna(row.get('duration')) else None
            )
            tracks.append(track)
    else:
        # Load as library file
        library = load_library(args.tracks)
        tracks = library.music_tracks
    
    print(f"Loaded {len(tracks)} tracks for playlist creation")
    
    # Setup playlist manager
    playlist_manager = PlaylistManager(args.headers)
    
    if not playlist_manager.is_available():
        print("❌ Error: YouTube Music API not available")
        return None
    
    # Validate tracks if requested
    if args.validate:
        from musiclib.playlist import PlaylistAnalyzer
        analyzer = PlaylistAnalyzer(playlist_manager)
        
        print("\n🔍 Analyzing playlist potential...")
        analysis = analyzer.analyze_playlist_potential(tracks)
        
        if analysis['analysis_available']:
            print(f"  Sample analysis ({analysis['sample_size']} tracks):")
            print(f"  Estimated success rate: {analysis['estimated_success_rate']:.1%}")
            print(f"  Average confidence:     {analysis['avg_confidence']:.1%}")
            print(f"  Recommendation: {analysis['recommendation']}")
            
            if not args.force and analysis['estimated_success_rate'] < 0.5:
                response = input("\n⚠️  Low success rate detected. Continue anyway? (y/N): ")
                if response.lower() != 'y':
                    print("Playlist creation cancelled.")
                    return None
    
    # Create playlist
    playlist_name = args.name or f"Music Library Import {time.strftime('%Y-%m-%d')}"
    print(f"\n🎵 Creating playlist: '{playlist_name}'")
    
    result = playlist_manager.create_playlist(
        playlist_name=playlist_name,
        tracks=tracks,
        search_fallback=args.search_fallback,
        progress_callback=ProgressTracker()
    )
    
    # Display results
    if result['success']:
        print(f"\n✅ Playlist created successfully!")
        print(f"  Playlist ID:    {result['playlist_id']}")
        print(f"  Tracks added:   {result['total_added']}/{result['total_requested']}")
        print(f"  Success rate:   {result['total_added']/result['total_requested']:.1%}")
        
        if result['failed_tracks']:
            print(f"  Failed tracks:  {len(result['failed_tracks'])}")
            
            if args.save_failed:
                failed_file = Path(args.output_dir or '.') / f"failed_tracks_{int(time.time())}.json"
                with open(failed_file, 'w') as f:
                    json.dump(result['failed_tracks'], f, indent=2)
                print(f"  Failed tracks saved to: {failed_file}")
    else:
        print(f"\n❌ Playlist creation failed: {result['error']}")
    
    return result


def analyze_command(args):
    """Handle multi-library analysis command."""
    print("🎵 Multi-Library Analysis")
    print("=" * 50)
    
    libraries = []
    
    # Load all libraries
    print("\nLoading libraries...")
    for lib_file in args.libraries:
        library = load_library(lib_file)
        libraries.append(library)
    
    # Setup comparator
    comparator = LibraryComparator(
        strict_mode=args.strict,
        enable_duration=not args.no_duration,
        enable_album=args.use_album,
        progress_callback=ProgressTracker()
    )
    
    print(f"\nAnalyzing {len(libraries)} libraries...")
    start_time = time.time()
    
    # Perform analysis
    analysis = comparator.analyze_libraries(libraries)
    
    elapsed = time.time() - start_time
    print(f"Analysis completed in {elapsed:.1f}s")
    
    # Display results
    print("\n📊 Library Statistics:")
    for lib_stats in analysis['libraries']:
        print(f"  {lib_stats['name']}: {lib_stats['music_tracks']:,} tracks, {lib_stats['unique_artists']:,} artists")
    
    print(f"\n🔄 Cross-Platform Analysis:")
    print(f"  Universal tracks: {len(analysis['universal_tracks']):,}")
    print(f"  Total unique artists: {analysis['artist_analysis']['total_unique_artists']:,}")
    print(f"  Universal artists: {len(analysis['artist_analysis']['universal_artists']):,}")
    
    # Pairwise comparisons
    print(f"\n🔍 Pairwise Comparisons:")
    for comparison in analysis['pairwise_comparisons']:
        stats = comparison['stats']
        print(f"  {comparison['source']} vs {comparison['target']}: {stats['match_rate']:.1f}% match rate")
    
    # Save analysis
    if args.output_dir:
        output_path = Path(args.output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        analysis_file = output_path / f"multi_library_analysis_{int(time.time())}.json"
        with open(analysis_file, 'w') as f:
            json.dump(analysis, f, indent=2, default=str)
        
        print(f"\n💾 Analysis saved to: {analysis_file}")
    
    return analysis


def enrich_command(args):
    """Handle metadata enrichment command."""
    print("🎵 Metadata Enrichment")
    print("=" * 50)
    
    # Load library
    print("\nLoading library...")
    library = load_library(args.library)
    
    # Setup enrichment
    enricher = EnrichmentManager()
    
    print(f"\nEnriching {library.music_count} tracks...")
    start_time = time.time()
    
    # Perform enrichment
    enriched_results = enricher.bulk_enrich(
        library.music_tracks[:args.limit] if args.limit else library.music_tracks,
        progress_callback=ProgressTracker()
    )
    
    elapsed = time.time() - start_time
    print(f"Enrichment completed in {elapsed:.1f}s")
    
    # Count successful enrichments
    successful = sum(1 for _, data in enriched_results if data.get('musicbrainz'))
    print(f"\n📊 Enrichment Results:")
    print(f"  Tracks processed: {len(enriched_results):,}")
    print(f"  Successfully enriched: {successful:,} ({successful/len(enriched_results):.1%})")
    
    # Save enriched data
    if args.output_dir:
        output_path = Path(args.output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        enriched_file = output_path / f"enriched_library_{int(time.time())}.json"
        
        # Convert to JSON-serializable format
        enrichment_data = []
        for enhanced_track, enrichment_info in enriched_results:
            enrichment_data.append({
                'original': enrichment_info['original_track'],
                'enhanced': enhanced_track.to_dict(),
                'enrichment': enrichment_info
            })
        
        with open(enriched_file, 'w') as f:
            json.dump(enrichment_data, f, indent=2, default=str)
        
        print(f"💾 Enriched data saved to: {enriched_file}")
    
    return enriched_results


def dedup_youtube_music_command(args):
    """Handle YouTube Music library deduplication."""
    print("🎵 YouTube Music Deduplication")
    print("=" * 50)

    if not args.headers or not Path(args.headers).exists():
        print("❌ Error: headers_auth.json is required (generate with 'ytmusicapi setup')")
        return None

    dedup = YouTubeMusicDeduplicator(args.headers)
    if not dedup.is_available():
        print("❌ ytmusicapi not installed. Install with: pip install ytmusicapi")
        return None

    print("\n🔐 Authenticating with YouTube Music...")
    if not dedup.authenticate():
        print("❌ Authentication failed. Ensure headers_auth.json is valid.")
        return None

    print("\n📥 Fetching library songs...")
    songs = dedup.get_library_songs(limit=args.limit)
    print(f"Loaded {len(songs)} library songs")

    print("\n🧭 Scanning for duplicates...")
    groups = dedup.find_duplicates(similarity_threshold=args.threshold)
    total_dup_tracks = sum(len(g['duplicates']) for g in groups)
    can_remove = sum(len(g['duplicates']) - 1 for g in groups)

    print("\n📊 Deduplication Summary:")
    print(f"  Duplicate groups: {len(groups)}")
    print(f"  Total dup tracks: {total_dup_tracks}")
    print(f"  Potential removals: {can_remove}")

    # Optionally export results
    if args.output_dir:
        out_dir = Path(args.output_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        json_path = out_dir / f"ytm_duplicates_{int(time.time())}.json"
        # Convert RankedDuplicate objects to dicts for JSON
        serializable = []
        for g in groups:
            serializable.append({
                'id': g['id'],
                'title': g['title'],
                'artist': g['artist'],
                'similarity_scores': g['similarity_scores'],
                'duplicates': [
                    (d.__dict__ if hasattr(d, '__dict__') else d) for d in g['duplicates']
                ]
            })
        with open(json_path, 'w') as f:
            json.dump({
                'total_library_songs': len(songs),
                'duplicate_groups': len(groups),
                'total_duplicates': total_dup_tracks,
                'can_remove': can_remove,
                'groups': serializable
            }, f, indent=2)
        print(f"💾 Exported duplicate report: {json_path}")

    # Optional playlist creation
    if args.create_playlist:
        print("\n🎵 Creating playlist of duplicates...")
        result = dedup.create_duplicates_playlist(
            name=args.playlist_name,
            prefer_explicit=bool(getattr(args, 'prefer_explicit', False)),
            losers_only=bool(getattr(args, 'losers_only', False)),
            winners_only=bool(getattr(args, 'winners_only', False))
        )
        if result.get('success'):
            print(f"✅ Playlist created: {result['playlist_url']}")
            print(f"   Tracks added: {result['total_added']}")
        else:
            print(f"❌ Failed to create playlist: {result.get('error')}")

    return {
        'groups': groups,
        'total_duplicates': total_dup_tracks,
        'can_remove': can_remove
    }


def clean_youtube_music_command(args):
    """Plan and optionally apply cleanup to YouTube Music library and playlists."""
    print("🧽 YouTube Music Cleanup")
    print("=" * 50)

    if not args.headers or not Path(args.headers).exists():
        print("❌ Error: headers_auth.json is required (generate with 'ytmusicapi setup')")
        return None

    dedup = YouTubeMusicDeduplicator(args.headers)
    if not dedup.is_available():
        print("❌ ytmusicapi not installed. Install with: pip install ytmusicapi")
        return None

    print("\n🔐 Authenticating with YouTube Music...")
    if not dedup.authenticate():
        print("❌ Authentication failed. Ensure headers_auth.json is valid.")
        return None

    print("\n📥 Fetching library songs...")
    songs = dedup.get_library_songs(limit=args.limit)
    print(f"Loaded {len(songs)} library songs")

    print("\n🧭 Scanning for duplicates...")
    groups = dedup.find_duplicates(similarity_threshold=args.threshold)
    print(f"Found {len(groups)} duplicate groups")

    # Filter by groups if specified
    include_ids = None
    if args.groups:
        try:
            include_ids = [int(x.strip()) for x in args.groups.split(',') if x.strip()]
        except ValueError:
            print("⚠️ Invalid --groups format; expected comma-separated integers")

    # Build plan
    print("\n📝 Building cleanup plan...")
    cleaner = YTMusicCleaner(dedup.ytmusic)
    plan = cleaner.plan_cleanup(
        groups,
        prefer_explicit=bool(getattr(args, 'prefer_explicit', False)),
        include_group_ids=include_ids,
        replace_in_playlists=bool(getattr(args, 'replace_in_playlists', False)),
        unlike_losers=bool(getattr(args, 'unlike_losers', False)),
    )

    # Summary
    print("\n📊 Plan Summary:")
    print(f"  Will Unlike:        {len(plan.unlike_video_ids)} tracks")
    print(f"  Playlists Affected: {len(plan.playlist_edits)}")
    print(f"  Total Adds:         {sum(len(e.add_video_ids) for e in plan.playlist_edits)}")
    print(f"  Total Removes:      {sum(len(e.remove_items) for e in plan.playlist_edits)}")

    # Save plan if requested
    if args.save_plan:
        out = {
            'winners_by_group': plan.winners_by_group,
            'losers_by_group': plan.losers_by_group,
            'unlike_video_ids': plan.unlike_video_ids,
            'playlist_edits': [
                {
                    'playlist_id': e.playlist_id,
                    'playlist_name': e.playlist_name,
                    'add_video_ids': e.add_video_ids,
                    'remove_items': e.remove_items,
                }
                for e in plan.playlist_edits
            ]
        }
        with open(args.save_plan, 'w') as f:
            json.dump(out, f, indent=2)
        print(f"💾 Saved plan to {args.save_plan}")

    # Apply if not dry-run
    if not args.dry_run:
        print("\n🧹 Applying cleanup...")
        summary = cleaner.apply_cleanup(
            plan,
            do_unlike=bool(getattr(args, 'unlike_losers', False)),
            do_playlists=bool(getattr(args, 'replace_in_playlists', False)),
            generate_undo=bool(getattr(args, 'save_undo', None)),
        )
        print(f"✅ Done — Unliked: {summary['unliked']}, Adds: {summary['playlist_adds']}, Removes: {summary['playlist_removes']}")
        if summary['errors']:
            print("⚠️ Some errors occurred:")
            for e in summary['errors']:
                print(f"   - {e}")
        if args.save_undo and summary.get('undo'):
            with open(args.save_undo, 'w') as f:
                json.dump(summary['undo'], f, indent=2)
            print(f"💾 Saved undo log to {args.save_undo}")
    else:
        print("\nℹ️ Dry run — no changes applied")
    
    return plan


def rollback_youtube_music_command(args):
    """Rollback a previous cleanup using an undo log."""
    print("↩️  Rollback YouTube Music Cleanup")
    print("=" * 50)

    if not args.headers or not Path(args.headers).exists():
        print("❌ Error: headers_auth.json is required (generate with 'ytmusicapi setup')")
        return None

    if not Path(args.undo_log).exists():
        print(f"❌ Undo log not found: {args.undo_log}")
        return None

    data = None
    with open(args.undo_log, 'r') as f:
        data = json.load(f)

    dedup = YouTubeMusicDeduplicator(args.headers)
    if not dedup.is_available():
        print("❌ ytmusicapi not installed. Install with: pip install ytmusicapi")
        return None
    if not dedup.authenticate():
        print("❌ Authentication failed. Ensure headers_auth.json is valid.")
        return None

    cleaner = YTMusicCleaner(dedup.ytmusic)
    print("\n⏪ Applying rollback...")
    res = cleaner.rollback(data)
    print(f"✅ Rolled back — Re-added: {res['playlist_readds']}, Removed Winners: {res['playlist_add_removals']}, Reliked: {res['ratings_liked']}")
    if res['errors']:
        print(f"⚠️ Errors: {res['errors']}")
    return res


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="MusicTools - Unified Music Library Management CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Compare Apple Music vs YouTube Music
  python musictools.py compare --source apple_music.csv --target youtube_music.json
  
  # Create YouTube Music playlist from missing tracks
  python musictools.py create-playlist --tracks missing_tracks.csv --name "Missing Songs" --headers headers_auth.json
  
  # Analyze multiple libraries
  python musictools.py analyze --libraries apple_music.csv spotify.csv youtube_music.json
  
  # Enrich metadata with MusicBrainz
  python musictools.py enrich --library apple_music.csv --output-dir enriched/
        """
    )
    
    # Global options
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    parser.add_argument('--output-dir', '-o', help='Output directory for results')
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')

    
    # Compare command
    compare_parser = subparsers.add_parser('compare', help='Compare two music libraries')
    compare_parser.add_argument('--source', required=True, help='Source library file')
    compare_parser.add_argument('--target', required=True, help='Target library file')
    compare_parser.add_argument('--source-platform', help='Source platform (auto-detect if not specified)')
    compare_parser.add_argument('--target-platform', help='Target platform (auto-detect if not specified)')
    compare_parser.add_argument('--strict', action='store_true', help='Use strict matching (higher precision)')
    compare_parser.add_argument('--no-duration', action='store_true', help='Disable duration matching')
    compare_parser.add_argument('--use-album', action='store_true', help='Enable album matching')
    
    # Create playlist command
    playlist_parser = subparsers.add_parser('create-playlist', help='Create YouTube Music playlist')
    playlist_parser.add_argument('--tracks', required=True, help='Tracks file (CSV or library file)')
    playlist_parser.add_argument('--name', help='Playlist name')
    playlist_parser.add_argument('--headers', required=True, help='YouTube Music headers file')
    playlist_parser.add_argument('--search-fallback', action='store_true', help='Use search fallback for missing tracks')
    playlist_parser.add_argument('--validate', action='store_true', help='Validate tracks before creating playlist')
    playlist_parser.add_argument('--force', action='store_true', help='Force creation even with low success rate')
    playlist_parser.add_argument('--save-failed', action='store_true', help='Save failed tracks to file')
    
    # Analyze command
    analyze_parser = subparsers.add_parser('analyze', help='Analyze multiple libraries')
    analyze_parser.add_argument('--libraries', nargs='+', required=True, help='Library files to analyze')
    analyze_parser.add_argument('--strict', action='store_true', help='Use strict matching')
    analyze_parser.add_argument('--no-duration', action='store_true', help='Disable duration matching')
    analyze_parser.add_argument('--use-album', action='store_true', help='Enable album matching')
    
    # Enrich command
    enrich_parser = subparsers.add_parser('enrich', help='Enrich metadata using MusicBrainz')
    enrich_parser.add_argument('--library', required=True, help='Library file to enrich')
    enrich_parser.add_argument('--limit', type=int, help='Limit number of tracks to enrich')

    # YouTube Music deduplication
    dedup_parser = subparsers.add_parser('dedup-ytm', help='Find duplicates in your YouTube Music library')
    dedup_parser.add_argument('--headers', required=True, help='Path to headers_auth.json (ytmusicapi)')
    dedup_parser.add_argument('--limit', type=int, help='Limit number of library songs to scan')
    dedup_parser.add_argument('--threshold', type=float, default=0.85, help='Similarity threshold (0-1, default 0.85)')
    dedup_parser.add_argument('--output-dir', '-o', help='Directory to export duplicate report JSON')
    dedup_parser.add_argument('--create-playlist', action='store_true', help='Create a playlist with detected duplicates')
    dedup_parser.add_argument('--playlist-name', help='Name for the duplicates playlist')
    dedup_parser.add_argument('--prefer-explicit', action='store_true', help='Prefer explicit version when picking the one to keep')
    dedup_parser.add_argument('--losers-only', action='store_true', help='Add only non-preferred items from each group to the playlist')
    dedup_parser.add_argument('--winners-only', action='store_true', help='Add only the preferred item from each group to the playlist')

    # Cleanup command
    clean_parser = subparsers.add_parser('clean-ytm', help='Plan and apply cleanup: unlike losers and replace in playlists')
    clean_parser.add_argument('--headers', required=True, help='Path to headers_auth.json (ytmusicapi)')
    clean_parser.add_argument('--limit', type=int, help='Limit number of library songs to scan')
    clean_parser.add_argument('--threshold', type=float, default=0.85, help='Similarity threshold (0-1, default 0.85)')
    clean_parser.add_argument('--prefer-explicit', action='store_true', help='Prefer explicit version as the one to keep')
    clean_parser.add_argument('--groups', help='Comma-separated group IDs to include (default: all)')
    clean_parser.add_argument('--unlike-losers', action='store_true', help='Unlike loser tracks from your library')
    clean_parser.add_argument('--replace-in-playlists', action='store_true', help='Replace losers with winners in your playlists')
    clean_parser.add_argument('--dry-run', action='store_true', help='Do not apply changes; just print summary')
    clean_parser.add_argument('--save-plan', help='Path to save cleanup plan JSON')
    clean_parser.add_argument('--save-undo', help='Path to save undo log JSON (for rollback)')

    rollback_parser = subparsers.add_parser('rollback-ytm', help='Rollback a previous cleanup using an undo log')
    rollback_parser.add_argument('--headers', required=True, help='Path to headers_auth.json (ytmusicapi)')
    rollback_parser.add_argument('--undo-log', required=True, help='Path to undo log JSON produced by clean-ytm')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    try:
        if args.command == 'compare':
            compare_command(args)
        elif args.command == 'create-playlist':
            create_playlist_command(args)
        elif args.command == 'analyze':
            analyze_command(args)
        elif args.command == 'enrich':
            enrich_command(args)
        elif args.command == 'dedup-ytm':
            dedup_youtube_music_command(args)
        elif args.command == 'rollback-ytm':
            rollback_youtube_music_command(args)
        elif args.command == 'ytm-headers-convert':
            convert_headers_command(args)
        elif args.command == 'clean-ytm':
            clean_youtube_music_command(args)
    
    except KeyboardInterrupt:
        print("\n\n⚠️ Operation cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


def convert_headers_command(args):
    """Convert raw HTTP headers text to headers_auth.json format for ytmusicapi."""
    raw_path = Path(args.input)
    if not raw_path.exists():
        print(f"❌ Raw headers file not found: {raw_path}")
        return None
    headers = {}
    for line in raw_path.read_text().splitlines():
        if not line.strip() or ':' not in line:
            continue
        key, val = line.split(':', 1)
        headers[key.strip()] = val.strip()

    # Ensure required defaults if missing
    headers.setdefault('X-Goog-AuthUser', '0')
    headers.setdefault('x-origin', 'https://music.youtube.com')

    out = Path(args.output)
    out.write_text(json.dumps(headers, indent=2))
    print(f"✅ Wrote {out} — you can now use it with ytmusicapi")
    return out


if __name__ == '__main__':
    main()
