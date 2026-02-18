"""
Tool Audit Logging for Cell 0 OS

Comprehensive audit logging for all tool usage.
Supports multiple backends: file, database, syslog, webhook.
"""
import json
import os
import sqlite3
import threading
import hashlib
import socket
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable, Union
from enum import Enum
from pathlib import Path
import queue
import logging


class AuditBackend(Enum):
    """Available audit backends."""
    FILE = "file"
    SQLITE = "sqlite"
    SYSLOG = "syslog"
    WEBHOOK = "webhook"
    CONSOLE = "console"
    MEMORY = "memory"


@dataclass
class AuditEvent:
    """Audit event record."""
    timestamp: str
    tool_name: str
    agent_id: str
    action: str  # ALLOW, DENY, ERROR, START, END
    details: Dict[str, Any]
    
    # Optional fields
    session_id: Optional[str] = None
    request_id: Optional[str] = None
    user_id: Optional[str] = None
    duration_ms: Optional[int] = None
    error_message: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)
    
    def to_json(self) -> str:
        """Convert to JSON."""
        return json.dumps(self.to_dict(), default=str)
    
    @property
    def event_hash(self) -> str:
        """Generate unique hash for this event."""
        content = f"{self.timestamp}:{self.tool_name}:{self.agent_id}:{self.action}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]


class AuditFormatter:
    """Format audit events for different outputs."""
    
    @staticmethod
    def jsonl(event: AuditEvent) -> str:
        """Format as JSON Lines."""
        return event.to_json()
    
    @staticmethod
    def syslog(event: AuditEvent) -> str:
        """Format as syslog message."""
        severity = AuditFormatter._get_severity(event.action)
        return (
            f"<{severity}>CELL0[{event.agent_id}]: "
            f"tool={event.tool_name} action={event.action} "
            f"details={json.dumps(event.details)}"
        )
    
    @staticmethod
    def human_readable(event: AuditEvent) -> str:
        """Format for human reading."""
        ts = event.timestamp[:19]  # Truncate to seconds
        action_icon = {
            "ALLOW": "✓",
            "DENY": "✗",
            "ERROR": "⚠",
            "START": "▶",
            "END": "■"
        }.get(event.action, "?")
        
        return (
            f"[{ts}] {action_icon} {event.tool_name} "
            f"(agent:{event.agent_id[:8]}...) - {event.action}"
        )
    
    @staticmethod
    def _get_severity(action: str) -> int:
        """Get syslog severity level."""
        return {
            "ALLOW": 6,   # INFO
            "DENY": 4,    # WARNING
            "ERROR": 3,   # ERROR
            "START": 6,   # INFO
            "END": 6      # INFO
        }.get(action, 6)


class BaseAuditBackend:
    """Base class for audit backends."""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.formatter = AuditFormatter()
    
    def write(self, event: AuditEvent):
        """Write an audit event."""
        raise NotImplementedError
    
    def query(self, **filters) -> List[AuditEvent]:
        """Query audit events."""
        raise NotImplementedError
    
    def close(self):
        """Close backend resources."""
        pass


class FileBackend(BaseAuditBackend):
    """File-based audit logging."""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.file_path = config.get('path', './logs/audit.log')
        self.format = config.get('format', 'jsonl')
        self.max_size_mb = config.get('max_size_mb', 100)
        self.max_files = config.get('max_files', 10)
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(self.file_path), exist_ok=True)
        
        self._lock = threading.Lock()
        self._file = None
        self._open()
    
    def _open(self):
        """Open log file."""
        self._file = open(self.file_path, 'a', buffering=1)
    
    def _rotate_if_needed(self):
        """Rotate log file if too large."""
        if not os.path.exists(self.file_path):
            return
        
        size_mb = os.path.getsize(self.file_path) / (1024 * 1024)
        if size_mb >= self.max_size_mb:
            self._rotate()
    
    def _rotate(self):
        """Perform log rotation."""
        self._file.close()
        
        # Shift existing files
        for i in range(self.max_files - 1, 0, -1):
            old_path = f"{self.file_path}.{i}"
            new_path = f"{self.file_path}.{i + 1}"
            if os.path.exists(old_path):
                os.rename(old_path, new_path)
        
        # Move current to .1
        if os.path.exists(self.file_path):
            os.rename(self.file_path, f"{self.file_path}.1")
        
        self._open()
    
    def write(self, event: AuditEvent):
        """Write event to file."""
        with self._lock:
            self._rotate_if_needed()
            
            if self.format == 'jsonl':
                line = self.formatter.jsonl(event)
            elif self.format == 'human':
                line = self.formatter.human_readable(event)
            else:
                line = event.to_json()
            
            self._file.write(line + '\n')
    
    def query(self, **filters) -> List[AuditEvent]:
        """Query events from file (limited capability)."""
        events = []
        
        files = [self.file_path]
        for i in range(1, self.max_files + 1):
            rotated = f"{self.file_path}.{i}"
            if os.path.exists(rotated):
                files.append(rotated)
        
        for file_path in files:
            if not os.path.exists(file_path):
                continue
            
            with open(file_path, 'r') as f:
                for line in f:
                    try:
                        data = json.loads(line)
                        
                        # Apply filters
                        match = True
                        for key, value in filters.items():
                            if data.get(key) != value:
                                match = False
                                break
                        
                        if match:
                            events.append(AuditEvent(**data))
                    except json.JSONDecodeError:
                        continue
        
        return events
    
    def close(self):
        """Close file."""
        if self._file:
            self._file.close()


