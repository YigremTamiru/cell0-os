"""
Search Result Caching System for Cell 0 OS

Provides intelligent caching for web search results with:
- Time-based expiration
- Query normalization
- Cache persistence
- Memory and disk backends
"""

import os
import json
import hashlib
import asyncio
from typing import Dict, Any, Optional, List, Union
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from pathlib import Path
import logging

logger = logging.getLogger("cell0.search.cache")


@dataclass
class CacheEntry:
    """Single cache entry"""
    query: str
    search_type: str  # web, news, image, academic
    provider: str
    results: List[Dict[str, Any]]
    timestamp: datetime
    expires_at: datetime
    metadata: Dict[str, Any]
    hit_count: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "query": self.query,
            "search_type": self.search_type,
            "provider": self.provider,
            "results": self.results,
            "timestamp": self.timestamp.isoformat(),
            "expires_at": self.expires_at.isoformat(),
            "metadata": self.metadata,
            "hit_count": self.hit_count,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CacheEntry":
        """Create from dictionary"""
        return cls(
            query=data["query"],
            search_type=data["search_type"],
            provider=data["provider"],
            results=data["results"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            expires_at=datetime.fromisoformat(data["expires_at"]),
            metadata=data.get("metadata", {}),
            hit_count=data.get("hit_count", 0),
        )
    
    def is_expired(self) -> bool:
        """Check if entry is expired"""
        return datetime.now() > self.expires_at
    
    def is_fresh(self, max_age: Optional[timedelta] = None) -> bool:
        """Check if entry is still fresh"""
        if self.is_expired():
            return False
        if max_age:
            return datetime.now() - self.timestamp < max_age
        return True


class SearchCache:
    """
    Intelligent search result cache
    
    Features:
    - Query normalization for better cache hits
    - Configurable TTL per search type
    - Memory + disk hybrid caching
    - Statistics tracking
    """
    
    # Default TTL for different search types
    DEFAULT_TTL = {
        "web": timedelta(hours=1),
        "news": timedelta(minutes=30),  # News changes faster
        "image": timedelta(hours=2),
        "academic": timedelta(days=7),  # Academic content is more stable
    }
    
    def __init__(
        self,
        cache_dir: Optional[str] = None,
        memory_cache_size: int = 100,
        enable_disk_cache: bool = True,
    ):
        """
        Initialize search cache
        
        Args:
            cache_dir: Directory for disk cache
            memory_cache_size: Maximum entries in memory cache
            enable_disk_cache: Whether to use disk caching
        """
        self._memory_cache: Dict[str, CacheEntry] = {}
        self._memory_cache_size = memory_cache_size
        self._enable_disk_cache = enable_disk_cache
        
        # Set up cache directory
        if cache_dir:
            self._cache_dir = Path(cache_dir)
        else:
            self._cache_dir = Path.home() / ".cell0" / "search_cache"
        
        if self._enable_disk_cache:
            self._cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Statistics
        self._stats = {
            "hits": 0,
            "misses": 0,
            "evictions": 0,
            "disk_writes": 0,
            "disk_reads": 0,
        }
        
        self._lock = asyncio.Lock()
    
    def _normalize_query(self, query: str, search_type: str, provider: str) -> str:
        """
        Normalize query for cache key generation
        
        Normalization includes:
        - Lowercasing
        - Whitespace normalization
        - Removal of extra spaces
        """
        # Normalize whitespace and lowercase
        normalized = " ".join(query.lower().split())
        # Create cache key
        key_data = f"{normalized}:{search_type}:{provider}"
        return hashlib.sha256(key_data.encode()).hexdigest()[:32]
    
    def _get_cache_file(self, cache_key: str) -> Path:
        """Get cache file path for a key"""
        # Use first 2 chars as subdirectory to avoid too many files in one dir
        subdir = cache_key[:2]
        return self._cache_dir / subdir / f"{cache_key}.json"
    
    async def get(
        self,
        query: str,
        search_type: str = "web",
        provider: str = "any",
        max_age: Optional[timedelta] = None,
    ) -> Optional[CacheEntry]:
        """
        Get cached results for a query
        
        Args:
            query: Search query
            search_type: Type of search (web, news, image, academic)
            provider: Provider name or "any"
            max_age: Maximum age for results
            
        Returns:
            Cache entry if found and fresh, None otherwise
        """
        async with self._lock:
            cache_key = self._normalize_query(query, search_type, provider)
            
            # Try memory cache first
            entry = self._memory_cache.get(cache_key)
            
            # If not in memory, try disk
            if entry is None and self._enable_disk_cache:
                entry = await self._load_from_disk(cache_key)
                if entry:
                    # Promote to memory cache if there's room
                    if len(self._memory_cache) < self._memory_cache_size:
                        self._memory_cache[cache_key] = entry
            
            if entry:
                if entry.is_fresh(max_age):
                    entry.hit_count += 1
                    self._stats["hits"] += 1
                    logger.debug(f"Cache hit for query: {query[:50]}...")
                    return entry
                else:
                    # Expired entry - remove it
                    await self._remove_entry(cache_key)
            
            self._stats["misses"] += 1
            logger.debug(f"Cache miss for query: {query[:50]}...")
            return None
    
    async def set(
        self,
        query: str,
        search_type: str,
        provider: str,
        results: List[Dict[str, Any]],
        ttl: Optional[timedelta] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> CacheEntry:
        """
        Cache search results
        
        Args:
            query: Search query
            search_type: Type of search
            provider: Provider that returned results
            results: Search results to cache
            ttl: Time to live (uses default if not specified)
            metadata: Additional metadata
            
        Returns:
            Created cache entry
        """
        async with self._lock:
            cache_key = self._normalize_query(query, search_type, provider)
            
            # Determine TTL
            if ttl is None:
                ttl = self.DEFAULT_TTL.get(search_type, self.DEFAULT_TTL["web"])
            
            now = datetime.now()
            entry = CacheEntry(
                query=query,
                search_type=search_type,
                provider=provider,
                results=results,
                timestamp=now,
                expires_at=now + ttl,
                metadata=metadata or {},
            )
            
            # Evict oldest if memory cache is full
            if len(self._memory_cache) >= self._memory_cache_size:
                await self._evict_oldest()
            
            # Store in memory
            self._memory_cache[cache_key] = entry
            
            # Store on disk if enabled
            if self._enable_disk_cache:
                await self._save_to_disk(cache_key, entry)
            
            logger.debug(f"Cached results for query: {query[:50]}...")
            return entry
    
    async def invalidate(
        self,
        query: Optional[str] = None,
        search_type: Optional[str] = None,
        provider: Optional[str] = None,
    ) -> int:
        """
        Invalidate cached entries
        
        Args:
            query: Specific query to invalidate (or None for all)
            search_type: Filter by search type
            provider: Filter by provider
            
        Returns:
            Number of entries invalidated
        """
        async with self._lock:
            count = 0
            
            if query:
                # Invalidate specific query
                cache_key = self._normalize_query(query, search_type or "web", provider or "any")
                if cache_key in self._memory_cache:
                    await self._remove_entry(cache_key)
                    count += 1
            else:
                # Invalidate by filters
                keys_to_remove = []
                for key, entry in self._memory_cache.items():
                    match = True
                    if search_type and entry.search_type != search_type:
                        match = False
                    if provider and entry.provider != provider:
                        match = False
                    if match:
                        keys_to_remove.append(key)
                
                for key in keys_to_remove:
                    await self._remove_entry(key)
                    count += 1
            
            logger.info(f"Invalidated {count} cache entries")
            return count
    
    async def _evict_oldest(self):
        """Evict oldest entry from memory cache"""
        if not self._memory_cache:
            return
        
        # Find oldest by timestamp
        oldest_key = min(
            self._memory_cache.keys(),
            key=lambda k: self._memory_cache[k].timestamp
        )
        
        del self._memory_cache[oldest_key]
        self._stats["evictions"] += 1
        logger.debug(f"Evicted cache entry: {oldest_key}")
    
    async def _remove_entry(self, cache_key: str):
        """Remove entry from both memory and disk"""
        # Remove from memory
        if cache_key in self._memory_cache:
            del self._memory_cache[cache_key]
        
        # Remove from disk
        if self._enable_disk_cache:
            cache_file = self._get_cache_file(cache_key)
            if cache_file.exists():
                cache_file.unlink()
    
    async def _save_to_disk(self, cache_key: str, entry: CacheEntry):
        """Save entry to disk cache"""
        try:
            cache_file = self._get_cache_file(cache_key)
            cache_file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(cache_file, "w") as f:
                json.dump(entry.to_dict(), f, indent=2)
            
            self._stats["disk_writes"] += 1
        except Exception as e:
            logger.warning(f"Failed to save cache to disk: {e}")
    
    async def _load_from_disk(self, cache_key: str) -> Optional[CacheEntry]:
        """Load entry from disk cache"""
        try:
            cache_file = self._get_cache_file(cache_key)
            if not cache_file.exists():
                return None
            
            with open(cache_file, "r") as f:
                data = json.load(f)
            
            entry = CacheEntry.from_dict(data)
            self._stats["disk_reads"] += 1
            return entry
        except Exception as e:
            logger.warning(f"Failed to load cache from disk: {e}")
            return None
    
    async def clear_expired(self) -> int:
        """Clear all expired entries from cache"""
        async with self._lock:
            count = 0
            expired_keys = [
                key for key, entry in self._memory_cache.items()
                if entry.is_expired()
            ]
            
            for key in expired_keys:
                await self._remove_entry(key)
                count += 1
            
            logger.info(f"Cleared {count} expired cache entries")
            return count
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        total_requests = self._stats["hits"] + self._stats["misses"]
        hit_rate = self._stats["hits"] / total_requests if total_requests > 0 else 0
        
        return {
            "memory_entries": len(self._memory_cache),
            "hits": self._stats["hits"],
            "misses": self._stats["misses"],
            "hit_rate": hit_rate,
            "evictions": self._stats["evictions"],
            "disk_writes": self._stats["disk_writes"],
            "disk_reads": self._stats["disk_reads"],
        }
    
    async def clear_all(self):
        """Clear all cache entries"""
        async with self._lock:
            self._memory_cache.clear()
            
            if self._enable_disk_cache and self._cache_dir.exists():
                for cache_file in self._cache_dir.rglob("*.json"):
                    cache_file.unlink()
            
            logger.info("Cleared all cache entries")


# Global cache instance
_global_cache: Optional[SearchCache] = None


def get_cache() -> SearchCache:
    """Get global cache instance"""
    global _global_cache
    if _global_cache is None:
        _global_cache = SearchCache()
    return _global_cache


def set_cache(cache: SearchCache):
    """Set global cache instance"""
    global _global_cache
    _global_cache = cache
