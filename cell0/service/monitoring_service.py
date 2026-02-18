"""
Cell 0 OS - HTTP Service with Monitoring Integration

Production-ready HTTP service that integrates:
- Prometheus metrics endpoint (/metrics)
- Health checks (/api/health, /api/health/deep)
- Structured logging
- Request tracing

This module provides a ready-to-use aiohttp application with all
monitoring capabilities enabled.
"""

import asyncio
import time
from typing import Optional, Dict, Any, Callable
from pathlib import Path

from aiohttp import web

# Import monitoring modules
try:
    from engine.monitoring import (
        metrics_handler,
        basic_health_handler,
        deep_health_handler,
        readiness_handler,
        liveness_handler,
        startup_handler,
        setup_health_routes_aiohttp,
        configure_logging,
        get_logger,
        set_trace_id,
        clear_trace_id,
        AGENTS_ACTIVE,
        WEBSOCKET_CONNECTIONS_ACTIVE,
        API_REQUESTS,
        API_REQUEST_DURATION,
        CELL0_UPTIME,
        INFERENCE_REQUESTS,
        INFERENCE_LATENCY,
        count_api_request,
        update_uptime,
    )
    MONITORING_AVAILABLE = True
except ImportError:
    MONITORING_AVAILABLE = False

# Global start time for uptime tracking
START_TIME = time.time()

# Logger
logger = None
if MONITORING_AVAILABLE:
    logger = get_logger("http_service")


# =============================================================================
# Middleware
# =============================================================================

@web.middleware
async def metrics_middleware(request: web.Request, handler: Callable) -> web.Response:
    """
    Middleware to track request metrics.
    
    Tracks:
    - Request count by method, endpoint, status
    - Request duration
    - Request/response size
    """
    if not MONITORING_AVAILABLE:
        return await handler(request)
    
    # Generate trace ID
    trace_id = request.headers.get("X-Trace-ID", "")
    if not trace_id:
        import uuid
        trace_id = str(uuid.uuid4())[:16]
    set_trace_id(trace_id)
    
    # Get endpoint pattern (simplified)
    endpoint = request.path
    method = request.method
    
    # Track start time
    start_time = time.time()
    
    try:
        # Process request
        response = await handler(request)
        
        # Calculate duration
        duration = time.time() - start_time
        status = str(response.status)
        
        # Record metrics
        count_api_request(method, endpoint, status)
        API_REQUEST_DURATION.labels(method=method, endpoint=endpoint).observe(duration)
        
        # Add trace ID to response
        response.headers["X-Trace-ID"] = trace_id
        
        # Log request
        if logger:
            logger.info(
                f"{method} {endpoint} - {status} ({duration:.3f}s)",
                extra={
                    "method": method,
                    "endpoint": endpoint,
                    "status": status,
                    "duration_seconds": duration,
                }
            )
        
        return response
        
    except Exception as e:
        # Record error metric
        duration = time.time() - start_time
        count_api_request(method, endpoint, "500")
        API_REQUEST_DURATION.labels(method=method, endpoint=endpoint).observe(duration)
        
        if logger:
            logger.exception(
                f"{method} {endpoint} - ERROR",
                extra={
                    "method": method,
                    "endpoint": endpoint,
                    "error": str(e),
                }
            )
        raise
        
    finally:
        clear_trace_id()


@web.middleware
async def error_handling_middleware(request: web.Request, handler: Callable) -> web.Response:
    """Middleware for consistent error handling."""
    try:
        return await handler(request)
    except web.HTTPException as e:
        # Return HTTP errors as JSON
        return web.json_response(
            {
                "error": e.reason,
                "status": e.status,
                "trace_id": get_trace_id() if MONITORING_AVAILABLE else None,
            },
            status=e.status
        )
    except Exception as e:
        # Log unexpected errors
        if logger:
            logger.exception("Unexpected error handling request")
        
        # Return generic error
        return web.json_response(
            {
                "error": "Internal server error",
                "status": 500,
                "trace_id": get_trace_id() if MONITORING_AVAILABLE else None,
            },
            status=500
        )


