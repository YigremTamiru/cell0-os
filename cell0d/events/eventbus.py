"""
EventBus - Internal Communication System for cell0d
Provides pub/sub pattern for decoupled component communication
"""
import asyncio
import logging
from typing import Dict, List, Callable, Any, Optional, Set
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
import json
import uuid

logger = logging.getLogger("cell0d.eventbus")


class EventType(Enum):
    """Supported event types for cell0d"""
    SYSTEM_STATUS = "system_status"
    CHAT_MESSAGE = "chat_message"
    MODEL_ACTIVITY = "model_activity"
    MCIC_EVENT = "mcic_event"
    LOG_STREAM = "log_stream"
    HEARTBEAT = "heartbeat"
    CLIENT_CONNECT = "client_connect"
    CLIENT_DISCONNECT = "client_disconnect"
    ALL = "all"  # Special type for subscribing to all events


@dataclass
class Event:
    """Event data structure"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    type: EventType = EventType.SYSTEM_STATUS
    timestamp: datetime = field(default_factory=datetime.utcnow)
    source: str = "cell0d"
    data: Dict[str, Any] = field(default_factory=dict)
    priority: int = 5  # 1-10, lower is higher priority
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "type": self.type.value,
            "timestamp": self.timestamp.isoformat(),
            "source": self.source,
            "data": self.data,
            "priority": self.priority
        }
    
    def to_json(self) -> str:
        return json.dumps(self.to_dict())
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Event':
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            type=EventType(data.get("type", "system_status")),
            timestamp=datetime.fromisoformat(data["timestamp"]) if "timestamp" in data else datetime.utcnow(),
            source=data.get("source", "cell0d"),
            data=data.get("data", {}),
            priority=data.get("priority", 5)
        )


class EventBus:
    """
    Central event bus for cell0d
    Supports multiple subscribers per event type with filtering
    """
    
    def __init__(self, max_history: int = 1000):
        self._subscribers: Dict[EventType, List[Callable[[Event], None]]] = {}
        self._event_history: List[Event] = []
        self._max_history = max_history
        self._lock = asyncio.Lock()
        self._running = False
        self._event_queue: asyncio.Queue = asyncio.Queue()
        self._worker_task: Optional[asyncio.Task] = None
        
        # Initialize subscriber lists for all event types
        for event_type in EventType:
            self._subscribers[event_type] = []
        
        logger.info("EventBus initialized")
    
    async def start(self):
        """Start the event bus processing loop"""
        self._running = True
        self._worker_task = asyncio.create_task(self._process_events())
        logger.info("EventBus started")
    
    async def stop(self):
        """Stop the event bus"""
        self._running = False
        if self._worker_task:
            self._worker_task.cancel()
            try:
                await self._worker_task
            except asyncio.CancelledError:
                pass
        logger.info("EventBus stopped")
    
    async def _process_events(self):
        """Background worker to process queued events"""
        while self._running:
            try:
                event = await asyncio.wait_for(self._event_queue.get(), timeout=1.0)
                await self._dispatch_event(event)
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"Error processing event: {e}")
    
    async def _dispatch_event(self, event: Event):
        """Dispatch event to all relevant subscribers"""
        async with self._lock:
            # Add to history
            self._event_history.append(event)
            if len(self._event_history) > self._max_history:
                self._event_history.pop(0)
            
            # Get subscribers for this event type AND subscribers to ALL
            subscribers = (
                self._subscribers.get(event.type, []) + 
                self._subscribers.get(EventType.ALL, [])
            )
        
        # Notify subscribers outside the lock
        for callback in subscribers:
            try:
                if asyncio.iscoroutinefunction(callback):
                    asyncio.create_task(callback(event))
                else:
                    callback(event)
            except Exception as e:
                logger.error(f"Error notifying subscriber: {e}")
    
    def subscribe(self, event_type: EventType, callback: Callable[[Event], None]) -> str:
        """
        Subscribe to events of a specific type
        Returns subscription ID for later unsubscribing
        """
        subscription_id = str(uuid.uuid4())
        
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        
        self._subscribers[event_type].append(callback)
        logger.debug(f"Subscribed {subscription_id} to {event_type.value}")
        return subscription_id
    
    def unsubscribe(self, event_type: EventType, callback: Callable[[Event], None]):
        """Unsubscribe a callback from an event type"""
        if event_type in self._subscribers:
            try:
                self._subscribers[event_type].remove(callback)
                logger.debug(f"Unsubscribed from {event_type.value}")
            except ValueError:
                pass
    
    async def emit(self, event: Event):
        """Emit an event to the bus"""
        await self._event_queue.put(event)
        logger.debug(f"Event queued: {event.type.value}")
    
    async def emit_now(self, event: Event):
        """Emit and dispatch immediately (synchronous)"""
        await self._dispatch_event(event)
    
    def get_history(self, event_type: Optional[EventType] = None, 
                   limit: int = 100, 
                   since: Optional[datetime] = None) -> List[Event]:
        """
        Get event history with optional filtering
        """
        history = self._event_history
        
        if event_type:
            history = [e for e in history if e.type == event_type]
        
        if since:
            history = [e for e in history if e.timestamp >= since]
        
        return history[-limit:]
    
    def get_stats(self) -> Dict[str, Any]:
        """Get event bus statistics"""
        return {
            "total_events_in_history": len(self._event_history),
            "subscriber_counts": {
                et.value: len(subs) for et, subs in self._subscribers.items()
            },
            "queue_size": self._event_queue.qsize(),
            "running": self._running
        }


# Global event bus instance
event_bus = EventBus()


# Convenience functions for creating common events
def create_system_status_event(status: str, details: Dict[str, Any] = None) -> Event:
    """Create a system status event"""
    return Event(
        type=EventType.SYSTEM_STATUS,
        source="cell0d.system",
        data={
            "status": status,
            "details": details or {},
            "uptime": details.get("uptime", 0) if details else 0
        }
    )


def create_chat_message_event(message: str, sender: str, 
                              channel: str = "general",
                              metadata: Dict[str, Any] = None) -> Event:
    """Create a chat message event"""
    return Event(
        type=EventType.CHAT_MESSAGE,
        source=f"chat.{channel}",
        data={
            "message": message,
            "sender": sender,
            "channel": channel,
            "metadata": metadata or {}
        }
    )


def create_model_activity_event(action: str, model_name: str,
                                details: Dict[str, Any] = None) -> Event:
    """Create a model activity event"""
    return Event(
        type=EventType.MODEL_ACTIVITY,
        source="cell0d.models",
        data={
            "action": action,  # loading, unloading, inference_started, inference_completed
            "model_name": model_name,
            "details": details or {}
        }
    )


def create_mcic_event(event_name: str, kernel_id: str,
                     payload: Dict[str, Any] = None) -> Event:
    """Create an MCIC (kernel) event"""
    return Event(
        type=EventType.MCIC_EVENT,
        source=f"mcic.{kernel_id}",
        data={
            "event": event_name,
            "kernel_id": kernel_id,
            "payload": payload or {}
        }
    )


def create_log_event(level: str, message: str,
                     logger_name: str = "cell0d",
                     metadata: Dict[str, Any] = None) -> Event:
    """Create a log stream event"""
    return Event(
        type=EventType.LOG_STREAM,
        source=f"log.{logger_name}",
        data={
            "level": level,
            "message": message,
            "logger": logger_name,
            "metadata": metadata or {}
        }
    )


def create_heartbeat_event(client_id: str, sequence: int) -> Event:
    """Create a heartbeat event"""
    return Event(
        type=EventType.HEARTBEAT,
        source="cell0d.heartbeat",
        data={
            "client_id": client_id,
            "sequence": sequence,
            "timestamp": datetime.utcnow().isoformat()
        }
    )