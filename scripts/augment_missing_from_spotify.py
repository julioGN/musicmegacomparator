#!/usr/bin/env python3
"""
Augment missing-tracks CSV with ISRC codes by matching against a local Spotify library export.

This avoids external APIs: it uses your spot.json (or CSV) and fuzzy matching to find
corresponding Spotify tracks and copy their ISRC where available.

Usage:
  PYTHONPATH=musicweb/src python3 scripts/augment_missing_from_spotify.py \
    --input private/results/playlist_missing.csv \
    --spotify private/spot.json \
    --output private/results/playlist_missing_soundiiz_enriched.csv \
    [--threshold 0.82]
"""

from __future__ import annotations

import csv
from pathlib import Path
from typing import List, Dict, Any

from musicweb.platforms import create_parser
from musicweb.platforms.detection import detect_platform
from musicweb.core.models import Track, Library, TrackMatcher


def load_spotify_library(path: str) -> Library:
    platform = detect_platform(path)
    if platform != 'spotify':
        raise ValueError(f"Expected a Spotify file, detected '{platform}' for {path}")
    parser = create_parser(platform)
    return parser.parse_file(path)


def load_missing_rows(path: str) -> List[Dict[str, Any]]:
    rows = []
    with open(path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for r in reader:
            rows.append(r)
    return rows


def build_track_from_row(r: Dict[str, Any]) -> Track:
    title = r.get('playlist_title') or r.get('title') or r.get('Name') or ''
    artist = r.get('playlist_artist') or r.get('artist') or r.get('Artist') or ''
    album = r.get('playlist_album') or r.get('album') or r.get('Album') or None
    dur = r.get('playlist_duration') or r.get('duration') or r.get('Duration') or ''
    try:
        duration = int(float(dur)) if dur not in (None, '') else None
    except Exception:
        duration = None
    return Track(title=str(title), artist=str(artist), album=str(album) if album else None, duration=duration)


def write_soundiiz_csv(rows: List[Dict[str, Any]], out_path: str) -> None:
    with open(out_path, 'w', newline='', encoding='utf-8') as f:
        fieldnames = ['Title', 'Artist', 'Album', 'ISRC', 'Duration']
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in rows:
            writer.writerow({
                'Title': r.get('Title', ''),
                'Artist': r.get('Artist', ''),
                'Album': r.get('Album', ''),
                'ISRC': r.get('ISRC', ''),
                'Duration': r.get('Duration', ''),
            })


def main(argv=None) -> int:
    import argparse
    ap = argparse.ArgumentParser(description='Augment missing CSV with ISRC from local Spotify library')
    ap.add_argument('--input', required=True, help='Input missing CSV path')
    ap.add_argument('--spotify', required=True, help='Spotify export path (JSON or CSV)')
    ap.add_argument('--output', required=True, help='Output Soundiiz CSV path')
    ap.add_argument('--threshold', type=float, default=0.82, help='Match confidence threshold')
    args = ap.parse_args(argv)

    missing = load_missing_rows(args.input)
    spot_lib = load_spotify_library(args.spotify)
    matcher = TrackMatcher(strict_mode=False, enable_duration=True, enable_album=True)

    out_rows: List[Dict[str, Any]] = []
    total = len(missing)
    for i, r in enumerate(missing, start=1):
        src = build_track_from_row(r)
        best = None
        best_score = 0.0
        for cand in spot_lib.music_tracks:
            score = matcher.calculate_match_confidence(src, cand)
            if score > best_score:
                best_score = score
                best = cand
        isrc = best.isrc if (best and best.isrc and best_score >= args.threshold) else ''
        out_rows.append({
            'Title': src.title,
            'Artist': src.artist,
            'Album': src.album or '',
            'ISRC': isrc,
            'Duration': src.duration or '',
        })
        if i % 50 == 0:
            print(f"Matched {i}/{total}...")

    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    write_soundiiz_csv(out_rows, args.output)
    print(f"Wrote Soundiiz CSV with ISRC (where matched) to {args.output}")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())

