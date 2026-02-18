"""
MLX Performance Benchmarks for Cell0 AI Engine

Benchmarks Apple Silicon MLX performance including:
- Model loading times
- Inference latency
- Throughput (tokens/second)
- Memory usage
- Quantization impact
"""

import pytest
import asyncio
import time
import statistics
from typing import List, Dict, Any
from dataclasses import dataclass
from unittest.mock import Mock, patch, MagicMock

# Import AI engine
from cell0.cell0.engine.ai_engine import (
    AIEngine,
    ModelConfig,
    ModelPrecision,
    TPVResonance,
    ModelQuantizer,
    MultiModelConsensus,
    MLXModel,
    HAS_MLX,
    HAS_NUMPY,
)


@dataclass
class BenchmarkResult:
    """Benchmark result container"""
    name: str
    iterations: int
    total_time_ms: float
    avg_time_ms: float
    min_time_ms: float
    max_time_ms: float
    std_dev_ms: float
    throughput: float  # ops/sec or tokens/sec
    memory_mb: float = 0.0


class PerformanceBenchmarks:
    """MLX Performance benchmark suite"""
    
    def __init__(self):
        self.results: List[BenchmarkResult] = []
        
    def run_benchmark(
        self,
        name: str,
        func,
        iterations: int = 10,
        warmup: int = 3
    ) -> BenchmarkResult:
        """Run a benchmark function multiple times"""
        # Warmup
        for _ in range(warmup):
            func()
        
        # Actual benchmark
        times = []
        for _ in range(iterations):
            start = time.perf_counter()
            func()
            end = time.perf_counter()
            times.append((end - start) * 1000)  # Convert to ms
        
        result = BenchmarkResult(
            name=name,
            iterations=iterations,
            total_time_ms=sum(times),
            avg_time_ms=statistics.mean(times),
            min_time_ms=min(times),
            max_time_ms=max(times),
            std_dev_ms=statistics.stdev(times) if len(times) > 1 else 0,
            throughput=iterations / (sum(times) / 1000)  # ops/sec
        )
        self.results.append(result)
        return result
    
    def print_report(self):
        """Print benchmark report"""
        print("\n" + "=" * 80)
        print("MLX PERFORMANCE BENCHMARK REPORT")
        print("=" * 80)
        print(f"{'Benchmark':<30} {'Avg (ms)':<12} {'Min (ms)':<12} {'Max (ms)':<12} {'Throughput':<15}")
        print("-" * 80)
        
        for result in self.results:
            print(f"{result.name:<30} "
                  f"{result.avg_time_ms:<12.2f} "
                  f"{result.min_time_ms:<12.2f} "
                  f"{result.max_time_ms:<12.2f} "
                  f"{result.throughput:<15.2f}")
        print("=" * 80)


# =============================================================================
# Benchmark Tests
# =============================================================================

@pytest.mark.benchmark
class TestModelQuantizationBenchmarks:
    """Benchmark model quantization performance"""
    
    @pytest.mark.skipif(not HAS_NUMPY, reason="NumPy not available")
    def test_quantization_fp32_to_fp16(self):
        """Benchmark FP32 to FP16 quantization"""
        import numpy as np
        
        quantizer = ModelQuantizer()
        weights = np.random.randn(1000, 1000).astype(np.float32)
        
        benchmark = PerformanceBenchmarks()
        
        def quantize():
            if HAS_MLX:
                import mlx.core as mx
                _ = weights.astype(mx.float16)
            else:
                _ = weights.astype(np.float16)
        
        result = benchmark.run_benchmark(
            "FP32→FP16 Quantization",
            quantize,
            iterations=100
        )
        
        assert result.avg_time_ms < 100  # Should be fast
        benchmark.print_report()
    
    @pytest.mark.skipif(not HAS_NUMPY, reason="NumPy not available")
    def test_quantization_fp32_to_int8(self):
        """Benchmark FP32 to INT8 quantization"""
        import numpy as np
        
        quantizer = ModelQuantizer()
        weights = np.random.randn(1000, 1000).astype(np.float32)
        
        benchmark = PerformanceBenchmarks()
        
        def quantize():
            scale = np.max(np.abs(weights)) / 127.0
            _ = np.round(weights / scale).astype(np.int8)
        
        result = benchmark.run_benchmark(
            "FP32→INT8 Quantization",
            quantize,
            iterations=100
        )
        
        assert result.avg_time_ms < 100
        benchmark.print_report()
    
    def test_memory_estimation_speed(self):
        """Benchmark memory estimation calculations"""
        quantizer = ModelQuantizer()
        
        test_params = [
            1_000_000,      # 1M params
            7_000_000_000,  # 7B params
            70_000_000_000, # 70B params
        ]
        
        benchmark = PerformanceBenchmarks()
        
        def estimate():
            for params in test_params:
                for precision in ModelPrecision:
                    _ = quantizer.estimate_memory_usage(params, precision)
        
        result = benchmark.run_benchmark(
            "Memory Estimation",
            estimate,
            iterations=1000
        )
        
        assert result.avg_time_ms < 1  # Should be very fast
        benchmark.print_report()


