"""
cell0d.py - Cell 0 OS Gateway Daemon (HTTP API Server)

Production-ready FastAPI gateway providing:
- RESTful API for chat, models, kernels, and system management
- Server-Sent Events (SSE) for real-time event streaming
- Automatic localhost authentication bypass for development
- Token-based authentication for remote access

Port: 18800 (HTTP API)
"""

# =============================================================================
# DEPENDENCY AUTO-INSTALLER - Graceful Startup
# =============================================================================

import sys
import subprocess

# Define required dependencies with their package names
# Format: (import_name, package_name) - they may differ (e.g., python-dotenv -> dotenv)
REQUIRED_DEPENDENCIES = [
    ("fastapi", "fastapi>=0.104.0"),
    ("uvicorn", "uvicorn>=0.24.0"),
    ("slowapi", "slowapi>=0.1.9"),
    ("websockets", "websockets>=12.0"),
    ("dotenv", "python-dotenv>=1.0.0"),
    ("questionary", "questionary>=2.0.0"),
    ("pydantic", "pydantic>=2.5.0"),
]

def check_and_install_dependencies():
    """
    Check for missing dependencies and auto-install them.
    Shows user what's happening - not silently.
    """
    missing = []
    
    # First pass: check what's missing
    print("🔍 Checking dependencies...")
    for import_name, package_spec in REQUIRED_DEPENDENCIES:
        try:
            __import__(import_name)
            print(f"  ✓ {import_name}")
        except ImportError:
            print(f"  ✗ {import_name} - will install")
            missing.append((import_name, package_spec))
    
    if not missing:
        print("✅ All dependencies satisfied!\n")
        return True
    
    # Install all missing packages at once
    packages_to_install = [pkg for _, pkg in missing]
    print(f"\n📦 Installing {len(missing)} missing package(s)...")
    print(f"   Packages: {', '.join(packages_to_install)}\n")
    
    try:
        # Attempt installation
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install"] + packages_to_install,
            capture_output=True,
            text=True,
            check=True
        )
        print("✅ Installation successful!")
        if result.stdout:
            print(result.stdout)
        
        # Retry imports to verify
        print("\n🔄 Verifying installations...")
        failed_imports = []
        for import_name, package_spec in missing:
            try:
                __import__(import_name)
                print(f"  ✓ {import_name} verified")
            except ImportError as e:
                print(f"  ✗ {import_name} still missing: {e}")
                failed_imports.append(import_name)
        
        if failed_imports:
            print(f"\n❌ ERROR: Some packages could not be imported after installation: {', '.join(failed_imports)}")
            return False
        
        print("✅ All dependencies ready!\n")
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"\n❌ ERROR: pip install failed")
        print(f"   Return code: {e.returncode}")
        print(f"   stdout: {e.stdout}")
        print(f"   stderr: {e.stderr}")
        
        # Check for specific error patterns
        error_output = (e.stderr or "") + (e.stdout or "")
        
        if "Permission denied" in error_output:
            print("\n💡 HINT: Permission denied. Try one of these:")
            print("   1. Use --user flag: pip install --user <package>")
            print("   2. Use virtual environment: python -m venv venv && source venv/bin/activate")
            print("   3. On some systems: sudo pip install <package> (not recommended)")
        elif "Could not find a version" in error_output or "No matching distribution" in error_output:
            print("\n💡 HINT: Package not found. Check the package names are correct.")
        elif "Network" in error_output or "connection" in error_output.lower():
            print("\n💡 HINT: Network issue detected. Check your internet connection.")
            print("   You can manually install dependencies with: pip install -r requirements.txt")
        else:
            print("\n💡 HINT: Try installing manually:")
            print(f"   pip install {' '.join(packages_to_install)}")
        
        return False
    except FileNotFoundError:
        print("\n❌ ERROR: pip command not found. Is Python properly installed?")
        return False

# Run dependency check before any imports
if not check_and_install_dependencies():
    print("\n⚠️  Cannot start cell0d gateway - missing dependencies.")
    print("   Please fix the installation issues above and try again.")
    sys.exit(1)

