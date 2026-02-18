"""
Voice WebSocket Gateway for Cell 0 OS
Handles real-time voice streaming over WebSocket on port 18803
"""

import asyncio
import json
import logging
import struct
import wave
from dataclasses import asdict, dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Optional, Dict, Set
import io

import websockets
from websockets.server import WebSocketServerProtocol

from ..voice.tts import TTSManager, TTSConfig, TTSProvider
from ..voice.stt import STTManager, STTConfig, STTProvider
from ..voice.wake_word import WakeWordManager, WakeWordConfig, WakeWordEvent
from ..voice.voice_session import VoiceSession, VoiceSessionConfig, SessionState

logger = logging.getLogger(__name__)


class MessageType(Enum):
    """WebSocket message types"""
    # Client -> Server
    AUDIO_CHUNK = "audio_chunk"  # Binary audio data
    CONFIGURE = "configure"  # Configure session
    START_LISTENING = "start_listening"
    STOP_LISTENING = "stop_listening"
    PING = "ping"
    
    # Server -> Client
    TRANSCRIPTION = "transcription"
    WAKE_WORD = "wake_word"
    STATE_CHANGE = "state_change"
    ERROR = "error"
    PONG = "pong"
    READY = "ready"
    AUDIO_RESPONSE = "audio_response"  # Binary audio data


@dataclass
class GatewayConfig:
    """Voice gateway configuration"""
    host: str = "0.0.0.0"
    port: int = 18803
    # WebSocket settings
    ping_interval: float = 20.0
    ping_timeout: float = 10.0
    max_size: int = 10 * 1024 * 1024  # 10MB
    # Audio settings
    sample_rate: int = 16000
    channels: int = 1
    sample_width: int = 2  # 16-bit
    chunk_duration_ms: int = 20
    # Security
    require_auth: bool = False
    allowed_origins: Optional[list] = None


@dataclass
class ClientSession:
    """Client connection session"""
    websocket: WebSocketServerProtocol
    session_id: str
    voice_session: VoiceSession
    connected_at: datetime
    last_activity: datetime
    is_listening: bool = False
    audio_buffer: bytes = b""
    
    def to_dict(self) -> dict:
        return {
            "session_id": self.session_id,
            "connected_at": self.connected_at.isoformat(),
            "last_activity": self.last_activity.isoformat(),
            "is_listening": self.is_listening,
            "state": self.voice_session.state.name
        }


