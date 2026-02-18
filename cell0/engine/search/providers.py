"""
Search Provider Implementations for Cell 0 OS

Supports multiple search providers with failover:
- Brave Search (primary)
- Google Custom Search API (fallback)
- Bing Search API (fallback)
"""

import os
import json
import asyncio
import aiohttp
from typing import Dict, Any, Optional, List, Union
from dataclasses import dataclass
from abc import ABC, abstractmethod
from datetime import datetime
import logging

logger = logging.getLogger("cell0.search.providers")


@dataclass
class SearchResult:
    """Standardized search result"""
    title: str
    url: str
    snippet: str
    source: str  # Provider name
    rank: int
    timestamp: Optional[datetime] = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "title": self.title,
            "url": self.url,
            "snippet": self.snippet,
            "source": self.source,
            "rank": self.rank,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "metadata": self.metadata,
        }


@dataclass
class ImageResult:
    """Image search result"""
    title: str
    url: str  # Direct image URL
    source_url: str  # Page containing the image
    thumbnail_url: Optional[str] = None
    width: Optional[int] = None
    height: Optional[int] = None
    source: str = ""
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "title": self.title,
            "url": self.url,
            "source_url": self.source_url,
            "thumbnail_url": self.thumbnail_url,
            "width": self.width,
            "height": self.height,
            "source": self.source,
            "metadata": self.metadata,
        }


@dataclass
class NewsResult:
    """News search result"""
    title: str
    url: str
    snippet: str
    source: str  # News provider
    publisher: str  # News outlet name
    published_at: Optional[datetime] = None
    image_url: Optional[str] = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "title": self.title,
            "url": self.url,
            "snippet": self.snippet,
            "source": self.source,
            "publisher": self.publisher,
            "published_at": self.published_at.isoformat() if self.published_at else None,
            "image_url": self.image_url,
            "metadata": self.metadata,
        }


@dataclass
class AcademicResult:
    """Academic search result"""
    title: str
    url: str
    authors: List[str]
    abstract: Optional[str] = None
    publication: Optional[str] = None
    year: Optional[int] = None
    doi: Optional[str] = None
    citations: Optional[int] = None
    source: str = ""
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "title": self.title,
            "url": self.url,
            "authors": self.authors,
            "abstract": self.abstract,
            "publication": self.publication,
            "year": self.year,
            "doi": self.doi,
            "citations": self.citations,
            "source": self.source,
            "metadata": self.metadata,
        }


class SearchProvider(ABC):
    """Abstract base class for search providers"""
    
    name: str = "base"
    
    def __init__(self, api_key: Optional[str] = None, config: Optional[Dict] = None):
        self.api_key = api_key
        self.config = config or {}
        self._session: Optional[aiohttp.ClientSession] = None
        self._timeout = aiohttp.ClientTimeout(total=30)
    
    async def __aenter__(self):
        self._session = aiohttp.ClientSession(timeout=self._timeout)
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self._session:
            await self._session.close()
            self._session = None
    
    @abstractmethod
    async def search(
        self,
        query: str,
        num_results: int = 10,
        **kwargs
    ) -> List[SearchResult]:
        """Perform web search"""
        pass
    
    @abstractmethod
    async def search_news(
        self,
        query: str,
        num_results: int = 10,
        **kwargs
    ) -> List[NewsResult]:
        """Perform news search"""
        pass
    
    @abstractmethod
    async def search_images(
        self,
        query: str,
        num_results: int = 10,
        **kwargs
    ) -> List[ImageResult]:
        """Perform image search"""
        pass
    
    @abstractmethod
    async def search_academic(
        self,
        query: str,
        num_results: int = 10,
        **kwargs
    ) -> List[AcademicResult]:
        """Perform academic search"""
        pass
    
    async def health_check(self) -> bool:
        """Check if provider is available"""
        try:
            results = await self.search("test", num_results=1)
            return len(results) >= 0
        except Exception as e:
            logger.warning(f"{self.name} health check failed: {e}")
            return False