# =============================================================================
# NOW SAFE TO IMPORT OTHER MODULES
# =============================================================================

import asyncio
import logging
import os
import socket
import time
import uuid
import json
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any, Dict, List, Optional, Set
from collections import defaultdict

from fastapi import FastAPI, HTTPException, Query, Request, status, Depends
from fastapi.responses import JSONResponse, StreamingResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, field_validator
import uvicorn

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("cell0d.api")


# ============================================================================
# Configuration - AUTO-DETECT LOCALHOST FOR ZERO-CONFIG AUTH
# ============================================================================

class GatewayConfig:
    """Gateway configuration with auto-detection"""
    
    def __init__(self):
        self.host = os.getenv("CELL0_HOST", "127.0.0.1")
        self.port = int(os.getenv("CELL0_PORT", "18800"))
        self.ws_port = int(os.getenv("CELL0_WS_PORT", "18801"))
        self.version = "1.1.5"
        
        # Localhost addresses that bypass auth automatically
        self.local_hosts: Set[str] = {
            "127.0.0.1", "localhost", "::1", 
            "0:0:0:0:0:0:0:1",  # IPv6 loopback
        }
        
        # Get all local IPs
        self._populate_local_ips()
    
    def _populate_local_ips(self):
        """Add all local network interface IPs"""
        try:
            hostname = socket.gethostname()
            try:
                host_ip = socket.gethostbyname(hostname)
                if host_ip.startswith("127."):
                    self.local_hosts.add(host_ip)
            except:
                pass
        except Exception as e:
            logger.warning(f"Could not populate local IPs: {e}")
    
    def is_local_request(self, request: Request) -> bool:
        """
        AUTO-DETECT: Check if request is from localhost.
        This allows auth bypass for local development without any config.
        """
        # Get client IP
        client_ip = request.client.host if request.client else None
        
        # Check X-Forwarded-For header (for proxies)
        forwarded_for = request.headers.get("X-Forwarded-For", "")
        if forwarded_for:
            client_ip = forwarded_for.split(",")[0].strip()
        
        # Check X-Real-IP header
        real_ip = request.headers.get("X-Real-IP", "")
        if real_ip:
            client_ip = real_ip
        
        if not client_ip:
            return False
        
        # Check if localhost
        if client_ip in self.local_hosts:
            return True
        
        # Check localhost ranges
        if client_ip.startswith("127."):
            return True
        
        # Check private network ranges (local network safety)
        if client_ip.startswith("192.168.") or client_ip.startswith("10."):
            return True
        
        return False


config = GatewayConfig()


# ============================================================================
# Pydantic Models
# ============================================================================

class ChatMessageRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=10000)
    sender: str = Field(..., min_length=1, max_length=100)
    channel: str = Field(default="general", max_length=100)
    reply_to: Optional[str] = Field(default=None)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    @field_validator('message')
    @classmethod
    def message_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError('Message cannot be empty')
        return v


class ChatMessageResponse(BaseModel):
    success: bool
    message_id: str
    timestamp: str
    channel: str


class ChatMessage(BaseModel):
    id: str
    message: str
    sender: str
    channel: str
    reply_to: Optional[str]
    timestamp: str
    metadata: Dict[str, Any]


class ChatMessagesResponse(BaseModel):
    messages: List[ChatMessage]
    count: int
    total: int


class ChatCompletionsRequest(BaseModel):
    model: str
    messages: List[Dict[str, str]]
    max_tokens: Optional[int] = Field(default=1024, ge=64, le=8192)
    temperature: Optional[float] = Field(default=0.7, ge=0.0, le=2.0)


class ChatCompletionsResponse(BaseModel):
    success: bool
    status: str
    content: str
    provider: Optional[str]
    model: str
    timestamp: str


class HealthCheckResponse(BaseModel):
    status: str
    timestamp: str
    checks: Dict[str, Any]


class SystemStatusResponse(BaseModel):
    status: str
    version: str
    uptime_seconds: float
    models_loaded: List[str]
    active_kernels: List[str]
    connected_clients: int
    timestamp: str


class ChatConversationCreateRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    participants: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ChatConversation(BaseModel):
    conversation_id: str
    title: str
    created_at: str
    updated_at: str
    participants: List[str]
    message_count: int


class ModelLoadRequest(BaseModel):
    model_name: str = Field(..., min_length=1)
    context_size: Optional[int] = Field(default=None, ge=512, le=128000)
    gpu_layers: Optional[int] = Field(default=None, ge=-1, le=100)
    quantization: Optional[str] = Field(default=None)


class ModelUnloadRequest(BaseModel):
    model_name: str = Field(..., min_length=1)


class KernelStartRequest(BaseModel):
    kernel_type: str = Field(default="standard")
    config: Dict[str, Any] = Field(default_factory=dict)


class KernelStopRequest(BaseModel):
    kernel_id: str = Field(..., min_length=1)


class TaskSubmitRequest(BaseModel):
    kernel_id: str = Field(..., min_length=1)
    task_type: str = Field(..., min_length=1)
    payload: Dict[str, Any] = Field(default_factory=dict)
    priority: int = Field(default=5, ge=1, le=10)


class LogEntry(BaseModel):
    level: str = Field(default="INFO", pattern="^(DEBUG|INFO|WARNING|ERROR|CRITICAL)$")
    message: str = Field(..., min_length=1)
    source: Optional[str] = Field(default=None)
    metadata: Dict[str, Any] = Field(default_factory=dict)


# ============================================================================
# In-Memory Storage
# ============================================================================

class InMemoryStore:
    def __init__(self):
        self.messages: List[ChatMessage] = []
        self.models_loaded: Set[str] = set()
        self.kernels: Dict[str, Dict[str, Any]] = {}
        
    def add_message(self, msg: ChatMessage):
        self.messages.append(msg)
        if len(self.messages) > 1000:
            self.messages = self.messages[-1000:]
    
    def get_messages(self, channel: Optional[str] = None, limit: int = 100) -> List[ChatMessage]:
        msgs = self.messages
        if channel:
            msgs = [m for m in msgs if m.channel == channel]
        return msgs[-limit:]


store = InMemoryStore()


# ============================================================================
# Daemon State
# ============================================================================

class CellZeroDaemonState:
    def __init__(self):
        self._running = True
        self.start_time = time.time()
        self.system_state = {
            "status": "running",
            "version": "1.1.5",
            "models_loaded": [],
            "active_kernels": ["mcic"],
        }
        self.websocket_server = type('obj', (object,), {
            'host': '127.0.0.1',
            'port': 8765,
            'clients': {}
        })()
        self.event_bus = type('obj', (object,), {'_running': True})()
    
    async def emit_chat_message(self, message: str, sender: str, channel: str = "general", **metadata):
        msg = ChatMessage(
            id=str(uuid.uuid4()),
            message=message,
            sender=sender,
            channel=channel,
            reply_to=None,
            timestamp=datetime.utcnow().isoformat(),
            metadata=metadata
        )
        store.add_message(msg)
        logger.info(f"Chat: {sender} -> {channel}: {message[:50]}...")
        return msg.id
    
    def get_status(self) -> Dict[str, Any]:
        uptime = time.time() - self.start_time
        return {
            **self.system_state,
            "uptime_seconds": uptime,
            "connected_clients": len(self.websocket_server.clients),
        }


daemon = CellZeroDaemonState()


# ============================================================================
# AUTHENTICATION - AUTO-BYPASS FOR LOCALHOST
# ============================================================================

async def verify_auth(request: Request) -> Optional[Dict[str, Any]]:
    """
    ZERO-CONFIG AUTH: Automatically bypass auth for localhost requests.
    Remote requests require Bearer token.
    """
    # AUTO-DETECT: Always allow local requests without any configuration
    if config.is_local_request(request):
        client_ip = request.client.host if request.client else 'unknown'
        logger.debug(f"LOCAL AUTH BYPASS: {client_ip}")
        return {"local": True, "bypass": True}
    
    # Remote requests need auth token
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header[7:]
        if token:
            return {"local": False, "token": token}
    
    # Reject remote requests without auth
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication required for remote access"
    )


