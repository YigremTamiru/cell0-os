"""
Example client for Cell 0 OS WebSocket Gateway

Demonstrates:
- Connection and authentication
- Subscribing to channels
- Sending/receiving messages
- Presence updates
- Event handling
"""

import asyncio
import json
import sys
from datetime import datetime
from typing import Optional, Dict, Any

try:
    import websockets
    from websockets.exceptions import ConnectionClosed
except ImportError:
    print("Please install websockets: pip install websockets")
    sys.exit(1)


class GatewayClient:
    """Client for Cell 0 OS WebSocket Gateway"""
    
    def __init__(
        self,
        uri: str = "ws://localhost:18801",
        auto_reconnect: bool = True,
        reconnect_delay: float = 5.0
    ):
        self.uri = uri
        self.auto_reconnect = auto_reconnect
        self.reconnect_delay = reconnect_delay
        
        self.websocket: Optional[websockets.WebSocketClientProtocol] = None
        self.connection_id: Optional[str] = None
        self.session_id: Optional[str] = None
        self.authenticated = False
        self.entity_id: Optional[str] = None
        
        self._running = False
        self._message_id = 0
        self._pending_requests: Dict[int, asyncio.Future] = {}
        self._event_handlers: Dict[str, list] = {}
    
    def _get_message_id(self) -> int:
        """Get next message ID"""
        self._message_id += 1
        return self._message_id
    
    async def connect(self):
        """Connect to the gateway"""
        print(f"Connecting to {self.uri}...")
        
        self.websocket = await websockets.connect(self.uri)
        self._running = True
        
        # Start message handler
        asyncio.create_task(self._message_loop())
        
        # Wait for welcome message
        await asyncio.sleep(0.5)
        
        print(f"Connected! Connection ID: {self.connection_id}")
    
    async def disconnect(self):
        """Disconnect from the gateway"""
        self._running = False
        self.authenticated = False
        
        if self.websocket:
            await self.websocket.close()
            self.websocket = None
        
        print("Disconnected")
    
    async def _message_loop(self):
        """Handle incoming messages"""
        while self._running and self.websocket:
            try:
                message = await self.websocket.recv()
                data = json.loads(message)
                
                await self._handle_message(data)
                
            except ConnectionClosed:
                print("Connection closed")
                if self.auto_reconnect:
                    await self._reconnect()
                else:
                    self._running = False
                break
            except json.JSONDecodeError as e:
                print(f"Invalid JSON received: {e}")
            except Exception as e:
                print(f"Error handling message: {e}")
    
    async def _handle_message(self, data: Dict[str, Any]):
        """Handle a received message"""
        # Handle responses
        if "id" in data and data["id"] is not None:
            msg_id = data["id"]
            if msg_id in self._pending_requests:
                future = self._pending_requests.pop(msg_id)
                future.set_result(data)
            return
        
        # Handle notifications
        method = data.get("method", "")
        params = data.get("params", {})
        
        if method == "connection.welcome":
            self.connection_id = params.get("connection_id")
            print(f"Welcome! Server version: {params.get('server_version')}")
            print(f"Capabilities: {', '.join(params.get('capabilities', []))}")
        
        elif method == "heartbeat":
            # Respond to heartbeat
            pass
        
        elif method == "event":
            event_type = params.get("type")
            event_data = params.get("data")
            await self._handle_event(event_type, event_data, params)
        
        elif method == "channel.message":
            channel = params.get("channel")
            message = params.get("message")
            print(f"\n[Channel: {channel}] {message}")
        
        elif method == "agent.message":
            from_agent = params.get("from")
            message = params.get("message")
            print(f"\n[Message from {from_agent}] {message}")
        
        else:
            print(f"\n[Notification: {method}] {params}")
    
    async def _handle_event(self, event_type: str, data: Dict, params: Dict):
        """Handle an event notification"""
        # Call registered handlers
        handlers = self._event_handlers.get(event_type, [])
        for handler in handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(event_type, data, params)
                else:
                    handler(event_type, data, params)
            except Exception as e:
                print(f"Error in event handler: {e}")
    
    def on_event(self, event_type: str, handler):
        """Register an event handler"""
        if event_type not in self._event_handlers:
            self._event_handlers[event_type] = []
        self._event_handlers[event_type].append(handler)
    
    async def _send_request(
        self,
        method: str,
        params: Optional[Dict] = None,
        timeout: float = 10.0
    ) -> Dict[str, Any]:
        """Send a request and wait for response"""
        if not self.websocket:
            raise ConnectionError("Not connected")
        
        msg_id = self._get_message_id()
        
        request = {
            "jsonrpc": "2.0",
            "method": method,
            "id": msg_id
        }
        if params:
            request["params"] = params
        
        # Create future for response
        future = asyncio.get_event_loop().create_future()
        self._pending_requests[msg_id] = future
        
        try:
            await self.websocket.send(json.dumps(request))
            
            # Wait for response
            response = await asyncio.wait_for(future, timeout=timeout)
            
            if "error" in response and response["error"]:
                raise Exception(f"RPC Error: {response['error']}")
            
            return response.get("result", {})
            
        except asyncio.TimeoutError:
            self._pending_requests.pop(msg_id, None)
            raise TimeoutError(f"Request timeout: {method}")
    
    async def _send_notification(self, method: str, params: Optional[Dict] = None):
        """Send a notification (no response expected)"""
        if not self.websocket:
            raise ConnectionError("Not connected")
        
        notification = {
            "jsonrpc": "2.0",
            "method": method
        }
        if params:
            notification["params"] = params
        
        await self.websocket.send(json.dumps(notification))
    
    async def _reconnect(self):
        """Attempt to reconnect"""
        print(f"Reconnecting in {self.reconnect_delay} seconds...")
        await asyncio.sleep(self.reconnect_delay)
        
        try:
            await self.connect()
            if self.entity_id:
                # Re-authenticate
                print("Re-authenticating...")
                # Note: Token would need to be stored for re-auth
        except Exception as e:
            print(f"Reconnection failed: {e}")
    
    # Public API methods
    
    async def authenticate(
        self,
        token: str,
        entity_id: str,
        entity_type: str = "agent",
        capabilities: Optional[list] = None
    ) -> Dict[str, Any]:
        """Authenticate with the gateway"""
        result = await self._send_request("auth.authenticate", {
            "token": token,
            "entity_id": entity_id,
            "entity_type": entity_type,
            "capabilities": capabilities or []
        })
        
        if result.get("success"):
            self.authenticated = True
            self.session_id = result.get("session_id")
            self.entity_id = result.get("entity_id")
            print(f"Authenticated as {self.entity_id}")
        
        return result
    
    async def generate_token(
        self,
        entity_id: str,
        entity_type: str = "agent",
        permissions: Optional[list] = None,
        expires_in_hours: int = 24
    ) -> str:
        """Generate a new authentication token"""
        result = await self._send_request("auth.generateToken", {
            "entity_id": entity_id,
            "entity_type": entity_type,
            "permissions": permissions or ["*"],
            "expires_in_hours": expires_in_hours
        })
        
        return result.get("token")
    
    async def get_session_info(self) -> Dict[str, Any]:
        """Get current session information"""
        return await self._send_request("session.getInfo")
    
    async def update_presence(
        self,
        status: str,
        status_message: Optional[str] = None,
        activity: Optional[str] = None
    ) -> Dict[str, Any]:
        """Update presence status"""
        params = {"status": status}
        if status_message:
            params["status_message"] = status_message
        if activity:
            params["activity"] = activity
        
        return await self._send_request("presence.update", params)
    
    async def get_presence(
        self,
        entity_id: Optional[str] = None,
        entity_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get presence information"""
        params = {}
        if entity_id:
            params["entity_id"] = entity_id
        if entity_type:
            params["entity_type"] = entity_type
        
        return await self._send_request("presence.get", params)
    
    async def subscribe_channel(self, channel: str) -> Dict[str, Any]:
        """Subscribe to a channel"""
        return await self._send_request("channel.subscribe", {"channel": channel})
    
    async def unsubscribe_channel(self, channel: str) -> Dict[str, Any]:
        """Unsubscribe from a channel"""
        return await self._send_request("channel.unsubscribe", {"channel": channel})
    
    async def publish_to_channel(
        self,
        channel: str,
        message: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Publish a message to a channel"""
        return await self._send_request("channel.publish", {
            "channel": channel,
            "message": message
        })
    
    async def send_to_agent(
        self,
        agent_id: str,
        message: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Send a message to a specific agent"""
        return await self._send_request("agent.send", {
            "agent_id": agent_id,
            "message": message
        })
    
    async def list_agents(self) -> list:
        """List all online agents"""
        return await self._send_request("agent.list")
    
    async def get_gateway_stats(self) -> Dict[str, Any]:
        """Get gateway statistics"""
        return await self._send_request("gateway.getStats")
    
    async def ping(self) -> str:
        """Ping the server"""
        return await self._send_request("rpc.ping")
    
    async def get_server_info(self) -> Dict[str, Any]:
        """Get server information"""
        return await self._send_request("rpc.getServerInfo")


async def demo():
    """Demonstration of gateway client usage"""
    
    print("=" * 60)
    print("Cell 0 OS Gateway Client Demo")
    print("=" * 60)
    
    # Create client
    client = GatewayClient(uri="ws://localhost:18801")
    
    try:
        # Connect
        await client.connect()
        
        # Get server info
        print("\n--- Server Info ---")
        server_info = await client.get_server_info()
        print(f"Server: {server_info.get('name')}")
        print(f"Version: {server_info.get('version')}")
        print(f"Capabilities: {', '.join(server_info.get('capabilities', []))}")
        
        # Ping
        print("\n--- Ping Test ---")
        pong = await client.ping()
        print(f"Ping response: {pong}")
        
        # Generate a token (would normally be pre-generated)
        print("\n--- Token Generation ---")
        print("Note: Token generation requires authentication")
        print("For this demo, we'll use a pre-generated token")
        
        # In a real scenario, you'd authenticate first or use a pre-generated token
        # For demo purposes, we'll skip authentication
        
        print("\n--- Press Ctrl+C to exit ---")
        
        # Keep running and handle events
        while True:
            await asyncio.sleep(1)
            
    except KeyboardInterrupt:
        print("\n\nShutting down...")
    except Exception as e:
        print(f"\nError: {e}")
    finally:
        await client.disconnect()


async def interactive_demo():
    """Interactive demo with authentication"""
    
    print("=" * 60)
    print("Cell 0 OS Gateway Interactive Demo")
    print("=" * 60)
    
    client = GatewayClient(uri="ws://localhost:18801")
    
    try:
        await client.connect()
        
        # Get server info
        server_info = await client.get_server_info()
        print(f"\nConnected to: {server_info.get('name')} v{server_info.get('version')}")
        
        # Prompt for authentication
        print("\n--- Authentication ---")
        print("Note: You need a valid token to proceed.")
        print("The server generates tokens after authentication.")
        print("For testing, you may need to generate a token via the admin API.")
        
        # For this demo, we'll just show the available commands
        print("\n--- Available Commands ---")
        print("1. ping - Test connectivity")
        print("2. info - Get server info")
        print("3. auth <token> - Authenticate")
        print("4. presence <status> - Update presence")
        print("5. subscribe <channel> - Subscribe to channel")
        print("6. publish <channel> <message> - Publish to channel")
        print("7. agents - List online agents")
        print("8. stats - Get gateway stats")
        print("9. quit - Exit")
        
        while True:
            try:
                command = await asyncio.get_event_loop().run_in_executor(
                    None, input, "\n> "
                )
                command = command.strip()
                
                if not command:
                    continue
                
                parts = command.split(maxsplit=1)
                cmd = parts[0].lower()
                args = parts[1] if len(parts) > 1 else ""
                
                if cmd == "quit" or cmd == "exit":
                    break
                
                elif cmd == "ping":
                    result = await client.ping()
                    print(f"Response: {result}")
                
                elif cmd == "info":
                    result = await client.get_server_info()
                    print(json.dumps(result, indent=2))
                
                elif cmd == "auth":
                    if not args:
                        print("Usage: auth <token>")
                        continue
                    result = await client.authenticate(
                        token=args,
                        entity_id="demo_user",
                        entity_type="user"
                    )
                    print(f"Authenticated: {result.get('success')}")
                
                elif cmd == "presence":
                    if not args:
                        print("Usage: presence <online|away|busy|dnd>")
                        continue
                    result = await client.update_presence(status=args)
                    print(f"Updated: {result.get('success')}")
                
                elif cmd == "subscribe":
                    if not args:
                        print("Usage: subscribe <channel>")
                        continue
                    result = await client.subscribe_channel(args)
                    print(f"Subscribed: {result.get('success')}")
                
                elif cmd == "publish":
                    parts = args.split(maxsplit=1)
                    if len(parts) < 2:
                        print("Usage: publish <channel> <message>")
                        continue
                    result = await client.publish_to_channel(
                        parts[0],
                        {"text": parts[1], "timestamp": datetime.now().isoformat()}
                    )
                    print(f"Published to {result.get('recipients')} recipients")
                
                elif cmd == "agents":
                    result = await client.list_agents()
                    print(f"Online agents ({len(result)}):")
                    for agent in result:
                        print(f"  - {agent.get('entity_id')}: {agent.get('status')}")
                
                elif cmd == "stats":
                    result = await client.get_gateway_stats()
                    print(json.dumps(result, indent=2))
                
                else:
                    print(f"Unknown command: {cmd}")
                    
            except Exception as e:
                print(f"Error: {e}")
                
    except KeyboardInterrupt:
        print("\n\nShutting down...")
    finally:
        await client.disconnect()


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Cell 0 OS Gateway Client")
    parser.add_argument("--interactive", "-i", action="store_true", help="Interactive mode")
    parser.add_argument("--uri", default="ws://localhost:18801", help="Gateway URI")
    
    args = parser.parse_args()
    
    if args.interactive:
        asyncio.run(interactive_demo())
    else:
        asyncio.run(demo())
