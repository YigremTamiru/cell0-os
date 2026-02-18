"""
Cell 0 OS - Monitoring & Observability Module

Production-ready monitoring stack providing:
- Prometheus metrics collection
- Structured JSON logging
- Health checks for K8s probes
- Distributed tracing support

Usage:
    from engine.monitoring import metrics, logging_config, health_checks
    
    # Configure logging
    logging_config.configure_logging(level="INFO")
    
    # Record metrics
    metrics.INFERENCE_REQUESTS.labels(model="qwen2.5:7b", status="success").inc()
    
    # Run health checks
    report = await health_checks.health_registry.run_all_checks()
"""

from cell0.engine.monitoring.metrics import (
    # Counters
    INFERENCE_REQUESTS,
    API_REQUESTS,
    WEBSOCKET_CONNECTIONS_TOTAL,
    WEBSOCKET_MESSAGES,
    OLLAMA_REQUESTS,
    SIGNAL_MESSAGES,
    COL_EVENTS,
    SECURITY_EVENTS,
    TOOL_EXECUTIONS,
    AUTH_ATTEMPTS,
    
    # Gauges
    AGENTS_ACTIVE,
    CELL0_UPTIME,
    WEBSOCKET_CONNECTIONS_ACTIVE,
    INFERENCE_QUEUE_SIZE,
    MEMORY_USAGE,
    CPU_USAGE,
    DISK_USAGE,
    DISK_FREE,
    
    # Histograms
    INFERENCE_LATENCY,
    API_REQUEST_DURATION,
    WEBSOCKET_MESSAGE_SIZE,
    OLLAMA_LATENCY,
    
    # Info
    CELL0_INFO,
    
    # Functions
    set_build_info,
    update_uptime,
    timer,
    track_request_duration,
    count_api_request,
    record_inference_metrics,
    update_agent_count,
    record_websocket_connection,
    record_websocket_disconnection,
    record_websocket_message,
    metrics_handler,
)

from cell0.engine.monitoring.logging_config import (
    configure_logging,
    get_logger,
    set_trace_id,
    get_trace_id,
    clear_trace_id,
    trace_context,
    request_context,
    set_request_context,
    clear_request_context,
    setup_request_logging_middleware,
    WebSocketLogger,
    log_operation,
    JSONFormatter,
    StructuredLogger,
    init_logging_from_env,
)

from cell0.engine.monitoring.health_checks import (
    HealthStatus,
    ComponentHealth,
    HealthReport,
    HealthCheckRegistry,
    health_registry,
    # Check functions
    check_ollama_health,
    check_signal_health,
    check_disk_space,
    check_memory_usage,
    check_cpu_usage,
    check_tpv_store,
    check_websocket_gateway,
    check_agent_coordinator,
    # Handlers
    basic_health_handler,
    deep_health_handler,
    readiness_handler,
    liveness_handler,
    startup_handler,
    setup_health_routes_aiohttp,
    setup_health_routes_fastapi,
)

__version__ = "1.0.0"
__all__ = [
    # Metrics
    "INFERENCE_REQUESTS",
    "API_REQUESTS",
    "WEBSOCKET_CONNECTIONS_TOTAL",
    "WEBSOCKET_MESSAGES",
    "OLLAMA_REQUESTS",
    "SIGNAL_MESSAGES",
    "COL_EVENTS",
    "SECURITY_EVENTS",
    "TOOL_EXECUTIONS",
    "AUTH_ATTEMPTS",
    "AGENTS_ACTIVE",
    "CELL0_UPTIME",
    "WEBSOCKET_CONNECTIONS_ACTIVE",
    "INFERENCE_QUEUE_SIZE",
    "MEMORY_USAGE",
    "CPU_USAGE",
    "DISK_USAGE",
    "DISK_FREE",
    "INFERENCE_LATENCY",
    "API_REQUEST_DURATION",
    "WEBSOCKET_MESSAGE_SIZE",
    "OLLAMA_LATENCY",
    "CELL0_INFO",
    "set_build_info",
    "update_uptime",
    "timer",
    "track_request_duration",
    "count_api_request",
    "record_inference_metrics",
    "update_agent_count",
    "record_websocket_connection",
    "record_websocket_disconnection",
    "record_websocket_message",
    "metrics_handler",
    
    # Logging
    "configure_logging",
    "get_logger",
    "set_trace_id",
    "get_trace_id",
    "clear_trace_id",
    "trace_context",
    "request_context",
    "set_request_context",
    "clear_request_context",
    "setup_request_logging_middleware",
    "WebSocketLogger",
    "log_operation",
    "JSONFormatter",
    "StructuredLogger",
    "init_logging_from_env",
    
    # Health Checks
    "HealthStatus",
    "ComponentHealth",
    "HealthReport",
    "HealthCheckRegistry",
    "health_registry",
    "check_ollama_health",
    "check_signal_health",
    "check_disk_space",
    "check_memory_usage",
    "check_cpu_usage",
    "check_tpv_store",
    "check_websocket_gateway",
    "check_agent_coordinator",
    "basic_health_handler",
    "deep_health_handler",
    "readiness_handler",
    "liveness_handler",
    "startup_handler",
    "setup_health_routes_aiohttp",
    "setup_health_routes_fastapi",
]