class SQLiteBackend(BaseAuditBackend):
    """SQLite-based audit logging with query capabilities."""
    
    SCHEMA = """
    CREATE TABLE IF NOT EXISTS audit_events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        event_hash TEXT UNIQUE,
        timestamp TEXT,
        tool_name TEXT,
        agent_id TEXT,
        action TEXT,
        session_id TEXT,
        request_id TEXT,
        user_id TEXT,
        duration_ms INTEGER,
        error_message TEXT,
        details_json TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    );
    
    CREATE INDEX IF NOT EXISTS idx_timestamp ON audit_events(timestamp);
    CREATE INDEX IF NOT EXISTS idx_tool ON audit_events(tool_name);
    CREATE INDEX IF NOT EXISTS idx_agent ON audit_events(agent_id);
    CREATE INDEX IF NOT EXISTS idx_action ON audit_events(action);
    """
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.db_path = config.get('path', './logs/audit.db')
        
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        
        self._local = threading.local()
        self._init_db()
    
    def _get_conn(self) -> sqlite3.Connection:
        """Get thread-local connection."""
        if not hasattr(self._local, 'conn') or self._local.conn is None:
            self._local.conn = sqlite3.connect(self.db_path)
            self._local.conn.row_factory = sqlite3.Row
        return self._local.conn
    
    def _init_db(self):
        """Initialize database."""
        conn = sqlite3.connect(self.db_path)
        conn.executescript(self.SCHEMA)
        conn.commit()
        conn.close()
    
    def write(self, event: AuditEvent):
        """Write event to database."""
        conn = self._get_conn()
        conn.execute(
            """INSERT OR REPLACE INTO audit_events 
               (event_hash, timestamp, tool_name, agent_id, action,
                session_id, request_id, user_id, duration_ms, 
                error_message, details_json)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                event.event_hash,
                event.timestamp,
                event.tool_name,
                event.agent_id,
                event.action,
                event.session_id,
                event.request_id,
                event.user_id,
                event.duration_ms,
                event.error_message,
                json.dumps(event.details)
            )
        )
        conn.commit()
    
    def query(self, limit: int = 100, offset: int = 0,
              start_time: Optional[str] = None,
              end_time: Optional[str] = None,
              tool_name: Optional[str] = None,
              agent_id: Optional[str] = None,
              action: Optional[str] = None,
              **kwargs) -> List[AuditEvent]:
        """Query events from database."""
        conn = self._get_conn()
        
        where_clauses = []
        params = []
        
        if start_time:
            where_clauses.append("timestamp >= ?")
            params.append(start_time)
        if end_time:
            where_clauses.append("timestamp <= ?")
            params.append(end_time)
        if tool_name:
            where_clauses.append("tool_name = ?")
            params.append(tool_name)
        if agent_id:
            where_clauses.append("agent_id = ?")
            params.append(agent_id)
        if action:
            where_clauses.append("action = ?")
            params.append(action)
        
        where_sql = "WHERE " + " AND ".join(where_clauses) if where_clauses else ""
        
        cursor = conn.execute(
            f"""SELECT * FROM audit_events 
                {where_sql}
                ORDER BY timestamp DESC 
                LIMIT ? OFFSET ?""",
            params + [limit, offset]
        )
        
        events = []
        for row in cursor.fetchall():
            events.append(AuditEvent(
                timestamp=row['timestamp'],
                tool_name=row['tool_name'],
                agent_id=row['agent_id'],
                action=row['action'],
                session_id=row['session_id'],
                request_id=row['request_id'],
                user_id=row['user_id'],
                duration_ms=row['duration_ms'],
                error_message=row['error_message'],
                details=json.loads(row['details_json'])
            ))
        
        return events
    
    def get_stats(self, hours: int = 24) -> Dict[str, Any]:
        """Get audit statistics."""
        conn = self._get_conn()
        since = (datetime.utcnow() - timedelta(hours=hours)).isoformat()
        
        cursor = conn.execute(
            """SELECT action, COUNT(*) as count 
               FROM audit_events 
               WHERE timestamp >= ?
               GROUP BY action""",
            (since,)
        )
        
        action_counts = {row['action']: row['count'] for row in cursor.fetchall()}
        
        cursor = conn.execute(
            """SELECT tool_name, COUNT(*) as count 
               FROM audit_events 
               WHERE timestamp >= ?
               GROUP BY tool_name 
               ORDER BY count DESC 
               LIMIT 10""",
            (since,)
        )
        
        top_tools = {row['tool_name']: row['count'] for row in cursor.fetchall()}
        
        return {
            'period_hours': hours,
            'action_counts': action_counts,
            'top_tools': top_tools
        }
    
    def close(self):
        """Close connection."""
        if hasattr(self._local, 'conn') and self._local.conn:
            self._local.conn.close()
            self._local.conn = None


class ConsoleBackend(BaseAuditBackend):
    """Console output for audit events."""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.level = config.get('level', 'info')
        self.logger = logging.getLogger('cell0.audit')
    
    def write(self, event: AuditEvent):
        """Write event to console."""
        msg = self.formatter.human_readable(event)
        
        if event.action == 'DENY':
            self.logger.warning(msg)
        elif event.action == 'ERROR':
            self.logger.error(msg)
        else:
            self.logger.info(msg)


class MemoryBackend(BaseAuditBackend):
    """In-memory audit storage (for testing)."""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self._events: List[AuditEvent] = []
        self._max_size = config.get('max_size', 10000)
        self._lock = threading.Lock()
    
    def write(self, event: AuditEvent):
        """Store event in memory."""
        with self._lock:
            self._events.append(event)
            if len(self._events) > self._max_size:
                self._events = self._events[-self._max_size:]
    
    def query(self, limit: int = 100, **filters) -> List[AuditEvent]:
        """Query in-memory events."""
        events = self._events
        
        # Apply filters
        for key, value in filters.items():
            events = [e for e in events if getattr(e, key, None) == value]
        
        return events[-limit:]
    
    def clear(self):
        """Clear all events."""
        with self._lock:
            self._events.clear()


class ToolAuditor:
    """
    Main auditor class managing multiple backends.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize auditor.
        
        Args:
            config: Configuration dict with backend settings
        """
        self.config = config or {}
        self.backends: List[BaseAuditBackend] = []
        self._async_queue: Optional[queue.Queue] = None
        self._worker_thread: Optional[threading.Thread] = None
        self._shutdown = False
        
        self._init_backends()
    
    def _init_backends(self):
        """Initialize configured backends."""
        backend_configs = self.config.get('backends', [
            {'type': 'file', 'path': './logs/audit.log'},
            {'type': 'sqlite', 'path': './logs/audit.db'}
        ])
        
        for cfg in backend_configs:
            backend_type = cfg.get('type', 'file')
            
            if backend_type == 'file':
                self.backends.append(FileBackend(cfg))
            elif backend_type == 'sqlite':
                self.backends.append(SQLiteBackend(cfg))
            elif backend_type == 'console':
                self.backends.append(ConsoleBackend(cfg))
            elif backend_type == 'memory':
                self.backends.append(MemoryBackend(cfg))
        
        # Set up async processing if enabled
        if self.config.get('async', False):
            self._async_queue = queue.Queue(maxsize=10000)
            self._worker_thread = threading.Thread(target=self._async_worker, daemon=True)
            self._worker_thread.start()
    
    def _async_worker(self):
        """Background worker for async logging."""
        while not self._shutdown:
            try:
                event = self._async_queue.get(timeout=1)
                for backend in self.backends:
                    try:
                        backend.write(event)
                    except Exception:
                        pass  # Don't crash on logging errors
            except queue.Empty:
                continue
    
    def log_event(self, event: AuditEvent):
        """Log an audit event to all backends."""
        if self._async_queue:
            try:
                self._async_queue.put_nowait(event)
            except queue.Full:
                pass  # Drop event if queue full
        else:
            for backend in self.backends:
                try:
                    backend.write(event)
                except Exception as e:
                    # Log to stderr if backend fails
                    import sys
                    print(f"Audit backend error: {e}", file=sys.stderr)
    
    def log(self, tool_name: str, agent_id: str, action: str, 
            details: Optional[Dict] = None, **kwargs):
        """Convenience method to log an event."""
        event = AuditEvent(
            timestamp=datetime.utcnow().isoformat(),
            tool_name=tool_name,
            agent_id=agent_id,
            action=action,
            details=details or {},
            **kwargs
        )
        self.log_event(event)
    
    def query(self, **filters) -> List[AuditEvent]:
        """Query audit events (from first queryable backend)."""
        for backend in self.backends:
            if hasattr(backend, 'query'):
                return backend.query(**filters)
        return []
    
    def get_stats(self, hours: int = 24) -> Dict[str, Any]:
        """Get audit statistics."""
        for backend in self.backends:
            if hasattr(backend, 'get_stats'):
                return backend.get_stats(hours)
        return {}
    
    def close(self):
        """Close all backends."""
        self._shutdown = True
        
        if self._worker_thread:
            self._worker_thread.join(timeout=5)
        
        for backend in self.backends:
            backend.close()


# Global auditor instance
_global_auditor: Optional[ToolAuditor] = None


def get_auditor() -> ToolAuditor:
    """Get global auditor instance."""
    global _global_auditor
    if _global_auditor is None:
        _global_auditor = ToolAuditor()
    return _global_auditor


def configure_auditor(config: Dict[str, Any]):
    """Configure global auditor."""
    global _global_auditor
    _global_auditor = ToolAuditor(config)
