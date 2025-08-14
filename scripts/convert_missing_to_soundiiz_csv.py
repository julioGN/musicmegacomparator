#!/usr/bin/env python3
"""
Convert a missing-tracks CSV into a Soundiiz-friendly CSV.

Reads a CSV produced by the Playlist Audit or Compare tools and outputs
columns that Soundiiz recognizes (Title, Artist, Album, ISRC, Duration).

Usage:
  python3 scripts/convert_missing_to_soundiiz_csv.py \
    --input private/results/playlist_missing.csv \
    --output private/results/playlist_missing_soundiiz.csv \
    [--delimiter ',']
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path
from typing import Optional


def load_rows(input_csv: str):
    p = Path(input_csv)
    if not p.exists():
        raise FileNotFoundError(f"Input CSV not found: {input_csv}")
    with p.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            yield r


def pick(r: dict, keys: list[str]) -> str:
    for k in keys:
        v = r.get(k)
        if v not in (None, ""):
            return str(v)
    return ""


def convert(input_csv: str, output_csv: str, delimiter: str = ",") -> None:
    out_path = Path(output_csv)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    with out_path.open("w", newline="", encoding="utf-8") as f:
        fieldnames = ["Title", "Artist", "Album", "ISRC", "Duration"]
        writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter=delimiter)
        writer.writeheader()

        for r in load_rows(input_csv):
            title = pick(r, [
                "playlist_title", "title", "Title", "Name"
            ])
            artist = pick(r, [
                "playlist_artist", "artist", "Artist"
            ])
            album = pick(r, [
                "playlist_album", "album", "Album"
            ])
            isrc = pick(r, [
                "isrc", "ISRC"
            ])
            duration = pick(r, [
                "playlist_duration", "duration", "Duration"
            ])
            writer.writerow({
                "Title": title,
                "Artist": artist,
                "Album": album,
                "ISRC": isrc,
                "Duration": duration,
            })


def main(argv=None) -> int:
    import argparse
    ap = argparse.ArgumentParser(description="Convert missing CSV to Soundiiz CSV")
    ap.add_argument("--input", required=True, help="Input missing CSV path")
    ap.add_argument("--output", required=True, help="Output Soundiiz CSV path")
    ap.add_argument("--delimiter", default=",", help="CSV delimiter for output (default ',')")
    args = ap.parse_args(argv)
    convert(args.input, args.output, args.delimiter)
    print(f"Wrote Soundiiz CSV to {args.output} (delimiter '{args.delimiter}')")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

