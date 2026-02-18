"""
metrics.py - Prometheus Metrics for Cell 0 OS

Provides comprehensive metrics collection for:
- System metrics (CPU, memory, disk)
- Application metrics (requests, latency, errors)
- Business metrics (agents, inference, TPV)
- Integration metrics (Ollama, Signal, etc.)
"""

import os
import time
from typing import Optional, Callable
from functools import wraps

# Try to import Prometheus client
try:
    from prometheus_client import Counter, Histogram, Gauge, Info, start_http_server, generate_latest
    from prometheus_client.core import CollectorRegistry
    HAS_PROMETHEUS = True
except ImportError:
    HAS_PROMETHEUS = False
    # Create dummy classes for when prometheus is not available
    class DummyMetric:
        def __init__(self, *args, **kwargs):
            pass
        def inc(self, *args, **kwargs):
            pass
        def observe(self, *args, **kwargs):
            pass
        def set(self, *args, **kwargs):
            pass
        def labels(self, *args, **kwargs):
            return self
    
    Counter = Histogram = Gauge = Info = DummyMetric
    CollectorRegistry = object
    def start_http_server(*args, **kwargs):
        pass
    def generate_latest(*args, **kwargs):
        return b""


# Create a global registry
REGISTRY = CollectorRegistry()


class Cell0Metrics:
    """Container for all Cell 0 metrics"""
    
    def __init__(self, registry: CollectorRegistry = REGISTRY):
        self.registry = registry
        self._setup_system_metrics()
        self._setup_api_metrics()
        self._setup_agent_metrics()
        self._setup_inference_metrics()
        self._setup_col_metrics()
        self._setup_integration_metrics()
        self._setup_info()
    
    def _setup_system_metrics(self):
        """Setup system-level metrics"""
        self.system_uptime = Gauge(
            "cell0_uptime_seconds",
            "Time since daemon start",
            registry=self.registry
        )
        self.system_memory_usage = Gauge(
            "cell0_memory_usage_bytes",
            "Current memory usage",
            registry=self.registry
        )
        self.system_memory_percent = Gauge(
            "cell0_memory_usage_percent",
            "Memory usage percentage",
            registry=self.registry
        )
        self.system_cpu_percent = Gauge(
            "cell0_cpu_usage_percent",
            "CPU usage percentage",
            registry=self.registry
        )
        self.system_disk_usage = Gauge(
            "cell0_disk_usage_bytes",
            "Disk usage in bytes",
            registry=self.registry
        )
        self.system_disk_percent = Gauge(
            "cell0_disk_usage_percent",
            "Disk usage percentage",
            registry=self.registry
        )
    
    def _setup_api_metrics(self):
        """Setup API metrics"""
        self.api_requests_total = Counter(
            "cell0_api_requests_total",
            "Total API requests",
            ["method", "endpoint", "status"],
            registry=self.registry
        )
        self.api_request_duration = Histogram(
            "cell0_api_request_duration_seconds",
            "API request duration",
            ["method", "endpoint"],
            buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
            registry=self.registry
        )
        self.websocket_connections = Gauge(
            "cell0_websocket_connections_active",
            "Active WebSocket connections",
            registry=self.registry
        )
        self.websocket_messages = Counter(
            "cell0_websocket_messages_total",
            "Total WebSocket messages",
            ["direction"],  # sent, received
            registry=self.registry
        )
    
    def _setup_agent_metrics(self):
        """Setup agent metrics"""
        self.agents_active = Gauge(
            "cell0_agents_active",
            "Number of active agents",
            ["type"],
            registry=self.registry
        )
        self.agents_total = Counter(
            "cell0_agents_total",
            "Total agents created",
            ["type"],
            registry=self.registry
        )
        self.agent_operations = Counter(
            "cell0_agent_operations_total",
            "Agent operations",
            ["operation", "status"],
            registry=self.registry
        )
    
    def _setup_inference_metrics(self):
        """Setup AI inference metrics"""
        self.inference_requests = Counter(
            "cell0_inference_requests_total",
            "Total inference requests",
            ["model", "status"],
            registry=self.registry
        )
        self.inference_latency = Histogram(
            "cell0_inference_latency_seconds",
            "Inference latency",
            ["model"],
            buckets=[0.1, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0],
            registry=self.registry
        )
        self.inference_tokens = Counter(
            "cell0_inference_tokens_total",
            "Total tokens processed",
            ["model", "type"],  # type: input, output
            registry=self.registry
        )
        self.model_load_duration = Histogram(
            "cell0_model_load_duration_seconds",
            "Model loading duration",
            ["model"],
            registry=self.registry
        )
    
    def _setup_col_metrics(self):
        """Setup COL (Cognitive Operating Layer) metrics"""
        self.col_events = Counter(
            "cell0_col_events_total",
            "COL events processed",
            ["type"],  # intent, capability, execution
            registry=self.registry
        )
        self.col_resonance = Gauge(
            "cell0_col_resonance_score",
            "Current resonance score",
            registry=self.registry
        )
        self.col_sypas_queued = Gauge(
            "cell0_col_sypas_events_queued",
            "SYPAS events in queue",
            registry=self.registry
        )
    
    def _setup_integration_metrics(self):
        """Setup integration metrics"""
        self.ollama_requests = Counter(
            "cell0_ollama_requests_total",
            "Ollama requests",
            ["operation", "status"],
            registry=self.registry
        )
        self.ollama_up = Gauge(
            "cell0_ollama_up",
            "Ollama service availability",
            registry=self.registry
        )
        self.signal_messages = Counter(
            "cell0_signal_messages_total",
            "Signal messages",
            ["direction"],  # sent, received
            registry=self.registry
        )
        self.search_requests = Counter(
            "cell0_search_requests_total",
            "Search requests",
            ["provider", "status"],
            registry=self.registry
        )
    
    def _setup_info(self):
        """Setup info metric"""
        self.info = Info(
            "cell0",
            "Cell 0 OS information",
            registry=self.registry
        )
        self.info.info({
            "version": "1.2.0",
            "environment": os.getenv("CELL0_ENV", "development"),
        })
    
    def update_system_metrics(self):
        """Update system metrics (call periodically)"""
        try:
            import psutil
            
            # Memory
            memory = psutil.virtual_memory()
            self.system_memory_usage.set(memory.used)
            self.system_memory_percent.set(memory.percent)
            
            # CPU
            self.system_cpu_percent.set(psutil.cpu_percent())
            
            # Disk
            disk = psutil.disk_usage("/")
            self.system_disk_usage.set(disk.used)
            self.system_disk_percent.set(disk.percent)
            
        except ImportError:
            pass
    
    def time_request(self, method: str, endpoint: str):
        """Context manager for timing API requests"""
        return RequestTimer(self, method, endpoint)
    
    def track_inference(self, model: str):
        """Context manager for tracking inference"""
        return InferenceTracker(self, model)


