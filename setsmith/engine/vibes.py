"""Event-vibe presets: target sound + axis-weight profile.

Each preset declares the genres/era/energy that fit the event, plus the base weights
for the four scoring axes (popularity, ease, vibe, member). Modes adjust these later
(brainstorm zeroes the member axis; ranker boosts it).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

# Cheap energy proxy by Deezer genre name (0 = mellow, 1 = high-energy).
GENRE_ENERGY: dict[str, float] = {
    "Dance": 0.9, "Electro": 0.9, "Reggaeton": 0.85, "Rap/Hip Hop": 0.75,
    "Rock": 0.8, "Alternative": 0.7, "Pop": 0.6, "Latin": 0.75, "R&B": 0.55,
    "Reggae": 0.55, "Country": 0.5, "Folk": 0.35, "Soul & Funk": 0.6,
    "Blues": 0.4, "Jazz": 0.3, "Classical": 0.2,
}


@dataclass(frozen=True)
class VibePreset:
    key: str
    name: str
    genres: tuple[str, ...]              # Deezer genre names to draw discovery from
    era_center: int                      # preferred release year center
    era_spread: int                      # tolerance (years)
    energy_target: float                 # 0..1
    weights: dict                        # base axis weights
    tags: tuple[str, ...] = field(default_factory=tuple)

    def energy_for(self, genre: Optional[str]) -> float:
        return GENRE_ENERGY.get(genre or "", 0.55)

    def fit(self, *, genre: Optional[str], year: Optional[int],
            energy: Optional[float], tags: Optional[list[str]] = None) -> float:
        """0..1 vibe-fit from the signals available for a song."""
        comps: list[tuple[float, float]] = []   # (value, weight)

        # genre match
        if genre:
            comps.append((1.0 if genre in self.genres else 0.3, 1.0))

        # era closeness (triangular falloff)
        if year:
            d = abs(year - self.era_center)
            comps.append((max(0.0, 1.0 - d / max(1, self.era_spread)), 0.8))

        # energy closeness
        e = energy if energy is not None else self.energy_for(genre)
        comps.append((1.0 - min(1.0, abs(e - self.energy_target)), 1.0))

        # tag overlap (optional, e.g. from Last.fm)
        if tags and self.tags:
            overlap = len(set(t.lower() for t in tags) & set(t.lower() for t in self.tags))
            comps.append((min(1.0, overlap / 2.0), 0.8))

        wsum = sum(w for _, w in comps) or 1.0
        return sum(v * w for v, w in comps) / wsum


def _w(pop, ease, vibe, member) -> dict:
    return {"popularity": pop, "ease": ease, "vibe": vibe, "member": member}


VIBE_PRESETS: dict[str, VibePreset] = {
    "wedding": VibePreset(
        "wedding", "Wedding reception",
        ("Pop", "Dance", "R&B", "Rock", "Soul & Funk"), 2005, 35, 0.7,
        _w(0.45, 0.15, 0.25, 0.15), ("party", "feel good", "love")),
    "cocktail": VibePreset(
        "cocktail", "Cocktail hour / dinner",
        ("Jazz", "Soul & Funk", "Folk", "Pop", "Blues"), 1985, 40, 0.3,
        _w(0.20, 0.30, 0.35, 0.15), ("chill", "smooth", "mellow")),
    "dive_bar": VibePreset(
        "dive_bar", "Dive bar / pub rock",
        ("Rock", "Alternative", "Pop", "Country"), 1995, 30, 0.8,
        _w(0.35, 0.20, 0.30, 0.15), ("rock", "singalong", "classic")),
    "dance_party": VibePreset(
        "dance_party", "Dance party / club",
        ("Dance", "Electro", "Pop", "Reggaeton", "Rap/Hip Hop"), 2015, 18, 0.92,
        _w(0.35, 0.15, 0.35, 0.15), ("party", "dance", "upbeat")),
    "corporate": VibePreset(
        "corporate", "Corporate / safe crowd-pleaser",
        ("Pop", "R&B", "Rock", "Soul & Funk"), 2008, 30, 0.55,
        _w(0.50, 0.20, 0.15, 0.15), ("feel good", "familiar")),
    "festival": VibePreset(
        "festival", "Festival / big outdoor",
        ("Rock", "Dance", "Pop", "Alternative"), 2012, 25, 0.85,
        _w(0.35, 0.15, 0.35, 0.15), ("anthem", "energetic")),
    "chill": VibePreset(
        "chill", "Chill / background",
        ("Folk", "Jazz", "Pop", "Soul & Funk"), 1990, 40, 0.25,
        _w(0.20, 0.30, 0.35, 0.15), ("chill", "acoustic", "mellow")),
}

DEFAULT_VIBE = "wedding"


def get_vibe(key: Optional[str]) -> VibePreset:
    return VIBE_PRESETS.get(key or DEFAULT_VIBE, VIBE_PRESETS[DEFAULT_VIBE])