class BraveSearchProvider(SearchProvider):
    """
    Brave Search API Provider
    
    Docs: https://api.search.brave.com/
    """
    
    name = "brave"
    BASE_URL = "https://api.search.brave.com/res/v1"
    
    def __init__(self, api_key: Optional[str] = None, config: Optional[Dict] = None):
        super().__init__(api_key, config)
        self.api_key = api_key or os.getenv("BRAVE_API_KEY")
        if not self.api_key:
            raise ValueError("Brave API key required. Set BRAVE_API_KEY environment variable.")
    
    def _get_headers(self) -> Dict[str, str]:
        """Get request headers"""
        return {
            "Accept": "application/json",
            "X-Subscription-Token": self.api_key,
        }
    
    async def search(
        self,
        query: str,
        num_results: int = 10,
        offset: int = 0,
        **kwargs
    ) -> List[SearchResult]:
        """Perform web search via Brave"""
        url = f"{self.BASE_URL}/web/search"
        params = {
            "q": query,
            "count": min(num_results, 20),
            "offset": offset,
        }
        
        # Add optional filters
        if "freshness" in kwargs:
            params["freshness"] = kwargs["freshness"]  # pd, pw, pm, py
        if "country" in kwargs:
            params["country"] = kwargs["country"]
        if "search_lang" in kwargs:
            params["search_lang"] = kwargs["search_lang"]
        
        async with self._session.get(url, headers=self._get_headers(), params=params) as resp:
            if resp.status != 200:
                text = await resp.text()
                raise Exception(f"Brave search failed: {resp.status} - {text}")
            
            data = await resp.json()
            results = []
            
            web_results = data.get("web", {}).get("results", [])
            for i, item in enumerate(web_results[:num_results]):
                results.append(SearchResult(
                    title=item.get("title", ""),
                    url=item.get("url", ""),
                    snippet=item.get("description", ""),
                    source=self.name,
                    rank=i + 1,
                    timestamp=datetime.now(),
                    metadata={
                        "age": item.get("age"),
                        "page_age": item.get("page_age"),
                    }
                ))
            
            return results
    
    async def search_news(
        self,
        query: str,
        num_results: int = 10,
        **kwargs
    ) -> List[NewsResult]:
        """Perform news search via Brave"""
        url = f"{self.BASE_URL}/news/search"
        params = {
            "q": query,
            "count": min(num_results, 20),
        }
        
        if "freshness" in kwargs:
            params["freshness"] = kwargs["freshness"]
        
        async with self._session.get(url, headers=self._get_headers(), params=params) as resp:
            if resp.status != 200:
                text = await resp.text()
                raise Exception(f"Brave news search failed: {resp.status} - {text}")
            
            data = await resp.json()
            results = []
            
            news_results = data.get("results", [])
            for item in news_results[:num_results]:
                # Parse published date
                pub_date = None
                if "age" in item:
                    # Brave returns relative age, we'll use current time
                    pub_date = datetime.now()
                
                results.append(NewsResult(
                    title=item.get("title", ""),
                    url=item.get("url", ""),
                    snippet=item.get("description", ""),
                    source=self.name,
                    publisher=item.get("meta", {}).get("publisher", "Unknown"),
                    published_at=pub_date,
                    image_url=item.get("meta", {}).get("thumbnail", {}).get("src"),
                    metadata={
                        "age": item.get("age"),
                    }
                ))
            
            return results
    
    async def search_images(
        self,
        query: str,
        num_results: int = 10,
        **kwargs
    ) -> List[ImageResult]:
        """Perform image search via Brave"""
        url = f"{self.BASE_URL}/images/search"
        params = {
            "q": query,
            "count": min(num_results, 50),
        }
        
        async with self._session.get(url, headers=self._get_headers(), params=params) as resp:
            if resp.status != 200:
                text = await resp.text()
                raise Exception(f"Brave image search failed: {resp.status} - {text}")
            
            data = await resp.json()
            results = []
            
            image_results = data.get("results", [])
            for item in image_results[:num_results]:
                results.append(ImageResult(
                    title=item.get("title", ""),
                    url=item.get("url", ""),
                    source_url=item.get("source", ""),
                    thumbnail_url=item.get("thumbnail", {}).get("src"),
                    width=item.get("properties", {}).get("width"),
                    height=item.get("properties", {}).get("height"),
                    source=self.name,
                ))
            
            return results
    
    async def search_academic(
        self,
        query: str,
        num_results: int = 10,
        **kwargs
    ) -> List[AcademicResult]:
        """
        Perform academic search via Brave
        
        Note: Brave doesn't have a dedicated academic endpoint,
        so we use web search with academic-focused query
        """
        # Enhance query for academic results
        academic_query = f"{query} site:arxiv.org OR site:scholar.google.com OR inurl:.edu"
        
        web_results = await self.search(academic_query, num_results=num_results * 2)
        
        results = []
        for result in web_results[:num_results]:
            results.append(AcademicResult(
                title=result.title,
                url=result.url,
                authors=[],  # Brave doesn't provide author info
                abstract=result.snippet,
                source=self.name,
                metadata=result.metadata,
            ))
        
        return results


