"""Core data models."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Song:
    """A candidate song, enriched with signals used for scoring."""

    title: str
    artist: str
    source: str = "deezer"
    source_id: Optional[str] = None
    duration_s: Optional[int] = None
    year: Optional[int] = None
    genre: Optional[str] = None
    popularity: float = 0.0          # 0..1, normalized within a pool
    energy_proxy: float = 0.5        # 0..1 (loudness/genre-derived)
    tags: list[str] = field(default_factory=list)
    ease: Optional[float] = None     # 0..1, band-rated; None = use heuristic default
    # provenance within a gig
    proposed_by: Optional[str] = None
    is_suggestion: bool = True
    upvotes: int = 0
    vetoed: bool = False
    # raw popularity rank from the source, before pool-normalization
    raw_rank: Optional[int] = None
    # database row id once persisted to a gig
    db_id: Optional[int] = None

    @property
    def key(self) -> str:
        return f"{self.artist.strip().lower()}|||{self.title.strip().lower()}"

    @property
    def duration_min(self) -> float:
        return (self.duration_s or 210) / 60.0


@dataclass
class Scored:
    song: Song
    score: float
    axes: dict[str, float] = field(default_factory=dict)   # popularity/ease/vibe/member

    def reason(self) -> str:
        bits = [f"{k} {v:.2f}" for k, v in self.axes.items() if v]
        return ", ".join(bits)


@dataclass
class SetSlot:
    scored: Scored
    section: str          # opener / build / peak / breather / closer / encore
    position: int


@dataclass
class SetList:
    slots: list[SetSlot] = field(default_factory=list)
    mode: str = "brainstorm"
    vibe: str = "party"

    @property
    def total_minutes(self) -> float:
        return sum(s.scored.song.duration_min for s in self.slots)
