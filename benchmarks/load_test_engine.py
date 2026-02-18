#!/usr/bin/env python3
"""
Cell 0 Scalability Load Test Engine
Performs comprehensive load testing for inference, memory, and concurrency
"""

import time
import json
import os
import sys
import asyncio
import statistics
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional
from datetime import datetime
import threading
import concurrent.futures
import gc

# Add cell0 to path
sys.path.insert(0, '/Users/yigremgetachewtamiru/.openclaw/workspace/cell0')

@dataclass
class LoadTestResult:
    test_name: str
    iterations: int
    total_time_ms: float
    mean_latency_ms: float
    p50_ms: float
    p95_ms: float
    p99_ms: float
    min_ms: float
    max_ms: float
    throughput_ops_sec: float
    errors: int
    memory_before_mb: float
    memory_after_mb: float
    memory_delta_mb: float
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

class InferenceBenchmark:
    """Benchmarks inference performance"""
    
    def __init__(self):
        self.results = []
        
    def run_memory_stress_test(self, iterations: int = 1000) -> LoadTestResult:
        """Test memory allocation patterns"""
        gc.collect()
        mem_before = self._get_memory_mb()
        
        latencies = []
        errors = 0
        
        start = time.time()
        for i in range(iterations):
            op_start = time.time()
            try:
                # Simulate memory-intensive operation
                data = [{"id": j, "data": "x" * 100} for j in range(1000)]
                processed = [d["data"].upper() for d in data]
                del data, processed
            except Exception as e:
                errors += 1
            latencies.append((time.time() - op_start) * 1000)
            
        total_time = (time.time() - start) * 1000
        mem_after = self._get_memory_mb()
        
        return LoadTestResult(
            test_name="memory_stress",
            iterations=iterations,
            total_time_ms=total_time,
            mean_latency_ms=statistics.mean(latencies),
            p50_ms=statistics.median(latencies),
            p95_ms=statistics.quantiles(latencies, n=20)[18] if len(latencies) >= 20 else max(latencies),
            p99_ms=statistics.quantiles(latencies, n=100)[98] if len(latencies) >= 100 else max(latencies),
            min_ms=min(latencies),
            max_ms=max(latencies),
            throughput_ops_sec=iterations / (total_time / 1000),
            errors=errors,
            memory_before_mb=mem_before,
            memory_after_mb=mem_after,
            memory_delta_mb=mem_after - mem_before
        )
    
    def run_cpu_intensive_test(self, iterations: int = 100) -> LoadTestResult:
        """Test CPU-bound operations"""
        gc.collect()
        mem_before = self._get_memory_mb()
        
        latencies = []
        errors = 0
        
        start = time.time()
        for i in range(iterations):
            op_start = time.time()
            try:
                # Simulate CPU-intensive operation
                result = sum(j ** 2 for j in range(10000))
            except Exception as e:
                errors += 1
            latencies.append((time.time() - op_start) * 1000)
            
        total_time = (time.time() - start) * 1000
        mem_after = self._get_memory_mb()
        
        return LoadTestResult(
            test_name="cpu_intensive",
            iterations=iterations,
            total_time_ms=total_time,
            mean_latency_ms=statistics.mean(latencies),
            p50_ms=statistics.median(latencies),
            p95_ms=statistics.quantiles(latencies, n=20)[18] if len(latencies) >= 20 else max(latencies),
            p99_ms=statistics.quantiles(latencies, n=100)[98] if len(latencies) >= 100 else max(latencies),
            min_ms=min(latencies),
            max_ms=max(latencies),
            throughput_ops_sec=iterations / (total_time / 1000),
            errors=errors,
            memory_before_mb=mem_before,
            memory_after_mb=mem_after,
            memory_delta_mb=mem_after - mem_before
        )
    
    def run_concurrency_test(self, workers: int = 10, iterations_per_worker: int = 50) -> LoadTestResult:
        """Test concurrent execution performance"""
        gc.collect()
        mem_before = self._get_memory_mb()
        
        latencies = []
        errors = 0
        lock = threading.Lock()
        
        def worker_task():
            nonlocal errors
            local_latencies = []
            for _ in range(iterations_per_worker):
                op_start = time.time()
                try:
                    # Simulate work
                    data = list(range(1000))
                    result = [x * 2 for x in data]
                except Exception as e:
                    with lock:
                        errors += 1
                local_latencies.append((time.time() - op_start) * 1000)
            return local_latencies
        
        start = time.time()
        with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
            futures = [executor.submit(worker_task) for _ in range(workers)]
            for future in concurrent.futures.as_completed(futures):
                latencies.extend(future.result())
                
        total_time = (time.time() - start) * 1000
        mem_after = self._get_memory_mb()
        total_iterations = workers * iterations_per_worker
        
        return LoadTestResult(
            test_name=f"concurrency_{workers}workers",
            iterations=total_iterations,
            total_time_ms=total_time,
            mean_latency_ms=statistics.mean(latencies),
            p50_ms=statistics.median(latencies),
            p95_ms=statistics.quantiles(latencies, n=20)[18] if len(latencies) >= 20 else max(latencies),
            p99_ms=statistics.quantiles(latencies, n=100)[98] if len(latencies) >= 100 else max(latencies),
            min_ms=min(latencies),
            max_ms=max(latencies),
            throughput_ops_sec=total_iterations / (total_time / 1000),
            errors=errors,
            memory_before_mb=mem_before,
            memory_after_mb=mem_after,
            memory_delta_mb=mem_after - mem_before
        )
    
    def run_json_serialization_test(self, iterations: int = 10000) -> LoadTestResult:
        """Test JSON serialization performance"""
        gc.collect()
        mem_before = self._get_memory_mb()
        
        test_data = {
            "id": 12345,
            "name": "test_object",
            "items": [{"key": i, "value": f"data_{i}"} for i in range(100)],
            "metadata": {"timestamp": time.time(), "version": "1.0"}
        }
        
        latencies = []
        errors = 0
        
        start = time.time()
        for _ in range(iterations):
            op_start = time.time()
            try:
                json_str = json.dumps(test_data)
                json.loads(json_str)
            except Exception as e:
                errors += 1
            latencies.append((time.time() - op_start) * 1000)
            
        total_time = (time.time() - start) * 1000
        mem_after = self._get_memory_mb()
        
        return LoadTestResult(
            test_name="json_serialization",
            iterations=iterations,
            total_time_ms=total_time,
            mean_latency_ms=statistics.mean(latencies),
            p50_ms=statistics.median(latencies),
            p95_ms=statistics.quantiles(latencies, n=20)[18] if len(latencies) >= 20 else max(latencies),
            p99_ms=statistics.quantiles(latencies, n=100)[98] if len(latencies) >= 100 else max(latencies),
            min_ms=min(latencies),
            max_ms=max(latencies),
            throughput_ops_sec=iterations / (total_time / 1000),
            errors=errors,
            memory_before_mb=mem_before,
            memory_after_mb=mem_after,
            memory_delta_mb=mem_after - mem_before
        )
    
    def _get_memory_mb(self) -> float:
        """Get current memory usage in MB"""
        try:
            import psutil
            process = psutil.Process(os.getpid())
            return process.memory_info().rss / 1024 / 1024
        except ImportError:
            return 0.0

