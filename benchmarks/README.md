# Cell 0 OS Live Benchmarks

This directory contains **live benchmark suites** that measure real runtime performance of the Cell 0 OS using actual API calls, real provider switching, and live system operations.

> ⚠️ **WARNING**: These benchmarks make REAL API calls to external services. Costs will be incurred. Monitor your API quotas and spending carefully.

## Overview

Unlike the simulated benchmarks (which use `asyncio.sleep()` to approximate latencies), the live benchmarks:

1. **Make real API calls** to search providers (Brave, Google, Bing)
2. **Actually switch providers** during failover tests
3. **Measure true end-to-end latency** including network RTT
4. **Track real token usage** and calculate actual costs
5. **Test real failure scenarios** like timeouts and rate limits

## Files

| File | Purpose | API Calls |
|------|---------|-----------|
| `latency_test_live.py` | Real latency measurements | Yes |
| `failover_test_live.py` | Real failover/recovery testing | Yes |
| `cost_analysis_live.py` | Real cost tracking | Yes |
| `latency_test.py` | Simulated latency (legacy) | No |
| `failover_test.py` | Simulated failover (legacy) | No |
| `cost_analysis.py` | Simulated costs (legacy) | No |

## Quick Start

### Prerequisites

```bash
# Install dependencies
cd /Users/yigremgetachewtamiru/.openclaw/workspace/cell0
source venv/bin/activate
pip install -r requirements.txt

# Set API keys (required for live benchmarks)
export BRAVE_API_KEY="your_key_here"
export GOOGLE_SEARCH_API_KEY="your_key_here"
export BING_SEARCH_API_KEY="your_key_here"
```

### Run Live Benchmarks

```bash
# Run all live benchmarks
cd /Users/yigremgetachewtamiru/.openclaw/workspace/benchmarks

# 1. Latency benchmark
python latency_test_live.py

# 2. Failover benchmark
python failover_test_live.py

# 3. Cost analysis
python cost_analysis_live.py
```

## Methodology

### 1. Latency Testing (`latency_test_live.py`)

#### What We Measure
- **Real API latency**: Time from request to response
- **Provider switching**: Time to failover between providers
- **Agent operations**: Registration, heartbeat, routing
- **Memory I/O**: Actual file system operations

#### Test Parameters
- **Iterations**: 20 calls per operation (default)
- **Warmup**: 3 calls to prime connections
- **Cooldown**: 100ms between calls to avoid rate limits

#### Operations Tested

```python
web_search_brave      # Brave Search API calls
web_search_google     # Google Search API calls
provider_switch       # Automatic failover between providers
agent_registration    # Register/unregister agents
capability_lookup     # Search agent registry
message_routing       # Route messages between agents
memory_read           # File read operations
memory_write          # File write operations
```

#### Output Example

```
📊 LIVE LATENCY BENCHMARK RESULTS
====================================================================================================
Operation                 P50 (ms)   P95 (ms)   P99 (ms)   Mean       Success   
----------------------------------------------------------------------------------------------------
web_search_brave          245.32     412.15     523.88     267.45     100.0%
web_search_google         198.45     356.22     445.12     215.33     100.0%
provider_switch           312.55     489.33     601.22     334.12     95.0%
agent_registration        12.45      28.33      35.12      15.22      100.0%
...
```

### 2. Failover Testing (`failover_test_live.py`)

#### What We Test
- **Provider timeouts**: Primary times out, fallback activates
- **API errors**: 5xx errors trigger failover
- **Rate limiting**: 429 responses handled gracefully
- **Network partitions**: Connection failures recovered
- **Circuit breakers**: Repeated failures open circuit

#### Failure Scenarios

| Scenario | Trigger | Expected Recovery |
|----------|---------|-------------------|
| Provider Timeout | 1ms socket timeout | <5s failover |
| Provider Error | HTTP 500/503 | <3s failover |
| Rate Limit | HTTP 429 | <2s failover |
| Network Partition | Invalid domain | <4s failover |
| Circuit Open | 10 rapid failures | <1s rejection |

#### Measurement
```python
detection_time    # Time to detect failure
failover_time     # Time to switch to fallback
total_recovery    # End-to-end recovery time
success_rate      # % of successful failovers
```

#### Output Example

```
📊 LIVE FAILOVER RECOVERY RESULTS
--------------------------------------------------------------------------------------------------------------
Failure Type         Target     Detect     Failover   Total      Success %  SLA   
--------------------------------------------------------------------------------------------------------------
provider_timeout     5000       15.2       245.3      312.5      100.0%     ✅    ✅
provider_error       3000       8.5        125.4      198.2      100.0%     ✅    ✅
rate_limit           2000       5.2        89.3       145.8      100.0%     ✅    ✅
...
```

### 3. Cost Analysis (`cost_analysis_live.py`)

#### What We Track
- **Actual token usage** from API responses
- **Real API call costs** per provider
- **Cost by operation type** (search, agent, skill, COL)
- **Cost by model tier** (FAST, BALANCED, POWER)

#### Pricing Model

| Tier | Input ($/1M tokens) | Output ($/1M tokens) | Example Models |
|------|--------------------|---------------------|----------------|
| FAST | $0.15 | $0.60 | GPT-4o-mini, Claude Haiku |
| BALANCED | $2.50 | $10.00 | GPT-4o, Claude Sonnet |
| POWER | $10.00 | $30.00 | GPT-4 Turbo, Claude Opus |

#### Search API Pricing

| Provider | Cost per 1000 calls | Free Tier |
|----------|-------------------|-----------|
| Brave | $3.00 | 2000/month |
| Google | $5.00 | None |
| Bing | $7.00 | None |

#### Token Estimation
Since search APIs don't return token counts, we estimate:

```python
prompt_tokens = len(query) // 4 + overhead
completion_tokens = len(results_json) // 4
```

#### Output Example

```
📊 LIVE COST BREAKDOWN BY OPERATION
====================================================================================================
Operation                    Tier       Tokens     Cost (USD)     Latency      $/1K ops    
----------------------------------------------------------------------------------------------------
search_brave                 fast       1250       $0.00000234    245.3        $0.0023
agent_registration           fast       600        $0.00000012    12.4         $0.0001
skill_code_review            power      6500       $0.00009500    5234.1       $0.0950
col_reasoning                power      7000       $0.00010000    8123.4       $0.1000
...

📅 PROJECTED MONTHLY COSTS (Based on Live Measurements)
--------------------------------------------------------------------------------
Usage        Searches     Agent Ops    Skills       COL          Monthly     
--------------------------------------------------------------------------------
Light        100          50           30           20           $12.45
Medium       1000         300          200          100          $124.50
Heavy        10000        2000         1000         500          $1,245.00
Enterprise   100000       15000        5000         2000         $12,450.00
```

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Live Benchmark Suite                     │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────┐ │
│  │ Latency Test    │  │ Failover Test   │  │ Cost Test   │ │
│  │                 │  │                 │  │             │ │
│  │ • Search APIs   │  │ • Provider      │  │ • Token     │ │
│  │ • Agent ops     │  │   failover      │  │   counting  │ │
│  │ • Memory I/O    │  │ • Circuit       │  │ • Pricing   │ │
│  │                 │  │   breaker       │  │   calc      │ │
│  └────────┬────────┘  └────────┬────────┘  └──────┬──────┘ │
│           │                    │                   │        │
│           └────────────────────┼───────────────────┘        │
│                                │                            │
│                     ┌──────────▼──────────┐                 │
│                     │  Cell 0 OS Engine   │                 │
│                     │                     │                 │
│                     │  ┌───────────────┐  │                 │
│                     │  │ Agent Coord   │  │                 │
│                     │  └───────────────┘  │                 │
│                     │  ┌───────────────┐  │                 │
│                     │  │ Search Tools  │  │                 │
│                     │  └───────────────┘  │                 │
│                     │  ┌───────────────┐  │                 │
│                     │  │ Skill Mgr     │  │                 │
│                     │  └───────────────┘  │                 │
│                     └──────────┬──────────┘                 │
│                                │                            │
│           ┌────────────────────┼───────────────────┐        │
│           │                    │                   │        │
│  ┌────────▼────────┐  ┌────────▼────────┐  ┌──────▼──────┐ │
│  │ Brave Search    │  │ Google Search   │  │ Bing Search │ │
│  │ API             │  │ API             │  │ API         │ │
│  └─────────────────┘  └─────────────────┘  └─────────────┘ │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## Comparison: Simulated vs Live

| Aspect | Simulated | Live |
|--------|-----------|------|
| **API Calls** | No | Yes |
| **Network Latency** | Simulated | Real |
| **Provider Failures** | Random sleep | Actual HTTP errors |
| **Cost Tracking** | Estimated | Real pricing |
| **Reproducibility** | Deterministic | Varies by network |
| **Runtime** | Fast (~seconds) | Slower (~minutes) |
| **Cost** | Free | Incurs API charges |
| **Credibility** | Low | High |

## Best Practices

### Before Running

1. **Check API quotas**
   ```bash
   # Verify you have sufficient quota
   echo "Brave: Check at https://api.search.brave.com/"
   ```

2. **Set spending limits**
   ```bash
   # Most providers allow setting limits
   export MAX_BENCHMARK_COST_USD=10.00
   ```

3. **Start small**
   ```python
   # Use fewer iterations for testing
   benchmark = LiveLatencyBenchmark(iterations=5, warmup=1)
   ```

### During Execution

1. **Monitor logs**
   - Watch for rate limit warnings
   - Check for connection errors

2. **Track costs**
   - Export results frequently
   - Compare against budget

3. **Handle failures gracefully**
   - Benchmarks continue on errors
   - Success rates reported

### After Completion

1. **Review results**
   - Check P95 vs SLA targets
   - Verify failover success rates
   - Validate cost projections

2. **Archive results**
   ```bash
   # Version your benchmarks
   cp benchmarks/latency_results_live.json \
      benchmarks/history/latency_$(date +%Y%m%d).json
   ```

## Troubleshooting

### Import Errors

```bash
# Ensure you're in the right directory
cd /Users/yigremgetachewtamiru/.openclaw/workspace/cell0
source venv/bin/activate

# Add to PYTHONPATH
export PYTHONPATH="/Users/yigremgetachewtamiru/.openclaw/workspace:$PYTHONPATH"
```

### API Key Errors

```bash
# Verify keys are set
echo $BRAVE_API_KEY

# If empty, set them
export BRAVE_API_KEY="your_actual_key"
```

### Rate Limiting

If you hit rate limits:

1. Increase cooldown between calls
2. Reduce iterations
3. Use caching (`use_cache=True`)
4. Stagger benchmark runs

```python
# Add delay between iterations
await asyncio.sleep(1.0)  # Increase from 0.1
```

## Contributing

When adding new live benchmarks:

1. **Document API requirements**
2. **Include cost estimates**
3. **Add error handling**
4. **Update this README**

## License

Part of Cell 0 OS - See main LICENSE file.

## References

- [Brave Search API Docs](https://api.search.brave.com/)
- [Google Custom Search](https://developers.google.com/custom-search)
- [Bing Web Search API](https://www.microsoft.com/en-us/bing/apis/bing-web-search-api)
- Cell 0 OS Architecture Docs (`/docs/architecture/`)