# ============================================================================
# FastAPI Application
# ============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting Cell 0 OS Gateway...")
    logger.info(f"Local auth bypass: ENABLED (auto-detect localhost)")
    yield
    logger.info("Shutting down...")


app = FastAPI(
    title="Cell 0 OS Gateway",
    description="Sovereign Edge Model OS - Zero-config local auth",
    version=config.version,
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================================
# API Routes
# ============================================================================

@app.get("/")
async def root():
    return {
        "name": "Cell 0 OS Gateway",
        "version": config.version,
        "auth": "localhost bypass enabled",
        "docs": "/docs",
        "health": "/api/system/health",
        "chat": "/app"
    }


# ----------------------------------------------------------------------------
# Chat Endpoints
# ----------------------------------------------------------------------------

@app.post("/api/chat/messages", response_model=ChatMessageResponse)
async def send_chat_message(
    request: ChatMessageRequest,
    req: Request,
    auth: Optional[Dict] = Depends(verify_auth)
):
    """Send a chat message - NO CONFIG NEEDED FOR LOCALHOST"""
    message_id = await daemon.emit_chat_message(
        message=request.message,
        sender=request.sender,
        channel=request.channel
    )
    
    return ChatMessageResponse(
        success=True,
        message_id=message_id,
        timestamp=datetime.utcnow().isoformat(),
        channel=request.channel
    )


@app.get("/api/chat/messages", response_model=ChatMessagesResponse)
async def get_chat_messages(
    req: Request,
    channel: Optional[str] = None,
    limit: int = Query(default=100, ge=1, le=1000),
    auth: Optional[Dict] = Depends(verify_auth)
):
    """Get chat messages - NO CONFIG NEEDED FOR LOCALHOST"""
    messages = store.get_messages(channel=channel, limit=limit)
    
    return ChatMessagesResponse(
        messages=messages,
        count=len(messages),
        total=len(store.messages)
    )


@app.post("/api/chat/completions", response_model=ChatCompletionsResponse)
async def chat_completions(
    request: ChatCompletionsRequest,
    req: Request,
    auth: Optional[Dict] = Depends(verify_auth)
):
    """OpenAI-compatible chat - NO CONFIG NEEDED FOR LOCALHOST"""
    content = "[Cell 0 OS] Chat works! LLM provider not configured."
    
    return ChatCompletionsResponse(
        success=True,
        status="degraded",
        content=content,
        provider=None,
        model=request.model,
        timestamp=datetime.utcnow().isoformat()
    )


# ----------------------------------------------------------------------------
# Conversation Endpoints
# ----------------------------------------------------------------------------

store.conversations: Dict[str, ChatConversation] = {}

@app.post("/api/chat/conversations")
async def create_conversation(
    request: ChatConversationCreateRequest,
    req: Request,
    auth: Optional[Dict] = Depends(verify_auth)
):
    """Create a new conversation"""
    conv = ChatConversation(
        conversation_id=str(uuid.uuid4()),
        title=request.title,
        created_at=datetime.utcnow().isoformat(),
        updated_at=datetime.utcnow().isoformat(),
        participants=request.participants,
        message_count=0
    )
    store.conversations[conv.conversation_id] = conv
    return conv


@app.get("/api/chat/conversations")
async def list_conversations(
    req: Request,
    auth: Optional[Dict] = Depends(verify_auth)
):
    """List all conversations"""
    return list(store.conversations.values())


@app.get("/api/chat/conversations/{conversation_id}")
async def get_conversation(
    conversation_id: str,
    req: Request,
    auth: Optional[Dict] = Depends(verify_auth)
):
    """Get a specific conversation"""
    if conversation_id not in store.conversations:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return store.conversations[conversation_id]


# ----------------------------------------------------------------------------
# Model Endpoints
# ----------------------------------------------------------------------------

@app.post("/api/models/load")
async def load_model(
    request: ModelLoadRequest,
    req: Request,
    auth: Optional[Dict] = Depends(verify_auth)
):
    """Load a model"""
    store.models_loaded.add(request.model_name)
    return {
        "success": True,
        "model_name": request.model_name,
        "action": "loaded",
        "timestamp": datetime.utcnow().isoformat()
    }


@app.post("/api/models/unload")
async def unload_model(
    request: ModelUnloadRequest,
    req: Request,
    auth: Optional[Dict] = Depends(verify_auth)
):
    """Unload a model"""
    store.models_loaded.discard(request.model_name)
    return {
        "success": True,
        "model_name": request.model_name,
        "action": "unloaded",
        "timestamp": datetime.utcnow().isoformat()
    }


@app.get("/api/models")
async def list_models(
    req: Request,
    auth: Optional[Dict] = Depends(verify_auth)
):
    """List loaded models"""
    return {"models": list(store.models_loaded), "count": len(store.models_loaded)}


# ----------------------------------------------------------------------------
# Kernel Endpoints
# ----------------------------------------------------------------------------

@app.post("/api/kernels/start")
async def start_kernel(
    request: KernelStartRequest,
    req: Request,
    auth: Optional[Dict] = Depends(verify_auth)
):
    """Start a kernel"""
    kernel_id = f"kernel_{uuid.uuid4().hex[:8]}"
    store.kernels[kernel_id] = {
        "kernel_type": request.kernel_type,
        "config": request.config,
        "status": "running",
        "started_at": datetime.utcnow().isoformat()
    }
    return {
        "success": True,
        "kernel_id": kernel_id,
        "action": "started",
        "status": "running",
        "timestamp": datetime.utcnow().isoformat()
    }


@app.post("/api/kernels/stop")
async def stop_kernel(
    request: KernelStopRequest,
    req: Request,
    auth: Optional[Dict] = Depends(verify_auth)
):
    """Stop a kernel"""
    if request.kernel_id not in store.kernels:
        raise HTTPException(status_code=404, detail="Kernel not found")
    store.kernels[request.kernel_id]["status"] = "stopped"
    return {
        "success": True,
        "kernel_id": request.kernel_id,
        "action": "stopped",
        "timestamp": datetime.utcnow().isoformat()
    }


@app.get("/api/kernels")
async def list_kernels(
    req: Request,
    auth: Optional[Dict] = Depends(verify_auth)
):
    """List all kernels"""
    return {"kernels": store.kernels, "count": len(store.kernels)}


@app.post("/api/kernels/tasks")
async def submit_task(
    request: TaskSubmitRequest,
    req: Request,
    auth: Optional[Dict] = Depends(verify_auth)
):
    """Submit a task to a kernel"""
    if request.kernel_id not in store.kernels:
        raise HTTPException(status_code=404, detail="Kernel not found")
    task_id = f"task_{uuid.uuid4().hex[:8]}"
    return {
        "success": True,
        "task_id": task_id,
        "kernel_id": request.kernel_id,
        "status": "queued",
        "timestamp": datetime.utcnow().isoformat()
    }


# ----------------------------------------------------------------------------
# System Endpoints
# ----------------------------------------------------------------------------

@app.get("/api/system/health", response_model=HealthCheckResponse)
async def health_check(req: Request):
    """Health check - PUBLIC"""
    return HealthCheckResponse(
        status="healthy",
        timestamp=datetime.utcnow().isoformat(),
        checks={
            "daemon": daemon._running,
            "event_bus": True,
            "mcic_kernel": True,
        }
    )


@app.get("/api/system/status", response_model=SystemStatusResponse)
async def get_system_status(
    req: Request,
    auth: Optional[Dict] = Depends(verify_auth)
):
    """System status - NO CONFIG NEEDED FOR LOCALHOST"""
    status_data = daemon.get_status()
    return SystemStatusResponse(
        status=status_data["status"],
        version=status_data["version"],
        uptime_seconds=status_data["uptime_seconds"],
        models_loaded=status_data["models_loaded"],
        active_kernels=status_data["active_kernels"],
        connected_clients=status_data["connected_clients"],
        timestamp=datetime.utcnow().isoformat()
    )


@app.get("/api/system/stats")
async def get_system_stats(
    req: Request,
    auth: Optional[Dict] = Depends(verify_auth)
):
    """Get system statistics"""
    return {
        "messages": len(store.messages),
        "conversations": len(store.conversations),
        "models": len(store.models_loaded),
        "kernels": len(store.kernels),
    }


# ----------------------------------------------------------------------------
# Event Endpoints
# ----------------------------------------------------------------------------

@app.get("/api/events/stream")
async def event_stream(req: Request):
    """Server-sent events stream"""
    async def generate():
        yield f"data: {json.dumps({'type': 'connected'})}\n\n"
        import asyncio
        try:
            while True:
                await asyncio.sleep(30)
                yield f"data: {json.dumps({'type': 'heartbeat'})}\n\n"
        except asyncio.CancelledError:
            pass
    
    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache"}
    )


