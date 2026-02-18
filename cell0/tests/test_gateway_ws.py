"""
test_gateway_ws.py - Test Suite for Cell 0 OS WebSocket Gateway

Comprehensive tests for:
- WebSocket connection handling
- JSON-RPC protocol compliance
- Authentication and authorization
- Presence tracking
- Event routing and channel subscriptions
- Multi-agent messaging
"""

import asyncio
import json
import pytest
import websockets
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from service.gateway_ws import (
    WebSocketGateway, ConnectionState, AuthenticationManager,
    EventRouter, register_gateway_methods
)
from service.gateway_protocol import (
    ProtocolHandler, JsonRpcRequest, JsonRpcResponse,
    JsonRpcNotification, JsonRpcErrorCode,
    AuthenticationError, MethodNotFoundError, InvalidParamsError
)
from service.presence import (
    presence_manager, PresenceInfo, SessionInfo,
    EntityType, PresenceStatus, register_agent, register_user
)


# Fixtures

@pytest.fixture
async def gateway():
    """Create a test gateway instance"""
    gw = WebSocketGateway(
        host="127.0.0.1",
        port=18802,  # Different port for testing
        heartbeat_interval=5.0,
        heartbeat_timeout=10.0,
    )
    register_gateway_methods(gw)
    yield gw
    await gw.stop()


@pytest.fixture
def auth_manager():
    """Create an auth manager for testing"""
    return AuthenticationManager(token_secret="test_secret")


@pytest.fixture
def event_router():
    """Create an event router for testing"""
    return EventRouter()


@pytest.fixture
def protocol_handler():
    """Create a protocol handler for testing"""
    return ProtocolHandler()


@pytest.fixture(autouse=True)
async def reset_presence_manager():
    """Reset presence manager state before each test"""
    presence_manager._presence.clear()
    presence_manager._sessions.clear()
    presence_manager._entity_sessions.clear()
    yield
    presence_manager._presence.clear()
    presence_manager._sessions.clear()
    presence_manager._entity_sessions.clear()


# Authentication Manager Tests

class TestAuthenticationManager:
    """Tests for AuthenticationManager"""
    
    def test_generate_token(self, auth_manager):
        """Test token generation"""
        token = auth_manager.generate_token(
            entity_id="agent_001",
            entity_type="agent",
            permissions=["read", "write"],
            expires_in_hours=1
        )
        
        assert token.startswith("cell0_")
        assert token in auth_manager._tokens
        
        token_info = auth_manager._tokens[token]
        assert token_info["entity_id"] == "agent_001"
        assert token_info["entity_type"] == "agent"
        assert "read" in token_info["permissions"]
    
    def test_validate_valid_token(self, auth_manager):
        """Test validating a valid token"""
        token = auth_manager.generate_token(
            entity_id="agent_001",
            entity_type="agent",
            expires_in_hours=1
        )
        
        token_info = auth_manager.validate_token(token)
        assert token_info is not None
        assert token_info["entity_id"] == "agent_001"
    
    def test_validate_invalid_token(self, auth_manager):
        """Test validating an invalid token"""
        result = auth_manager.validate_token("invalid_token")
        assert result is None
    
    def test_validate_expired_token(self, auth_manager):
        """Test validating an expired token"""
        token = auth_manager.generate_token(
            entity_id="agent_001",
            entity_type="agent",
            expires_in_hours=-1  # Already expired
        )
        
        result = auth_manager.validate_token(token)
        assert result is None
    
    def test_revoke_token(self, auth_manager):
        """Test token revocation"""
        token = auth_manager.generate_token(
            entity_id="agent_001",
            entity_type="agent"
        )
        
        assert auth_manager.validate_token(token) is not None
        
        auth_manager.revoke_token(token)
        assert auth_manager.validate_token(token) is None
    
    def test_cleanup_expired_tokens(self, auth_manager):
        """Test cleanup of expired tokens"""
        # Create expired token
        expired_token = auth_manager.generate_token(
            entity_id="agent_001",
            entity_type="agent",
            expires_in_hours=-1
        )
        
        # Create valid token
        valid_token = auth_manager.generate_token(
            entity_id="agent_002",
            entity_type="agent",
            expires_in_hours=1
        )
        
        auth_manager.cleanup_expired_tokens()
        
        assert expired_token not in auth_manager._tokens
        assert valid_token in auth_manager._tokens


