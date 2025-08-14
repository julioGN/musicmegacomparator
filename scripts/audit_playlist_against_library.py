#!/usr/bin/env python3
"""
Audit a playlist export against Apple Music Library.xml to find which items
are already present, which are near-matches (manual review), and which appear missing.

Input formats supported for the playlist file:
- Apple Music text export (tab-delimited, often UTF-16) with headers including Name and Artist
- Simple lines (one per row) in the form: Title - Artist or Artist - Title (auto-detected)

Outputs three CSVs in the chosen output directory:
- playlist_present.csv   (confident present in library)
- playlist_review.csv    (near matches that should be manually reviewed)
- playlist_missing.csv   (no good match in library)

Usage:
  PYTHONPATH=musicweb/src python3 scripts/audit_playlist_against_library.py \
    --playlist "potential missing trax.txt" --library private/Library.xml \
    --output-dir private/results
"""

from __future__ import annotations

import csv
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple

from musicweb import create_parser, detect_platform, LibraryComparator
from musicweb.core.models import Track, Library, TrackNormalizer


@dataclass
class PlaylistItem:
    title: str
    artist: str
    album: str | None = None
    duration: int | None = None  # seconds


def read_playlist(path: str) -> List[PlaylistItem]:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Playlist file not found: {path}")

    # Try common encodings for Apple Music text export
    encodings = ["utf-16", "utf-16-le", "utf-16-be", "utf-8-sig", "utf-8"]
    content = None
    for enc in encodings:
        try:
            content = p.read_text(encoding=enc)
            break
        except Exception:
            continue
    if content is None:
        # Fallback binary decode ignoring errors
        content = p.read_bytes().decode("utf-8", errors="ignore")

    # Normalize newlines
    content = content.replace("\r\n", "\n").replace("\r", "\n")
    lines = [ln for ln in content.split("\n") if ln.strip()]
    if not lines:
        return []

    # Detect tab-delimited header with Name/Artist
    header = lines[0]
    items: List[PlaylistItem] = []
    if "\t" in header and ("Name" in header or "N\x00a\x00m\x00e" in header):
        # Tab-separated export
        # Use csv with delimiter tab
        rows = []
        for ln in lines:
            rows.append(ln.split("\t"))
        # Find columns
        hdr = [h.strip() for h in rows[0]]
        def find_col(names: List[str]) -> Optional[int]:
            low = [h.lower() for h in hdr]
            for nm in names:
                if nm.lower() in low:
                    return low.index(nm.lower())
            return None
        i_title = find_col(["Name", "Title", "Song", "Track"])
        i_artist = find_col(["Artist", "Artists", "Performer"]) 
        i_album = find_col(["Album", "Release", "Album Name"]) 
        i_time = find_col(["Time", "Duration"]) 
        if i_title is None or i_artist is None:
            # Fallback: try first two cols
            i_title, i_artist = 0, 1
        for row in rows[1:]:
            title = row[i_title].strip() if i_title < len(row) else ""
            artist = row[i_artist].strip() if i_artist < len(row) else ""
            album = row[i_album].strip() if (i_album is not None and i_album < len(row)) else None
            duration = None
            if i_time is not None and i_time < len(row):
                duration = _parse_time_to_seconds(row[i_time].strip())
            if title and artist:
                items.append(PlaylistItem(title=title, artist=artist, album=album or None, duration=duration))
        return items

    # Otherwise, simple line format: try to parse as "Artist - Title" or "Title - Artist"
    for ln in lines:
        if " - " in ln:
            left, right = [x.strip() for x in ln.split(" - ", 1)]
            # Heuristic: if either side has commas/featuring keywords, assume artist is left
            if any(k in left.lower() for k in ["feat", "ft", ",", " & "]):
                artist, title = left, right
            else:
                # Prefer artist-first default
                artist, title = left, right
        else:
            # Single token line; treat as title only
            title, artist = ln.strip(), ""
        if title and artist:
            items.append(PlaylistItem(title=title, artist=artist))
    return items


def load_apple_library(xml_path: str) -> Library:
    parser = create_parser("apple_music_xml")
    lib = parser.parse_file(xml_path)
    return lib


def build_indices(tracks: List[Track]):
    # Exact normalized and base-title indices for quick candidate lookups
    exact = {}
    base = {}
    for t in tracks:
        key = (t.normalized_title, t.normalized_artist)
        exact.setdefault(key, []).append(t)
        base_title = _strip_version_tokens(t.normalized_title)
        base.setdefault((base_title, t.normalized_artist), []).append(t)
    return exact, base


def _strip_version_tokens(title: str) -> str:
    import re
    if not title:
        return ""
    patterns = [
        r"\bremaster(?:ed)?\b",
        r"\bremix\b",
        r"\bversion\b",
        r"\blive\b",
        r"\bacoustic\b",
        r"\binstrumental\b",
        r"\bdeluxe\b",
        r"\bextended\b",
        r"\bedit\b",
        r"\bradio\s+edit\b",
        r"\bdemo\b",
        r"\bmono\b",
        r"\bstereo\b",
        r"\bexplicit\b",
        r"\bclean\b",
        r"\b\d{2,4}\s+remaster(?:ed)?\b",
    ]
    cleaned = title
    for p in patterns:
        cleaned = __import__("re").sub(p, " ", cleaned, flags=__import__("re").IGNORECASE)
    return __import__("re").sub(r"\s+", " ", cleaned).strip()


