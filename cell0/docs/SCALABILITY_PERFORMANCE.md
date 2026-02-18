# Cell 0 OS - Scalability & Performance Guide

## Overview

This document describes the production-grade scalability and performance features implemented in Cell 0 OS.

## Components

### 1. Resource Management & Limits (`cell0/engine/resource_limits.py`)

#### ResourceMonitor
Continuous monitoring of system resources:
```python
from cell0.engine import get_resource_monitor

monitor = get_resource_monitor()
await monitor.start()

# Get current usage
usage = await monitor.get_current_usage()
print(f"Memory: {usage.memory_percent}%")

# Get history
history = await monitor.get_history(limit=100)
```

#### ResourceLimiter
Enforces resource limits:
```python
from cell0.engine import get_resource_limiter, ResourceLimits

limits = ResourceLimits(
    max_memory_percent=85.0,
    max_cpu_percent=90.0,
    max_disk_percent=90.0,
)

limiter = get_resource_limiter()
await limiter.start()

# Check limits
within_limits, violations = limiter.check_limits()
```

#### ModelMemoryManager
Intelligent model memory management with eviction policies:
```python
from cell0.engine import get_model_manager, EvictionPolicy

manager = get_model_manager()
manager.policy = EvictionPolicy.LRU

# Register model
info = await manager.register_model(
    model_id="qwen2.5:7b",
    model_name="Qwen 2.5 7B",
    memory_bytes=4 * 1024 * 1024 * 1024,  # 4GB
    priority=1,  # Higher = less likely to evict
)

# Access model (updates LRU)
await manager.access_model("qwen2.5:7b")

# Get stats
stats = manager.get_stats()
```

Eviction policies:
- `LRU`: Least Recently Used
- `LFU`: Least Frequently Used
- `FIFO`: First In First Out
- `TTL`: Time To Live
- `COST_BASED`: Based on memory/load_time ratio

#### DiskCleanupManager
Automatic disk space management:
```python
from cell0.engine import get_disk_cleanup

cleanup = get_disk_cleanup()
cleanup.register_cleanup_path("/tmp/cell0", max_age_days=7)
cleanup.register_cleanup_path("~/.cell0/cache", max_age_days=3)

await cleanup.start()
```

### 2. Caching Layer (`cell0/engine/cache/`)

#### Redis Client
Production-grade Redis client with circuit breaker:
```python
from cell0.engine.cache import RedisClient, RedisConfig

config = RedisConfig(
    host="localhost",
    port=6379,
    max_connections=50,
    circuit_failure_threshold=5,
)

client = RedisClient(config)
await client.connect()

# Basic operations
await client.set("key", {"data": "value"}, ttl_seconds=3600)
value = await client.get("key")

# Health check
health = await client.health_check()
```

#### Response Cache
HTTP response caching for API endpoints:
```python
from cell0.engine.cache import ResponseCache, CacheConfig, CacheStrategy

config = CacheConfig(
    default_ttl_seconds=300,
    max_body_size_bytes=1024*1024,
)

cache = ResponseCache(config=config)

# Configure endpoint
cache.configure_endpoint(
    "/api/models",
    strategy=CacheStrategy.ALWAYS,
    ttl_seconds=600,
)

# In FastAPI
from fastapi import FastAPI
from cell0.engine.cache import CacheMiddleware

app = FastAPI()
app.add_middleware(CacheMiddleware, cache=cache)
```

#### Search Result Cache
Intelligent caching for search results:
```python
from cell0.engine.cache import get_search_cache, SearchProvider, SearchType

cache = get_search_cache()

# Set TTL per search type
from datetime import timedelta
cache.set_ttl(SearchType.NEWS, ttl_seconds=600)
cache.set_ttl(SearchType.ACADEMIC, ttl_seconds=86400)

# Cache results
await cache.set(
    query="quantum computing",
    provider=SearchProvider.BRAVE,
    search_type=SearchType.WEB,
    results=[...],
)

# Retrieve
entry = await cache.get(
    query="quantum computing",
    provider=SearchProvider.BRAVE,
    search_type=SearchType.WEB,
)
```