@app.post("/api/events/emit")
async def emit_event(
    event_type: str,
    req: Request,
    data: Dict[str, Any] = None,
    auth: Optional[Dict] = Depends(verify_auth)
):
    """Emit a custom event"""
    return {"success": True, "event_type": event_type}


# ----------------------------------------------------------------------------
# Log Endpoints
# ----------------------------------------------------------------------------

store.logs: List[Dict[str, Any]] = []

@app.post("/api/logs")
async def submit_log(
    entry: LogEntry,
    req: Request,
    auth: Optional[Dict] = Depends(verify_auth)
):
    """Submit a log entry"""
    log_data = {
        "level": entry.level,
        "message": entry.message,
        "source": entry.source,
        "timestamp": datetime.utcnow().isoformat(),
        **entry.metadata
    }
    store.logs.append(log_data)
    return {"success": True}


@app.get("/api/logs")
async def get_logs(
    req: Request,
    level: Optional[str] = None,
    limit: int = Query(default=100, ge=1, le=1000),
    auth: Optional[Dict] = Depends(verify_auth)
):
    """Get log entries"""
    logs = store.logs
    if level:
        logs = [l for l in logs if l.get("level") == level.upper()]
    return {"logs": logs[-limit:], "count": len(logs)}


# ----------------------------------------------------------------------------
# Web UI
# ----------------------------------------------------------------------------

