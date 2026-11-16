"""
scratch_next.cache_http
=======================
F028: ReadOnlySafeMode / F048: SmartTTLCache / F052: CircuitBreaker 搭載HTTPクライアント
"""

import json
import time
import threading
import urllib.request
import urllib.error
from typing import Any, Dict, Optional, Tuple
from .exceptions import ScratchNextError, AuthenticationError, RateLimitError, SecurityViolationError


class SmartCache:
    """F048: スレッドセーフなLRU+TTLメモリキャッシュ"""
    def __init__(self, default_ttl: float = 30.0, max_size: int = 4096):
        self.default_ttl = default_ttl
        self.max_size = max_size
        self._store: Dict[str, Tuple[float, Any]] = {}
        self._lock = threading.Lock()
        self.hits = 0
        self.misses = 0

    def get(self, key: str) -> Optional[Any]:
        with self._lock:
            item = self._store.get(key)
            if not item:
                self.misses += 1
                return None
            exp, val = item
            if time.monotonic() > exp:
                del self._store[key]
                self.misses += 1
                return None
            self.hits += 1
            return val

    def set(self, key: str, value: Any, ttl: Optional[float] = None) -> None:
        with self._lock:
            if len(self._store) >= self.max_size:
                del self._store[next(iter(self._store))]
            self._store[key] = (time.monotonic() + (ttl or self.default_ttl), value)

    def stats(self) -> Dict[str, Any]:
        total = self.hits + self.misses
        return {
            "entries": len(self._store),
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate": round((self.hits / total * 100) if total else 0.0, 2),
        }

    def clear(self) -> None:
        with self._lock:
            self._store.clear()


class HTTPClient:
    """指数バックオフ・サーキットブレーカー・セーフモード内蔵HTTPエンジン"""
    BASE_API = "https://api.scratch.mit.edu"
    BASE_SITE = "https://scratch.mit.edu"

    def __init__(self, session_id: Optional[str] = None, csrf_token: str = "a", username: Optional[str] = None):
        self.session_id = session_id
        self.csrf_token = csrf_token
        self.username = username
        self.cache = SmartCache(default_ttl=30.0)
        self.read_only_mode = False
        self._consecutive_failures = 0
        self._circuit_open_until = 0.0

    def _headers(self) -> Dict[str, str]:
        h = {
            "User-Agent": "Mozilla/5.0 (Scratch-Next/3.0.0)",
            "Accept": "application/json",
            "Content-Type": "application/json",
            "X-CSRFToken": self.csrf_token,
            "X-Requested-With": "XMLHttpRequest",
            "Referer": "https://scratch.mit.edu/",
        }
        if self.session_id:
            h["Cookie"] = f'scratchsessionsid="{self.session_id}"; scratchcsrftoken={self.csrf_token};'
        return h

    def request(
        self,
        method: str,
        url: str,
        data: Optional[Dict[str, Any]] = None,
        use_cache: bool = False,
        retries: int = 3,
    ) -> Any:
        if self.read_only_mode and method.upper() in ("POST", "PUT", "DELETE"):
            raise SecurityViolationError(f"ReadOnlySafeMode blocked {method} {url}")

        if time.monotonic() < self._circuit_open_until:
            raise ScratchNextError("CircuitBreaker is OPEN. Cooling down API requests.")

        cache_key = f"{method}:{url}"
        if use_cache and method == "GET":
            cached = self.cache.get(cache_key)
            if cached is not None:
                return cached

        body = json.dumps(data).encode("utf-8") if data is not None else None
        req = urllib.request.Request(url, data=body, headers=self._headers(), method=method)

        last_err = None
        for attempt in range(retries):
            try:
                with urllib.request.urlopen(req, timeout=15) as resp:
                    raw = resp.read().decode("utf-8", errors="replace")
                    parsed = json.loads(raw) if raw.strip().startswith(("{", "[")) else raw
                    self._consecutive_failures = 0
                    if use_cache and method == "GET":
                        self.cache.set(cache_key, parsed)
                    return parsed
            except urllib.error.HTTPError as e:
                if e.code == 429:
                    time.sleep(1.5 * (attempt + 1))
                    last_err = RateLimitError(f"Rate limited: {url}")
                    continue
                if e.code in (401, 403):
                    raise AuthenticationError(f"HTTP {e.code} Unauthorized: {url}") from e
                last_err = ScratchNextError(f"HTTP {e.code}: {e.reason}")
            except Exception as e:
                last_err = ScratchNextError(f"Network error: {e}")
                time.sleep(0.35 * (attempt + 1))

        self._consecutive_failures += 1
        if self._consecutive_failures >= 5:
            self._circuit_open_until = time.monotonic() + 15.0
        raise last_err or ScratchNextError("HTTP Request failed")
