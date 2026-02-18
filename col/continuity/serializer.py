"""
COL-Continuity State Serializer

Handles serialization, compression, and encryption of session state.
Supports differential state storage for efficiency.
"""

from __future__ import annotations

import base64
import hashlib
import json
import pickle
import struct
from dataclasses import dataclass
from enum import Enum
from typing import Any, Optional


class SerializationFormat(Enum):
    """Supported serialization formats."""
    JSON = "json"       # Human-readable, good for simple types
    PICKLE = "pickle"   # Python-native, handles complex objects
    MESSAGEPACK = "msgpack"  # Binary, compact (if available)


class CompressionAlgorithm(Enum):
    """Supported compression algorithms."""
    NONE = "none"
    ZLIB = "zlib"
    LZ4 = "lz4"         # Fast compression (if available)
    ZSTD = "zstd"       # High ratio compression (if available)


class EncryptionAlgorithm(Enum):
    """Supported encryption algorithms."""
    NONE = "none"
    AES256_GCM = "aes256_gcm"  # AES-256 in GCM mode
    CHACHA20_POLY1305 = "chacha20_poly1305"


@dataclass
class SerializedState:
    """Container for serialized state with metadata."""
    payload: bytes
    format: SerializationFormat
    compression: CompressionAlgorithm
    encryption: EncryptionAlgorithm
    checksum: str
    size_bytes: int
    compressed_size_bytes: int
    is_diff: bool
    base_checkpoint_id: Optional[str]
    metadata: dict[str, Any]
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "payload": base64.b64encode(self.payload).decode(),
            "format": self.format.value,
            "compression": self.compression.value,
            "encryption": self.encryption.value,
            "checksum": self.checksum,
            "size_bytes": self.size_bytes,
            "compressed_size_bytes": self.compressed_size_bytes,
            "is_diff": self.is_diff,
            "base_checkpoint_id": self.base_checkpoint_id,
            "metadata": self.metadata,
        }
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SerializedState:
        return cls(
            payload=base64.b64decode(data["payload"]),
            format=SerializationFormat(data["format"]),
            compression=CompressionAlgorithm(data["compression"]),
            encryption=EncryptionAlgorithm(data["encryption"]),
            checksum=data["checksum"],
            size_bytes=data["size_bytes"],
            compressed_size_bytes=data["compressed_size_bytes"],
            is_diff=data["is_diff"],
            base_checkpoint_id=data.get("base_checkpoint_id"),
            metadata=data.get("metadata", {}),
        )