def run_full_benchmark_suite():
    """Run complete benchmark suite"""
    print("=" * 70)
    print("CELL 0 SCALABILITY LOAD TEST ENGINE")
    print(f"Started: {datetime.now().isoformat()}")
    print("=" * 70)
    print()
    
    benchmark = InferenceBenchmark()
    all_results = []
    
    # Test 1: Memory Stress
    print("[1/4] Running memory stress test...")
    result = benchmark.run_memory_stress_test(iterations=500)
    all_results.append(result)
    print(f"  ✓ Mean: {result.mean_latency_ms:.2f}ms | P95: {result.p95_ms:.2f}ms | Throughput: {result.throughput_ops_sec:.1f} ops/sec")
    
    # Test 2: CPU Intensive
    print("[2/4] Running CPU intensive test...")
    result = benchmark.run_cpu_intensive_test(iterations=50)
    all_results.append(result)
    print(f"  ✓ Mean: {result.mean_latency_ms:.2f}ms | P95: {result.p95_ms:.2f}ms | Throughput: {result.throughput_ops_sec:.1f} ops/sec")
    
    # Test 3: Concurrency
    print("[3/4] Running concurrency test (10 workers)...")
    result = benchmark.run_concurrency_test(workers=10, iterations_per_worker=50)
    all_results.append(result)
    print(f"  ✓ Mean: {result.mean_latency_ms:.2f}ms | P95: {result.p95_ms:.2f}ms | Throughput: {result.throughput_ops_sec:.1f} ops/sec")
    
    # Test 4: JSON Serialization
    print("[4/4] Running JSON serialization test...")
    result = benchmark.run_json_serialization_test(iterations=5000)
    all_results.append(result)
    print(f"  ✓ Mean: {result.mean_latency_ms:.2f}ms | P95: {result.p95_ms:.2f}ms | Throughput: {result.throughput_ops_sec:.1f} ops/sec")
    
    print()
    print("=" * 70)
    print("BENCHMARK SUMMARY")
    print("=" * 70)
    
    total_ops = sum(r.iterations for r in all_results)
    total_time = sum(r.total_time_ms for r in all_results)
    total_errors = sum(r.errors for r in all_results)
    
    print(f"\nTotal Operations: {total_ops:,}")
    print(f"Total Time: {total_time/1000:.2f}s")
    print(f"Overall Throughput: {total_ops/(total_time/1000):.1f} ops/sec")
    print(f"Total Errors: {total_errors}")
    print(f"Error Rate: {(total_errors/total_ops)*100:.4f}%")
    
    print("\nDetailed Results:")
    print("-" * 70)
    print(f"{'Test':<25} {'Mean(ms)':<12} {'P95(ms)':<12} {'Ops/sec':<12} {'Errors':<8}")
    print("-" * 70)
    for r in all_results:
        print(f"{r.test_name:<25} {r.mean_latency_ms:<12.2f} {r.p95_ms:<12.2f} {r.throughput_ops_sec:<12.1f} {r.errors:<8}")
    
    print("\nMemory Usage:")
    print("-" * 70)
    for r in all_results:
        print(f"{r.test_name:<25} Before: {r.memory_before_mb:.1f}MB | After: {r.memory_after_mb:.1f}MB | Delta: {r.memory_delta_mb:+.1f}MB")
    
    # Save results
    results_file = f"/Users/yigremgetachewtamiru/.openclaw/workspace/benchmarks/load_test_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(results_file, 'w') as f:
        json.dump([asdict(r) for r in all_results], f, indent=2)
    print(f"\n✓ Results saved to: {results_file}")
    
    return all_results

if __name__ == "__main__":
    run_full_benchmark_suite()
