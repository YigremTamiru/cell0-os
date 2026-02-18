"""
Cell 0 Monitoring Module

Provides observability for Cell 0 OS:
- Prometheus metrics
- Structured logging
- Health checks
"""

from .metrics import (
    Cell0Metrics,
    setup_metrics,
    get_metrics,
    get_metrics_registry,
    timed,
)

from .logging_config import (
    configure_logging,
    get_logger,
    LogContext,
    Cell0JsonFormatter,
)

from .health import (
    HealthChecker,
    HealthStatus,
    HealthReport,
    ComponentHealth,
    get_health_checker,
)

__all__ = [
    "Cell0Metrics",
    "setup_metrics",
    "get_metrics",
    "get_metrics_registry",
    "timed",
    "configure_logging",
    "get_logger",
    "LogContext",
    "Cell0JsonFormatter",
    "HealthChecker",
    "HealthStatus",
    "HealthReport",
    "ComponentHealth",
    "get_health_checker",
]
