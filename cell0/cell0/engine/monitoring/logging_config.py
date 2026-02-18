"""
logging_config.py - Structured Logging Configuration for Cell 0 OS

Provides JSON-structured logging for production environments with:
- Trace ID correlation
- Rotating file handlers
- Contextual information
- Rich console output for development
"""

import os
import sys
import json
import logging
import logging.handlers
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime

# Try to import python-json-logger
try:
    from pythonjsonlogger import jsonlogger
    HAS_JSON_LOGGER = True
except ImportError:
    HAS_JSON_LOGGER = False

# Try to import structlog for advanced logging
try:
    import structlog
    HAS_STRUCTLOG = True
except ImportError:
    HAS_STRUCTLOG = False


class Cell0JsonFormatter(logging.Formatter):
    """JSON formatter for structured logging"""
    
    def __init__(self, environment: str = "development"):
        super().__init__()
        self.environment = environment
        self.hostname = os.uname().nodename
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON"""
        log_data = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "environment": self.environment,
            "hostname": self.hostname,
            "pid": os.getpid(),
        }
        
        # Add extra fields if present
        if hasattr(record, "trace_id"):
            log_data["trace_id"] = record.trace_id
        if hasattr(record, "request_id"):
            log_data["request_id"] = record.request_id
        if hasattr(record, "user_id"):
            log_data["user_id"] = record.user_id
        if hasattr(record, "agent_id"):
            log_data["agent_id"] = record.agent_id
        if hasattr(record, "duration_ms"):
            log_data["duration_ms"] = record.duration_ms
        
        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        
        # Add any extra fields from the record
        for key, value in record.__dict__.items():
            if key not in log_data and not key.startswith("_") and key not in (
                "args", "asctime", "created", "exc_info", "exc_text", "filename",
                "funcName", "levelname", "levelno", "lineno", "module", "msecs",
                "msg", "name", "pathname", "process", "processName", "relativeCreated",
                "stack_info", "thread", "threadName"
            ):
                log_data[key] = value
        
        return json.dumps(log_data, default=str)


class TraceIdFilter(logging.Filter):
    """Add trace ID to log records"""
    
    def __init__(self, trace_id: Optional[str] = None):
        super().__init__()
        self._trace_id = trace_id
    
    def filter(self, record: logging.LogRecord) -> bool:
        if not hasattr(record, "trace_id"):
            record.trace_id = self._trace_id or "-"
        return True


def get_log_directory() -> Path:
    """Get the log directory"""
    log_dir = Path(os.getenv("CELL0_STATE_DIR", Path.home() / ".cell0")) / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    return log_dir


def configure_logging(
    level: str = "INFO",
    environment: str = "development",
    json_output: Optional[bool] = None,
    log_file: Optional[str] = None
):
    """
    Configure logging for Cell 0 OS
    
    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR)
        environment: Environment name (development, staging, production)
        json_output: Whether to use JSON formatting (default: True for prod)
        log_file: Specific log file path (default: auto-generated)
    """
    if json_output is None:
        json_output = environment in ("staging", "production")
    
    # Determine log level
    log_level = getattr(logging, level.upper(), logging.INFO)
    
    # Setup formatters
    if json_output:
        formatter = Cell0JsonFormatter(environment=environment)
    else:
        # Human-readable format for development
        formatter = logging.Formatter(
            "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
    
    # Get root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    
    # Clear existing handlers
    root_logger.handlers = []
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # File handler with rotation (100MB chunks, 10 backups)
    if log_file is None:
        log_file = get_log_directory() / "cell0d.log"
    else:
        log_file = Path(log_file)
    
    file_handler = logging.handlers.RotatingFileHandler(
        log_file,
        maxBytes=100 * 1024 * 1024,  # 100MB
        backupCount=10
    )
    file_handler.setLevel(log_level)
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)
    
    # Add trace ID filter
    trace_filter = TraceIdFilter()
    root_logger.addFilter(trace_filter)
    
    # Configure third-party loggers
    logging.getLogger("uvicorn").setLevel(logging.WARNING)
    logging.getLogger("websockets").setLevel(logging.WARNING)
    
    # Setup structlog if available
    if HAS_STRUCTLOG:
        structlog.configure(
            processors=[
                structlog.stdlib.filter_by_level,
                structlog.stdlib.add_logger_name,
                structlog.stdlib.add_log_level,
                structlog.stdlib.PositionalArgumentsFormatter(),
                structlog.processors.TimeStamper(fmt="iso"),
                structlog.processors.StackInfoRenderer(),
                structlog.processors.format_exc_info,
                structlog.processors.UnicodeDecoder(),
                structlog.processors.JSONRenderer() if json_output else structlog.dev.ConsoleRenderer(),
            ],
            context_class=dict,
            logger_factory=structlog.stdlib.LoggerFactory(),
            wrapper_class=structlog.stdlib.BoundLogger,
            cache_logger_on_first_use=True,
        )
    
    # Log startup message
    logger = logging.getLogger("cell0.logging")
    logger.info(
        f"Logging configured: level={level}, env={environment}, json={json_output}"
    )


def get_logger(name: str) -> logging.Logger:
    """Get a logger with the given name"""
    return logging.getLogger(name)


# Context manager for trace IDs
class LogContext:
    """Context manager for adding context to logs"""
    
    def __init__(self, **context):
        self.context = context
        self.logger = logging.getLogger("cell0")
    
    def __enter__(self):
        for key, value in self.context.items():
            setattr(self.logger, key, value)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        for key in self.context.keys():
            if hasattr(self.logger, key):
                delattr(self.logger, key)