class VoiceGateway:
    """WebSocket gateway for voice interactions"""
    
    def __init__(self, config: Optional[GatewayConfig] = None):
        self.config = config or GatewayConfig()
        self.clients: Dict[str, ClientSession] = {}
        self.server: Optional[websockets.WebSocketServer] = None
        self._shutdown_event = asyncio.Event()
        
    async def start(self):
        """Start the WebSocket server"""
        logger.info(f"Starting Voice Gateway on {self.config.host}:{self.config.port}")
        
        self.server = await websockets.serve(
            self._handle_client,
            self.config.host,
            self.config.port,
            ping_interval=self.config.ping_interval,
            ping_timeout=self.config.ping_timeout,
            max_size=self.config.max_size,
            process_request=self._process_request if self.config.allowed_origins else None
        )
        
        logger.info(f"Voice Gateway listening on ws://{self.config.host}:{self.config.port}")
    
    async def stop(self):
        """Stop the WebSocket server"""
        logger.info("Stopping Voice Gateway...")
        
        self._shutdown_event.set()
        
        # Close all client connections
        close_tasks = []
        for client in list(self.clients.values()):
            close_tasks.append(self._disconnect_client(client, "Server shutting down"))
        
        if close_tasks:
            await asyncio.gather(*close_tasks, return_exceptions=True)
        
        if self.server:
            self.server.close()
            await self.server.wait_closed()
        
        logger.info("Voice Gateway stopped")
    
    async def _process_request(self, path, request_headers):
        """Process HTTP request for CORS"""
        origin = request_headers.get("Origin", "")
        
        if self.config.allowed_origins and origin not in self.config.allowed_origins:
            return (403, [], b"Forbidden")
        
        return None  # Continue with normal WebSocket handshake
    
    async def _handle_client(self, websocket: WebSocketServerProtocol, path: str):
        """Handle new client connection"""
        session_id = f"client_{id(websocket)}"
        
        logger.info(f"New client connection: {session_id} from {websocket.remote_address}")
        
        # Create voice session
        voice_config = VoiceSessionConfig(
            sample_rate=self.config.sample_rate,
            on_wake_word=lambda e: self._on_wake_word(session_id, e),
            on_command=lambda r: self._on_command(session_id, r),
            on_response=lambda t: self._on_response(session_id, t),
            on_state_change=lambda old, new: self._on_state_change(session_id, old, new),
            on_error=lambda e: self._on_error(session_id, e)
        )
        
        voice_session = VoiceSession(voice_config)
        await voice_session.start()
        
        # Create client session
        client = ClientSession(
            websocket=websocket,
            session_id=session_id,
            voice_session=voice_session,
            connected_at=datetime.now(),
            last_activity=datetime.now()
        )
        
        self.clients[session_id] = client
        
        try:
            # Send ready message
            await self._send_message(client, MessageType.READY, {
                "session_id": session_id,
                "config": {
                    "sample_rate": self.config.sample_rate,
                    "channels": self.config.channels,
                    "sample_width": self.config.sample_width
                }
            })
            
            # Handle messages
            async for message in websocket:
                if self._shutdown_event.is_set():
                    break
                
                client.last_activity = datetime.now()
                
                if isinstance(message, bytes):
                    await self._handle_binary_message(client, message)
                else:
                    await self._handle_text_message(client, message)
        
        except websockets.exceptions.ConnectionClosed:
            logger.info(f"Client disconnected: {session_id}")
        except Exception as e:
            logger.error(f"Error handling client {session_id}: {e}")
        finally:
            await self._disconnect_client(client)
    
    async def _handle_text_message(self, client: ClientSession, message: str):
        """Handle text WebSocket message"""
        try:
            data = json.loads(message)
            msg_type = data.get("type")
            payload = data.get("payload", {})
            
            if msg_type == MessageType.CONFIGURE.value:
                await self._handle_configure(client, payload)
            elif msg_type == MessageType.START_LISTENING.value:
                await self._handle_start_listening(client)
            elif msg_type == MessageType.STOP_LISTENING.value:
                await self._handle_stop_listening(client)
            elif msg_type == MessageType.PING.value:
                await self._send_message(client, MessageType.PONG, {"timestamp": payload.get("timestamp")})
            else:
                logger.warning(f"Unknown message type: {msg_type}")
        
        except json.JSONDecodeError:
            logger.error("Invalid JSON received")
            await self._send_error(client, "Invalid JSON")
        except Exception as e:
            logger.error(f"Error handling text message: {e}")
            await self._send_error(client, str(e))
    
    async def _handle_binary_message(self, client: ClientSession, data: bytes):
        """Handle binary audio data"""
        if not client.is_listening:
            return
        
        # Add to buffer and process
        client.audio_buffer += data
        
        # Process in chunks (simulate streaming)
        chunk_size = int(self.config.sample_rate * self.config.chunk_duration_ms / 1000) * self.config.sample_width
        
        while len(client.audio_buffer) >= chunk_size:
            chunk = client.audio_buffer[:chunk_size]
            client.audio_buffer = client.audio_buffer[chunk_size:]
            
            # Feed to voice session
            # Create async iterator for single chunk
            async def chunk_iter():
                yield chunk
            
            await client.voice_session.process_audio_stream(chunk_iter())
    
    async def _handle_configure(self, client: ClientSession, config: dict):
        """Handle configuration message"""
        logger.info(f"Configuring session {client.session_id}: {config}")
        
        # Update TTS config
        if "tts" in config:
            tts_config = config["tts"]
            if "provider" in tts_config:
                provider = TTSProvider(tts_config["provider"])
                client.voice_session.tts.switch_provider(provider)
            if "voice" in tts_config:
                client.voice_session.tts.config.voice_id = tts_config["voice"]
        
        # Update STT config
        if "stt" in config:
            stt_config = config["stt"]
            if "provider" in stt_config:
                provider = STTProvider(stt_config["provider"])
                client.voice_session.stt.switch_provider(provider)
            if "language" in stt_config:
                client.voice_session.stt.config.language = stt_config["language"]
        
        # Update wake word config
        if "wake_word" in config:
            ww_config = config["wake_word"]
            if "keyword" in ww_config:
                client.voice_session.wake_word.config.keyword = ww_config["keyword"]
        
        await self._send_message(client, MessageType.READY, {"configured": True})
    
    async def _handle_start_listening(self, client: ClientSession):
        """Start listening for audio"""
        client.is_listening = True
        client.voice_session.state = SessionState.LISTENING_WAKE
        logger.info(f"Started listening for {client.session_id}")
    
    async def _handle_stop_listening(self, client: ClientSession):
        """Stop listening for audio"""
        client.is_listening = False
        client.audio_buffer = b""
        logger.info(f"Stopped listening for {client.session_id}")
    
    async def _disconnect_client(self, client: ClientSession, reason: str = "Disconnected"):
        """Disconnect a client"""
        if client.session_id in self.clients:
            del self.clients[client.session_id]
        
        await client.voice_session.stop()
        
        try:
            await client.websocket.close()
        except:
            pass
        
        logger.info(f"Client {client.session_id} disconnected: {reason}")
    
    async def _send_message(self, client: ClientSession, msg_type: MessageType, payload: dict):
        """Send message to client"""
        try:
            message = {
                "type": msg_type.value,
                "timestamp": datetime.now().isoformat(),
                "payload": payload
            }
            await client.websocket.send(json.dumps(message))
        except websockets.exceptions.ConnectionClosed:
            logger.warning(f"Cannot send to closed connection: {client.session_id}")
        except Exception as e:
            logger.error(f"Error sending message: {e}")
    
    async def _send_binary(self, client: ClientSession, data: bytes):
        """Send binary data to client"""
        try:
            await client.websocket.send(data)
        except websockets.exceptions.ConnectionClosed:
            logger.warning(f"Cannot send to closed connection: {client.session_id}")
        except Exception as e:
            logger.error(f"Error sending binary: {e}")
    
    async def _send_error(self, client: ClientSession, error: str):
        """Send error message"""
        await self._send_message(client, MessageType.ERROR, {"message": error})
    
    # Callback handlers
    def _on_wake_word(self, session_id: str, event: WakeWordEvent):
        """Handle wake word detection"""
        if session_id not in self.clients:
            return
        
        client = self.clients[session_id]
        asyncio.create_task(self._send_message(client, MessageType.WAKE_WORD, {
            "keyword": event.keyword,
            "confidence": event.confidence,
            "timestamp": event.timestamp
        }))
    
    def _on_command(self, session_id: str, result):
        """Handle command transcription"""
        if session_id not in self.clients:
            return
        
        client = self.clients[session_id]
        asyncio.create_task(self._send_message(client, MessageType.TRANSCRIPTION, {
            "text": result.text,
            "language": result.language,
            "confidence": result.confidence,
            "is_final": True
        }))
    
    def _on_response(self, session_id: str, text: str):
        """Handle TTS response"""
        if session_id not in self.clients:
            return
        
        client = self.clients[session_id]
        # Response text is sent via transcription message for simplicity
        # Could also stream audio back
    
    def _on_state_change(self, session_id: str, old_state: SessionState, new_state: SessionState):
        """Handle session state change"""
        if session_id not in self.clients:
            return
        
        client = self.clients[session_id]
        asyncio.create_task(self._send_message(client, MessageType.STATE_CHANGE, {
            "old_state": old_state.name,
            "new_state": new_state.name
        }))
    
    def _on_error(self, session_id: str, error: Exception):
        """Handle session error"""
        if session_id not in self.clients:
            return
        
        client = self.clients[session_id]
        asyncio.create_task(self._send_error(client, str(error)))
    
    # Public API
    def get_client_info(self) -> list[dict]:
        """Get information about connected clients"""
        return [client.to_dict() for client in self.clients.values()]
    
    async def broadcast(self, message: dict, exclude: Optional[Set[str]] = None):
        """Broadcast message to all clients"""
        exclude = exclude or set()
        
        tasks = []
        for session_id, client in self.clients.items():
            if session_id not in exclude:
                tasks.append(self._send_message(client, MessageType.READY, message))
        
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
    
    async def send_tts(self, session_id: str, text: str):
        """Send TTS to specific client"""
        if session_id not in self.clients:
            raise ValueError(f"Client {session_id} not found")
        
        client = self.clients[session_id]
        await client.voice_session.speak(text)


# Standalone server runner
async def run_server(config: Optional[GatewayConfig] = None):
    """Run voice gateway server"""
    gateway = VoiceGateway(config)
    
    await gateway.start()
    
    # Keep running until interrupted
    try:
        await asyncio.Future()  # Run forever
    except asyncio.CancelledError:
        pass
    finally:
        await gateway.stop()


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Cell 0 Voice Gateway")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind to")
    parser.add_argument("--port", type=int, default=18803, help="Port to bind to")
    parser.add_argument("--auth", action="store_true", help="Require authentication")
    
    args = parser.parse_args()
    
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    config = GatewayConfig(
        host=args.host,
        port=args.port,
        require_auth=args.auth
    )
    
    try:
        asyncio.run(run_server(config))
    except KeyboardInterrupt:
        logger.info("Server stopped by user")


if __name__ == "__main__":
    main()