# Event Router Tests

class TestEventRouter:
    """Tests for EventRouter"""
    
    def test_subscribe_to_channel(self, event_router):
        """Test channel subscription"""
        event_router.subscribe_to_channel("conn_001", "general")
        
        subscribers = event_router.get_channel_subscribers("general")
        assert "conn_001" in subscribers
    
    def test_unsubscribe_from_channel(self, event_router):
        """Test channel unsubscription"""
        event_router.subscribe_to_channel("conn_001", "general")
        event_router.unsubscribe_from_channel("conn_001", "general")
        
        subscribers = event_router.get_channel_subscribers("general")
        assert "conn_001" not in subscribers
    
    def test_multiple_subscribers(self, event_router):
        """Test multiple subscribers to a channel"""
        event_router.subscribe_to_channel("conn_001", "general")
        event_router.subscribe_to_channel("conn_002", "general")
        event_router.subscribe_to_channel("conn_003", "other")
        
        subscribers = event_router.get_channel_subscribers("general")
        assert len(subscribers) == 2
        assert "conn_001" in subscribers
        assert "conn_002" in subscribers
    
    def test_register_agent_route(self, event_router):
        """Test agent route registration"""
        event_router.register_agent_route("agent_001", "conn_001")
        
        route = event_router.get_agent_route("agent_001")
        assert route == "conn_001"
    
    def test_unregister_agent_route(self, event_router):
        """Test agent route unregistration"""
        event_router.register_agent_route("agent_001", "conn_001")
        event_router.unregister_agent_route("agent_001")
        
        route = event_router.get_agent_route("agent_001")
        assert route is None
    
    def test_event_filter(self, event_router):
        """Test event filtering"""
        # No filter set - should receive all events
        assert event_router.should_receive_event("conn_001", "test", {}) is True
        
        # Set filter that blocks all events
        event_router.set_event_filter("conn_001", lambda et, ed: False)
        assert event_router.should_receive_event("conn_001", "test", {}) is False
        
        # Set filter that allows specific events
        event_router.set_event_filter(
            "conn_002",
            lambda et, ed: et == "allowed"
        )
        assert event_router.should_receive_event("conn_002", "allowed", {}) is True
        assert event_router.should_receive_event("conn_002", "blocked", {}) is False


# Protocol Handler Tests

