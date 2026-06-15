"""Four-axis scoring: popularity, ease, vibe-fit, member votes.

Popularity and member votes are normalized *within the candidate pool* so the numbers
are comparable. Vetoed songs are dropped before scoring. Weights come from the vibe
preset, already adjusted for the mode by the caller.
"""

from __future__ import annotations

from typing import Optional

from ..models import Scored, Song
from .vibes import VibePreset

DEFAULT_EASE = 0.5


def _normalized(values: list[Optional[float]]) -> list[float]:
    nums = [v for v in values if v]
    hi = max(nums) if nums else 0.0
    return [(v / hi) if (v and hi) else 0.0 for v in values]


def score_pool(songs: list[Song], preset: VibePreset, weights: dict) -> list[Scored]:
    live = [s for s in songs if not s.vetoed]
    if not live:
        return []

    # normalize popularity (Deezer rank) and member upvotes within the pool
    pops = _normalized([s.raw_rank if s.raw_rank else s.popularity for s in live])
    members = _normalized([float(s.upvotes) for s in live])

    wsum = sum(weights.values()) or 1.0
    w = {k: v / wsum for k, v in weights.items()}

    scored: list[Scored] = []
    for song, pop, mem in zip(live, pops, members):
        song.popularity = pop
        ease = song.ease if song.ease is not None else DEFAULT_EASE
        energy = song.energy_proxy if song.energy_proxy is not None else None
        vibe = preset.fit(genre=song.genre, year=song.year, energy=energy, tags=song.tags)
        axes = {"popularity": pop, "ease": ease, "vibe": vibe, "member": mem}
        total = sum(w[k] * axes[k] for k in axes)
        scored.append(Scored(song=song, score=round(total, 4), axes=axes))

    scored.sort(key=lambda s: -s.score)
    return scored