class StateSerializer:
    """
    Serializes session state with compression and optional encryption.
    
    Features:
    - Multiple serialization formats
    - Configurable compression
    - Encryption for sensitive data
    - Differential state storage
    - Integrity verification
    """
    
    def __init__(
        self,
        format: SerializationFormat = SerializationFormat.JSON,
        compression: CompressionAlgorithm = CompressionAlgorithm.ZLIB,
        encryption: EncryptionAlgorithm = EncryptionAlgorithm.NONE,
        encryption_key: bytes | None = None,
        diff_threshold: float = 0.3,  # Store diff if < 30% changed
    ):
        self.format = format
        self.compression = compression
        self.encryption = encryption
        self.encryption_key = encryption_key
        self.diff_threshold = diff_threshold
        
        self._compression_level = 6  # Default zlib level
        self._last_full_state: dict[str, Any] | None = None
        self._last_checkpoint_id: Optional[str] = None
        
        # Try to import optional dependencies
        self._has_msgpack = self._try_import("msgpack")
        self._has_lz4 = self._try_import("lz4.frame")
        self._has_zstd = self._try_import("zstandard")
        self._has_crypto = self._try_import("cryptography")
    
    def _try_import(self, module: str) -> bool:
        """Try to import an optional module."""
        try:
            __import__(module)
            return True
        except ImportError:
            return False
    
    async def serialize(
        self,
        state: dict[str, Any],
        parent_checkpoint: Optional[str] = None,
        force_full: bool = False,
    ) -> dict[str, Any]:
        """
        Serialize state with compression and optional encryption.
        
        Args:
            state: The state to serialize
            parent_checkpoint: ID of parent checkpoint for diff calculation
            force_full: Force full serialization (no diff)
        
        Returns:
            Dictionary containing serialized state and metadata
        """
        # Determine if we should create a diff
        is_diff = False
        base_checkpoint_id = None
        state_to_serialize = state
        
        if not force_full and parent_checkpoint and self._last_full_state:
            diff = self._compute_diff(self._last_full_state, state)
            diff_ratio = self._calculate_diff_ratio(diff, state)
            
            if diff_ratio < self.diff_threshold:
                is_diff = True
                base_checkpoint_id = parent_checkpoint
                state_to_serialize = diff
        
        # Serialize to bytes
        raw_bytes = self._serialize_to_bytes(state_to_serialize)
        size_bytes = len(raw_bytes)
        
        # Compress
        compressed = self._compress(raw_bytes)
        compressed_size = len(compressed)
        
        # Encrypt if enabled
        if self.encryption != EncryptionAlgorithm.NONE and self._has_crypto:
            compressed = self._encrypt(compressed)
        
        # Calculate checksum
        checksum = hashlib.sha256(raw_bytes).hexdigest()
        
        # Update last full state if this is a full checkpoint
        if not is_diff:
            self._last_full_state = state
            self._last_checkpoint_id = parent_checkpoint
        
        serialized = SerializedState(
            payload=compressed,
            format=self.format,
            compression=self.compression,
            encryption=self.encryption,
            checksum=checksum,
            size_bytes=size_bytes,
            compressed_size_bytes=compressed_size,
            is_diff=is_diff,
            base_checkpoint_id=base_checkpoint_id,
            metadata={
                "version": "1.0",
                "timestamp": __import__("time").time(),
            },
        )
        
        return serialized.to_dict()
    
    async def deserialize(
        self,
        serialized: dict[str, Any],
        base_state: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Deserialize state, handling decompression and decryption.
        
        Args:
            serialized: Serialized state dictionary
            base_state: Base state for applying diffs
        
        Returns:
            Deserialized state dictionary
        """
        state_obj = SerializedState.from_dict(serialized)
        
        payload = state_obj.payload
        
        # Decrypt if needed
        if state_obj.encryption != EncryptionAlgorithm.NONE and self._has_crypto:
            payload = self._decrypt(payload)
        
        # Decompress
        raw_bytes = self._decompress(payload, state_obj.compression)
        
        # Deserialize
        state = self._deserialize_from_bytes(raw_bytes, state_obj.format)
        
        # Apply diff if needed
        if state_obj.is_diff and base_state is not None:
            state = self._apply_diff(base_state, state)
        
        return state
    
    def _serialize_to_bytes(self, state: dict[str, Any]) -> bytes:
        """Convert state to bytes using selected format."""
        if self.format == SerializationFormat.JSON:
            return json.dumps(state, default=str, separators=(",", ":")).encode("utf-8")
        
        elif self.format == SerializationFormat.PICKLE:
            return pickle.dumps(state, protocol=pickle.HIGHEST_PROTOCOL)
        
        elif self.format == SerializationFormat.MESSAGEPACK:
            if self._has_msgpack:
                import msgpack
                return msgpack.packb(state, use_bin_type=True)
            else:
                # Fallback to JSON
                return json.dumps(state, default=str, separators=(",", ":")).encode("utf-8")
        
        else:
            raise ValueError(f"Unknown format: {self.format}")
    
    def _deserialize_from_bytes(self, data: bytes, format: SerializationFormat) -> dict[str, Any]:
        """Convert bytes back to state."""
        if format == SerializationFormat.JSON:
            return json.loads(data.decode("utf-8"))
        
        elif format == SerializationFormat.PICKLE:
            return pickle.loads(data)
        
        elif format == SerializationFormat.MESSAGEPACK:
            if self._has_msgpack:
                import msgpack
                return msgpack.unpackb(data, raw=False)
            else:
                return json.loads(data.decode("utf-8"))
        
        else:
            raise ValueError(f"Unknown format: {format}")
    
    def _compress(self, data: bytes) -> bytes:
        """Compress data using selected algorithm."""
        if self.compression == CompressionAlgorithm.NONE:
            return data
        
        elif self.compression == CompressionAlgorithm.ZLIB:
            import zlib
            return zlib.compress(data, level=self._compression_level)
        
        elif self.compression == CompressionAlgorithm.LZ4:
            if self._has_lz4:
                import lz4.frame
                return lz4.frame.compress(data)
            else:
                import zlib
                return zlib.compress(data, level=self._compression_level)
        
        elif self.compression == CompressionAlgorithm.ZSTD:
            if self._has_zstd:
                import zstandard
                cctx = zstandard.ZstdCompressor()
                return cctx.compress(data)
            else:
                import zlib
                return zlib.compress(data, level=self._compression_level)
        
        else:
            raise ValueError(f"Unknown compression: {self.compression}")
    
    def _decompress(self, data: bytes, algorithm: CompressionAlgorithm) -> bytes:
        """Decompress data."""
        if algorithm == CompressionAlgorithm.NONE:
            return data
        
        elif algorithm == CompressionAlgorithm.ZLIB:
            import zlib
            return zlib.decompress(data)
        
        elif algorithm == CompressionAlgorithm.LZ4:
            if self._has_lz4:
                import lz4.frame
                return lz4.frame.decompress(data)
            else:
                import zlib
                return zlib.decompress(data)
        
        elif algorithm == CompressionAlgorithm.ZSTD:
            if self._has_zstd:
                import zstandard
                dctx = zstandard.ZstdDecompressor()
                return dctx.decompress(data)
            else:
                import zlib
                return zlib.decompress(data)
        
        else:
            raise ValueError(f"Unknown compression: {algorithm}")
    
    def _encrypt(self, data: bytes) -> bytes:
        """Encrypt data using selected algorithm."""
        if not self._has_crypto:
            raise RuntimeError("cryptography package required for encryption")
        
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        
        if self.encryption == EncryptionAlgorithm.AES256_GCM:
            if not self.encryption_key:
                raise ValueError("Encryption key required")
            
            # Derive 256-bit key if needed
            key = hashlib.sha256(self.encryption_key).digest()
            
            # Generate random nonce
            import os
            nonce = os.urandom(12)
            
            aesgcm = AESGCM(key)
            ciphertext = aesgcm.encrypt(nonce, data, None)
            
            # Prepend nonce for decryption
            return nonce + ciphertext
        
        else:
            raise ValueError(f"Unknown encryption: {self.encryption}")
    
    def _decrypt(self, data: bytes) -> bytes:
        """Decrypt data."""
        if not self._has_crypto:
            raise RuntimeError("cryptography package required for encryption")
        
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        
        if self.encryption == EncryptionAlgorithm.AES256_GCM:
            if not self.encryption_key:
                raise ValueError("Encryption key required")
            
            key = hashlib.sha256(self.encryption_key).digest()
            
            # Extract nonce (first 12 bytes)
            nonce = data[:12]
            ciphertext = data[12:]
            
            aesgcm = AESGCM(key)
            return aesgcm.decrypt(nonce, ciphertext, None)
        
        else:
            raise ValueError(f"Unknown encryption: {self.encryption}")
    
    def _compute_diff(
        self,
        base: dict[str, Any],
        current: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Compute differential state - only the changes from base to current.
        
        Uses a simple key-based diff for nested dictionaries.
        """
        diff: dict[str, Any] = {}
        
        # Find added or modified keys
        for key, value in current.items():
            if key not in base:
                diff[key] = {"__op": "add", "__value": value}
            elif isinstance(value, dict) and isinstance(base.get(key), dict):
                nested_diff = self._compute_diff(base[key], value)
                if nested_diff:
                    diff[key] = {"__op": "merge", "__diff": nested_diff}
            elif value != base[key]:
                diff[key] = {"__op": "set", "__value": value}
        
        # Find removed keys
        for key in base:
            if key not in current:
                diff[key] = {"__op": "delete"}
        
        return diff
    
    def _apply_diff(
        self,
        base: dict[str, Any],
        diff: dict[str, Any],
    ) -> dict[str, Any]:
        """Apply differential state to base state."""
        result = dict(base)  # Shallow copy
        
        for key, operation in diff.items():
            op_type = operation.get("__op")
            
            if op_type == "add" or op_type == "set":
                result[key] = operation["__value"]
            
            elif op_type == "delete":
                result.pop(key, None)
            
            elif op_type == "merge":
                if key in result and isinstance(result[key], dict):
                    result[key] = self._apply_diff(result[key], operation["__diff"])
                else:
                    result[key] = operation["__diff"]
        
        return result
    
    def _calculate_diff_ratio(self, diff: dict[str, Any], full_state: dict[str, Any]) -> float:
        """Calculate the ratio of changed state to full state."""
        if not full_state:
            return 0.0
        
        diff_keys = len(diff)
        total_keys = len(full_state)
        
        return diff_keys / total_keys if total_keys > 0 else 0.0
    
    def set_encryption_key(self, key: bytes) -> None:
        """Set or update the encryption key."""
        self.encryption_key = key
    
    def get_stats(self) -> dict[str, Any]:
        """Get serializer statistics."""
        return {
            "format": self.format.value,
            "compression": self.compression.value,
            "encryption": self.encryption.value,
            "diff_threshold": self.diff_threshold,
            "has_msgpack": self._has_msgpack,
            "has_lz4": self._has_lz4,
            "has_zstd": self._has_zstd,
            "has_crypto": self._has_crypto,
        }