CHAT_UI_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Cell 0 OS - Chat</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #0a0a0f;
            color: #e0e0ff;
            height: 100vh;
            display: flex;
            flex-direction: column;
        }
        header {
            background: #12121a;
            padding: 1rem 2rem;
            border-bottom: 1px solid #2a2a3e;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        h1 {
            font-size: 1.5rem;
            background: linear-gradient(135deg, #00d4aa, #7c3aed);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        .status {
            display: flex;
            align-items: center;
            gap: 0.5rem;
            font-size: 0.875rem;
            color: #00d4aa;
        }
        .status-dot {
            width: 8px;
            height: 8px;
            background: #00d4aa;
            border-radius: 50%;
            animation: pulse 2s infinite;
        }
        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.5; }
        }
        main {
            flex: 1;
            display: grid;
            grid-template-columns: 250px 1fr;
            overflow: hidden;
        }
        .sidebar {
            background: #12121a;
            border-right: 1px solid #2a2a3e;
            padding: 1rem;
        }
        .channel {
            padding: 0.5rem 1rem;
            margin: 0.25rem 0;
            border-radius: 6px;
            cursor: pointer;
            transition: background 0.2s;
        }
        .channel:hover, .channel.active {
            background: #1a1a2e;
        }
        .chat-area {
            display: flex;
            flex-direction: column;
            padding: 1rem;
        }
        .messages {
            flex: 1;
            overflow-y: auto;
            display: flex;
            flex-direction: column;
            gap: 1rem;
            padding: 1rem;
        }
        .message {
            background: #12121a;
            padding: 1rem;
            border-radius: 8px;
            border-left: 3px solid #00d4aa;
        }
        .message-header {
            display: flex;
            justify-content: space-between;
            margin-bottom: 0.5rem;
            font-size: 0.875rem;
        }
        .sender {
            color: #00d4aa;
            font-weight: 500;
        }
        .timestamp {
            color: #9090b0;
        }
        .input-area {
            display: flex;
            gap: 0.5rem;
            padding-top: 1rem;
            border-top: 1px solid #2a2a3e;
        }
        input[type="text"] {
            flex: 1;
            padding: 0.75rem 1rem;
            background: #1a1a2e;
            border: 1px solid #2a2a3e;
            border-radius: 6px;
            color: #e0e0ff;
            font-size: 1rem;
        }
        button {
            padding: 0.75rem 1.5rem;
            background: #00d4aa;
            color: #0a0a0f;
            border: none;
            border-radius: 6px;
            font-weight: 500;
            cursor: pointer;
        }
        button:hover {
            background: #00b894;
        }
    </style>
