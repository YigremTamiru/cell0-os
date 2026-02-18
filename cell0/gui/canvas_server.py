"""
Canvas WebSocket Server for Cell 0 OS
Provides real-time UI rendering and interaction via A2UI protocol
"""
import asyncio
import websockets
import json
import logging
import base64
import io
from typing import Dict, Set, Optional, List, Any, Callable
from dataclasses import dataclass, field
from datetime import datetime
from websockets.server import WebSocketServerProtocol
from websockets.exceptions import ConnectionClosed, InvalidMessage
from pathlib import Path

from gui.canvas_components import (
    Component, ComponentType, CanvasState, A2UIMessage,
    container, text, button, input_field, chart
)

logger = logging.getLogger("cell0.canvas")


@dataclass
class CanvasConnection:
    """Represents a connected canvas client"""
    websocket: WebSocketServerProtocol
    client_id: str
    canvas_id: str
    connected_at: datetime = field(default_factory=datetime.utcnow)
    last_ping: datetime = field(default_factory=datetime.utcnow)
    is_alive: bool = True
    user_agent: Optional[str] = None
    viewport: Dict[str, int] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "clientId": self.client_id,
            "canvasId": self.canvas_id,
            "connectedAt": self.connected_at.isoformat(),
            "lastPing": self.last_ping.isoformat(),
            "isAlive": self.is_alive,
            "userAgent": self.user_agent,
            "viewport": self.viewport
        }


