"""
cell0d - Cell Zero Daemon
Main daemon process that runs the event streaming system
"""
import asyncio
import logging
import signal
import sys
import os
from typing import Optional
from datetime import datetime

from events.eventbus import (
    EventBus, EventType, Event, event_bus,
    create_system_status_event, create_log_event,
    create_model_activity_event, create_chat_message_event,
    create_mcic_event
)
from websocket.server import WebSocketServer

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("cell0d")


class CellZeroDaemon:
    """
    Main daemon for Cell 0 OS
    Manages event bus, WebSocket server, and system services
    """
    
    def __init__(self, ws_host: str = "0.0.0.0", ws_port: int = 8765):
        self.event_bus = event_bus
        self.websocket_server = WebSocketServer(
            host=ws_host,
            port=ws_port,
            event_bus=self.event_bus
        )
        
        self._running = False
        self._shutdown_event = asyncio.Event()
        self._tasks: list = []
        self._start_time: Optional[datetime] = None
        
        # System state
        self.system_state = {
            "status": "initializing",
            "version": "1.0.0",
            "models_loaded": [],
            "active_kernels": [],
            "uptime_seconds": 0
        }
        
        logger.info("CellZeroDaemon initialized")
    
    async def start(self):
        """Start the daemon"""
        self._running = True
        self._start_time = datetime.utcnow()
        
        logger.info("Starting cell0d...")
        
        # Setup signal handlers
        self._setup_signals()
        
        # Start event bus
        await self.event_bus.start()
        
        # Start WebSocket server
        await self.websocket_server.start()
        
        # Start system services
        self._tasks.append(asyncio.create_task(self._status_reporter()))
        self._tasks.append(asyncio.create_task(self._uptime_tracker()))
        self._tasks.append(asyncio.create_task(self._log_forwarder()))
        
        # Update system state
        self.system_state["status"] = "running"
        
        # Emit startup event
        await self.event_bus.emit(create_system_status_event(
            "daemon_started",
            self.system_state
        ))
        
        logger.info("cell0d started successfully")
        logger.info(f"WebSocket server available at ws://{self.websocket_server.host}:{self.websocket_server.port}")
        
        # Wait for shutdown signal
        await self._shutdown_event.wait()
        
        # Perform graceful shutdown
        await self.stop()
    
    async def stop(self):
        """Stop the daemon gracefully"""
        if not self._running:
            return
        
        logger.info("Shutting down cell0d...")
        self._running = False
        self.system_state["status"] = "shutting_down"
        
        # Emit shutdown event
        await self.event_bus.emit(create_system_status_event(
            "daemon_stopping",
            self.system_state
        ))
        
        # Cancel all tasks
        for task in self._tasks:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        
        # Stop WebSocket server
        await self.websocket_server.stop()
        
        # Stop event bus
        await self.event_bus.stop()
        
        self.system_state["status"] = "stopped"
        logger.info("cell0d stopped")
    
    def _setup_signals(self):
        """Setup signal handlers for graceful shutdown"""
        loop = asyncio.get_event_loop()
        
        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, self._signal_handler)
    
    def _signal_handler(self):
        """Handle shutdown signals"""
        logger.info("Shutdown signal received")
        self._shutdown_event.set()
    
    async def _status_reporter(self):
        """Periodic system status reporter"""
        while self._running:
            try:
                await asyncio.sleep(30)  # Report every 30 seconds
                
                if not self._running:
                    break
                
                # Update system state
                self.system_state["uptime_seconds"] = (
                    datetime.utcnow() - self._start_time
                ).total_seconds() if self._start_time else 0
                
                self.system_state["connected_clients"] = len(
                    self.websocket_server.clients
                )
                self.system_state["event_queue_size"] = (
                    self.event_bus._event_queue.qsize()
                )
                
                # Emit status event
                await self.event_bus.emit(create_system_status_event(
                    "periodic_update",
                    self.system_state
                ))
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in status reporter: {e}")
    
    async def _uptime_tracker(self):
        """Track system uptime"""
        while self._running:
            try:
                await asyncio.sleep(1)
                
                if self._start_time:
                    self.system_state["uptime_seconds"] = (
                        datetime.utcnow() - self._start_time
                    ).total_seconds()
                    
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in uptime tracker: {e}")
    
    async def _log_forwarder(self):
        """Forward Python logs as events"""
        # This is a placeholder for a more sophisticated log forwarding system
        # For now, we'll just demonstrate the capability
        while self._running:
            try:
                await asyncio.sleep(60)
                
                # Emit a periodic log event for testing
                await self.event_bus.emit(create_log_event(
                    level="INFO",
                    message="cell0d operational",
                    logger_name="cell0d",
                    metadata={"uptime": self.system_state["uptime_seconds"]}
                ))
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in log forwarder: {e}")
    
    # Public API methods for external integration
    
    async def emit_chat_message(self, message: str, sender: str, 
                                channel: str = "general", **metadata):
        """Emit a chat message event"""
        event = create_chat_message_event(
            message=message,
            sender=sender,
            channel=channel,
            metadata=metadata
        )
        await self.event_bus.emit(event)
    
    async def emit_model_activity(self, action: str, model_name: str, **details):
        """Emit a model activity event"""
        # Update internal state
        if action == "loaded":
            if model_name not in self.system_state["models_loaded"]:
                self.system_state["models_loaded"].append(model_name)
        elif action == "unloaded":
            if model_name in self.system_state["models_loaded"]:
                self.system_state["models_loaded"].remove(model_name)
        
        event = create_model_activity_event(
            action=action,
            model_name=model_name,
            details=details
        )
        await self.event_bus.emit(event)
    
    async def emit_mcic_event(self, event_name: str, kernel_id: str, **payload):
        """Emit an MCIC (kernel) event"""
        # Update internal state
        if event_name == "kernel_started":
            if kernel_id not in self.system_state["active_kernels"]:
                self.system_state["active_kernels"].append(kernel_id)
        elif event_name == "kernel_stopped":
            if kernel_id in self.system_state["active_kernels"]:
                self.system_state["active_kernels"].remove(kernel_id)
        
        event = create_mcic_event(
            event_name=event_name,
            kernel_id=kernel_id,
            payload=payload
        )
        await self.event_bus.emit(event)
    
    async def emit_log(self, level: str, message: str, **metadata):
        """Emit a log event"""
        event = create_log_event(
            level=level,
            message=message,
            logger_name="cell0d.external",
            metadata=metadata
        )
        await self.event_bus.emit(event)
    
    def get_status(self) -> dict:
        """Get current daemon status"""
        return {
            **self.system_state,
            "websocket": {
                "host": self.websocket_server.host,
                "port": self.websocket_server.port,
                "connected_clients": len(self.websocket_server.clients),
                "client_ids": list(self.websocket_server.clients.keys())
            },
            "event_bus": self.event_bus.get_stats()
        }


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Cell Zero Daemon")
    parser.add_argument(
        "--host", 
        default="0.0.0.0",
        help="WebSocket server host (default: 0.0.0.0)"
    )
    parser.add_argument(
        "--port", 
        type=int,
        default=8765,
        help="WebSocket server port (default: 8765)"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose logging"
    )
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Create and run daemon
    daemon = CellZeroDaemon(ws_host=args.host, ws_port=args.port)
    
    try:
        asyncio.run(daemon.start())
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()