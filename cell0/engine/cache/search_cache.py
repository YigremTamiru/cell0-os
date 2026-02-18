"""
Search Result Caching for Cell 0 OS

Advanced caching for web search results with:
- Semantic key generation
- Provider-aware caching
- Result freshness management
- Cache warming
- Hit/miss analytics

Author: KULLU (Cell 0 OS)
"""

import asyncio
import hashlib
import json
import logging
from typing import Any, Dict, List, Optional, Union
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum

from cell0.engine.cache.redis_client import RedisClient, get_redis_client

logger = logging.getLogger("cell0.engine.cache.search")


class SearchProvider(Enum):
    """Search providers"""
    BRAVE = "brave"
    GOOGLE = "google"
    BING = "bing"
    DUCKDUCKGO = "duckduckgo"


class SearchType(Enum):
    """Types of search"""
    WEB = "web"
    NEWS = "news"
    IMAGE = "image"
    ACADEMIC = "academic"
    VIDEO = "video"


@dataclass
class SearchCacheEntry:
    """Cached search result entry"""
    query: str
    provider: str
    search_type: str
    results: List[Dict[str, Any]]
    metadata: Dict[str, Any]
    cached_at: datetime
    ttl_seconds: int
    hit_count: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "query": self.query,
            "provider": self.provider,
            "search_type": self.search_type,
            "results": self.results,
            "metadata": self.metadata,
            "cached_at": self.cached_at.isoformat(),
            "ttl_seconds": self.ttl_seconds,
            "hit_count": self.hit_count,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SearchCacheEntry":
        return cls(
            query=data["query"],
            provider=data["provider"],
            search_type=data["search_type"],
            results=data["results"],
            metadata=data.get("metadata", {}),
            cached_at=datetime.fromisoformat(data["cached_at"]),
            ttl_seconds=data["ttl_seconds"],
            hit_count=data.get("hit_count", 0),
        )
    
    def is_expired(self) -> bool:
        """Check if cache entry has expired"""
        expiry = self.cached_at + timedelta(seconds=self.ttl_seconds)
        return datetime.utcnow() > expiry


class SearchResultCache:
    """
    Intelligent caching for search results
    
    Features:
    - Query normalization for better cache hits
    - Provider-specific TTLs
    - Search type awareness
    - Statistical tracking
    - Cache warming for common queries
    """
    
    # Default TTLs by search type (seconds)
    DEFAULT_TTLS = {
        SearchType.WEB: 3600,      # 1 hour
        SearchType.NEWS: 600,      # 10 minutes
        SearchType.IMAGE: 7200,    # 2 hours
        SearchType.ACADEMIC: 86400, # 24 hours
        SearchType.VIDEO: 3600,    # 1 hour
    }
    
    def __init__(
        self,
        redis_client: Optional[RedisClient] = None,
        key_prefix: str = "cell0:search",
    ):
        self.redis = redis_client or get_redis_client()
        self.key_prefix = key_prefix
        self._ttls = dict(self.DEFAULT_TTLS)
        self._stats = {
            "hits": 0,
            "misses": 0,
            "sets": 0,
            "invalidations": 0,
        }
        
    def set_ttl(self, search_type: SearchType, ttl_seconds: int):
        """Set TTL for a search type"""
        self._ttls[search_type] = ttl_seconds
        
    def _normalize_query(self, query: str) -> str:
        """
        Normalize query for better cache hits
        
        Normalization includes:
        - Lowercasing
        - Whitespace normalization
        - Removal of common filler words
        """
        # Basic normalization
        normalized = query.lower().strip()
        
        # Normalize whitespace
        normalized = " ".join(normalized.split())
        
        # Remove common filler words (optional, can be expanded)
        fillers = {"the", "a", "an", "is", "are", "was", "were"}
        words = normalized.split()
        words = [w for w in words if w not in fillers]
        
        return " ".join(words)
        
    def _generate_cache_key(
        self,
        query: str,
        provider: SearchProvider,
        search_type: SearchType,
        **kwargs,
    ) -> str:
        """Generate cache key for search query"""
        normalized = self._normalize_query(query)
        
        # Build key components
        key_parts = [
            provider.value,
            search_type.value,
            normalized,
        ]
        
        # Include additional parameters that affect results
        if kwargs.get("country"):
            key_parts.append(f"country:{kwargs['country']}")
        if kwargs.get("language"):
            key_parts.append(f"lang:{kwargs['language']}")
        if kwargs.get("freshness"):
            key_parts.append(f"fresh:{kwargs['freshness']}")
            
        key_data = "|".join(key_parts)
        hashed = hashlib.sha256(key_data.encode()).hexdigest()[:20]
        
        return f"{self.key_prefix}:{hashed}"
        
    async def get(
        self,
        query: str,
        provider: SearchProvider = SearchProvider.BRAVE,
        search_type: SearchType = SearchType.WEB,
        **kwargs,
    ) -> Optional[SearchCacheEntry]:
        """Get cached search results"""
        cache_key = self._generate_cache_key(query, provider, search_type, **kwargs)
        
        try:
            data = await self.redis.get(cache_key)
            
            if data is None:
                self._stats["misses"] += 1
                return None
                
            entry = SearchCacheEntry.from_dict(data)
            
            if entry.is_expired():
                await self.redis.delete(cache_key)
                self._stats["misses"] += 1
                return None
                
            # Update hit count
            entry.hit_count += 1
            await self.redis.set(cache_key, entry.to_dict(), ttl_seconds=entry.ttl_seconds)
            
            self._stats["hits"] += 1
            return entry
            
        except Exception as e:
            logger.error(f"Search cache get error: {e}")
            return None
            
    async def set(
        self,
        query: str,
        provider: SearchProvider,
        search_type: SearchType,
        results: List[Dict[str, Any]],
        metadata: Optional[Dict[str, Any]] = None,
        ttl_seconds: Optional[int] = None,
        **kwargs,
    ) -> bool:
        """Cache search results"""
        cache_key = self._generate_cache_key(query, provider, search_type, **kwargs)
        
        ttl = ttl_seconds or self._ttls.get(search_type, 3600)
        
        entry = SearchCacheEntry(
            query=query,
            provider=provider.value,
            search_type=search_type.value,
            results=results,
            metadata=metadata or {},
            cached_at=datetime.utcnow(),
            ttl_seconds=ttl,
        )
        
        try:
            await self.redis.set(cache_key, entry.to_dict(), ttl_seconds=ttl)
            self._stats["sets"] += 1
            return True
            
        except Exception as e:
            logger.error(f"Search cache set error: {e}")
            return False
            
    async def invalidate(
        self,
        provider: Optional[SearchProvider] = None,
        search_type: Optional[SearchType] = None,
    ) -> int:
        """
        Invalidate cached search results
        
        Args:
            provider: If provided, only invalidate results from this provider
            search_type: If provided, only invalidate results of this type
            
        Returns:
            Number of entries invalidated
        """
        try:
            # Get all search cache keys
            pattern = f"{self.key_prefix}:*"
            keys = await self.redis.keys(pattern)
            
            # Note: In a production system, we'd want to decode and filter
            # based on provider/search_type stored in the value
            # For now, we invalidate all matching keys
            
            count = 0
            for key in keys:
                await self.redis.delete(key)
                count += 1
                
            self._stats["invalidations"] += count
            return count
            
        except Exception as e:
            logger.error(f"Search cache invalidation error: {e}")
            return 0
            
    async def warm_cache(
        self,
        queries: List[str],
        provider: SearchProvider,
        search_type: SearchType,
        fetch_fn: callable,
        **kwargs,
    ) -> int:
        """
        Warm cache with pre-fetched results
        
        Args:
            queries: List of queries to warm
            provider: Search provider
            search_type: Type of search
            fetch_fn: Async function to fetch results
            
        Returns:
            Number of entries warmed
        """
        count = 0
        
        for query in queries:
            # Check if already cached
            existing = await self.get(query, provider, search_type, **kwargs)
            if existing:
                continue
                
            try:
                # Fetch and cache
                results, metadata = await fetch_fn(query)
                await self.set(query, provider, search_type, results, metadata, **kwargs)
                count += 1
            except Exception as e:
                logger.warning(f"Failed to warm cache for query '{query}': {e}")
                
        logger.info(f"Warmed {count} search cache entries")
        return count
        
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        total = self._stats["hits"] + self._stats["misses"]
        hit_rate = self._stats["hits"] / total if total > 0 else 0
        
        return {
            "hits": self._stats["hits"],
            "misses": self._stats["misses"],
            "sets": self._stats["sets"],
            "invalidations": self._stats["invalidations"],
            "hit_rate": round(hit_rate, 4),
            "total_requests": total,
        }