class CanvasServer:
    """
    WebSocket server for Canvas/A2UI system
    Features:
    - Real-time component rendering
    - Bidirectional event handling
    - Multiple canvas sessions
    - Screenshot capability
    - Mobile-responsive coordination
    """
    
    def __init__(self, host: str = "0.0.0.0", port: int = 18802,
                 heartbeat_interval: float = 30.0,
                 heartbeat_timeout: float = 60.0):
        self.host = host
        self.port = port
        self.heartbeat_interval = heartbeat_interval
        self.heartbeat_timeout = heartbeat_timeout
        
        # Connections and sessions
        self.clients: Dict[str, CanvasConnection] = {}
        self.sessions: Dict[str, CanvasState] = {}
        self.canvas_to_clients: Dict[str, Set[str]] = {}
        
        # Server state
        self.server = None
        self._running = False
        self._heartbeat_task: Optional[asyncio.Task] = None
        
        # Event handlers
        self._event_handlers: Dict[str, Callable] = {}
        self._global_handlers: Dict[str, Callable] = {}
        
        # Statistics
        self.stats = {
            "totalConnections": 0,
            "messagesSent": 0,
            "messagesReceived": 0,
            "eventsHandled": 0,
            "screenshotsTaken": 0,
            "startTime": None
        }
        
        logger.info(f"CanvasServer initialized on {host}:{port}")
    
    async def start(self):
        """Start the Canvas WebSocket server"""
        self._running = True
        self.stats["startTime"] = datetime.utcnow().isoformat()
        
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
        
        logger.info(f"Canvas server started on ws://{self.host}:{self.port}")
        logger.info(f"Canvas UI available at http://{self.host}:{self.port}/canvas")
    
    async def stop(self):
        """Stop the Canvas server"""
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
        
        # Close server
        if self.server:
            self.server.close()
            await self.server.wait_closed()
        
        logger.info("Canvas server stopped")
    
    async def _handle_client(self, websocket: WebSocketServerProtocol, path: str):
        """Handle a new WebSocket connection"""
        client_id = f"canvas_client_{id(websocket)}_{datetime.utcnow().timestamp()}"
        
        try:
            # Extract canvas ID from path (e.g., /canvas/{canvas_id})
            canvas_id = self._extract_canvas_id(path)
            
            # Create client connection
            client = CanvasConnection(
                websocket=websocket,
                client_id=client_id,
                canvas_id=canvas_id
            )
            self.clients[client_id] = client
            
            # Track canvas-to-client mapping
            if canvas_id not in self.canvas_to_clients:
                self.canvas_to_clients[canvas_id] = set()
            self.canvas_to_clients[canvas_id].add(client_id)
            
            # Create or get canvas session
            if canvas_id not in self.sessions:
                self.sessions[canvas_id] = CanvasState(canvas_id)
            
            self.stats["totalConnections"] += 1
            logger.info(f"Client connected: {client_id} to canvas: {canvas_id}")
            
            # Send welcome message
            await self._send_message(client, {
                "type": "connection_established",
                "clientId": client_id,
                "canvasId": canvas_id,
                "timestamp": datetime.utcnow().isoformat(),
                "serverVersion": "cell0-canvas-1.0.0"
            })
            
            # Send current canvas state if available
            session = self.sessions[canvas_id]
            if session.root:
                await self._send_message(client, A2UIMessage.render(session.root))
            
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
    
    def _extract_canvas_id(self, path: str) -> str:
        """Extract canvas ID from WebSocket path"""
        parts = path.strip("/").split("/")
        if len(parts) >= 2 and parts[0] == "canvas":
            return parts[1]
        return "default"
    
    async def _handle_message(self, client: CanvasConnection, message: str):
        """Handle incoming message from client"""
        self.stats["messagesReceived"] += 1
        
        try:
            data = json.loads(message)
            msg_type = data.get("type", "unknown")
            
            if msg_type == "ping":
                await self._handle_ping(client, data)
            elif msg_type == "pong":
                await self._handle_pong(client, data)
            elif msg_type == "event":
                await self._handle_event(client, data)
            elif msg_type == "viewport":
                await self._handle_viewport(client, data)
            elif msg_type == "screenshot":
                await self._handle_screenshot_request(client, data)
            elif msg_type == "get_state":
                await self._handle_get_state(client)
            elif msg_type == "user_agent":
                await self._handle_user_agent(client, data)
            else:
                await self._send_message(client, A2UIMessage.error(
                    f"Unknown message type: {msg_type}",
                    "UNKNOWN_MESSAGE_TYPE"
                ))
                
        except json.JSONDecodeError:
            await self._send_message(client, A2UIMessage.error(
                "Invalid JSON",
                "INVALID_JSON"
            ))
        except Exception as e:
            logger.error(f"Error handling message: {e}")
            await self._send_message(client, A2UIMessage.error(
                str(e),
                "INTERNAL_ERROR"
            ))
    
    async def _handle_ping(self, client: CanvasConnection, data: dict):
        """Handle ping message"""
        client.last_ping = datetime.utcnow()
        await self._send_message(client, A2UIMessage.pong())
    
    async def _handle_pong(self, client: CanvasConnection, data: dict):
        """Handle pong message"""
        client.last_ping = datetime.utcnow()
    
    async def _handle_event(self, client: CanvasConnection, data: dict):
        """Handle event from UI"""
        payload = data.get("payload", {})
        handler_id = payload.get("handlerId")
        event_data = payload.get("data", {})
        
        # Add metadata to event
        event_data["_clientId"] = client.client_id
        event_data["_canvasId"] = client.canvas_id
        event_data["_timestamp"] = datetime.utcnow().isoformat()
        
        # Get canvas session
        session = self.sessions.get(client.canvas_id)
        
        # Call session handler if exists
        if session and handler_id:
            result = session.handle_event(handler_id, event_data)
            if result:
                await self._send_message(client, A2UIMessage.state_update({
                    "handlerId": handler_id,
                    "result": result
                }))
        
        # Call global handler if exists
        if handler_id and handler_id in self._global_handlers:
            try:
                handler = self._global_handlers[handler_id]
                if asyncio.iscoroutinefunction(handler):
                    result = await handler(event_data)
                else:
                    result = handler(event_data)
                
                if result:
                    await self._send_message(client, A2UIMessage.state_update({
                        "handlerId": handler_id,
                        "result": result
                    }))
            except Exception as e:
                logger.error(f"Error in event handler {handler_id}: {e}")
        
        self.stats["eventsHandled"] += 1
        logger.debug(f"Event handled: {handler_id} from {client.client_id}")
    
    async def _handle_viewport(self, client: CanvasConnection, data: dict):
        """Handle viewport update from client"""
        payload = data.get("payload", {})
        client.viewport = {
            "width": payload.get("width", 0),
            "height": payload.get("height", 0),
            "devicePixelRatio": payload.get("devicePixelRatio", 1)
        }
        logger.debug(f"Viewport updated for {client.client_id}: {client.viewport}")
    
    async def _handle_screenshot_request(self, client: CanvasConnection, data: dict):
        """Handle screenshot request"""
        payload = data.get("payload", {})
        format_type = payload.get("format", "png")
        quality = payload.get("quality", 0.9)
        
        # Request screenshot from client (client will capture and send back)
        await self._send_message(client, {
            "type": "capture_screenshot",
            "payload": {"format": format_type, "quality": quality}
        })
    
    async def _handle_screenshot_response(self, client: CanvasConnection, data: dict):
        """Handle screenshot data from client"""
        payload = data.get("payload", {})
        image_data = payload.get("data")
        format_type = payload.get("format", "png")
        
        if image_data:
            self.stats["screenshotsTaken"] += 1
            # Store or forward screenshot
            logger.info(f"Screenshot received from {client.client_id}")
    
    async def _handle_get_state(self, client: CanvasConnection):
        """Handle state request"""
        session = self.sessions.get(client.canvas_id)
        if session:
            await self._send_message(client, {
                "type": "canvas_state",
                "payload": session.to_dict()
            })
        else:
            await self._send_message(client, A2UIMessage.error(
                "Canvas session not found",
                "SESSION_NOT_FOUND"
            ))
    
    async def _handle_user_agent(self, client: CanvasConnection, data: dict):
        """Handle user agent info"""
        payload = data.get("payload", {})
        client.user_agent = payload.get("userAgent")
        logger.debug(f"User agent for {client.client_id}: {client.user_agent}")
    
    async def _send_message(self, client: CanvasConnection, message: dict):
        """Send message to a client"""
        try:
            if client.is_alive and client.websocket.open:
                await client.websocket.send(json.dumps(message))
                self.stats["messagesSent"] += 1
        except ConnectionClosed:
            client.is_alive = False
        except Exception as e:
            logger.error(f"Error sending message to {client.client_id}: {e}")
            client.is_alive = False
    
    async def _disconnect_client(self, client: CanvasConnection, reason: str):
        """Disconnect a client"""
        client.is_alive = False
        
        # Remove from clients dict
        if client.client_id in self.clients:
            del self.clients[client.client_id]
        
        # Remove from canvas mapping
        if client.canvas_id in self.canvas_to_clients:
            self.canvas_to_clients[client.canvas_id].discard(client.client_id)
            if not self.canvas_to_clients[client.canvas_id]:
                del self.canvas_to_clients[client.canvas_id]
        
        try:
            await client.websocket.close()
        except:
            pass
        
        logger.info(f"Client disconnected: {client.client_id} ({reason})")
    
    async def _heartbeat_loop(self):
        """Periodic heartbeat to check client health"""
        while self._running:
            try:
                await asyncio.sleep(self.heartbeat_interval)
                
                now = datetime.utcnow()
                dead_clients = []
                
                for client in list(self.clients.values()):
                    time_since_ping = (now - client.last_ping).total_seconds()
                    
                    if time_since_ping > self.heartbeat_timeout:
                        logger.warning(f"Client {client.client_id} timed out")
                        dead_clients.append(client)
                    else:
                        await self._send_message(client, A2UIMessage.ping())
                
                for client in dead_clients:
                    await self._disconnect_client(client, "timeout")
                    
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in heartbeat loop: {e}")
    
    # =====================================================================
    # Public API for Agents
    # =====================================================================
    
    def create_canvas(self, canvas_id: str, root_component: Component = None) -> CanvasState:
        """Create a new canvas session"""
        session = CanvasState(canvas_id)
        if root_component:
            session.set_root(root_component)
        self.sessions[canvas_id] = session
        logger.info(f"Canvas created: {canvas_id}")
        return session
    
    def get_canvas(self, canvas_id: str) -> Optional[CanvasState]:
        """Get a canvas session"""
        return self.sessions.get(canvas_id)
    
    def delete_canvas(self, canvas_id: str) -> bool:
        """Delete a canvas session"""
        if canvas_id in self.sessions:
            del self.sessions[canvas_id]
            # Disconnect all clients for this canvas
            if canvas_id in self.canvas_to_clients:
                for client_id in list(self.canvas_to_clients[canvas_id]):
                    if client_id in self.clients:
                        asyncio.create_task(
                            self._disconnect_client(self.clients[client_id], "canvas_deleted")
                        )
            logger.info(f"Canvas deleted: {canvas_id}")
            return True
        return False
    
    async def render(self, canvas_id: str, component: Component) -> bool:
        """Render a component to a canvas"""
        session = self.sessions.get(canvas_id)
        if not session:
            logger.warning(f"Canvas not found: {canvas_id}")
            return False
        
        session.set_root(component)
        
        # Send to all connected clients
        if canvas_id in self.canvas_to_clients:
            message = A2UIMessage.render(component)
            tasks = []
            for client_id in self.canvas_to_clients[canvas_id]:
                if client_id in self.clients:
                    tasks.append(self._send_message(self.clients[client_id], message))
            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)
        
        return True
    
    async def update_component(self, canvas_id: str, component_id: str, **props) -> bool:
        """Update a specific component in a canvas"""
        session = self.sessions.get(canvas_id)
        if not session:
            return False
        
        success = session.update_component(component_id, **props)
        if success:
            # Notify all clients
            if canvas_id in self.canvas_to_clients:
                message = A2UIMessage.update(component_id, **props)
                tasks = []
                for client_id in self.canvas_to_clients[canvas_id]:
                    if client_id in self.clients:
                        tasks.append(self._send_message(self.clients[client_id], message))
                if tasks:
                    await asyncio.gather(*tasks, return_exceptions=True)
        
        return success
    
    async def broadcast_to_canvas(self, canvas_id: str, message: dict) -> bool:
        """Broadcast a message to all clients of a canvas"""
        if canvas_id not in self.canvas_to_clients:
            return False
        
        tasks = []
        for client_id in self.canvas_to_clients[canvas_id]:
            if client_id in self.clients:
                tasks.append(self._send_message(self.clients[client_id], message))
        
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        
        return True
    
    def register_handler(self, handler_id: str, callback: Callable) -> None:
        """Register a global event handler"""
        self._global_handlers[handler_id] = callback
        logger.debug(f"Handler registered: {handler_id}")
    
    def unregister_handler(self, handler_id: str) -> bool:
        """Unregister a global event handler"""
        if handler_id in self._global_handlers:
            del self._global_handlers[handler_id]
            return True
        return False
    
    def get_stats(self) -> Dict[str, Any]:
        """Get server statistics"""
        return {
            **self.stats,
            "connectedClients": len(self.clients),
            "activeCanvases": len(self.sessions),
            "clientIds": list(self.clients.keys()),
            "canvasIds": list(self.sessions.keys())
        }
    
    async def request_screenshot(self, canvas_id: str, client_id: Optional[str] = None,
                                  format: str = "png", quality: float = 0.9) -> Optional[str]:
        """Request a screenshot from a canvas client"""
        # This would need to wait for the client to respond
        # For now, just send the request
        target_clients = []
        
        if client_id and client_id in self.clients:
            target_clients.append(self.clients[client_id])
        elif canvas_id in self.canvas_to_clients:
            for cid in self.canvas_to_clients[canvas_id]:
                if cid in self.clients:
                    target_clients.append(self.clients[cid])
        
        for client in target_clients:
            await self._send_message(client, {
                "type": "capture_screenshot",
                "payload": {"format": format, "quality": quality}
            })
        
        return None