@pytest.mark.benchmark
class TestTPVResonanceBenchmarks:
    """Benchmark TPV resonance calculations"""
    
    @pytest.mark.skipif(not HAS_NUMPY, reason="NumPy not available")
    def test_tpv_calculation_small(self):
        """Benchmark TPV calculation with small embeddings"""
        import numpy as np
        
        tpv = TPVResonance(
            thought_weight=1.0,
            preference_weight=0.8,
            value_weight=0.6
        )
        
        thought = np.random.randn(128).tolist()
        preference = np.random.randn(128).tolist()
        value = np.random.randn(128).tolist()
        
        benchmark = PerformanceBenchmarks()
        
        def calculate():
            _ = tpv.calculate_resonance(thought, preference, value)
        
        result = benchmark.run_benchmark(
            "TPV Calculation (128-dim)",
            calculate,
            iterations=1000
        )
        
        assert result.avg_time_ms < 1
        benchmark.print_report()
    
    @pytest.mark.skipif(not HAS_NUMPY, reason="NumPy not available")
    def test_tpv_calculation_large(self):
        """Benchmark TPV calculation with large embeddings"""
        import numpy as np
        
        tpv = TPVResonance()
        
        thought = np.random.randn(4096).tolist()
        preference = np.random.randn(4096).tolist()
        value = np.random.randn(4096).tolist()
        
        benchmark = PerformanceBenchmarks()
        
        def calculate():
            _ = tpv.calculate_resonance(thought, preference, value)
        
        result = benchmark.run_benchmark(
            "TPV Calculation (4096-dim)",
            calculate,
            iterations=100
        )
        
        assert result.avg_time_ms < 10
        benchmark.print_report()


@pytest.mark.benchmark
class TestAIEngineBenchmarks:
    """Benchmark AI Engine operations"""
    
    @pytest.mark.asyncio
    async def test_engine_initialization(self):
        """Benchmark AI engine initialization"""
        benchmark = PerformanceBenchmarks()
        
        async def init():
            engine = AIEngine()
            await engine.initialize()
        
        # Time the initialization
        times = []
        for _ in range(5):
            start = time.perf_counter()
            await init()
            end = time.perf_counter()
            times.append((end - start) * 1000)
        
        result = BenchmarkResult(
            name="Engine Initialization",
            iterations=5,
            total_time_ms=sum(times),
            avg_time_ms=statistics.mean(times),
            min_time_ms=min(times),
            max_time_ms=max(times),
            std_dev_ms=statistics.stdev(times) if len(times) > 1 else 0,
            throughput=5 / (sum(times) / 1000)
        )
        
        print(f"\nEngine Init: {result.avg_time_ms:.2f}ms avg")
        assert result.avg_time_ms < 1000  # Should init in under 1 second
    
    @pytest.mark.asyncio
    async def test_model_config_creation(self):
        """Benchmark model config creation"""
        benchmark = PerformanceBenchmarks()
        
        def create_config():
            _ = ModelConfig(
                model_id="test-model",
                precision=ModelPrecision.FP16,
                max_tokens=2048,
                temperature=0.7,
                top_p=0.9,
                use_neural_engine=True,
                unified_memory=True
            )
        
        result = benchmark.run_benchmark(
            "Model Config Creation",
            create_config,
            iterations=10000
        )
        
        assert result.avg_time_ms < 0.01  # Should be microseconds
        benchmark.print_report()


