"""
COL-Flow Interrupt Module
Cell 0 OS - Cognitive Operating Layer

Interrupt handling and resumption.
Manages flow interruptions, checkpoints, and recovery.
"""

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import List, Optional, Dict, Any, Callable, Set
from collections import deque
import json


class InterruptType(Enum):
    """Types of interrupts."""
    USER = auto()           # User interrupted
    SYSTEM = auto()         # System event
    TIMEOUT = auto()        # Operation timeout
    ERROR = auto()          # Error occurred
    PAUSE = auto()          # Explicit pause
    EXTERNAL = auto()       # External event


class InterruptPriority(Enum):
    """Priority of interrupts."""
    LOW = 0
    NORMAL = 1
    HIGH = 2
    CRITICAL = 3


@dataclass
class Checkpoint:
    """A snapshot of flow state at a point in time."""
    id: str
    timestamp: float
    flow_state: Dict[str, Any]
    request_queue: List[str]
    completed_requests: Set[str]
    context: Dict[str, Any]
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Interrupt:
    """An interrupt event."""
    id: str
    type: InterruptType
    priority: InterruptPriority
    timestamp: float
    source: str
    message: str
    payload: Dict[str, Any] = field(default_factory=dict)
    handled: bool = False
    resumed_from: Optional[str] = None


@dataclass
class FlowSession:
    """A resumable flow session."""
    id: str
    created_at: float
    last_active: float
    checkpoints: List[Checkpoint] = field(default_factory=list)
    interrupts: List[Interrupt] = field(default_factory=list)
    current_state: Dict[str, Any] = field(default_factory=dict)
    is_active: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)