class TestProtocolHandler:
    """Tests for ProtocolHandler"""
    
    @pytest.mark.asyncio
    async def test_handle_valid_request(self, protocol_handler):
        """Test handling a valid JSON-RPC request"""
        # Register a test method
        @protocol_handler.registry.register("test.echo", require_auth=False)
        async def echo(message: str, **kwargs):
            return message
        
        message = json.dumps({
            "jsonrpc": "2.0",
            "method": "test.echo",
            "params": {"message": "hello"},
            "id": 1
        })
        
        result = await protocol_handler.handle_message(message)
        
        assert isinstance(result, JsonRpcResponse)
        assert result.id == 1
        assert result.result == "hello"
        assert result.error is None
    
    @pytest.mark.asyncio
    async def test_handle_notification(self, protocol_handler):
        """Test handling a JSON-RPC notification (no id)"""
        received = []
        
        @protocol_handler.registry.register("test.notify", require_auth=False)
        async def notify(data: str, **kwargs):
            received.append(data)
        
        message = json.dumps({
            "jsonrpc": "2.0",
            "method": "test.notify",
            "params": {"data": "test_data"}
        })
        
        result = await protocol_handler.handle_message(message)
        
        # Notifications return None immediately
        assert result is None
        
        # Wait a bit for the notification handler
        await asyncio.sleep(0.1)
        assert "test_data" in received
    
    @pytest.mark.asyncio
    async def test_handle_method_not_found(self, protocol_handler):
        """Test handling unknown method"""
        message = json.dumps({
            "jsonrpc": "2.0",
            "method": "unknown.method",
            "id": 1
        })
        
        result = await protocol_handler.handle_message(message)
        
        assert isinstance(result, JsonRpcResponse)
        assert result.error is not None
        assert result.error["code"] == JsonRpcErrorCode.METHOD_NOT_FOUND.value
    
    @pytest.mark.asyncio
    async def test_handle_parse_error(self, protocol_handler):
        """Test handling invalid JSON"""
        message = "not valid json{"
        
        result = await protocol_handler.handle_message(message)
        
        assert isinstance(result, JsonRpcResponse)
        assert result.error is not None
        assert result.error["code"] == JsonRpcErrorCode.PARSE_ERROR.value
    
    @pytest.mark.asyncio
    async def test_handle_invalid_request(self, protocol_handler):
        """Test handling invalid JSON-RPC request"""
        message = json.dumps({
            "jsonrpc": "1.0",  # Wrong version
            "method": "test",
            "id": 1
        })
        
        result = await protocol_handler.handle_message(message)
        
        assert isinstance(result, JsonRpcResponse)
        assert result.error is not None
        assert result.error["code"] == JsonRpcErrorCode.INVALID_REQUEST.value
    
    @pytest.mark.asyncio
    async def test_handle_batch_request(self, protocol_handler):
        """Test handling batch requests"""
        @protocol_handler.registry.register("test.add", require_auth=False)
        async def add(a: int, b: int, **kwargs):
            return a + b
        
        message = json.dumps([
            {"jsonrpc": "2.0", "method": "test.add", "params": {"a": 1, "b": 2}, "id": 1},
            {"jsonrpc": "2.0", "method": "test.add", "params": {"a": 3, "b": 4}, "id": 2},
        ])
        
        result = await protocol_handler.handle_message(message)
        
        assert isinstance(result, list)
        assert len(result) == 2
        assert result[0].result == 3
        assert result[1].result == 7
    
    @pytest.mark.asyncio
    async def test_handle_auth_required(self, protocol_handler):
        """Test authentication required error"""
        @protocol_handler.registry.register("test.secure", require_auth=True)
        async def secure(**kwargs):
            return "secret"
        
        message = json.dumps({
            "jsonrpc": "2.0",
            "method": "test.secure",
            "id": 1
        })
        
        result = await protocol_handler.handle_message(message)
        
        assert isinstance(result, JsonRpcResponse)
        assert result.error is not None
        assert result.error["code"] == JsonRpcErrorCode.AUTHENTICATION_ERROR.value
    
    @pytest.mark.asyncio
    async def test_handle_with_auth(self, protocol_handler):
        """Test request with authentication"""
        @protocol_handler.registry.register("test.secure", require_auth=True)
        async def secure(**kwargs):
            return "secret"
        
        # Create mock session
        mock_session = Mock()
        mock_session.authenticated = True
        mock_session.has_permission = Mock(return_value=True)
        
        message = json.dumps({
            "jsonrpc": "2.0",
            "method": "test.secure",
            "id": 1
        })
        
        context = {"session": mock_session}
        result = await protocol_handler.handle_message(message, context)
        
        assert isinstance(result, JsonRpcResponse)
        assert result.result == "secret"
        assert result.error is None


# Presence Manager Tests

