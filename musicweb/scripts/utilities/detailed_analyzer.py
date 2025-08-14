#!/usr/bin/env python3
"""
Detailed analysis of specific tracks that might fail in playlist creation.
"""

import pandas as pd
from musicweb.platforms import create_parser, detect_platform
from musiclib.comparison import LibraryComparator
from pathlib import Path

def analyze_problematic_tracks():
    """Analyze tracks that are likely to fail in YouTube Music playlist creation."""
    
    print("🔍 DETAILED MISSING TRACKS ANALYSIS")
    print("=" * 70)
    
    # Load libraries
    spot_file = Path("spot.json")
    music_csv = Path("music library songs.csv")
    
    if not spot_file.exists() or not music_csv.exists():
        print("❌ Required files not found")
        return
    
    # Load Spotify library
    spotify_parser = create_parser(detect_platform(str(spot_file)))
    spotify_lib = spotify_parser.parse_file(str(spot_file))
    
    # Load comparison library
    other_parser = create_parser(detect_platform(str(music_csv)))
    other_lib = other_parser.parse_file(str(music_csv))
    
    # Compare libraries
    comparator = LibraryComparator(strict_mode=True)
    result = comparator.compare_libraries(spotify_lib, other_lib)
    
    missing_tracks = result.missing_tracks
    print(f"📊 Found {len(missing_tracks)} missing tracks")
    
    # Analyze characteristics that might cause failures
    problematic_tracks = []
    
    for track in missing_tracks:
        issues = []
        risk_score = 0
        
        # Check for version indicators
        title_lower = track.title.lower()
        if any(word in title_lower for word in ['remaster', 'remastered', '- 20', 'deluxe', 'extended']):
            issues.append("Version/Remaster")
            risk_score += 3
        
        # Check for live versions
        if any(word in title_lower for word in ['live', 'en vivo', 'concert', 'acoustic']):
            issues.append("Live/Special Version")
            risk_score += 4
        
        # Check for featuring artists
        if any(word in title_lower for word in ['feat.', 'ft.', 'featuring', 'with ']):
            issues.append("Featuring Artists")
            risk_score += 2
        
        # Check for special characters
        if any(char in track.title for char in ['/', '(', ')', '-', '&', '#']):
            issues.append("Special Characters")
            risk_score += 1
        
        # Check for non-English characters
        if any(ord(char) > 127 for char in track.title):
            issues.append("Non-English Characters")
            risk_score += 2
        
        # Check for very long titles
        if len(track.title) > 60:
            issues.append("Long Title")
            risk_score += 1
        
        # Check for missing album info
        if not track.album:
            issues.append("No Album Info")
            risk_score += 1
        
        # Check for short duration (might be intro/outro)
        if track.duration and track.duration < 60:
            issues.append("Very Short (<1min)")
            risk_score += 3
        
        # Check for very long duration (might be mix/compilation)
        if track.duration and track.duration > 600:  # > 10 minutes
            issues.append("Very Long (>10min)")
            risk_score += 2
        
        if issues:
            problematic_tracks.append({
                'track': track,
                'issues': issues,
                'risk_score': risk_score
            })
    
    # Sort by risk score
    problematic_tracks.sort(key=lambda x: x['risk_score'], reverse=True)
    
    print(f"\n🚨 HIGH-RISK TRACKS (likely to fail): {len([t for t in problematic_tracks if t['risk_score'] >= 5])}")
    print(f"⚠️  MEDIUM-RISK TRACKS: {len([t for t in problematic_tracks if 2 <= t['risk_score'] < 5])}")
    print(f"✅ LOW-RISK TRACKS: {len([t for t in problematic_tracks if t['risk_score'] < 2])}")
    
    print(f"\n📋 TOP 20 MOST LIKELY TO FAIL:")
    print("-" * 70)
    
    for i, item in enumerate(problematic_tracks[:20]):
        track = item['track']
        issues = item['issues']
        risk = item['risk_score']
        
        print(f"{i+1:2d}. \"{track.title}\" by {track.artist}")
        print(f"    Album: {track.album or 'N/A'}")
        print(f"    Duration: {track.duration or 'N/A'}s")
        print(f"    Risk Score: {risk} | Issues: {', '.join(issues)}")
        print()
    
    # Generate patterns analysis
    print(f"\n📈 FAILURE PATTERN ANALYSIS:")
    print("-" * 70)
    
    all_issues = []
    for item in problematic_tracks:
        all_issues.extend(item['issues'])
    
    from collections import Counter
    issue_counts = Counter(all_issues)
    
    for issue, count in issue_counts.most_common():
        percentage = (count / len(missing_tracks)) * 100
        print(f"  • {issue}: {count} tracks ({percentage:.1f}% of missing tracks)")
    
    # Export detailed CSV for manual review
    export_data = []
    for item in problematic_tracks:
        track = item['track']
        export_data.append({
            'Title': track.title,
            'Artist': track.artist,
            'Album': track.album or '',
            'Duration': track.duration or '',
            'Risk_Score': item['risk_score'],
            'Issues': ', '.join(item['issues']),
            'Platform': track.platform,
            'ISRC': track.isrc or ''
        })
    
    df = pd.DataFrame(export_data)
    csv_filename = "high_risk_missing_tracks.csv"
    df.to_csv(csv_filename, index=False)
    print(f"\n💾 Exported detailed analysis to: {csv_filename}")
    
    print(f"\n💡 RECOMMENDATIONS:")
    print("1. High-risk tracks are most likely among the 65 that failed")
    print("2. Try searching for these manually in YouTube Music to verify availability")
    print("3. Consider alternative versions (non-remastered, studio vs live)")
    print("4. Check if tracks have different titles/artists on YouTube Music")

if __name__ == "__main__":
    analyze_problematic_tracks()