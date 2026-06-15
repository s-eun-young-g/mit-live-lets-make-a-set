"""SQLite persistence: gigs, members, songs, votes.

Songs round-trip to the engine's ``Song`` model; votes are aggregated into each
song's ``upvotes`` / ``vetoed`` flags when loaded (any veto removes the song).
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Optional

from .models import Song

SCHEMA = """
CREATE TABLE IF NOT EXISTS gig (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT, vibe TEXT, mode TEXT,
    target_count INTEGER, target_minutes REAL,
    weights_json TEXT, setlist_json TEXT, created_at REAL
);
CREATE TABLE IF NOT EXISTS member (
    id INTEGER PRIMARY KEY AUTOINCREMENT, gig_id INTEGER, name TEXT
);
CREATE TABLE IF NOT EXISTS song (
    id INTEGER PRIMARY KEY AUTOINCREMENT, gig_id INTEGER,
    source TEXT, source_id TEXT, title TEXT, artist TEXT,
    duration_s INTEGER, year INTEGER, genre TEXT,
    popularity REAL, energy_proxy REAL, raw_rank INTEGER,
    tags_json TEXT, ease REAL, proposed_by TEXT, is_suggestion INTEGER
);
CREATE TABLE IF NOT EXISTS vote (
    id INTEGER PRIMARY KEY AUTOINCREMENT, gig_id INTEGER,
    song_id INTEGER, member TEXT, value INTEGER,
    UNIQUE(song_id, member)
);
"""

import sqlite3


class DB:
    def __init__(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(SCHEMA)
        self.conn.commit()

    # -- gigs --------------------------------------------------------------
    def create_gig(self, name: str, vibe: str, mode: str,
                   target_count: Optional[int], target_minutes: Optional[float],
                   weights: Optional[dict] = None) -> int:
        cur = self.conn.execute(
            "INSERT INTO gig (name, vibe, mode, target_count, target_minutes, "
            "weights_json, created_at) VALUES (?,?,?,?,?,?,?)",
            (name, vibe, mode, target_count, target_minutes,
             json.dumps(weights) if weights else None, time.time()),
        )
        self.conn.commit()
        return cur.lastrowid

    def get_gig(self, gig_id: int) -> Optional[dict]:
        row = self.conn.execute("SELECT * FROM gig WHERE id=?", (gig_id,)).fetchone()
        if not row:
            return None
        g = dict(row)
        g["weights"] = json.loads(g["weights_json"]) if g["weights_json"] else None
        return g

    def update_gig(self, gig_id: int, **fields) -> None:
        if not fields:
            return
        cols = ", ".join(f"{k}=?" for k in fields)
        self.conn.execute(f"UPDATE gig SET {cols} WHERE id=?",
                          (*fields.values(), gig_id))
        self.conn.commit()

    def save_setlist(self, gig_id: int, setlist: list[dict]) -> None:
        self.conn.execute("UPDATE gig SET setlist_json=? WHERE id=?",
                          (json.dumps(setlist), gig_id))
        self.conn.commit()

    def get_setlist(self, gig_id: int) -> list[dict]:
        row = self.conn.execute("SELECT setlist_json FROM gig WHERE id=?", (gig_id,)).fetchone()
        return json.loads(row["setlist_json"]) if row and row["setlist_json"] else []

    # -- songs -------------------------------------------------------------
    def add_song(self, gig_id: int, song: Song) -> int:
        # de-dupe within a gig by source_id or artist+title
        existing = self.conn.execute(
            "SELECT id FROM song WHERE gig_id=? AND "
            "((source_id IS NOT NULL AND source_id=?) OR "
            "(lower(title)=lower(?) AND lower(artist)=lower(?)))",
            (gig_id, song.source_id, song.title, song.artist),
        ).fetchone()
        if existing:
            return existing["id"]
        cur = self.conn.execute(
            "INSERT INTO song (gig_id, source, source_id, title, artist, duration_s, "
            "year, genre, popularity, energy_proxy, raw_rank, tags_json, ease, "
            "proposed_by, is_suggestion) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (gig_id, song.source, song.source_id, song.title, song.artist,
             song.duration_s, song.year, song.genre, song.popularity,
             song.energy_proxy, song.raw_rank, json.dumps(song.tags),
             song.ease, song.proposed_by, 1 if song.is_suggestion else 0),
        )
        self.conn.commit()
        return cur.lastrowid

    def set_ease(self, song_id: int, ease: Optional[float]) -> None:
        self.conn.execute("UPDATE song SET ease=? WHERE id=?", (ease, song_id))
        self.conn.commit()

    def _row_to_song(self, r: sqlite3.Row, votes: dict) -> Song:
        up, veto = votes.get(r["id"], (0, False))
        return Song(
            title=r["title"], artist=r["artist"], source=r["source"],
            source_id=r["source_id"], duration_s=r["duration_s"], year=r["year"],
            genre=r["genre"], popularity=r["popularity"] or 0.0,
            energy_proxy=r["energy_proxy"] if r["energy_proxy"] is not None else 0.5,
            tags=json.loads(r["tags_json"]) if r["tags_json"] else [],
            ease=r["ease"], proposed_by=r["proposed_by"],
            is_suggestion=bool(r["is_suggestion"]), raw_rank=r["raw_rank"],
            upvotes=up, vetoed=veto, db_id=r["id"],
        )

    def get_songs(self, gig_id: int, *, only_proposals: bool = False) -> list[Song]:
        votes = self._vote_tally(gig_id)
        q = "SELECT * FROM song WHERE gig_id=?"
        if only_proposals:
            q += " AND is_suggestion=0"
        rows = self.conn.execute(q, (gig_id,)).fetchall()
        return [self._row_to_song(r, votes) for r in rows]

    # -- votes -------------------------------------------------------------
    def set_vote(self, gig_id: int, song_id: int, member: str, value: int) -> None:
        if value == 0:
            self.conn.execute("DELETE FROM vote WHERE song_id=? AND member=?",
                              (song_id, member))
        else:
            self.conn.execute(
                "INSERT INTO vote (gig_id, song_id, member, value) VALUES (?,?,?,?) "
                "ON CONFLICT(song_id, member) DO UPDATE SET value=excluded.value",
                (gig_id, song_id, member, value))
        self.conn.commit()

    def _vote_tally(self, gig_id: int) -> dict:
        """song_id -> (upvotes, vetoed)."""
        out: dict[int, tuple[int, bool]] = {}
        for r in self.conn.execute(
                "SELECT song_id, value, COUNT(*) n FROM vote WHERE gig_id=? "
                "GROUP BY song_id, value", (gig_id,)):
            up, veto = out.get(r["song_id"], (0, False))
            if r["value"] > 0:
                up += r["n"]
            elif r["value"] < 0:
                veto = True             # any veto removes the song
            out[r["song_id"]] = (up, veto)
        return out