def match_item(item: PlaylistItem, lib_tracks: List[Track], exact_idx, base_idx) -> Tuple[str, Optional[Track], float]:
    # Returns (bucket, best_track, confidence)
    # Buckets: present | review | missing
    source = Track(title=item.title, artist=item.artist, album=item.album or None, duration=item.duration or None, platform="playlist")
    # 1) Exact normalized
    key = (source.normalized_title, source.normalized_artist)
    candidates = exact_idx.get(key, [])
    if candidates:
        return "present", candidates[0], 0.98
    # 2) Base-title exact
    base_title = _strip_version_tokens(source.normalized_title)
    base_key = (base_title, source.normalized_artist)
    candidates = base_idx.get(base_key, [])
    if candidates:
        # Evaluate with matcher (album/duration enabled) to assign confidence
        matcher = LibraryComparator(strict_mode=False, enable_duration=True, enable_album=True).matcher
        best, best_score = None, 0.0
        for c in candidates:
            score = matcher.calculate_match_confidence(source, c)
            if score > best_score:
                best, best_score = c, score
        if best and best_score >= 0.80:
            return "present", best, best_score
        if best and best_score >= 0.70:
            return "review", best, best_score
    # 3) Fuzzy across all (limited scan for performance)
    matcher = LibraryComparator(strict_mode=False, enable_duration=True, enable_album=True).matcher
    # Pre-filter candidates by same artist token overlap to reduce work
    src_tokens = source.artist_tokens or set()
    cands = []
    if src_tokens:
        for t in lib_tracks:
            if not t.is_music:
                continue
            if not t.artist_tokens:
                continue
            if src_tokens.intersection(t.artist_tokens):
                cands.append(t)
    else:
        cands = lib_tracks
    best, best_score = None, 0.0
    for c in cands:
        score = matcher.calculate_match_confidence(source, c)
        if score > best_score:
            best, best_score = c, score
    if best and best_score >= 0.82:
        return "present", best, best_score
    if best and best_score >= 0.70:
        return "review", best, best_score
    return "missing", None, best_score or 0.0


def write_csv(path: Path, rows: List[dict]):
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        for r in rows:
            w.writerow(r)


def main(argv=None):
    import argparse
    ap = argparse.ArgumentParser(description="Audit playlist against Apple Library.xml")
    ap.add_argument("--playlist", required=True, help="Path to playlist text export")
    ap.add_argument("--library", default="private/Library.xml", help="Path to Apple Library.xml")
    ap.add_argument("--output-dir", default="private/results", help="Output directory")
    args = ap.parse_args(argv)

    items = read_playlist(args.playlist)
    if not items:
        print("No playlist items parsed.")
        return 1
    print(f"Parsed {len(items)} playlist items")

    lib = load_apple_library(args.library)
    print(f"Loaded Apple library: {lib.music_count} music tracks")

    exact_idx, base_idx = build_indices(lib.music_tracks)

    present_rows, review_rows, missing_rows = [], [], []
    for it in items:
        bucket, best, score = match_item(it, lib.music_tracks, exact_idx, base_idx)
        row = {
            "playlist_title": it.title,
            "playlist_artist": it.artist,
            "status": bucket,
            "confidence": f"{score:.3f}",
            "match_title": best.title if best else "",
            "match_artist": best.artist if best else "",
            "match_album": best.album if best else "",
            "match_duration": best.duration if best else "",
        }
        if bucket == "present":
            present_rows.append(row)
        elif bucket == "review":
            review_rows.append(row)
        else:
            missing_rows.append(row)

    out_dir = Path(args.output_dir)
    write_csv(out_dir / "playlist_present.csv", present_rows)
    write_csv(out_dir / "playlist_review.csv", review_rows)
    write_csv(out_dir / "playlist_missing.csv", missing_rows)

    print("Done.")
    print(f"  Present: {len(present_rows)}")
    print(f"  Review:  {len(review_rows)}")
    print(f"  Missing: {len(missing_rows)}")
    return 0


def _parse_time_to_seconds(val: str) -> Optional[int]:
    if not val:
        return None
    s = val.strip()
    # Formats: H:MM:SS, M:SS, or pure seconds
    # Also handle integers like 208
    try:
        if ":" in s:
            parts = [p for p in s.split(":") if p != ""]
            parts = [int(p) for p in parts]
            if len(parts) == 3:
                return parts[0] * 3600 + parts[1] * 60 + parts[2]
            if len(parts) == 2:
                return parts[0] * 60 + parts[1]
        # Fallback: numeric seconds
        return int(float(s))
    except Exception:
        return None


if __name__ == "__main__":
    sys.exit(main())
