"""
Playlist Audit utilities for the Streamlit web app.

Parses a playlist text export and audits it against a loaded Library
using the LibraryComparator/TrackMatcher for fuzzy matching.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple, Dict, Any
import csv

from ..core.models import Track, Library
from ..core.comparison import LibraryComparator


@dataclass
class PlaylistItem:
    title: str
    artist: str
    album: Optional[str] = None
    duration: Optional[int] = None  # seconds


def parse_playlist_bytes(data: bytes) -> List[PlaylistItem]:
    """Parse a playlist text export from bytes into PlaylistItem list.

    Supports Apple Music text export (UTF-16/TSV with headers) and simple
    "Artist - Title" per line formats.
    """
    # Try common encodings for Apple Music text export
    encodings = ["utf-16", "utf-16-le", "utf-16-be", "utf-8-sig", "utf-8"]
    text = None
    for enc in encodings:
        try:
            text = data.decode(enc)
            break
        except Exception:
            continue
    if text is None:
        text = data.decode("utf-8", errors="ignore")

    # Normalize newlines
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = [ln for ln in text.split("\n") if ln.strip()]
    if not lines:
        return []

    header = lines[0]
    items: List[PlaylistItem] = []
    if "\t" in header and ("Name" in header or "N\x00a\x00m\x00e" in header):
        # Tab-separated export with headers
        rows = [ln.split("\t") for ln in lines]
        hdr = [h.strip() for h in rows[0]]

        def find_col(names: List[str]) -> Optional[int]:
            low = [h.lower() for h in hdr]
            for nm in names:
                if nm.lower() in low:
                    return low.index(nm.lower())
            return None

        i_title = find_col(["Name", "Title", "Song", "Track"]) or 0
        i_artist = find_col(["Artist", "Artists", "Performer"]) or 1
        i_album = find_col(["Album", "Release", "Album Name"])  # optional
        i_time = find_col(["Time", "Duration"])  # optional

        for row in rows[1:]:
            title = row[i_title].strip() if i_title < len(row) else ""
            artist = row[i_artist].strip() if i_artist < len(row) else ""
            if not (title and artist):
                continue
            album = row[i_album].strip() if (i_album is not None and i_album < len(row)) else None
            duration = None
            if i_time is not None and i_time < len(row):
                duration = _parse_time_to_seconds(row[i_time].strip())
            items.append(PlaylistItem(title=title, artist=artist, album=album or None, duration=duration))
        return items

    # Otherwise assume simple per-line format: "Artist - Title" or "Title - Artist"
    for ln in lines:
        if " - " in ln:
            left, right = [x.strip() for x in ln.split(" - ", 1)]
            # Default to artist-first
            artist, title = left, right
        else:
            title, artist = ln.strip(), ""
        if title and artist:
            items.append(PlaylistItem(title=title, artist=artist))
    return items


def _parse_time_to_seconds(val: str) -> Optional[int]:
    if not val:
        return None
    s = val.strip()
    try:
        if ":" in s:
            parts = [int(p) for p in s.split(":")]
            if len(parts) == 3:
                return parts[0] * 3600 + parts[1] * 60 + parts[2]
            if len(parts) == 2:
                return parts[0] * 60 + parts[1]
        return int(float(s))
    except Exception:
        return None


def audit_playlist(
    items: List[PlaylistItem],
    library: Library,
    *,
    enable_album: bool = True,
    enable_duration: bool = True,
    present_threshold: float = 0.82,
    review_threshold: float = 0.70,
) -> Dict[str, List[Dict[str, Any]]]:
    """Audit items against the given library and bucket into present/review/missing.

    Returns dict with keys 'present', 'review', 'missing' containing row dicts.
    """
    # Build indices
    exact_idx, base_idx = _build_indices(library.music_tracks)
    present_rows: List[Dict[str, Any]] = []
    review_rows: List[Dict[str, Any]] = []
    missing_rows: List[Dict[str, Any]] = []

    matcher = LibraryComparator(strict_mode=False, enable_duration=enable_duration, enable_album=enable_album).matcher

    for it in items:
        bucket, best, score = _match_item(it, library.music_tracks, exact_idx, base_idx, matcher, present_threshold, review_threshold)
        row = {
            "playlist_title": it.title,
            "playlist_artist": it.artist,
            "playlist_album": it.album or "",
            "playlist_duration": it.duration or "",
            "status": bucket,
            "confidence": round(score, 3),
            "match_title": getattr(best, 'title', '') or '',
            "match_artist": getattr(best, 'artist', '') or '',
            "match_album": getattr(best, 'album', '') or '',
            "match_duration": getattr(best, 'duration', '') or '',
        }
        if bucket == "present":
            present_rows.append(row)
        elif bucket == "review":
            review_rows.append(row)
        else:
            missing_rows.append(row)

    return {"present": present_rows, "review": review_rows, "missing": missing_rows}


def _build_indices(tracks: List[Track]):
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
        cleaned = re.sub(p, " ", cleaned, flags=re.IGNORECASE)
    return re.sub(r"\s+", " ", cleaned).strip()


def _match_item(
    item: PlaylistItem,
    lib_tracks: List[Track],
    exact_idx,
    base_idx,
    matcher,
    present_threshold: float,
    review_threshold: float,
) -> Tuple[str, Optional[Track], float]:
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
        best, best_score = None, 0.0
        for c in candidates:
            score = matcher.calculate_match_confidence(source, c)
            if score > best_score:
                best, best_score = c, score
        if best and best_score >= present_threshold:
            return "present", best, best_score
        if best and best_score >= review_threshold:
            return "review", best, best_score

    # 3) Fuzzy across all (prefilter by artist token overlap)
    src_tokens = source.artist_tokens or set()
    cands = []
    if src_tokens:
        for t in lib_tracks:
            if not t.is_music or not t.artist_tokens:
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
    if best and best_score >= present_threshold:
        return "present", best, best_score
    if best and best_score >= review_threshold:
        return "review", best, best_score
    return "missing", None, best_score or 0.0