# =============================================================================
# HTTP Server for Canvas UI (serves the HTML interface)
# =============================================================================

from aiohttp import web


class CanvasHTTPServer:
    """HTTP server for serving Canvas HTML interface"""
    
    def __init__(self, host: str = "0.0.0.0", port: int = 18802,
                 template_dir: Optional[str] = None):
        self.host = host
        self.port = port
        self.app = web.Application()
        self.runner = None
        self.site = None
        
        # Template directory
        if template_dir is None:
            template_dir = Path(__file__).parent / "canvas_templates"
        self.template_dir = Path(template_dir)
        
        # Setup routes
        self._setup_routes()
    
    def _setup_routes(self):
        """Setup HTTP routes"""
        self.app.router.add_get("/", self._handle_index)
        self.app.router.add_get("/canvas/{canvas_id}", self._handle_canvas)
        self.app.router.add_get("/api/stats", self._handle_stats)
        self.app.router.add_static("/static/", self.template_dir / "static")
    
    async def _handle_index(self, request: web.Request) -> web.Response:
        """Handle index page"""
        return web.HTTPFound("/canvas/default")
    
    async def _handle_canvas(self, request: web.Request) -> web.Response:
        """Handle canvas page"""
        canvas_id = request.match_info.get("canvas_id", "default")
        
        # Read template
        template_path = self.template_dir / "canvas.html"
        if not template_path.exists():
            return web.Response(
                text="Canvas template not found",
                status=500
            )
        
        html = template_path.read_text()
        
        # Inject canvas ID
        html = html.replace("{{CANVAS_ID}}", canvas_id)
        html = html.replace("{{WS_URL}}", f"ws://{self.host}:{self.port}/canvas/{canvas_id}")
        
        return web.Response(text=html, content_type="text/html")
    
    async def _handle_stats(self, request: web.Request) -> web.Response:
        """Handle stats endpoint"""
        return web.json_response({
            "status": "ok",
            "timestamp": datetime.utcnow().isoformat()
        })
    
    async def start(self):
        """Start HTTP server"""
        self.runner = web.AppRunner(self.app)
        await self.runner.setup()
        self.site = web.TCPSite(self.runner, self.host, self.port)
        await self.site.start()
        logger.info(f"Canvas HTTP server started on http://{self.host}:{self.port}")
    
    async def stop(self):
        """Stop HTTP server"""
        if self.runner:
            await self.runner.cleanup()
        logger.info("Canvas HTTP server stopped")


