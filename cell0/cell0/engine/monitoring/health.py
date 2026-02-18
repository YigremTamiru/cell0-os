"""
health.py - Health Check System for Cell 0 OS

Provides comprehensive health checking for:
- Basic health (liveness)
- Deep health (readiness with component checks)
- Individual component health
- Kubernetes probe compatibility
"""

import os
import time
import asyncio
from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Callable, Any
from datetime import datetime


class HealthStatus(Enum):
    """Health status enumeration"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


@dataclass
class ComponentHealth:
    """Health status for a single component"""
    name: str
    status: HealthStatus
    message: str = ""
    timestamp: datetime = field(default_factory=datetime.utcnow)
    latency_ms: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "status": self.status.value,
            "message": self.message,
            "timestamp": self.timestamp.isoformat() + "Z",
            "latency_ms": self.latency_ms,
            "metadata": self.metadata
        }


@dataclass
class HealthReport:
    """Complete health report"""
    overall: HealthStatus
    components: Dict[str, ComponentHealth]
    timestamp: datetime = field(default_factory=datetime.utcnow)
    version: str = "1.2.0"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "status": self.overall.value,
            "version": self.version,
            "timestamp": self.timestamp.isoformat() + "Z",
            "components": {
                name: comp.to_dict()
                for name, comp in self.components.items()
            }
        }


class HealthChecker:
    """Health checker for Cell 0 OS components"""
    
    def __init__(self):
        self.checks: Dict[str, Callable] = {}
        self.results: Dict[str, ComponentHealth] = {}
        self._last_check: Optional[datetime] = None
        self._cache_duration = 5  # Cache results for 5 seconds
    
    def register_check(self, name: str, check_func: Callable) -> None:
        """
        Register a health check function
        
        Args:
            name: Component name
            check_func: Async function that returns ComponentHealth
        """
        self.checks[name] = check_func
    
    async def initialize(self) -> None:
        """Initialize the health checker with default checks"""
        # Register default checks
        self.register_check("ollama", self._check_ollama)
        self.register_check("signal", self._check_signal)
        self.register_check("disk", self._check_disk)
        self.register_check("memory", self._check_memory)
        self.register_check("tpv_store", self._check_tpv_store)
    
    async def check_all(self) -> HealthReport:
        """Run all health checks and return report"""
        # Check cache
        if self._last_check and self._cache_duration > 0:
            elapsed = (datetime.utcnow() - self._last_check).total_seconds()
            if elapsed < self._cache_duration:
                return HealthReport(
                    overall=self._calculate_overall(),
                    components=self.results
                )
        
        # Run all checks concurrently
        tasks = []
        for name, check_func in self.checks.items():
            task = self._run_check(name, check_func)
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        self.results = {}
        for name, result in zip(self.checks.keys(), results):
            if isinstance(result, Exception):
                self.results[name] = ComponentHealth(
                    name=name,
                    status=HealthStatus.UNHEALTHY,
                    message=f"Check failed: {str(result)}"
                )
            else:
                self.results[name] = result
        
        self._last_check = datetime.utcnow()
        
        return HealthReport(
            overall=self._calculate_overall(),
            components=self.results
        )
    
    async def _run_check(self, name: str, check_func: Callable) -> ComponentHealth:
        """Run a single health check with timeout"""
        start = time.time()
        try:
            # Run check with 10 second timeout
            result = await asyncio.wait_for(check_func(), timeout=10.0)
            result.latency_ms = (time.time() - start) * 1000
            return result
        except asyncio.TimeoutError:
            return ComponentHealth(
                name=name,
                status=HealthStatus.UNHEALTHY,
                message="Health check timed out",
                latency_ms=(time.time() - start) * 1000
            )
        except Exception as e:
            return ComponentHealth(
                name=name,
                status=HealthStatus.UNHEALTHY,
                message=f"Check error: {str(e)}",
                latency_ms=(time.time() - start) * 1000
            )
    
    def _calculate_overall(self) -> HealthStatus:
        """Calculate overall health from component results"""
        if not self.results:
            return HealthStatus.UNKNOWN
        
        statuses = [r.status for r in self.results.values()]
        
        if any(s == HealthStatus.UNHEALTHY for s in statuses):
            return HealthStatus.UNHEALTHY
        elif any(s == HealthStatus.DEGRADED for s in statuses):
            return HealthStatus.DEGRADED
        elif all(s == HealthStatus.HEALTHY for s in statuses):
            return HealthStatus.HEALTHY
        else:
            return HealthStatus.UNKNOWN
    
    # Default health checks
    
    async def _check_ollama(self) -> ComponentHealth:
        """Check Ollama service health"""
        try:
            import aiohttp
            
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    "http://localhost:11434/api/tags",
                    timeout=aiohttp.ClientTimeout(total=5)
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        models = len(data.get("models", []))
                        return ComponentHealth(
                            name="ollama",
                            status=HealthStatus.HEALTHY,
                            message=f"Ollama running with {models} models",
                            metadata={"models_available": models}
                        )
                    else:
                        return ComponentHealth(
                            name="ollama",
                            status=HealthStatus.UNHEALTHY,
                            message=f"Ollama returned status {resp.status}"
                        )
        except aiohttp.ClientError as e:
            return ComponentHealth(
                name="ollama",
                status=HealthStatus.UNHEALTHY,
                message=f"Cannot connect to Ollama: {str(e)}"
            )
        except ImportError:
            return ComponentHealth(
                name="ollama",
                status=HealthStatus.UNKNOWN,
                message="aiohttp not installed"
            )
    
    async def _check_signal(self) -> ComponentHealth:
        """Check Signal integration health"""
        # Check if Signal config exists
        signal_config = os.path.expanduser("~/.cell0/signal/config.json")
        
        if not os.path.exists(signal_config):
            return ComponentHealth(
                name="signal",
                status=HealthStatus.UNKNOWN,
                message="Signal not configured"
            )
        
        # Try to check Signal daemon if running
        try:
            import subprocess  # nosec B404 - intentional subprocess usage for health check
            result = subprocess.run(
                ["pgrep", "-f", "signal-cli"],  # nosec B607, B603 - hardcoded safe command for health check
                capture_output=True,
                timeout=2
            )
            if result.returncode == 0:
                return ComponentHealth(
                    name="signal",
                    status=HealthStatus.HEALTHY,
                    message="Signal daemon running"
                )
            else:
                return ComponentHealth(
                    name="signal",
                    status=HealthStatus.DEGRADED,
                    message="Signal daemon not running"
                )
        except Exception as e:
            return ComponentHealth(
                name="signal",
                status=HealthStatus.UNKNOWN,
                message=f"Cannot check Signal: {str(e)}"
            )
    
    async def _check_disk(self) -> ComponentHealth:
        """Check disk space"""
        try:
            import shutil
            
            stat = shutil.disk_usage("/")
            free_gb = stat.free / (1024**3)
            used_percent = (stat.used / stat.total) * 100
            
            if used_percent > 95:
                status = HealthStatus.UNHEALTHY
            elif used_percent > 85:
                status = HealthStatus.DEGRADED
            else:
                status = HealthStatus.HEALTHY
            
            return ComponentHealth(
                name="disk",
                status=status,
                message=f"{free_gb:.1f}GB free ({used_percent:.1f}% used)",
                metadata={
                    "free_bytes": stat.free,
                    "total_bytes": stat.total,
                    "used_percent": used_percent
                }
            )
        except Exception as e:
            return ComponentHealth(
                name="disk",
                status=HealthStatus.UNKNOWN,
                message=f"Cannot check disk: {str(e)}"
            )
    
    async def _check_memory(self) -> ComponentHealth:
        """Check memory usage"""
        try:
            import psutil
            
            memory = psutil.virtual_memory()
            available_gb = memory.available / (1024**3)
            
            if memory.percent > 95:
                status = HealthStatus.UNHEALTHY
            elif memory.percent > 85:
                status = HealthStatus.DEGRADED
            else:
                status = HealthStatus.HEALTHY
            
            return ComponentHealth(
                name="memory",
                status=status,
                message=f"{available_gb:.1f}GB available ({memory.percent}% used)",
                metadata={
                    "available_bytes": memory.available,
                    "total_bytes": memory.total,
                    "used_percent": memory.percent
                }
            )
        except ImportError:
            return ComponentHealth(
                name="memory",
                status=HealthStatus.UNKNOWN,
                message="psutil not installed"
            )
    
    async def _check_tpv_store(self) -> ComponentHealth:
        """Check TPV store health"""
        tpv_dir = os.path.expanduser("~/.cell0/tpv")
        
        if not os.path.exists(tpv_dir):
            return ComponentHealth(
                name="tpv_store",
                status=HealthStatus.HEALTHY,  # Not configured is OK
                message="TPV store not yet initialized"
            )
        
        # Count TPV files
        try:
            tpv_files = len([f for f in os.listdir(tpv_dir) if f.endswith(".json")])
            return ComponentHealth(
                name="tpv_store",
                status=HealthStatus.HEALTHY,
                message=f"TPV store active with {tpv_files} profiles",
                metadata={"profile_count": tpv_files}
            )
        except Exception as e:
            return ComponentHealth(
                name="tpv_store",
                status=HealthStatus.UNHEALTHY,
                message=f"Cannot read TPV store: {str(e)}"
            )


# Global health checker instance
_health_checker: Optional[HealthChecker] = None


def get_health_checker() -> HealthChecker:
    """Get the global health checker instance"""
    global _health_checker
    if _health_checker is None:
        _health_checker = HealthChecker()
    return _health_checker