# =============================================================================
# Handlers
# =============================================================================

async def metrics_endpoint(request: web.Request) -> web.Response:
    """Prometheus metrics endpoint."""
    if not MONITORING_AVAILABLE:
        return web.Response(
            text="# Monitoring module not available",
            content_type="text/plain"
        )
    
    # Update uptime metric
    update_uptime(START_TIME)
    
    body, content_type, status = await metrics_handler(request)
    return web.Response(body=body, content_type=content_type, status=status)


async def version_endpoint(request: web.Request) -> web.Response:
    """Version information endpoint."""
    try:
        from cell0 import __version__ as version
    except:
        version = "1.1.5"
    
    return web.json_response({
        "version": version,
        "codename": "The Glass Melted",
        "build_time": None,
        "commit": None,
    })


async def status_endpoint(request: web.Request) -> web.Response:
    """System status endpoint."""
    uptime = time.time() - START_TIME
    
    response = {
        "version": "1.1.5",
        "codename": "The Glass Melted",
        "uptime": uptime,
        "status": "stable",
        "timestamp": time.time(),
    }
    
    # Add monitoring data if available
    if MONITORING_AVAILABLE:
        from engine.monitoring.metrics import REGISTRY
        
        # Get metric values
        try:
            response["metrics"] = {
                "agents_active": get_metric_value(AGENTS_ACTIVE),
                "websocket_connections": get_metric_value(WEBSOCKET_CONNECTIONS_ACTIVE),
            }
        except:
            pass
    
    return web.json_response(response)


def get_metric_value(metric):
    """Helper to get current value from a metric."""
    try:
        # This is a simplified approach - in production you'd use the Prometheus client API
        return 0
    except:
        return 0


# =============================================================================
# Application Factory
# =============================================================================

def create_monitoring_app(
    log_level: str = "INFO",
    log_dir: Optional[Path] = None,
    additional_routes: Optional[list] = None,
) -> web.Application:
    """
    Create an aiohttp application with monitoring enabled.
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR)
        log_dir: Directory for log files
        additional_routes: Additional routes to add to the app
    
    Returns:
        Configured aiohttp Application
    """
    # Configure logging
    if MONITORING_AVAILABLE:
        configure_logging(
            level=log_level,
            log_dir=log_dir,
            enable_file_logging=True,
            enable_console_logging=True,
            json_format=True,
        )
    
    # Create application with middleware
    app = web.Application(middlewares=[
        error_handling_middleware,
        metrics_middleware,
    ])
    
    # Add monitoring routes
    app.router.add_get("/metrics", metrics_endpoint)
    app.router.add_get("/api/version", version_endpoint)
    app.router.add_get("/api/status", status_endpoint)
    
    # Add health check routes
    if MONITORING_AVAILABLE:
        setup_health_routes_aiohttp(app)
    else:
        # Basic health routes without monitoring module
        async def health(request):
            return web.json_response({
                "status": "healthy",
                "timestamp": time.time(),
            })
        
        async def health_deep(request):
            return web.json_response({
                "status": "healthy",
                "timestamp": time.time(),
                "note": "Monitoring module not available",
            })
        
        app.router.add_get("/api/health", health)
        app.router.add_get("/api/health/deep", health_deep)
    
    # Add additional routes
    if additional_routes:
        for route in additional_routes:
            app.router.add_route(route[0], route[1], route[2])
    
    # Startup and cleanup handlers
    async def on_startup(app):
        if logger:
            logger.info("HTTP service starting up")
    
    async def on_cleanup(app):
        if logger:
            logger.info("HTTP service shutting down")
    
    app.on_startup.append(on_startup)
    app.on_cleanup.append(on_cleanup)
    
    return app


# =============================================================================
# Standalone Server
# =============================================================================

