"""
Cell 0 OS - Prometheus Metrics Module

Production-ready metrics collection using Prometheus client library.
Provides comprehensive instrumentation for all Cell 0 components.
"""

import time
import os
from functools import wraps
from typing import Optional, Callable, Any, Dict
from contextlib import contextmanager

# Prometheus client imports
try:
    from prometheus_client import Counter, Histogram, Gauge, Info, Enum
    from prometheus_client import CollectorRegistry, generate_latest, CONTENT_TYPE_LATEST
    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False
    # Create dummy classes for when prometheus_client is not installed
    class _DummyMetric:
        def __init__(self, *args, **kwargs): pass
        def inc(self, *args, **kwargs): pass
        def dec(self, *args, **kwargs): pass
        def set(self, *args, **kwargs): pass
        def observe(self, *args, **kwargs): pass
        def labels(self, *args, **kwargs): return self
    
    Counter = Histogram = Gauge = Info = Enum = _DummyMetric
    CollectorRegistry = object
    def generate_latest(*args): return b"# Prometheus client not installed"
    CONTENT_TYPE_LATEST = "text/plain"


# =============================================================================
# Registry
# =============================================================================

# Use a custom registry to avoid conflicts with other libraries
REGISTRY = CollectorRegistry() if PROMETHEUS_AVAILABLE else None

# =============================================================================
# System Metrics
# =============================================================================

CELL0_INFO = Info(
    "cell0_build_info",
    "Cell 0 OS build information",
    registry=REGISTRY
)

CELL0_UPTIME = Gauge(
    "cell0_uptime_seconds",
    "Time since Cell 0 OS started",
    registry=REGISTRY
)

# =============================================================================
# Agent Metrics
# =============================================================================

AGENTS_ACTIVE = Gauge(
    "cell0_agents_active",
    "Number of currently active agents",
    ["agent_type"],
    registry=REGISTRY
)

AGENTS_TOTAL = Counter(
    "cell0_agents_total",
    "Total number of agents created",
    ["agent_type", "status"],
    registry=REGISTRY
)

AGENT_MESSAGE_COUNT = Counter(
    "cell0_agent_messages_total",
    "Total messages processed by agents",
    ["agent_id", "direction"],  # direction: inbound, outbound
    registry=REGISTRY
)

AGENT_SESSION_DURATION = Histogram(
    "cell0_agent_session_duration_seconds",
    "Duration of agent sessions",
    ["agent_type"],
    buckets=[60, 300, 600, 1800, 3600, 7200, 14400, 28800],
    registry=REGISTRY
)

# =============================================================================
# Inference Metrics
# =============================================================================

INFERENCE_REQUESTS = Counter(
    "cell0_inference_requests_total",
    "Total inference requests",
    ["model", "status"],  # status: success, error, timeout
    registry=REGISTRY
)

INFERENCE_LATENCY = Histogram(
    "cell0_inference_latency_seconds",
    "Inference request latency",
    ["model"],
    buckets=[0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0],
    registry=REGISTRY
)

INFERENCE_TOKENS = Counter(
    "cell0_inference_tokens_total",
    "Total tokens processed",
    ["model", "type"],  # type: input, output
    registry=REGISTRY
)

INFERENCE_QUEUE_SIZE = Gauge(
    "cell0_inference_queue_size",
    "Current inference queue size",
    registry=REGISTRY
)

MODEL_LOAD_TIME = Histogram(
    "cell0_model_load_duration_seconds",
    "Time to load a model",
    ["model"],
    buckets=[1.0, 2.5, 5.0, 10.0, 30.0, 60.0, 120.0],
    registry=REGISTRY
)

MODEL_MEMORY_USAGE = Gauge(
    "cell0_model_memory_bytes",
    "Memory usage by model",
    ["model"],
    registry=REGISTRY
)

# =============================================================================
# API Metrics
# =============================================================================

API_REQUESTS = Counter(
    "cell0_api_requests_total",
    "Total API requests",
    ["method", "endpoint", "status"],
    registry=REGISTRY
)

