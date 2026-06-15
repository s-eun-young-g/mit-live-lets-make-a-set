"""Runtime configuration (override with SETSMITH_* / LASTFM_API_KEY env vars)."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

__version__ = "0.1.0"

DATA_DIR = Path(os.environ.get("SETSMITH_DATA_DIR", Path.home() / ".local" / "share" / "setsmith"))
USER_AGENT = os.environ.get(
    "SETSMITH_USER_AGENT",
    f"setsmith/{__version__} (band set-list tool; "
    "+https://github.com/s-eun-young-g/mit-live-lets-make-a-set)",
)


@dataclass(frozen=True)
class Settings:
    data_dir: Path = DATA_DIR
    user_agent: str = USER_AGENT
    lastfm_key: str | None = os.environ.get("LASTFM_API_KEY") or None
    min_request_interval: float = float(os.environ.get("SETSMITH_RATE", "0.2"))
    cache_ttl_hours: float = float(os.environ.get("SETSMITH_TTL_HOURS", "168"))
    request_timeout: float = float(os.environ.get("SETSMITH_TIMEOUT", "20"))
    host: str = os.environ.get("SETSMITH_HOST", "0.0.0.0")
    port: int = int(os.environ.get("SETSMITH_PORT", "8000"))

    @property
    def db_path(self) -> Path:
        return self.data_dir / "setsmith.db"

    @property
    def cache_path(self) -> Path:
        return self.data_dir / "httpcache.sqlite"


settings = Settings()
