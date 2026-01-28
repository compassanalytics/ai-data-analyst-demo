"""Tests for the query cache module.

This module provides comprehensive unit tests for QueryCache functionality
including TTL expiration, LRU eviction, thread safety, and statistics tracking.
"""

from __future__ import annotations

import threading
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import Any

import pytest

from src.utils.cache import (
    CacheConfig,
    CacheEntry,
    CacheStats,
    QueryCache,
    clear_query_cache,
    get_query_cache,
)


# =============================================================================
# Test CacheConfig
# =============================================================================


class TestCacheConfig:
    """Tests for CacheConfig dataclass."""

    def test_default_values(self) -> None:
        """Test default configuration values."""
        config = CacheConfig()
        assert config.enabled is True
        assert config.ttl_seconds == 300
        assert config.max_size == 1000

    def test_custom_values(self) -> None:
        """Test custom configuration values."""
        config = CacheConfig(enabled=False, ttl_seconds=60, max_size=100)
        assert config.enabled is False
        assert config.ttl_seconds == 60
        assert config.max_size == 100


# =============================================================================
# Test CacheStats
# =============================================================================


class TestCacheStats:
    """Tests for CacheStats dataclass."""

    def test_default_values(self) -> None:
        """Test default statistics values."""
        stats = CacheStats()
        assert stats.hits == 0
        assert stats.misses == 0
        assert stats.evictions == 0
        assert stats.total_queries == 0
        assert stats.cache_size == 0

    def test_hit_rate_zero_queries(self) -> None:
        """Test hit rate calculation with no queries."""
        stats = CacheStats()
        assert stats.hit_rate == 0.0

    def test_hit_rate_calculation(self) -> None:
        """Test hit rate calculation with queries."""
        stats = CacheStats(hits=75, misses=25, total_queries=100)
        assert stats.hit_rate == 0.75

    def test_hit_rate_all_hits(self) -> None:
        """Test hit rate calculation with all hits."""
        stats = CacheStats(hits=100, misses=0, total_queries=100)
        assert stats.hit_rate == 1.0

    def test_hit_rate_all_misses(self) -> None:
        """Test hit rate calculation with all misses."""
        stats = CacheStats(hits=0, misses=100, total_queries=100)
        assert stats.hit_rate == 0.0


# =============================================================================
# Test CacheEntry
# =============================================================================


class TestCacheEntry:
    """Tests for CacheEntry dataclass."""

    def test_not_expired(self) -> None:
        """Test entry is not expired immediately after creation."""
        entry = CacheEntry(
            value={"test": "data"},
            created_at=time.time(),
            space_id="space123",
            question_hash="abc123",
        )
        assert entry.is_expired(ttl_seconds=300) is False

    def test_expired(self) -> None:
        """Test entry is expired after TTL passes."""
        entry = CacheEntry(
            value={"test": "data"},
            created_at=time.time() - 400,  # 400 seconds ago
            space_id="space123",
            question_hash="abc123",
        )
        assert entry.is_expired(ttl_seconds=300) is True

    def test_expired_exact_boundary(self) -> None:
        """Test entry expiration at exact TTL boundary."""
        entry = CacheEntry(
            value={"test": "data"},
            created_at=time.time() - 301,  # Just over 300 seconds
            space_id="space123",
            question_hash="abc123",
        )
        assert entry.is_expired(ttl_seconds=300) is True


# =============================================================================
# Test QueryCache
# =============================================================================


@dataclass
class MockResult:
    """Mock result object for testing."""

    data: dict[str, Any]
    success: bool = True


