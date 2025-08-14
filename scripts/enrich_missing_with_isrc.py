#!/usr/bin/env python3
"""
Enrich a missing-tracks CSV with ISRC codes using MusicBrainz, then write
an updated CSV suitable for Soundiiz import.

Usage:
  python3 scripts/enrich_missing_with_isrc.py \
    --input private/results/playlist_missing.csv \
    --output private/results/playlist_missing_enriched.csv

Note: Requires network access. Respects MusicBrainz rate limits.
"""

from __future__ import annotations

import csv
from pathlib import Path
from typing import List

from musicweb.core.models import Track
from musicweb.core.enrichment import EnrichmentManager


def load_tracks_from_csv(path: str) -> List[Track]:
    rows = []
    with open(path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for r in reader:
            title = r.get('playlist_title') or r.get('title') or r.get('Name') or ''
            artist = r.get('playlist_artist') or r.get('artist') or r.get('Artist') or ''
            album = r.get('playlist_album') or r.get('album') or r.get('Album') or ''
            dur = r.get('playlist_duration') or r.get('duration') or r.get('Duration') or ''
            try:
                duration = int(float(dur)) if dur not in (None, '') else None
            except Exception:
                duration = None
            isrc = r.get('isrc') or r.get('ISRC') or None
            rows.append(Track(title=title, artist=artist, album=album or None, duration=duration, isrc=isrc))
    return rows


def write_enriched_csv(tracks: List[Track], out_path: str) -> None:
    with open(out_path, 'w', newline='', encoding='utf-8') as f:
        fieldnames = ['Title', 'Artist', 'Album', 'ISRC', 'Duration']
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for t in tracks:
            writer.writerow({
                'Title': t.title,
                'Artist': t.artist,
                'Album': t.album or '',
                'ISRC': t.isrc or '',
                'Duration': t.duration or ''
            })


def main(argv=None) -> int:
    import argparse
    ap = argparse.ArgumentParser(description='Enrich missing CSV with ISRC via MusicBrainz')
    ap.add_argument('--input', required=True, help='Input missing CSV path')
    ap.add_argument('--output', required=True, help='Output enriched CSV path')
    args = ap.parse_args(argv)

    tracks = load_tracks_from_csv(args.input)
    mgr = EnrichmentManager()

    def cb(i, n, msg):
        print(f"[{i}/{n}] {msg}")

    enriched_pairs = mgr.bulk_enrich(tracks, progress_callback=cb)
    enhanced = [t for (t, _) in enriched_pairs]
    write_enriched_csv(enhanced, args.output)
    print(f"Wrote enriched CSV with ISRC to {args.output}")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())

