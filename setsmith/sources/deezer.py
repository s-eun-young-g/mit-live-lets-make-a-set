"""Deezer adapter — keyless discovery, popularity, duration, era.

Deezer's public API needs no key. We use it for:
- search (propose autocomplete + seed lookups)
- genre charts and the global chart (discovery candidate pool)
- artist top tracks + related artists (seed-based discovery)
- track detail (optional enrichment: release year, loudness)

Popularity comes from the ``rank`` field; energy is proxied from genre/loudness since
reliable per-track audio features aren't available.
"""

from __future__ import annotations

import re
from typing import Optional

from ..http import Client
from ..models import Song

BASE = "https://api.deezer.com"
_YEAR_RE = re.compile(r"(\d{4})")


def _to_song(item: dict, genre: Optional[str] = None) -> Optional[Song]:
    artist = (item.get("artist") or {}).get("name")
    title = item.get("title") or item.get("title_short")
    if not artist or not title:
        return None
    year = None
    rd = item.get("release_date") or (item.get("album") or {}).get("release_date")
    if rd and (m := _YEAR_RE.search(rd)):
        year = int(m.group(1))
    return Song(
        title=title, artist=artist, source="deezer",
        source_id=str(item.get("id")) if item.get("id") else None,
        duration_s=item.get("duration"),
        year=year, genre=genre,
        raw_rank=item.get("rank"),
    )


class Deezer:
    def __init__(self, client: Client):
        self.client = client

    def search(self, query: str, *, limit: int = 25, **kw) -> list[Song]:
        data = self.client.get_json(f"{BASE}/search", {"q": query, "limit": limit}, **kw)
        out = [_to_song(t) for t in data.get("data", [])]
        return [s for s in out if s]

    def genres(self, **kw) -> list[dict]:
        data = self.client.get_json(f"{BASE}/genre", **kw)
        return [{"id": g["id"], "name": g["name"]} for g in data.get("data", [])
                if g.get("id") != 0]

    def chart_tracks(self, genre_id: int = 0, *, limit: int = 50, **kw) -> list[Song]:
        data = self.client.get_json(
            f"{BASE}/chart/{genre_id}/tracks", {"limit": limit}, **kw)
        out = [_to_song(t) for t in data.get("data", [])]
        return [s for s in out if s]

    def artist_id(self, name: str, **kw) -> Optional[str]:
        data = self.client.get_json(f"{BASE}/search/artist", {"q": name, "limit": 1}, **kw)
        hits = data.get("data") or []
        return str(hits[0]["id"]) if hits else None

    def artist_top(self, artist_id: str, *, limit: int = 25, **kw) -> list[Song]:
        data = self.client.get_json(
            f"{BASE}/artist/{artist_id}/top", {"limit": limit}, **kw)
        return [s for s in (_to_song(t) for t in data.get("data", [])) if s]

    def related_artists(self, artist_id: str, *, limit: int = 12, **kw) -> list[str]:
        data = self.client.get_json(
            f"{BASE}/artist/{artist_id}/related", {"limit": limit}, **kw)
        return [str(a["id"]) for a in data.get("data", [])]

    def track_detail(self, track_id: str, **kw) -> dict:
        """Optional enrichment: bpm, gain (loudness), release_date."""
        return self.client.get_json(f"{BASE}/track/{track_id}", **kw)
