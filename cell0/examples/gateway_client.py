"""
Example client for Cell 0 OS WebSocket Gateway

Demonstrates:
- Connecting to the gateway
- Authenticating
- Subscribing to channels
- Sending/receiving messages
- Handling events
"""

import asyncio
import json
import websockets
from typing import Optional, Dict, Any, Callable
from datetime import datetime


class Cell0GatewayClient:
    """Client for Cell 0 OS WebSocket Gateway"""
    
    def __init__(
        self,
        uri: str = "ws://localhost:18801",
        entity_id: Optional[str] = None,
        entity_type: str = "agent"
    ):
        self.uri = uri
        self.entity_id = entity_id or f"client_{datetime.utcnow().timestamp()}"
        self.entity_type = entity_type
        
        self.websocket: Optional[websockets.WebSocketClientProtocol] = None
        self.connection_id: Optional[str] = None
        self.session_id: Optional[str] = None
        self.authenticated = False
        
        # Message handling
        self._message_handlers: Dict[str, Callable] = {}
        self._pending_requests: Dict[str, asyncio.Future] = {}
        self._request_counter = 0
        
        # Event handlers
        self._event_handlers: Dict[str, list] = {}
        self._default_event_handler: Optional[Callable] = None
    
    async def connect(self):
        """Connect to the gateway"""
        self.websocket = await websockets.connect(self.uri)
        
        # Start message handler
        asyncio.create_task(self._message_loop())
        
        # Wait for welcome message
        await asyncio.sleep(0.5)
        
        print(f"Connected to {self.uri}")
    
    async def disconnect(self):
        """Disconnect from the gateway"""
        if self.websocket:
            await self.websocket.close()
            self.websocket = None
            print("Disconnected")
    
    async def authenticate(self, token: str, capabilities: Optional[list] = None):
        """Authenticate with the gateway"""
        response = await self._send_request(
            "auth.authenticate",
            {
                "token": token,
                "entity_id": self.entity_id,
                "entity_type": self.entity_type,
                "capabilities": capabilities or []
            }
        )
        
        if response.get("success"):
            self.authenticated = True
            self.session_id = response.get("session_id")
            print(f"Authenticated as {self.entity_id}")
        
        return response
    
    async def update_presence(
        self,
        status: str = "online",
        status_message: Optional[str] = None,
        activity: Optional[str] = None
    ):
        """Update presence status"""
        params = {"status": status}
        if status_message:
            params["status_message"] = status_message
        if activity:
            params["activity"] = activity
        
        return await self._send_request("presence.update", params)
    
    async def subscribe_channel(self, channel: str):
        """Subscribe to a channel"""
        return await self._send_request(
            "channel.subscribe",
            {"channel": channel}
        )
    
    async def unsubscribe_channel(self, channel: str):
        """Unsubscribe from a channel"""
        return await self._send_request(
            "channel.unsubscribe",
            {"channel": channel}
        )
    
    async def publish_to_channel(self, channel: str, message: Dict[str, Any]):
        """Publish a message to a channel"""
        return await self._send_request(
            "channel.publish",
            {"channel": channel, "message": message}
        )
    
    async def send_to_agent(self, agent_id: str, message: Dict[str, Any]):
        """Send a message to a specific agent"""
        return await self._send_request(
            "agent.send",
            {"agent_id": agent_id, "message": message}
        )
    
    async def list_agents(self):
        """List all online agents"""
        return await self._send_request("agent.list", {})
    
    async def get_server_info(self):
        """Get server information"""
        return await self._send_request("rpc.getServerInfo", {})
    
    async def ping(self):
        """Ping the server"""
        return await self._send_request("rpc.ping", {})
    
    # Event handling
    
    def on_event(self, event_type: str, handler: Callable):
        """Register an event handler"""
        if event_type not in self._event_handlers:
            self._event_handlers[event_type] = []
        self._event_handlers[event_type].append(handler)
    
    def on_any_event(self, handler: Callable):
        """Register a default event handler"""
        self._default_event_handler = handler
    
    # Internal methods
    
    def _get_request_id(self) -> str:
        """Generate a unique request ID"""
        self._request_counter += 1
        return f"req_{self._request_counter}"
    
    async def _send_request(
        self,
        method: str,
        params: Optional[Dict[str, Any]] = None
    ) -> Any:
        """Send a request and wait for response"""
        if not self.websocket:
            raise ConnectionError("Not connected")
        
        request_id = self._get_request_id()
        
        message = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params or {},
            "id": request_id
        }
        
        # Create future for response
        future = asyncio.get_event_loop().create_future()
        self._pending_requests[request_id] = future
        
        # Send message
        await self.websocket.send(json.dumps(message))
        
        # Wait for response
        try:
            response = await asyncio.wait_for(future, timeout=30.0)
            if "error" in response:
                raise Exception(f"RPC Error: {response['error']}")
            return response.get("result")
        except asyncio.TimeoutError:
            self._pending_requests.pop(request_id, None)
            raise TimeoutError(f"Request {request_id} timed out")
    
    async def _message_loop(self):
        """Handle incoming messages"""
        try:
            async for message in self.websocket:
                await self._handle_message(json.loads(message))
        except websockets.exceptions.ConnectionClosed:
            print("Connection closed")
        except Exception as e:
            print(f"Error in message loop: {e}")
    
    async def _handle_message(self, message: Dict[str, Any]):
        """Handle a received message"""
        # Check if it's a response
        if "id" in message and message["id"] in self._pending_requests:
            request_id = message["id"]
            future = self._pending_requests.pop(request_id)
            future.set_result(message)
            return
        
        # Check if it's a notification/event
        if "method" in message:
            method = message["method"]
            params = message.get("params", {})
            
            # Handle welcome message
            if method == "connection.welcome":
                self.connection_id = params.get("connection_id")
                print(f"Received welcome. Connection ID: {self.connection_id}")
                return
            
            # Handle heartbeat
            if method == "heartbeat":
                # Send heartbeat response
                await self.websocket.send(json.dumps({
                    "jsonrpc": "2.0",
                    "method": "heartbeat",
                    "params": {"timestamp": datetime.utcnow().isoformat()}
                }))
                return
            
            # Handle events
            event_type = params.get("type", method)
            
            # Call specific handlers
            if event_type in self._event_handlers:
                for handler in self._event_handlers[event_type]:
                    try:
                        if asyncio.iscoroutinefunction(handler):
                            asyncio.create_task(handler(params))
                        else:
                            handler(params)
                    except Exception as e:
                        print(f"Error in event handler: {e}")
            
            # Call default handler
            if self._default_event_handler:
                try:
                    if asyncio.iscoroutinefunction(self._default_event_handler):
                        asyncio.create_task(self._default_event_handler(event_type, params))
                    else:
                        self._default_event_handler(event_type, params)
                except Exception as e:
                    print(f"Error in default event handler: {e}")


async def main():
    """Example usage"""
    
    # Create client
    client = Cell0GatewayClient(
        uri="ws://localhost:18801",
        entity_id="example_client_001",
        entity_type="agent"
    )
    
    try:
        # Connect
        await client.connect()
        
        # Get server info
        info = await client.get_server_info()
        print(f"Server: {info['name']} v{info['version']}")
        print(f"Capabilities: {', '.join(info['capabilities'])}")
        
        # Note: For this example, you'd need a valid token
        # In production, get a token from the auth system
        print("\nNote: Authentication requires a valid token")
        print("Use 'auth.generateToken' with an authenticated session to create one")
        
        # If we had a token, we would:
        # await client.authenticate("your_token_here", capabilities=["chat"])
        # await client.update_presence("online", activity="demo")
        # await client.subscribe_channel("events")
        
        # Keep running to receive events
        print("\nPress Ctrl+C to disconnect")
        while True:
            await asyncio.sleep(1)
            
    except KeyboardInterrupt:
        print("\nDisconnecting...")
    finally:
        await client.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