class TestPresenceManager:
    """Tests for PresenceManager"""
    
    @pytest.mark.asyncio
    async def test_register_presence(self):
        """Test registering presence"""
        info = await presence_manager.register_presence(
            entity_id="agent_001",
            entity_type=EntityType.AGENT,
            status=PresenceStatus.ONLINE,
            capabilities=["read", "write"]
        )
        
        assert info.entity_id == "agent_001"
        assert info.entity_type == EntityType.AGENT
        assert info.status == PresenceStatus.ONLINE
        assert "read" in info.capabilities
        
        # Verify it was stored
        stored = presence_manager.get_presence("agent_001")
        assert stored is not None
        assert stored.entity_id == "agent_001"
    
    @pytest.mark.asyncio
    async def test_update_presence(self):
        """Test updating presence"""
        await presence_manager.register_presence(
            entity_id="agent_001",
            entity_type=EntityType.AGENT
        )
        
        updated = await presence_manager.update_presence(
            entity_id="agent_001",
            status=PresenceStatus.BUSY,
            status_message="Working on task",
            current_activity="processing"
        )
        
        assert updated.status == PresenceStatus.BUSY
        assert updated.status_message == "Working on task"
        assert updated.current_activity == "processing"
    
    @pytest.mark.asyncio
    async def test_remove_presence(self):
        """Test removing presence"""
        await presence_manager.register_presence(
            entity_id="agent_001",
            entity_type=EntityType.AGENT
        )
        
        assert presence_manager.get_presence("agent_001") is not None
        
        await presence_manager.remove_presence("agent_001")
        
        assert presence_manager.get_presence("agent_001") is None
    
    @pytest.mark.asyncio
    async def test_create_session(self):
        """Test creating a session"""
        session = await presence_manager.create_session(
            entity_id="agent_001",
            entity_type=EntityType.AGENT,
            websocket_id="conn_001"
        )
        
        assert session.entity_id == "agent_001"
        assert session.entity_type == EntityType.AGENT
        assert session.websocket_id == "conn_001"
        assert session.session_id is not None
        assert not session.authenticated
        
        # Verify it was stored
        stored = presence_manager.get_session(session.session_id)
        assert stored is not None
    
    @pytest.mark.asyncio
    async def test_authenticate_session(self):
        """Test authenticating a session"""
        session = await presence_manager.create_session(
            entity_id="agent_001",
            entity_type=EntityType.AGENT
        )
        
        authenticated = await presence_manager.authenticate_session(
            session_id=session.session_id,
            auth_token="test_token",
            permissions=["read", "write"]
        )
        
        assert authenticated.authenticated is True
        assert authenticated.has_permission("read") is True
        assert authenticated.has_permission("write") is True
        assert authenticated.has_permission("admin") is False
    
    @pytest.mark.asyncio
    async def test_get_all_presence(self):
        """Test getting all presence entries"""
        await presence_manager.register_presence(
            entity_id="agent_001",
            entity_type=EntityType.AGENT
        )
        await presence_manager.register_presence(
            entity_id="user_001",
            entity_type=EntityType.USER
        )
        
        all_presence = presence_manager.get_all_presence()
        assert len(all_presence) == 2
        
        agents_only = presence_manager.get_all_presence(entity_type=EntityType.AGENT)
        assert len(agents_only) == 1
        assert agents_only[0].entity_id == "agent_001"
    
    @pytest.mark.asyncio
    async def test_presence_subscription(self):
        """Test presence change notifications"""
        notifications = []
        
        def callback(info, change_type):
            notifications.append((info.entity_id, change_type))
        
        await presence_manager.register_presence(
            entity_id="agent_001",
            entity_type=EntityType.AGENT
        )
        
        # Subscribe to presence changes
        presence_manager.subscribe_to_presence("agent_001", callback)
        
        # Update presence
        await presence_manager.update_presence(
            entity_id="agent_001",
            status=PresenceStatus.BUSY
        )
        
        # Wait for notification
        await asyncio.sleep(0.1)
        
        assert len(notifications) > 0
        assert notifications[0][0] == "agent_001"


# WebSocket Gateway Integration Tests

