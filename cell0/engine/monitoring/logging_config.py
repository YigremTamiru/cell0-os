"""
Cell 0 OS - Structured JSON Logging Configuration

Production-ready structured logging with:
- JSON format for log aggregation
- Trace ID correlation across requests
- Rotating file handlers
- Configurable log levels per component
- Contextual logging support
"""

import os
import sys
import json
import logging
import logging.handlers
import uuid
from typing import Optional, Dict, Any, Union
from datetime import datetime
from contextvars import ContextVar
from pathlib import Path
from contextlib import contextmanager

# Context variable for trace IDs
trace_id_var: ContextVar[str] = ContextVar('trace_id', default='')

# Context variable for request context
request_context_var: ContextVar[Dict[str, Any]] = ContextVar('request_context', default={})


# =============================================================================
# JSON Formatter
# =============================================================================

class JSONFormatter(logging.Formatter):
    """
    Custom JSON formatter for structured logging.
    
    Output format:
    {
        "timestamp": "2026-02-18T00:00:00.000Z",
        "level": "INFO",
        "logger": "cell0.gateway.ws",
        "message": "Connection established",
        "trace_id": "abc123",
        "source": {"file": "gateway_ws.py", "line": 150},
        "context": {"agent_id": "agent_001"},
        "cell0": {"version": "1.1.5"}
    }
    """
    
    def __init__(
        self,
        include_trace_id: bool = True,
        include_source: bool = True,
        include_context: bool = True,
        cell0_version: str = "1.1.5"
    ):
        super().__init__()
        self.include_trace_id = include_trace_id
        self.include_source = include_source
        self.include_context = include_context
        self.cell0_version = cell0_version
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        log_obj: Dict[str, Any] = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        
        # Include trace ID if available
        if self.include_trace_id:
            trace_id = trace_id_var.get()
            if trace_id:
                log_obj["trace_id"] = trace_id
        
        # Include source location
        if self.include_source:
            log_obj["source"] = {
                "file": record.filename,
                "line": record.lineno,
                "function": record.funcName,
            }
        
        # Include exception info if present
        if record.exc_info:
            log_obj["exception"] = {
                "type": record.exc_info[0].__name__ if record.exc_info[0] else None,
                "message": str(record.exc_info[1]) if record.exc_info[1] else None,
                "traceback": self.formatException(record.exc_info) if record.exc_info else None,
            }
        
        # Include extra fields from record
        if hasattr(record, 'extra_fields') and record.extra_fields:
            log_obj.update(record.extra_fields)
        
        # Include structured context
        if self.include_context:
            context = request_context_var.get()
            if context:
                log_obj["context"] = context
        
        # Include Cell 0 metadata
        log_obj["cell0"] = {
            "version": self.cell0_version,
            "hostname": os.uname().nodename if hasattr(os, 'uname') else 'unknown',
        }
        
        return json.dumps(log_obj, default=str)


# =============================================================================
# Trace ID Management
# =============================================================================

def get_trace_id() -> str:
    """Get current trace ID from context."""
    return trace_id_var.get()

def set_trace_id(trace_id: Optional[str] = None) -> str:
    """
    Set trace ID in context.
    
    Args:
        trace_id: Trace ID to set. If None, generates a new UUID.
    
    Returns:
        The trace ID that was set.
    """
    if trace_id is None:
        trace_id = str(uuid.uuid4())[:16]
    trace_id_var.set(trace_id)
    return trace_id

def clear_trace_id():
    """Clear the current trace ID."""
    trace_id_var.set('')

@contextmanager
def trace_context(trace_id: Optional[str] = None):
    """
    Context manager for trace ID scoping.
    
    Usage:
        with trace_context():
            logger.info("Processing request")
            # All logs within this block will have the same trace_id
    """
    tid = set_trace_id(trace_id)
    try:
        yield tid
    finally:
        clear_trace_id()


# =============================================================================
# Request Context Management
# =============================================================================

def set_request_context(**kwargs):
    """Set request context values."""
    current = request_context_var.get()
    current.update(kwargs)
    request_context_var.set(current)

def clear_request_context():
    """Clear all request context."""
    request_context_var.set({})

@contextmanager
def request_context(**kwargs):
    """
    Context manager for request context.
    
    Usage:
        with request_context(agent_id="agent_001", user_id="user_123"):
            process_request()
    """
    token = request_context_var.set(kwargs)
    try:
        yield kwargs
    finally:
        request_context_var.reset(token)