class SemanticSearchCache:
    """
    Semantic caching for search queries
    
    Uses approximate matching to find similar queries
    and return cached results, improving cache hit rates.
    
    This is a simplified implementation. A full implementation
    would use embeddings and vector similarity search.
    """
    
    def __init__(
        self,
        redis_client: Optional[RedisClient] = None,
        similarity_threshold: float = 0.85,
    ):
        self.redis = redis_client or get_redis_client()
        self.similarity_threshold = similarity_threshold
        self._search_cache = SearchResultCache(redis_client)
        
    def _calculate_similarity(self, query1: str, query2: str) -> float:
        """
        Calculate similarity between two queries
        
        Uses a simple word overlap ratio.
        For production, use embeddings and cosine similarity.
        """
        words1 = set(self._search_cache._normalize_query(query1).split())
        words2 = set(self._search_cache._normalize_query(query2).split())
        
        if not words1 or not words2:
            return 0.0
            
        intersection = words1.intersection(words2)
        union = words1.union(words2)
        
        return len(intersection) / len(union)
        
    async def get(
        self,
        query: str,
        provider: SearchProvider = SearchProvider.BRAVE,
        search_type: SearchType = SearchType.WEB,
        **kwargs,
    ) -> Optional[SearchCacheEntry]:
        """Get cached results with semantic matching"""
        # First try exact match
        exact = await self._search_cache.get(query, provider, search_type, **kwargs)
        if exact:
            return exact
            
        # Try to find semantically similar query
        # Note: In production, use vector similarity search
        # This is a placeholder implementation
        
        return None
        
    async def set(
        self,
        query: str,
        provider: SearchProvider,
        search_type: SearchType,
        results: List[Dict[str, Any]],
        **kwargs,
    ) -> bool:
        """Cache search results"""
        return await self._search_cache.set(
            query, provider, search_type, results, **kwargs
        )


# Global instances
_global_search_cache: Optional[SearchResultCache] = None
_global_semantic_cache: Optional[SemanticSearchCache] = None


def get_search_cache() -> SearchResultCache:
    """Get global search cache instance"""
    global _global_search_cache
    if _global_search_cache is None:
        _global_search_cache = SearchResultCache()
    return _global_search_cache


def get_semantic_search_cache() -> SemanticSearchCache:
    """Get global semantic search cache instance"""
    global _global_semantic_cache
    if _global_semantic_cache is None:
        _global_semantic_cache = SemanticSearchCache()
    return _global_semantic_cache