"""
core/local_state_client.py — In-Memory State Client (OSS-4 / #1085).

Drop-in replacement for Redis in desktop/local mode. Provides the same
interface as redis-py for the operations used by the AAAgents codebase:

  - get/set/delete (key-value)
  - setnx (distributed locks)
  - rpush/ltrim/lrange (lists / rolling buffers)
  - xadd/xread (streams — simplified in-memory FIFO)
  - ping (health check)
  - pipeline (batched operations)

All data is ephemeral (in-memory, lost on process restart). This is
acceptable for desktop mode where persistence is handled by SQLite.

Thread-safe via threading.Lock.
"""

import json
import logging
import threading
import time
import uuid
from collections import defaultdict, deque
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class LocalPipeline:
    """Batch command executor for LocalStateClient (mimics redis.Pipeline)."""

    def __init__(self, client: "LocalStateClient"):
        self._client = client
        self._commands: list = []

    def rpush(self, key: str, *values):
        self._commands.append(("rpush", key, values))
        return self

    def ltrim(self, key: str, start: int, end: int):
        self._commands.append(("ltrim", key, start, end))
        return self

    async def execute(self):
        # BORA-02: Acquire the parent client's lock to prevent race conditions
        # when concurrent threads call rpush/ltrim/lrange while a pipeline runs.
        with self._client._lock:
            results = []
            for cmd in self._commands:
                if cmd[0] == "rpush":
                    for v in cmd[2]:
                        self._client._lists[cmd[1]].append(v)
                    results.append(len(self._client._lists[cmd[1]]))
                elif cmd[0] == "ltrim":
                    key, start, end = cmd[1], cmd[2], cmd[3]
                    lst = self._client._lists[key]
                    # Redis LTRIM semantics: keep elements [start, end] inclusive
                    trimmed = (
                        list(lst)[start:] if end == -1 else list(lst)[start : end + 1]
                    )
                    self._client._lists[key] = deque(trimmed)
                    results.append(True)
            self._commands.clear()
            return results


class LocalStateClient:
    """In-memory state client replacing Redis for desktop mode.

    Implements the subset of the redis-py API used across the AAAgents
    codebase. Thread-safe, ephemeral (no disk persistence).

    Used by RedisClient as a transparent fallback when REDIS_URL is empty.
    """

    def __init__(self):
        self._lock = threading.Lock()
        self._store: Dict[str, str] = {}
        self._lists: Dict[str, deque] = defaultdict(deque)
        self._streams: Dict[str, list] = defaultdict(list)
        self._expiries: Dict[str, float] = {}
        logger.info("LocalStateClient initialized (in-memory, no Redis)")

    # ── Pub/Sub ──────────────────────────────────────────────────────────────

    async def publish(self, channel: str, message: str) -> int:
        """Stub for pub/sub publish to prevent crashes and warnings in local mode."""
        logger.debug("LocalStateClient: publish to %s skipped in local mode", channel)
        return 0

    # ── Key-Value ────────────────────────────────────────────────────────────

    async def get(self, key: str) -> Optional[str]:
        with self._lock:
            self._evict_expired(key)
            return self._store.get(key)

    def get_sync(self, key: str) -> Optional[str]:
        """Synchronous get (for get_sync_redis consumers)."""
        with self._lock:
            self._evict_expired(key)
            return self._store.get(key)

    async def set(
        self, key: str, value: str, px: int | None = None, nx: bool = False
    ) -> Optional[bool]:
        with self._lock:
            self._evict_expired(key)
            if nx and key in self._store:
                return None  # SETNX semantics: key exists → no-op
            self._store[key] = str(value)
            if px:
                self._expiries[key] = time.time() + (px / 1000.0)
            return True

    def set_sync(
        self, key: str, value: str, px: int | None = None, nx: bool = False
    ) -> Optional[bool]:
        """Synchronous set."""
        with self._lock:
            self._evict_expired(key)
            if nx and key in self._store:
                return None
            self._store[key] = str(value)
            if px:
                self._expiries[key] = time.time() + (px / 1000.0)
            return True

    async def delete(self, *keys: str) -> int:
        with self._lock:
            count = 0
            for key in keys:
                if key in self._store:
                    del self._store[key]
                    self._expiries.pop(key, None)
                    count += 1
            return count

    def delete_sync(self, *keys: str) -> int:
        """Synchronous delete."""
        with self._lock:
            count = 0
            for key in keys:
                if key in self._store:
                    del self._store[key]
                    self._expiries.pop(key, None)
                    count += 1
            return count

    # ── Health ───────────────────────────────────────────────────────────────

    async def ping(self) -> bool:
        return True

    def ping_sync(self) -> bool:
        return True

    # ── Lists (OHLCV Rolling Buffer) ─────────────────────────────────────────

    async def rpush(self, key: str, *values) -> int:
        with self._lock:
            for v in values:
                self._lists[key].append(v)
            return len(self._lists[key])

    async def ltrim(self, key: str, start: int, end: int) -> bool:
        with self._lock:
            lst = self._lists[key]
            trimmed = list(lst)[start:] if end == -1 else list(lst)[start : end + 1]
            self._lists[key] = deque(trimmed)
            return True

    async def lrange(self, key: str, start: int, end: int) -> List[str]:
        with self._lock:
            lst = list(self._lists[key])
            if end == -1:
                return lst[start:]
            return lst[start : end + 1]

    def pipeline(self) -> LocalPipeline:
        return LocalPipeline(self)

    # ── Streams (Inter-Agent Messaging) ──────────────────────────────────────

    async def xadd(self, stream: str, fields: Dict[str, str]) -> str:
        with self._lock:
            ts = int(time.time() * 1000)
            msg_id = f"{ts}-{len(self._streams[stream])}"
            self._streams[stream].append((msg_id, fields))
            return msg_id

    async def xread(self, streams: Dict[str, str], count: int = 100) -> list:
        with self._lock:
            result = []
            for stream_name, last_id in streams.items():
                entries = self._streams.get(stream_name, [])
                if last_id == "$":
                    # Only new messages (none in-memory)
                    filtered = []
                elif last_id == "0":
                    filtered = entries[:count]
                else:
                    # Find entries after last_id
                    filtered = []
                    found = False
                    for entry in entries:
                        if found:
                            filtered.append(entry)
                            if len(filtered) >= count:
                                break
                        if entry[0] == last_id:
                            found = True
                if filtered:
                    result.append((stream_name, filtered))
            return result

    # ── Cleanup ──────────────────────────────────────────────────────────────

    async def aclose(self):
        """Mimics redis.aclose() — clears in-memory state."""
        with self._lock:
            self._store.clear()
            self._lists.clear()
            self._streams.clear()
            self._expiries.clear()

    def close(self):
        """Synchronous close."""
        with self._lock:
            self._store.clear()
            self._lists.clear()
            self._streams.clear()
            self._expiries.clear()

    # ── Internal ─────────────────────────────────────────────────────────────

    def _evict_expired(self, key: str):
        """Remove key if its TTL has expired (called under lock)."""
        if key in self._expiries and time.time() > self._expiries[key]:
            self._store.pop(key, None)
            del self._expiries[key]