#### Model Output Cache (Semantic Caching)
Cache LLM outputs based on semantic similarity:
```python
from cell0.engine.cache import get_model_output_cache, CacheMatchConfidence

cache = get_model_output_cache()

# Get with semantic matching
cached = await cache.get(
    prompt="What is the capital of France?",
    model_id="qwen2.5:7b",
    min_confidence=CacheMatchConfidence.MEDIUM,
)

if cached:
    print(f"Cache hit! Similarity: {cached.similarity}")
    output = cached.entry.output
else:
    # Generate and cache
    output = await generate_response(prompt)
    await cache.set(prompt, output, model_id="qwen2.5:7b")
```

Using the decorator:
```python
from cell0.engine.cache import with_model_cache

@with_model_cache(ttl_seconds=3600)
async def generate_response(prompt: str, model_id: str):
    return await call_llm(prompt, model_id)
```

### 3. Performance Optimizations (`cell0/engine/performance.py`)

#### Connection Pooling
```python
from cell0.engine import HTTPConnectionPool

pool = HTTPConnectionPool(
    base_url="https://api.example.com",
    max_connections=100,
    timeout=30.0,
)

# Use for requests
async with pool.get("/endpoint") as response:
    data = await response.json()
```

#### Request Coalescing
Prevent duplicate simultaneous requests:
```python
from cell0.engine import get_request_coalescer, coalesced

coalescer = get_request_coalescer()

@coalesced(coalescer)
async def fetch_expensive_data(param: str):
    return await expensive_query(param)

# Multiple simultaneous calls will be coalesced
results = await asyncio.gather(
    fetch_expensive_data("key"),
    fetch_expensive_data("key"),
    fetch_expensive_data("key"),
)
# Only one actual query executed!
```

#### Batch Processing
```python
from cell0.engine import AsyncBatchProcessor

async def process_batch(items: List[DataItem]):
    await db.bulk_insert(items)

processor = AsyncBatchProcessor(
    processor=process_batch,
    batch_size=100,
    max_wait_time=1.0,
)

await processor.start()

# Add items
await processor.add(item)
await processor.add_many(items)
```

#### Rate Limiting
```python
from cell0.engine import TokenBucketRateLimiter

limiter = TokenBucketRateLimiter(
    rate=10,  # 10 requests per second
    capacity=20,  # Burst up to 20
)

# Acquire tokens
if await limiter.acquire(tokens=1, timeout=5.0):
    await make_request()

# Or use as context manager
async with limiter:
    await make_request()
```

#### Async LRU Cache
```python
from cell0.engine import async_lru_cache

@async_lru_cache(maxsize=128, ttl=300)
async def expensive_computation(param: str):
    return await compute(param)
```

## Best Practices

### 1. Resource Management

```python
# Initialize at startup
from cell0.engine import initialize_resource_management, ResourceLimits

await initialize_resource_management(
    limits=ResourceLimits(
        max_memory_percent=80,
        max_cpu_percent=85,
    ),
)

# Register cleanup handlers
limiter = get_resource_limiter()
limiter.register_cleanup_handler(on_resource_pressure)

# Shutdown gracefully
await shutdown_resource_management()
```

### 2. Caching Strategy

```python
# Tiered caching approach

# L1: In-memory for hot data
@async_lru_cache(maxsize=1000, ttl=60)

# L2: Redis for distributed caching
redis_client = get_redis_client()

# L3: Response caching for HTTP
response_cache = get_response_cache()

# L4: Semantic caching for LLM outputs
model_cache = get_model_output_cache()
```

### 3. Performance Tuning