API_REQUEST_DURATION = Histogram(
    "cell0_api_request_duration_seconds",
    "API request duration",
    ["method", "endpoint"],
    buckets=[0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
    registry=REGISTRY
)

API_REQUEST_SIZE = Histogram(
    "cell0_api_request_size_bytes",
    "API request payload size",
    ["endpoint"],
    buckets=[1024, 10240, 102400, 1048576, 10485760],
    registry=REGISTRY
)

API_RESPONSE_SIZE = Histogram(
    "cell0_api_response_size_bytes",
    "API response payload size",
    ["endpoint"],
    buckets=[1024, 10240, 102400, 1048576, 10485760],
    registry=REGISTRY
)

API_RATE_LIMIT_HITS = Counter(
    "cell0_api_rate_limit_hits_total",
    "Total rate limit hits",
    ["endpoint", "client_id"],
    registry=REGISTRY
)

# =============================================================================
# WebSocket Metrics
# =============================================================================

WEBSOCKET_CONNECTIONS_ACTIVE = Gauge(
    "cell0_websocket_connections_active",
    "Number of active WebSocket connections",
    ["connection_type"],  # type: gateway, canvas, voice
    registry=REGISTRY
)

WEBSOCKET_CONNECTIONS_TOTAL = Counter(
    "cell0_websocket_connections_total",
    "Total WebSocket connections",
    ["connection_type", "status"],  # status: success, error, timeout
    registry=REGISTRY
)

WEBSOCKET_MESSAGES = Counter(
    "cell0_websocket_messages_total",
    "Total WebSocket messages",
    ["connection_type", "direction"],  # direction: sent, received
    registry=REGISTRY
)

WEBSOCKET_MESSAGE_SIZE = Histogram(
    "cell0_websocket_message_size_bytes",
    "WebSocket message size",
    ["connection_type"],
    buckets=[1024, 10240, 102400, 1048576],
    registry=REGISTRY
)

WEBSOCKET_ERRORS = Counter(
    "cell0_websocket_errors_total",
    "Total WebSocket errors",
    ["connection_type", "error_type"],
    registry=REGISTRY
)

# =============================================================================
# Ollama Integration Metrics
# =============================================================================

OLLAMA_REQUESTS = Counter(
    "cell0_ollama_requests_total",
    "Total Ollama requests",
    ["operation", "status"],  # operation: generate, embed, list, pull
    registry=REGISTRY
)

OLLAMA_LATENCY = Histogram(
    "cell0_ollama_latency_seconds",
    "Ollama request latency",
    ["operation"],
    buckets=[0.1, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0],
    registry=REGISTRY
)

OLLAMA_CONNECTION_STATUS = Enum(
    "cell0_ollama_connection_status",
    "Ollama service connection status",
    states=["connected", "disconnected", "error"],
    registry=REGISTRY
)

# =============================================================================
# Signal Integration Metrics
# =============================================================================

SIGNAL_MESSAGES = Counter(
    "cell0_signal_messages_total",
    "Total Signal messages",
    ["direction", "status"],  # direction: sent, received
    registry=REGISTRY
)

SIGNAL_CONNECTION_STATUS = Enum(
    "cell0_signal_connection_status",
    "Signal service connection status",
    states=["connected", "disconnected", "error"],
    registry=REGISTRY
)

SIGNAL_LATENCY = Histogram(
    "cell0_signal_latency_seconds",
    "Signal operation latency",
    ["operation"],
    buckets=[0.1, 0.5, 1.0, 2.5, 5.0, 10.0],
    registry=REGISTRY
)

# =============================================================================
# COL (Cognitive Operating Layer) Metrics
# =============================================================================

COL_EVENTS = Counter(
    "cell0_col_events_total",
    "Total COL events processed",
    ["event_type", "status"],
    registry=REGISTRY
)

COL_EVENT_LATENCY = Histogram(
    "cell0_col_event_latency_seconds",
    "COL event processing latency",
    ["event_type"],
    buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0],
    registry=REGISTRY
)

COL_RESONANCE_SCORE = Gauge(
    "cell0_col_resonance_score",
    "Current COL resonance score",
    registry=REGISTRY
)

COL_SYPAS_QUEUE_SIZE = Gauge(
    "cell0_col_sypas_queue_size",
    "SYPAS event queue size",
    registry=REGISTRY
)

# =============================================================================
# TPV (Thought-Preference-Value) Metrics
# =============================================================================

TPV_ENTRIES = Gauge(
    "cell0_tpv_entries_total",
    "Total TPV entries",
    ["domain"],
    registry=REGISTRY
)

TPV_COHERENCE = Gauge(
    "cell0_tpv_coherence_score",
    "TPV coherence score",
    registry=REGISTRY
)

TPV_UPDATE_LATENCY = Histogram(
    "cell0_tpv_update_latency_seconds",
    "TPV update latency",
    buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1],
    registry=REGISTRY
)

# =============================================================================
# Resource Metrics
# =============================================================================

MEMORY_USAGE = Gauge(
    "cell0_memory_usage_bytes",
    "Memory usage by component",
    ["component"],
    registry=REGISTRY
)

CPU_USAGE = Gauge(
    "cell0_cpu_usage_percent",
    "CPU usage percentage",
    ["component"],
    registry=REGISTRY
)

DISK_USAGE = Gauge(
    "cell0_disk_usage_bytes",
    "Disk usage",
    ["path"],
    registry=REGISTRY
)

DISK_FREE = Gauge(
    "cell0_disk_free_bytes",
    "Free disk space",
    ["path"],
    registry=REGISTRY
)

# =============================================================================
# Security Metrics
# =============================================================================

SECURITY_EVENTS = Counter(
    "cell0_security_events_total",
    "Total security events",
    ["event_type", "severity"],
    registry=REGISTRY
)

TOOL_EXECUTIONS = Counter(
    "cell0_tool_executions_total",
    "Total tool executions",
    ["tool_name", "status"],
    registry=REGISTRY
)

