"""
COL-Continuity Persistence Backend

Storage abstraction layer supporting multiple backends:
- Local filesystem
- SQLite for structured queries
- Optional cloud backends (S3-compatible)
"""

from __future__ import annotations

import asyncio
import json
import sqlite3
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Any, AsyncIterator, Optional


@dataclass
class StorageConfig:
    """Configuration for storage backend."""
    path: Path
    max_file_size_mb: int = 100
    use_sqlite: bool = True
    enable_wal: bool = True  # Write-Ahead Logging for better concurrency
    sync_mode: str = "NORMAL"  # SQLite sync mode


class StorageBackend(ABC):
    """Abstract base class for storage backends."""
    
    @abstractmethod
    async def store(self, key: str, data: dict[str, Any]) -> None:
        """Store data with the given key."""
        pass
    
    @abstractmethod
    async def load(self, key: str) -> dict[str, Any]:
        """Load data by key."""
        pass
    
    @abstractmethod
    async def delete(self, key: str) -> bool:
        """Delete data by key. Returns True if deleted, False if not found."""
        pass
    
    @abstractmethod
    async def exists(self, key: str) -> bool:
        """Check if key exists."""
        pass
    
    @abstractmethod
    async def list_keys(self, prefix: str = "") -> list[str]:
        """List all keys with optional prefix filter."""
        pass
    
    @abstractmethod
    async def get_stats(self) -> dict[str, Any]:
        """Get storage statistics."""
        pass


class FileSystemBackend(StorageBackend):
    """Filesystem-based storage backend."""
    
    def __init__(self, config: StorageConfig):
        self.config = config
        self.base_path = config.path
        self.base_path.mkdir(parents=True, exist_ok=True)
        
        # Create subdirectories for sharding
        self._ensure_shards()
    
    def _ensure_shards(self) -> None:
        """Create shard directories for better filesystem performance."""
        for i in range(256):
            shard = self.base_path / f"{i:02x}"
            shard.mkdir(exist_ok=True)
    
    def _get_shard_path(self, key: str) -> Path:
        """Get the shard directory for a key."""
        # Use first 2 chars of key as shard
        shard = key[:2] if len(key) >= 2 else "00"
        return self.base_path / shard
    
    def _get_file_path(self, key: str) -> Path:
        """Get the file path for a key."""
        return self._get_shard_path(key) / f"{key}.json"
    
    async def store(self, key: str, data: dict[str, Any]) -> None:
        """Store data to filesystem."""
        file_path = self._get_file_path(key)
        
        # Write atomically using temp file
        temp_path = file_path.with_suffix(".tmp")
        
        def _write():
            with open(temp_path, "w") as f:
                json.dump(data, f, indent=2)
            temp_path.rename(file_path)
        
        await asyncio.get_event_loop().run_in_executor(None, _write)
    
    async def load(self, key: str) -> dict[str, Any]:
        """Load data from filesystem."""
        file_path = self._get_file_path(key)
        
        def _read():
            with open(file_path, "r") as f:
                return json.load(f)
        
        if not file_path.exists():
            raise KeyError(f"Key not found: {key}")
        
        return await asyncio.get_event_loop().run_in_executor(None, _read)
    
    async def delete(self, key: str) -> bool:
        """Delete data from filesystem."""
        file_path = self._get_file_path(key)
        
        def _delete():
            if file_path.exists():
                file_path.unlink()
                return True
            return False
        
        return await asyncio.get_event_loop().run_in_executor(None, _delete)
    
    async def exists(self, key: str) -> bool:
        """Check if key exists."""
        file_path = self._get_file_path(key)
        return await asyncio.get_event_loop().run_in_executor(
            None, file_path.exists
        )
    
    async def list_keys(self, prefix: str = "") -> list[str]:
        """List all keys with optional prefix filter."""
        keys = []
        
        def _list():
            for shard_dir in self.base_path.iterdir():
                if shard_dir.is_dir():
                    for file_path in shard_dir.glob("*.json"):
                        key = file_path.stem
                        if key.startswith(prefix):
                            keys.append(key)
            return keys
        
        return await asyncio.get_event_loop().run_in_executor(None, _list)
    
    async def get_stats(self) -> dict[str, Any]:
        """Get filesystem storage statistics."""
        def _stats():
            total_size = 0
            file_count = 0
            
            for shard_dir in self.base_path.iterdir():
                if shard_dir.is_dir():
                    for file_path in shard_dir.glob("*.json"):
                        total_size += file_path.stat().st_size
                        file_count += 1
            
            return {
                "type": "filesystem",
                "path": str(self.base_path),
                "file_count": file_count,
                "total_size_bytes": total_size,
                "total_size_mb": round(total_size / (1024 * 1024), 2),
            }
        
        return await asyncio.get_event_loop().run_in_executor(None, _stats)


