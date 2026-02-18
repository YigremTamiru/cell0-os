"""
presence.py - Presence Tracking System for Cell 0 OS Gateway

Manages real-time presence state for agents, users, and sessions.
Provides heartbeat tracking, status updates, and presence subscriptions.
"""

import asyncio
import logging
import time
from typing import Dict, List, Optional, Set, Callable, Any, Union
from dataclasses import dataclass, field, asdict
from enum import Enum, auto
from datetime import datetime, timedelta
import json
import uuid

logger = logging.getLogger("cell0.gateway.presence")


class PresenceStatus(Enum):
    """Presence status states"""
    ONLINE = "online"
    AWAY = "away"
    BUSY = "busy"
    OFFLINE = "offline"
    DND = "do_not_disturb"


class EntityType(Enum):
    """Types of entities that can have presence"""
    AGENT = "agent"
    USER = "user"
    SESSION = "session"
    CHANNEL = "channel"
    SYSTEM = "system"


@dataclass
class PresenceInfo:
    """Presence information for an entity"""
    entity_id: str
    entity_type: EntityType
    status: PresenceStatus = PresenceStatus.ONLINE
    status_message: Optional[str] = None
    connected_at: datetime = field(default_factory=datetime.utcnow)
    last_seen: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)
    capabilities: List[str] = field(default_factory=list)
    current_activity: Optional[str] = None
    
    # Session-specific fields
    session_id: Optional[str] = None
    client_version: Optional[str] = None
    platform: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "entity_id": self.entity_id,
            "entity_type": self.entity_type.value,
            "status": self.status.value,
            "status_message": self.status_message,
            "connected_at": self.connected_at.isoformat(),
            "last_seen": self.last_seen.isoformat(),
            "metadata": self.metadata,
            "capabilities": self.capabilities,
            "current_activity": self.current_activity,
            "session_id": self.session_id,
            "client_version": self.client_version,
            "platform": self.platform,
        }
    
    def update_activity(self, activity: str):
        """Update current activity"""
        self.current_activity = activity
        self.last_seen = datetime.utcnow()
    
    def update_status(self, status: PresenceStatus, message: Optional[str] = None):
        """Update presence status"""
        self.status = status
        if message is not None:
            self.status_message = message
        self.last_seen = datetime.utcnow()
    
    def touch(self):
        """Update last_seen timestamp"""
        self.last_seen = datetime.utcnow()
    
    def is_stale(self, timeout_seconds: float = 120.0) -> bool:
        """Check if presence hasn't been updated recently"""
        return (datetime.utcnow() - self.last_seen).total_seconds() > timeout_seconds


@dataclass 
class SessionInfo:
    """Session information for connected clients"""
    session_id: str
    entity_id: str
    entity_type: EntityType
    websocket_id: Optional[str] = None
    connected_at: datetime = field(default_factory=datetime.utcnow)
    last_activity: datetime = field(default_factory=datetime.utcnow)
    authenticated: bool = False
    auth_token: Optional[str] = None
    permissions: Set[str] = field(default_factory=set)
    subscriptions: Set[str] = field(default_factory=set)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "entity_id": self.entity_id,
            "entity_type": self.entity_type.value,
            "connected_at": self.connected_at.isoformat(),
            "last_activity": self.last_activity.isoformat(),
            "authenticated": self.authenticated,
            "permissions": list(self.permissions),
            "subscriptions": list(self.subscriptions),
        }
    
    def touch(self):
        """Update last activity timestamp"""
        self.last_activity = datetime.utcnow()
    
    def has_permission(self, permission: str) -> bool:
        """Check if session has a specific permission"""
        return permission in self.permissions or "*" in self.permissions
    
    def add_subscription(self, channel: str):
        """Add channel subscription"""
        self.subscriptions.add(channel)
        self.touch()
    
    def remove_subscription(self, channel: str):
        """Remove channel subscription"""
        self.subscriptions.discard(channel)
        self.touch()


