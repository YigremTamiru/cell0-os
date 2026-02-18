#!/usr/bin/env python3
"""
Cell 0 OS - Latency Benchmark Suite
Measures P95 latency for various COL operations
"""

import asyncio
import time
import statistics
from dataclasses import dataclass
from typing import List, Callable, Optional
import json
from datetime import datetime


@dataclass
class LatencyResult:
    operation: str
    samples: List[float]
    p50: float
    p95: float
    p99: float
    min_ms: float
    max_ms: float
    mean: float
    std_dev: float
    timestamp: str


class LatencyBenchmark:
    """Benchmark P95 latency for COL operations"""
    
    def __init__(self, iterations: int = 1000):
        self.iterations = iterations
        self.results: List[LatencyResult] = []
        
    async def measure_operation(
        self, 
        name: str, 
        operation: Callable,
        warmup: int = 100
    ) -> LatencyResult:
        """Measure latency for a single operation"""
        
        # Warmup phase
        for _ in range(warmup):
            await operation()
        
        # Actual measurement
        samples = []
        for _ in range(self.iterations):
            start = time.perf_counter()
            await operation()
            elapsed = (time.perf_counter() - start) * 1000  # Convert to ms
            samples.append(elapsed)
        
        samples.sort()
        n = len(samples)
        
        result = LatencyResult(
            operation=name,
            samples=samples,
            p50=samples[int(n * 0.5)],
            p95=samples[int(n * 0.95)],
            p99=samples[int(n * 0.99)],
            min_ms=min(samples),
            max_ms=max(samples),
            mean=statistics.mean(samples),
            std_dev=statistics.stdev(samples) if n > 1 else 0,
            timestamp=datetime.now().isoformat()
        )
        
        self.results.append(result)
        return result
    
    async def run_all(self) -> List[LatencyResult]:
        """Run complete latency benchmark suite"""
        
        print(f"🚀 Running Latency Benchmark Suite ({self.iterations} iterations)")
        print("=" * 60)
        
        # Simulate COL operations
        await self.measure_operation(
            "col_classify",
            self._simulate_classify
        )
        
        await self.measure_operation(
            "col_load",
            self._simulate_load
        )
        
        await self.measure_operation(
            "col_apply",
            self._simulate_apply
        )
        
        await self.measure_operation(
            "agent_spawn",
            self._simulate_agent_spawn
        )
        
        await self.measure_operation(
            "skill_invoke",
            self._simulate_skill_invoke
        )
        
        await self.measure_operation(
            "memory_read",
            self._simulate_memory_read
        )
        
        await self.measure_operation(
            "memory_write",
            self._simulate_memory_write
        )
        
        return self.results
    
    # Simulated operations (replace with actual COL calls)
    async def _simulate_classify(self):
        await asyncio.sleep(0.001)  # 1ms base
    
    async def _simulate_load(self):
        await asyncio.sleep(0.002)  # 2ms base
    
    async def _simulate_apply(self):
        await asyncio.sleep(0.0015)  # 1.5ms base
    
    async def _simulate_agent_spawn(self):
        await asyncio.sleep(0.050)  # 50ms base
    
    async def _simulate_skill_invoke(self):
        await asyncio.sleep(0.010)  # 10ms base
    
    async def _simulate_memory_read(self):
        await asyncio.sleep(0.0005)  # 0.5ms base
    
    async def _simulate_memory_write(self):
        await asyncio.sleep(0.001)  # 1ms base
    
    def print_results(self):
        """Print formatted results"""
        print("\n📊 LATENCY BENCHMARK RESULTS")
        print("=" * 80)
        print(f"{'Operation':<20} {'P50 (ms)':<10} {'P95 (ms)':<10} {'P99 (ms)':<10} {'Mean':<10} {'StdDev':<10}")
        print("-" * 80)
        
        for r in self.results:
            print(f"{r.operation:<20} {r.p50:<10.3f} {r.p95:<10.3f} {r.p99:<10.3f} {r.mean:<10.3f} {r.std_dev:<10.3f}")
        
        print("-" * 80)
    
    def export_json(self, path: str = "benchmarks/latency_results.json"):
        """Export results to JSON"""
        data = {
            "timestamp": datetime.now().isoformat(),
            "iterations": self.iterations,
            "results": [
                {
                    "operation": r.operation,
                    "p50_ms": r.p50,
                    "p95_ms": r.p95,
                    "p99_ms": r.p99,
                    "min_ms": r.min_ms,
                    "max_ms": r.max_ms,
                    "mean_ms": r.mean,
                    "std_dev": r.std_dev,
                    "timestamp": r.timestamp
                }
                for r in self.results
            ]
        }
        
        with open(path, 'w') as f:
            json.dump(data, f, indent=2)
        
        print(f"\n💾 Results exported to {path}")


async def main():
    benchmark = LatencyBenchmark(iterations=1000)
    await benchmark.run_all()
    benchmark.print_results()
    benchmark.export_json()


if __name__ == "__main__":
    asyncio.run(main())
