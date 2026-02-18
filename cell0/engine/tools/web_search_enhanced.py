"""
Enhanced Web Search Tool for Cell 0 OS

Advanced web search with:
- Multiple provider support (Brave, Google, Bing)
- Intelligent failover
- Result caching
- Ranking and filtering
- News, image, and academic search

Author: KULLU (Cell 0 OS)
"""

import os
import json
import asyncio
from typing import Dict, Any, Optional, List, Union
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import logging

from cell0.engine.search.cache import SearchCache, get_cache
from cell0.engine.search.providers import (
    SearchProvider,
    BraveSearchProvider,
    GoogleSearchProvider,
    BingSearchProvider,
    SearchResult,
    NewsResult,
    ImageResult,
    AcademicResult,
)
from cell0.engine.search.ranker import (
    ResultRanker,
    ResultFilter,
    ResultAggregator,
)

logger = logging.getLogger("cell0.tools.web_search_enhanced")


class SearchType(str, Enum):
    """Types of search"""
    WEB = "web"
    NEWS = "news"
    IMAGE = "image"
    ACADEMIC = "academic"


@dataclass
class SearchRequest:
    """Enhanced search request"""
    query: str
    search_type: SearchType = SearchType.WEB
    num_results: int = 10
    providers: Optional[List[str]] = None  # None = use defaults
    use_cache: bool = True
    enable_ranking: bool = True
    enable_filtering: bool = True
    freshness: Optional[str] = None  # pd, pw, pm, py
    country: Optional[str] = None
    language: Optional[str] = None
    since: Optional[datetime] = None
    until: Optional[datetime] = None
    exclude_domains: Optional[List[str]] = None
    include_domains: Optional[List[str]] = None
    min_content_length: int = 0
    max_content_length: Optional[int] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "query": self.query,
            "search_type": self.search_type.value,
            "num_results": self.num_results,
            "providers": self.providers,
            "use_cache": self.use_cache,
            "enable_ranking": self.enable_ranking,
            "enable_filtering": self.enable_filtering,
            "freshness": self.freshness,
            "country": self.country,
            "language": self.language,
            "since": self.since.isoformat() if self.since else None,
            "until": self.until.isoformat() if self.until else None,
            "exclude_domains": self.exclude_domains,
            "include_domains": self.include_domains,
            "min_content_length": self.min_content_length,
            "max_content_length": self.max_content_length,
        }


@dataclass
class SearchResponse:
    """Enhanced search response"""
    query: str
    search_type: SearchType
    results: List[Union[SearchResult, NewsResult, ImageResult, AcademicResult]]
    total_results: int
    providers_used: List[str]
    cached: bool
    execution_time_ms: float
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "query": self.query,
            "search_type": self.search_type.value,
            "results": [r.to_dict() for r in self.results],
            "total_results": self.total_results,
            "providers_used": self.providers_used,
            "cached": self.cached,
            "execution_time_ms": self.execution_time_ms,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata,
        }
    
    def to_json(self, indent: int = 2) -> str:
        """Convert to JSON string"""
        return json.dumps(self.to_dict(), indent=indent, default=str)