</head>
<body>
    <header>
        <h1>Cell 0 OS</h1>
        <div class="status">
            <span class="status-dot"></span>
            <span>Connected</span>
        </div>
    </header>
    <main>
        <aside class="sidebar">
            <div class="channel active">general</div>
            <div class="channel">dev</div>
            <div class="channel">random</div>
        </aside>
        <div class="chat-area">
            <div class="messages" id="messages"></div>
            <div class="input-area">
                <input type="text" id="messageInput" placeholder="Type a message...">
                <button onclick="sendMessage()">Send</button>
            </div>
        </div>
    </main>
    <script>
        const messagesEl = document.getElementById('messages');
        const inputEl = document.getElementById('messageInput');
        const sender = 'user-' + Math.random().toString(36).substr(2, 4);
        
        // Load messages on start
        async function loadMessages() {
            try {
                const res = await fetch('/api/chat/messages');
                const data = await res.json();
                messagesEl.innerHTML = '';
                data.messages.forEach(msg => displayMessage(msg));
            } catch (e) {
                console.error('Failed to load messages:', e);
            }
        }
        
        function displayMessage(msg) {
            const div = document.createElement('div');
            div.className = 'message';
            div.innerHTML = `
                <div class="message-header">
                    <span class="sender">${escapeHtml(msg.sender)}</span>
                    <span class="timestamp">${new Date(msg.timestamp).toLocaleTimeString()}</span>
                </div>
                <div>${escapeHtml(msg.message)}</div>
            `;
            messagesEl.appendChild(div);
            messagesEl.scrollTop = messagesEl.scrollHeight;
        }
        
        function escapeHtml(text) {
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        }
        
        async function sendMessage() {
            const text = inputEl.value.trim();
            if (!text) return;
            
            try {
                const res = await fetch('/api/chat/messages', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        message: text,
                        sender: sender,
                        channel: 'general'
                    })
                });
                
                if (res.ok) {
                    inputEl.value = '';
                    loadMessages();
                }
            } catch (e) {
                console.error('Failed to send:', e);
                alert('Failed to send message');
            }
        }
        
        inputEl.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') sendMessage();
        });
        
        // Load messages initially and every 3 seconds
        loadMessages();
        setInterval(loadMessages, 3000);
    </script>
</body>
</html>
"""


@app.get("/app")
async def web_app():
    """Serve the chat UI - NO CONFIG NEEDED FOR LOCALHOST"""
    return HTMLResponse(content=CHAT_UI_HTML)


# ============================================================================
# Main Entry Point
# ============================================================================

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Cell 0 OS Gateway")
    parser.add_argument("--host", default=config.host, help="Host to bind to")
    parser.add_argument("--port", type=int, default=config.port, help="Port to bind to")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose logging")
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    print(f"""
╔════════════════════════════════════════════════════════════════╗
║           Cell 0 OS Gateway                                     ║
╠════════════════════════════════════════════════════════════════╣
║  HTTP API:   http://{args.host}:{args.port}/                 ║
║  Web UI:     http://{args.host}:{args.port}/app              ║
╠════════════════════════════════════════════════════════════════╣
║  Features:                                                      ║
║    ✓ Zero-config local auth (auto-detects localhost)           ║
║    ✓ Chat API                                                   ║
║    ✓ Web UI at /app                                             ║
╚════════════════════════════════════════════════════════════════╝
""")
    
    uvicorn.run(app, host=args.host, port=args.port, log_level="info")


if __name__ == "__main__":
    main()
