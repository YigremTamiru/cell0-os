"""
Agent Session - Per-agent session management and isolation.

Cell 0 OS - Multi-Agent Routing System
"""
from __future__ import annotations
import asyncio
import uuid
import time
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Optional, Callable, Coroutine, AsyncIterator
from collections import deque
import contextvars


# Context variable to track current agent in execution context
current_agent_id: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar(
    'current_agent_id', default=None
)


class SessionState(Enum):
    """Session lifecycle states."""
    INITIALIZING = auto()
    ACTIVE = auto()
    PAUSED = auto()
    SHUTDOWN = auto()
    ERROR = auto()


@dataclass
class SessionContext:
    """Context information for an agent session."""
    session_id: str
    agent_id: str
    created_at: float = field(default_factory=time.time)
    memory: dict[str, Any] = field(default_factory=dict)
    message_history: deque = field(default_factory=lambda: deque(maxlen=100))
    user_context: dict[str, Any] = field(default_factory=dict)
    execution_count: int = 0
    total_tokens: int = 0
    
    def add_to_history(self, role: str, content: str, metadata: Optional[dict] = None) -> None:
        """Add a message to session history."""
        self.message_history.append({
            "timestamp": time.time(),
            "role": role,
            "content": content,
            "metadata": metadata or {}
        })
    
    def get_recent_history(self, n: int = 10) -> list[dict]:
        """Get the n most recent messages from history."""
        return list(self.message_history)[-n:]
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "agent_id": self.agent_id,
            "created_at": self.created_at,
            "memory": self.memory,
            "message_history": list(self.message_history),
            "user_context": self.user_context,
            "execution_count": self.execution_count,
            "total_tokens": self.total_tokens
        }


@dataclass 
class SessionMessage:
    """A message within an agent session."""
    message_id: str
    session_id: str
    source: str  # agent_id or "user" or "system"
    target: str  # agent_id or "broadcast"
    content: Any
    message_type: str = "text"
    timestamp: float = field(default_factory=time.time)
    metadata: dict[str, Any] = field(default_factory=dict)
    correlation_id: Optional[str] = None  # For request/response tracking
    
    def is_request(self) -> bool:
        """Check if this is a request message (expects response)."""
        return self.message_type.endswith("_request")
    
    def is_response(self) -> bool:
        """Check if this is a response message."""
        return self.message_type.endswith("_response") or self.message_type.endswith("_error")
    
    def create_response(self, content: Any, success: bool = True) -> SessionMessage:
        """Create a response message to this message."""
        return SessionMessage(
            message_id=str(uuid.uuid4()),
            session_id=self.session_id,
            source=self.target,
            target=self.source,
            content=content,
            message_type=self.message_type.replace("_request", "_response" if success else "_error"),
            correlation_id=self.message_id,
            metadata={"in_response_to": self.message_id}
        )


