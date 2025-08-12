"""
YouTube Music Deduplication utilities integrated into MusicLib.

Provides a programmatic interface to authenticate with YouTube Music via
ytmusicapi, scan a user's library for likely duplicate tracks, rank them,
and optionally create a playlist containing the duplicates.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any, Dict, List, Optional
import re

try:
    from ytmusicapi import YTMusic  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    YTMusic = None  # type: ignore


@dataclass
class RankedDuplicate:
    id: str
    title: str
    album: str
    source: str
    quality: str
    quality_score: int
    duration: str
    thumbnail: str
    artists: List[str]
    is_explicit: bool
    original_data: Dict[str, Any]


class YouTubeMusicDeduplicator:
    """Detect and manage duplicates in a YouTube Music library."""

    def __init__(self, headers_auth_path: Optional[str] = None, ytmusic: Optional[YTMusic] = None):
        self.headers_auth_path = str(headers_auth_path) if headers_auth_path else None
        self.ytmusic: Optional[YTMusic] = ytmusic
        self.library_songs: List[Dict[str, Any]] = []
        self.duplicate_groups: List[Dict[str, Any]] = []

    def is_available(self) -> bool:
        """Return True if ytmusicapi is importable."""
        return YTMusic is not None

    def authenticate(self) -> bool:
        """Authenticate with YouTube Music using headers_auth.json."""
        if not self.is_available():
            raise RuntimeError("ytmusicapi not installed. Install with: pip install ytmusicapi")

        if self.ytmusic is not None:
            # Already authenticated
            return True

        if not self.headers_auth_path or not Path(self.headers_auth_path).exists():
            return False

        try:
            self.ytmusic = YTMusic(self.headers_auth_path)
            # Probe the API to verify session
            self.ytmusic.get_library_songs(limit=1)
            return True
        except Exception:
            self.ytmusic = None
            return False

    def get_library_songs(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Fetch library songs and cache them locally."""
        if not self.ytmusic:
            raise RuntimeError("Not authenticated with YouTube Music")
        songs = self.ytmusic.get_library_songs(limit=limit)
        self.library_songs = songs or []
        return self.library_songs

    @staticmethod
    def _normalize(text: str) -> str:
        if not text:
            return ""
        normalized = re.sub(r"[^\w\s]", "", text.lower().strip())
        return re.sub(r"\s+", " ", normalized)

    @classmethod
    def _similarity(cls, a: str, b: str) -> float:
        return SequenceMatcher(None, cls._normalize(a), cls._normalize(b)).ratio()

    def find_duplicates(self, similarity_threshold: float = 0.85) -> List[Dict[str, Any]]:
        """Group likely duplicates using title+artist similarity.

        Returns a list of groups with ranked duplicate entries.
        """
        if not self.library_songs:
            return []

        groups: List[Dict[str, Any]] = []
        processed: set[int] = set()

        for i, song1 in enumerate(self.library_songs):
            if i in processed:
                continue

            title1 = song1.get("title", "")
            artists1 = [a.get("name", "") for a in song1.get("artists", [])]
            artist1 = artists1[0] if artists1 else ""

            current_group = [song1]
            idx_group = {i}
            # Track worst-case similarities for the representative pair (for display only)
            rep_title_sim = 1.0
            rep_artist_sim = 1.0

            for j, song2 in enumerate(self.library_songs[i + 1 :], i + 1):
                if j in processed:
                    continue

                title2 = song2.get("title", "")
                artists2 = [a.get("name", "") for a in song2.get("artists", [])]
                artist2 = artists2[0] if artists2 else ""

                t_sim = self._similarity(title1, title2)
                a_sim = self._similarity(artist1, artist2)
                if t_sim >= similarity_threshold and a_sim >= similarity_threshold:
                    current_group.append(song2)
                    idx_group.add(j)
                    rep_title_sim = min(rep_title_sim, t_sim)
                    rep_artist_sim = min(rep_artist_sim, a_sim)

            if len(current_group) > 1:
                ranked = self._rank_duplicates(current_group)
                groups.append(
                    {
                        "id": len(groups) + 1,
                        "title": title1,
                        "artist": artist1,
                        "duplicates": ranked,
                        "similarity_scores": {
                            "title_similarity": rep_title_sim,
                            "artist_similarity": rep_artist_sim,
                        },
                    }
                )
                processed.update(idx_group)

        self.duplicate_groups = groups
        return groups

    def _rank_duplicates(self, duplicates: List[Dict[str, Any]]) -> List[RankedDuplicate]:
        def quality_score(song: Dict[str, Any]) -> int:
            score = 0
            album = song.get("album", {}) or {}
            album_name = str(album.get("name", ""))
            if album_name:
                low = album_name.lower()
                if "album" in low or len(low) > 10:
                    score += 10
                elif "single" in low:
                    score += 5
            duration = song.get("duration_seconds") or 0
            if isinstance(duration, (int, float)) and duration > 60:
                score += 5
            # Prefer explicit versions strongly
            is_explicit = bool(song.get("isExplicit"))
            title = str(song.get("title", "")).lower()
            if is_explicit or "explicit" in title:
                score += 15
            if "clean" in title or "radio edit" in title:
                score -= 3
            if song.get("videoType") == "MUSIC_VIDEO_TYPE_ATV":
                score += 8
            return score

        ranked: List[RankedDuplicate] = []
        for s in duplicates:
            q = quality_score(s)
            qlabel = "High" if q >= 15 else ("Medium" if q >= 8 else "Low")
            album = s.get("album", {}) or {}
            album_name = str(album.get("name", ""))
            src = (
                "Single"
                if "single" in album_name.lower()
                else ("Album" if album_name and len(album_name) > 3 else "Unknown")
            )
            is_explicit = bool(s.get("isExplicit")) or ("explicit" in str(s.get("title", "")).lower())
            ranked.append(
                RankedDuplicate(
                    id=str(s.get("videoId", "")),
                    title=str(s.get("title", "")),
                    album=album_name,
                    source=src,
                    quality=qlabel,
                    quality_score=q,
                    duration=str(s.get("duration", "")),
                    thumbnail=(s.get("thumbnails", [{}])[-1] or {}).get("url", "")
                    if s.get("thumbnails")
                    else "",
                    artists=[a.get("name", "") for a in s.get("artists", [])],
                    is_explicit=is_explicit,
                    original_data=s,
                )
            )

        ranked.sort(key=lambda x: x.quality_score, reverse=True)
        return ranked

    def create_playlist(self, title: str, song_ids: List[str], description: str = "") -> str:
        """Create a YouTube Music playlist and add given `videoId`s."""
        if not self.ytmusic:
            raise RuntimeError("Not authenticated with YouTube Music")
        playlist_id = self.ytmusic.create_playlist(title=title, description=description)
        if song_ids:
            self.ytmusic.add_playlist_items(playlist_id, song_ids)
        return playlist_id

    def create_duplicates_playlist(
        self,
        name: Optional[str] = None,
        include_group_ids: Optional[List[int]] = None,
        prefer_explicit: bool = False,
        losers_only: bool = False,
        winners_only: bool = False,
    ) -> Dict[str, Any]:
        """Create a playlist composed of duplicates from detected groups.

        - prefer_explicit: if True, when picking a single preferred item, choose
          the first explicit entry in the ranked list if available.
        - losers_only: if True, add all entries except the preferred one.
          Useful when you want a playlist of items to remove, keeping the preferred.
        - winners_only: if True, add only the preferred entry per group.
        """
        if not self.duplicate_groups:
            return {"success": False, "error": "No duplicate groups available"}

        ids: List[str] = []
        if include_group_ids:
            chosen = [g for g in self.duplicate_groups if g["id"] in set(include_group_ids)]
        else:
            chosen = self.duplicate_groups

        for g in chosen:
            dup_ids: List[str] = []
            exp_flags: List[bool] = []
            for d in g["duplicates"]:
                if isinstance(d, RankedDuplicate):
                    dup_ids.append(d.id)
                    exp_flags.append(bool(d.is_explicit))
                else:
                    dup_ids.append(str(d.get("id", "")))
                    exp_flags.append(bool(d.get("is_explicit") or ("explicit" in str(d.get("title", "")).lower())))

            if not dup_ids:
                continue

            preferred_idx = 0
            if prefer_explicit:
                try:
                    preferred_idx = exp_flags.index(True)
                except ValueError:
                    preferred_idx = 0

            if winners_only:
                ids.append(dup_ids[preferred_idx])
            elif losers_only:
                ids.extend([vid for i, vid in enumerate(dup_ids) if i != preferred_idx])
            else:
                ids.extend(dup_ids)
        ids = [i for i in ids if i]
        if not ids:
            return {"success": False, "error": "No songs to add"}

        playlist_name = name or f"🗂️ True Duplicates ({datetime.now().strftime('%Y-%m-%d')})"
        playlist_id = self.create_playlist(playlist_name, ids, "Duplicate songs playlist")
        return {
            "success": True,
            "playlist_id": playlist_id,
            "playlist_url": f"https://music.youtube.com/playlist?list={playlist_id}",
            "total_added": len(ids),
        }
