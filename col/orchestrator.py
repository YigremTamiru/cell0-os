"""
COL Orchestrator Module - Cell 0 OS
The Cognitive Operating Layer that governs all operations.

Architecture: STOP → CLASSIFY → LOAD → APPLY → EXECUTE
This module intercepts ALL operations before execution.
"""

import asyncio
import functools
import inspect
import json
import os
import threading
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Type, Union
from contextlib import contextmanager
import weakref

from .classifier import RequestClassifier, ClassificationResult, RequestType
from .protocol_loader import ProtocolLoader, Protocol
from .token_economy import TokenEconomy, TokenBudget, TokenTransaction
from .checkpoint import CheckpointManager, Checkpoint


class OrchestratorState(Enum):
    """Orchestrator runtime states."""
    STOPPED = auto()
    INITIALIZING = auto()
    ACTIVE = auto()
    GOVERNANCE = auto()
    EXECUTING = auto()
    CHECKPOINTING = auto()
    SHUTTING_DOWN = auto()


@dataclass
class OperationContext:
    """Context for any operation passing through COL."""
    operation_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    timestamp: datetime = field(default_factory=datetime.utcnow)
    source: str = "unknown"
    classification: Optional[ClassificationResult] = None
    protocol_id: Optional[str] = None
    token_budget: Optional[TokenBudget] = None
    checkpoint_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    execution_trace: List[Dict] = field(default_factory=list)
    
    def trace(self, phase: str, data: Dict[str, Any]):
        """Add execution trace entry."""
        self.execution_trace.append({
            "phase": phase,
            "timestamp": datetime.utcnow().isoformat(),
            **data
        })


@dataclass  
class OperationResult:
    """Result of a governed operation."""
    success: bool
    context: OperationContext
    result: Any = None
    error: Optional[str] = None
    tokens_consumed: int = 0
    duration_ms: float = 0.0


class GovernanceError(Exception):
    """Raised when governance prevents execution."""
    pass


class _COLMeta(type):
    """Metaclass that ensures COL is a singleton and auto-initializes."""
    _instance: Optional['COL'] = None
    _lock = threading.Lock()
    
    def __call__(cls, *args, **kwargs):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__call__(*args, **kwargs)
                    cls._instance._initialize()
        return cls._instance


