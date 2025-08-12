"""
Cleanup utilities for YouTube Music based on duplicate analysis.

Provides planning and application of cleanup operations:
- Unlike loser tracks in the user's library (set rating to INDIFFERENT)
- Replace loser occurrences in the user's playlists with the preferred winner
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple
import time

try:
    from ytmusicapi import YTMusic  # type: ignore
except Exception:  # pragma: no cover
    YTMusic = None  # type: ignore


@dataclass
class PlaylistEdit:
    playlist_id: str
    playlist_name: str
    remove_items: List[Dict[str, str]]  # each: {videoId, setVideoId}
    add_video_ids: List[str]
    replacements: List[Dict[str, str]]  # each: {from_setVideoId, to_videoId}


@dataclass
class CleanupPlan:
    winners_by_group: Dict[int, str]
    losers_by_group: Dict[int, List[str]]
    unlike_video_ids: List[str]
    playlist_edits: List[PlaylistEdit]


class YTMusicCleaner:
    """Plan and apply cleanup actions using a YTMusic session."""

    def __init__(self, ytmusic: YTMusic):
        if YTMusic is None:
            raise RuntimeError("ytmusicapi is not installed")
        self.ytmusic = ytmusic

    @staticmethod
    def _extract_video_id(entry: Any) -> Optional[str]:
        if hasattr(entry, 'id'):
            return getattr(entry, 'id') or None
        if isinstance(entry, dict):
            return entry.get('id')
        return None

    @staticmethod
    def _extract_is_explicit(entry: Any) -> bool:
        if hasattr(entry, 'is_explicit'):
            return bool(getattr(entry, 'is_explicit'))
        if isinstance(entry, dict):
            return bool(entry.get('is_explicit') or ("explicit" in str(entry.get('title', '')).lower()))
        return False

    def _build_winners_losers(
        self,
        groups: List[Dict[str, Any]],
        prefer_explicit: bool,
        include_group_ids: Optional[List[int]] = None,
    ) -> Tuple[Dict[int, str], Dict[int, List[str]]]:
        winners: Dict[int, str] = {}
        losers: Dict[int, List[str]] = {}
        chosen = groups
        if include_group_ids:
            filt = set(include_group_ids)
            chosen = [g for g in groups if g['id'] in filt]

        for g in chosen:
            vids: List[str] = []
            flags: List[bool] = []
            for d in g['duplicates']:
                vid = self._extract_video_id(d)
                if not vid:
                    continue
                vids.append(vid)
                flags.append(self._extract_is_explicit(d))
            if not vids:
                continue
            pref_idx = 0
            if prefer_explicit:
                try:
                    pref_idx = flags.index(True)
                except ValueError:
                    pref_idx = 0
            winners[g['id']] = vids[pref_idx]
            losers[g['id']] = [v for i, v in enumerate(vids) if i != pref_idx]

        return winners, losers

    def plan_cleanup(
        self,
        groups: List[Dict[str, Any]],
        prefer_explicit: bool = True,
        include_group_ids: Optional[List[int]] = None,
        replace_in_playlists: bool = True,
        unlike_losers: bool = True,
    ) -> CleanupPlan:
        winners, losers_map = self._build_winners_losers(groups, prefer_explicit, include_group_ids)
        unlike_ids: List[str] = []
        if unlike_losers:
            for vids in losers_map.values():
                unlike_ids.extend(vids)

        playlist_edits: List[PlaylistEdit] = []
        if replace_in_playlists and unlike_ids:
            # Get user's playlists
            playlists = self.ytmusic.get_library_playlists(limit=1000) or []
            for pl in playlists:
                pid = pl.get('playlistId') or pl.get('playlist_id')
                if not pid:
                    continue
                details = self.ytmusic.get_playlist(pid, limit=None)
                tracks = details.get('tracks', [])

                to_remove: List[Dict[str, str]] = []
                to_add: List[str] = []
                existing_ids = {t.get('videoId') for t in tracks if t.get('videoId')}

                for t in tracks:
                    vid = t.get('videoId')
                    set_vid = t.get('setVideoId')
                    if not vid or not set_vid:
                        continue
                    if vid in unlike_ids:
                        # Find corresponding group winner
                        for gid, group_losers in losers_map.items():
                            if vid in group_losers:
                                win_vid = winners.get(gid)
                                if win_vid and win_vid not in existing_ids and win_vid not in to_add:
                                    to_add.append(win_vid)
                                to_remove.append({'videoId': vid, 'setVideoId': set_vid})
                                break

                if to_remove or to_add:
                    playlist_edits.append(
                        PlaylistEdit(
                            playlist_id=pid,
                            playlist_name=details.get('title') or pl.get('title', pid),
                            remove_items=to_remove,
                            add_video_ids=to_add,
                            replacements=[{'from_setVideoId': r['setVideoId'], 'to_videoId': winners.get(self._group_for_loser(losers_map, r['videoId']))} for r in to_remove]
                        )
                    )

        return CleanupPlan(
            winners_by_group=winners,
            losers_by_group=losers_map,
            unlike_video_ids=unlike_ids,
            playlist_edits=playlist_edits,
        )

    @staticmethod
    def _group_for_loser(losers_map: Dict[int, List[str]], video_id: str) -> Optional[int]:
        for gid, vids in losers_map.items():
            if video_id in vids:
                return gid
        return None

    def apply_cleanup(self, plan: CleanupPlan, do_unlike: bool = True, do_playlists: bool = True, generate_undo: bool = False) -> Dict[str, Any]:
        summary: Dict[str, Any] = {
            'unliked': 0,
            'playlist_adds': 0,
            'playlist_removes': 0,
            'errors': []
        }
        undo: Dict[str, Any] = {
            'ratings_like': [],  # videoIds to set back to LIKE
            'playlist_adds': [],  # items we added (to be removed): {playlist_id, items:[{videoId,setVideoId}]}
            'playlist_removes': [],  # items we removed (to re-add): {playlist_id, videoIds:[...]}
        }
        try:
            if do_playlists:
                for edit in plan.playlist_edits:
                    # Add winners first (avoid duplicates)
                    if edit.add_video_ids:
                        self.ytmusic.add_playlist_items(edit.playlist_id, edit.add_video_ids)
                        summary['playlist_adds'] += len(edit.add_video_ids)
                        time.sleep(0.2)
                        if generate_undo:
                            # Refresh to capture setVideoId for newly added winners
                            details = self.ytmusic.get_playlist(edit.playlist_id, limit=None)
                            items = details.get('tracks', [])
                            added = []
                            for it in items:
                                vid = it.get('videoId')
                                set_vid = it.get('setVideoId')
                                if vid in edit.add_video_ids and vid and set_vid:
                                    added.append({'videoId': vid, 'setVideoId': set_vid})
                            undo['playlist_adds'].append({'playlist_id': edit.playlist_id, 'items': added})
                    # Best-effort in-place move: try to move added winners near losers
                    try:
                        details = self.ytmusic.get_playlist(edit.playlist_id, limit=None)
                        items = details.get('tracks', [])
                        id_to_set = {i.get('videoId'): i.get('setVideoId') for i in items if i.get('videoId') and i.get('setVideoId')}
                        if hasattr(self.ytmusic, 'move_playlist_item'):
                            for rep in edit.replacements:
                                loser_set = rep.get('from_setVideoId')
                                winner_vid = rep.get('to_videoId')
                                winner_set = id_to_set.get(winner_vid)
                                if loser_set and winner_set:
                                    try:
                                        # Attempt to move winner before loser; API signature may vary
                                        self.ytmusic.move_playlist_item(edit.playlist_id, winner_set, before_set_video_id=loser_set)  # type: ignore
                                        time.sleep(0.1)
                                    except Exception:
                                        # Try after loser as fallback
                                        try:
                                            self.ytmusic.move_playlist_item(edit.playlist_id, winner_set, after_set_video_id=loser_set)  # type: ignore
                                            time.sleep(0.1)
                                        except Exception:
                                            pass
                    except Exception:
                        pass
                    # Remove losers by setVideoId
                    if edit.remove_items:
                        self.ytmusic.remove_playlist_items(edit.playlist_id, edit.remove_items)
                        summary['playlist_removes'] += len(edit.remove_items)
                        time.sleep(0.2)
                        if generate_undo:
                            undo['playlist_removes'].append({
                                'playlist_id': edit.playlist_id,
                                'videoIds': [ri['videoId'] for ri in edit.remove_items if ri.get('videoId')],
                            })
            if do_unlike:
                for vid in plan.unlike_video_ids:
                    try:
                        self.ytmusic.rate_song(vid, 'INDIFFERENT')
                        summary['unliked'] += 1
                        time.sleep(0.1)
                        if generate_undo:
                            undo['ratings_like'].append(vid)
                    except Exception as e:
                        summary['errors'].append(str(e))
        except Exception as e:
            summary['errors'].append(str(e))
        if generate_undo:
            summary['undo'] = undo
        return summary

    def rollback(self, undo: Dict[str, Any]) -> Dict[str, int]:
        """Apply rollback using the provided undo log."""
        result = {
            'playlist_add_removals': 0,  # removed winners we added
            'playlist_readds': 0,        # re-added losers
            'ratings_liked': 0,
            'errors': 0
        }
        try:
            # Re-add losers to playlists
            for entry in undo.get('playlist_removes', []):
                pid = entry.get('playlist_id')
                vids = entry.get('videoIds', [])
                if pid and vids:
                    self.ytmusic.add_playlist_items(pid, vids)
                    result['playlist_readds'] += len(vids)
                    time.sleep(0.2)

            # Remove winners that were added
            for entry in undo.get('playlist_adds', []):
                pid = entry.get('playlist_id')
                items = entry.get('items', [])
                removes = [{'videoId': it.get('videoId'), 'setVideoId': it.get('setVideoId')} for it in items if it.get('videoId') and it.get('setVideoId')]
                if pid and removes:
                    self.ytmusic.remove_playlist_items(pid, removes)
                    result['playlist_add_removals'] += len(removes)
                    time.sleep(0.2)

            # Restore likes
            for vid in undo.get('ratings_like', []):
                try:
                    self.ytmusic.rate_song(vid, 'LIKE')
                    result['ratings_liked'] += 1
                    time.sleep(0.1)
                except Exception:
                    result['errors'] += 1
        except Exception:
            result['errors'] += 1
        return result