# =============================================================================
# Logger Adapters
# =============================================================================

class StructuredLogger(logging.LoggerAdapter):
    """
    Logger adapter that supports structured logging with extra fields.
    
    Usage:
        logger = StructuredLogger(logging.getLogger("cell0.gateway"))
        logger.info("Request processed", extra={"duration_ms": 150, "status": 200})
    """
    
    def __init__(self, logger: logging.Logger, extra: Optional[Dict[str, Any]] = None):
        super().__init__(logger, extra or {})
    
    def process(self, msg: str, kwargs: Dict[str, Any]) -> tuple:
        """Process log message with extra fields."""
        extra = kwargs.get('extra', {})
        
        # Merge with adapter's extra
        if self.extra:
            extra = {**self.extra, **extra}
        
        # Set extra_fields on the record
        kwargs['extra'] = {'extra_fields': extra}
        
        return msg, kwargs
    
    def bind(self, **kwargs) -> 'StructuredLogger':
        """Create a new logger with bound context."""
        new_extra = {**self.extra, **kwargs}
        return StructuredLogger(self.logger, new_extra)


# =============================================================================
# Configuration
# =============================================================================

LOG_LEVELS = {
    "DEBUG": logging.DEBUG,
    "INFO": logging.INFO,
    "WARNING": logging.WARNING,
    "ERROR": logging.ERROR,
    "CRITICAL": logging.CRITICAL,
}

DEFAULT_LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

# Default log directory
DEFAULT_LOG_DIR = Path("/var/log/cell0")
if not DEFAULT_LOG_DIR.parent.exists():
    # Fallback to local logs if /var/log doesn't exist
    DEFAULT_LOG_DIR = Path.home() / ".cell0" / "logs"


