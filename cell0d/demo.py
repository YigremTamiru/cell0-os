"""
Test and demo script for cell0d event streaming system
Generates various event types to demonstrate the system
"""
import asyncio
import random
import logging
from datetime import datetime
import argparse

# Add parent directory to path for imports
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from core.daemon import CellZeroDaemon
from events.eventbus import (
    EventType, Event, event_bus,
    create_system_status_event, create_chat_message_event,
    create_model_activity_event, create_mcic_event, create_log_event
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("cell0d.demo")


class EventDemo:
    """Generates demo events for testing the event streaming system"""
    
    def __init__(self, daemon: CellZeroDaemon):
        self.daemon = daemon
        self.models = ["qwen2.5-7b", "qwen2.5-3b", "llama3.2-3b", "phi4-mini"]
        self.kernels = ["kernel_001", "kernel_002", "kernel_003"]
        self.senders = ["user", "assistant", "system", "kullu"]
        self._running = False
        self._tasks = []
    
    async def start(self):
        """Start generating demo events"""
        self._running = True
        logger.info("Starting event demo generator...")
        
        # Start various event generators
        self._tasks = [
            asyncio.create_task(self._generate_system_status()),
            asyncio.create_task(self._generate_chat_messages()),
            asyncio.create_task(self._generate_model_activity()),
            asyncio.create_task(self._generate_mcic_events()),
            asyncio.create_task(self._generate_log_stream()),
        ]
        
        await asyncio.gather(*self._tasks, return_exceptions=True)
    
    async def stop(self):
        """Stop generating events"""
        self._running = False
        for task in self._tasks:
            task.cancel()
    
    async def _generate_system_status(self):
        """Generate periodic system status updates"""
        while self._running:
            try:
                await asyncio.sleep(random.uniform(10, 20))
                
                if not self._running:
                    break
                
                status = random.choice(["healthy", "busy", "idle", "optimizing"])
                
                await self.daemon.event_bus.emit(create_system_status_event(
                    status=status,
                    details={
                        "cpu_usage": random.uniform(10, 80),
                        "memory_usage": random.uniform(30, 70),
                        "active_models": len(self.daemon.system_state["models_loaded"]),
                        "temperature": random.uniform(45, 65)
                    }
                ))
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in system status generator: {e}")
    
    async def _generate_chat_messages(self):
        """Generate chat message events"""
        messages = [
            "Hello, how can I help you today?",
            "I'm processing your request...",
            "Here's what I found:",
            "Let me think about that...",
            "Interesting question!",
            "I need more context to answer that.",
            "That's a great idea!",
            "I'm not sure I understand. Could you clarify?",
            "Working on it...",
            "Done! Here's the result:",
        ]
        
        while self._running:
            try:
                await asyncio.sleep(random.uniform(3, 8))
                
                if not self._running:
                    break
                
                sender = random.choice(self.senders)
                message = random.choice(messages)
                
                await self.daemon.emit_chat_message(
                    message=message,
                    sender=sender,
                    channel="general",
                    metadata={
                        "message_id": f"msg_{datetime.utcnow().timestamp()}",
                        "reply_to": None
                    }
                )
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in chat message generator: {e}")
    
    async def _generate_model_activity(self):
        """Generate model loading/unloading events"""
        while self._running:
            try:
                await asyncio.sleep(random.uniform(15, 30))
                
                if not self._running:
                    break
                
                model = random.choice(self.models)
                action = random.choice(["loading", "loaded", "unloading", "unloaded", 
                                       "inference_started", "inference_completed"])
                
                await self.daemon.emit_model_activity(
                    action=action,
                    model_name=model,
                    details={
                        "quantization": "Q4_K_M",
                        "context_size": 32768 if "7b" in model else 8192,
                        "memory_required": f"{random.uniform(2, 6):.1f}GB"
                    }
                )
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in model activity generator: {e}")
    
    async def _generate_mcic_events(self):
        """Generate MCIC (kernel) events"""
        events = [
            "kernel_started",
            "kernel_ready",
            "task_submitted",
            "task_running",
            "task_completed",
            "kernel_idle",
            "kernel_stopping",
            "kernel_stopped",
        ]
        
        while self._running:
            try:
                await asyncio.sleep(random.uniform(5, 15))
                
                if not self._running:
                    break
                
                kernel_id = random.choice(self.kernels)
                event_name = random.choice(events)
                
                await self.daemon.emit_mcic_event(
                    event_name=event_name,
                    kernel_id=kernel_id,
                    payload={
                        "task_id": f"task_{random.randint(1000, 9999)}" if "task" in event_name else None,
                        "duration_ms": random.randint(100, 5000) if "completed" in event_name else None,
                        "queue_depth": random.randint(0, 10)
                    }
                )
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in MCIC event generator: {e}")
    
    async def _generate_log_stream(self):
        """Generate log stream events"""
        log_levels = ["DEBUG", "INFO", "WARNING", "ERROR"]
        log_messages = {
            "DEBUG": [
                "Processing request ID: {id}",
                "Cache hit for key: {key}",
                "Optimizing memory layout",
                "Batch processing {n} items",
            ],
            "INFO": [
                "Request completed successfully",
                "Model {model} loaded in {time}s",
                "New client connected: {client}",
                "Scheduled maintenance in {time} hours",
            ],
            "WARNING": [
                "High memory usage detected: {percent}%",
                "Slow query detected: {duration}ms",
                "Rate limit approaching for {service}",
                "Deprecated API usage: {api}",
            ],
            "ERROR": [
                "Failed to load model: {error}",
                "Connection timeout to {host}",
                "Invalid configuration: {config_key}",
                "Resource not found: {resource}",
            ]
        }
        
        while self._running:
            try:
                await asyncio.sleep(random.uniform(2, 6))
                
                if not self._running:
                    break
                
                level = random.choices(
                    log_levels, 
                    weights=[30, 50, 15, 5]
                )[0]  # Most logs are DEBUG/INFO
                
                template = random.choice(log_messages[level])
                message = template.format(
                    id=random.randint(10000, 99999),
                    key=f"cache_{random.randint(1, 100)}",
                    n=random.randint(10, 100),
                    model=random.choice(self.models),
                    time=f"{random.uniform(0.5, 5):.2f}",
                    client=f"client_{random.randint(1, 10)}",
                    percent=random.randint(80, 95),
                    duration=random.randint(1000, 5000),
                    service=random.choice(["ollama", "openclaw", "gateway"]),
                    api="/v1/chat/completions",
                    error="timeout",
                    host="localhost:11434",
                    config_key="temperature",
                    resource=f"model_{random.randint(1, 5)}"
                )
                
                await self.daemon.emit_log(
                    level=level,
                    message=message,
                    source="cell0d.demo",
                    line=random.randint(1, 1000)
                )
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in log stream generator: {e}")


async def main():
    parser = argparse.ArgumentParser(description="cell0d Demo")
    parser.add_argument("--ws-port", type=int, default=8765, help="WebSocket port")
    parser.add_argument("--http-port", type=int, default=8080, help="HTTP port")
    parser.add_argument("--no-demo-events", action="store_true", help="Don't generate demo events")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose logging")
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Create daemon
    daemon = CellZeroDaemon(ws_host="0.0.0.0", ws_port=args.ws_port)
    
    # Create demo event generator
    demo = None if args.no_demo_events else EventDemo(daemon)
    
    # Start HTTP server in background
    from core.http_server import create_http_server
    http_server = create_http_server(port=args.http_port)
    http_task = asyncio.create_task(asyncio.to_thread(http_server.serve_forever))
    
    print(f"""
╔═══════════════════════════════════════════════════════════════╗
║                    cell0d Event Streaming Demo                 ║
╠═══════════════════════════════════════════════════════════════╣
║  WebSocket: ws://localhost:{args.ws_port:<5}                        ║
║  HTTP UI:   http://localhost:{args.http_port:<5}                      ║
╠═══════════════════════════════════════════════════════════════╣
║  Event Types:                                                  ║
║    • system_status    • chat_message    • model_activity      ║
║    • mcic_event       • log_stream      • heartbeat           ║
╠═══════════════════════════════════════════════════════════════╣
║  Features:                                                     ║
║    ✓ Multiple concurrent clients                              ║
║    ✓ Event filtering per client                               ║
║    ✓ Heartbeat/ping-pong health checks                        ║
║    ✓ Automatic reconnection with backoff                      ║
║    ✓ Event history buffer for new connections                 ║
╚═══════════════════════════════════════════════════════════════╝
""")
    
    try:
        # Start demo event generator
        if demo:
            demo_task = asyncio.create_task(demo.start())
        
        # Run daemon (this blocks until shutdown)
        await daemon.start()
        
    except KeyboardInterrupt:
        print("\nShutting down...")
    finally:
        if demo:
            await demo.stop()
        await daemon.stop()
        http_server.shutdown()


if __name__ == "__main__":
    asyncio.run(main())