class GoogleSearchProvider(SearchProvider):
    """
    Google Custom Search API Provider
    
    Docs: https://developers.google.com/custom-search/v1/overview
    """
    
    name = "google"
    BASE_URL = "https://www.googleapis.com/customsearch/v1"
    
    def __init__(self, api_key: Optional[str] = None, config: Optional[Dict] = None):
        super().__init__(api_key, config)
        self.api_key = api_key or os.getenv("GOOGLE_SEARCH_API_KEY")
        self.cx = config.get("cx") if config else os.getenv("GOOGLE_SEARCH_CX")
        
        if not self.api_key:
            raise ValueError("Google API key required. Set GOOGLE_SEARCH_API_KEY.")
        if not self.cx:
            raise ValueError("Google Search CX required. Set GOOGLE_SEARCH_CX.")
    
    async def search(
        self,
        query: str,
        num_results: int = 10,
        **kwargs
    ) -> List[SearchResult]:
        """Perform web search via Google"""
        url = self.BASE_URL
        params = {
            "key": self.api_key,
            "cx": self.cx,
            "q": query,
            "num": min(num_results, 10),
        }
        
        if "start" in kwargs:
            params["start"] = kwargs["start"]
        if "date_restrict" in kwargs:
            params["dateRestrict"] = kwargs["date_restrict"]
        if "lr" in kwargs:
            params["lr"] = kwargs["lr"]
        
        async with self._session.get(url, params=params) as resp:
            if resp.status != 200:
                text = await resp.text()
                raise Exception(f"Google search failed: {resp.status} - {text}")
            
            data = await resp.json()
            results = []
            
            items = data.get("items", [])
            for i, item in enumerate(items):
                results.append(SearchResult(
                    title=item.get("title", ""),
                    url=item.get("link", ""),
                    snippet=item.get("snippet", ""),
                    source=self.name,
                    rank=i + 1,
                    timestamp=datetime.now(),
                    metadata={
                        "displayLink": item.get("displayLink"),
                        "formattedUrl": item.get("formattedUrl"),
                    }
                ))
            
            return results
    
    async def search_news(
        self,
        query: str,
        num_results: int = 10,
        **kwargs
    ) -> List[NewsResult]:
        """Perform news search via Google"""
        # Use sort by date for news
        params = {
            "key": self.api_key,
            "cx": self.cx,
            "q": query,
            "num": min(num_results, 10),
            "sort": "date",
        }
        
        if "date_restrict" in kwargs:
            params["dateRestrict"] = kwargs["date_restrict"]
        
        async with self._session.get(self.BASE_URL, params=params) as resp:
            if resp.status != 200:
                text = await resp.text()
                raise Exception(f"Google news search failed: {resp.status} - {text}")
            
            data = await resp.json()
            results = []
            
            items = data.get("items", [])
            for item in items:
                # Try to parse date from pagemap
                pub_date = None
                pagemap = item.get("pagemap", {})
                if "metatags" in pagemap:
                    for meta in pagemap["metatags"]:
                        if "article:published_time" in meta:
                            try:
                                pub_date = datetime.fromisoformat(
                                    meta["article:published_time"].replace("Z", "+00:00")
                                )
                            except:
                                pass
                
                results.append(NewsResult(
                    title=item.get("title", ""),
                    url=item.get("link", ""),
                    snippet=item.get("snippet", ""),
                    source=self.name,
                    publisher=item.get("displayLink", "Unknown"),
                    published_at=pub_date,
                    metadata={
                        "pagemap": pagemap,
                    }
                ))
            
            return results
    
    async def search_images(
        self,
        query: str,
        num_results: int = 10,
        **kwargs
    ) -> List[ImageResult]:
        """Perform image search via Google"""
        params = {
            "key": self.api_key,
            "cx": self.cx,
            "q": query,
            "num": min(num_results, 10),
            "searchType": "image",
        }
        
        if "img_size" in kwargs:
            params["imgSize"] = kwargs["img_size"]
        if "img_type" in kwargs:
            params["imgType"] = kwargs["img_type"]
        
        async with self._session.get(self.BASE_URL, params=params) as resp:
            if resp.status != 200:
                text = await resp.text()
                raise Exception(f"Google image search failed: {resp.status} - {text}")
            
            data = await resp.json()
            results = []
            
            items = data.get("items", [])
            for item in items:
                image_data = item.get("image", {})
                results.append(ImageResult(
                    title=item.get("title", ""),
                    url=item.get("link", ""),
                    source_url=item.get("image", {}).get("contextLink", ""),
                    thumbnail_url=item.get("image", {}).get("thumbnailLink"),
                    width=image_data.get("width"),
                    height=image_data.get("height"),
                    source=self.name,
                ))
            
            return results
    
    async def search_academic(
        self,
        query: str,
        num_results: int = 10,
        **kwargs
    ) -> List[AcademicResult]:
        """Perform academic search via Google"""
        # Use Google Scholar style search
        academic_query = f"{query} filetype:pdf OR site:arxiv.org OR site:researchgate.net"
        
        web_results = await self.search(academic_query, num_results=num_results * 2)
        
        results = []
        for result in web_results[:num_results]:
            results.append(AcademicResult(
                title=result.title,
                url=result.url,
                authors=[],  # Would need parsing
                abstract=result.snippet,
                source=self.name,
                metadata=result.metadata,
            ))
        
        return results


