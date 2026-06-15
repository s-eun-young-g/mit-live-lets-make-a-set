"""Scoring + sequencing engine (pure-Python, no web/DB deps)."""

from .vibes import VIBE_PRESETS, get_vibe  # noqa: F401
from .score import score_pool  # noqa: F401
from .sequence import sequence_set  # noqa: F401
from .build import build_setlist  # noqa: F401
