"""
gateway_ws.py - WebSocket Gateway Server for Cell 0 OS

Production-ready WebSocket gateway providing:
- Real-time control plane capabilities
- Session management with presence tracking
- Event streaming (agent events, system events, channel events)
- JSON-RPC protocol for commands
- Token-based authentication
- Multi-agent routing support
- Message routing between agents and channels

Port: 18801 (separate from HTTP API on 18800)
"""

import asyncio
import logging
import json
import uuid
import time
from typing import Dict, List, Optional, Set, Any, Callable, Union
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import defaultdict
import traceback

import websockets
from websockets.server import WebSocketServerProtocol
from websockets.exceptions import ConnectionClosed, ConnectionClosedOK, ConnectionClosedError

# Import Cell 0 OS components
try:
    from service.presence import (
        presence_manager, PresenceInfo, SessionInfo,
        EntityType, PresenceStatus,
        register_agent, register_user
    )
    from service.gateway_protocol import (
        ProtocolHandler, JsonRpcRequest, JsonRpcResponse,
        JsonRpcNotification, JsonRpcErrorCode, GatewayError,
        AuthenticationError, protocol_handler
    )
except ImportError:
    # Fallback for standalone usage
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from service.presence import (
        presence_manager, PresenceInfo, SessionInfo,
        EntityType, PresenceStatus,
        register_agent, register_user
    )
    from service.gateway_protocol import (
        ProtocolHandler, JsonRpcRequest, JsonRpcResponse,
        JsonRpcNotification, JsonRpcErrorCode, GatewayError,
        AuthenticationError, protocol_handler
    )

logger = logging.getLogger("cell0.gateway.ws")


@dataclass
class ConnectionState:
    """State for a WebSocket connection"""
    websocket: WebSocketServerProtocol
    connection_id: str
    connected_at: datetime = field(default_factory=datetime.utcnow)
    last_activity: datetime = field(default_factory=datetime.utcnow)
    session: Optional[SessionInfo] = None
    authenticated: bool = False
    subscriptions: Set[str] = field(default_factory=set)
    entity_id: Optional[str] = None
    entity_type: Optional[EntityType] = None
    
    def touch(self):
        """Update last activity timestamp"""
        self.last_activity = datetime.utcnow()
    
    @property
    def is_active(self) -> bool:
        """Check if connection is still active"""
        return self.websocket.open


