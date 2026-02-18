"""
Cell 0 OS Search Module

Advanced web search with multiple providers, caching, and ranking.

Usage:
    from cell0.engine.search import EnhancedWebSearch
    
    async with EnhancedWebSearch() as search:
        results = await search.search("python async")
"""

from .cache import SearchCache, CacheEntry, get_cache, set_cache
from .providers import (
    SearchProvider,
    BraveSearchProvider,
    GoogleSearchProvider,
    BingSearchProvider,
    SearchResult,
    NewsResult,
    ImageResult,
    AcademicResult,
    get_provider,
    list_providers,
)
from .ranker import (
    ResultRanker,
    ResultFilter,
    ResultAggregator,
    RankedResult,
)

__all__ = [
    # Cache
    "SearchCache",
    "CacheEntry",
    "get_cache",
    "set_cache",
    # Providers
    "SearchProvider",
    "BraveSearchProvider",
    "GoogleSearchProvider",
    "BingSearchProvider",
    "SearchResult",
    "NewsResult",
    "ImageResult",
    "AcademicResult",
    "get_provider",
    "list_providers",
    # Ranker
    "ResultRanker",
    "ResultFilter",
    "ResultAggregator",
    "RankedResult",
]

__version__ = "1.0.0"
