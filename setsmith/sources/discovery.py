"""Build a candidate song pool for a vibe via Deezer (open discovery).

Strategy: pull the genre charts that match the vibe preset, optionally expand from
seed artists (their top tracks + related artists' top tracks), tag each song with the
genre it came from and a genre-derived energy proxy, then dedupe.
"""

from __future__ import annotations

from typing import Optional

from ..engine.vibes import GENRE_ENERGY, VibePreset, get_vibe
from ..models import Song
from .deezer import Deezer


def _genre_id_map(deezer: Deezer) -> dict[str, int]:
    return {g["name"].lower(): g["id"] for g in deezer.genres()}


def _tag(song: Song, genre: Optional[str]) -> Song:
    if genre and not song.genre:
        song.genre = genre
    song.energy_proxy = GENRE_ENERGY.get(song.genre or "", 0.55)
    return song


def discover(deezer: Deezer, vibe: str, *, seed_artists: Optional[list[str]] = None,
             per_genre: int = 40, limit: int = 150, lastfm=None) -> list[Song]:
    preset: VibePreset = get_vibe(vibe)
    gmap = _genre_id_map(deezer)
    pool: dict[str, Song] = {}

    def add(songs, genre=None):
        for s in songs:
            s = _tag(s, genre)
            pool.setdefault(s.key, s)

    matched = 0
    for name in preset.genres:
        gid = gmap.get(name.lower())
        if gid is None:
            continue
        matched += 1
        add(deezer.chart_tracks(gid, limit=per_genre), genre=name)

    if matched == 0:                      # vibe genres not found → global chart
        add(deezer.chart_tracks(0, limit=per_genre))

    for artist in (seed_artists or []):
        aid = deezer.artist_id(artist)
        if not aid:
            continue
        add(deezer.artist_top(aid, limit=15))
        for rid in deezer.related_artists(aid, limit=6):
            add(deezer.artist_top(rid, limit=8))

    # optional: widen with Last.fm mood-tag charts (sharpens vibe-fit)
    if lastfm is not None and getattr(lastfm, "enabled", False):
        for tag in preset.tags:
            for s in lastfm.tag_tracks(tag, limit=30):
                pool.setdefault(s.key, s)

    songs = list(pool.values())
    songs.sort(key=lambda s: -(s.raw_rank or 0))    # popular first; engine re-scores
    return songs[:limit]
