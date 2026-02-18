"""
Example WebSocket client for cell0d
Demonstrates connecting, subscribing, and receiving events
"""
import asyncio
import websockets
import json
import signal


class Cell0dClient:
    """Example client for cell0d WebSocket server"""
    
    def __init__(self, uri="ws://localhost:8765"):
        self.uri = uri
        self.ws = None
        self._running = False
        self._reconnect = True
        self._reconnect_delay = 1.0
        self.sequence = 0
    
    async def connect(self):
        """Connect to the WebSocket server with auto-reconnect"""
        self._running = True
        
        while self._running and self._reconnect:
            try:
                print(f"Connecting to {self.uri}...")
                self.ws = await websockets.connect(self.uri)
                
                print("Connected!")
                self._reconnect_delay = 1.0  # Reset delay
                
                # Subscribe to specific events
                await self.subscribe(["system_status", "chat_message", "model_activity"])
                
                # Start ping task
                ping_task = asyncio.create_task(self._ping_loop())
                
                # Handle messages
                await self._receive_loop()
                
                ping_task.cancel()
                
            except websockets.exceptions.ConnectionClosed:
                print("Connection closed")
            except Exception as e:
                print(f"Connection error: {e}")
            
            if self._running and self._reconnect:
                print(f"Reconnecting in {self._reconnect_delay}s...")
                await asyncio.sleep(self._reconnect_delay)
                self._reconnect_delay = min(self._reconnect_delay * 1.5, 30.0)
    
    async def _receive_loop(self):
        """Receive and handle messages"""
        async for message in self.ws:
            try:
                data = json.loads(message)
                await self._handle_message(data)
            except json.JSONDecodeError:
                print(f"Invalid JSON: {message[:100]}")
    
    async def _handle_message(self, data):
        """Handle incoming messages"""
        msg_type = data.get("type")
        
        if msg_type == "connection_established":
            print(f"Server ready. Client ID: {data.get('client_id')}")
            
        elif msg_type == "pong":
            print(f"  → Pong received (seq: {data.get('sequence')})")
            
        elif msg_type == "event":
            event = data.get("event", {})
            self._display_event(event)
            
        elif msg_type == "event_history":
            events = data.get("events", [])
            print(f"\n📚 Received {len(events)} historical events")
            for event in events:
                self._display_event(event, prefix="  [HIST]")
                
        elif msg_type == "subscription_updated":
            print(f"✓ Subscribed to: {data.get('subscribed_events')}")
            
        elif msg_type == "server_stats":
            stats = data.get("stats", {})
            print(f"\n📊 Server Stats:")
            print(f"  Connected clients: {stats.get('connected_clients', 0)}")
            print(f"  Total messages sent: {stats.get('messages_sent', 0)}")
            
        elif msg_type == "error":
            print(f"❌ Server error: {data.get('error')}")
            
        else:
            print(f"? Unknown message type: {msg_type}")
    
    def _display_event(self, event, prefix=""):
        """Display an event"""
        event_type = event.get("type", "unknown")
        timestamp = event.get("timestamp", "")[11:19]  # Extract time
        source = event.get("source", "unknown")
        
        # Color codes
        colors = {
            "system_status": "\033[92m",   # Green
            "chat_message": "\033[94m",    # Blue
            "model_activity": "\033[93m",  # Yellow
            "mcic_event": "\033[91m",      # Red
            "log_stream": "\033[90m",      # Gray
            "heartbeat": "\033[96m",       # Cyan
            "RESET": "\033[0m"
        }
        color = colors.get(event_type, "")
        reset = colors["RESET"]
        
        # Format based on event type
        if event_type == "chat_message":
            msg = event.get("data", {}).get("message", "")
            sender = event.get("data", {}).get("sender", "unknown")
            print(f"{prefix}{color}[{timestamp}] 💬 {sender}: {msg}{reset}")
            
        elif event_type == "model_activity":
            action = event.get("data", {}).get("action", "")
            model = event.get("data", {}).get("model_name", "")
            print(f"{prefix}{color}[{timestamp}] 🤖 Model {model}: {action}{reset}")
            
        elif event_type == "system_status":
            status = event.get("data", {}).get("status", "")
            print(f"{prefix}{color}[{timestamp}] ⚙️  System: {status}{reset}")
            
        elif event_type == "log_stream":
            level = event.get("data", {}).get("level", "")
            msg = event.get("data", {}).get("message", "")
            print(f"{prefix}{color}[{timestamp}] 📝 [{level}] {msg[:60]}{reset}")
            
        else:
            print(f"{prefix}{color}[{timestamp}] {event_type}: {event.get('data', {})}{reset}")
    
    async def _ping_loop(self):
        """Send periodic pings"""
        while self._running:
            try:
                await asyncio.sleep(30)
                if self.ws and self.ws.open:
                    self.sequence += 1
                    await self.ws.send(json.dumps({
                        "type": "ping",
                        "sequence": self.sequence
                    }))
            except Exception as e:
                print(f"Ping error: {e}")
                break
    
    async def subscribe(self, event_types):
        """Subscribe to event types"""
        if self.ws and self.ws.open:
            await self.ws.send(json.dumps({
                "type": "subscribe",
                "event_types": event_types,
                "replace": True
            }))
    
    async def get_history(self, event_type=None, limit=50):
        """Request event history"""
        if self.ws and self.ws.open:
            msg = {
                "type": "get_history",
                "limit": limit
            }
            if event_type:
                msg["event_type"] = event_type
            await self.ws.send(json.dumps(msg))
    
    async def get_stats(self):
        """Request server stats"""
        if self.ws and self.ws.open:
            await self.ws.send(json.dumps({"type": "get_stats"}))
    
    async def disconnect(self):
        """Disconnect from server"""
        self._running = False
        self._reconnect = False
        if self.ws:
            await self.ws.close()


async def main():
    """Example usage"""
    client = Cell0dClient("ws://localhost:8765")
    
    # Handle Ctrl+C gracefully
    def signal_handler():
        print("\nDisconnecting...")
        asyncio.create_task(client.disconnect())
    
    signal.signal(signal.SIGINT, lambda s, f: signal_handler())
    
    print("Cell0d WebSocket Client Example")
    print("Commands (type in terminal):")
    print("  h - Get event history")
    print("  s - Get server stats")
    print("  c - Change subscription (all/system/chat/model/mcic/log)")
    print("  q - Quit")
    print()
    
    # Start connection in background
    connect_task = asyncio.create_task(client.connect())
    
    # Simple command interface
    while client._running:
        try:
            cmd = await asyncio.get_event_loop().run_in_executor(
                None, lambda: input("\n> ")
            )
            
            if cmd == "h":
                await client.get_history()
            elif cmd == "s":
                await client.get_stats()
            elif cmd == "c":
                sub = input("Subscribe to (all/system/chat/model/mcic/log): ")
                mapping = {
                    "all": ["all"],
                    "system": ["system_status"],
                    "chat": ["chat_message"],
                    "model": ["model_activity"],
                    "mcic": ["mcic_event"],
                    "log": ["log_stream"]
                }
                if sub in mapping:
                    await client.subscribe(mapping[sub])
            elif cmd == "q":
                await client.disconnect()
                break
                
        except EOFError:
            break
        except Exception as e:
            print(f"Error: {e}")
    
    await connect_task


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nGoodbye!")