@pytest.mark.asyncio
class TestWebSocketGateway:
    """Integration tests for WebSocketGateway"""
    
    async def test_gateway_start_stop(self, gateway):
        """Test starting and stopping the gateway"""
        await gateway.start()
        
        assert gateway._running is True
        assert gateway._server is not None
        assert gateway.stats["start_time"] is not None
        
        await gateway.stop()
        
        assert gateway._running is False
        assert len(gateway._connections) == 0
    
    async def test_client_connection(self, gateway):
        """Test client WebSocket connection"""
        await gateway.start()
        
        async with websockets.connect(f"ws://{gateway.host}:{gateway.port}") as ws:
            # Receive welcome message
            welcome = await asyncio.wait_for(ws.recv(), timeout=2.0)
            welcome_data = json.loads(welcome)
            
            assert welcome_data["jsonrpc"] == "2.0"
            assert welcome_data["method"] == "connection.welcome"
            assert "connection_id" in welcome_data["params"]
            assert "capabilities" in welcome_data["params"]
    
    async def test_ping_method(self, gateway):
        """Test the ping method"""
        await gateway.start()
        
        async with websockets.connect(f"ws://{gateway.host}:{gateway.port}") as ws:
            # Receive welcome
            await ws.recv()
            
            # Send ping
            await ws.send(json.dumps({
                "jsonrpc": "2.0",
                "method": "rpc.ping",
                "id": 1
            }))
            
            response = await asyncio.wait_for(ws.recv(), timeout=2.0)
            response_data = json.loads(response)
            
            assert response_data["jsonrpc"] == "2.0"
            assert response_data["id"] == 1
            assert response_data["result"] == "pong"
    
    async def test_authentication(self, gateway):
        """Test authentication flow"""
        await gateway.start()
        
        # Generate token first
        token = gateway.auth_manager.generate_token(
            entity_id="test_agent",
            entity_type="agent",
            permissions=["*"]
        )
        
        async with websockets.connect(f"ws://{gateway.host}:{gateway.port}") as ws:
            # Receive welcome
            await ws.recv()
            
            # Authenticate
            await ws.send(json.dumps({
                "jsonrpc": "2.0",
                "method": "auth.authenticate",
                "params": {
                    "token": token,
                    "entity_id": "test_agent",
                    "entity_type": "agent"
                },
                "id": 1
            }))
            
            response = await asyncio.wait_for(ws.recv(), timeout=2.0)
            response_data = json.loads(response)
            
            assert response_data["error"] is None
            assert response_data["result"]["success"] is True
            assert response_data["result"]["entity_id"] == "test_agent"
    
    async def test_unauthorized_access(self, gateway):
        """Test accessing protected method without auth"""
        await gateway.start()
        
        async with websockets.connect(f"ws://{gateway.host}:{gateway.port}") as ws:
            # Receive welcome
            await ws.recv()
            
            # Try to access protected method
            await ws.send(json.dumps({
                "jsonrpc": "2.0",
                "method": "gateway.getStats",
                "id": 1
            }))
            
            response = await asyncio.wait_for(ws.recv(), timeout=2.0)
            response_data = json.loads(response)
            
            assert response_data["error"] is not None
            assert response_data["error"]["code"] == JsonRpcErrorCode.AUTHENTICATION_ERROR.value
    
    async def test_channel_subscription(self, gateway):
        """Test channel subscribe/unsubscribe"""
        await gateway.start()
        
        token = gateway.auth_manager.generate_token(
            entity_id="test_agent",
            entity_type="agent",
            permissions=["*"]
        )
        
        async with websockets.connect(f"ws://{gateway.host}:{gateway.port}") as ws:
            await ws.recv()  # Welcome
            
            # Authenticate
            await ws.send(json.dumps({
                "jsonrpc": "2.0",
                "method": "auth.authenticate",
                "params": {"token": token, "entity_id": "test_agent", "entity_type": "agent"},
                "id": 1
            }))
            await ws.recv()
            
            # Subscribe to channel
            await ws.send(json.dumps({
                "jsonrpc": "2.0",
                "method": "channel.subscribe",
                "params": {"channel": "test_channel"},
                "id": 2
            }))
            
            response = await asyncio.wait_for(ws.recv(), timeout=2.0)
            response_data = json.loads(response)
            
            assert response_data["result"]["success"] is True
            assert response_data["result"]["channel"] == "test_channel"
    
    async def test_presence_update(self, gateway):
        """Test presence update after authentication"""
        await gateway.start()
        
        token = gateway.auth_manager.generate_token(
            entity_id="test_agent",
            entity_type="agent",
            permissions=["*"]
        )
        
        async with websockets.connect(f"ws://{gateway.host}:{gateway.port}") as ws:
            await ws.recv()  # Welcome
            
            # Authenticate
            await ws.send(json.dumps({
                "jsonrpc": "2.0",
                "method": "auth.authenticate",
                "params": {"token": token, "entity_id": "test_agent", "entity_type": "agent"},
                "id": 1
            }))
            await ws.recv()
            
            # Update presence
            await ws.send(json.dumps({
                "jsonrpc": "2.0",
                "method": "presence.update",
                "params": {
                    "status": "busy",
                    "activity": "testing"
                },
                "id": 2
            }))
            
            response = await asyncio.wait_for(ws.recv(), timeout=2.0)
            response_data = json.loads(response)
            
            assert response_data["result"]["success"] is True
            
            # Verify presence was updated
            presence = presence_manager.get_presence("test_agent")
            assert presence is not None
            assert presence.status == PresenceStatus.BUSY
            assert presence.current_activity == "testing"


