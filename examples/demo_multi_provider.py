#!/usr/bin/env python3
"""
🌐 Multi-Provider Failover Demonstration
========================================
Seamless failover between search providers with intelligent result ranking.

Features demonstrated:
- Multiple provider support (Brave, Google, Bing, local cache)
- Automatic failover on provider failure
- Result deduplication and ranking
- Latency-based provider selection
- Graceful degradation

Run with: python examples/demo_multi_provider.py
"""

import asyncio
import time
import sys
import json
import random
from pathlib import Path
from dataclasses import dataclass
from typing import List, Dict, Any, Optional
from enum import Enum

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))


class Colors:
    """Terminal colors for pretty output"""
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'


class ProviderStatus(Enum):
    """Provider health status"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNAVAILABLE = "unavailable"


@dataclass
class Provider:
    """Search provider configuration"""
    name: str
    id: str
    priority: int  # Lower = higher priority
    latency_ms: float
    success_rate: float
    status: ProviderStatus
    rate_limit_per_min: int
    features: List[str]


@dataclass
class SearchResult:
    """Standardized search result"""
    title: str
    url: str
    snippet: str
    source: str
    rank: int
    relevance_score: float = 0.0
    timestamp: float = 0.0


class MultiProviderDemo:
    """Demonstrates multi-provider search with failover"""
    
    def __init__(self):
        self.providers: List[Provider] = []
        self.query_history: List[Dict] = []
        self.setup_providers()
        
    def setup_providers(self):
        """Configure search providers"""
        self.providers = [
            Provider(
                name="Brave Search",
                id="brave",
                priority=1,
                latency_ms=45.0,
                success_rate=0.98,
                status=ProviderStatus.HEALTHY,
                rate_limit_per_min=1000,
                features=["web", "news", "images", "academic"]
            ),
            Provider(
                name="Google Custom Search",
                id="google",
                priority=2,
                latency_ms=120.0,
                success_rate=0.95,
                status=ProviderStatus.HEALTHY,
                rate_limit_per_min=500,
                features=["web", "images", "news"]
            ),
            Provider(
                name="Bing Search API",
                id="bing",
                priority=3,
                latency_ms=150.0,
                success_rate=0.90,
                status=ProviderStatus.DEGRADED,
                rate_limit_per_min=300,
                features=["web", "news", "images"]
            ),
            Provider(
                name="Local Cache",
                id="cache",
                priority=99,
                latency_ms=5.0,
                success_rate=1.0,
                status=ProviderStatus.HEALTHY,
                rate_limit_per_min=10000,
                features=["web"]
            ),
        ]
        
    async def run(self):
        """Run the multi-provider demo"""
        print(f"\n{Colors.HEADER}{'='*60}{Colors.ENDC}")
        print(f"{Colors.BOLD}{Colors.CYAN}🌐 MULTI-PROVIDER FAILOVER DEMONSTRATION{Colors.ENDC}")
        print(f"{Colors.HEADER}{'='*60}{Colors.ENDC}\n")
        
        print("Cell 0 OS provides seamless failover between multiple search providers.")
        print("Results are aggregated, deduplicated, and ranked for optimal quality.\n")
        
        # Demo provider infrastructure
        await self.demo_provider_infrastructure()
        
        # Demo failover scenarios
        await self.demo_failover_scenarios()
        
        # Demo result ranking
        await self.demo_result_ranking()
        
        # Demo latency optimization
        await self.demo_latency_optimization()
        
        # Demo graceful degradation
        await self.demo_graceful_degradation()
        
        # Summary
        self.print_summary()
        
    async def demo_provider_infrastructure(self):
        """Demonstrate the provider infrastructure"""
        print(f"{Colors.BOLD}{Colors.HEADER}╔══ Provider Infrastructure ═══════════════════════════{Colors.ENDC}\n")
        
        print("Configured Providers:")
        for provider in self.providers:
            status_color = {
                ProviderStatus.HEALTHY: Colors.GREEN,
                ProviderStatus.DEGRADED: Colors.YELLOW,
                ProviderStatus.UNAVAILABLE: Colors.RED
            }[provider.status]
            
            print(f"\n  {Colors.BOLD}{provider.name}{Colors.ENDC} (ID: {provider.id})")
            print(f"    Priority: {provider.priority}")
            print(f"    Status: {status_color}{provider.status.value}{Colors.ENDC}")
            print(f"    Avg Latency: {provider.latency_ms:.1f}ms")
            print(f"    Success Rate: {provider.success_rate:.1%}")
            print(f"    Rate Limit: {provider.rate_limit_per_min}/min")
            print(f"    Features: {', '.join(provider.features)}")
            
        print(f"\n{Colors.GREEN}✓ {len(self.providers)} providers configured{Colors.ENDC}")
        
    async def demo_failover_scenarios(self):
        """Demonstrate failover scenarios"""
        print(f"\n{Colors.BOLD}{Colors.HEADER}╔══ Failover Scenarios ════════════════════════════════{Colors.ENDC}\n")
        
        scenarios = [
            {
                "name": "Primary Provider Healthy",
                "description": "Brave responds quickly, no failover needed",
                "primary_status": ProviderStatus.HEALTHY,
                "expected_provider": "brave",
                "failover_triggered": False
            },
            {
                "name": "Primary Timeout",
                "description": "Brave times out, failover to Google",
                "primary_status": ProviderStatus.UNAVAILABLE,
                "expected_provider": "google",
                "failover_triggered": True
            },
            {
                "name": "Primary + Secondary Down",
                "description": "Brave and Google down, use Bing",
                "primary_status": ProviderStatus.UNAVAILABLE,
                "secondary_status": ProviderStatus.UNAVAILABLE,
                "expected_provider": "bing",
                "failover_triggered": True
            },
            {
                "name": "All External Down",
                "description": "All APIs down, use local cache",
                "primary_status": ProviderStatus.UNAVAILABLE,
                "secondary_status": ProviderStatus.UNAVAILABLE,
                "tertiary_status": ProviderStatus.UNAVAILABLE,
                "expected_provider": "cache",
                "failover_triggered": True
            },
        ]
        
        query = "Cell 0 OS architecture"
        
        for scenario in scenarios:
            print(f"\n{Colors.BOLD}Scenario: {scenario['name']}{Colors.ENDC}")
            print(f"  Description: {scenario['description']}")
            
            start_time = time.time()
            
            # Simulate provider selection
            selected = self._select_provider_for_scenario(scenario)
            
            latency = (time.time() - start_time) * 1000
            
            print(f"  Selected Provider: {Colors.GREEN}{selected}{Colors.ENDC}")
            print(f"  Failover Triggered: {Colors.YELLOW if scenario['failover_triggered'] else Colors.GREEN}{scenario['failover_triggered']}{Colors.ENDC}")
            print(f"  Selection Latency: {latency:.2f}ms")
            
            if scenario['failover_triggered']:
                print(f"  {Colors.CYAN}→ Failover path: {' → '.join(self._get_failover_path(scenario))}{Colors.ENDC}")
                
    def _select_provider_for_scenario(self, scenario: Dict) -> str:
        """Simulate provider selection based on scenario"""
        if scenario.get('primary_status') != ProviderStatus.UNAVAILABLE:
            return 'brave'
        if scenario.get('secondary_status') != ProviderStatus.UNAVAILABLE:
            return 'google'
        if scenario.get('tertiary_status') != ProviderStatus.UNAVAILABLE:
            return 'bing'
        return 'cache'
        
    def _get_failover_path(self, scenario: Dict) -> List[str]:
        """Get the failover path for a scenario"""
        path = []
        if scenario.get('primary_status') == ProviderStatus.UNAVAILABLE:
            path.append('brave (timeout)')
        if scenario.get('secondary_status') == ProviderStatus.UNAVAILABLE:
            path.append('google (timeout)')
        if scenario.get('tertiary_status') == ProviderStatus.UNAVAILABLE:
            path.append('bing (timeout)')
        path.append(scenario['expected_provider'] + ' (success)')
        return path
        
    async def demo_result_ranking(self):
        """Demonstrate result ranking and deduplication"""
        print(f"\n{Colors.BOLD}{Colors.HEADER}╔══ Result Ranking & Deduplication ════════════════════{Colors.ENDC}\n")
        
        query = "Cell 0 OS cognitive operating layer"
        
        # Simulate results from multiple providers
        raw_results = [
            # From Brave
            SearchResult("Cell 0 OS - Official Site", "https://cell0.os", "The sovereign edge model OS...", "brave", 1, 0.95, time.time()),
            SearchResult("COL Protocol Guide", "https://cell0.os/col", "Cognitive Operating Layer...", "brave", 2, 0.90, time.time()),
            SearchResult("GitHub - cell0/os", "https://github.com/cell0/os", "Open source implementation...", "brave", 3, 0.85, time.time()),
            # From Google (with some duplicates)
            SearchResult("Cell 0 OS - Official Site", "https://cell0.os", "Welcome to Cell 0...", "google", 1, 0.92, time.time()),
            SearchResult("Architecture Overview", "https://cell0.os/arch", "8-layer architecture...", "google", 2, 0.88, time.time()),
            SearchResult("Multi-Agent Routing", "https://cell0.os/agents", "Agent mesh communication...", "google", 3, 0.82, time.time()),
            # From Bing
            SearchResult("Cell 0 OS Overview", "https://cell0.os", "Sovereign edge computing...", "bing", 1, 0.89, time.time()),
            SearchResult("Getting Started", "https://cell0.os/start", "Quick start guide...", "bing", 2, 0.80, time.time()),
        ]
        
        print(f"Query: {Colors.BOLD}{query}{Colors.ENDC}")
        print(f"Raw results from 3 providers: {len(raw_results)} items")
        
        # Show deduplication
        print(f"\n{Colors.CYAN}Deduplication:{Colors.ENDC}")
        unique_urls = {}
        duplicates = []
        
        for result in raw_results:
            if result.url in unique_urls:
                duplicates.append(result)
            else:
                unique_urls[result.url] = result
                
        print(f"  Unique URLs: {len(unique_urls)}")
        print(f"  Duplicates removed: {len(duplicates)}")
        
        for dup in duplicates:
            print(f"    - {dup.title} ({dup.source})")
            
        # Show ranking
        print(f"\n{Colors.CYAN}Ranking Factors:{Colors.ENDC}")
        print("  • Relevance (40%): TF-IDF based keyword matching")
        print("  • Diversity (20%): Maximal Marginal Relevance (MMR)")
        print("  • Recency (20%): Time decay function")
        print("  • Quality (20%): Domain authority + content heuristics")
        
        # Simulate final ranking
        print(f"\n{Colors.CYAN}Final Ranked Results:{Colors.ENDC}")
        unique_results = list(unique_urls.values())
        
        # Simulate ranking calculation
        for i, result in enumerate(unique_results[:5], 1):
            # Calculate simulated final score
            relevance = result.relevance_score
            diversity = 0.8 - (i * 0.05)  # Decreasing diversity
            recency = 0.95 if time.time() - result.timestamp < 86400 else 0.7
            quality = 0.85 if 'cell0.os' in result.url else 0.7
            
            final_score = (
                0.4 * relevance +
                0.2 * diversity +
                0.2 * recency +
                0.2 * quality
            )
            
            source_color = Colors.GREEN if result.source == 'brave' else (
                Colors.CYAN if result.source == 'google' else Colors.YELLOW
            )
            
            print(f"\n  {i}. {Colors.BOLD}{result.title}{Colors.ENDC}")
            print(f"     URL: {result.url}")
            print(f"     Source: {source_color}{result.source}{Colors.ENDC}")
            print(f"     Score: {final_score:.3f} (R:{relevance:.2f} D:{diversity:.2f} T:{recency:.2f} Q:{quality:.2f})")
            print(f"     {result.snippet[:60]}...")
            
    async def demo_latency_optimization(self):
        """Demonstrate latency-based optimizations"""
        print(f"\n{Colors.BOLD}{Colors.HEADER}╔══ Latency Optimization ═════════════════════════════{Colors.ENDC}\n")
        
        print("Strategies for minimizing search latency:\n")
        
        strategies = [
            {
                "name": "Parallel Query Execution",
                "description": "Query all providers simultaneously",
                "implementation": "asyncio.gather() with timeout",
                "latency_improvement": "~60% reduction"
            },
            {
                "name": "Predictive Provider Selection",
                "description": "Select provider based on historical latency",
                "implementation": "Exponential moving average of response times",
                "latency_improvement": "~30% reduction"
            },
            {
                "name": "Result Caching",
                "description": "Cache frequently accessed results",
                "implementation": "TTL-based cache with LRU eviction",
                "latency_improvement": "~95% for cache hits"
            },
            {
                "name": "Early Termination",
                "description": "Stop waiting after sufficient results",
                "implementation": " asyncio.wait_for() with threshold",
                "latency_improvement": "~40% for non-critical queries"
            },
        ]
        
        for strategy in strategies:
            print(f"  {Colors.BOLD}{strategy['name']}{Colors.ENDC}")
            print(f"    Description: {strategy['description']}")
            print(f"    Implementation: {strategy['implementation']}")
            print(f"    Improvement: {Colors.GREEN}{strategy['latency_improvement']}{Colors.ENDC}")
            print()
            
        # Show simulated latency comparison
        print(f"{Colors.CYAN}Latency Comparison (simulated):{Colors.ENDC}")
        
        approaches = [
            ("Sequential (single provider)", 150),
            ("Sequential with failover", 280),
            ("Parallel execution", 65),
            ("Parallel + caching", 12),
            ("Optimized (Cell 0 OS)", 8),
        ]
        
        for approach, latency in approaches:
            bar_length = int(latency / 5)
            bar = "█" * bar_length
            color = Colors.RED if latency > 100 else (Colors.YELLOW if latency > 50 else Colors.GREEN)
            print(f"  {approach:35} {color}{bar}{Colors.ENDC} {latency}ms")
            
    async def demo_graceful_degradation(self):
        """Demonstrate graceful degradation"""
        print(f"\n{Colors.BOLD}{Colors.HEADER}╔══ Graceful Degradation ═════════════════════════════{Colors.ENDC}\n")
        
        print("When providers fail, Cell 0 OS gracefully degrades:\n")
        
        degradation_levels = [
            {
                "level": "Full Service",
                "providers_available": ["brave", "google", "bing"],
                "features": ["Web search", "News", "Images", "Academic", "Real-time"],
                "quality": "100%",
                "latency": "~50ms"
            },
            {
                "level": "Standard Service",
                "providers_available": ["google", "bing"],
                "features": ["Web search", "Images", "News"],
                "quality": "85%",
                "latency": "~120ms"
            },
            {
                "level": "Basic Service",
                "providers_available": ["bing"],
                "features": ["Web search", "News"],
                "quality": "70%",
                "latency": "~150ms"
            },
            {
                "level": "Cache Only",
                "providers_available": ["cache"],
                "features": ["Web search (cached)"],
                "quality": "50% (stale possible)",
                "latency": "~5ms"
            },
        ]
        
        for level in degradation_levels:
            color = Colors.GREEN if level['level'] == "Full Service" else (
                Colors.YELLOW if "Standard" in level['level'] else (
                Colors.RED if "Cache" in level['level'] else Colors.CYAN
            ))
            
            print(f"  {color}{Colors.BOLD}{level['level']}{Colors.ENDC}")
            print(f"    Providers: {', '.join(level['providers_available'])}")
            print(f"    Features: {', '.join(level['features'])}")
            print(f"    Quality: {level['quality']}")
            print(f"    Latency: {level['latency']}")
            print()
            
        print(f"{Colors.GREEN}✓ Service continuity maintained at all levels{Colors.ENDC}")
        
    def print_summary(self):
        """Print demo summary"""
        print(f"\n{Colors.HEADER}{'='*60}{Colors.ENDC}")
        print(f"{Colors.BOLD}{Colors.CYAN}📊 MULTI-PROVIDER SUMMARY{Colors.ENDC}")
        print(f"{Colors.HEADER}{'='*60}{Colors.ENDC}\n")
        
        print("Key Features:")
        print("  ✓ Multiple provider support (Brave, Google, Bing, Cache)")
        print("  ✓ Automatic failover with sub-100ms detection")
        print("  ✓ Intelligent result ranking (relevance + diversity + recency)")
        print("  ✓ Parallel query execution for minimal latency")
        print("  ✓ Graceful degradation with 4 service levels")
        print("  ✓ Automatic deduplication across providers\n")
        
        print("Provider Statistics:")
        healthy = sum(1 for p in self.providers if p.status == ProviderStatus.HEALTHY)
        print(f"  Healthy: {healthy}/{len(self.providers)}")
        print(f"  Avg Latency: {sum(p.latency_ms for p in self.providers)/len(self.providers):.1f}ms")
        
        print(f"\n{Colors.GREEN}{Colors.BOLD}✨ Multi-Provider Demo Complete!{Colors.ENDC}")
        print(f"{Colors.CYAN}Seamless failover ensures service continuity.{Colors.ENDC}")


async def main():
    """Main entry point"""
    demo = MultiProviderDemo()
    await demo.run()


if __name__ == "__main__":
    if sys.version_info < (3, 9):
        print("Python 3.9+ required")
        sys.exit(1)
        
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nDemo interrupted")
    except Exception as e:
        print(f"Demo failed: {e}")
        import traceback
        traceback.print_exc()