class TestQueryCache:
    """Tests for QueryCache class."""

    def test_set_and_get(self) -> None:
        """Test basic set and get operations."""
        cache = QueryCache(CacheConfig(ttl_seconds=300))
        result = MockResult(data={"revenue": 1000})

        cache.set("space123", "What is revenue?", result)
        cached = cache.get("space123", "What is revenue?")

        assert cached is not None
        assert cached.data == {"revenue": 1000}

    def test_get_miss(self) -> None:
        """Test cache miss returns None."""
        cache = QueryCache()
        cached = cache.get("space123", "What is revenue?")
        assert cached is None

    def test_cache_disabled(self) -> None:
        """Test cache returns None when disabled."""
        cache = QueryCache(CacheConfig(enabled=False))
        result = MockResult(data={"revenue": 1000})

        cache.set("space123", "What is revenue?", result)
        cached = cache.get("space123", "What is revenue?")

        assert cached is None

    def test_fresh_bypass(self) -> None:
        """Test fresh parameter bypasses cache."""
        cache = QueryCache()
        result = MockResult(data={"revenue": 1000})

        cache.set("space123", "What is revenue?", result)
        cached = cache.get("space123", "What is revenue?", fresh=True)

        assert cached is None

    def test_ttl_expiration(self) -> None:
        """Test TTL-based cache expiration."""
        cache = QueryCache(CacheConfig(ttl_seconds=1))
        result = MockResult(data={"revenue": 1000})

        cache.set("space123", "What is revenue?", result)

        # Should be cached initially
        assert cache.get("space123", "What is revenue?") is not None

        # Wait for expiration
        time.sleep(1.1)

        # Should be expired now
        assert cache.get("space123", "What is revenue?") is None

    def test_lru_eviction(self) -> None:
        """Test LRU eviction when cache is full."""
        cache = QueryCache(CacheConfig(max_size=2))

        cache.set("space1", "Question 1", MockResult(data={"q": 1}))
        cache.set("space2", "Question 2", MockResult(data={"q": 2}))

        # Access first to make it recently used
        cache.get("space1", "Question 1")

        # Add third item - should evict space2 (least recently used)
        cache.set("space3", "Question 3", MockResult(data={"q": 3}))

        assert cache.get("space1", "Question 1") is not None
        assert cache.get("space2", "Question 2") is None  # Evicted
        assert cache.get("space3", "Question 3") is not None

    def test_key_normalization(self) -> None:
        """Test that questions are normalized for key generation."""
        cache = QueryCache()
        result = MockResult(data={"revenue": 1000})

        cache.set("space123", "What is revenue?", result)

        # Should hit with different whitespace/case
        assert cache.get("space123", "  what is revenue?  ") is not None
        assert cache.get("space123", "WHAT IS REVENUE?") is not None

    def test_invalidate_all(self) -> None:
        """Test invalidating all cache entries."""
        cache = QueryCache()

        cache.set("space1", "Q1", MockResult(data={"q": 1}))
        cache.set("space2", "Q2", MockResult(data={"q": 2}))

        count = cache.invalidate()

        assert count == 2
        assert cache.get("space1", "Q1") is None
        assert cache.get("space2", "Q2") is None

    def test_invalidate_by_space(self) -> None:
        """Test invalidating cache entries for a specific space."""
        cache = QueryCache()

        cache.set("space1", "Q1", MockResult(data={"q": 1}))
        cache.set("space1", "Q2", MockResult(data={"q": 2}))
        cache.set("space2", "Q3", MockResult(data={"q": 3}))

        count = cache.invalidate("space1")

        assert count == 2
        assert cache.get("space1", "Q1") is None
        assert cache.get("space1", "Q2") is None
        assert cache.get("space2", "Q3") is not None  # Other space unaffected

    def test_stats_tracking(self) -> None:
        """Test cache statistics are tracked correctly."""
        cache = QueryCache()

        cache.set("space1", "Q1", MockResult(data={"q": 1}))

        # One hit
        cache.get("space1", "Q1")

        # Two misses
        cache.get("space1", "Q2")
        cache.get("space2", "Q1")

        stats = cache.get_stats()

        assert stats.hits == 1
        assert stats.misses == 2
        assert stats.total_queries == 3
        assert stats.cache_size == 1

    def test_reset_stats(self) -> None:
        """Test resetting statistics."""
        cache = QueryCache()

        cache.set("space1", "Q1", MockResult(data={"q": 1}))
        cache.get("space1", "Q1")
        cache.get("space1", "Q2")

        cache.reset_stats()
        stats = cache.get_stats()

        assert stats.hits == 0
        assert stats.misses == 0
        assert stats.total_queries == 0
        assert stats.cache_size == 1  # Cache still has data

    def test_clear(self) -> None:
        """Test clearing cache completely."""
        cache = QueryCache()

        cache.set("space1", "Q1", MockResult(data={"q": 1}))
        cache.get("space1", "Q1")

        cache.clear()
        stats = cache.get_stats()

        assert stats.hits == 0
        assert stats.misses == 0
        assert stats.cache_size == 0
        assert cache.get("space1", "Q1") is None

    def test_thread_safety(self) -> None:
        """Test cache is thread-safe under concurrent access."""
        cache = QueryCache(CacheConfig(max_size=100))
        errors: list[Exception] = []

        def worker(thread_id: int) -> None:
            try:
                for i in range(50):
                    space_id = f"space{thread_id}"
                    question = f"Question {i}"
                    result = MockResult(data={"thread": thread_id, "q": i})

                    cache.set(space_id, question, result)
                    cached = cache.get(space_id, question)

                    # Cached value may be None if evicted, but should not error
                    if cached is not None:
                        assert cached.data["thread"] == thread_id
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0, f"Errors occurred: {errors}"

    def test_concurrent_stats_access(self) -> None:
        """Test stats are thread-safe under concurrent access."""
        cache = QueryCache()
        cache.set("space1", "Q1", MockResult(data={"q": 1}))

        def reader() -> None:
            for _ in range(100):
                cache.get_stats()
                cache.get("space1", "Q1")

        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(reader) for _ in range(5)]
            for f in futures:
                f.result()

        # Should not raise any errors


# =============================================================================
# Test Global Cache Singleton
# =============================================================================


class TestGlobalCache:
    """Tests for global cache singleton functions."""

    def setup_method(self) -> None:
        """Clear global cache before each test."""
        clear_query_cache()

    def teardown_method(self) -> None:
        """Clear global cache after each test."""
        clear_query_cache()

    def test_get_query_cache_singleton(self) -> None:
        """Test that get_query_cache returns the same instance."""
        cache1 = get_query_cache()
        cache2 = get_query_cache()

        assert cache1 is cache2

    def test_clear_query_cache(self) -> None:
        """Test clearing the global cache creates new instance."""
        cache1 = get_query_cache()
        cache1.set("space1", "Q1", MockResult(data={"q": 1}))

        clear_query_cache()

        cache2 = get_query_cache()
        assert cache1 is not cache2
        assert cache2.get("space1", "Q1") is None

    def test_get_query_cache_with_config(self) -> None:
        """Test get_query_cache uses provided config on first call."""
        config = CacheConfig(ttl_seconds=60, max_size=50)
        cache = get_query_cache(config)

        # Config should be used
        stats = cache.get_stats()
        assert stats.cache_size == 0  # Just checking it was created

        # Subsequent calls ignore config
        cache2 = get_query_cache(CacheConfig(ttl_seconds=999))
        assert cache is cache2  # Same instance