AUTH_ATTEMPTS = Counter(
    "cell0_auth_attempts_total",
    "Total authentication attempts",
    ["method", "status"],
    registry=REGISTRY
)

# =============================================================================
# Utility Functions
# =============================================================================

def set_build_info(version: str, commit: str = "", branch: str = ""):
    """Set build information metric."""
    if PROMETHEUS_AVAILABLE:
        CELL0_INFO.info({
            "version": version,
            "commit": commit,
            "branch": branch,
            "python_version": os.sys.version.split()[0],
        })

def update_uptime(start_time: float):
    """Update uptime metric based on start timestamp."""
    if PROMETHEUS_AVAILABLE:
        CELL0_UPTIME.set(time.time() - start_time)

@contextmanager
def timer(metric: Histogram, labels: Optional[Dict[str, str]] = None):
    """
    Context manager for timing operations.
    
    Usage:
        with timer(INFERENCE_LATENCY, {"model": "qwen2.5:7b"}):
            result = model.generate(prompt)
    """
    if not PROMETHEUS_AVAILABLE:
        yield
        return
    
    start = time.time()
    try:
        yield
    finally:
        duration = time.time() - start
        if labels:
            metric.labels(**labels).observe(duration)
        else:
            metric.observe(duration)

def track_request_duration(method: str, endpoint: str):
    """
    Decorator to track API request duration.
    
    Usage:
        @track_request_duration("GET", "/api/status")
        async def get_status(request):
            ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            with timer(API_REQUEST_DURATION, {"method": method, "endpoint": endpoint}):
                return await func(*args, **kwargs)
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            with timer(API_REQUEST_DURATION, {"method": method, "endpoint": endpoint}):
                return func(*args, **kwargs)
        
        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    return decorator

def count_api_request(method: str, endpoint: str, status: str):
    """Count an API request with status."""
    if PROMETHEUS_AVAILABLE:
        API_REQUESTS.labels(method=method, endpoint=endpoint, status=status).inc()

def record_inference_metrics(
    model: str,
    status: str,
    latency: float,
    input_tokens: int = 0,
    output_tokens: int = 0
):
    """Record comprehensive inference metrics."""
    if not PROMETHEUS_AVAILABLE:
        return
    
    INFERENCE_REQUESTS.labels(model=model, status=status).inc()
    INFERENCE_LATENCY.labels(model=model).observe(latency)
    
    if input_tokens > 0:
        INFERENCE_TOKENS.labels(model=model, type="input").inc(input_tokens)
    if output_tokens > 0:
        INFERENCE_TOKENS.labels(model=model, type="output").inc(output_tokens)

def update_agent_count(agent_type: str, count: int):
    """Update the active agent count."""
    if PROMETHEUS_AVAILABLE:
        AGENTS_ACTIVE.labels(agent_type=agent_type).set(count)

def record_websocket_connection(connection_type: str, established: bool = True):
    """Record WebSocket connection metrics."""
    if not PROMETHEUS_AVAILABLE:
        return
    
    status = "success" if established else "error"
    WEBSOCKET_CONNECTIONS_TOTAL.labels(
        connection_type=connection_type,
        status=status
    ).inc()
    
    if established:
        WEBSOCKET_CONNECTIONS_ACTIVE.labels(connection_type=connection_type).inc()

def record_websocket_disconnection(connection_type: str):
    """Record WebSocket disconnection."""
    if PROMETHEUS_AVAILABLE:
        WEBSOCKET_CONNECTIONS_ACTIVE.labels(connection_type=connection_type).dec()

def record_websocket_message(connection_type: str, direction: str, size_bytes: int = 0):
    """Record WebSocket message metrics."""
    if not PROMETHEUS_AVAILABLE:
        return
    
    WEBSOCKET_MESSAGES.labels(
        connection_type=connection_type,
        direction=direction
    ).inc()
    
    if size_bytes > 0:
        WEBSOCKET_MESSAGE_SIZE.labels(connection_type=connection_type).observe(size_bytes)

# =============================================================================
# Metrics Endpoint Handler
# =============================================================================

async def metrics_handler(request) -> tuple:
    """
    HTTP handler for /metrics endpoint.
    
    Returns:
        Tuple of (body, content_type, status_code)
    """
    if not PROMETHEUS_AVAILABLE:
        return (
            b"# Prometheus client not installed. Run: pip install prometheus-client",
            "text/plain",
            200
        )
    
    # Update uptime if start time is available
    try:
        import engine
        if hasattr(engine, 'START_TIME'):
            update_uptime(engine.START_TIME)
    except:
        pass
    
    body = generate_latest(REGISTRY)
    return (body, CONTENT_TYPE_LATEST, 200)


# Import for decorator check
import asyncio

# Set initial build info
try:
    from cell0 import __version__ as CELL0_VERSION
except:
    CELL0_VERSION = "1.1.5"

set_build_info(CELL0_VERSION)