class PresenceManager:
    """
    Manages presence state for all entities in the system.
    Provides real-time presence tracking with subscriptions and updates.
    """
    
    def __init__(
        self,
        heartbeat_timeout: float = 60.0,
        stale_timeout: float = 120.0,
        cleanup_interval: float = 30.0
    ):
        self.heartbeat_timeout = heartbeat_timeout
        self.stale_timeout = stale_timeout
        self.cleanup_interval = cleanup_interval
        
        # Presence state storage
        self._presence: Dict[str, PresenceInfo] = {}
        self._sessions: Dict[str, SessionInfo] = {}
        self._entity_sessions: Dict[str, Set[str]] = {}  # entity_id -> session_ids
        
        # Subscription management
        self._presence_subscribers: Dict[str, List[Callable]] = {}  # entity_id -> callbacks
        self._global_subscribers: List[Callable] = []
        
        # Background tasks
        self._cleanup_task: Optional[asyncio.Task] = None
        self._running = False
        self._lock = asyncio.Lock()
        
        logger.info("PresenceManager initialized")
    
    async def start(self):
        """Start the presence manager"""
        self._running = True
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())
        logger.info("PresenceManager started")
    
    async def stop(self):
        """Stop the presence manager"""
        self._running = False
        
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
        
        # Clear all presence state
        async with self._lock:
            self._presence.clear()
            self._sessions.clear()
            self._entity_sessions.clear()
        
        logger.info("PresenceManager stopped")
    
    async def _cleanup_loop(self):
        """Periodic cleanup of stale presence entries"""
        while self._running:
            try:
                await asyncio.sleep(self.cleanup_interval)
                await self._cleanup_stale_entries()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in cleanup loop: {e}")
    
    async def _cleanup_stale_entries(self):
        """Remove stale presence entries and sessions"""
        stale_entities = []
        stale_sessions = []
        
        async with self._lock:
            now = datetime.utcnow()
            
            # Find stale presence entries
            for entity_id, info in self._presence.items():
                if info.is_stale(self.stale_timeout):
                    stale_entities.append(entity_id)
            
            # Find stale sessions
            for session_id, session in self._sessions.items():
                time_since_activity = (now - session.last_activity).total_seconds()
                if time_since_activity > self.heartbeat_timeout:
                    stale_sessions.append(session_id)
        
        # Remove stale entries outside the lock
        for entity_id in stale_entities:
            await self.update_presence(
                entity_id, 
                PresenceStatus.OFFLINE,
                reason="timeout"
            )
        
        for session_id in stale_sessions:
            await self.remove_session(session_id, reason="timeout")
    
    # Presence Management
    
    async def register_presence(
        self,
        entity_id: str,
        entity_type: EntityType,
        status: PresenceStatus = PresenceStatus.ONLINE,
        metadata: Optional[Dict[str, Any]] = None,
        capabilities: Optional[List[str]] = None
    ) -> PresenceInfo:
        """Register a new presence entry"""
        async with self._lock:
            info = PresenceInfo(
                entity_id=entity_id,
                entity_type=entity_type,
                status=status,
                metadata=metadata or {},
                capabilities=capabilities or [],
            )
            self._presence[entity_id] = info
            
            # Initialize entity session tracking
            if entity_id not in self._entity_sessions:
                self._entity_sessions[entity_id] = set()
        
        logger.debug(f"Registered presence: {entity_id} ({entity_type.value})")
        await self._notify_presence_change(info, "online")
        return info
    
    async def update_presence(
        self,
        entity_id: str,
        status: PresenceStatus,
        status_message: Optional[str] = None,
        current_activity: Optional[str] = None,
        metadata_updates: Optional[Dict[str, Any]] = None,
        reason: str = "manual"
    ) -> Optional[PresenceInfo]:
        """Update presence status for an entity"""
        async with self._lock:
            if entity_id not in self._presence:
                logger.warning(f"Cannot update presence for unknown entity: {entity_id}")
                return None
            
            info = self._presence[entity_id]
            old_status = info.status
            
            info.update_status(status, status_message)
            
            if current_activity:
                info.current_activity = current_activity
            
            if metadata_updates:
                info.metadata.update(metadata_updates)
        
        logger.debug(f"Updated presence: {entity_id} -> {status.value} ({reason})")
        
        if old_status != status:
            await self._notify_presence_change(info, status.value)
        
        return info
    
    async def remove_presence(self, entity_id: str, reason: str = "disconnect"):
        """Remove a presence entry"""
        async with self._lock:
            if entity_id not in self._presence:
                return
            
            info = self._presence.pop(entity_id)
            
            # Clean up entity sessions
            if entity_id in self._entity_sessions:
                session_ids = self._entity_sessions.pop(entity_id)
                for session_id in session_ids:
                    self._sessions.pop(session_id, None)
        
        logger.debug(f"Removed presence: {entity_id} ({reason})")
        
        # Notify with offline status
        info.status = PresenceStatus.OFFLINE
        await self._notify_presence_change(info, "offline")
    
    async def touch_presence(self, entity_id: str):
        """Update last_seen timestamp for an entity"""
        async with self._lock:
            if entity_id in self._presence:
                self._presence[entity_id].touch()
    
    def get_presence(self, entity_id: str) -> Optional[PresenceInfo]:
        """Get presence info for an entity"""
        return self._presence.get(entity_id)
    
    def get_all_presence(
        self,
        entity_type: Optional[EntityType] = None,
        status: Optional[PresenceStatus] = None
    ) -> List[PresenceInfo]:
        """Get all presence entries, optionally filtered"""
        results = []
        for info in self._presence.values():
            if entity_type and info.entity_type != entity_type:
                continue
            if status and info.status != status:
                continue
            results.append(info)
        return results
    
    # Session Management
    
    async def create_session(
        self,
        entity_id: str,
        entity_type: EntityType,
        websocket_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> SessionInfo:
        """Create a new session"""
        session_id = f"sess_{uuid.uuid4().hex[:16]}"
        
        async with self._lock:
            session = SessionInfo(
                session_id=session_id,
                entity_id=entity_id,
                entity_type=entity_type,
                websocket_id=websocket_id,
                metadata=metadata or {},
            )
            self._sessions[session_id] = session
            
            # Track session for entity
            if entity_id not in self._entity_sessions:
                self._entity_sessions[entity_id] = set()
            self._entity_sessions[entity_id].add(session_id)
        
        logger.debug(f"Created session: {session_id} for {entity_id}")
        return session
    
    async def authenticate_session(
        self,
        session_id: str,
        auth_token: str,
        permissions: Optional[List[str]] = None
    ) -> Optional[SessionInfo]:
        """Mark a session as authenticated"""
        async with self._lock:
            if session_id not in self._sessions:
                return None
            
            session = self._sessions[session_id]
            session.authenticated = True
            session.auth_token = auth_token
            session.permissions = set(permissions or [])
            session.touch()
        
        logger.debug(f"Authenticated session: {session_id}")
        return session
    
    async def remove_session(self, session_id: str, reason: str = "disconnect"):
        """Remove a session"""
        async with self._lock:
            if session_id not in self._sessions:
                return
            
            session = self._sessions.pop(session_id)
            
            # Remove from entity tracking
            entity_id = session.entity_id
            if entity_id in self._entity_sessions:
                self._entity_sessions[entity_id].discard(session_id)
                
                # If no more sessions for entity, mark offline
                if not self._entity_sessions[entity_id]:
                    if entity_id in self._presence:
                        info = self._presence[entity_id]
                        info.status = PresenceStatus.OFFLINE
        
        logger.debug(f"Removed session: {session_id} ({reason})")
    
    def get_session(self, session_id: str) -> Optional[SessionInfo]:
        """Get session info"""
        return self._sessions.get(session_id)
    
    def get_entity_sessions(self, entity_id: str) -> List[SessionInfo]:
        """Get all sessions for an entity"""
        session_ids = self._entity_sessions.get(entity_id, set())
        return [self._sessions[sid] for sid in session_ids if sid in self._sessions]
    
    def get_all_sessions(
        self,
        authenticated_only: bool = False
    ) -> List[SessionInfo]:
        """Get all sessions"""
        sessions = list(self._sessions.values())
        if authenticated_only:
            sessions = [s for s in sessions if s.authenticated]
        return sessions
    
    # Subscriptions
    
    def subscribe_to_presence(
        self,
        entity_id: str,
        callback: Callable[[PresenceInfo, str], Any]
    ) -> str:
        """Subscribe to presence changes for a specific entity"""
        subscription_id = f"sub_{uuid.uuid4().hex[:8]}"
        
        if entity_id not in self._presence_subscribers:
            self._presence_subscribers[entity_id] = []
        
        self._presence_subscribers[entity_id].append((subscription_id, callback))
        return subscription_id
    
    def unsubscribe_from_presence(self, entity_id: str, subscription_id: str):
        """Unsubscribe from presence changes"""
        if entity_id in self._presence_subscribers:
            self._presence_subscribers[entity_id] = [
                (sid, cb) for sid, cb in self._presence_subscribers[entity_id]
                if sid != subscription_id
            ]
    
    def subscribe_to_all_presence(
        self,
        callback: Callable[[PresenceInfo, str], Any]
    ) -> str:
        """Subscribe to all presence changes"""
        subscription_id = f"sub_{uuid.uuid4().hex[:8]}"
        self._global_subscribers.append((subscription_id, callback))
        return subscription_id
    
    def unsubscribe_from_all_presence(self, subscription_id: str):
        """Unsubscribe from global presence changes"""
        self._global_subscribers = [
            (sid, cb) for sid, cb in self._global_subscribers
            if sid != subscription_id
        ]
    
    async def _notify_presence_change(self, info: PresenceInfo, change_type: str):
        """Notify subscribers of a presence change"""
        # Notify entity-specific subscribers
        if info.entity_id in self._presence_subscribers:
            for _, callback in self._presence_subscribers[info.entity_id]:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        asyncio.create_task(callback(info, change_type))
                    else:
                        callback(info, change_type)
                except Exception as e:
                    logger.error(f"Error notifying presence subscriber: {e}")
        
        # Notify global subscribers
        for _, callback in self._global_subscribers:
            try:
                if asyncio.iscoroutinefunction(callback):
                    asyncio.create_task(callback(info, change_type))
                else:
                    callback(info, change_type)
            except Exception as e:
                logger.error(f"Error notifying global presence subscriber: {e}")
    
    # Statistics
    
    def get_stats(self) -> Dict[str, Any]:
        """Get presence manager statistics"""
        return {
            "total_presence_entries": len(self._presence),
            "total_sessions": len(self._sessions),
            "online_entities": len([
                p for p in self._presence.values()
                if p.status == PresenceStatus.ONLINE
            ]),
            "authenticated_sessions": len([
                s for s in self._sessions.values() if s.authenticated
            ]),
            "presence_by_type": {
                et.value: len([p for p in self._presence.values() if p.entity_type == et])
                for et in EntityType
            },
            "subscribers": {
                "entity_specific": sum(len(subs) for subs in self._presence_subscribers.values()),
                "global": len(self._global_subscribers),
            }
        }


# Singleton instance
presence_manager = PresenceManager()


# Convenience functions for common operations

async def register_agent(
    agent_id: str,
    capabilities: Optional[List[str]] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> PresenceInfo:
    """Register an agent's presence"""
    return await presence_manager.register_presence(
        entity_id=agent_id,
        entity_type=EntityType.AGENT,
        status=PresenceStatus.ONLINE,
        capabilities=capabilities,
        metadata=metadata
    )


async def register_user(
    user_id: str,
    metadata: Optional[Dict[str, Any]] = None
) -> PresenceInfo:
    """Register a user's presence"""
    return await presence_manager.register_presence(
        entity_id=user_id,
        entity_type=EntityType.USER,
        status=PresenceStatus.ONLINE,
        metadata=metadata
    )


async def set_agent_busy(agent_id: str, activity: str):
    """Mark an agent as busy with an activity"""
    await presence_manager.update_presence(
        entity_id=agent_id,
        status=PresenceStatus.BUSY,
        current_activity=activity
    )


async def set_agent_available(agent_id: str):
    """Mark an agent as available"""
    await presence_manager.update_presence(
        entity_id=agent_id,
        status=PresenceStatus.ONLINE,
        current_activity=None
    )


def get_online_agents() -> List[PresenceInfo]:
    """Get all online agents"""
    return presence_manager.get_all_presence(
        entity_type=EntityType.AGENT,
        status=PresenceStatus.ONLINE
    )


def get_online_users() -> List[PresenceInfo]:
    """Get all online users"""
    return presence_manager.get_all_presence(
        entity_type=EntityType.USER,
        status=PresenceStatus.ONLINE
    )
