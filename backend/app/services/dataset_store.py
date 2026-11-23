from __future__ import annotations

import os
import json
import threading
import time
from collections import OrderedDict
from dataclasses import dataclass, field
from typing import Any

import pandas as pd
from dotenv import load_dotenv


@dataclass
class DatasetSession:
    dataset_id: str
    name: str
    suffix: str
    mime_type: str
    size: int
    raw: bytes
    frame: pd.DataFrame
    sheets: list[str]
    active_sheet: str
    created_at: float = field(default_factory=time.time)
    last_accessed: float = field(default_factory=time.time)
    cache: dict[str, Any] = field(default_factory=dict)


class DatasetCapacityError(RuntimeError):
    """Raised when all bounded in-memory dataset slots are occupied."""


class DatasetStore:
    def __init__(self, ttl_seconds: int = 900, maximum_sessions: int = 3):
        self.ttl_seconds = ttl_seconds
        self.maximum_sessions = maximum_sessions
        self._items: dict[str, DatasetSession] = {}
        self._lock = threading.RLock()
        self._stop = threading.Event()
        self._sweeper = threading.Thread(target=self._sweep_loop, name="dataset-session-cleanup", daemon=True)
        self._sweeper.start()

    def _expire(self) -> int:
        cutoff = time.time() - self.ttl_seconds
        expired = [key for key, item in self._items.items() if item.last_accessed < cutoff]
        for key in expired:
            del self._items[key]
        return len(expired)

    def _sweep_loop(self) -> None:
        interval = max(5, min(60, self.ttl_seconds / 4))
        while not self._stop.wait(interval):
            with self._lock:
                self._expire()

    def cleanup(self) -> int:
        with self._lock:
            return self._expire()

    def stats(self) -> dict[str, int]:
        with self._lock:
            self._expire()
            return {"sessions": len(self._items), "maximum_sessions": self.maximum_sessions, "ttl_seconds": self.ttl_seconds}

    def put(self, session: DatasetSession) -> None:
        with self._lock:
            self._expire()
            if len(self._items) >= self.maximum_sessions:
                raise DatasetCapacityError(
                    f"The server already has {self.maximum_sessions} active datasets. "
                    "Please clear an existing dataset or wait for an inactive session to expire."
                )
            self._items[session.dataset_id] = session

    def get(self, dataset_id: str) -> DatasetSession | None:
        with self._lock:
            self._expire()
            item = self._items.get(dataset_id)
            if item:
                item.last_accessed = time.time()
            return item

    def delete(self, dataset_id: str) -> bool:
        with self._lock:
            return self._items.pop(dataset_id, None) is not None

    def clear(self) -> None:
        with self._lock:
            self._items.clear()


def cached_analysis(session: DatasetSession, namespace: str, payload: Any, factory, maximum: int = 32):
    cache: OrderedDict = session.cache.setdefault("analysis_results", OrderedDict())
    key = f"{namespace}:{json.dumps(payload, sort_keys=True, default=str, separators=(',', ':'))}"
    if key in cache:
        cache.move_to_end(key)
        return cache[key]
    result = factory()
    cache[key] = result
    while len(cache) > maximum:
        cache.popitem(last=False)
    return result


def invalidate_analysis(session: DatasetSession, prefix: str | None = None) -> None:
    cache: OrderedDict = session.cache.get("analysis_results", OrderedDict())
    if prefix is None:
        cache.clear()
    else:
        for key in [key for key in cache if key.startswith(prefix)]:
            del cache[key]


load_dotenv()
dataset_store = DatasetStore(
    ttl_seconds=int(os.getenv("DATASET_TTL_SECONDS", "900")),
    maximum_sessions=int(os.getenv("MAX_DATASET_SESSIONS", "3")),
)