class AuthenticationManager:
    """Manages token-based authentication"""
    
    def __init__(self, token_secret: Optional[str] = None):
        self.token_secret = token_secret or uuid.uuid4().hex
        self._tokens: Dict[str, Dict[str, Any]] = {}  # token -> token info
        self._revoked_tokens: Set[str] = set()
    
    def generate_token(
        self,
        entity_id: str,
        entity_type: str,
        permissions: Optional[List[str]] = None,
        expires_in_hours: int = 24
    ) -> str:
        """Generate a new authentication token"""
        token = f"cell0_{uuid.uuid4().hex}_{int(time.time())}"
        
        expires_at = datetime.utcnow() + timedelta(hours=expires_in_hours)
        
        self._tokens[token] = {
            "entity_id": entity_id,
            "entity_type": entity_type,
            "permissions": permissions or ["*"],
            "created_at": datetime.utcnow(),
            "expires_at": expires_at,
        }
        
        return token
    
    def validate_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Validate a token and return token info"""
        if token in self._revoked_tokens:
            return None
        
        token_info = self._tokens.get(token)
        if not token_info:
            return None
        
        # Check expiration
        if datetime.utcnow() > token_info["expires_at"]:
            return None
        
        return token_info
    
    def revoke_token(self, token: str):
        """Revoke a token"""
        self._revoked_tokens.add(token)
        self._tokens.pop(token, None)
    
    def cleanup_expired_tokens(self):
        """Remove expired tokens"""
        now = datetime.utcnow()
        expired = [
            token for token, info in self._tokens.items()
            if now > info["expires_at"]
        ]
        for token in expired:
            self._tokens.pop(token, None)


class EventRouter:
    """Routes events between agents and channels"""
    
    def __init__(self):
        self._channel_subscribers: Dict[str, Set[str]] = defaultdict(set)  # channel -> connection_ids
        self._agent_routes: Dict[str, str] = {}  # agent_id -> connection_id
        self._event_filters: Dict[str, Callable] = {}  # connection_id -> filter function
    
    def subscribe_to_channel(self, connection_id: str, channel: str):
        """Subscribe a connection to a channel"""
        self._channel_subscribers[channel].add(connection_id)
        logger.debug(f"{connection_id} subscribed to channel: {channel}")
    
    def unsubscribe_from_channel(self, connection_id: str, channel: str):
        """Unsubscribe a connection from a channel"""
        self._channel_subscribers[channel].discard(connection_id)
        logger.debug(f"{connection_id} unsubscribed from channel: {channel}")
    
    def get_channel_subscribers(self, channel: str) -> Set[str]:
        """Get all subscribers to a channel"""
        return self._channel_subscribers[channel].copy()
    
    def register_agent_route(self, agent_id: str, connection_id: str):
        """Register a route to an agent"""
        self._agent_routes[agent_id] = connection_id
        logger.debug(f"Registered route for agent {agent_id} -> {connection_id}")
    
    def unregister_agent_route(self, agent_id: str):
        """Unregister a route to an agent"""
        self._agent_routes.pop(agent_id, None)
    
    def get_agent_route(self, agent_id: str) -> Optional[str]:
        """Get the connection ID for an agent"""
        return self._agent_routes.get(agent_id)
    
    def set_event_filter(self, connection_id: str, filter_fn: Callable):
        """Set an event filter for a connection"""
        self._event_filters[connection_id] = filter_fn
    
    def should_receive_event(
        self,
        connection_id: str,
        event_type: str,
        event_data: Dict[str, Any]
    ) -> bool:
        """Check if a connection should receive an event"""
        filter_fn = self._event_filters.get(connection_id)
        if filter_fn:
            return filter_fn(event_type, event_data)
        return True


class WebSocketGateway:
    """
    WebSocket Gateway Server for Cell 0 OS
    
    Provides real-time control plane capabilities with:
    - JSON-RPC protocol over WebSocket
    - Session management and presence tracking
    - Event streaming and routing
    - Multi-agent support
    - Token-based authentication
    """
    
    def __init__(
        self,
        host: str = "0.0.0.0",
        port: int = 18801,
        heartbeat_interval: float = 30.0,
        heartbeat_timeout: float = 60.0,
        max_message_size: int = 10 * 1024 * 1024,  # 10MB
        enable_compression: bool = True,
    ):
        self.host = host
        self.port = port
        self.heartbeat_interval = heartbeat_interval
        self.heartbeat_timeout = heartbeat_timeout
        self.max_message_size = max_message_size
        self.enable_compression = enable_compression
        
        # Connection management
        self._connections: Dict[str, ConnectionState] = {}
        self._server: Optional[websockets.WebSocketServer] = None
        
        # Subsystems
        self.auth_manager = AuthenticationManager()
        self.event_router = EventRouter()
        self.protocol = protocol_handler
        
        # Tasks
        self._running = False
        self._heartbeat_task: Optional[asyncio.Task] = None
        self._cleanup_task: Optional[asyncio.Task] = None
        
        # Event bus integration
        self._event_bus_subscriptions: List[str] = []
        
        # Statistics
        self.stats = {
            "connections_total": 0,
            "connections_active": 0,
            "messages_sent": 0,
            "messages_received": 0,
            "errors": 0,
            "start_time": None,
        }
        
        logger.info(f"WebSocketGateway initialized on {host}:{port}")
    
    async def start(self):
        """Start the WebSocket gateway"""
        self._running = True
        self.stats["start_time"] = datetime.utcnow().isoformat()
        
        # Start presence manager
        await presence_manager.start()
        
        # Start heartbeat task
        self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())
        
        # Start cleanup task
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())
        
        # Start WebSocket server
        self._server = await websockets.serve(
            self._handle_connection,
            self.host,
            self.port,
            ping_interval=None,  # We handle our own heartbeat
            ping_timeout=None,
            max_size=self.max_message_size,
            compression=self.enable_compression,
        )
        
        logger.info(f"WebSocket Gateway started on ws://{self.host}:{self.port}")
    
    async def stop(self):
        """Stop the WebSocket gateway gracefully"""
        self._running = False
        
        logger.info("Stopping WebSocket Gateway...")
        
        # Cancel background tasks
        if self._heartbeat_task:
            self._heartbeat_task.cancel()
            try:
                await self._heartbeat_task
            except asyncio.CancelledError:
                pass
        
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
        
        # Close all connections
        close_tasks = []
        for conn in list(self._connections.values()):
            close_tasks.append(asyncio.create_task(self._close_connection(
                conn, "server_shutdown"
            )))
        
        if close_tasks:
            await asyncio.gather(*close_tasks, return_exceptions=True)
        
        # Stop presence manager
        await presence_manager.stop()
        
        # Close server
        if self._server:
            self._server.close()
            await self._server.wait_closed()
        
        logger.info("WebSocket Gateway stopped")
    
    async def _handle_connection(self, websocket: WebSocketServerProtocol, path: str):
        """Handle a new WebSocket connection"""
        connection_id = f"conn_{uuid.uuid4().hex[:12]}"
        
        try:
            # Create connection state
            conn = ConnectionState(
                websocket=websocket,
                connection_id=connection_id,
            )
            self._connections[connection_id] = conn
            self.stats["connections_total"] += 1
            self.stats["connections_active"] = len(self._connections)
            
            logger.info(f"New connection: {connection_id} from {websocket.remote_address}")
            
            # Send welcome message
            await self._send_message(conn, {
                "jsonrpc": "2.0",
                "method": "connection.welcome",
                "params": {
                    "connection_id": connection_id,
                    "server_version": "cell0-1.0.0",
                    "timestamp": datetime.utcnow().isoformat(),
                    "capabilities": [
                        "jsonrpc_2.0",
                        "event_streaming",
                        "presence",
                        "multi_agent",
                        "channel_subscriptions",
                    ]
                }
            })
            
            # Handle messages
            async for message in websocket:
                await self._handle_message(conn, message)
                
        except ConnectionClosed:
            logger.debug(f"Connection closed: {connection_id}")
        except Exception as e:
            logger.error(f"Error handling connection {connection_id}: {e}")
            self.stats["errors"] += 1
        finally:
            await self._cleanup_connection(connection_id)
    
    async def _handle_message(self, conn: ConnectionState, message: str):
        """Handle an incoming message"""
        conn.touch()
        self.stats["messages_received"] += 1
        
        try:
            # Build context
            context = {
                "connection_id": conn.connection_id,
                "session": conn.session,
                "authenticated": conn.authenticated,
                "gateway": self,
            }
            
            # Process through protocol handler
            result = await self.protocol.handle_message(message, context)
            
            if result is not None:
                # Send response
                if isinstance(result, list):
                    # Batch response
                    response_data = [r.to_dict() for r in result]
                else:
                    response_data = result.to_dict()
                
                await self._send_message(conn, response_data)
        
        except Exception as e:
            logger.error(f"Error handling message from {conn.connection_id}: {e}")
            self.stats["errors"] += 1
            
            # Send error response
            error_response = {
                "jsonrpc": "2.0",
                "error": {
                    "code": JsonRpcErrorCode.INTERNAL_ERROR.value,
                    "message": "Internal server error",
                },
                "id": None
            }
            await self._send_message(conn, error_response)
    
    async def _send_message(self, conn: ConnectionState, message: Dict[str, Any]):
        """Send a message to a connection"""
        try:
            if conn.is_active:
                await conn.websocket.send(json.dumps(message))
                self.stats["messages_sent"] += 1
                conn.touch()
        except ConnectionClosed:
            logger.debug(f"Cannot send to closed connection: {conn.connection_id}")
        except Exception as e:
            logger.error(f"Error sending message to {conn.connection_id}: {e}")
    
    async def _send_notification(
        self,
        connection_id: str,
        notification: JsonRpcNotification
    ):
        """Send a notification to a specific connection"""
        if connection_id not in self._connections:
            return
        
        conn = self._connections[connection_id]
        await self._send_message(conn, notification.to_dict())
    
    async def broadcast_notification(
        self,
        notification: JsonRpcNotification,
        exclude_connection: Optional[str] = None
    ):
        """Broadcast a notification to all connections"""
        tasks = []
        for conn_id, conn in self._connections.items():
            if conn_id != exclude_connection and conn.is_active:
                tasks.append(asyncio.create_task(
                    self._send_message(conn, notification.to_dict())
                ))
        
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
    
    async def _close_connection(self, conn: ConnectionState, reason: str):
        """Close a connection"""
        try:
            # Close WebSocket
            if conn.websocket.open:
                await conn.websocket.close()
            
            logger.debug(f"Closed connection {conn.connection_id}: {reason}")
        except Exception as e:
            logger.debug(f"Error closing connection {conn.connection_id}: {e}")
    
    async def _cleanup_connection(self, connection_id: str):
        """Clean up a disconnected connection"""
        if connection_id not in self._connections:
            return
        
        conn = self._connections.pop(connection_id)
        self.stats["connections_active"] = len(self._connections)
        
        # Remove from presence
        if conn.entity_id:
            await presence_manager.remove_presence(conn.entity_id, reason="disconnect")
            
            # Unregister agent route
            if conn.entity_type == EntityType.AGENT:
                self.event_router.unregister_agent_route(conn.entity_id)
        
        # Remove session
        if conn.session:
            await presence_manager.remove_session(conn.session.session_id, reason="disconnect")
        
        logger.info(f"Cleaned up connection: {connection_id}")
    
    async def _heartbeat_loop(self):
        """Periodic heartbeat and stale connection cleanup"""
        while self._running:
            try:
                await asyncio.sleep(self.heartbeat_interval)
                
                now = datetime.utcnow()
                stale_connections = []
                
                for conn_id, conn in self._connections.items():
                    time_since_activity = (now - conn.last_activity).total_seconds()
                    
                    if time_since_activity > self.heartbeat_timeout:
                        stale_connections.append(conn_id)
                    else:
                        # Send heartbeat ping
                        await self._send_message(conn, {
                            "jsonrpc": "2.0",
                            "method": "heartbeat",
                            "params": {
                                "timestamp": now.isoformat(),
                            }
                        })
                
                # Clean up stale connections
                for conn_id in stale_connections:
                    logger.warning(f"Connection {conn_id} timed out")
                    if conn_id in self._connections:
                        await self._cleanup_connection(conn_id)
                        
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in heartbeat loop: {e}")
    
    async def _cleanup_loop(self):
        """Periodic cleanup tasks"""
        while self._running:
            try:
                await asyncio.sleep(300)  # Every 5 minutes
                self.auth_manager.cleanup_expired_tokens()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in cleanup loop: {e}")
    
    # Public API methods
    
    def get_connection(self, connection_id: str) -> Optional[ConnectionState]:
        """Get connection state by ID"""
        return self._connections.get(connection_id)
    
    def get_connection_by_entity(self, entity_id: str) -> Optional[ConnectionState]:
        """Get connection by entity ID"""
        for conn in self._connections.values():
            if conn.entity_id == entity_id:
                return conn
        return None
    
    def get_all_connections(self) -> List[ConnectionState]:
        """Get all active connections"""
        return list(self._connections.values())
    
    async def send_to_entity(self, entity_id: str, message: Dict[str, Any]) -> bool:
        """Send a message to a specific entity"""
        conn = self.get_connection_by_entity(entity_id)
        if conn:
            await self._send_message(conn, message)
            return True
        return False
    
    async def route_to_agent(self, agent_id: str, message: Dict[str, Any]) -> bool:
        """Route a message to a specific agent"""
        connection_id = self.event_router.get_agent_route(agent_id)
        if connection_id and connection_id in self._connections:
            await self._send_message(self._connections[connection_id], message)
            return True
        return False


def register_gateway_methods(gateway: WebSocketGateway):
    """Register gateway-specific JSON-RPC methods"""
    
    @gateway.protocol.registry.register("auth.authenticate", require_auth=False)
    async def authenticate(
        token: str,
        entity_id: Optional[str] = None,
        entity_type: str = "agent",
        context=None,
        **kwargs
    ) -> Dict[str, Any]:
        """Authenticate a connection"""
        if not context:
            raise AuthenticationError("No connection context")
        
        conn_id = context.get("connection_id")
        conn = gateway.get_connection(conn_id)
        if not conn:
            raise AuthenticationError("Connection not found")
        
        # Validate token
        token_info = gateway.auth_manager.validate_token(token)
        if not token_info:
            raise AuthenticationError("Invalid or expired token")
        
        # Use token entity_id if not provided
        entity_id = entity_id or token_info["entity_id"]
        entity_type_enum = EntityType(entity_type)
        
        # Create session
        session = await presence_manager.create_session(
            entity_id=entity_id,
            entity_type=entity_type_enum,
            websocket_id=conn_id,
        )
        
        # Authenticate session
        await presence_manager.authenticate_session(
            session_id=session.session_id,
            auth_token=token,
            permissions=token_info.get("permissions", []),
        )
        
        # Update connection state
        conn.session = session
        conn.authenticated = True
        conn.entity_id = entity_id
        conn.entity_type = entity_type_enum
        
        # Register presence
        if entity_type_enum == EntityType.AGENT:
            await register_agent(
                agent_id=entity_id,
                capabilities=kwargs.get("capabilities", []),
                metadata=kwargs.get("metadata", {})
            )
            gateway.event_router.register_agent_route(entity_id, conn_id)
        else:
            await register_user(
                user_id=entity_id,
                metadata=kwargs.get("metadata", {})
            )
        
        return {
            "success": True,
            "session_id": session.session_id,
            "entity_id": entity_id,
            "entity_type": entity_type,
        }
    
    @gateway.protocol.registry.register("auth.generateToken", require_auth=True)
    async def generate_token(
        entity_id: str,
        entity_type: str = "agent",
        permissions: Optional[List[str]] = None,
        expires_in_hours: int = 24,
        context=None,
        **kwargs
    ) -> Dict[str, Any]:
        """Generate a new authentication token"""
        token = gateway.auth_manager.generate_token(
            entity_id=entity_id,
            entity_type=entity_type,
            permissions=permissions,
            expires_in_hours=expires_in_hours,
        )
        return {
            "token": token,
            "expires_in_hours": expires_in_hours,
        }
    
    @gateway.protocol.registry.register("session.getInfo", require_auth=True)
    async def get_session_info(context=None, **kwargs) -> Dict[str, Any]:
        """Get current session information"""
        if not context or not context.get("session"):
            raise AuthenticationError("No active session")
        
        session = context["session"]
        return session.to_dict()
    
    @gateway.protocol.registry.register("presence.update", require_auth=True)
    async def update_presence(
        status: str,
        status_message: Optional[str] = None,
        activity: Optional[str] = None,
        context=None,
        **kwargs
    ) -> Dict[str, Any]:
        """Update presence status"""
        if not context or not context.get("session"):
            raise AuthenticationError("No active session")
        
        session = context["session"]
        
        await presence_manager.update_presence(
            entity_id=session.entity_id,
            status=PresenceStatus(status),
            status_message=status_message,
            current_activity=activity,
        )
        
        return {"success": True}
    
    @gateway.protocol.registry.register("presence.get", require_auth=False)
    async def get_presence(
        entity_id: Optional[str] = None,
        entity_type: Optional[str] = None,
        context=None,
        **kwargs
    ) -> Union[Dict[str, Any], List[Dict[str, Any]]]:
        """Get presence information"""
        if entity_id:
            info = presence_manager.get_presence(entity_id)
            if info:
                return info.to_dict()
            return {"error": "Entity not found"}
        
        entity_type_enum = EntityType(entity_type) if entity_type else None
        all_presence = presence_manager.get_all_presence(entity_type_enum)
        return [p.to_dict() for p in all_presence]
    
    @gateway.protocol.registry.register("channel.subscribe", require_auth=True)
    async def subscribe_channel(
        channel: str,
        context=None,
        **kwargs
    ) -> Dict[str, Any]:
        """Subscribe to a channel"""
        if not context:
            raise AuthenticationError("No connection context")
        
        conn_id = context.get("connection_id")
        gateway.event_router.subscribe_to_channel(conn_id, channel)
        
        # Update session subscriptions
        if context.get("session"):
            context["session"].add_subscription(channel)
        
        return {"success": True, "channel": channel}
    
    @gateway.protocol.registry.register("channel.unsubscribe", require_auth=True)
    async def unsubscribe_channel(
        channel: str,
        context=None,
        **kwargs
    ) -> Dict[str, Any]:
        """Unsubscribe from a channel"""
        if not context:
            raise AuthenticationError("No connection context")
        
        conn_id = context.get("connection_id")
        gateway.event_router.unsubscribe_from_channel(conn_id, channel)
        
        if context.get("session"):
            context["session"].remove_subscription(channel)
        
        return {"success": True, "channel": channel}
    
    @gateway.protocol.registry.register("channel.publish", require_auth=True)
    async def publish_to_channel(
        channel: str,
        message: Dict[str, Any],
        context=None,
        **kwargs
    ) -> Dict[str, Any]:
        """Publish a message to a channel"""
        notification = JsonRpcNotification(
            method="channel.message",
            params={
                "channel": channel,
                "message": message,
                "timestamp": datetime.utcnow().isoformat(),
            }
        )
        
        # Get subscribers
        subscribers = gateway.event_router.get_channel_subscribers(channel)
        
        # Send to all subscribers
        tasks = []
        for subscriber_conn_id in subscribers:
            if subscriber_conn_id in gateway._connections:
                conn = gateway._connections[subscriber_conn_id]
                tasks.append(asyncio.create_task(
                    gateway._send_message(conn, notification.to_dict())
                ))
        
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        
        return {"success": True, "recipients": len(subscribers)}
    
    @gateway.protocol.registry.register("agent.send", require_auth=True)
    async def send_to_agent(
        agent_id: str,
        message: Dict[str, Any],
        context=None,
        **kwargs
    ) -> Dict[str, Any]:
        """Send a message to a specific agent"""
        success = await gateway.route_to_agent(agent_id, {
            "jsonrpc": "2.0",
            "method": "agent.message",
            "params": {
                "from": context.get("session", {}).entity_id if context.get("session") else None,
                "message": message,
                "timestamp": datetime.utcnow().isoformat(),
            }
        })
        
        return {"success": success}
    
    @gateway.protocol.registry.register("agent.list", require_auth=False)
    async def list_agents(context=None, **kwargs) -> List[Dict[str, Any]]:
        """List all online agents"""
        from service.presence import get_online_agents
        agents = get_online_agents()
        return [a.to_dict() for a in agents]
    
    @gateway.protocol.registry.register("gateway.getStats", require_auth=True)
    async def get_gateway_stats(context=None, **kwargs) -> Dict[str, Any]:
        """Get gateway statistics"""
        return {
            **gateway.stats,
            "presence": presence_manager.get_stats(),
            "active_connections": len(gateway._connections),
        }


# Global gateway instance
gateway = WebSocketGateway()
register_gateway_methods(gateway)


async def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Cell 0 OS WebSocket Gateway")
    parser.add_argument("--host", default="0.0.0.0", help="WebSocket host")
    parser.add_argument("--port", type=int, default=18801, help="WebSocket port")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose logging")
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)
    
    # Create and start gateway
    gw = WebSocketGateway(host=args.host, port=args.port)
    register_gateway_methods(gw)
    
    print(f"""
╔════════════════════════════════════════════════════════════════╗
║           Cell 0 OS WebSocket Gateway                           ║
╠════════════════════════════════════════════════════════════════╣
║  WebSocket: ws://{args.host}:{args.port:<5}                              ║
╠════════════════════════════════════════════════════════════════╣
║  Features:                                                      ║
║    ✓ JSON-RPC 2.0 Protocol                                     ║
║    ✓ Token-based Authentication                                ║
║    ✓ Session Management                                        ║
║    ✓ Presence Tracking                                         ║
║    ✓ Event Streaming                                           ║
║    ✓ Multi-Agent Routing                                       ║
║    ✓ Channel Pub/Sub                                           ║
╚════════════════════════════════════════════════════════════════╝
""")
    
    try:
        await gw.start()
        # Keep running
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        print("\nShutting down...")
    finally:
        await gw.stop()


if __name__ == "__main__":
    asyncio.run(main())