class AgentSession:
    """
    Manages a single agent's isolated session.
    
    Each agent gets its own session with:
    - Isolated memory/context
    - Message inbox
    - Execution sandbox
    - Resource tracking
    """
    
    def __init__(
        self,
        agent_id: str,
        session_id: Optional[str] = None,
        max_inbox_size: int = 1000,
        max_concurrent_tasks: int = 5
    ):
        self.agent_id = agent_id
        self.session_id = session_id or str(uuid.uuid4())
        self.context = SessionContext(
            session_id=self.session_id,
            agent_id=agent_id
        )
        
        self.state = SessionState.INITIALIZING
        self._inbox: asyncio.Queue[SessionMessage] = asyncio.Queue(maxsize=max_inbox_size)
        self._outbox_callbacks: list[Callable[[SessionMessage], Coroutine]] = []
        self._task_sem = asyncio.Semaphore(max_concurrent_tasks)
        self._active_tasks: set[asyncio.Task] = set()
        self._lock = asyncio.Lock()
        self._shutdown_event = asyncio.Event()
        
        # Resource tracking
        self._resource_usage = {
            "cpu_time": 0.0,
            "memory_peak": 0,
            "api_calls": 0,
            "tokens_consumed": 0
        }
    
    async def start(self) -> None:
        """Start the session."""
        async with self._lock:
            if self.state != SessionState.INITIALIZING:
                raise RuntimeError(f"Cannot start session in state {self.state}")
            self.state = SessionState.ACTIVE
    
    async def shutdown(self, timeout: float = 30.0) -> None:
        """Gracefully shutdown the session."""
        async with self._lock:
            self.state = SessionState.SHUTDOWN
            self._shutdown_event.set()
        
        # Cancel active tasks
        if self._active_tasks:
            for task in self._active_tasks:
                task.cancel()
            
            # Wait for tasks to complete
            done, pending = await asyncio.wait(
                self._active_tasks,
                timeout=timeout,
                return_when=asyncio.ALL_COMPLETED
            )
            
            for task in pending:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
    
    async def pause(self) -> None:
        """Pause the session temporarily."""
        async with self._lock:
            if self.state == SessionState.ACTIVE:
                self.state = SessionState.PAUSED
    
    async def resume(self) -> None:
        """Resume a paused session."""
        async with self._lock:
            if self.state == SessionState.PAUSED:
                self.state = SessionState.ACTIVE
    
    async def receive(self, message: SessionMessage) -> bool:
        """
        Receive a message into the session inbox.
        Returns False if inbox is full.
        """
        if self.state not in (SessionState.ACTIVE, SessionState.PAUSED):
            return False
        
        try:
            self._inbox.put_nowait(message)
            return True
        except asyncio.QueueFull:
            return False
    
    async def send(
        self,
        target: str,
        content: Any,
        message_type: str = "text",
        metadata: Optional[dict] = None,
        correlation_id: Optional[str] = None
    ) -> SessionMessage:
        """
        Send a message from this session to another agent/target.
        """
        message = SessionMessage(
            message_id=str(uuid.uuid4()),
            session_id=self.session_id,
            source=self.agent_id,
            target=target,
            content=content,
            message_type=message_type,
            metadata=metadata or {},
            correlation_id=correlation_id
        )
        
        # Notify outbox callbacks
        for callback in self._outbox_callbacks:
            try:
                await callback(message)
            except Exception:
                pass
        
        return message
    
    async def get_next_message(
        self,
        timeout: Optional[float] = None,
        message_type: Optional[str] = None
    ) -> Optional[SessionMessage]:
        """
        Get the next message from the inbox.
        Optionally filter by message type.
        """
        if self.state == SessionState.SHUTDOWN:
            return None
        
        try:
            if timeout:
                message = await asyncio.wait_for(
                    self._inbox.get(),
                    timeout=timeout
                )
            else:
                message = await self._inbox.get()
            
            if message_type and message.message_type != message_type:
                # Put it back and wait for next
                await self.receive(message)
                return await self.get_next_message(timeout, message_type)
            
            return message
        except asyncio.TimeoutError:
            return None
    
    async def iter_messages(self) -> AsyncIterator[SessionMessage]:
        """Iterate over incoming messages until shutdown."""
        while self.state != SessionState.SHUTDOWN:
            try:
                message = await asyncio.wait_for(
                    self._inbox.get(),
                    timeout=1.0
                )
                yield message
            except asyncio.TimeoutError:
                continue
    
    def subscribe_to_outbox(self, callback: Callable[[SessionMessage], Coroutine]) -> None:
        """Subscribe to outgoing messages from this session."""
        self._outbox_callbacks.append(callback)
    
    def unsubscribe_from_outbox(self, callback: Callable[[SessionMessage], Coroutine]) -> None:
        """Unsubscribe from outgoing messages."""
        if callback in self._outbox_callbacks:
            self._outbox_callbacks.remove(callback)
    
    async def execute(
        self,
        func: Callable[..., Coroutine],
        *args,
        track_resources: bool = True,
        **kwargs
    ) -> Any:
        """
        Execute a function within this session's context.
        Provides isolation and resource tracking.
        """
        if self.state not in (SessionState.ACTIVE,):
            raise RuntimeError(f"Cannot execute in session state {self.state}")
        
        async with self._task_sem:
            # Set context variable
            token = current_agent_id.set(self.agent_id)
            
            start_time = time.time()
            self.context.execution_count += 1
            
            try:
                # Wrap in task for tracking
                task = asyncio.create_task(func(*args, **kwargs))
                self._active_tasks.add(task)
                
                try:
                    result = await task
                    return result
                finally:
                    self._active_tasks.discard(task)
                    
            except Exception as e:
                self.state = SessionState.ERROR
                raise
            finally:
                # Track resource usage
                elapsed = time.time() - start_time
                self._resource_usage["cpu_time"] += elapsed
                current_agent_id.reset(token)
    
    def update_memory(self, key: str, value: Any) -> None:
        """Update session memory."""
        self.context.memory[key] = value
    
    def get_memory(self, key: str, default: Any = None) -> Any:
        """Get value from session memory."""
        return self.context.memory.get(key, default)
    
    def clear_memory(self) -> None:
        """Clear session memory."""
        self.context.memory.clear()
    
    def get_stats(self) -> dict[str, Any]:
        """Get session statistics."""
        return {
            "session_id": self.session_id,
            "agent_id": self.agent_id,
            "state": self.state.name,
            "inbox_size": self._inbox.qsize(),
            "active_tasks": len(self._active_tasks),
            "execution_count": self.context.execution_count,
            "resource_usage": self._resource_usage.copy(),
            "memory_keys": len(self.context.memory),
            "history_size": len(self.context.message_history)
        }
    
    def to_dict(self) -> dict[str, Any]:
        """Serialize session state."""
        return {
            "session_id": self.session_id,
            "agent_id": self.agent_id,
            "state": self.state.name,
            "context": self.context.to_dict(),
            "stats": self.get_stats()
        }