```python
# Connection pooling
pool = HTTPConnectionPool(
    base_url="...",
    max_connections=100,
    max_connections_per_host=10,
)

# Request coalescing for high-cardinality queries
@coalesced()
async def get_user_profile(user_id: str):
    return await db.get_user(user_id)

# Batch writes
processor = AsyncBatchProcessor(
    processor=db.bulk_insert,
    batch_size=1000,
    max_wait_time=0.5,
)
```

## Load Testing

### Running Tests

```bash
# Install dependencies
pip install -r tests/load/requirements.txt

# Run benchmark
cd tests/load
locust -f locustfile.py Cell0User -u 50 -r 5 -t 5m --headless

# Run stress test
locust -f locustfile.py StressTestUser -u 500 -r 50 -t 10m --headless

# Run soak test
locust -f locustfile.py SustainedLoadUser -u 20 -r 2 -t 1h --headless
```

### Available Scenarios

| Scenario | User Class | Purpose |
|----------|------------|---------|
| Standard | `Cell0User` | Realistic mixed traffic |
| Sustained | `SustainedLoadUser` | Stability testing |
| Burst | `BurstLoadUser` | Spike handling |
| Stress | `StressTestUser` | Breaking point |
| Benchmark | `BenchmarkChatUser` | Performance measurement |

### Test Configuration

```python
# tests/load/config.py
from tests.load.config import get_config

config = get_config("production")
print(config.THRESHOLD_CHAT_P95)  # 800ms
```

## Monitoring

### Resource Metrics

```python
monitor = get_resource_monitor()
usage = await monitor.get_current_usage()

# Export to Prometheus/Grafana
metrics = {
    "cell0_memory_percent": usage.memory_percent,
    "cell0_cpu_percent": usage.cpu_percent,
    "cell0_disk_percent": usage.disk_percent,
}
```

### Cache Metrics

```python
# Redis metrics
redis = get_redis_client()
print(redis.get_metrics())

# Response cache metrics
cache = get_response_cache()
print(cache.get_stats())

# Model output cache
cache = get_model_output_cache()
print(cache.get_stats())
```

## Troubleshooting

### High Memory Usage

1. Check resource limits:
```python
within_limits, violations = limiter.check_limits()
```

2. Review model memory:
```python
stats = get_model_manager().get_stats()
```

3. Enable aggressive cleanup:
```python
cleanup = get_disk_cleanup()
cleanup.cleanup_threshold = 75.0
```

### Slow Response Times

1. Check cache hit rates:
```python
stats = get_response_cache().get_stats()
if stats["hit_rate"] < 0.5:
    print("Consider increasing TTL")
```

2. Enable request coalescing:
```python
@coalesced()
async def slow_endpoint():
    ...
```

3. Add connection pooling:
```python
pool = get_http_pool("https://api.example.com")
```

### Redis Connection Issues

1. Check circuit breaker state:
```python
client = get_redis_client()
metrics = client.get_metrics()
print(metrics["circuit_state"])
```

2. Verify health:
```python
health = await client.health_check()
```

## Configuration Reference

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `CELL0_MAX_MEMORY_PERCENT` | Memory limit threshold | 85 |
| `CELL0_MAX_CPU_PERCENT` | CPU limit threshold | 90 |
| `CELL0_REDIS_HOST` | Redis server host | localhost |
| `CELL0_REDIS_PORT` | Redis server port | 6379 |
| `CELL0_CACHE_TTL` | Default cache TTL (seconds) | 300 |

### File Locations

```
cell0/
├── engine/
│   ├── resource_limits.py    # Resource management
│   ├── performance.py        # Performance optimizations
│   └── cache/
│       ├── __init__.py
│       ├── redis_client.py   # Redis wrapper
│       ├── response_cache.py # HTTP caching
│       ├── search_cache.py   # Search caching
│       └── model_output_cache.py # LLM caching
└── tests/
    └── load/
        ├── locustfile.py     # Load tests
        ├── config.py         # Test config
        └── README.md         # Load test docs
```