"""Polite, cached HTTP GET-JSON client shared by the music sources."""

from __future__ import annotations

import json
import threading
import time
from typing import Any, Optional

import httpx

from .cache import Cache
from .config import Settings


class Client:
    def __init__(self, settings: Settings, cache: Cache):
        self.settings = settings
        self.cache = cache
        self._last = 0.0
        self._lock = threading.Lock()
        self._http = httpx.Client(
            headers={"User-Agent": settings.user_agent},
            timeout=settings.request_timeout, follow_redirects=True,
        )

    def get_json(self, url: str, params: Optional[dict] = None, *,
                 refresh: bool = False) -> Any:
        key = url + "?" + json.dumps(params or {}, sort_keys=True)
        if not refresh:
            cached = self.cache.get(key, self.settings.cache_ttl_hours * 3600)
            if cached is not None:
                return json.loads(cached)
        with self._lock:
            wait = self.settings.min_request_interval - (time.time() - self._last)
            if wait > 0:
                time.sleep(wait)
            resp = self._http.get(url, params=params)
            self._last = time.time()
        resp.raise_for_status()
        self.cache.put(key, resp.text)
        return resp.json()