class InterruptHandler:
    """
    Handles interrupts and manages flow resumption.
    
    Features:
    - Interrupt detection and classification
    - Checkpoint creation
    - State preservation
    - Resume from checkpoint
    - Interrupt queue management
    """
    
    def __init__(self, auto_checkpoint: bool = True, max_checkpoints: int = 10):
        """
        Initialize interrupt handler.
        
        Args:
            auto_checkpoint: Automatically create checkpoints
            max_checkpoints: Maximum checkpoints to retain
        """
        self.auto_checkpoint = auto_checkpoint
        self.max_checkpoints = max_checkpoints
        
        # Active session
        self._session: Optional[FlowSession] = None
        
        # Interrupt queue
        self._interrupt_queue: deque = deque()
        self._handled_interrupts: List[Interrupt] = []
        
        # Callbacks
        self._on_interrupt: Optional[Callable] = None
        self._on_resume: Optional[Callable] = None
        self._on_checkpoint: Optional[Callable] = None
    
    def start_session(self, session_id: Optional[str] = None, metadata: Optional[Dict] = None) -> FlowSession:
        """
        Start a new flow session.
        
        Args:
            session_id: Optional session ID (generated if not provided)
            metadata: Session metadata
            
        Returns:
            New FlowSession
        """
        now = time.time()
        session = FlowSession(
            id=session_id or str(uuid.uuid4())[:8],
            created_at=now,
            last_active=now,
            metadata=metadata or {}
        )
        
        self._session = session
        return session
    
    def create_checkpoint(
        self,
        flow_state: Dict[str, Any],
        request_queue: List[str],
        completed_requests: Set[str],
        context: Dict[str, Any],
        metadata: Optional[Dict] = None
    ) -> Checkpoint:
        """
        Create a checkpoint of current state.
        
        Args:
            flow_state: Current flow state
            request_queue: Pending requests
            completed_requests: Completed request IDs
            context: Context to preserve
            metadata: Additional metadata
            
        Returns:
            Created checkpoint
        """
        if not self._session:
            raise RuntimeError("No active session. Call start_session() first.")
        
        checkpoint = Checkpoint(
            id=f"chk_{len(self._session.checkpoints):03d}",
            timestamp=time.time(),
            flow_state=flow_state.copy(),
            request_queue=request_queue.copy(),
            completed_requests=completed_requests.copy(),
            context=context.copy(),
            metadata=metadata or {}
        )
        
        self._session.checkpoints.append(checkpoint)
        
        # Trim old checkpoints
        while len(self._session.checkpoints) > self.max_checkpoints:
            self._session.checkpoints.pop(0)
        
        if self._on_checkpoint:
            self._on_checkpoint(checkpoint)
        
        return checkpoint
    
    def interrupt(
        self,
        interrupt_type: InterruptType,
        source: str,
        message: str,
        priority: InterruptPriority = InterruptPriority.NORMAL,
        payload: Optional[Dict] = None
    ) -> Interrupt:
        """
        Trigger an interrupt.
        
        Args:
            interrupt_type: Type of interrupt
            source: Source of interrupt
            message: Human-readable message
            priority: Interrupt priority
            payload: Additional data
            
        Returns:
            Created interrupt
        """
        interrupt = Interrupt(
            id=f"int_{uuid.uuid4().hex[:8]}",
            type=interrupt_type,
            priority=priority,
            timestamp=time.time(),
            source=source,
            message=message,
            payload=payload or {}
        )
        
        # Add to queue (sorted by priority)
        inserted = False
        for i, existing in enumerate(self._interrupt_queue):
            if existing.priority.value < priority.value:
                self._interrupt_queue.insert(i, interrupt)
                inserted = True
                break
        
        if not inserted:
            self._interrupt_queue.append(interrupt)
        
        if self._session:
            self._session.interrupts.append(interrupt)
            self._session.is_active = False
        
        if self._on_interrupt:
            self._on_interrupt(interrupt)
        
        return interrupt
    
    def get_next_interrupt(self) -> Optional[Interrupt]:
        """Get the next interrupt to handle."""
        while self._interrupt_queue:
            interrupt = self._interrupt_queue.popleft()
            if not interrupt.handled:
                return interrupt
        return None
    
    def handle_interrupt(self, interrupt: Interrupt, handler_result: Any = None):
        """
        Mark an interrupt as handled.
        
        Args:
            interrupt: The interrupt to handle
            handler_result: Result from handler
        """
        interrupt.handled = True
        interrupt.payload['handler_result'] = handler_result
        self._handled_interrupts.append(interrupt)
    
    def resume(
        self,
        from_checkpoint: Optional[str] = None,
        modified_context: Optional[Dict] = None
    ) -> Optional[Checkpoint]:
        """
        Resume from a checkpoint.
        
        Args:
            from_checkpoint: Checkpoint ID to resume from (None = latest)
            modified_context: Context modifications to apply
            
        Returns:
            Checkpoint resumed from, or None if no session
        """
        if not self._session:
            return None
        
        checkpoint = None
        
        if from_checkpoint:
            # Find specific checkpoint
            for chk in self._session.checkpoints:
                if chk.id == from_checkpoint:
                    checkpoint = chk
                    break
        else:
            # Use latest
            if self._session.checkpoints:
                checkpoint = self._session.checkpoints[-1]
        
        if not checkpoint:
            return None
        
        # Update session
        self._session.last_active = time.time()
        self._session.is_active = True
        self._session.current_state = checkpoint.flow_state.copy()
        
        # Apply context modifications
        if modified_context:
            checkpoint.context.update(modified_context)
        
        # Record resume
        for interrupt in self._session.interrupts:
            if not interrupt.resumed_from:
                interrupt.resumed_from = checkpoint.id
        
        if self._on_resume:
            self._on_resume(checkpoint)
        
        return checkpoint
    
    def get_resume_options(self) -> List[Dict[str, Any]]:
        """Get available resume options."""
        if not self._session:
            return []
        
        options = []
        
        for checkpoint in reversed(self._session.checkpoints):
            options.append({
                'id': checkpoint.id,
                'timestamp': checkpoint.timestamp,
                'age': time.time() - checkpoint.timestamp,
                'queue_size': len(checkpoint.request_queue),
                'completed_count': len(checkpoint.completed_requests),
                'description': checkpoint.metadata.get('description', f"Checkpoint {checkpoint.id}")
            })
        
        return options
    
    def can_resume(self) -> bool:
        """Check if flow can be resumed."""
        return (
            self._session is not None and
            len(self._session.checkpoints) > 0 and
            not self._session.is_active
        )
    
    def get_session_summary(self) -> Dict[str, Any]:
        """Get summary of current session."""
        if not self._session:
            return {'active': False}
        
        return {
            'active': self._session.is_active,
            'session_id': self._session.id,
            'duration': time.time() - self._session.created_at,
            'checkpoints': len(self._session.checkpoints),
            'interrupts': len(self._session.interrupts),
            'pending_interrupts': len(self._interrupt_queue),
            'handled_interrupts': len(self._handled_interrupts),
        }
    
    def save_session(self) -> Dict[str, Any]:
        """
        Serialize session for persistence.
        
        Returns:
            Serializable session data
        """
        if not self._session:
            return {}
        
        return {
            'id': self._session.id,
            'created_at': self._session.created_at,
            'last_active': self._session.last_active,
            'is_active': self._session.is_active,
            'metadata': self._session.metadata,
            'checkpoints': [
                {
                    'id': c.id,
                    'timestamp': c.timestamp,
                    'flow_state': c.flow_state,
                    'request_queue': c.request_queue,
                    'completed_requests': list(c.completed_requests),
                    'context': c.context,
                    'metadata': c.metadata
                }
                for c in self._session.checkpoints
            ],
            'interrupts': [
                {
                    'id': i.id,
                    'type': i.type.name,
                    'priority': i.priority.name,
                    'timestamp': i.timestamp,
                    'source': i.source,
                    'message': i.message,
                    'handled': i.handled,
                    'resumed_from': i.resumed_from
                }
                for i in self._session.interrupts
            ]
        }
    
    def load_session(self, data: Dict[str, Any]) -> FlowSession:
        """
        Load session from serialized data.
        
        Args:
            data: Serialized session data
            
        Returns:
            Loaded FlowSession
        """
        session = FlowSession(
            id=data['id'],
            created_at=data['created_at'],
            last_active=data['last_active'],
            is_active=data['is_active'],
            metadata=data.get('metadata', {}),
            checkpoints=[
                Checkpoint(
                    id=c['id'],
                    timestamp=c['timestamp'],
                    flow_state=c['flow_state'],
                    request_queue=c['request_queue'],
                    completed_requests=set(c['completed_requests']),
                    context=c['context'],
                    metadata=c.get('metadata', {})
                )
                for c in data.get('checkpoints', [])
            ],
            interrupts=[
                Interrupt(
                    id=i['id'],
                    type=InterruptType[i['type']],
                    priority=InterruptPriority[i['priority']],
                    timestamp=i['timestamp'],
                    source=i['source'],
                    message=i['message'],
                    handled=i.get('handled', False),
                    resumed_from=i.get('resumed_from')
                )
                for i in data.get('interrupts', [])
            ]
        )
        
        self._session = session
        return session
    
    def end_session(self) -> Optional[FlowSession]:
        """End the current session."""
        session = self._session
        self._session = None
        self._interrupt_queue.clear()
        return session
    
    def on_interrupt(self, callback: Callable):
        """Set callback for interrupt events."""
        self._on_interrupt = callback
    
    def on_resume(self, callback: Callable):
        """Set callback for resume events."""
        self._on_resume = callback
    
    def on_checkpoint(self, callback: Callable):
        """Set callback for checkpoint creation."""
        self._on_checkpoint = callback


