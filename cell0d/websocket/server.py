"""
WebSocket Server for cell0d
Handles multiple concurrent clients with event filtering and heartbeat
"""
import asyncio
import websockets
import json
import logging
from typing import Dict, Set, Optional, List, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from websockets.server import WebSocketServerProtocol
from websockets.exceptions import ConnectionClosed, InvalidMessage

from events.eventbus import (
    EventBus, Event, EventType, event_bus,
    create_heartbeat_event, create_system_status_event
)

logger = logging.getLogger("cell0d.websocket")


@dataclass
class ClientConnection:
    """Represents a connected WebSocket client"""
    websocket: WebSocketServerProtocol
    client_id: str
    connected_at: datetime = field(default_factory=datetime.utcnow)
    last_ping: datetime = field(default_factory=datetime.utcnow)
    subscribed_events: Set[EventType] = field(default_factory=set)
    metadata: Dict[str, Any] = field(default_factory=dict)
    sequence_number: int = 0
    is_alive: bool = True
    
    def __post_init__(self):
        # Default to subscribing to all events if none specified
        if not self.subscribed_events:
            self.subscribed_events = {EventType.ALL}
    
    def accepts_event(self, event: Event) -> bool:
        """Check if client accepts this event type"""
        if EventType.ALL in self.subscribed_events:
            return True
        return event.type in self.subscribed_events
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "client_id": self.client_id,
            "connected_at": self.connected_at.isoformat(),
            "last_ping": self.last_ping.isoformat(),
            "subscribed_events": [et.value for et in self.subscribed_events],
            "sequence": self.sequence_number,
            "is_alive": self.is_alive
        }


