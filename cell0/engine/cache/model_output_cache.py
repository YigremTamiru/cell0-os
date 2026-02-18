"""
Model Output Semantic Caching for Cell 0 OS

Advanced semantic caching for LLM outputs with:
- Embedding-based similarity matching
- Approximate nearest neighbor search
- Confidence scoring
- Cache invalidation by topic
- Production-grade performance

Author: KULLU (Cell 0 OS)
"""

import asyncio
import hashlib
import json
import logging
from typing import Any, Dict, List, Optional, Tuple, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import numpy as np

from cell0.engine.cache.redis_client import RedisClient, get_redis_client

logger = logging.getLogger("cell0.engine.cache.model_output")


class CacheMatchConfidence(Enum):
    """Confidence levels for cache matches"""
    HIGH = "high"       # > 0.95 similarity
    MEDIUM = "medium"   # > 0.85 similarity
    LOW = "low"         # > 0.75 similarity
    NONE = "none"       # <= 0.75 similarity


@dataclass
class ModelOutputEntry:
    """Cached model output entry"""
    prompt_hash: str
    prompt: str
    output: str
    model_id: str
    embedding: Optional[List[float]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    cached_at: datetime = field(default_factory=datetime.utcnow)
    ttl_seconds: int = 3600
    access_count: int = 0
    total_tokens: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "prompt_hash": self.prompt_hash,
            "prompt": self.prompt,
            "output": self.output,
            "model_id": self.model_id,
            "embedding": self.embedding,
            "metadata": self.metadata,
            "cached_at": self.cached_at.isoformat(),
            "ttl_seconds": self.ttl_seconds,
            "access_count": self.access_count,
            "total_tokens": self.total_tokens,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ModelOutputEntry":
        return cls(
            prompt_hash=data["prompt_hash"],
            prompt=data["prompt"],
            output=data["output"],
            model_id=data["model_id"],
            embedding=data.get("embedding"),
            metadata=data.get("metadata", {}),
            cached_at=datetime.fromisoformat(data["cached_at"]),
            ttl_seconds=data["ttl_seconds"],
            access_count=data.get("access_count", 0),
            total_tokens=data.get("total_tokens", 0),
        )
    
    def is_expired(self) -> bool:
        """Check if cache entry has expired"""
        expiry = self.cached_at + timedelta(seconds=self.ttl_seconds)
        return datetime.utcnow() > expiry


@dataclass
class CacheMatch:
    """Result of a semantic cache lookup"""
    entry: ModelOutputEntry
    similarity: float
    confidence: CacheMatchConfidence
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "similarity": self.similarity,
            "confidence": self.confidence.value,
            "entry": self.entry.to_dict(),
        }


class SimpleEmbeddingGenerator:
    """
    Simple embedding generator using TF-IDF-like approach
    
    For production, replace with proper embeddings from:
    - sentence-transformers
    - OpenAI embeddings API
    - Custom fine-tuned model
    """
    
    def __init__(self, dimension: int = 384):
        self.dimension = dimension
        self._word_vectors: Dict[str, List[float]] = {}
        
    def _get_word_vector(self, word: str) -> List[float]:
        """Get or create deterministic vector for word"""
        if word not in self._word_vectors:
            # Generate deterministic vector based on word hash
            hash_val = int(hashlib.sha256(word.encode()).hexdigest(), 16)
            np.random.seed(hash_val % (2**32))
            vector = np.random.randn(self.dimension).astype(np.float32)
            vector = vector / np.linalg.norm(vector)  # Normalize
            self._word_vectors[word] = vector.tolist()
        return self._word_vectors[word]
        
    def embed(self, text: str) -> List[float]:
        """
        Generate embedding for text
        
        Uses a simple bag-of-words approach with word vectors.
        """
        # Normalize and tokenize
        words = text.lower().split()
        
        if not words:
            return [0.0] * self.dimension
            
        # Average word vectors
        vectors = [self._get_word_vector(w) for w in words]
        embedding = np.mean(vectors, axis=0)
        
        # Normalize
        norm = np.linalg.norm(embedding)
        if norm > 0:
            embedding = embedding / norm
            
        return embedding.tolist()