# JSON-RPC Compliance Tests

class TestJsonRpcCompliance:
    """Tests for JSON-RPC 2.0 specification compliance"""
    
    def test_request_serialization(self):
        """Test request serialization"""
        request = JsonRpcRequest(
            method="test.method",
            params={"key": "value"},
            id=1
        )
        
        data = request.to_dict()
        assert data["jsonrpc"] == "2.0"
        assert data["method"] == "test.method"
        assert data["params"]["key"] == "value"
        assert data["id"] == 1
    
    def test_request_deserialization(self):
        """Test request deserialization"""
        data = {
            "jsonrpc": "2.0",
            "method": "test.method",
            "params": {"key": "value"},
            "id": "abc123"
        }
        
        request = JsonRpcRequest.from_dict(data)
        assert request.jsonrpc == "2.0"
        assert request.method == "test.method"
        assert request.params["key"] == "value"
        assert request.id == "abc123"
    
    def test_response_serialization(self):
        """Test response serialization"""
        response = JsonRpcResponse.success(id=1, result={"data": "test"})
        
        data = response.to_dict()
        assert data["jsonrpc"] == "2.0"
        assert data["result"]["data"] == "test"
        assert data["id"] == 1
    
    def test_error_response(self):
        """Test error response creation"""
        response = JsonRpcResponse.error(
            id=1,
            code=-32600,
            message="Invalid Request",
            data={"details": "test"}
        )
        
        data = response.to_dict()
        assert data["jsonrpc"] == "2.0"
        assert data["error"]["code"] == -32600
        assert data["error"]["message"] == "Invalid Request"
        assert data["error"]["data"]["details"] == "test"
        assert data["id"] == 1
    
    def test_notification_creation(self):
        """Test notification creation"""
        notification = JsonRpcNotification(
            method="test.notify",
            params={"message": "hello"}
        )
        
        data = notification.to_dict()
        assert data["jsonrpc"] == "2.0"
        assert data["method"] == "test.notify"
        assert data["params"]["message"] == "hello"
        assert "id" not in data
    
    def test_event_notification(self):
        """Test event notification creation"""
        notification = JsonRpcNotification.event(
            event_type="system.status",
            data={"status": "online"},
            source="test"
        )
        
        assert notification.method == "event"
        assert notification.params["type"] == "system.status"
        assert notification.params["data"]["status"] == "online"
        assert notification.params["source"] == "test"
        assert "timestamp" in notification.params


# Performance Tests

@pytest.mark.asyncio
class TestPerformance:
    """Performance tests for the gateway"""
    
    async def test_concurrent_connections(self, gateway):
        """Test handling multiple concurrent connections"""
        await gateway.start()
        
        connection_count = 10
        connections = []
        
        for i in range(connection_count):
            ws = await websockets.connect(f"ws://{gateway.host}:{gateway.port}")
            connections.append(ws)
        
        # Verify all connections
        assert len(gateway._connections) == connection_count
        
        # Close all connections
        for ws in connections:
            await ws.close()
        
        # Wait for cleanup
        await asyncio.sleep(0.5)
        assert len(gateway._connections) == 0
    
    async def test_message_throughput(self, gateway):
        """Test message throughput"""
        await gateway.start()
        
        message_count = 100
        responses = []
        
        async with websockets.connect(f"ws://{gateway.host}:{gateway.port}") as ws:
            await ws.recv()  # Welcome
            
            # Send many ping requests
            for i in range(message_count):
                await ws.send(json.dumps({
                    "jsonrpc": "2.0",
                    "method": "rpc.ping",
                    "id": i
                }))
            
            # Collect responses
            for _ in range(message_count):
                response = await asyncio.wait_for(ws.recv(), timeout=5.0)
                responses.append(json.loads(response))
        
        assert len(responses) == message_count
        assert all(r["result"] == "pong" for r in responses)


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