class MonitoringService:
    """
    Standalone monitoring HTTP service.
    
    Provides:
    - Prometheus metrics endpoint
    - Health checks
    - Status endpoints
    """
    
    def __init__(
        self,
        host: str = "0.0.0.0",
        port: int = 18800,
        log_level: str = "INFO",
        log_dir: Optional[Path] = None,
    ):
        self.host = host
        self.port = port
        self.log_level = log_level
        self.log_dir = log_dir
        
        self.app: Optional[web.Application] = None
        self.runner: Optional[web.AppRunner] = None
        self.site: Optional[web.TCPSite] = None
        self._running = False
    
    async def start(self):
        """Start the monitoring service."""
        if self._running:
            return
        
        self.app = create_monitoring_app(
            log_level=self.log_level,
            log_dir=self.log_dir,
        )
        
        self.runner = web.AppRunner(self.app)
        await self.runner.setup()
        
        self.site = web.TCPSite(self.runner, self.host, self.port)
        await self.site.start()
        
        self._running = True
        
        if logger:
            logger.info(f"Monitoring service started on http://{self.host}:{self.port}")
        else:
            print(f"Monitoring service started on http://{self.host}:{self.port}")
    
    async def stop(self):
        """Stop the monitoring service."""
        if not self._running:
            return
        
        if self.runner:
            await self.runner.cleanup()
        
        self._running = False
        
        if logger:
            logger.info("Monitoring service stopped")
        else:
            print("Monitoring service stopped")
    
    def add_route(self, method: str, path: str, handler: Callable):
        """Add a custom route to the service."""
        if self.app:
            self.app.router.add_route(method, path, handler)


# =============================================================================
# Integration with Existing Services
# =============================================================================

def enable_monitoring(
    app: web.Application,
    log_level: str = "INFO",
    log_dir: Optional[Path] = None,
):
    """
    Enable monitoring on an existing aiohttp application.
    
    Args:
        app: The aiohttp Application to instrument
        log_level: Logging level
        log_dir: Directory for log files
    """
    # Configure logging
    if MONITORING_AVAILABLE:
        configure_logging(
            level=log_level,
            log_dir=log_dir,
            enable_file_logging=True,
            enable_console_logging=True,
            json_format=True,
        )
    
    # Add middleware
    app.middlewares.insert(0, error_handling_middleware)
    app.middlewares.insert(0, metrics_middleware)
    
    # Add routes
    app.router.add_get("/metrics", metrics_endpoint)
    app.router.add_get("/api/version", version_endpoint)
    
    # Add health routes
    if MONITORING_AVAILABLE:
        setup_health_routes_aiohttp(app)


# =============================================================================
# Main Entry Point
# =============================================================================

async def main():
    """Run standalone monitoring service."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Cell 0 Monitoring Service")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind to")
    parser.add_argument("--port", type=int, default=18800, help="Port to bind to")
    parser.add_argument("--log-level", default="INFO", help="Log level")
    parser.add_argument("--log-dir", help="Log directory")
    
    args = parser.parse_args()
    
    log_dir = Path(args.log_dir) if args.log_dir else None
    
    service = MonitoringService(
        host=args.host,
        port=args.port,
        log_level=args.log_level,
        log_dir=log_dir,
    )
    
    await service.start()
    
    print(f"""
╔════════════════════════════════════════════════════════════════╗
║           Cell 0 OS Monitoring Service                         ║
╠════════════════════════════════════════════════════════════════╣
║  HTTP: http://{args.host}:{args.port:<5}                              ║
╠════════════════════════════════════════════════════════════════╣
║  Endpoints:                                                    ║
║    • /metrics         - Prometheus metrics                     ║
║    • /api/health      - Basic health check                   ║
║    • /api/health/deep - Deep health check                    ║
║    • /healthz         - K8s readiness probe                  ║
║    • /livez           - K8s liveness probe                   ║
║    • /api/status      - System status                        ║
║    • /api/version     - Version information                  ║
╚════════════════════════════════════════════════════════════════╝
""")
    
    # Keep running
    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        print("\nShutting down...")
    finally:
        await service.stop()


if __name__ == "__main__":
    asyncio.run(main())