class RequestTimer:
    """Context manager for timing requests"""
    
    def __init__(self, metrics: Cell0Metrics, method: str, endpoint: str):
        self.metrics = metrics
        self.method = method
        self.endpoint = endpoint
        self.start_time = None
    
    def __enter__(self):
        self.start_time = time.time()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        duration = time.time() - self.start_time
        status = "error" if exc_type else "success"
        
        self.metrics.api_requests_total.labels(
            method=self.method,
            endpoint=self.endpoint,
            status=status
        ).inc()
        
        self.metrics.api_request_duration.labels(
            method=self.method,
            endpoint=self.endpoint
        ).observe(duration)


class InferenceTracker:
    """Context manager for tracking inference"""
    
    def __init__(self, metrics: Cell0Metrics, model: str):
        self.metrics = metrics
        self.model = model
        self.start_time = None
    
    def __enter__(self):
        self.start_time = time.time()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        duration = time.time() - self.start_time
        status = "error" if exc_type else "success"
        
        self.metrics.inference_requests.labels(
            model=self.model,
            status=status
        ).inc()
        
        self.metrics.inference_latency.labels(
            model=self.model
        ).observe(duration)


# Global metrics instance
_metrics: Optional[Cell0Metrics] = None


def setup_metrics(port: int = 18802) -> Cell0Metrics:
    """
    Setup metrics and start Prometheus HTTP server
    
    Args:
        port: Port for Prometheus metrics endpoint
    
    Returns:
        Cell0Metrics instance
    """
    global _metrics
    
    if _metrics is None:
        _metrics = Cell0Metrics()
        
        if HAS_PROMETHEUS:
            start_http_server(port, registry=REGISTRY)
    
    return _metrics


def get_metrics_registry() -> CollectorRegistry:
    """Get the metrics registry"""
    return REGISTRY


def get_metrics() -> Cell0Metrics:
    """Get the global metrics instance"""
    if _metrics is None:
        return setup_metrics()
    return _metrics


def timed(metric_name: str, labels: Optional[dict] = None):
    """Decorator for timing function execution"""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            start = time.time()
            try:
                return func(*args, **kwargs)
            finally:
                duration = time.time() - start
                # Record metric (implementation depends on your setup)
                metrics = get_metrics()
                # This is a simplified example
        return wrapper
    return decorator