class SessionManager:
    """Manages all agent sessions in the system."""
    
    def __init__(self):
        self._sessions: dict[str, AgentSession] = {}
        self._agent_sessions: dict[str, str] = {}  # agent_id -> session_id
        self._lock = asyncio.Lock()
    
    async def create_session(
        self,
        agent_id: str,
        session_id: Optional[str] = None
    ) -> AgentSession:
        """Create a new session for an agent."""
        async with self._lock:
            if agent_id in self._agent_sessions:
                raise ValueError(f"Agent {agent_id} already has an active session")
            
            session = AgentSession(agent_id, session_id)
            await session.start()
            
            self._sessions[session.session_id] = session
            self._agent_sessions[agent_id] = session.session_id
            
            return session
    
    async def destroy_session(
        self,
        session_id: str,
        timeout: float = 30.0
    ) -> bool:
        """Destroy a session and cleanup resources."""
        async with self._lock:
            session = self._sessions.get(session_id)
            if not session:
                return False
            
            await session.shutdown(timeout)
            
            del self._sessions[session_id]
            if session.agent_id in self._agent_sessions:
                del self._agent_sessions[session.agent_id]
            
            return True
    
    def get_session(self, session_id: str) -> Optional[AgentSession]:
        """Get a session by ID."""
        return self._sessions.get(session_id)
    
    def get_session_for_agent(self, agent_id: str) -> Optional[AgentSession]:
        """Get the session for a specific agent."""
        session_id = self._agent_sessions.get(agent_id)
        if session_id:
            return self._sessions.get(session_id)
        return None
    
    def get_all_sessions(self) -> list[AgentSession]:
        """Get all active sessions."""
        return list(self._sessions.values())
    
    async def broadcast(
        self,
        source_agent_id: str,
        content: Any,
        message_type: str = "broadcast",
        exclude_self: bool = True
    ) -> list[str]:
        """Broadcast a message to all sessions."""
        message = SessionMessage(
            message_id=str(uuid.uuid4()),
            session_id="broadcast",
            source=source_agent_id,
            target="broadcast",
            content=content,
            message_type=message_type
        )
        
        delivered = []
        for session in self._sessions.values():
            if exclude_self and session.agent_id == source_agent_id:
                continue
            if await session.receive(message):
                delivered.append(session.agent_id)
        
        return delivered
    
    def get_stats(self) -> dict[str, Any]:
        """Get manager statistics."""
        return {
            "total_sessions": len(self._sessions),
            "by_state": {},
            "total_messages_in_inbox": sum(
                s._inbox.qsize() for s in self._sessions.values()
            )
        }


def get_current_agent_id() -> Optional[str]:
    """Get the current agent ID from context."""
    return current_agent_id.get()