def configure_logging(
    level: Union[str, int] = "INFO",
    log_dir: Optional[Path] = None,
    enable_file_logging: bool = True,
    enable_console_logging: bool = True,
    json_format: bool = True,
    max_bytes: int = 104857600,  # 100MB
    backup_count: int = 10,
    component_levels: Optional[Dict[str, str]] = None,
    cell0_version: str = "1.1.5",
) -> logging.Logger:
    """
    Configure structured logging for Cell 0 OS.
    
    Args:
        level: Default log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_dir: Directory for log files (default: /var/log/cell0 or ~/.cell0/logs)
        enable_file_logging: Whether to log to files
        enable_console_logging: Whether to log to console
        json_format: Use JSON format for file logs
        max_bytes: Maximum bytes per log file before rotation
        backup_count: Number of backup files to keep
        component_levels: Dict of logger names to log levels
        cell0_version: Cell 0 version for log metadata
    
    Returns:
        Root Cell 0 logger
    """
    # Convert string level to int
    if isinstance(level, str):
        level = LOG_LEVELS.get(level.upper(), logging.INFO)
    
    # Determine log directory
    if log_dir is None:
        log_dir = DEFAULT_LOG_DIR
    log_dir = Path(log_dir)
    log_dir.mkdir(parents=True, exist_ok=True)
    
    # Create root logger
    root_logger = logging.getLogger("cell0")
    root_logger.setLevel(level)
    root_logger.handlers = []  # Clear existing handlers
    
    # Console handler
    if enable_console_logging:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(level)
        
        if json_format:
            console_handler.setFormatter(JSONFormatter(cell0_version=cell0_version))
        else:
            console_handler.setFormatter(logging.Formatter(DEFAULT_LOG_FORMAT))
        
        root_logger.addHandler(console_handler)
    
    # File handlers
    if enable_file_logging:
        # Main application log
        app_handler = logging.handlers.RotatingFileHandler(
            log_dir / "cell0.json",
            maxBytes=max_bytes,
            backupCount=backup_count,
        )
        app_handler.setLevel(level)
        app_handler.setFormatter(JSONFormatter(cell0_version=cell0_version))
        root_logger.addHandler(app_handler)
        
        # Error log (errors and above only)
        error_handler = logging.handlers.RotatingFileHandler(
            log_dir / "cell0-error.json",
            maxBytes=max_bytes,
            backupCount=backup_count,
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(JSONFormatter(cell0_version=cell0_version))
        root_logger.addHandler(error_handler)
        
        # Audit log for security events
        audit_handler = logging.handlers.RotatingFileHandler(
            log_dir / "cell0-audit.json",
            maxBytes=max_bytes,
            backupCount=backup_count,
        )
        audit_handler.setLevel(logging.INFO)
        audit_handler.setFormatter(JSONFormatter(cell0_version=cell0_version))
        audit_logger = logging.getLogger("cell0.audit")
        audit_logger.addHandler(audit_handler)
        audit_logger.setLevel(logging.INFO)
    
    # Configure component-specific log levels
    if component_levels:
        for component, comp_level in component_levels.items():
            if isinstance(comp_level, str):
                comp_level = LOG_LEVELS.get(comp_level.upper(), logging.INFO)
            logging.getLogger(f"cell0.{component}").setLevel(comp_level)
    
    # Suppress verbose third-party logs
    logging.getLogger("websockets").setLevel(logging.WARNING)
    logging.getLogger("aiohttp").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    
    root_logger.info(
        "Logging configured",
        extra={
            "log_dir": str(log_dir),
            "level": logging.getLevelName(level),
            "json_format": json_format,
            "max_bytes": max_bytes,
            "backup_count": backup_count,
        }
    )
    
    return root_logger


def get_logger(name: str, extra: Optional[Dict[str, Any]] = None) -> StructuredLogger:
    """
    Get a structured logger instance.
    
    Args:
        name: Logger name (will be prefixed with 'cell0.')
        extra: Default extra fields to include
    
    Returns:
        StructuredLogger instance
    """
    if not name.startswith("cell0."):
        name = f"cell0.{name}"
    
    logger = logging.getLogger(name)
    return StructuredLogger(logger, extra)


# =============================================================================
# FastAPI/HTTP Integration
# =============================================================================

def setup_request_logging_middleware(app):
    """
    Setup request logging middleware for FastAPI/aiohttp apps.
    
    This middleware:
    - Generates trace IDs for each request
    - Logs request start and completion
    - Captures request duration
    - Includes request metadata in logs
    """
    try:
        # Try FastAPI
        from fastapi import Request
        from starlette.middleware.base import BaseHTTPMiddleware
        
        class RequestLoggingMiddleware(BaseHTTPMiddleware):
            async def dispatch(self, request: Request, call_next):
                # Generate trace ID
                trace_id = request.headers.get("X-Trace-ID") or str(uuid.uuid4())[:16]
                set_trace_id(trace_id)
                
                # Set request context
                set_request_context(
                    method=request.method,
                    path=request.url.path,
                    client_ip=request.client.host if request.client else None,
                    user_agent=request.headers.get("User-Agent"),
                )
                
                logger = get_logger("http")
                start_time = datetime.utcnow()
                
                logger.info("Request started")
                
                try:
                    response = await call_next(request)
                    duration = (datetime.utcnow() - start_time).total_seconds()
                    
                    logger.info(
                        "Request completed",
                        extra={
                            "status_code": response.status_code,
                            "duration_seconds": duration,
                        }
                    )
                    
                    # Add trace ID to response
                    response.headers["X-Trace-ID"] = trace_id
                    return response
                    
                except Exception as e:
                    duration = (datetime.utcnow() - start_time).total_seconds()
                    logger.exception(
                        "Request failed",
                        extra={
                            "error": str(e),
                            "duration_seconds": duration,
                        }
                    )
                    raise
                finally:
                    clear_trace_id()
                    clear_request_context()
        
        app.add_middleware(RequestLoggingMiddleware)
        
    except ImportError:
        # Try aiohttp
        try:
            from aiohttp import web
            
            @web.middleware
            async def request_logging_middleware(request, handler):
                trace_id = request.headers.get("X-Trace-ID") or str(uuid.uuid4())[:16]
                set_trace_id(trace_id)
                
                set_request_context(
                    method=request.method,
                    path=request.path,
                    client_ip=request.remote,
                    user_agent=request.headers.get("User-Agent"),
                )
                
                logger = get_logger("http")
                start_time = datetime.utcnow()
                
                logger.info("Request started")
                
                try:
                    response = await handler(request)
                    duration = (datetime.utcnow() - start_time).total_seconds()
                    
                    logger.info(
                        "Request completed",
                        extra={
                            "status_code": response.status,
                            "duration_seconds": duration,
                        }
                    )
                    
                    response.headers["X-Trace-ID"] = trace_id
                    return response
                    
                except Exception as e:
                    duration = (datetime.utcnow() - start_time).total_seconds()
                    logger.exception(
                        "Request failed",
                        extra={
                            "error": str(e),
                            "duration_seconds": duration,
                        }
                    )
                    raise
                finally:
                    clear_trace_id()
                    clear_request_context()
            
            app.middlewares.append(request_logging_middleware)
            
        except ImportError:
            raise RuntimeError("Neither FastAPI nor aiohttp is available")


# =============================================================================
# WebSocket Integration
# =============================================================================

class WebSocketLogger:
    """
    Helper class for logging WebSocket events with trace IDs.
    """
    
    def __init__(self, connection_type: str, connection_id: str):
        self.connection_type = connection_type
        self.connection_id = connection_id
        self.logger = get_logger(f"websocket.{connection_type}")
        
        # Set trace ID for this connection
        set_trace_id(connection_id)
        set_request_context(
            connection_type=connection_type,
            connection_id=connection_id,
        )
    
    def connection_opened(self, client_info: Optional[Dict] = None):
        """Log connection opened."""
        self.logger.info(
            "WebSocket connection opened",
            extra={"client_info": client_info or {}}
        )
    
    def connection_closed(self, reason: str = ""):
        """Log connection closed."""
        self.logger.info(
            "WebSocket connection closed",
            extra={"reason": reason}
        )
        clear_trace_id()
        clear_request_context()
    
    def message_received(self, message_type: str, size_bytes: int = 0):
        """Log message received."""
        self.logger.debug(
            "Message received",
            extra={
                "message_type": message_type,
                "size_bytes": size_bytes,
            }
        )
    
    def message_sent(self, message_type: str, size_bytes: int = 0):
        """Log message sent."""
        self.logger.debug(
            "Message sent",
            extra={
                "message_type": message_type,
                "size_bytes": size_bytes,
            }
        )
    
    def error(self, error_type: str, error_message: str):
        """Log WebSocket error."""
        self.logger.error(
            "WebSocket error",
            extra={
                "error_type": error_type,
                "error_message": error_message,
            }
        )


# =============================================================================
# Context Manager Support
# =============================================================================

from contextlib import contextmanager

@contextmanager
def log_operation(operation: str, logger_name: str = "cell0", **context):
    """
    Context manager for logging operations with timing.
    
    Usage:
        with log_operation("model_inference", model="qwen2.5:7b"):
            result = model.generate(prompt)
    """
    logger = get_logger(logger_name)
    start_time = datetime.utcnow()
    
    set_request_context(operation=operation, **context)
    
    logger.info(f"{operation} started")
    
    try:
        yield
        duration = (datetime.utcnow() - start_time).total_seconds()
        logger.info(
            f"{operation} completed",
            extra={"duration_seconds": duration}
        )
    except Exception as e:
        duration = (datetime.utcnow() - start_time).total_seconds()
        logger.exception(
            f"{operation} failed",
            extra={
                "error": str(e),
                "duration_seconds": duration,
            }
        )
        raise
    finally:
        clear_request_context()


# =============================================================================
# Initialize Default Configuration
# =============================================================================

def init_logging_from_env():
    """
    Initialize logging configuration from environment variables.
    
    Environment variables:
    - CELL0_LOG_LEVEL: Log level (default: INFO)
    - CELL0_LOG_DIR: Log directory (default: /var/log/cell0)
    - CELL0_LOG_FORMAT: Format type (json|text, default: json)
    - CELL0_LOG_MAX_BYTES: Max bytes per file (default: 104857600)
    - CELL0_LOG_BACKUP_COUNT: Number of backups (default: 10)
    """
    level = os.environ.get("CELL0_LOG_LEVEL", "INFO")
    log_dir = os.environ.get("CELL0_LOG_DIR")
    json_format = os.environ.get("CELL0_LOG_FORMAT", "json").lower() == "json"
    max_bytes = int(os.environ.get("CELL0_LOG_MAX_BYTES", "104857600"))
    backup_count = int(os.environ.get("CELL0_LOG_BACKUP_COUNT", "10"))
    
    return configure_logging(
        level=level,
        log_dir=Path(log_dir) if log_dir else None,
        json_format=json_format,
        max_bytes=max_bytes,
        backup_count=backup_count,
    )


# Auto-initialize if CELL0_AUTO_INIT_LOGGING is set
if os.environ.get("CELL0_AUTO_INIT_LOGGING", "false").lower() == "true":
    init_logging_from_env()