# =============================================================================
# Combined Server (WebSocket + HTTP)
# =============================================================================

class CanvasService:
    """Combined Canvas service with WebSocket and HTTP servers"""
    
    def __init__(self, host: str = "0.0.0.0", ws_port: int = 18802, 
                 http_port: Optional[int] = None,
                 template_dir: Optional[str] = None):
        self.host = host
        self.ws_port = ws_port
        self.http_port = http_port or ws_port
        
        self.ws_server = CanvasServer(host, ws_port)
        self.http_server = CanvasHTTPServer(host, self.http_port, template_dir)
        
        self._running = False
    
    async def start(self):
        """Start both servers"""
        self._running = True
        
        # Start WebSocket server
        await self.ws_server.start()
        
        # Start HTTP server (if different port)
        if self.http_port != self.ws_port:
            await self.http_server.start()
        
        logger.info(f"Canvas service started - WS: {self.ws_port}, HTTP: {self.http_port}")
    
    async def stop(self):
        """Stop both servers"""
        self._running = False
        
        await self.ws_server.stop()
        
        if self.http_port != self.ws_port:
            await self.http_server.stop()
        
        logger.info("Canvas service stopped")
    
    def create_canvas(self, canvas_id: str, root_component: Component = None) -> CanvasState:
        """Create a new canvas"""
        return self.ws_server.create_canvas(canvas_id, root_component)
    
    def get_canvas(self, canvas_id: str) -> Optional[CanvasState]:
        """Get a canvas"""
        return self.ws_server.get_canvas(canvas_id)
    
    async def render(self, canvas_id: str, component: Component) -> bool:
        """Render to a canvas"""
        return await self.ws_server.render(canvas_id, component)
    
    def register_handler(self, handler_id: str, callback: Callable) -> None:
        """Register an event handler"""
        self.ws_server.register_handler(handler_id, callback)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get service statistics"""
        return self.ws_server.get_stats()


# =============================================================================
# Standalone Server Runner
# =============================================================================

async def main():
    """Run the Canvas server standalone"""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    service = CanvasService(
        host="0.0.0.0",
        ws_port=18802,
        http_port=18802
    )
    
    try:
        await service.start()
        
        # Create a demo canvas
        demo_canvas = service.create_canvas("demo")
        
        # Build a simple UI
        root = container(
            display="flex",
            flex_direction="column",
            padding="24px",
            gap="16px"
        ).add_child(
            header("Cell 0 Canvas Demo", "A2UI Protocol Test")
        ).add_child(
            card(title="Welcome").add_child(
                text("This is a live canvas connected via WebSocket.")
            )
        ).add_child(
            hstack(
                button("Click Me", handler="demo_click", variant="primary"),
                input_field("name", placeholder="Enter your name", handler="name_input"),
                gap="8px"
            )
        )
        
        await service.render("demo", root)
        
        # Register demo handlers
        def on_click(data):
            print(f"Button clicked: {data}")
            return {"message": "Button clicked!"}
        
        def on_input(data):
            print(f"Input changed: {data}")
            return {"value": data.get("value")}
        
        service.register_handler("demo_click", on_click)
        service.register_handler("name_input", on_input)
        
        logger.info("Canvas server running. Press Ctrl+C to stop.")
        
        # Keep running
        while True:
            await asyncio.sleep(1)
            
    except KeyboardInterrupt:
        logger.info("Shutting down...")
    finally:
        await service.stop()


if __name__ == "__main__":
    asyncio.run(main())