@pytest.mark.benchmark
class TestMLXModelBenchmarks:
    """Benchmark MLX model operations"""
    
    @pytest.mark.skipif(not HAS_MLX, reason="MLX not available")
    @pytest.mark.asyncio
    async def test_model_warmup(self):
        """Benchmark model warmup time"""
        import mlx.core as mx
        
        config = ModelConfig(
            model_id="test-model",
            precision=ModelPrecision.FP16
        )
        model = MLXModel(config)
        
        times = []
        for _ in range(3):
            start = time.perf_counter()
            await model._warmup()
            end = time.perf_counter()
            times.append((end - start) * 1000)
        
        avg_time = statistics.mean(times)
        print(f"\nModel Warmup: {avg_time:.2f}ms")
        assert avg_time < 100  # Should be fast
    
    @pytest.mark.skipif(not HAS_MLX, reason="MLX not available")
    @pytest.mark.asyncio
    async def test_array_operations(self):
        """Benchmark basic MLX array operations"""
        import mlx.core as mx
        
        benchmark = PerformanceBenchmarks()
        
        # Matrix multiplication
        a = mx.random.normal((1000, 1000))
        b = mx.random.normal((1000, 1000))
        
        def matmul():
            _ = mx.matmul(a, b)
            mx.eval(_)  # Force evaluation
        
        result = benchmark.run_benchmark(
            "MLX MatMul (1000x1000)",
            matmul,
            iterations=10
        )
        
        print(f"\nMLX MatMul: {result.avg_time_ms:.2f}ms")
        benchmark.print_report()
    
    @pytest.mark.skipif(not HAS_MLX, reason="MLX not available")
    def test_memory_bandwidth(self):
        """Test memory bandwidth with large arrays"""
        import mlx.core as mx
        
        # Create large arrays to test memory bandwidth
        size = 10_000_000  # 10M elements
        a = mx.ones(size)
        b = mx.ones(size)
        
        start = time.perf_counter()
        c = a + b
        mx.eval(c)
        end = time.perf_counter()
        
        elapsed_ms = (end - start) * 1000
        bytes_transferred = size * 4 * 3  # read a, read b, write c (4 bytes per float32)
        bandwidth_gbps = (bytes_transferred / (1024**3)) / (elapsed_ms / 1000)
        
        print(f"\nMemory Bandwidth: {bandwidth_gbps:.2f} GB/s")
        # Apple Silicon should achieve good bandwidth
        assert bandwidth_gbps > 10  # At least 10 GB/s


@pytest.mark.benchmark
class TestPrecisionComparison:
    """Compare performance across precision levels"""
    
    @pytest.mark.skipif(not HAS_NUMPY, reason="NumPy not available")
    def test_precision_impact(self):
        """Compare operation speed across precision levels"""
        import numpy as np
        
        sizes = [1000, 5000, 10000]
        precisions = [
            (np.float32, "FP32"),
            (np.float16, "FP16"),
        ]
        
        print("\n" + "=" * 60)
        print("PRECISION COMPARISON")
        print("=" * 60)
        print(f"{'Size':<10} {'Precision':<10} {'Time (ms)':<15} {'Speedup':<10}")
        print("-" * 60)
        
        baseline_time = None
        
        for size in sizes:
            a = np.random.randn(size, size).astype(np.float32)
            b = np.random.randn(size, size).astype(np.float32)
            
            for dtype, name in precisions:
                a_typed = a.astype(dtype)
                b_typed = b.astype(dtype)
                
                times = []
                for _ in range(5):
                    start = time.perf_counter()
                    _ = np.matmul(a_typed, b_typed)
                    end = time.perf_counter()
                    times.append((end - start) * 1000)
                
                avg_time = statistics.mean(times)
                
                if name == "FP32":
                    baseline_time = avg_time
                    speedup = 1.0
                else:
                    speedup = baseline_time / avg_time if avg_time > 0 else 0
                
                print(f"{size:<10} {name:<10} {avg_time:<15.2f} {speedup:<10.2f}x")
        
        print("=" * 60)


# =============================================================================
# Load Testing
# =============================================================================

@pytest.mark.load
class TestLoadPerformance:
    """Load testing for AI engine"""
    
    @pytest.mark.asyncio
    async def test_concurrent_model_configs(self):
        """Test creating many model configs concurrently"""
        async def create_many_configs(count: int):
            configs = []
            for i in range(count):
                config = ModelConfig(
                    model_id=f"model-{i}",
                    precision=ModelPrecision.FP16
                )
                configs.append(config)
            return configs
        
        start = time.perf_counter()
        configs = await create_many_configs(1000)
        end = time.perf_counter()
        
        elapsed_ms = (end - start) * 1000
        print(f"\nCreated 1000 configs in {elapsed_ms:.2f}ms")
        assert elapsed_ms < 1000  # Should be under 1 second
    
    @pytest.mark.skipif(not HAS_NUMPY, reason="NumPy not available")
    def test_batch_tpv_calculations(self):
        """Test batch TPV calculations"""
        import numpy as np
        
        tpv = TPVResonance()
        batch_size = 100
        
        # Create batch of embeddings
        thoughts = [np.random.randn(128).tolist() for _ in range(batch_size)]
        preferences = [np.random.randn(128).tolist() for _ in range(batch_size)]
        values = [np.random.randn(128).tolist() for _ in range(batch_size)]
        
        start = time.perf_counter()
        results = []
        for t, p, v in zip(thoughts, preferences, values):
            result = tpv.calculate_resonance(t, p, v)
            results.append(result)
        end = time.perf_counter()
        
        elapsed_ms = (end - start) * 1000
        print(f"\nBatch TPV (100): {elapsed_ms:.2f}ms")
        assert elapsed_ms < 100  # Should be fast


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--benchmark"])