class EnhancedWebSearch:
    """
    Enhanced web search tool with multiple providers and intelligent features
    
    Features:
    - Multi-provider support (Brave, Google, Bing)
    - Automatic failover between providers
    - Result caching with TTL
    - Intelligent ranking
    - Duplicate removal
    - Domain filtering
    
    Usage:
        async with EnhancedWebSearch() as search:
            # Simple web search
            response = await search.search("python async")
            
            # Advanced search with options
            request = SearchRequest(
                query="machine learning",
                search_type=SearchType.NEWS,
                num_results=20,
                freshness="pw",  # Past week
            )
            response = await search.search_with_request(request)
            
            # Academic search
            results = await search.search_academic("neural networks", num_results=15)
    """
    
    # Default provider priority (failover order)
    DEFAULT_PROVIDERS = ["brave", "google", "bing"]
    
    def __init__(
        self,
        providers: Optional[List[str]] = None,
        cache: Optional[SearchCache] = None,
        enable_failover: bool = True,
        failover_timeout: float = 10.0,
        ranker: Optional[ResultRanker] = None,
    ):
        """
        Initialize enhanced web search
        
        Args:
            providers: List of provider names in priority order
            cache: Cache instance (uses global if not specified)
            enable_failover: Whether to enable provider failover
            failover_timeout: Timeout for failover attempts
            ranker: Custom result ranker
        """
        self.providers = providers or self.DEFAULT_PROVIDERS
        self.cache = cache or get_cache()
        self.enable_failover = enable_failover
        self.failover_timeout = failover_timeout
        self.ranker = ranker or ResultRanker()
        
        self._provider_instances: Dict[str, SearchProvider] = {}
        self._initialized = False
    
    async def __aenter__(self):
        """Async context manager entry"""
        await self.initialize()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.shutdown()
    
    async def initialize(self):
        """Initialize providers"""
        if self._initialized:
            return
        
        logger.info(f"Initializing EnhancedWebSearch with providers: {self.providers}")
        
        for provider_name in self.providers:
            try:
                provider = self._create_provider(provider_name)
                await provider.__aenter__()
                self._provider_instances[provider_name] = provider
                logger.info(f"Initialized provider: {provider_name}")
            except Exception as e:
                logger.warning(f"Failed to initialize provider {provider_name}: {e}")
        
        if not self._provider_instances:
            raise RuntimeError("No providers could be initialized")
        
        self._initialized = True
    
    async def shutdown(self):
        """Shutdown providers"""
        for name, provider in self._provider_instances.items():
            try:
                await provider.__aexit__(None, None, None)
                logger.info(f"Shutdown provider: {name}")
            except Exception as e:
                logger.warning(f"Error shutting down provider {name}: {e}")
        
        self._provider_instances.clear()
        self._initialized = False
    
    def _create_provider(self, name: str) -> SearchProvider:
        """Create a provider instance by name"""
        name = name.lower()
        
        if name == "brave":
            return BraveSearchProvider()
        elif name == "google":
            return GoogleSearchProvider()
        elif name == "bing":
            return BingSearchProvider()
        else:
            raise ValueError(f"Unknown provider: {name}")
    
    async def search(
        self,
        query: str,
        num_results: int = 10,
        **kwargs
    ) -> SearchResponse:
        """
        Perform a web search
        
        Args:
            query: Search query
            num_results: Number of results to return
            **kwargs: Additional search options
            
        Returns:
            SearchResponse with results
        """
        request = SearchRequest(
            query=query,
            search_type=SearchType.WEB,
            num_results=num_results,
            **kwargs
        )
        return await self.search_with_request(request)
    
    async def search_news(
        self,
        query: str,
        num_results: int = 10,
        **kwargs
    ) -> SearchResponse:
        """
        Perform a news search
        
        Args:
            query: Search query
            num_results: Number of results to return
            **kwargs: Additional search options
            
        Returns:
            SearchResponse with news results
        """
        request = SearchRequest(
            query=query,
            search_type=SearchType.NEWS,
            num_results=num_results,
            **kwargs
        )
        return await self.search_with_request(request)
    
    async def search_images(
        self,
        query: str,
        num_results: int = 10,
        **kwargs
    ) -> SearchResponse:
        """
        Perform an image search
        
        Args:
            query: Search query
            num_results: Number of results to return
            **kwargs: Additional search options
            
        Returns:
            SearchResponse with image results
        """
        request = SearchRequest(
            query=query,
            search_type=SearchType.IMAGE,
            num_results=num_results,
            **kwargs
        )
        return await self.search_with_request(request)
    
    async def search_academic(
        self,
        query: str,
        num_results: int = 10,
        **kwargs
    ) -> SearchResponse:
        """
        Perform an academic search
        
        Args:
            query: Search query
            num_results: Number of results to return
            **kwargs: Additional search options
            
        Returns:
            SearchResponse with academic results
        """
        request = SearchRequest(
            query=query,
            search_type=SearchType.ACADEMIC,
            num_results=num_results,
            **kwargs
        )
        return await self.search_with_request(request)
    
    async def search_with_request(self, request: SearchRequest) -> SearchResponse:
        """
        Perform search with a complete request object
        
        Args:
            request: SearchRequest with all options
            
        Returns:
            SearchResponse with results
        """
        import time
        start_time = time.time()
        
        # Check cache if enabled
        if request.use_cache:
            cached = await self._check_cache(request)
            if cached:
                execution_time = (time.time() - start_time) * 1000
                return SearchResponse(
                    query=request.query,
                    search_type=request.search_type,
                    results=cached.results,
                    total_results=len(cached.results),
                    providers_used=[cached.provider],
                    cached=True,
                    execution_time_ms=execution_time,
                    metadata={"cache_hit": True, "cache_timestamp": cached.timestamp.isoformat()},
                )
        
        # Determine which providers to use
        providers_to_try = request.providers or list(self._provider_instances.keys())
        
        # Execute search with failover
        all_results = []
        providers_used = []
        errors = []
        
        for provider_name in providers_to_try:
            if provider_name not in self._provider_instances:
                logger.warning(f"Provider {provider_name} not available, skipping")
                continue
            
            provider = self._provider_instances[provider_name]
            
            try:
                results = await asyncio.wait_for(
                    self._execute_provider_search(provider, request),
                    timeout=self.failover_timeout
                )
                
                if results:
                    all_results.extend(results)
                    providers_used.append(provider_name)
                    
                    # If we have enough results and failover is enabled, stop
                    if len(all_results) >= request.num_results and self.enable_failover:
                        break
                        
            except asyncio.TimeoutError:
                logger.warning(f"Provider {provider_name} timed out")
                errors.append(f"{provider_name}: timeout")
            except Exception as e:
                logger.warning(f"Provider {provider_name} failed: {e}")
                errors.append(f"{provider_name}: {str(e)}")
        
        # Apply filtering
        if request.enable_filtering:
            all_results = self._apply_filters(all_results, request)
        
        # Apply ranking
        if request.enable_ranking:
            ranked = self.ranker.rank(
                all_results,
                request.query,
                enable_diversity=True,
                enable_recency=request.search_type in [SearchType.NEWS, SearchType.WEB],
            )
            all_results = [r.result for r in ranked]
        
        # Limit results
        final_results = all_results[:request.num_results]
        
        # Cache results
        if request.use_cache and final_results and providers_used:
            await self._cache_results(request, final_results, providers_used[0])
        
        execution_time = (time.time() - start_time) * 1000
        
        return SearchResponse(
            query=request.query,
            search_type=request.search_type,
            results=final_results,
            total_results=len(final_results),
            providers_used=providers_used,
            cached=False,
            execution_time_ms=execution_time,
            metadata={
                "errors": errors if errors else None,
                "total_raw_results": len(all_results),
            },
        )
    
    async def _execute_provider_search(
        self,
        provider: SearchProvider,
        request: SearchRequest
    ) -> List[Any]:
        """Execute search on a specific provider"""
        search_kwargs = {
            "freshness": request.freshness,
            "country": request.country,
        }
        
        if request.language:
            search_kwargs["search_lang"] = request.language
        
        if request.search_type == SearchType.WEB:
            return await provider.search(
                request.query,
                num_results=request.num_results * 2,  # Get more for filtering
                **search_kwargs
            )
        elif request.search_type == SearchType.NEWS:
            return await provider.search_news(
                request.query,
                num_results=request.num_results * 2,
                **search_kwargs
            )
        elif request.search_type == SearchType.IMAGE:
            return await provider.search_images(
                request.query,
                num_results=request.num_results * 2,
            )
        elif request.search_type == SearchType.ACADEMIC:
            return await provider.search_academic(
                request.query,
                num_results=request.num_results * 2,
            )
        else:
            raise ValueError(f"Unknown search type: {request.search_type}")
    
    async def _check_cache(self, request: SearchRequest) -> Optional[Any]:
        """Check if results are cached"""
        try:
            entry = await self.cache.get(
                query=request.query,
                search_type=request.search_type.value,
                provider="any",
            )
            if entry and entry.results:
                # Convert cached dicts back to result objects
                return entry
            return None
        except Exception as e:
            logger.warning(f"Cache check failed: {e}")
            return None
    
    async def _cache_results(
        self,
        request: SearchRequest,
        results: List[Any],
        provider: str
    ):
        """Cache search results"""
        try:
            # Convert results to dicts for caching
            results_dict = [r.to_dict() if hasattr(r, 'to_dict') else r for r in results]
            
            await self.cache.set(
                query=request.query,
                search_type=request.search_type.value,
                provider=provider,
                results=results_dict,
                metadata={
                    "request": request.to_dict(),
                    "result_count": len(results),
                }
            )
        except Exception as e:
            logger.warning(f"Failed to cache results: {e}")
    
    def _apply_filters(
        self,
        results: List[Any],
        request: SearchRequest
    ) -> List[Any]:
        """Apply filters to results"""
        # Domain filtering
        if request.include_domains or request.exclude_domains:
            results = ResultFilter.filter_by_domain(
                results,
                include_domains=request.include_domains,
                exclude_domains=request.exclude_domains,
            )
        
        # Date filtering
        if request.since or request.until:
            results = ResultFilter.filter_by_date(
                results,
                since=request.since,
                until=request.until,
            )
        
        # Content length filtering
        if request.min_content_length > 0 or request.max_content_length:
            results = ResultFilter.filter_by_content_length(
                results,
                min_length=request.min_content_length,
                max_length=request.max_content_length,
            )
        
        # Remove duplicates
        results = ResultFilter.remove_duplicates(results)
        
        return results
    
    async def health_check(self) -> Dict[str, bool]:
        """Check health of all providers"""
        health = {}
        for name, provider in self._provider_instances.items():
            try:
                health[name] = await provider.health_check()
            except Exception as e:
                logger.warning(f"Health check failed for {name}: {e}")
                health[name] = False
        return health
    
    def get_provider_status(self) -> Dict[str, str]:
        """Get status of all configured providers"""
        status = {}
        for name in self.providers:
            if name in self._provider_instances:
                status[name] = "available"
            else:
                status[name] = "unavailable"
        return status


# Convenience functions for simple usage
async def web_search(query: str, num_results: int = 10, **kwargs) -> SearchResponse:
    """
    Simple web search function
    
    Usage:
        response = await web_search("python async")
        for result in response.results:
            print(result.title)
    """
    async with EnhancedWebSearch() as search:
        return await search.search(query, num_results, **kwargs)


async def news_search(query: str, num_results: int = 10, **kwargs) -> SearchResponse:
    """Simple news search function"""
    async with EnhancedWebSearch() as search:
        return await search.search_news(query, num_results, **kwargs)


async def image_search(query: str, num_results: int = 10, **kwargs) -> SearchResponse:
    """Simple image search function"""
    async with EnhancedWebSearch() as search:
        return await search.search_images(query, num_results, **kwargs)


async def academic_search(query: str, num_results: int = 10, **kwargs) -> SearchResponse:
    """Simple academic search function"""
    async with EnhancedWebSearch() as search:
        return await search.search_academic(query, num_results, **kwargs)