class WebSocketServer:
    """
    WebSocket server for real-time event streaming
    Features:
    - Multiple concurrent clients
    - Event filtering per client
    - Heartbeat/ping-pong for connection health
    - Event history buffer for new connections
    - Automatic reconnection support
    """
    
    def __init__(self, host: str = "0.0.0.0", port: int = 8765,
                 event_bus: EventBus = None,
                 heartbeat_interval: float = 30.0,
                 heartbeat_timeout: float = 60.0):
        self.host = host
        self.port = port
        self.event_bus = event_bus or event_bus
        self.heartbeat_interval = heartbeat_interval
        self.heartbeat_timeout = heartbeat_timeout
        
        self.clients: Dict[str, ClientConnection] = {}
        self.server = None
        self._running = False
        self._heartbeat_task: Optional[asyncio.Task] = None
        self._event_bus_subscription = None
        
        # Statistics
        self.stats = {
            "total_connections": 0,
            "messages_sent": 0,
            "messages_received": 0,
            "start_time": None
        }
        
        logger.info(f"WebSocketServer initialized on {host}:{port}")
    
    async def start(self):
        """Start the WebSocket server"""
        self._running = True
        self.stats["start_time"] = datetime.utcnow().isoformat()
        
        # Subscribe to all events from the event bus
        self._event_bus_subscription = self.event_bus.subscribe(
            EventType.ALL, self._on_event
        )
        
        # Start heartbeat task
        self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())
        
        # Start WebSocket server
        self.server = await websockets.serve(
            self._handle_client,
            self.host,
            self.port,
            ping_interval=None,  # We handle our own heartbeat
            ping_timeout=None
        )
        
        logger.info(f"WebSocket server started on ws://{self.host}:{self.port}")
        
        # Emit server start event
        await self.event_bus.emit(create_system_status_event(
            "websocket_server_started",
            {"host": self.host, "port": self.port}
        ))
    
    async def stop(self):
        """Stop the WebSocket server"""
        self._running = False
        
        # Cancel heartbeat task
        if self._heartbeat_task:
            self._heartbeat_task.cancel()
            try:
                await self._heartbeat_task
            except asyncio.CancelledError:
                pass
        
        # Close all client connections
        close_tasks = []
        for client in list(self.clients.values()):
            close_tasks.append(asyncio.create_task(
                self._disconnect_client(client, "server_shutdown")
            ))
        if close_tasks:
            await asyncio.gather(*close_tasks, return_exceptions=True)
        
        # Unsubscribe from event bus
        if self._event_bus_subscription:
            self.event_bus.unsubscribe(EventType.ALL, self._on_event)
        
        # Close server
        if self.server:
            self.server.close()
            await self.server.wait_closed()
        
        logger.info("WebSocket server stopped")
    
    async def _handle_client(self, websocket: WebSocketServerProtocol, path: str):
        """Handle a new WebSocket connection"""
        client_id = f"client_{id(websocket)}_{datetime.utcnow().timestamp()}"
        
        try:
            # Create client connection object
            client = ClientConnection(
                websocket=websocket,
                client_id=client_id
            )
            self.clients[client_id] = client
            self.stats["total_connections"] += 1
            
            logger.info(f"Client connected: {client_id}")
            
            # Send welcome message with connection info
            await self._send_message(client, {
                "type": "connection_established",
                "client_id": client_id,
                "timestamp": datetime.utcnow().isoformat(),
                "server_version": "cell0d-1.0.0"
            })
            
            # Send event history if requested
            await self._send_event_history(client)
            
            # Emit client connect event
            await self.event_bus.emit(Event(
                type=EventType.CLIENT_CONNECT,
                source="websocket.server",
                data={"client_id": client_id, "path": path}
            ))
            
            # Handle client messages
            async for message in websocket:
                await self._handle_message(client, message)
                
        except ConnectionClosed:
            logger.info(f"Client disconnected: {client_id}")
        except Exception as e:
            logger.error(f"Error handling client {client_id}: {e}")
        finally:
            if client_id in self.clients:
                await self._disconnect_client(self.clients[client_id], "connection_closed")
    
    async def _handle_message(self, client: ClientConnection, message: str):
        """Handle incoming message from client"""
        self.stats["messages_received"] += 1
        
        try:
            data = json.loads(message)
            msg_type = data.get("type", "unknown")
            
            if msg_type == "ping":
                await self._handle_ping(client, data)
            elif msg_type == "subscribe":
                await self._handle_subscribe(client, data)
            elif msg_type == "unsubscribe":
                await self._handle_unsubscribe(client, data)
            elif msg_type == "get_history":
                await self._handle_get_history(client, data)
            elif msg_type == "get_stats":
                await self._handle_get_stats(client)
            elif msg_type == "echo":
                await self._send_message(client, {"type": "echo", "data": data})
            else:
                await self._send_message(client, {
                    "type": "error",
                    "error": f"Unknown message type: {msg_type}"
                })
                
        except json.JSONDecodeError:
            await self._send_message(client, {
                "type": "error",
                "error": "Invalid JSON"
            })
        except Exception as e:
            logger.error(f"Error handling message: {e}")
            await self._send_message(client, {
                "type": "error",
                "error": str(e)
            })
    
    async def _handle_ping(self, client: ClientConnection, data: dict):
        """Handle ping message"""
        client.last_ping = datetime.utcnow()
        client.sequence_number = data.get("sequence", client.sequence_number + 1)
        
        await self._send_message(client, {
            "type": "pong",
            "sequence": client.sequence_number,
            "timestamp": datetime.utcnow().isoformat(),
            "client_id": client.client_id
        })
    
    async def _handle_subscribe(self, client: ClientConnection, data: dict):
        """Handle subscription request"""
        event_types = data.get("event_types", ["all"])
        
        # Clear existing subscriptions if specified
        if data.get("replace", False):
            client.subscribed_events.clear()
        
        for et_str in event_types:
            try:
                event_type = EventType(et_str)
                client.subscribed_events.add(event_type)
            except ValueError:
                pass  # Invalid event type, skip
        
        await self._send_message(client, {
            "type": "subscription_updated",
            "subscribed_events": [et.value for et in client.subscribed_events]
        })
        
        logger.debug(f"Client {client.client_id} subscribed to: {event_types}")
    
    async def _handle_unsubscribe(self, client: ClientConnection, data: dict):
        """Handle unsubscription request"""
        event_types = data.get("event_types", [])
        
        for et_str in event_types:
            try:
                event_type = EventType(et_str)
                client.subscribed_events.discard(event_type)
            except ValueError:
                pass
        
        await self._send_message(client, {
            "type": "subscription_updated",
            "subscribed_events": [et.value for et in client.subscribed_events]
        })
    
    async def _handle_get_history(self, client: ClientConnection, data: dict):
        """Handle history request"""
        event_type_str = data.get("event_type")
        limit = data.get("limit", 100)
        
        event_type = None
        if event_type_str:
            try:
                event_type = EventType(event_type_str)
            except ValueError:
                pass
        
        history = self.event_bus.get_history(event_type=event_type, limit=limit)
        
        await self._send_message(client, {
            "type": "event_history",
            "events": [e.to_dict() for e in history],
            "count": len(history)
        })
    
    async def _handle_get_stats(self, client: ClientConnection):
        """Handle stats request"""
        await self._send_message(client, {
            "type": "server_stats",
            "stats": {
                **self.stats,
                "connected_clients": len(self.clients),
                "client_ids": list(self.clients.keys())
            }
        })
    
    async def _send_event_history(self, client: ClientConnection):
        """Send recent event history to newly connected client"""
        try:
            # Get last 50 events of types the client is interested in
            if EventType.ALL in client.subscribed_events:
                history = self.event_bus.get_history(limit=50)
            else:
                history = []
                for event_type in client.subscribed_events:
                    history.extend(self.event_bus.get_history(event_type=event_type, limit=50))
                # Sort by timestamp and limit
                history.sort(key=lambda e: e.timestamp)
                history = history[-50:]
            
            if history:
                await self._send_message(client, {
                    "type": "event_history",
                    "events": [e.to_dict() for e in history],
                    "count": len(history),
                    "note": "Recent events before connection"
                })
        except Exception as e:
            logger.error(f"Error sending history: {e}")
    
    async def _send_message(self, client: ClientConnection, message: dict):
        """Send message to a client"""
        try:
            if client.is_alive and client.websocket.open:
                await client.websocket.send(json.dumps(message))
                self.stats["messages_sent"] += 1
        except ConnectionClosed:
            client.is_alive = False
        except Exception as e:
            logger.error(f"Error sending message to {client.client_id}: {e}")
            client.is_alive = False
    
    async def _disconnect_client(self, client: ClientConnection, reason: str):
        """Disconnect a client"""
        client.is_alive = False
        
        if client.client_id in self.clients:
            del self.clients[client.client_id]
        
        try:
            await client.websocket.close()
        except:
            pass
        
        # Emit disconnect event
        await self.event_bus.emit(Event(
            type=EventType.CLIENT_DISCONNECT,
            source="websocket.server",
            data={"client_id": client.client_id, "reason": reason}
        ))
        
        logger.info(f"Client disconnected: {client.client_id} ({reason})")
    
    async def _on_event(self, event: Event):
        """Handle events from the event bus and forward to clients"""
        if not self._running:
            return
        
        message = {
            "type": "event",
            "event": event.to_dict()
        }
        
        # Send to all clients that accept this event type
        send_tasks = []
        for client in list(self.clients.values()):
            if client.accepts_event(event) and client.is_alive:
                send_tasks.append(asyncio.create_task(
                    self._send_message(client, message)
                ))
        
        if send_tasks:
            await asyncio.gather(*send_tasks, return_exceptions=True)
    
    async def _heartbeat_loop(self):
        """Periodic heartbeat to check client health"""
        while self._running:
            try:
                await asyncio.sleep(self.heartbeat_interval)
                
                now = datetime.utcnow()
                dead_clients = []
                
                for client in list(self.clients.values()):
                    # Check if client hasn't pinged recently
                    time_since_ping = (now - client.last_ping).total_seconds()
                    
                    if time_since_ping > self.heartbeat_timeout:
                        logger.warning(f"Client {client.client_id} timed out")
                        dead_clients.append(client)
                    else:
                        # Send server-side ping
                        await self._send_message(client, {
                            "type": "ping",
                            "timestamp": now.isoformat(),
                            "sequence": client.sequence_number
                        })
                
                # Disconnect dead clients
                for client in dead_clients:
                    await self._disconnect_client(client, "timeout")
                
                # Emit heartbeat event
                await self.event_bus.emit(create_heartbeat_event(
                    "server", 0
                ))
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in heartbeat loop: {e}")
    
    def get_connected_clients(self) -> List[Dict[str, Any]]:
        """Get list of connected clients"""
        return [c.to_dict() for c in self.clients.values()]
    
    async def broadcast(self, message: dict, exclude_client: str = None):
        """Broadcast a message to all clients"""
        send_tasks = []
        for client in list(self.clients.values()):
            if client.client_id != exclude_client and client.is_alive:
                send_tasks.append(asyncio.create_task(
                    self._send_message(client, message)
                ))
        
        if send_tasks:
            await asyncio.gather(*send_tasks, return_exceptions=True)