class SQLiteBackend(StorageBackend):
    """SQLite-based storage backend for metadata and small payloads."""
    
    def __init__(self, config: StorageConfig):
        self.config = config
        self.db_path = config.path / "continuity.db"
        self._lock = asyncio.Lock()
        
        # Initialize database
        self._init_db()
    
    def _init_db(self) -> None:
        """Initialize SQLite database."""
        conn = sqlite3.connect(str(self.db_path))
        try:
            cursor = conn.cursor()
            
            # Enable WAL mode for better concurrency
            if self.config.enable_wal:
                cursor.execute("PRAGMA journal_mode=WAL")
            
            cursor.execute(f"PRAGMA synchronous={self.config.sync_mode}")
            
            # Create checkpoints table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS checkpoints (
                    key TEXT PRIMARY KEY,
                    data BLOB NOT NULL,
                    created_at REAL NOT NULL,
                    size_bytes INTEGER NOT NULL,
                    checksum TEXT
                )
            """)
            
            # Create index on created_at for cleanup queries
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_created_at 
                ON checkpoints(created_at)
            """)
            
            # Create metadata table for storage info
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS storage_meta (
                    key TEXT PRIMARY KEY,
                    value TEXT
                )
            """)
            
            conn.commit()
        finally:
            conn.close()
    
    def _get_connection(self) -> sqlite3.Connection:
        """Get a database connection."""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn
    
    async def store(self, key: str, data: dict[str, Any]) -> None:
        """Store data in SQLite."""
        import time
        
        # Serialize data
        payload = json.dumps(data).encode("utf-8")
        checksum = __import__("hashlib").sha256(payload).hexdigest()
        
        async with self._lock:
            def _store():
                conn = self._get_connection()
                try:
                    cursor = conn.cursor()
                    cursor.execute("""
                        INSERT OR REPLACE INTO checkpoints 
                        (key, data, created_at, size_bytes, checksum)
                        VALUES (?, ?, ?, ?, ?)
                    """, (
                        key,
                        payload,
                        time.time(),
                        len(payload),
                        checksum,
                    ))
                    conn.commit()
                finally:
                    conn.close()
            
            await asyncio.get_event_loop().run_in_executor(None, _store)
    
    async def load(self, key: str) -> dict[str, Any]:
        """Load data from SQLite."""
        async with self._lock:
            def _load():
                conn = self._get_connection()
                try:
                    cursor = conn.cursor()
                    cursor.execute(
                        "SELECT data FROM checkpoints WHERE key = ?",
                        (key,)
                    )
                    row = cursor.fetchone()
                    
                    if row is None:
                        raise KeyError(f"Key not found: {key}")
                    
                    return json.loads(row["data"])
                finally:
                    conn.close()
            
            return await asyncio.get_event_loop().run_in_executor(None, _load)
    
    async def delete(self, key: str) -> bool:
        """Delete data from SQLite."""
        async with self._lock:
            def _delete():
                conn = self._get_connection()
                try:
                    cursor = conn.cursor()
                    cursor.execute(
                        "DELETE FROM checkpoints WHERE key = ?",
                        (key,)
                    )
                    conn.commit()
                    return cursor.rowcount > 0
                finally:
                    conn.close()
            
            return await asyncio.get_event_loop().run_in_executor(None, _delete)
    
    async def exists(self, key: str) -> bool:
        """Check if key exists."""
        async with self._lock:
            def _exists():
                conn = self._get_connection()
                try:
                    cursor = conn.cursor()
                    cursor.execute(
                        "SELECT 1 FROM checkpoints WHERE key = ?",
                        (key,)
                    )
                    return cursor.fetchone() is not None
                finally:
                    conn.close()
            
            return await asyncio.get_event_loop().run_in_executor(None, _exists)
    
    async def list_keys(self, prefix: str = "") -> list[str]:
        """List all keys with optional prefix filter."""
        async with self._lock:
            def _list():
                conn = self._get_connection()
                try:
                    cursor = conn.cursor()
                    if prefix:
                        cursor.execute(
                            "SELECT key FROM checkpoints WHERE key LIKE ?",
                            (f"{prefix}%",)
                        )
                    else:
                        cursor.execute("SELECT key FROM checkpoints")
                    
                    return [row["key"] for row in cursor.fetchall()]
                finally:
                    conn.close()
            
            return await asyncio.get_event_loop().run_in_executor(None, _list)
    
    async def get_stats(self) -> dict[str, Any]:
        """Get SQLite storage statistics."""
        async with self._lock:
            def _stats():
                conn = self._get_connection()
                try:
                    cursor = conn.cursor()
                    
                    cursor.execute(
                        "SELECT COUNT(*), SUM(size_bytes) FROM checkpoints"
                    )
                    row = cursor.fetchone()
                    
                    cursor.execute(
                        "SELECT COUNT(*) FROM sqlite_master WHERE type='table'"
                    )
                    table_count = cursor.fetchone()[0]
                    
                    return {
                        "type": "sqlite",
                        "path": str(self.db_path),
                        "record_count": row[0] or 0,
                        "total_size_bytes": row[1] or 0,
                        "total_size_mb": round((row[1] or 0) / (1024 * 1024), 2),
                        "table_count": table_count,
                    }
                finally:
                    conn.close()
            
            return await asyncio.get_event_loop().run_in_executor(None, _stats)
    
    async def cleanup_old(self, older_than_seconds: float) -> int:
        """Remove checkpoints older than specified seconds."""
        import time
        
        cutoff = time.time() - older_than_seconds
        
        async with self._lock:
            def _cleanup():
                conn = self._get_connection()
                try:
                    cursor = conn.cursor()
                    cursor.execute(
                        "DELETE FROM checkpoints WHERE created_at < ?",
                        (cutoff,)
                    )
                    conn.commit()
                    return cursor.rowcount
                finally:
                    conn.close()
            
            return await asyncio.get_event_loop().run_in_executor(None, _cleanup)


class HybridBackend(StorageBackend):
    """
    Hybrid storage backend using SQLite for metadata and filesystem for large payloads.
    
    Small payloads (< 1MB) go to SQLite for fast queries.
    Large payloads go to filesystem for efficiency.
    """
    
    SIZE_THRESHOLD = 1024 * 1024  # 1MB
    
    def __init__(self, config: StorageConfig):
        self.config = config
        self.sqlite = SQLiteBackend(config)
        self.filesystem = FileSystemBackend(
            StorageConfig(path=config.path / "large_files")
        )
    
    def _is_large(self, data: dict[str, Any]) -> bool:
        """Check if data should be stored in filesystem."""
        # Estimate size
        payload = json.dumps(data)
        return len(payload.encode("utf-8")) > self.SIZE_THRESHOLD
    
    async def store(self, key: str, data: dict[str, Any]) -> None:
        """Store data using appropriate backend."""
        if self._is_large(data):
            # Store large payload in filesystem
            await self.filesystem.store(key, data)
            # Store reference in SQLite
            await self.sqlite.store(key, {
                "_storage_type": "filesystem",
                "_reference_key": key,
                "checksum": data.get("checksum"),
            })
        else:
            await self.sqlite.store(key, data)
    
    async def load(self, key: str) -> dict[str, Any]:
        """Load data from appropriate backend."""
        # Try SQLite first
        try:
            data = await self.sqlite.load(key)
            
            # Check if it's a reference
            if data.get("_storage_type") == "filesystem":
                return await self.filesystem.load(key)
            
            return data
        except KeyError:
            # Try filesystem as fallback
            return await self.filesystem.load(key)
    
    async def delete(self, key: str) -> bool:
        """Delete data from both backends."""
        sqlite_result = await self.sqlite.delete(key)
        fs_result = await self.filesystem.delete(key)
        return sqlite_result or fs_result
    
    async def exists(self, key: str) -> bool:
        """Check if key exists in either backend."""
        return await self.sqlite.exists(key) or await self.filesystem.exists(key)
    
    async def list_keys(self, prefix: str = "") -> list[str]:
        """List keys from both backends."""
        sqlite_keys = await self.sqlite.list_keys(prefix)
        fs_keys = await self.filesystem.list_keys(prefix)
        return list(set(sqlite_keys + fs_keys))
    
    async def get_stats(self) -> dict[str, Any]:
        """Get combined storage statistics."""
        sqlite_stats = await self.sqlite.get_stats()
        fs_stats = await self.filesystem.get_stats()
        
        return {
            "type": "hybrid",
            "sqlite": sqlite_stats,
            "filesystem": fs_stats,
            "total_size_mb": sqlite_stats["total_size_mb"] + fs_stats["total_size_mb"],
            "total_records": sqlite_stats["record_count"] + fs_stats["file_count"],
        }


class PersistenceBackend:
    """
    Main persistence backend for COL-Continuity.
    
    Provides a unified interface over multiple storage backends.
    """
    
    def __init__(
        self,
        storage_path: Path | str,
        backend_type: str = "hybrid",
    ):
        self.path = Path(storage_path)
        self.path.mkdir(parents=True, exist_ok=True)
        
        config = StorageConfig(path=self.path)
        
        if backend_type == "sqlite":
            self._backend: StorageBackend = SQLiteBackend(config)
        elif backend_type == "filesystem":
            self._backend = FileSystemBackend(config)
        elif backend_type == "hybrid":
            self._backend = HybridBackend(config)
        else:
            raise ValueError(f"Unknown backend type: {backend_type}")
    
    async def store(self, key: str, data: dict[str, Any]) -> None:
        """Store data."""
        await self._backend.store(key, data)
    
    async def load(self, key: str) -> dict[str, Any]:
        """Load data."""
        return await self._backend.load(key)
    
    async def delete(self, key: str) -> bool:
        """Delete data."""
        return await self._backend.delete(key)
    
    async def exists(self, key: str) -> bool:
        """Check if key exists."""
        return await self._backend.exists(key)
    
    async def list_keys(self, prefix: str = "") -> list[str]:
        """List all keys."""
        return await self._backend.list_keys(prefix)
    
    async def get_stats(self) -> dict[str, Any]:
        """Get storage statistics."""
        return await self._backend.get_stats()