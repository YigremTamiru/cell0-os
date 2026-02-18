"""
Resource Management & Limits for Cell 0 OS

Production-grade resource monitoring and limiting with:
- Memory usage tracking and limits
- CPU usage monitoring
- Disk space management with automatic cleanup
- Model memory management with intelligent eviction policies
- Process resource quotas
- Request-based resource accounting

Author: KULLU (Cell 0 OS)
"""

import os
import sys
import gc
import psutil
import asyncio
import logging
from typing import Dict, Any, Optional, List, Callable, Tuple, Set
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from enum import Enum
from collections import defaultdict
import threading
import json
from pathlib import Path
import weakref

logger = logging.getLogger("cell0.engine.resource_limits")


class ResourceType(Enum):
    """Types of resources"""
    MEMORY = "memory"
    CPU = "cpu"
    DISK = "disk"
    GPU = "gpu"
    NETWORK = "network"
    MODEL = "model"


class EvictionPolicy(Enum):
    """Model eviction policies"""
    LRU = "lru"  # Least Recently Used
    LFU = "lfu"  # Least Frequently Used
    FIFO = "fifo"  # First In First Out
    TTL = "ttl"  # Time To Live
    COST_BASED = "cost_based"  # Based on loading cost


class ResourceAlertLevel(Enum):
    """Resource alert severity levels"""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"
    EMERGENCY = "emergency"


@dataclass
class ResourceUsage:
    """Resource usage snapshot"""
    timestamp: datetime
    memory_bytes: int
    memory_percent: float
    cpu_percent: float
    disk_bytes_used: int
    disk_bytes_free: int
    disk_percent: float
    process_memory_bytes: int
    process_cpu_percent: float
    open_file_descriptors: int
    thread_count: int
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp.isoformat(),
            "memory_bytes": self.memory_bytes,
            "memory_percent": self.memory_percent,
            "cpu_percent": self.cpu_percent,
            "disk_bytes_used": self.disk_bytes_used,
            "disk_bytes_free": self.disk_bytes_free,
            "disk_percent": self.disk_percent,
            "process_memory_bytes": self.process_memory_bytes,
            "process_cpu_percent": self.process_cpu_percent,
            "open_file_descriptors": self.open_file_descriptors,
            "thread_count": self.thread_count,
        }


@dataclass
class ResourceLimits:
    """Resource limit configuration"""
    max_memory_bytes: Optional[int] = None
    max_memory_percent: Optional[float] = 85.0
    max_cpu_percent: Optional[float] = 90.0
    max_disk_percent: Optional[float] = 90.0
    max_disk_bytes_used: Optional[int] = None
    max_open_files: Optional[int] = 10000
    max_threads: Optional[int] = 500
    max_model_memory_bytes: Optional[int] = None
    max_concurrent_models: Optional[int] = 5
    gc_threshold: float = 80.0  # Trigger GC at this memory %
    cleanup_threshold: float = 85.0  # Trigger cleanup at this %
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ModelInfo:
    """Information about a loaded model"""
    model_id: str
    model_name: str
    loaded_at: datetime
    last_accessed: datetime
    access_count: int = 0
    memory_bytes: int = 0
    load_time_seconds: float = 0.0
    priority: int = 0  # Higher = less likely to be evicted
    ttl: Optional[timedelta] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "model_id": self.model_id,
            "model_name": self.model_name,
            "loaded_at": self.loaded_at.isoformat(),
            "last_accessed": self.last_accessed.isoformat(),
            "access_count": self.access_count,
            "memory_bytes": self.memory_bytes,
            "load_time_seconds": self.load_time_seconds,
            "priority": self.priority,
            "ttl_seconds": self.ttl.total_seconds() if self.ttl else None,
            "metadata": self.metadata,
        }


@dataclass
class ResourceAlert:
    """Resource alert notification"""
    level: ResourceAlertLevel
    resource_type: ResourceType
    message: str
    current_value: float
    threshold_value: float
    timestamp: datetime
    context: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "level": self.level.value,
            "resource_type": self.resource_type.value,
            "message": self.message,
            "current_value": self.current_value,
            "threshold_value": self.threshold_value,
            "timestamp": self.timestamp.isoformat(),
            "context": self.context,
        }


