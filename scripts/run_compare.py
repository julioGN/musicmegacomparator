#!/usr/bin/env python3
"""
Lightweight compare runner that avoids optional CLI imports.

Usage:
  PYTHONPATH=musicweb/src python3 scripts/run_compare.py \
    --source private/spot.json --target private/Library.xml \
    --strict False --output-dir private/results
"""

import argparse
import time
from pathlib import Path

from musicweb import LibraryComparator, detect_platform, create_parser


def load_library(path: str, platform: str | None = None):
    path_obj = Path(path)
    if not path_obj.exists():
        raise FileNotFoundError(f"File not found: {path}")
    if not platform:
        platform = detect_platform(str(path_obj))
        print(f"Auto-detected platform for {path_obj.name}: {platform}")
    parser = create_parser(platform)
    lib = parser.parse_file(str(path_obj))
    print(f"Loaded {lib.name}: {lib.music_count} music, {lib.non_music_count} non-music")
    return lib


def main():
    ap = argparse.ArgumentParser(description="Run library comparison with minimal deps")
    ap.add_argument("--source", required=True, help="Source library file")
    ap.add_argument("--target", required=True, help="Target library file")
    ap.add_argument("--strict", default="True", help="Use strict matching (True/False)")
    ap.add_argument("--no-duration", action="store_true", help="Disable duration matching")
    ap.add_argument("--use-album", action="store_true", help="Enable album matching")
    ap.add_argument("--output-dir", default="private/results", help="Output directory")
    args = ap.parse_args()

    strict_mode = str(args.strict).lower() in {"1", "true", "yes", "y"}

    src = load_library(args.source)
    tgt = load_library(args.target)

    comp = LibraryComparator(
        strict_mode=strict_mode,
        enable_duration=not args.no_duration,
        enable_album=args.use_album,
    )
    print(f"\nComparing '{src.name}' vs '{tgt.name}' (strict={strict_mode})...")
    t0 = time.time()
    res = comp.compare_libraries(src, tgt)
    dt = time.time() - t0
    stats = res.get_stats()
    print(f"Done in {dt:.1f}s — match rate: {stats['match_rate']:.1f}% | missing: {stats['missing_tracks']}")

    out_dir = args.output_dir
    files = res.save_results(out_dir)
    for kind, path in files.items():
        print(f"Saved {kind}: {path}")


if __name__ == "__main__":
    main()

