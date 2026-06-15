"""Assemble a set list: weight by mode -> score -> select to length -> sequence.

The caller composes the candidate ``pool`` per mode:
- brainstorm: discovery songs only
- ranker:     member-proposed songs only
- mix:        proposals + discovery
This module handles weighting, selection to the target length, and sequencing.
"""

from __future__ import annotations

from typing import Optional

from ..models import SetList, Song
from .score import score_pool
from .sequence import sequence_set
from .vibes import get_vibe

DEFAULT_COUNT = 15


def adjust_weights(base: dict, mode: str) -> dict:
    """Tune the axis weights for the mode."""
    w = dict(base)
    if mode == "brainstorm":
        w["member"] = 0.0                       # no member signal in pure brainstorm
    elif mode == "ranker":
        # the band's voice dominates when we're only ranking their picks
        w = {"popularity": 0.20, "ease": 0.15, "vibe": 0.15, "member": 0.50}
    # "mix" keeps the vibe's base weights
    return w


def _select(scored, target_count: Optional[int], target_minutes: Optional[float]):
    chosen, minutes = [], 0.0
    for s in scored:
        chosen.append(s)
        minutes += s.song.duration_min
        if target_minutes and minutes >= target_minutes:
            break
        if target_count and len(chosen) >= target_count:
            break
    return chosen


def build_setlist(pool: list[Song], *, mode: str = "brainstorm", vibe: str = "wedding",
                  target_count: Optional[int] = None,
                  target_minutes: Optional[float] = None,
                  weights: Optional[dict] = None,
                  guaranteed_keys: Optional[set] = None) -> SetList:
    preset = get_vibe(vibe)
    w = adjust_weights(weights or preset.weights, mode)
    scored = score_pool(pool, preset, w)
    if not target_count and not target_minutes:
        target_count = DEFAULT_COUNT
    # pin guaranteed songs (e.g. band proposals in mix mode) ahead of suggestions
    guaranteed_keys = guaranteed_keys or set()
    if guaranteed_keys:
        must = [s for s in scored if s.song.key in guaranteed_keys]
        rest = [s for s in scored if s.song.key not in guaranteed_keys]
        scored = must + rest
    chosen = _select(scored, target_count, target_minutes)
    return sequence_set(chosen, preset, mode=mode, vibe=vibe)