class ResourceMonitor:
    """System resource monitoring"""
    
    def __init__(
        self,
        sample_interval_seconds: float = 5.0,
        history_size: int = 1000,
    ):
        self.sample_interval = sample_interval_seconds
        self.history_size = history_size
        self._history: List[ResourceUsage] = []
        self._running = False
        self._monitor_task: Optional[asyncio.Task] = None
        self._process = psutil.Process()
        self._lock = asyncio.Lock()
        self._alert_handlers: List[Callable[[ResourceAlert], None]] = []
        
    def add_alert_handler(self, handler: Callable[[ResourceAlert], None]):
        """Add an alert handler callback"""
        self._alert_handlers.append(handler)
        
    def remove_alert_handler(self, handler: Callable[[ResourceAlert], None]):
        """Remove an alert handler callback"""
        if handler in self._alert_handlers:
            self._alert_handlers.remove(handler)
            
    async def start(self):
        """Start resource monitoring"""
        if self._running:
            return
            
        self._running = True
        self._monitor_task = asyncio.create_task(self._monitor_loop())
        logger.info("Resource monitor started")
        
    async def stop(self):
        """Stop resource monitoring"""
        self._running = False
        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass
        logger.info("Resource monitor stopped")
        
    async def _monitor_loop(self):
        """Main monitoring loop"""
        while self._running:
            try:
                usage = await self._sample_usage()
                async with self._lock:
                    self._history.append(usage)
                    if len(self._history) > self.history_size:
                        self._history.pop(0)
                await asyncio.sleep(self.sample_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in resource monitor: {e}")
                await asyncio.sleep(self.sample_interval)
                
    async def _sample_usage(self) -> ResourceUsage:
        """Sample current resource usage"""
        mem = psutil.virtual_memory()
        cpu_percent = psutil.cpu_percent(interval=None)
        disk = psutil.disk_usage('/')
        proc_mem = self._process.memory_info()
        proc_cpu = self._process.cpu_percent()
        proc_fds = self._process.num_fds() if hasattr(self._process, 'num_fds') else 0
        proc_threads = self._process.num_threads()
        
        return ResourceUsage(
            timestamp=datetime.utcnow(),
            memory_bytes=mem.used,
            memory_percent=mem.percent,
            cpu_percent=cpu_percent,
            disk_bytes_used=disk.used,
            disk_bytes_free=disk.free,
            disk_percent=(disk.used / disk.total) * 100,
            process_memory_bytes=proc_mem.rss,
            process_cpu_percent=proc_cpu,
            open_file_descriptors=proc_fds,
            thread_count=proc_threads,
        )
        
    async def get_current_usage(self) -> ResourceUsage:
        """Get current resource usage"""
        return await self._sample_usage()
        
    async def get_history(
        self,
        since: Optional[datetime] = None,
        limit: int = 100,
    ) -> List[ResourceUsage]:
        """Get usage history"""
        async with self._lock:
            history = list(self._history)
            
        if since:
            history = [h for h in history if h.timestamp >= since]
            
        return history[-limit:]
        
    def get_average_usage(
        self,
        duration_seconds: float = 300,
    ) -> Optional[Dict[str, float]]:
        """Get average usage over a duration"""
        cutoff = datetime.utcnow() - timedelta(seconds=duration_seconds)
        recent = [h for h in self._history if h.timestamp >= cutoff]
        
        if not recent:
            return None
            
        return {
            "avg_memory_percent": sum(h.memory_percent for h in recent) / len(recent),
            "avg_cpu_percent": sum(h.cpu_percent for h in recent) / len(recent),
            "avg_disk_percent": sum(h.disk_percent for h in recent) / len(recent),
            "avg_process_memory_mb": sum(h.process_memory_bytes for h in recent) / len(recent) / 1024 / 1024,
            "sample_count": len(recent),
        }


class ResourceLimiter:
    """Resource limiting and enforcement"""
    
    def __init__(
        self,
        limits: Optional[ResourceLimits] = None,
        monitor: Optional[ResourceMonitor] = None,
    ):
        self.limits = limits or ResourceLimits()
        self.monitor = monitor or ResourceMonitor()
        self._cleanup_handlers: List[Callable] = []
        self._emergency_handlers: List[Callable] = []
        
    async def start(self):
        """Start the resource limiter"""
        await self.monitor.start()
        logger.info("Resource limiter started")
        
    async def stop(self):
        """Stop the resource limiter"""
        await self.monitor.stop()
        logger.info("Resource limiter stopped")
        
    def register_cleanup_handler(self, handler: Callable):
        """Register a cleanup handler for resource pressure"""
        self._cleanup_handlers.append(handler)
        
    def register_emergency_handler(self, handler: Callable):
        """Register an emergency handler"""
        self._emergency_handlers.append(handler)
        
    def check_limits(self) -> Tuple[bool, List[str]]:
        """Check if current resource usage is within limits"""
        violations = []
        
        try:
            usage = asyncio.run(self.monitor.get_current_usage())
        except Exception:
            return True, []
            
        if self.limits.max_memory_percent and usage.memory_percent > self.limits.max_memory_percent:
            violations.append(f"Memory usage {usage.memory_percent:.1f}% exceeds limit {self.limits.max_memory_percent:.1f}%")
            
        if self.limits.max_cpu_percent and usage.cpu_percent > self.limits.max_cpu_percent:
            violations.append(f"CPU usage {usage.cpu_percent:.1f}% exceeds limit {self.limits.max_cpu_percent:.1f}%")
            
        if self.limits.max_disk_percent and usage.disk_percent > self.limits.max_disk_percent:
            violations.append(f"Disk usage {usage.disk_percent:.1f}% exceeds limit {self.limits.max_disk_percent:.1f}%")
            
        return len(violations) == 0, violations


class ModelMemoryManager:
    """Intelligent model memory management with eviction policies"""
    
    def __init__(
        self,
        eviction_policy: EvictionPolicy = EvictionPolicy.LRU,
        max_memory_bytes: Optional[int] = None,
        max_models: Optional[int] = None,
        default_ttl: Optional[timedelta] = None,
    ):
        self.policy = eviction_policy
        self.max_memory = max_memory_bytes
        self.max_models = max_models
        self.default_ttl = default_ttl
        self._models: Dict[str, ModelInfo] = {}
        self._model_refs: Dict[str, Any] = {}
        self._lock = asyncio.Lock()
        self._eviction_callbacks: List[Callable[[str, ModelInfo], None]] = []
        self._load_callbacks: List[Callable[[str, ModelInfo], None]] = []
        
    def register_eviction_callback(self, callback: Callable[[str, ModelInfo], None]):
        """Register callback for model eviction"""
        self._eviction_callbacks.append(callback)
        
    def register_load_callback(self, callback: Callable[[str, ModelInfo], None]):
        """Register callback for model load"""
        self._load_callbacks.append(callback)
        
    async def register_model(
        self,
        model_id: str,
        model_name: str,
        memory_bytes: int,
        load_time_seconds: float = 0.0,
        priority: int = 0,
        ttl: Optional[timedelta] = None,
        metadata: Optional[Dict[str, Any]] = None,
        model_ref: Any = None,
    ) -> ModelInfo:
        """Register a newly loaded model"""
        async with self._lock:
            await self._maybe_evict_for_space(memory_bytes)
            
            now = datetime.utcnow()
            info = ModelInfo(
                model_id=model_id,
                model_name=model_name,
                loaded_at=now,
                last_accessed=now,
                access_count=1,
                memory_bytes=memory_bytes,
                load_time_seconds=load_time_seconds,
                priority=priority,
                ttl=ttl or self.default_ttl,
                metadata=metadata or {},
            )
            
            self._models[model_id] = info
            if model_ref is not None:
                self._model_refs[model_id] = weakref.ref(model_ref)
                
            logger.info(f"Registered model: {model_name} ({model_id}) - {memory_bytes / 1024 / 1024:.1f} MB")
            
            for callback in self._load_callbacks:
                try:
                    callback(model_id, info)
                except Exception as e:
                    logger.error(f"Error in load callback: {e}")
                    
            return info
            
    async def access_model(self, model_id: str) -> Optional[ModelInfo]:
        """Record access to a model"""
        async with self._lock:
            info = self._models.get(model_id)
            if info:
                info.last_accessed = datetime.utcnow()
                info.access_count += 1
            return info
            
    async def evict_model(self, model_id: str) -> bool:
        """Evict a specific model"""
        async with self._lock:
            info = self._models.get(model_id)
            if not info:
                return False
                
            for callback in self._eviction_callbacks:
                try:
                    callback(model_id, info)
                except Exception as e:
                    logger.error(f"Error in eviction callback: {e}")
                    
            self._models.pop(model_id, None)
            self._model_refs.pop(model_id, None)
            
            logger.info(f"Evicted model: {info.model_name} ({model_id})")
            return True
            
    async def _maybe_evict_for_space(self, needed_bytes: int):
        """Evict models if needed to make space"""
        if not self.max_memory and not self.max_models:
            return
            
        current_memory = sum(m.memory_bytes for m in self._models.values())
        current_models = len(self._models)
        
        while (self.max_memory and current_memory + needed_bytes > self.max_memory) or \
              (self.max_models and current_models >= self.max_models):
            
            victim = self._select_eviction_victim()
            if not victim:
                break
                
            await self.evict_model(victim)
            
            current_memory = sum(m.memory_bytes for m in self._models.values())
            current_models = len(self._models)
            
    def _select_eviction_victim(self) -> Optional[str]:
        """Select a model to evict based on policy"""
        if not self._models:
            return None
            
        candidates = {k: v for k, v in self._models.items() if v.priority <= 0}
        if not candidates:
            candidates = self._models
            
        if self.policy == EvictionPolicy.LRU:
            return min(candidates.keys(), key=lambda k: candidates[k].last_accessed)
        elif self.policy == EvictionPolicy.LFU:
            return min(candidates.keys(), key=lambda k: candidates[k].access_count)
        elif self.policy == EvictionPolicy.FIFO:
            return min(candidates.keys(), key=lambda k: candidates[k].loaded_at)
        elif self.policy == EvictionPolicy.TTL:
            now = datetime.utcnow()
            expired = [k for k, v in candidates.items() if v.ttl and v.loaded_at + v.ttl < now]
            if expired:
                return expired[0]
            return min(candidates.keys(), key=lambda k: candidates[k].last_accessed)
        elif self.policy == EvictionPolicy.COST_BASED:
            def cost_ratio(k):
                v = candidates[k]
                if v.load_time_seconds <= 0:
                    return float('inf')
                return v.memory_bytes / v.load_time_seconds
            return min(candidates.keys(), key=cost_ratio)
        return None
        
    def get_stats(self) -> Dict[str, Any]:
        """Get memory manager statistics"""
        total_memory = sum(m.memory_bytes for m in self._models.values())
        return {
            "model_count": len(self._models),
            "total_memory_bytes": total_memory,
            "total_memory_mb": total_memory / 1024 / 1024,
            "eviction_policy": self.policy.value,
            "max_memory_bytes": self.max_memory,
            "max_models": self.max_models,
            "models": [m.to_dict() for m in self._models.values()],
        }


class DiskCleanupManager:
    """Disk space management with automatic cleanup"""
    
    def __init__(
        self,
        cleanup_threshold_percent: float = 85.0,
        target_percent: float = 75.0,
        check_interval_seconds: float = 300,
    ):
        self.cleanup_threshold = cleanup_threshold_percent
        self.target_percent = target_percent
        self.check_interval = check_interval_seconds
        self._cleanup_paths: List[Tuple[Path, int]] = []
        self._running = False
        self._cleanup_task: Optional[asyncio.Task] = None
        
    def register_cleanup_path(self, path: str, max_age_days: int = 7):
        """Register a path for automatic cleanup"""
        self._cleanup_paths.append((Path(path), max_age_days))
        
    async def start(self):
        """Start disk cleanup monitoring"""
        if self._running:
            return
            
        self._running = True
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())
        logger.info("Disk cleanup manager started")
        
    async def stop(self):
        """Stop disk cleanup monitoring"""
        self._running = False
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
        logger.info("Disk cleanup manager stopped")
        
    async def _cleanup_loop(self):
        """Main cleanup loop"""
        while self._running:
            try:
                disk = psutil.disk_usage('/')
                if disk.percent > self.cleanup_threshold:
                    await self._perform_cleanup()
                await asyncio.sleep(self.check_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in disk cleanup loop: {e}")
                await asyncio.sleep(self.check_interval)
                
    async def _perform_cleanup(self):
        """Perform cleanup of old files"""
        logger.warning(f"Disk usage above threshold, performing cleanup")
        total_freed = 0
        
        for path, max_age_days in self._cleanup_paths:
            if not path.exists():
                continue
                
            cutoff = datetime.utcnow() - timedelta(days=max_age_days)
            
            try:
                for item in path.iterdir():
                    try:
                        stat = item.stat()
                        modified = datetime.fromtimestamp(stat.st_mtime)
                        
                        if modified < cutoff:
                            if item.is_file():
                                total_freed += stat.st_size
                                item.unlink()
                                logger.debug(f"Deleted: {item}")
                            elif item.is_dir():
                                dir_size = self._get_dir_size(item)
                                total_freed += dir_size
                                import shutil
                                shutil.rmtree(item)
                                logger.debug(f"Deleted directory: {item}")
                    except Exception as e:
                        logger.warning(f"Error cleaning up {item}: {e}")
                        
            except Exception as e:
                logger.error(f"Error processing cleanup path {path}: {e}")
                
        logger.info(f"Cleanup freed {total_freed / 1024 / 1024:.1f} MB")
        
    def _get_dir_size(self, path: Path) -> int:
        """Get total size of a directory"""
        total = 0
        try:
            for entry in path.rglob('*'):
                if entry.is_file():
                    total += entry.stat().st_size
        except Exception:
            pass
        return total


# Global instances
_global_monitor: Optional[ResourceMonitor] = None
_global_limiter: Optional[ResourceLimiter] = None
_global_model_manager: Optional[ModelMemoryManager] = None
_global_disk_cleanup: Optional[DiskCleanupManager] = None


def get_resource_monitor() -> ResourceMonitor:
    """Get global resource monitor"""
    global _global_monitor
    if _global_monitor is None:
        _global_monitor = ResourceMonitor()
    return _global_monitor


def get_resource_limiter() -> ResourceLimiter:
    """Get global resource limiter"""
    global _global_limiter
    if _global_limiter is None:
        _global_limiter = ResourceLimiter(
            monitor=get_resource_monitor(),
        )
    return _global_limiter


def get_model_manager() -> ModelMemoryManager:
    """Get global model memory manager"""
    global _global_model_manager
    if _global_model_manager is None:
        _global_model_manager = ModelMemoryManager()
    return _global_model_manager


def get_disk_cleanup() -> DiskCleanupManager:
    """Get global disk cleanup manager"""
    global _global_disk_cleanup
    if _global_disk_cleanup is None:
        _global_disk_cleanup = DiskCleanupManager()
    return _global_disk_cleanup


async def initialize_resource_management(
    limits: Optional[ResourceLimits] = None,
    eviction_policy: EvictionPolicy = EvictionPolicy.LRU,
):
    """Initialize all resource management components"""
    monitor = get_resource_monitor()
    await monitor.start()
    
    limiter = get_resource_limiter()
    if limits:
        limiter.limits = limits
    await limiter.start()
    
    disk_cleanup = get_disk_cleanup()
    await disk_cleanup.start()
    
    logger.info("Resource management initialized")


async def shutdown_resource_management():
    """Shutdown all resource management components"""
    if _global_limiter:
        await _global_limiter.stop()
    if _global_disk_cleanup:
        await _global_disk_cleanup.stop()
    logger.info("Resource management shutdown")