class COL(metaclass=_COLMeta):
    """
    Cognitive Operating Layer - The Heart of Cell 0 OS
    
    Self-invoking governance that intercepts ALL operations.
    Always active. Always watching. Always deciding.
    
    Usage:
        # Automatic - COL governs all decorated operations
        @COL.govern()
        def my_function():
            pass
            
        # Or manual operation submission
        result = await COL.submit(operation, context)
    """
    
    VERSION = "1.0.0-cell0"
    
    def __init__(self):
        self.state = OrchestratorState.STOPPED
        self._lock = asyncio.Lock()
        self._state_lock = threading.RLock()
        self._active_operations: Dict[str, OperationContext] = {}
        self._hooks: Dict[str, List[Callable]] = {
            'pre_classify': [],
            'post_classify': [],
            'pre_execute': [],
            'post_execute': [],
            'on_checkpoint': [],
            'on_governance_violation': []
        }
        
        # Core components
        self._classifier: Optional[RequestClassifier] = None
        self._protocol_loader: Optional[ProtocolLoader] = None
        self._token_economy: Optional[TokenEconomy] = None
        self._checkpoint_manager: Optional[CheckpointManager] = None
        
        # Resource monitoring
        self._resource_pressure = 0.0
        self._pressure_history: List[tuple] = []
        self._max_pressure_history = 100
        
        # Statistics
        self._stats = {
            'total_operations': 0,
            'governed_operations': 0,
            'rejected_operations': 0,
            'checkpoints_created': 0,
            'tokens_consumed': 0
        }
        
        # Self-governance thread
        self._governance_thread: Optional[threading.Thread] = None
        self._shutdown_event = threading.Event()
        
    def _initialize(self):
        """Initialize COL components. Called once on first access."""
        if self.state != OrchestratorState.STOPPED:
            return
            
        self.state = OrchestratorState.INITIALIZING
        
        # Initialize core components
        self._checkpoint_manager = CheckpointManager()
        self._token_economy = TokenEconomy()
        self._classifier = RequestClassifier()
        self._protocol_loader = ProtocolLoader()
        
        # Restore state if exists
        self._restore_state()
        
        # Start governance monitoring
        self._start_governance_thread()
        
        self.state = OrchestratorState.ACTIVE
        self._log("COL initialized", {"version": self.VERSION})
        
    def _start_governance_thread(self):
        """Start background governance monitoring."""
        def governance_loop():
            while not self._shutdown_event.is_set():
                try:
                    self._monitor_resources()
                    self._auto_checkpoint()
                    time.sleep(5)  # Check every 5 seconds
                except Exception as e:
                    self._log("Governance error", {"error": str(e)})
                    
        self._governance_thread = threading.Thread(
            target=governance_loop,
            name="COL-Governance",
            daemon=True
        )
        self._governance_thread.start()
        
    def _monitor_resources(self):
        """Monitor system resource pressure."""
        import psutil
        
        cpu = psutil.cpu_percent(interval=0.1)
        memory = psutil.virtual_memory().percent
        
        # Calculate composite pressure (0-1)
        pressure = max(cpu, memory) / 100.0
        
        with self._state_lock:
            self._resource_pressure = pressure
            self._pressure_history.append((time.time(), pressure))
            
            # Trim history
            if len(self._pressure_history) > self._max_pressure_history:
                self._pressure_history = self._pressure_history[-self._max_pressure_history:]
        
        # Trigger pressure response if needed
        if pressure > 0.9:
            self._handle_high_pressure()
            
    def _handle_high_pressure(self):
        """Respond to high resource pressure."""
        self._log("HIGH PRESSURE DETECTED", {
            "pressure": self._resource_pressure,
            "active_ops": len(self._active_operations)
        })
        
        # Emergency checkpoint
        self._checkpoint_manager.create_emergency_checkpoint()
        
        # Trigger hooks
        for hook in self._hooks.get('on_governance_violation', []):
            try:
                hook('high_pressure', self._resource_pressure)
            except:
                pass
                
    def _auto_checkpoint(self):
        """Create automatic checkpoints based on conditions."""
        # Checkpoint every N operations or time interval
        if self._stats['total_operations'] % 100 == 0:
            self._checkpoint_manager.create_checkpoint(
                reason="auto_operations",
                state=self._capture_state()
            )
            self._stats['checkpoints_created'] += 1
            
    def _capture_state(self) -> Dict:
        """Capture current COL state for checkpointing."""
        return {
            'version': self.VERSION,
            'state': self.state.name,
            'stats': self._stats.copy(),
            'pressure_history': self._pressure_history[-20:],
            'active_operations': len(self._active_operations),
            'token_economy': self._token_economy.get_state() if self._token_economy else None
        }
        
    def _restore_state(self):
        """Restore COL state from last checkpoint."""
        checkpoint = self._checkpoint_manager.get_latest()
        if checkpoint:
            self._log("Restoring from checkpoint", {"id": checkpoint.id})
            # Restore relevant state
            if checkpoint.state:
                self._stats.update(checkpoint.state.get('stats', {}))
                
    def _log(self, message: str, data: Dict = None):
        """Internal logging with COL context."""
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "col_version": self.VERSION,
            "state": self.state.name,
            "message": message,
            "data": data or {}
        }
        # Write to COL log
        log_path = Path.home() / ".openclaw" / "col" / "orchestrator.log"
        log_path.parent.mkdir(parents=True, exist_ok=True)
        with open(log_path, 'a') as f:
            f.write(json.dumps(log_entry) + "\n")
            
    # ========================================================================
    # PUBLIC API
    # ========================================================================
    
    @classmethod
    def govern(cls, **governance_kwargs):
        """
        Decorator to govern a function/method.
        
        This is the primary interface for COL governance.
        All decorated operations flow through: STOP → CLASSIFY → LOAD → APPLY → EXECUTE
        
        Args:
            priority: Operation priority (0-10)
            token_budget: Max tokens to allocate
            require_checkpoint: Force checkpoint before execution
            custom_protocol: Use specific protocol instead of classification
        """
        def decorator(func: Callable) -> Callable:
            @functools.wraps(func)
            async def async_wrapper(*args, **kwargs):
                col = cls()
                context = OperationContext(
                    source=func.__qualname__,
                    metadata={
                        'args_count': len(args),
                        'kwargs_keys': list(kwargs.keys()),
                        'governance': governance_kwargs
                    }
                )
                return await col._execute_pipeline(func, args, kwargs, context, governance_kwargs)
                
            @functools.wraps(func)
            def sync_wrapper(*args, **kwargs):
                col = cls()
                context = OperationContext(
                    source=func.__qualname__,
                    metadata={
                        'args_count': len(args),
                        'kwargs_keys': list(kwargs.keys()),
                        'governance': governance_kwargs
                    }
                )
                
                # Run async pipeline in sync context
                try:
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        # Nested async - return coro for await
                        return col._execute_pipeline(func, args, kwargs, context, governance_kwargs)
                except RuntimeError:
                    pass
                
                # Create new event loop for sync execution
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    result = loop.run_until_complete(
                        col._execute_pipeline(func, args, kwargs, context, governance_kwargs)
                    )
                    # Extract actual result from OperationResult
                    if isinstance(result, OperationResult):
                        if result.success:
                            return result.result
                        else:
                            raise RuntimeError(f"Governed operation failed: {result.error}")
                    return result
                finally:
                    loop.close()
            
            return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
        return decorator
    
    async def _execute_pipeline(
        self,
        operation: Callable,
        args: tuple,
        kwargs: dict,
        context: OperationContext,
        governance: dict
    ) -> OperationResult:
        """
        Execute the full COL pipeline: STOP → CLASSIFY → LOAD → APPLY → EXECUTE
        """
        start_time = time.time()
        
        # =====================================================================
        # STOP: Interception point - ALL operations stop here
        # =====================================================================
        context.trace("STOP", {"status": "intercepted", "governance": governance})
        
        async with self._lock:
            self._active_operations[context.operation_id] = context
            self._stats['total_operations'] += 1
            
        try:
            # Run pre-classify hooks
            for hook in self._hooks['pre_classify']:
                hook(context)
            
            # =====================================================================
            # CLASSIFY: Determine request type and risk
            # =====================================================================
            self.state = OrchestratorState.GOVERNANCE
            
            classification = await self._classifier.classify(
                operation=operation,
                args=args,
                kwargs=kwargs,
                context=context
            )
            context.classification = classification
            context.trace("CLASSIFY", {
                "type": classification.request_type.name,
                "risk": classification.risk_score,
                "confidence": classification.confidence
            })
            
            # Run post-classify hooks
            for hook in self._hooks['post_classify']:
                hook(context, classification)
            
            # Check if operation should proceed
            risk_threshold = governance.get('risk_threshold', 0.95)
            if classification.risk_score > risk_threshold and not governance.get('force_execute'):
                self._stats['rejected_operations'] += 1
                raise GovernanceError(
                    f"Operation blocked: risk score {classification.risk_score:.2f} exceeds threshold {risk_threshold}"
                )
            
            # =====================================================================
            # LOAD: Dynamic protocol loading
            # =====================================================================
            protocol = self._protocol_loader.load(
                classification=classification,
                governance=governance
            )
            context.protocol_id = protocol.id if protocol else None
            context.trace("LOAD", {"protocol": protocol.id if protocol else None})
            
            # =====================================================================
            # APPLY: Token-economic decision making
            # =====================================================================
            token_budget = self._token_economy.allocate_budget(
                operation_type=classification.request_type,
                risk_score=classification.risk_score,
                priority=governance.get('priority', 5),
                custom_budget=governance.get('token_budget')
            )
            context.token_budget = token_budget
            context.trace("APPLY", {
                "budget_allocated": token_budget.allocated,
                "priority": governance.get('priority', 5)
            })
            
            # Check if we can afford this operation
            if not token_budget.can_execute():
                raise GovernanceError(
                    f"Operation blocked: insufficient token budget "
                    f"({token_budget.available} < {token_budget.required})"
                )
            
            # Pre-execution checkpoint if required
            if governance.get('require_checkpoint') or classification.risk_score > 0.7:
                checkpoint = self._checkpoint_manager.create_checkpoint(
                    reason="pre_execution",
                    state={
                        'operation_id': context.operation_id,
                        'classification': classification.to_dict()
                    }
                )
                context.checkpoint_id = checkpoint.id
            
            # =====================================================================
            # EXECUTE: Run the actual operation
            # =====================================================================
            self.state = OrchestratorState.EXECUTING
            context.trace("EXECUTE", {"status": "starting"})
            
            for hook in self._hooks['pre_execute']:
                hook(context)
            
            # Execute with resource tracking
            result = await self._execute_with_tracking(
                operation, args, kwargs, context, token_budget
            )
            
            # Consume tokens
            tokens_used = token_budget.consume()
            self._stats['tokens_consumed'] += tokens_used
            
            context.trace("EXECUTE", {"status": "completed", "tokens_used": tokens_used})
            
            for hook in self._hooks['post_execute']:
                hook(context, result)
            
            duration_ms = (time.time() - start_time) * 1000
            self._stats['governed_operations'] += 1
            
            return OperationResult(
                success=True,
                context=context,
                result=result,
                tokens_consumed=tokens_used,
                duration_ms=duration_ms
            )
            
        except GovernanceError:
            raise
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            context.trace("ERROR", {"error": str(e), "type": type(e).__name__})
            
            # Create error checkpoint
            self._checkpoint_manager.create_checkpoint(
                reason="error",
                state={
                    'operation_id': context.operation_id,
                    'error': str(e),
                    'trace': context.execution_trace
                }
            )
            
            return OperationResult(
                success=False,
                context=context,
                error=str(e),
                duration_ms=duration_ms
            )
        finally:
            # Cleanup
            async with self._lock:
                self._active_operations.pop(context.operation_id, None)
            self.state = OrchestratorState.ACTIVE
            
    async def _execute_with_tracking(
        self,
        operation: Callable,
        args: tuple,
        kwargs: dict,
        context: OperationContext,
        token_budget: TokenBudget
    ) -> Any:
        """Execute operation with token tracking."""
        if asyncio.iscoroutinefunction(operation):
            return await operation(*args, **kwargs)
        else:
            # Run sync function in thread pool
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, functools.partial(operation, *args, **kwargs))
    
    @classmethod
    async def submit(cls, operation: Callable, context: Optional[OperationContext] = None) -> OperationResult:
        """Submit an operation for COL governance."""
        col = cls()
        ctx = context or OperationContext(source="manual_submit")
        return await col._execute_pipeline(operation, (), {}, ctx, {})
    
    @classmethod
    def register_hook(cls, event: str, callback: Callable):
        """Register a governance hook."""
        col = cls()
        if event in col._hooks:
            col._hooks[event].append(callback)
    
    @classmethod
    def get_stats(cls) -> Dict:
        """Get COL statistics."""
        col = cls()
        return {
            **col._stats,
            'state': col.state.name,
            'resource_pressure': col._resource_pressure,
            'active_operations': len(col._active_operations),
            'version': cls.VERSION
        }
    
    @classmethod
    def shutdown(cls):
        """Gracefully shutdown COL."""
        col = cls()
        col.state = OrchestratorState.SHUTTING_DOWN
        col._shutdown_event.set()
        
        # Final checkpoint
        col._checkpoint_manager.create_checkpoint(
            reason="shutdown",
            state=col._capture_state()
        )
        
        col._log("COL shutdown complete")


# Convenience alias
govern = COL.govern
get_stats = COL.get_stats
shutdown = COL.shutdown