class LongRunningTaskManager:
    """
    Manages long-running tasks with checkpointing.
    
    Features:
    - Progress tracking
    - Periodic checkpointing
    - Resume on interrupt
    - Timeout handling
    """
    
    def __init__(self, checkpoint_interval: float = 30.0):
        """
        Initialize task manager.
        
        Args:
            checkpoint_interval: Seconds between checkpoints
        """
        self.checkpoint_interval = checkpoint_interval
        self._tasks: Dict[str, Dict[str, Any]] = {}
        self._interrupt_handler: Optional[InterruptHandler] = None
    
    def attach_interrupt_handler(self, handler: InterruptHandler):
        """Attach an interrupt handler."""
        self._interrupt_handler = handler
    
    def start_task(
        self,
        task_id: str,
        description: str,
        total_steps: int = 100,
        metadata: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Start tracking a long-running task.
        
        Args:
            task_id: Unique task ID
            description: Task description
            total_steps: Total steps in task
            metadata: Additional metadata
            
        Returns:
            Task tracking dict
        """
        task = {
            'id': task_id,
            'description': description,
            'total_steps': total_steps,
            'current_step': 0,
            'status': 'running',
            'started_at': time.time(),
            'last_checkpoint': time.time(),
            'metadata': metadata or {},
            'state': {}
        }
        
        self._tasks[task_id] = task
        return task
    
    def update_progress(
        self,
        task_id: str,
        current_step: int,
        state: Optional[Dict] = None,
        force_checkpoint: bool = False
    ):
        """
        Update task progress.
        
        Args:
            task_id: Task ID
            current_step: Current step number
            state: Current state for checkpointing
            force_checkpoint: Force a checkpoint
        """
        if task_id not in self._tasks:
            return
        
        task = self._tasks[task_id]
        task['current_step'] = current_step
        
        if state:
            task['state'] = state
        
        # Check if checkpoint needed
        now = time.time()
        if force_checkpoint or (now - task['last_checkpoint'] >= self.checkpoint_interval):
            self._create_task_checkpoint(task)
            task['last_checkpoint'] = now
    
    def _create_task_checkpoint(self, task: Dict[str, Any]):
        """Create a checkpoint for a task."""
        if self._interrupt_handler:
            self._interrupt_handler.create_checkpoint(
                flow_state={
                    'task_id': task['id'],
                    'task_state': task['state'],
                    'progress': task['current_step'] / task['total_steps']
                },
                request_queue=[],
                completed_requests=set(),
                context={'task_checkpoint': True},
                metadata={
                    'description': f"Task {task['id']} checkpoint at step {task['current_step']}",
                    'task_progress': f"{task['current_step']}/{task['total_steps']}"
                }
            )
    
    def complete_task(self, task_id: str, result: Any = None):
        """Mark a task as complete."""
        if task_id in self._tasks:
            self._tasks[task_id]['status'] = 'completed'
            self._tasks[task_id]['completed_at'] = time.time()
            self._tasks[task_id]['result'] = result
    
    def fail_task(self, task_id: str, error: str):
        """Mark a task as failed."""
        if task_id in self._tasks:
            self._tasks[task_id]['status'] = 'failed'
            self._tasks[task_id]['error'] = error
    
    def get_task_progress(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get task progress information."""
        if task_id not in self._tasks:
            return None
        
        task = self._tasks[task_id]
        return {
            'id': task['id'],
            'description': task['description'],
            'progress': task['current_step'] / task['total_steps'],
            'current_step': task['current_step'],
            'total_steps': task['total_steps'],
            'status': task['status'],
            'elapsed': time.time() - task['started_at']
        }
    
    def get_all_tasks(self) -> List[Dict[str, Any]]:
        """Get all task progress information."""
        return [self.get_task_progress(tid) for tid in self._tasks]
    
    def format_progress_bar(self, task_id: str, width: int = 40) -> str:
        """Format a progress bar for a task."""
        progress = self.get_task_progress(task_id)
        if not progress:
            return "[Unknown task]"
        
        pct = progress['progress']
        filled = int(width * pct)
        bar = "█" * filled + "░" * (width - filled)
        
        return f"{progress['description']}\n[{bar}] {pct*100:.1f}% ({progress['current_step']}/{progress['total_steps']})"