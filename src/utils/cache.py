"""Query result caching for Genie agents.

This module provides an in-memory cache for Genie query results with
TTL-based expiration, thread-safety, and statistics tracking.
"""

from __future__ import annotations

import hashlib
import logging
import threading
import time
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class CacheConfig:
    """Configuration for the query cache."""

    enabled: bool = True
    ttl_seconds: int = 300
    max_size: int = 1000


@dataclass
class CacheStats:
    """Statistics for cache performance monitoring."""

    hits: int = 0
    misses: int = 0
    evictions: int = 0
    total_queries: int = 0
    cache_size: int = 0

    @property
    def hit_rate(self) -> float:
        """Calculate the cache hit rate.

        Returns:
            Hit rate as a float between 0.0 and 1.0
        """
        if self.total_queries == 0:
            return 0.0
        return self.hits / self.total_queries


@dataclass
class CacheEntry:
    """A single cache entry with metadata."""

    value: Any  # Store GenieResult directly, not JSON
    created_at: float
    space_id: str
    question_hash: str

    def is_expired(self, ttl_seconds: int) -> bool:
        """Check if this entry has expired.

        Args:
            ttl_seconds: Time-to-live in seconds

        Returns:
            True if the entry has expired
        """
        return (time.time() - self.created_at) > ttl_seconds


class QueryCache:
    """Thread-safe in-memory cache for Genie query results.

    Provides LRU eviction, TTL-based expiration, and statistics tracking.

    Example:
        >>> cache = QueryCache(CacheConfig(ttl_seconds=300))
        >>> cache.set("space123", "What is revenue?", result)
        >>> cached = cache.get("space123", "What is revenue?")
        >>> if cached is not None:
        ...     print("Cache hit!")
    """

    def __init__(self, config: CacheConfig | None = None):
        """Initialize the query cache.

        Args:
            config: Cache configuration (uses defaults if not provided)
        """
        self._config = config or CacheConfig()
        self._cache: dict[str, CacheEntry] = {}
        self._access_order: list[str] = []  # For LRU eviction
        self._lock = threading.Lock()
        self._stats = CacheStats()

    @staticmethod
    def _generate_key(space_id: str, question: str) -> str:
        """Generate a cache key from space ID and question.

        Args:
            space_id: The Genie Space ID
            question: The natural language question

        Returns:
            A 32-character hash key
        """
        normalized = question.strip().lower()
        content = f"{space_id}:{normalized}"
        return hashlib.sha256(content.encode()).hexdigest()[:32]

    def get(
        self,
        space_id: str,
        question: str,
        fresh: bool = False,
    ) -> Any | None:
        """Get cached result.

        Args:
            space_id: The Genie Space ID
            question: The natural language question
            fresh: If True, bypass cache and return None

        Returns:
            The stored object (GenieResult) or None if not found/expired
        """
        if not self._config.enabled or fresh:
            with self._lock:
                self._stats.total_queries += 1
                self._stats.misses += 1
            return None

        key = self._generate_key(space_id, question)

        with self._lock:
            self._stats.total_queries += 1
            entry = self._cache.get(key)

            if entry is None:
                self._stats.misses += 1
                logger.debug("Cache miss for space=%s", space_id)
                return None

            if entry.is_expired(self._config.ttl_seconds):
                del self._cache[key]
                if key in self._access_order:
                    self._access_order.remove(key)
                self._stats.misses += 1
                self._stats.evictions += 1
                self._stats.cache_size = len(self._cache)
                logger.debug("Cache entry expired for space=%s", space_id)
                return None

            # Update LRU order
            if key in self._access_order:
                self._access_order.remove(key)
            self._access_order.append(key)

            self._stats.hits += 1
            logger.debug("Cache hit for space=%s", space_id)
            return entry.value

    def set(self, space_id: str, question: str, result: Any) -> None:
        """Store a result (GenieResult object) in the cache.

        Args:
            space_id: The Genie Space ID
            question: The natural language question
            result: The result to cache (typically GenieResult)
        """
        if not self._config.enabled:
            return

        key = self._generate_key(space_id, question)

        with self._lock:
            # LRU eviction if at capacity
            while len(self._cache) >= self._config.max_size and self._access_order:
                lru_key = self._access_order.pop(0)
                if lru_key in self._cache:
                    del self._cache[lru_key]
                    self._stats.evictions += 1

            self._cache[key] = CacheEntry(
                value=result,
                created_at=time.time(),
                space_id=space_id,
                question_hash=key,
            )

            if key in self._access_order:
                self._access_order.remove(key)
            self._access_order.append(key)

            self._stats.cache_size = len(self._cache)
            logger.debug("Cached result for space=%s", space_id)

    def invalidate(self, space_id: str | None = None) -> int:
        """Invalidate cache entries.

        Args:
            space_id: If provided, only invalidate entries for this space.
                     If None, invalidate all entries.

        Returns:
            Number of entries invalidated
        """
        with self._lock:
            if space_id is None:
                count = len(self._cache)
                self._cache.clear()
                self._access_order.clear()
                self._stats.evictions += count
                self._stats.cache_size = 0
                logger.info("Invalidated all %d cache entries", count)
                return count

            keys_to_remove = [k for k, e in self._cache.items() if e.space_id == space_id]
            for key in keys_to_remove:
                del self._cache[key]
                if key in self._access_order:
                    self._access_order.remove(key)
                self._stats.evictions += 1

            self._stats.cache_size = len(self._cache)
            logger.info(
                "Invalidated %d entries for space=%s",
                len(keys_to_remove),
                space_id,
            )
            return len(keys_to_remove)

    def get_stats(self) -> CacheStats:
        """Get current cache statistics.

        Returns:
            CacheStats with current metrics
        """
        with self._lock:
            return CacheStats(
                hits=self._stats.hits,
                misses=self._stats.misses,
                evictions=self._stats.evictions,
                total_queries=self._stats.total_queries,
                cache_size=len(self._cache),
            )

    def reset_stats(self) -> None:
        """Reset statistics while keeping cached data."""
        with self._lock:
            self._stats = CacheStats(cache_size=len(self._cache))

    def clear(self) -> None:
        """Clear all cached data and reset statistics."""
        with self._lock:
            self._cache.clear()
            self._access_order.clear()
            self._stats = CacheStats()
            logger.info("Cache cleared")


# Module-level singleton
_global_cache: QueryCache | None = None
_global_cache_lock = threading.Lock()


def get_query_cache(config: CacheConfig | None = None) -> QueryCache:
    """Get or create the global query cache singleton.

    Args:
        config: Optional configuration (only used on first call)

    Returns:
        The global QueryCache instance
    """
    global _global_cache
    with _global_cache_lock:
        if _global_cache is None:
            _global_cache = QueryCache(config)
        return _global_cache


def clear_query_cache() -> None:
    """Clear and reset the global query cache."""
    global _global_cache
    with _global_cache_lock:
        if _global_cache is not None:
            _global_cache.clear()
        _global_cache = None
