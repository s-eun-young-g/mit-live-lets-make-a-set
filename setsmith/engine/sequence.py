"""Sequence chosen songs into an energy arc (not just a ranked list).

Target shape across the set: strong opener → build → peak (~2/3 in) → a breather →
strong close. We greedily place songs whose energy best matches each slot's target,
while avoiding back-to-back songs by the same artist.
"""

from __future__ import annotations

from typing import Optional

from ..models import Scored, SetList, SetSlot
from .vibes import VibePreset


def _energy(s: Scored, preset: VibePreset) -> float:
    e = s.song.energy_proxy
    if e is None or e == 0.5:           # fall back to genre proxy if not enriched
        e = preset.energy_for(s.song.genre)
    return e


def target_curve(n: int) -> list[float]:
    """Desired energy (0..1) at each of n slots."""
    curve = []
    for i in range(n):
        t = i / max(1, n - 1)
        if t < 0.10:
            val = 0.80                                   # strong opener
        elif t < 0.65:
            val = 0.70 + 0.27 * (t - 0.10) / 0.55        # build toward the peak
        elif t < 0.80:
            val = 0.97 - 0.50 * (t - 0.65) / 0.15        # drop into a breather
        else:
            val = 0.47 + 0.46 * (t - 0.80) / 0.20        # climb to a big close
        curve.append(min(1.0, val))
    return curve


def sequence_set(chosen: list[Scored], preset: VibePreset,
                 mode: str = "brainstorm", vibe: str = "") -> SetList:
    remaining = list(chosen)
    targets = target_curve(len(remaining))
    energies = {id(s): _energy(s, preset) for s in remaining}

    ordered: list[Scored] = []
    prev_artist: Optional[str] = None
    for ti in targets:
        pool = [s for s in remaining if s.song.artist != prev_artist] or remaining
        pick = min(pool, key=lambda s: (abs(energies[id(s)] - ti), -s.score))
        ordered.append(pick)
        remaining.remove(pick)
        prev_artist = pick.song.artist

    setlist = SetList(mode=mode, vibe=vibe or preset.key)
    peak_idx = max(range(len(ordered)), key=lambda i: energies[id(ordered[i])]) if ordered else -1
    n = len(ordered)
    for i, s in enumerate(ordered):
        setlist.slots.append(SetSlot(scored=s, section=_section(i, n, peak_idx), position=i + 1))
    return setlist


def _section(i: int, n: int, peak_idx: int) -> str:
    if n == 0:
        return ""
    if i == 0:
        return "opener"
    if i == n - 1:
        return "closer"
    if i == peak_idx:
        return "peak"
    t = i / (n - 1)
    if 0.65 <= t < 0.82:
        return "breather"
    return "build"
