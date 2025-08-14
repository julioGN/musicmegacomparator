#!/usr/bin/env python3
"""
Convert a missing-tracks CSV into an Apple Music-compatible text playlist (UTF-16 TSV).

Input: CSV with columns at least: title, artist, album, duration
Output: UTF-16 tab-delimited text with header: Name, Artist, Album, Time

Usage:
  python3 scripts/convert_missing_to_apple_txt.py \
    --input private/results/playlist_missing.csv \
    --output private/results/playlist_missing_apple.txt
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path
from typing import Optional


def sec_to_time(sec: Optional[str | int | float]) -> str:
    if sec is None or sec == "":
        return ""
    try:
        s = int(float(sec))
    except Exception:
        return ""
    h = s // 3600
    m = (s % 3600) // 60
    ss = s % 60
    if h > 0:
        return f"{h}:{m:02d}:{ss:02d}"
    return f"{m}:{ss:02d}"


def convert(input_csv: str, output_txt: str) -> None:
    rows_out: list[str] = []
    # Header with Apple Music-friendly columns
    header = ["Name", "Artist", "Album", "Time"]
    rows_out.append("\t".join(header))

    input_path = Path(input_csv)
    if not input_path.exists():
        raise FileNotFoundError(f"Input CSV not found: {input_csv}")

    with input_path.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            title = r.get("title") or r.get("Title") or r.get("playlist_title") or r.get("playlist_title".title()) or r.get("Name") or ""
            artist = r.get("artist") or r.get("Artist") or r.get("playlist_artist") or ""
            album = r.get("album") or r.get("Album") or r.get("playlist_album") or ""
            duration = r.get("duration") or r.get("Duration") or r.get("playlist_duration") or ""
            time_str = sec_to_time(duration)
            line = [title.strip(), artist.strip(), (album or "").strip(), time_str]
            rows_out.append("\t".join(line))

    # Write UTF-16 with BOM so Apple Music recognizes it
    out_path = Path(output_txt)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    content = "\n".join(rows_out)
    out_path.write_text(content, encoding="utf-16")


def main(argv=None) -> int:
    import argparse
    ap = argparse.ArgumentParser(description="Convert missing CSV to Apple Music text playlist")
    ap.add_argument("--input", required=True, help="Input CSV path")
    ap.add_argument("--output", required=True, help="Output TXT path")
    args = ap.parse_args(argv)
    convert(args.input, args.output)
    print(f"Wrote Apple Music playlist text to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

