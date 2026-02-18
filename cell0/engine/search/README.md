# Enhanced Web Search for Cell 0 OS

Advanced web search module with multiple providers, intelligent caching, and result ranking.

## Features

- **Multi-Provider Support**: Brave Search (primary), Google Search API, Bing Search API
- **Intelligent Failover**: Automatically switches to backup providers when primary fails
- **Smart Caching**: Time-based caching with query normalization
- **Result Ranking**: TF-IDF relevance scoring, diversity ranking (MMR), recency boosting
- **Search Types**: Web, News, Images, Academic
- **Filtering**: Domain filtering, date range, content length, duplicate removal

## Quick Start

```python
from cell0.engine.tools.web_search_enhanced import EnhancedWebSearch, SearchType

async with EnhancedWebSearch() as search:
    # Simple web search
    response = await search.search("python async programming")
    
    # News search
    news = await search.search_news("AI breakthrough", freshness="pw")  # Past week
    
    # Image search
    images = await search.search_images("cute cats")
    
    # Academic search
    papers = await search.search_academic("neural networks")
```

## Configuration

### Environment Variables

Set the following environment variables for API access:

```bash
# Brave Search (primary) - Required
export BRAVE_API_KEY="your_brave_api_key"

# Google Search (fallback) - Optional
export GOOGLE_SEARCH_API_KEY="your_google_api_key"
export GOOGLE_SEARCH_CX="your_custom_search_engine_id"

# Bing Search (fallback) - Optional
export BING_SEARCH_API_KEY="your_bing_api_key"
```

### Provider Priority

By default, the system tries providers in this order:
1. Brave Search
2. Google Search
3. Bing Search

You can customize the provider order:

```python
search = EnhancedWebSearch(providers=["google", "bing", "brave"])
```

## Advanced Usage

### Custom Search Request

```python
from cell0.engine.tools.web_search_enhanced import SearchRequest, SearchType

request = SearchRequest(
    query="machine learning",
    search_type=SearchType.NEWS,
    num_results=20,
    freshness="pm",  # Past month
    exclude_domains=["spam-site.com"],
    include_domains=["arxiv.org", "ieee.org"],
    enable_ranking=True,
    enable_filtering=True,
)

response = await search.search_with_request(request)
```

### Caching Options

```python
from cell0.engine.search.cache import SearchCache

# Custom cache configuration
cache = SearchCache(
    cache_dir="/path/to/cache",
    memory_cache_size=200,
    enable_disk_cache=True,
)

search = EnhancedWebSearch(cache=cache)
```

### Result Ranking

```python
from cell0.engine.search.ranker import ResultRanker

# Custom ranking weights
ranker = ResultRanker(
    relevance_weight=0.5,
    diversity_weight=0.2,
    recency_weight=0.2,
    quality_weight=0.1,
)

search = EnhancedWebSearch(ranker=ranker)
```

## API Reference

### EnhancedWebSearch

Main search tool class.

#### Methods

- `search(query, num_results=10, **kwargs)` - Web search
- `search_news(query, num_results=10, **kwargs)` - News search
- `search_images(query, num_results=10, **kwargs)` - Image search
- `search_academic(query, num_results=10, **kwargs)` - Academic search
- `search_with_request(request)` - Search with SearchRequest object
- `health_check()` - Check provider health

### SearchRequest

Complete search request configuration.

```python
@dataclass
class SearchRequest:
    query: str
    search_type: SearchType = SearchType.WEB
    num_results: int = 10
    providers: Optional[List[str]] = None
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
```

### SearchResponse

Search response containing results.

```python
@dataclass
class SearchResponse:
    query: str
    search_type: SearchType
    results: List[Union[SearchResult, NewsResult, ImageResult, AcademicResult]]
    total_results: int
    providers_used: List[str]
    cached: bool
    execution_time_ms: float
    timestamp: datetime
    metadata: Dict[str, Any]
```

## Search Types

### Web Search
```python
response = await search.search("python tutorials")
for result in response.results:
    print(f"{result.title}: {result.url}")
```

### News Search
```python
response = await search.search_news("technology", freshness="pd")  # Past day
for article in response.results:
    print(f"{article.title} - {article.publisher}")
    print(f"Published: {article.published_at}")
```

### Image Search
```python
response = await search.search_images("landscapes")
for image in response.results:
    print(f"{image.title}: {image.url}")
    print(f"Thumbnail: {image.thumbnail_url}")
```

### Academic Search
```python
response = await search.search_academic("quantum computing")
for paper in response.results:
    print(f"{paper.title}")
    print(f"Authors: {', '.join(paper.authors)}")
    print(f"Year: {paper.year}, Citations: {paper.citations}")
```

## Architecture

### Components

1. **cache.py** - Caching system with memory and disk backends
2. **providers.py** - Search provider implementations
3. **ranker.py** - Result ranking and filtering algorithms
4. **web_search_enhanced.py** - Main tool interface

### Data Flow

```
User Request
     |
     v
SearchRequest -> Cache Check -> Provider(s) -> Filter -> Rank -> Cache Store -> Response
                                    ^
                                    |
                              Failover on Error
```

### Failover Logic

1. Try primary provider (Brave)
2. If timeout or error, try next provider (Google)
3. If that fails, try final provider (Bing)
4. Return results from first successful provider
5. Aggregate results if multiple providers succeed

## Testing

Run tests with pytest:

```bash
cd /Users/yigremgetachewtamiru/.openclaw/workspace/cell0
pytest tests/test_enhanced_search.py -v
```

## License

Part of Cell 0 OS
