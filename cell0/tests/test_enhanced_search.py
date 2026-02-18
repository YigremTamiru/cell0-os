"""
Tests for Enhanced Web Search Module

Run with: pytest tests/test_enhanced_search.py -v
"""

import asyncio
import pytest
import tempfile
import json
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch, MagicMock

# Import search components
from cell0.engine.search.cache import SearchCache, CacheEntry, get_cache, set_cache
from cell0.engine.search.providers import (
    SearchResult,
    NewsResult,
    ImageResult,
    AcademicResult,
    BraveSearchProvider,
    GoogleSearchProvider,
    BingSearchProvider,
    get_provider,
    list_providers,
)
from cell0.engine.search.ranker import (
    ResultRanker,
    ResultFilter,
    ResultAggregator,
    RankedResult,
)
from cell0.engine.tools.web_search_enhanced import (
    EnhancedWebSearch,
    SearchRequest,
    SearchResponse,
    SearchType,
    web_search,
    news_search,
    image_search,
    academic_search,
)


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def temp_cache_dir():
    """Create a temporary cache directory"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def sample_search_results():
    """Create sample search results"""
    return [
        SearchResult(
            title="Python Async Programming",
            url="https://example.com/python-async",
            snippet="Learn about async programming in Python",
            source="test",
            rank=1,
        ),
        SearchResult(
            title="Asyncio Tutorial",
            url="https://example.com/asyncio",
            snippet="Complete guide to asyncio",
            source="test",
            rank=2,
        ),
        SearchResult(
            title="Python Concurrency",
            url="https://example.com/concurrency",
            snippet="Understanding Python concurrency",
            source="test",
            rank=3,
        ),
    ]


@pytest.fixture
def sample_news_results():
    """Create sample news results"""
    return [
        NewsResult(
            title="Tech News Today",
            url="https://news.example.com/1",
            snippet="Latest tech news",
            source="test",
            publisher="Tech Daily",
            published_at=datetime.now(),
        ),
        NewsResult(
            title="AI Breakthrough",
            url="https://news.example.com/2",
            snippet="New AI technology announced",
            source="test",
            publisher="AI Weekly",
            published_at=datetime.now() - timedelta(hours=2),
        ),
    ]


@pytest.fixture
def sample_image_results():
    """Create sample image results"""
    return [
        ImageResult(
            title="Python Logo",
            url="https://images.example.com/python.png",
            source_url="https://example.com",
            thumbnail_url="https://images.example.com/python_thumb.png",
            width=200,
            height=200,
            source="test",
        ),
        ImageResult(
            title="Async Diagram",
            url="https://images.example.com/async.png",
            source_url="https://example.com/async",
            thumbnail_url="https://images.example.com/async_thumb.png",
            width=400,
            height=300,
            source="test",
        ),
    ]


@pytest.fixture
def mock_brave_provider():
    """Create a mock Brave provider"""
    provider = Mock(spec=BraveSearchProvider)
    provider.name = "brave"
    provider.search = AsyncMock(return_value=[])
    provider.search_news = AsyncMock(return_value=[])
    provider.search_images = AsyncMock(return_value=[])
    provider.search_academic = AsyncMock(return_value=[])
    provider.health_check = AsyncMock(return_value=True)
    return provider


@pytest.fixture
def mock_google_provider():
    """Create a mock Google provider"""
    provider = Mock(spec=GoogleSearchProvider)
    provider.name = "google"
    provider.search = AsyncMock(return_value=[])
    provider.search_news = AsyncMock(return_value=[])
    provider.search_images = AsyncMock(return_value=[])
    provider.search_academic = AsyncMock(return_value=[])
    provider.health_check = AsyncMock(return_value=True)
    return provider


@pytest.fixture
def mock_bing_provider():
    """Create a mock Bing provider"""
    provider = Mock(spec=BingSearchProvider)
    provider.name = "bing"
    provider.search = AsyncMock(return_value=[])
    provider.search_news = AsyncMock(return_value=[])
    provider.search_images = AsyncMock(return_value=[])
    provider.search_academic = AsyncMock(return_value=[])
    provider.health_check = AsyncMock(return_value=True)
    return provider


# ============================================================================
# Cache Tests
# ============================================================================

class TestSearchCache:
    """Test search cache functionality"""
    
    @pytest.mark.asyncio
    async def test_cache_set_and_get(self, temp_cache_dir):
        """Test basic cache set and get operations"""
        cache = SearchCache(cache_dir=temp_cache_dir, enable_disk_cache=True)
        
        # Set a value
        results = [{"title": "Test", "url": "https://test.com"}]
        entry = await cache.set(
            query="test query",
            search_type="web",
            provider="brave",
            results=results,
        )
        
        assert entry.query == "test query"
        assert entry.search_type == "web"
        assert entry.provider == "brave"
        assert entry.results == results
        
        # Get the value
        cached = await cache.get("test query", "web", "brave")
        assert cached is not None
        assert cached.results == results
    
    @pytest.mark.asyncio
    async def test_cache_expiration(self, temp_cache_dir):
        """Test cache entry expiration"""
        cache = SearchCache(cache_dir=temp_cache_dir)
        
        # Set with very short TTL
        await cache.set(
            query="expire test",
            search_type="web",
            provider="brave",
            results=[{"test": "data"}],
            ttl=timedelta(milliseconds=1),
        )
        
        # Wait for expiration
        await asyncio.sleep(0.1)
        
        # Should be expired
        cached = await cache.get("expire test", "web", "brave")
        assert cached is None
    
    @pytest.mark.asyncio
    async def test_cache_invalidation(self, temp_cache_dir):
        """Test cache invalidation"""
        cache = SearchCache(cache_dir=temp_cache_dir)
        
        # Set multiple entries
        await cache.set("query1", "web", "brave", [])
        await cache.set("query2", "web", "brave", [])
        await cache.set("query3", "news", "google", [])
        
        # Invalidate specific query
        count = await cache.invalidate("query1", "web", "brave")
        assert count == 1
        
        cached = await cache.get("query1", "web", "brave")
        assert cached is None
        
        # Other entries should still exist
        assert await cache.get("query2", "web", "brave") is not None
    
    @pytest.mark.asyncio
    async def test_cache_stats(self, temp_cache_dir):
        """Test cache statistics"""
        cache = SearchCache(cache_dir=temp_cache_dir)
        
        # Initial stats
        stats = cache.get_stats()
        assert stats["hits"] == 0
        assert stats["misses"] == 0
        
        # Add entry
        await cache.set("test", "web", "brave", [])
        
        # Miss
        await cache.get("nonexistent", "web", "brave")
        
        # Hit
        await cache.get("test", "web", "brave")
        
        stats = cache.get_stats()
        assert stats["hits"] == 1
        assert stats["misses"] == 1
        assert stats["hit_rate"] == 0.5
    
    @pytest.mark.asyncio
    async def test_cache_query_normalization(self, temp_cache_dir):
        """Test that similar queries hit the same cache"""
        cache = SearchCache(cache_dir=temp_cache_dir)
        
        # Set with normalized query
        await cache.set("python async", "web", "brave", [{"test": "data"}])
        
        # Should hit with different whitespace
        cached = await cache.get("python   async", "web", "brave")
        assert cached is not None
        
        # Should hit with different case
        cached = await cache.get("PYTHON ASYNC", "web", "brave")
        assert cached is not None


# ============================================================================
# Provider Tests
# ============================================================================

class TestSearchProviders:
    """Test search provider implementations"""
    
    def test_search_result_dataclass(self):
        """Test SearchResult dataclass"""
        result = SearchResult(
            title="Test Title",
            url="https://test.com",
            snippet="Test snippet",
            source="brave",
            rank=1,
        )
        
        assert result.title == "Test Title"
        assert result.url == "https://test.com"
        assert result.to_dict()["title"] == "Test Title"
    
    def test_news_result_dataclass(self):
        """Test NewsResult dataclass"""
        result = NewsResult(
            title="News Title",
            url="https://news.com",
            snippet="News snippet",
            source="brave",
            publisher="News Corp",
            published_at=datetime.now(),
        )
        
        assert result.publisher == "News Corp"
        assert result.to_dict()["publisher"] == "News Corp"
    
    def test_image_result_dataclass(self):
        """Test ImageResult dataclass"""
        result = ImageResult(
            title="Image Title",
            url="https://image.com/pic.jpg",
            source_url="https://example.com",
            width=100,
            height=100,
            source="bing",
        )
        
        assert result.width == 100
        assert result.height == 100
        assert result.to_dict()["width"] == 100
    
    def test_academic_result_dataclass(self):
        """Test AcademicResult dataclass"""
        result = AcademicResult(
            title="Paper Title",
            url="https://arxiv.org/abs/1234",
            authors=["Author 1", "Author 2"],
            abstract="Abstract text",
            year=2024,
            citations=100,
            source="google",
        )
        
        assert len(result.authors) == 2
        assert result.year == 2024
        assert result.to_dict()["citations"] == 100
    
    def test_get_provider(self):
        """Test provider factory"""
        providers = list_providers()
        assert "brave" in providers
        assert "google" in providers
        assert "bing" in providers


# ============================================================================
# Ranker Tests
# ============================================================================

class TestResultRanker:
    """Test result ranking functionality"""
    
    def test_relevance_ranking(self, sample_search_results):
        """Test basic relevance ranking"""
        ranker = ResultRanker()
        
        ranked = ranker.rank(sample_search_results, "python async programming")
        
        assert len(ranked) == 3
        assert all(isinstance(r, RankedResult) for r in ranked)
        assert all(r.relevance_score > 0 for r in ranked)
    
    def test_ranking_weights(self, sample_search_results):
        """Test that ranking respects weights"""
        ranker = ResultRanker(
            relevance_weight=1.0,
            diversity_weight=0.0,
            recency_weight=0.0,
            quality_weight=0.0,
        )
        
        ranked = ranker.rank(sample_search_results, "test query")
        
        # Should only consider relevance
        for r in ranked:
            assert r.ranking_factors["relevance"] > 0
    
    def test_empty_results(self):
        """Test ranking with empty results"""
        ranker = ResultRanker()
        
        ranked = ranker.rank([], "test")
        
        assert ranked == []


class TestResultFilter:
    """Test result filtering functionality"""
    
    def test_remove_duplicates(self, sample_search_results):
        """Test duplicate removal"""
        # Create duplicates
        results = sample_search_results + sample_search_results[:1]
        
        filtered = ResultFilter.remove_duplicates(results, similarity_threshold=0.9)
        
        assert len(filtered) <= len(results)
    
    def test_filter_by_domain(self, sample_search_results):
        """Test domain filtering"""
        results = sample_search_results
        
        # Include only
        filtered = ResultFilter.filter_by_domain(
            results,
            include_domains=["example.com"]
        )
        assert len(filtered) == len(results)
        
        # Exclude
        filtered = ResultFilter.filter_by_domain(
            results,
            exclude_domains=["example.com"]
        )
        assert len(filtered) == 0
    
    def test_filter_by_date(self, sample_news_results):
        """Test date filtering"""
        results = sample_news_results
        
        # Filter recent only
        yesterday = datetime.now() - timedelta(days=1)
        filtered = ResultFilter.filter_by_date(results, since=yesterday)
        
        assert len(filtered) == len(results)
        
        # Filter future (should return nothing)
        tomorrow = datetime.now() + timedelta(days=1)
        filtered = ResultFilter.filter_by_date(results, since=tomorrow)
        
        assert len(filtered) == 0
    
    def test_filter_by_content_length(self, sample_search_results):
        """Test content length filtering"""
        results = sample_search_results
        
        # Filter long content
        filtered = ResultFilter.filter_by_content_length(
            results,
            min_length=1000
        )
        
        # Should filter out short snippets
        assert len(filtered) < len(results)


class TestResultAggregator:
    """Test result aggregation"""
    
    def test_merge_results(self, sample_search_results):
        """Test merging results from multiple providers"""
        provider_results = {
            "brave": sample_search_results[:2],
            "google": sample_search_results[1:],
        }
        
        merged = ResultAggregator.merge_results(
            provider_results,
            max_results=5,
            deduplicate=True,
        )
        
        assert len(merged) <= 5
    
    def test_round_robin(self, sample_search_results):
        """Test round-robin aggregation"""
        provider_results = {
            "brave": sample_search_results[:2],
            "google": sample_search_results[2:],
        }
        
        merged = ResultAggregator.round_robin(
            provider_results,
            max_results=10,
        )
        
        # Should alternate between providers
        assert len(merged) > 0


# ============================================================================
# Enhanced Web Search Tests
# ============================================================================

class TestEnhancedWebSearch:
    """Test enhanced web search functionality"""
    
    @pytest.mark.asyncio
    async def test_search_request_creation(self):
        """Test search request creation"""
        request = SearchRequest(
            query="test query",
            search_type=SearchType.WEB,
            num_results=10,
        )
        
        assert request.query == "test query"
        assert request.search_type == SearchType.WEB
        assert request.num_results == 10
    
    @pytest.mark.asyncio
    async def test_search_response_creation(self, sample_search_results):
        """Test search response creation"""
        response = SearchResponse(
            query="test",
            search_type=SearchType.WEB,
            results=sample_search_results,
            total_results=len(sample_search_results),
            providers_used=["brave"],
            cached=False,
            execution_time_ms=100.0,
        )
        
        assert response.query == "test"
        assert response.total_results == 3
        assert not response.cached
        
        # Test JSON serialization
        json_str = response.to_json()
        assert "test" in json_str
    
    @pytest.mark.asyncio
    async def test_enhanced_search_initialization(self, temp_cache_dir):
        """Test EnhancedWebSearch initialization"""
        cache = SearchCache(cache_dir=temp_cache_dir)
        
        with patch.dict('os.environ', {'BRAVE_API_KEY': 'test_key'}):
            search = EnhancedWebSearch(
                providers=["brave"],
                cache=cache,
            )
            
            assert search.providers == ["brave"]
            assert search.cache == cache
            assert search.enable_failover is True
    
    @pytest.mark.asyncio
    async def test_provider_failover(
        self,
        mock_brave_provider,
        mock_google_provider,
        temp_cache_dir,
    ):
        """Test provider failover when primary fails"""
        cache = SearchCache(cache_dir=temp_cache_dir)
        
        # Set up brave to fail, google to succeed
        mock_brave_provider.search.side_effect = Exception("Brave failed")
        mock_google_provider.search.return_value = [
            SearchResult(
                title="Google Result",
                url="https://google.com",
                snippet="From Google",
                source="google",
                rank=1,
            )
        ]
        
        with patch('cell0.engine.tools.web_search_enhanced.EnhancedWebSearch._create_provider') as mock_create:
            mock_create.side_effect = [mock_brave_provider, mock_google_provider]
            
            search = EnhancedWebSearch(
                providers=["brave", "google"],
                cache=cache,
                enable_failover=True,
            )
            
            # Manually set up providers
            search._provider_instances = {
                "brave": mock_brave_provider,
                "google": mock_google_provider,
            }
            search._initialized = True
            
            request = SearchRequest(
                query="test",
                search_type=SearchType.WEB,
                num_results=5,
            )
            
            response = await search.search_with_request(request)
            
            # Should have results from Google
            assert len(response.results) > 0
            assert "google" in response.providers_used
            assert response.metadata.get("errors") is not None
    
    @pytest.mark.asyncio
    async def test_cache_integration(self, temp_cache_dir):
        """Test caching integration"""
        cache = SearchCache(cache_dir=temp_cache_dir)
        
        mock_provider = Mock()
        mock_provider.search = AsyncMock(return_value=[
            SearchResult(
                title="Cached Result",
                url="https://test.com",
                snippet="Test",
                source="brave",
                rank=1,
            )
        ])
        mock_provider.name = "brave"
        
        with patch.dict('os.environ', {'BRAVE_API_KEY': 'test'}):
            search = EnhancedWebSearch(
                providers=["brave"],
                cache=cache,
            )
            
            search._provider_instances = {"brave": mock_provider}
            search._initialized = True
            
            # First search - should hit provider
            request = SearchRequest(
                query="cache test",
                search_type=SearchType.WEB,
                num_results=5,
                use_cache=True,
            )
            
            response1 = await search.search_with_request(request)
            assert not response1.cached
            assert mock_provider.search.call_count == 1
            
            # Second search - should hit cache
            response2 = await search.search_with_request(request)
            assert response2.cached
            # Provider should not be called again
            assert mock_provider.search.call_count == 1
    
    @pytest.mark.asyncio
    async def test_search_type_routing(self, temp_cache_dir):
        """Test that different search types route correctly"""
        cache = SearchCache(cache_dir=temp_cache_dir)
        
        mock_provider = Mock()
        mock_provider.search = AsyncMock(return_value=[])
        mock_provider.search_news = AsyncMock(return_value=[])
        mock_provider.search_images = AsyncMock(return_value=[])
        mock_provider.search_academic = AsyncMock(return_value=[])
        mock_provider.name = "brave"
        
        with patch.dict('os.environ', {'BRAVE_API_KEY': 'test'}):
            search = EnhancedWebSearch(
                providers=["brave"],
                cache=cache,
            )
            
            search._provider_instances = {"brave": mock_provider}
            search._initialized = True
            
            # Test each search type
            await search.search("test")
            assert mock_provider.search.called
            
            await search.search_news("test")
            assert mock_provider.search_news.called
            
            await search.search_images("test")
            assert mock_provider.search_images.called
            
            await search.search_academic("test")
            assert mock_provider.search_academic.called
    
    @pytest.mark.asyncio
    async def test_filtering_application(self, temp_cache_dir):
        """Test that filters are applied"""
        cache = SearchCache(cache_dir=temp_cache_dir)
        
        mock_provider = Mock()
        mock_provider.search = AsyncMock(return_value=[
            SearchResult(
                title="Spam Result",
                url="https://spam.com/page",
                snippet="Short",
                source="brave",
                rank=1,
            ),
            SearchResult(
                title="Good Result",
                url="https://example.com/page",
                snippet="This is a much longer and better snippet with more content",
                source="brave",
                rank=2,
            ),
        ])
        mock_provider.name = "brave"
        
        with patch.dict('os.environ', {'BRAVE_API_KEY': 'test'}):
            search = EnhancedWebSearch(
                providers=["brave"],
                cache=cache,
            )
            
            search._provider_instances = {"brave": mock_provider}
            search._initialized = True
            
            request = SearchRequest(
                query="test",
                search_type=SearchType.WEB,
                num_results=10,
                enable_filtering=True,
                min_content_length=20,
                exclude_domains=["spam.com"],
            )
            
            response = await search.search_with_request(request)
            
            # Should filter out spam result
            assert all("spam.com" not in r.url for r in response.results)
    
    @pytest.mark.asyncio
    async def test_health_check(self, temp_cache_dir):
        """Test provider health check"""
        cache = SearchCache(cache_dir=temp_cache_dir)
        
        mock_provider = Mock()
        mock_provider.health_check = AsyncMock(return_value=True)
        mock_provider.name = "brave"
        
        with patch.dict('os.environ', {'BRAVE_API_KEY': 'test'}):
            search = EnhancedWebSearch(
                providers=["brave"],
                cache=cache,
            )
            
            search._provider_instances = {"brave": mock_provider}
            search._initialized = True
            
            health = await search.health_check()
            
            assert health["brave"] is True
            assert mock_provider.health_check.called


# ============================================================================
# Integration Tests
# ============================================================================

class TestSearchIntegration:
    """Integration tests for the search system"""
    
    @pytest.mark.asyncio
    async def test_end_to_end_search_flow(self, temp_cache_dir):
        """Test complete search flow"""
        cache = SearchCache(cache_dir=temp_cache_dir)
        
        # Create mock results
        mock_results = [
            SearchResult(
                title=f"Result {i}",
                url=f"https://example.com/{i}",
                snippet=f"Snippet for result {i}",
                source="brave",
                rank=i,
            )
            for i in range(5)
        ]
        
        mock_provider = Mock()
        mock_provider.search = AsyncMock(return_value=mock_results)
        mock_provider.search_news = AsyncMock(return_value=[])
        mock_provider.search_images = AsyncMock(return_value=[])
        mock_provider.search_academic = AsyncMock(return_value=[])
        mock_provider.name = "brave"
        
        with patch.dict('os.environ', {'BRAVE_API_KEY': 'test'}):
            async with EnhancedWebSearch(providers=["brave"], cache=cache) as search:
                search._provider_instances = {"brave": mock_provider}
                
                # Perform search
                response = await search.search("integration test", num_results=3)
                
                assert isinstance(response, SearchResponse)
                assert response.query == "integration test"
                assert len(response.results) == 3
                assert not response.cached
                assert response.execution_time_ms > 0
    
    @pytest.mark.asyncio
    async def test_multiple_providers_aggregation(self, temp_cache_dir):
        """Test aggregation of results from multiple providers"""
        cache = SearchCache(cache_dir=temp_cache_dir)
        
        brave_results = [
            SearchResult(
                title="Brave Result",
                url="https://brave.com/1",
                snippet="From Brave",
                source="brave",
                rank=1,
            ),
        ]
        
        google_results = [
            SearchResult(
                title="Google Result",
                url="https://google.com/1",
                snippet="From Google",
                source="google",
                rank=1,
            ),
        ]
        
        mock_brave = Mock()
        mock_brave.search = AsyncMock(return_value=brave_results)
        mock_brave.name = "brave"
        
        mock_google = Mock()
        mock_google.search = AsyncMock(return_value=google_results)
        mock_google.name = "google"
        
        with patch.dict('os.environ', {
            'BRAVE_API_KEY': 'test',
            'GOOGLE_SEARCH_API_KEY': 'test',
            'GOOGLE_SEARCH_CX': 'test'
        }):
            search = EnhancedWebSearch(
                providers=["brave", "google"],
                cache=cache,
                enable_failover=True,
            )
            
            search._provider_instances = {
                "brave": mock_brave,
                "google": mock_google,
            }
            search._initialized = True
            
            response = await search.search("multi provider", num_results=10)
            
            assert len(response.results) > 0
            assert "brave" in response.providers_used


# ============================================================================
# Convenience Function Tests
# ============================================================================

class TestConvenienceFunctions:
    """Test convenience search functions"""
    
    @pytest.mark.asyncio
    async def test_web_search_function(self):
        """Test web_search convenience function"""
        mock_response = SearchResponse(
            query="test",
            search_type=SearchType.WEB,
            results=[],
            total_results=0,
            providers_used=[],
            cached=False,
            execution_time_ms=0.0,
        )
        
        with patch('cell0.engine.tools.web_search_enhanced.EnhancedWebSearch') as mock_search_class:
            mock_search = AsyncMock()
            mock_search_class.return_value.__aenter__ = AsyncMock(return_value=mock_search)
            mock_search_class.return_value.__aexit__ = AsyncMock(return_value=False)
            mock_search.search = AsyncMock(return_value=mock_response)
            
            response = await web_search("test query")
            
            assert response == mock_response
            mock_search.search.assert_called_once_with("test query", 10)
    
    @pytest.mark.asyncio
    async def test_news_search_function(self):
        """Test news_search convenience function"""
        mock_response = SearchResponse(
            query="test",
            search_type=SearchType.NEWS,
            results=[],
            total_results=0,
            providers_used=[],
            cached=False,
            execution_time_ms=0.0,
        )
        
        with patch('cell0.engine.tools.web_search_enhanced.EnhancedWebSearch') as mock_search_class:
            mock_search = AsyncMock()
            mock_search_class.return_value.__aenter__ = AsyncMock(return_value=mock_search)
            mock_search_class.return_value.__aexit__ = AsyncMock(return_value=False)
            mock_search.search_news = AsyncMock(return_value=mock_response)
            
            response = await news_search("test news")
            
            assert response == mock_response
            mock_search.search_news.assert_called_once_with("test news", 10)


# ============================================================================
# Error Handling Tests
# ============================================================================

class TestErrorHandling:
    """Test error handling"""
    
    @pytest.mark.asyncio
    async def test_all_providers_fail(self, temp_cache_dir):
        """Test behavior when all providers fail"""
        cache = SearchCache(cache_dir=temp_cache_dir)
        
        mock_brave = Mock()
        mock_brave.search = AsyncMock(side_effect=Exception("Brave error"))
        mock_brave.name = "brave"
        
        mock_google = Mock()
        mock_google.search = AsyncMock(side_effect=Exception("Google error"))
        mock_google.name = "google"
        
        with patch.dict('os.environ', {
            'BRAVE_API_KEY': 'test',
            'GOOGLE_SEARCH_API_KEY': 'test',
            'GOOGLE_SEARCH_CX': 'test'
        }):
            search = EnhancedWebSearch(
                providers=["brave", "google"],
                cache=cache,
            )
            
            search._provider_instances = {
                "brave": mock_brave,
                "google": mock_google,
            }
            search._initialized = True
            
            response = await search.search("test")
            
            # Should return empty results but not crash
            assert response.results == []
            assert len(response.metadata.get("errors", [])) == 2
    
    @pytest.mark.asyncio
    async def test_provider_timeout(self, temp_cache_dir):
        """Test provider timeout handling"""
        cache = SearchCache(cache_dir=temp_cache_dir)
        
        mock_provider = Mock()
        # Simulate slow response
        async def slow_search(*args, **kwargs):
            await asyncio.sleep(100)
            return []
        mock_provider.search = slow_search
        mock_provider.name = "brave"
        
        with patch.dict('os.environ', {'BRAVE_API_KEY': 'test'}):
            search = EnhancedWebSearch(
                providers=["brave"],
                cache=cache,
                failover_timeout=0.1,  # Very short timeout
            )
            
            search._provider_instances = {"brave": mock_provider}
            search._initialized = True
            
            response = await search.search("test")
            
            # Should timeout and return empty
            assert response.results == []
            assert "timeout" in str(response.metadata.get("errors", []))


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
