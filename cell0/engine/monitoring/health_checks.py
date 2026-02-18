"""
Cell 0 OS - Health Check Module

Production-ready health checks for Kubernetes probes and monitoring.
Implements:
- Basic health endpoint (/api/health)
- Deep health checks (/api/health/deep)
- Component-specific health checks
- Proper HTTP status codes for K8s probes
"""

import os
import sys
import time
import asyncio
import platform
import shutil
from typing import Dict, List, Optional, Any, Callable, Coroutine
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path

# HTTP response types
try:
    from aiohttp import web
    AIOHTTP_AVAILABLE = True
except ImportError:
    AIOHTTP_AVAILABLE = False
    web = None

try:
    from fastapi import Response, status
    FASTAPI_AVAILABLE = True
except ImportError:
    FASTAPI_AVAILABLE = False


# =============================================================================
# Health Status Enums and Classes
# =============================================================================

class HealthStatus(str, Enum):
    """Health status values."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


@dataclass
class ComponentHealth:
    """Health status for a single component."""
    name: str
    status: HealthStatus
    message: str = ""
    latency_ms: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "status": self.status.value,
            "message": self.message,
            "latency_ms": round(self.latency_ms, 2),
            "metadata": self.metadata,
            "timestamp": self.timestamp,
        }


@dataclass
class HealthReport:
    """Complete health report for the system."""
    status: HealthStatus
    timestamp: str
    version: str
    uptime_seconds: float
    components: List[ComponentHealth]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "status": self.status.value,
            "timestamp": self.timestamp,
            "version": self.version,
            "uptime_seconds": round(self.uptime_seconds, 2),
            "components": [c.to_dict() for c in self.components],
        }
    
    @property
    def http_status_code(self) -> int:
        """Get appropriate HTTP status code for health status."""
        if self.status == HealthStatus.HEALTHY:
            return 200
        elif self.status == HealthStatus.DEGRADED:
            return 200  # Still serving traffic, but with issues
        elif self.status == HealthStatus.UNHEALTHY:
            return 503  # Service Unavailable
        else:
            return 500  # Internal Server Error


# =============================================================================
# Check Functions
# =============================================================================

HealthCheckFn = Callable[[], Coroutine[Any, Any, ComponentHealth]]


async def check_ollama_health(
    ollama_url: str = "http://localhost:11434",
    timeout: float = 5.0
) -> ComponentHealth:
    """Check Ollama service connectivity."""
    start = time.time()
    
    try:
        import aiohttp
        
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{ollama_url}/api/tags",
                timeout=aiohttp.ClientTimeout(total=timeout)
            ) as resp:
                latency = (time.time() - start) * 1000
                
                if resp.status == 200:
                    data = await resp.json()
                    models = data.get("models", [])
                    
                    return ComponentHealth(
                        name="ollama",
                        status=HealthStatus.HEALTHY,
                        message=f"Connected, {len(models)} models available",
                        latency_ms=latency,
                        metadata={
                            "url": ollama_url,
                            "models_loaded": len(models),
                            "models": [m.get("name") for m in models[:5]],
                        }
                    )
                else:
                    return ComponentHealth(
                        name="ollama",
                        status=HealthStatus.UNHEALTHY,
                        message=f"HTTP {resp.status} from Ollama",
                        latency_ms=latency,
                    )
    
    except asyncio.TimeoutError:
        return ComponentHealth(
            name="ollama",
            status=HealthStatus.UNHEALTHY,
            message=f"Connection timeout after {timeout}s",
            latency_ms=timeout * 1000,
        )
    except Exception as e:
        return ComponentHealth(
            name="ollama",
            status=HealthStatus.UNHEALTHY,
            message=f"Connection failed: {str(e)}",
            latency_ms=(time.time() - start) * 1000,
        )


async def check_signal_health(
    signal_rest_url: str = "http://localhost:8080",
    timeout: float = 5.0
) -> ComponentHealth:
    """Check Signal service connectivity."""
    start = time.time()
    
    try:
        import aiohttp
        
        async with aiohttp.ClientSession() as session:
            # Try to get Signal status
            async with session.get(
                f"{signal_rest_url}/v1/about",
                timeout=aiohttp.ClientTimeout(total=timeout)
            ) as resp:
                latency = (time.time() - start) * 1000
                
                if resp.status == 200:
                    return ComponentHealth(
                        name="signal",
                        status=HealthStatus.HEALTHY,
                        message="Signal REST API reachable",
                        latency_ms=latency,
                        metadata={"url": signal_rest_url},
                    )
                else:
                    return ComponentHealth(
                        name="signal",
                        status=HealthStatus.DEGRADED,
                        message=f"Signal returned HTTP {resp.status}",
                        latency_ms=latency,
                    )
    
    except asyncio.TimeoutError:
        return ComponentHealth(
            name="signal",
            status=HealthStatus.UNHEALTHY,
            message=f"Signal connection timeout after {timeout}s",
            latency_ms=timeout * 1000,
        )
    except Exception as e:
        return ComponentHealth(
            name="signal",
            status=HealthStatus.UNHEALTHY,
            message=f"Signal connection failed: {str(e)}",
            latency_ms=(time.time() - start) * 1000,
        )


async def check_disk_space(
    path: str = "/",
    warning_threshold: float = 80.0,
    critical_threshold: float = 95.0
) -> ComponentHealth:
    """Check disk space availability."""
    start = time.time()
    
    try:
        if platform.system() == "Windows":
            # Windows disk usage
            usage = shutil.disk_usage(path)
            total = usage.total
            free = usage.free
            used = total - free
            percent_used = (used / total) * 100
        else:
            # Unix-like disk usage
            stat = os.statvfs(path)
            total = stat.f_blocks * stat.f_frsize
            free = stat.f_bavail * stat.f_frsize
            used = total - free
            percent_used = (used / total) * 100
        
        latency = (time.time() - start) * 1000
        
        # Determine status
        if percent_used >= critical_threshold:
            status = HealthStatus.UNHEALTHY
            message = f"CRITICAL: {percent_used:.1f}% disk usage"
        elif percent_used >= warning_threshold:
            status = HealthStatus.DEGRADED
            message = f"WARNING: {percent_used:.1f}% disk usage"
        else:
            status = HealthStatus.HEALTHY
            message = f"OK: {percent_used:.1f}% disk usage"
        
        return ComponentHealth(
            name="disk",
            status=status,
            message=message,
            latency_ms=latency,
            metadata={
                "path": path,
                "total_bytes": total,
                "used_bytes": used,
                "free_bytes": free,
                "percent_used": round(percent_used, 2),
            }
        )
    
    except Exception as e:
        return ComponentHealth(
            name="disk",
            status=HealthStatus.UNHEALTHY,
            message=f"Disk check failed: {str(e)}",
            latency_ms=(time.time() - start) * 1000,
        )


async def check_memory_usage(
    warning_threshold: float = 80.0,
    critical_threshold: float = 95.0
) -> ComponentHealth:
    """Check memory usage."""
    start = time.time()
    
    try:
        # Try psutil first
        try:
            import psutil
            mem = psutil.virtual_memory()
            total = mem.total
            available = mem.available
            percent_used = mem.percent
            
            metadata = {
                "total_bytes": total,
                "available_bytes": available,
                "used_bytes": mem.used,
                "percent_used": percent_used,
            }
        except ImportError:
            # Fallback to simple check on Unix
            if platform.system() != "Windows":
                with open('/proc/meminfo', 'r') as f:
                    lines = f.readlines()
                
                mem_info = {}
                for line in lines:
                    if ':' in line:
                        key, value = line.split(':', 1)
                        mem_info[key.strip()] = int(value.split()[0]) * 1024
                
                total = mem_info.get('MemTotal', 0)
                available = mem_info.get('MemAvailable', mem_info.get('MemFree', 0))
                percent_used = ((total - available) / total) * 100 if total > 0 else 0
                
                metadata = {
                    "total_bytes": total,
                    "available_bytes": available,
                    "percent_used": round(percent_used, 2),
                }
            else:
                raise RuntimeError("psutil required on Windows")
        
        latency = (time.time() - start) * 1000
        
        # Determine status
        if percent_used >= critical_threshold:
            status = HealthStatus.UNHEALTHY
            message = f"CRITICAL: {percent_used:.1f}% memory usage"
        elif percent_used >= warning_threshold:
            status = HealthStatus.DEGRADED
            message = f"WARNING: {percent_used:.1f}% memory usage"
        else:
            status = HealthStatus.HEALTHY
            message = f"OK: {percent_used:.1f}% memory usage"
        
        return ComponentHealth(
            name="memory",
            status=status,
            message=message,
            latency_ms=latency,
            metadata=metadata,
        )
    
    except Exception as e:
        return ComponentHealth(
            name="memory",
            status=HealthStatus.UNHEALTHY,
            message=f"Memory check failed: {str(e)}",
            latency_ms=(time.time() - start) * 1000,
        )


async def check_cpu_usage(
    warning_threshold: float = 80.0,
    critical_threshold: float = 95.0,
    interval: float = 0.1
) -> ComponentHealth:
    """Check CPU usage."""
    start = time.time()
    
    try:
        try:
            import psutil
            # Get CPU percent over interval
            percent_used = psutil.cpu_percent(interval=interval)
            
            # Get load average on Unix
            load_avg = None
            if hasattr(os, 'getloadavg'):
                load1, load5, load15 = os.getloadavg()
                load_avg = {"1m": load1, "5m": load5, "15m": load15}
            
            metadata = {
                "percent_used": round(percent_used, 2),
                "cpu_count": psutil.cpu_count(),
                "load_average": load_avg,
            }
        except ImportError:
            # Fallback to load average only
            if hasattr(os, 'getloadavg'):
                load1, load5, load15 = os.getloadavg()
                cpu_count = os.cpu_count() or 1
                percent_used = (load1 / cpu_count) * 100
                
                metadata = {
                    "percent_used": round(percent_used, 2),
                    "cpu_count": cpu_count,
                    "load_average": {"1m": load1, "5m": load5, "15m": load15},
                }
            else:
                raise RuntimeError("psutil required on Windows")
        
        latency = (time.time() - start) * 1000
        
        # Determine status
        if percent_used >= critical_threshold:
            status = HealthStatus.UNHEALTHY
            message = f"CRITICAL: {percent_used:.1f}% CPU usage"
        elif percent_used >= warning_threshold:
            status = HealthStatus.DEGRADED
            message = f"WARNING: {percent_used:.1f}% CPU usage"
        else:
            status = HealthStatus.HEALTHY
            message = f"OK: {percent_used:.1f}% CPU usage"
        
        return ComponentHealth(
            name="cpu",
            status=status,
            message=message,
            latency_ms=latency,
            metadata=metadata,
        )
    
    except Exception as e:
        return ComponentHealth(
            name="cpu",
            status=HealthStatus.UNHEALTHY,
            message=f"CPU check failed: {str(e)}",
            latency_ms=(time.time() - start) * 1000,
        )


async def check_tpv_store(data_dir: Optional[str] = None) -> ComponentHealth:
    """Check TPV (Thought-Preference-Value) store accessibility."""
    start = time.time()
    
    try:
        if data_dir is None:
            data_dir = Path.home() / ".cell0" / "data"
        else:
            data_dir = Path(data_dir)
        
        # Check if directory exists and is writable
        if not data_dir.exists():
            status = HealthStatus.DEGRADED
            message = f"TPV data directory does not exist: {data_dir}"
        elif not os.access(data_dir, os.W_OK):
            status = HealthStatus.UNHEALTHY
            message = f"TPV data directory not writable: {data_dir}"
        else:
            # Count TPV files
            tpv_files = list(data_dir.glob("*.json"))
            
            status = HealthStatus.HEALTHY
            message = f"TPV store accessible, {len(tpv_files)} entries"
        
        latency = (time.time() - start) * 1000
        
        return ComponentHealth(
            name="tpv_store",
            status=status,
            message=message,
            latency_ms=latency,
            metadata={
                "data_dir": str(data_dir),
                "exists": data_dir.exists(),
                "writable": os.access(data_dir, os.W_OK) if data_dir.exists() else False,
            }
        )
    
    except Exception as e:
        return ComponentHealth(
            name="tpv_store",
            status=HealthStatus.UNHEALTHY,
            message=f"TPV store check failed: {str(e)}",
            latency_ms=(time.time() - start) * 1000,
        )


async def check_websocket_gateway(
    gateway_host: str = "localhost",
    gateway_port: int = 18801,
    timeout: float = 5.0
) -> ComponentHealth:
    """Check WebSocket gateway connectivity."""
    start = time.time()
    
    try:
        import websockets
        
        uri = f"ws://{gateway_host}:{gateway_port}"
        
        async with websockets.connect(uri, timeout=timeout) as ws:
            latency = (time.time() - start) * 1000
            
            # Try to receive welcome message
            try:
                import json
                message = await asyncio.wait_for(ws.recv(), timeout=2.0)
                data = json.loads(message)
                
                return ComponentHealth(
                    name="websocket_gateway",
                    status=HealthStatus.HEALTHY,
                    message="WebSocket gateway responding",
                    latency_ms=latency,
                    metadata={
                        "host": gateway_host,
                        "port": gateway_port,
                        "server_version": data.get("params", {}).get("server_version", "unknown"),
                    }
                )
            except asyncio.TimeoutError:
                return ComponentHealth(
                    name="websocket_gateway",
                    status=HealthStatus.DEGRADED,
                    message="Connected but no welcome message received",
                    latency_ms=latency,
                )
    
    except Exception as e:
        return ComponentHealth(
            name="websocket_gateway",
            status=HealthStatus.UNHEALTHY,
            message=f"WebSocket gateway unreachable: {str(e)}",
            latency_ms=(time.time() - start) * 1000,
        )


async def check_agent_coordinator() -> ComponentHealth:
    """Check agent coordinator health."""
    start = time.time()
    
    try:
        from service.agent_coordinator import AgentCoordinator
        
        # Try to get stats from coordinator
        # This assumes a global coordinator instance or singleton pattern
        # In practice, you might need to pass the coordinator instance
        
        latency = (time.time() - start) * 1000
        
        return ComponentHealth(
            name="agent_coordinator",
            status=HealthStatus.HEALTHY,
            message="Agent coordinator operational",
            latency_ms=latency,
        )
    
    except ImportError:
        return ComponentHealth(
            name="agent_coordinator",
            status=HealthStatus.UNKNOWN,
            message="Agent coordinator not available",
            latency_ms=(time.time() - start) * 1000,
        )
    except Exception as e:
        return ComponentHealth(
            name="agent_coordinator",
            status=HealthStatus.UNHEALTHY,
            message=f"Agent coordinator error: {str(e)}",
            latency_ms=(time.time() - start) * 1000,
        )


# =============================================================================
# Health Check Registry
# =============================================================================

class HealthCheckRegistry:
    """Registry for health check functions."""
    
    def __init__(self):
        self._checks: Dict[str, HealthCheckFn] = {}
        self._version: str = "1.1.5"
        self._start_time: float = time.time()
    
    def register(self, name: str, check_fn: HealthCheckFn):
        """Register a health check function."""
        self._checks[name] = check_fn
    
    def unregister(self, name: str):
        """Unregister a health check."""
        self._checks.pop(name, None)
    
    async def run_check(self, name: str) -> Optional[ComponentHealth]:
        """Run a single health check."""
        check_fn = self._checks.get(name)
        if not check_fn:
            return None
        
        try:
            return await check_fn()
        except Exception as e:
            return ComponentHealth(
                name=name,
                status=HealthStatus.UNHEALTHY,
                message=f"Check failed with exception: {str(e)}",
            )
    
    async def run_all_checks(self) -> HealthReport:
        """Run all registered health checks."""
        components: List[ComponentHealth] = []
        
        # Run all checks concurrently
        results = await asyncio.gather(
            *[self.run_check(name) for name in self._checks.keys()],
            return_exceptions=True
        )
        
        for result in results:
            if isinstance(result, ComponentHealth):
                components.append(result)
            elif isinstance(result, Exception):
                components.append(ComponentHealth(
                    name="unknown",
                    status=HealthStatus.UNHEALTHY,
                    message=f"Check failed: {str(result)}",
                ))
        
        # Determine overall status
        statuses = [c.status for c in components]
        
        if HealthStatus.UNHEALTHY in statuses:
            overall_status = HealthStatus.UNHEALTHY
        elif HealthStatus.DEGRADED in statuses:
            overall_status = HealthStatus.DEGRADED
        elif all(s == HealthStatus.HEALTHY for s in statuses):
            overall_status = HealthStatus.HEALTHY
        else:
            overall_status = HealthStatus.UNKNOWN
        
        return HealthReport(
            status=overall_status,
            timestamp=datetime.utcnow().isoformat() + "Z",
            version=self._version,
            uptime_seconds=time.time() - self._start_time,
            components=components,
        )
    
    def get_basic_health(self) -> Dict[str, Any]:
        """Get basic health status (fast, no external checks)."""
        uptime = time.time() - self._start_time
        
        return {
            "status": HealthStatus.HEALTHY.value,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "version": self._version,
            "uptime_seconds": round(uptime, 2),
        }


# Global registry instance
health_registry = HealthCheckRegistry()

# Register default checks
health_registry.register("ollama", check_ollama_health)
health_registry.register("signal", check_signal_health)
health_registry.register("disk", check_disk_space)
health_registry.register("memory", check_memory_usage)
health_registry.register("cpu", check_cpu_usage)
health_registry.register("tpv_store", check_tpv_store)
health_registry.register("websocket_gateway", check_websocket_gateway)


# =============================================================================
# HTTP Handlers
# =============================================================================

async def basic_health_handler(request=None) -> tuple:
    """
    Handler for basic health check (/api/health).
    
    Returns:
        Tuple of (body, status_code, headers)
    """
    health = health_registry.get_basic_health()
    
    body = health
    status_code = 200
    headers = {"Content-Type": "application/json"}
    
    return (body, status_code, headers)


async def deep_health_handler(request=None) -> tuple:
    """
    Handler for deep health check (/api/health/deep).
    
    Returns:
        Tuple of (body, status_code, headers)
    """
    report = await health_registry.run_all_checks()
    
    body = report.to_dict()
    status_code = report.http_status_code
    headers = {"Content-Type": "application/json"}
    
    return (body, status_code, headers)


async def readiness_handler(request=None) -> tuple:
    """
    Handler for Kubernetes readiness probe.
    
    Returns 200 if ready to receive traffic, 503 otherwise.
    """
    # For readiness, check essential services
    checks_to_run = ["ollama", "tpv_store"]
    
    components = []
    for check_name in checks_to_run:
        result = await health_registry.run_check(check_name)
        if result:
            components.append(result)
    
    # Ready if all essential services are healthy
    is_ready = all(c.status == HealthStatus.HEALTHY for c in components)
    
    body = {
        "ready": is_ready,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "checks": [c.to_dict() for c in components],
    }
    
    status_code = 200 if is_ready else 503
    headers = {"Content-Type": "application/json"}
    
    return (body, status_code, headers)


async def liveness_handler(request=None) -> tuple:
    """
    Handler for Kubernetes liveness probe.
    
    Returns 200 if alive, 500 if should be restarted.
    """
    # Liveness is simple - if we can respond, we're alive
    body = {
        "alive": True,
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }
    
    return (body, 200, {"Content-Type": "application/json"})


async def startup_handler(request=None) -> tuple:
    """
    Handler for Kubernetes startup probe.
    
    Returns 200 if started successfully, 503 if still starting.
    """
    uptime = time.time() - health_registry._start_time
    
    # Consider started after 10 seconds
    is_started = uptime > 10
    
    body = {
        "started": is_started,
        "uptime_seconds": round(uptime, 2),
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }
    
    status_code = 200 if is_started else 503
    headers = {"Content-Type": "application/json"}
    
    return (body, status_code, headers)


# =============================================================================
# Integration Helpers
# =============================================================================

def setup_health_routes_aiohttp(app):
    """Setup health check routes for aiohttp application."""
    if not AIOHTTP_AVAILABLE:
        raise RuntimeError("aiohttp is required")
    
    async def _basic_handler(request):
        body, status, headers = await basic_health_handler(request)
        return web.json_response(body, status=status, headers=headers)
    
    async def _deep_handler(request):
        body, status, headers = await deep_health_handler(request)
        return web.json_response(body, status=status, headers=headers)
    
    async def _readiness_handler(request):
        body, status, headers = await readiness_handler(request)
        return web.json_response(body, status=status, headers=headers)
    
    async def _liveness_handler(request):
        body, status, headers = await liveness_handler(request)
        return web.json_response(body, status=status, headers=headers)
    
    async def _startup_handler(request):
        body, status, headers = await startup_handler(request)
        return web.json_response(body, status=status, headers=headers)
    
    app.router.add_get("/api/health", _basic_handler)
    app.router.add_get("/api/health/deep", _deep_handler)
    app.router.add_get("/healthz", _readiness_handler)  # K8s readiness
    app.router.add_get("/livez", _liveness_handler)     # K8s liveness
    app.router.add_get("/readyz", _readiness_handler)   # K8s readiness alt
    app.router.add_get("/startupz", _startup_handler)   # K8s startup


def setup_health_routes_fastapi(app):
    """Setup health check routes for FastAPI application."""
    if not FASTAPI_AVAILABLE:
        raise RuntimeError("FastAPI is required")
    
    from fastapi import Response
    import json
    
    @app.get("/api/health")
    async def health():
        body, status, headers = await basic_health_handler()
        return Response(
            content=json.dumps(body),
            status_code=status,
            headers=headers
        )
    
    @app.get("/api/health/deep")
    async def health_deep():
        body, status, headers = await deep_health_handler()
        return Response(
            content=json.dumps(body),
            status_code=status,
            headers=headers
        )
    
    @app.get("/healthz")
    async def readiness():
        body, status, headers = await readiness_handler()
        return Response(
            content=json.dumps(body),
            status_code=status,
            headers=headers
        )
    
    @app.get("/livez")
    async def liveness():
        body, status, headers = await liveness_handler()
        return Response(
            content=json.dumps(body),
            status_code=status,
            headers=headers
        )
    
    @app.get("/readyz")
    async def readyz():
        body, status, headers = await readiness_handler()
        return Response(
            content=json.dumps(body),
            status_code=status,
            headers=headers
        )