class BingSearchProvider(SearchProvider):
    """
    Bing Search API Provider
    
    Docs: https://www.microsoft.com/en-us/bing/apis/bing-web-search-api
    """
    
    name = "bing"
    BASE_URL = "https://api.bing.microsoft.com/v7.0"
    
    def __init__(self, api_key: Optional[str] = None, config: Optional[Dict] = None):
        super().__init__(api_key, config)
        self.api_key = api_key or os.getenv("BING_SEARCH_API_KEY")
        if not self.api_key:
            raise ValueError("Bing API key required. Set BING_SEARCH_API_KEY.")
    
    def _get_headers(self) -> Dict[str, str]:
        """Get request headers"""
        return {
            "Ocp-Apim-Subscription-Key": self.api_key,
        }
    
    async def search(
        self,
        query: str,
        num_results: int = 10,
        **kwargs
    ) -> List[SearchResult]:
        """Perform web search via Bing"""
        url = f"{self.BASE_URL}/search"
        params = {
            "q": query,
            "count": min(num_results, 50),
            "responseFilter": "Webpages",
        }
        
        if "offset" in kwargs:
            params["offset"] = kwargs["offset"]
        if "freshness" in kwargs:
            params["freshness"] = kwargs["freshness"]  # Day, Week, Month
        if "mkt" in kwargs:
            params["mkt"] = kwargs["mkt"]
        
        async with self._session.get(url, headers=self._get_headers(), params=params) as resp:
            if resp.status != 200:
                text = await resp.text()
                raise Exception(f"Bing search failed: {resp.status} - {text}")
            
            data = await resp.json()
            results = []
            
            webpages = data.get("webPages", {}).get("value", [])
            for i, item in enumerate(webpages):
                results.append(SearchResult(
                    title=item.get("name", ""),
                    url=item.get("url", ""),
                    snippet=item.get("snippet", ""),
                    source=self.name,
                    rank=i + 1,
                    timestamp=datetime.now(),
                    metadata={
                        "displayUrl": item.get("displayUrl"),
                        "dateLastCrawled": item.get("dateLastCrawled"),
                    }
                ))
            
            return results
    
    async def search_news(
        self,
        query: str,
        num_results: int = 10,
        **kwargs
    ) -> List[NewsResult]:
        """Perform news search via Bing"""
        url = f"{self.BASE_URL}/news/search"
        params = {
            "q": query,
            "count": min(num_results, 100),
        }
        
        if "freshness" in kwargs:
            params["freshness"] = kwargs["freshness"]
        if "sortBy" in kwargs:
            params["sortBy"] = kwargs["sortBy"]
        
        async with self._session.get(url, headers=self._get_headers(), params=params) as resp:
            if resp.status != 200:
                text = await resp.text()
                raise Exception(f"Bing news search failed: {resp.status} - {text}")
            
            data = await resp.json()
            results = []
            
            news_items = data.get("value", [])
            for item in news_items:
                # Parse date
                pub_date = None
                if "datePublished" in item:
                    try:
                        pub_date = datetime.fromisoformat(
                            item["datePublished"].replace("Z", "+00:00")
                        )
                    except:
                        pass
                
                results.append(NewsResult(
                    title=item.get("name", ""),
                    url=item.get("url", ""),
                    snippet=item.get("description", ""),
                    source=self.name,
                    publisher=item.get("provider", [{}])[0].get("name", "Unknown"),
                    published_at=pub_date,
                    image_url=item.get("image", {}).get("thumbnail", {}).get("contentUrl"),
                    metadata={
                        "category": item.get("category"),
                    }
                ))
            
            return results
    
    async def search_images(
        self,
        query: str,
        num_results: int = 10,
        **kwargs
    ) -> List[ImageResult]:
        """Perform image search via Bing"""
        url = f"{self.BASE_URL}/images/search"
        params = {
            "q": query,
            "count": min(num_results, 150),
        }
        
        async with self._session.get(url, headers=self._get_headers(), params=params) as resp:
            if resp.status != 200:
                text = await resp.text()
                raise Exception(f"Bing image search failed: {resp.status} - {text}")
            
            data = await resp.json()
            results = []
            
            image_items = data.get("value", [])
            for item in image_items:
                results.append(ImageResult(
                    title=item.get("name", ""),
                    url=item.get("contentUrl", ""),
                    source_url=item.get("hostPageUrl", ""),
                    thumbnail_url=item.get("thumbnailUrl"),
                    width=item.get("width"),
                    height=item.get("height"),
                    source=self.name,
                ))
            
            return results
    
    async def search_academic(
        self,
        query: str,
        num_results: int = 10,
        **kwargs
    ) -> List[AcademicResult]:
        """Perform academic search via Bing"""
        # Use Bing's academic query enhancement
        academic_query = f"{query} (academic OR research OR paper OR journal)"
        
        web_results = await self.search(academic_query, num_results=num_results * 2)
        
        results = []
        for result in web_results[:num_results]:
            results.append(AcademicResult(
                title=result.title,
                url=result.url,
                authors=[],
                abstract=result.snippet,
                source=self.name,
                metadata=result.metadata,
            ))
        
        return results


# Provider registry
_PROVIDER_MAP = {
    "brave": BraveSearchProvider,
    "google": GoogleSearchProvider,
    "bing": BingSearchProvider,
}


def get_provider(name: str, **kwargs) -> SearchProvider:
    """
    Get a search provider by name
    
    Args:
        name: Provider name (brave, google, bing)
        **kwargs: Provider configuration
        
    Returns:
        Configured provider instance
    """
    provider_class = _PROVIDER_MAP.get(name.lower())
    if not provider_class:
        raise ValueError(f"Unknown provider: {name}. Available: {list(_PROVIDER_MAP.keys())}")
    
    return provider_class(**kwargs)


def list_providers() -> List[str]:
    """List available provider names"""
    return list(_PROVIDER_MAP.keys())
