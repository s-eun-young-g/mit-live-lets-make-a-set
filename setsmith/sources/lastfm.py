"""Optional Last.fm enrichment (needs a free LASTFM_API_KEY).

When a key is present we widen discovery with mood-tag charts (e.g. "party", "chill")
and tag each resulting song with that mood, which sharpens vibe-fit. Without a key
every method is a no-op, so the rest of the app is unaffected.
"""

from __future__ import annotations

from typing import Optional

from ..http import Client
from ..models import Song

BASE = "https://ws.audioscrobbler.com/2.0/"


class LastFM:
    def __init__(self, client: Client, api_key: Optional[str]):
        self.client = client
        self.api_key = api_key

    @property
    def enabled(self) -> bool:
        return bool(self.api_key)

    def _call(self, method: str, **params):
        return self.client.get_json(BASE, {
            "method": method, "api_key": self.api_key, "format": "json", **params})

    def tag_tracks(self, tag: str, *, limit: int = 40) -> list[Song]:
        """Top tracks for a mood/genre tag, each tagged with that mood."""
        if not self.enabled:
            return []
        try:
            data = self._call("tag.gettoptracks", tag=tag, limit=limit)
        except Exception:
            return []
        out = []
        for t in (data.get("tracks", {}) or {}).get("track", []) or []:
            name = t.get("name")
            artist = (t.get("artist") or {}).get("name")
            if name and artist:
                out.append(Song(title=name, artist=artist, source="lastfm",
                                tags=[tag], is_suggestion=True))
        return out