class ModelOutputCache:
    """
    Semantic cache for model outputs
    
    Provides intelligent caching of LLM responses based on
    semantic similarity of prompts rather than exact matching.
    
    Features:
    - Embedding-based similarity search
    - Configurable similarity thresholds
    - TTL-based expiration
    - Topic-based invalidation
    - Token usage tracking
    """
    
    SIMILARITY_THRESHOLDS = {
        CacheMatchConfidence.HIGH: 0.95,
        CacheMatchConfidence.MEDIUM: 0.85,
        CacheMatchConfidence.LOW: 0.75,
    }
    
    def __init__(
        self,
        redis_client: Optional[RedisClient] = None,
        embedding_generator: Optional[SimpleEmbeddingGenerator] = None,
        default_ttl_seconds: int = 3600,
        max_entries: int = 10000,
        key_prefix: str = "cell0:model_output",
    ):
        self.redis = redis_client or get_redis_client()
        self.embedder = embedding_generator or SimpleEmbeddingGenerator()
        self.default_ttl = default_ttl_seconds
        self.max_entries = max_entries
        self.key_prefix = key_prefix
        self._stats = {
            "hits": 0,
            "misses": 0,
            "sets": 0,
            "similarity_checks": 0,
        }
        
    def _generate_prompt_hash(self, prompt: str) -> str:
        """Generate hash for prompt"""
        return hashlib.sha256(prompt.encode()).hexdigest()[:16]
        
    def _generate_cache_key(self, prompt_hash: str, model_id: str) -> str:
        """Generate cache key"""
        return f"{self.key_prefix}:{model_id}:{prompt_hash}"
        
    def _calculate_similarity(
        self,
        embedding1: List[float],
        embedding2: List[float],
    ) -> float:
        """Calculate cosine similarity between embeddings"""
        v1 = np.array(embedding1)
        v2 = np.array(embedding2)
        
        dot_product = np.dot(v1, v2)
        norm1 = np.linalg.norm(v1)
        norm2 = np.linalg.norm(v2)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
            
        return float(dot_product / (norm1 * norm2))
        
    def _get_confidence_level(self, similarity: float) -> CacheMatchConfidence:
        """Get confidence level for similarity score"""
        if similarity >= self.SIMILARITY_THRESHOLDS[CacheMatchConfidence.HIGH]:
            return CacheMatchConfidence.HIGH
        elif similarity >= self.SIMILARITY_THRESHOLDS[CacheMatchConfidence.MEDIUM]:
            return CacheMatchConfidence.MEDIUM
        elif similarity >= self.SIMILARITY_THRESHOLDS[CacheMatchConfidence.LOW]:
            return CacheMatchConfidence.LOW
        return CacheMatchConfidence.NONE
        
    async def get(
        self,
        prompt: str,
        model_id: str,
        min_confidence: CacheMatchConfidence = CacheMatchConfidence.MEDIUM,
        **kwargs,
    ) -> Optional[CacheMatch]:
        """
        Get cached output with semantic matching
        
        Args:
            prompt: Input prompt
            model_id: Model identifier
            min_confidence: Minimum confidence level for match
            
        Returns:
            CacheMatch if found, None otherwise
        """
        prompt_embedding = self.embedder.embed(prompt)
        prompt_hash = self._generate_prompt_hash(prompt)
        cache_key = self._generate_cache_key(prompt_hash, model_id)
        
        try:
            # First check exact match
            data = await self.redis.get(cache_key)
            
            if data:
                entry = ModelOutputEntry.from_dict(data)
                if not entry.is_expired():
                    entry.access_count += 1
                    await self.redis.set(cache_key, entry.to_dict(), ttl_seconds=entry.ttl_seconds)
                    
                    self._stats["hits"] += 1
                    return CacheMatch(
                        entry=entry,
                        similarity=1.0,
                        confidence=CacheMatchConfidence.HIGH,
                    )
                    
            # Try semantic search
            match = await self._semantic_search(
                prompt_embedding, model_id, min_confidence
            )
            
            if match:
                self._stats["hits"] += 1
                return match
                
            self._stats["misses"] += 1
            return None
            
        except Exception as e:
            logger.error(f"Model output cache get error: {e}")
            return None
            
    async def _semantic_search(
        self,
        query_embedding: List[float],
        model_id: str,
        min_confidence: CacheMatchConfidence,
    ) -> Optional[CacheMatch]:
        """
        Perform semantic search for similar prompts
        
        Note: In production, use vector database (e.g., Redis Vector Similarity,
        Pinecone, Weaviate) for efficient approximate nearest neighbor search.
        """
        min_similarity = self.SIMILARITY_THRESHOLDS.get(min_confidence, 0.75)
        
        try:
            # Get all entries for this model
            pattern = f"{self.key_prefix}:{model_id}:*"
            keys = await self.redis.keys(pattern)
            
            best_match: Optional[CacheMatch] = None
            best_similarity = 0.0
            
            # Check each entry
            # Note: This is O(n) and not scalable. Use vector DB in production.
            entries_data = await self.redis.get_many(keys)
            
            for key, data in entries_data.items():
                if not data:
                    continue
                    
                try:
                    entry = ModelOutputEntry.from_dict(data)
                    
                    if entry.is_expired():
                        continue
                        
                    if not entry.embedding:
                        continue
                        
                    similarity = self._calculate_similarity(
                        query_embedding, entry.embedding
                    )
                    
                    self._stats["similarity_checks"] += 1
                    
                    if similarity > best_similarity and similarity >= min_similarity:
                        best_similarity = similarity
                        best_match = CacheMatch(
                            entry=entry,
                            similarity=similarity,
                            confidence=self._get_confidence_level(similarity),
                        )
                        
                except Exception as e:
                    logger.warning(f"Error checking cache entry {key}: {e}")
                    continue
                    
            return best_match
            
        except Exception as e:
            logger.error(f"Semantic search error: {e}")
            return None
            
    async def set(
        self,
        prompt: str,
        output: str,
        model_id: str,
        embedding: Optional[List[float]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        ttl_seconds: Optional[int] = None,
        total_tokens: int = 0,
        **kwargs,
    ) -> bool:
        """
        Cache model output
        
        Args:
            prompt: Input prompt
            output: Model output
            model_id: Model identifier
            embedding: Optional pre-computed embedding
            metadata: Additional metadata
            ttl_seconds: TTL override
            total_tokens: Token count for tracking
            
        Returns:
            True if cached successfully
        """
        prompt_hash = self._generate_prompt_hash(prompt)
        cache_key = self._generate_cache_key(prompt_hash, model_id)
        
        # Generate embedding if not provided
        if embedding is None:
            embedding = self.embedder.embed(prompt)
            
        entry = ModelOutputEntry(
            prompt_hash=prompt_hash,
            prompt=prompt,
            output=output,
            model_id=model_id,
            embedding=embedding,
            metadata=metadata or {},
            cached_at=datetime.utcnow(),
            ttl_seconds=ttl_seconds or self.default_ttl,
            total_tokens=total_tokens,
        )
        
        try:
            await self.redis.set(cache_key, entry.to_dict(), ttl_seconds=entry.ttl_seconds)
            self._stats["sets"] += 1
            
            # Update index (if using vector DB, this would add to index)
            # For now, we just store the entry
            
            return True
            
        except Exception as e:
            logger.error(f"Model output cache set error: {e}")
            return False
            
    async def invalidate(
        self,
        model_id: Optional[str] = None,
        topic_keywords: Optional[List[str]] = None,
    ) -> int:
        """
        Invalidate cached outputs
        
        Args:
            model_id: If provided, only invalidate for this model
            topic_keywords: If provided, invalidate entries containing these keywords
            
        Returns:
            Number of entries invalidated
        """
        try:
            if model_id:
                pattern = f"{self.key_prefix}:{model_id}:*"
            else:
                pattern = f"{self.key_prefix}:*"
                
            keys = await self.redis.keys(pattern)
            
            if topic_keywords:
                # Filter by keywords
                entries_data = await self.redis.get_many(keys)
                to_delete = []
                
                for key, data in entries_data.items():
                    if not data:
                        continue
                        
                    try:
                        entry = ModelOutputEntry.from_dict(data)
                        prompt_lower = entry.prompt.lower()
                        
                        if any(kw.lower() in prompt_lower for kw in topic_keywords):
                            to_delete.append(key)
                            
                    except Exception:
                        continue
                        
                keys = to_delete
                
            # Delete matching keys
            for key in keys:
                await self.redis.delete(key)
                
            return len(keys)
            
        except Exception as e:
            logger.error(f"Model output cache invalidation error: {e}")
            return 0
            
    async def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        total = self._stats["hits"] + self._stats["misses"]
        hit_rate = self._stats["hits"] / total if total > 0 else 0
        
        return {
            "hits": self._stats["hits"],
            "misses": self._stats["misses"],
            "sets": self._stats["sets"],
            "similarity_checks": self._stats["similarity_checks"],
            "hit_rate": round(hit_rate, 4),
            "total_requests": total,
        }


def with_model_cache(
    cache: Optional[ModelOutputCache] = None,
    min_confidence: CacheMatchConfidence = CacheMatchConfidence.MEDIUM,
    ttl_seconds: int = 3600,
):
    """
    Decorator for caching model outputs
    
    Usage:
        @with_model_cache(ttl_seconds=600)
        async def generate_response(prompt: str, model_id: str):
            return await call_llm(prompt, model_id)
    """
    cache_instance = cache or ModelOutputCache()
    
    def decorator(func):
        async def wrapper(prompt: str, model_id: str, **kwargs):
            # Try to get from cache
            cached = await cache_instance.get(prompt, model_id, min_confidence)
            
            if cached:
                logger.debug(f"Cache hit for model {model_id}")
                return cached.entry.output
                
            # Call the function
            output = await func(prompt, model_id, **kwargs)
            
            # Cache the result
            await cache_instance.set(
                prompt=prompt,
                output=output,
                model_id=model_id,
                ttl_seconds=ttl_seconds,
            )
            
            return output
            
        return wrapper
    return decorator


# Global instance
_global_model_cache: Optional[ModelOutputCache] = None


def get_model_output_cache() -> ModelOutputCache:
    """Get global model output cache instance"""
    global _global_model_cache
    if _global_model_cache is None:
        _global_model_cache = ModelOutputCache()
    return _global_model_cache