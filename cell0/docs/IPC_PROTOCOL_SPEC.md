# Cell 0 OS - Kernel↔Daemon IPC Protocol

## Architecture Decision Record (ADR-001)

### Status: PROPOSED
### Date: 2026-02-18
### Author: Cell 0 Architect

---

## Context

Cell 0 OS requires a high-performance, secure communication channel between:
- **Kernel Layer** (Rust bare-metal / containerized)
- **Daemon Layer** (Python service - cell0d)
- **Future: Multi-node federation** (distributed kernels)

## Decision

We will implement a **hybrid IPC protocol** using:

### Layer 1: Unix Domain Sockets (Primary)
- Low-latency local communication
- File-system based access control
- Zero network overhead

### Layer 2: gRPC (Secondary)
- Structured message definitions
- Streaming support
- Cross-platform compatibility

### Layer 3: Shared Memory (High-Bandwidth)
- For large payloads (>64KB)
- Zero-copy where possible
- Lock-free ring buffers

---

## Protocol Stack

```
┌─────────────────────────────────────────────────────────────┐
│                    APPLICATION LAYER                        │
│         (cell0d / Kernel / Swarm Coordinator)               │
├─────────────────────────────────────────────────────────────┤
│                    SYPAS PROTOCOL                           │
│        (Message types, capability tokens, events)           │
├─────────────────────────────────────────────────────────────┤
│                   TRANSPORT LAYER                           │
│    ┌─────────────┐  ┌─────────────┐  ┌─────────────┐       │
│    │ Unix Socket │  │    gRPC     │  │ Shared Mem  │       │
│    │  (primary)  │  │  (fallback) │  │ (bulk data) │       │
│    └─────────────┘  └─────────────┘  └─────────────┘       │
├─────────────────────────────────────────────────────────────┤
│                    SECURITY LAYER                           │
│         (Capability tokens, attestation, ACL)               │
└─────────────────────────────────────────────────────────────┘
```

---

## SYPAS Protocol Specification v2.0

### Message Format

All messages use the SYPAS (Secure Yield Protocol for Agent Systems) format:

```rust
/// SYPAS Protocol Header (32 bytes)
#[repr(C)]
pub struct SYPASHeader {
    /// Magic bytes: "SYP\0"
    pub magic: [u8; 4],
    
    /// Protocol version
    pub version: u8,          // Current: 2
    
    /// Message type
    pub msg_type: u8,         // See MessageType enum
    
    /// Priority level
    pub priority: u8,         // 0-255, lower = higher priority
    
    /// Flags
    pub flags: u8,            // Bitfield: ENCRYPTED, COMPRESSED, etc.
    
    /// Capability token reference
    pub capability_id: u16,   // Reference to active capability
    
    /// Payload size (excluding header)
    pub payload_len: u32,     // Big-endian
    
    /// Sequence number for ordering
    pub sequence: u64,        // Monotonic, per-connection
    
    /// Message timestamp (nanoseconds since Unix epoch)
    pub timestamp: u64,       // For replay protection
}

impl SYPASHeader {
    pub const MAGIC: [u8; 4] = *b"SYP\0";
    pub const VERSION: u8 = 2;
    pub const SIZE: usize = 32;
}
```

### Message Types

```rust
#[repr(u8)]
pub enum MessageType {
    // System Messages (0x00-0x0F)
    Heartbeat = 0x00,        // Keepalive
    Handshake = 0x01,        // Initial connection
    Capabilities = 0x02,     // Capability exchange
    Shutdown = 0x03,         // Graceful shutdown
    
    // Agent Messages (0x10-0x2F)
    AgentSpawn = 0x10,       // Spawn new agent
    AgentKill = 0x11,        // Terminate agent
    AgentStatus = 0x12,      // Agent state query
    AgentEvent = 0x13,       // Agent lifecycle event
    
    // Resource Messages (0x20-0x3F)
    ResourceAlloc = 0x20,    // Allocate resource
    ResourceFree = 0x21,     // Free resource
    ResourceQuery = 0x22,    // Query availability
    
    // Compute Messages (0x30-0x4F)
    ComputeSubmit = 0x30,    // Submit computation task
    ComputeResult = 0x31,    // Task completion
    ComputeCancel = 0x32,    // Cancel task
    
    // Storage Messages (0x40-0x5F)
    StorageRead = 0x40,      // Read from storage
    StorageWrite = 0x41,     // Write to storage
    StorageDelete = 0x42,    // Delete object
    
    // Event Messages (0x50-0x6F)
    EventEmit = 0x50,        // Emit system event
    EventSubscribe = 0x51,   // Subscribe to events
    EventUnsubscribe = 0x52, // Unsubscribe
    
    // Security Messages (0x70-0x7F)
    AttestationRequest = 0x70,
    AttestationResponse = 0x71,
    TokenMint = 0x72,        // Create capability token
    TokenRevoke = 0x73,      // Revoke token
    
    // Federation Messages (0x80-0x9F)
    NodeJoin = 0x80,         // Join federation
    NodeLeave = 0x81,        // Leave federation
    NodeDiscovery = 0x82,    // Discover peers
    SyncState = 0x83,        // State synchronization
    
    // Error Messages (0xF0-0xFF)
    Error = 0xF0,            // General error
    ErrorAuth = 0xF1,        // Authentication error
    ErrorResource = 0xF2,    // Resource unavailable
    ErrorCapability = 0xF3,  // Insufficient capabilities
}
```

### Capability Token Format

```rust
/// Capability token - grants specific permissions
#[repr(C)]
pub struct CapabilityToken {
    /// Token version
    pub version: u8,          // Currently 1
    
    /// Token type
    pub token_type: TokenType,
    
    /// Issuer (kernel or trusted authority)
    pub issuer: [u8; 32],     // Ed25519 public key hash
    
    /// Token subject (who can use this)
    pub subject: [u8; 32],    // Agent/process identifier
    
    /// Permissions bitmask
    pub permissions: u64,     // Bitfield of allowed operations
    
    /// Resource constraints
    pub resource_limits: ResourceLimits,
    
    /// Validity period
    pub issued_at: u64,       // Unix timestamp
    pub expires_at: u64,      // Unix timestamp (0 = never)
    
    /// Token nonce (prevents replay)
    pub nonce: [u8; 16],
    
    /// Signature (Ed25519)
    pub signature: [u8; 64],
}

pub struct ResourceLimits {
    pub max_memory_bytes: u64,
    pub max_cpu_percent: u8,   // 0-100
    pub max_io_mbps: u32,
    pub max_storage_bytes: u64,
    pub max_agents: u16,
}

#[repr(u8)]
pub enum TokenType {
    System = 0,        // Kernel-level permissions
    Agent = 1,         // Agent permissions
    User = 2,          // User session permissions
    Federation = 3,    // Cross-node permissions
    Ephemeral = 4,     // Short-lived (single operation)
}
```

### Permission Bits

```rust
pub const PERM_AGENT_SPAWN: u64 = 1 << 0;
pub const PERM_AGENT_KILL: u64 = 1 << 1;
pub const PERM_RESOURCE_ALLOC: u64 = 1 << 2;
pub const PERM_RESOURCE_FREE: u64 = 1 << 3;
pub const PERM_STORAGE_READ: u64 = 1 << 4;
pub const PERM_STORAGE_WRITE: u64 = 1 << 5;
pub const PERM_COMPUTE_SUBMIT: u64 = 1 << 6;
pub const PERM_EVENT_EMIT: u64 = 1 << 7;
pub const PERM_EVENT_SUBSCRIBE: u64 = 1 << 8;
pub const PERM_SYSTEM_CONFIG: u64 = 1 << 9;
pub const PERM_SECURITY_ADMIN: u64 = 1 << 10;
pub const PERM_FEDERATION_JOIN: u64 = 1 << 11;
pub const PERM_FEDERATION_SYNC: u64 = 1 << 12;
```

---

## Transport Implementations

### 1. Unix Domain Socket Transport

```rust
pub struct UnixSocketTransport {
    socket_path: PathBuf,
    listener: Option<UnixListener>,
    connections: HashMap<ConnectionId, UnixStream>,
    capability_cache: Arc<RwLock<CapabilityCache>>,
}

impl UnixSocketTransport {
    pub const DEFAULT_PATH: &'static str = "/var/run/cell0/kernel.sock";
    pub const BUFFER_SIZE: usize = 65536;
    
    pub async fn bind(path: impl AsRef<Path>) -> Result<Self> {
        let listener = UnixListener::bind(path)?;
        Ok(Self {
            socket_path: path.as_ref().to_path_buf(),
            listener: Some(listener),
            connections: HashMap::new(),
            capability_cache: Arc::new(RwLock::new(CapabilityCache::new())),
        })
    }
    
    pub async fn accept(&mut self) -> Result<(ConnectionId, UnixStream)> {
        let (stream, _) = self.listener.as_ref()
            .unwrap()
            .accept()
            .await?;
        
        let conn_id = ConnectionId::generate();
        self.connections.insert(conn_id, stream.try_clone()?);
        
        Ok((conn_id, stream))
    }
    
    pub async fn send(&mut self, conn_id: ConnectionId, msg: &SYPASMessage) -> Result<()> {
        let stream = self.connections.get_mut(&conn_id)
            .ok_or(Error::UnknownConnection)?;
        
        // Serialize header + payload
        let header_bytes = msg.header.to_bytes();
        stream.write_all(&header_bytes).await?;
        stream.write_all(&msg.payload).await?;
        stream.flush().await?;
        
        Ok(())
    }
    
    pub async fn receive(&mut self, conn_id: ConnectionId) -> Result<SYPASMessage> {
        let stream = self.connections.get_mut(&conn_id)
            .ok_or(Error::UnknownConnection)?;
        
        // Read fixed-size header
        let mut header_buf = [0u8; SYPASHeader::SIZE];
        stream.read_exact(&mut header_buf).await?;
        let header = SYPASHeader::from_bytes(&header_buf)?;
        
        // Validate header
        if header.magic != SYPASHeader::MAGIC {
            return Err(Error::InvalidMagic);
        }
        if header.version != SYPASHeader::VERSION {
            return Err(Error::VersionMismatch);
        }
        
        // Read payload
        let mut payload = vec![0u8; header.payload_len as usize];
        stream.read_exact(&mut payload).await?;
        
        // Verify capability if present
        if header.capability_id != 0 {
            self.verify_capability(conn_id, header.capability_id).await?;
        }
        
        Ok(SYPASMessage { header, payload })
    }
}
```

### 2. Shared Memory Transport (High-Bandwidth)

```rust
pub struct SharedMemoryTransport {
    /// Memory-mapped region
    region: MmapMut,
    
    /// Ring buffer for incoming messages
    rx_ring: RingBuffer,
    
    /// Ring buffer for outgoing messages  
    tx_ring: RingBuffer,
    
    /// Lock-free synchronization
    sync: AtomicSync,
}

const SHM_SIZE: usize = 16 * 1024 * 1024; // 16MB
const RING_SIZE: usize = 8 * 1024 * 1024; // 8MB per direction

impl SharedMemoryTransport {
    pub fn create(name: &str) -> Result<Self> {
        let shm_path = format!("/cell0_shm_{}", name);
        let shm = SharedMemory::create(&shm_path, SHM_SIZE)?;
        let region = unsafe { MmapMut::map_mut(&shm)? };
        
        // Layout: [Sync][RX Ring][TX Ring]
        let sync = AtomicSync::new(&region[0..4096]);
        let rx_ring = RingBuffer::new(&region[4096..4096+RING_SIZE]);
        let tx_ring = RingBuffer::new(&region[4096+RING_SIZE..SHM_SIZE]);
        
        Ok(Self { region, rx_ring, tx_ring, sync })
    }
    
    pub fn attach(name: &str) -> Result<Self> {
        let shm_path = format!("/cell0_shm_{}", name);
        let shm = SharedMemory::open(&shm_path)?;
        let region = unsafe { MmapMut::map_mut(&shm)? };
        
        // Same layout as create
        let sync = AtomicSync::attach(&region[0..4096]);
        let rx_ring = RingBuffer::attach(&region[4096..4096+RING_SIZE]);
        let tx_ring = RingBuffer::attach(&region[4096+RING_SIZE..SHM_SIZE]);
        
        Ok(Self { region, rx_ring, tx_ring, sync })
    }
    
    /// Zero-copy write (for messages < ring buffer capacity)
    pub fn try_send(&self, msg: &[u8]) -> Result<()> {
        // Wait for space (with timeout)
        if !self.tx_ring.wait_for_space(msg.len(), TIMEOUT)? {
            return Err(Error::BufferFull);
        }
        
        // Write to ring buffer
        self.tx_ring.write(msg)?;
        
        // Notify receiver
        self.sync.signal_tx_available();
        
        Ok(())
    }
    
    /// Zero-copy read
    pub fn try_receive(&self, buf: &mut [u8]) -> Result<usize> {
        // Wait for data (with timeout)
        if !self.rx_ring.wait_for_data(TIMEOUT)? {
            return Err(Error::NoData);
        }
        
        // Read from ring buffer
        let n = self.rx_ring.read(buf)?;
        
        // Notify sender
        self.sync.signal_rx_consumed(n);
        
        Ok(n)
    }
}
```

---

## Connection Lifecycle

```
┌─────────┐                    ┌─────────┐
│  Daemon │                    │ Kernel  │
└────┬────┘                    └────┬────┘
     │                              │
     │  1. CONNECT (Unix Socket)    │
     │─────────────────────────────>│
     │                              │
     │  2. HANDSHAKE Request        │
     │─────────────────────────────>│
     │     {version, capabilities}  │
     │                              │
     │  3. HANDSHAKE Response       │
     │<─────────────────────────────│
     │     {session_id, token_req}  │
     │                              │
     │  4. ATTESTATION              │
     │─────────────────────────────>│
     │     (measurements, proof)    │
     │                              │
     │  5. TOKEN Minted             │
     │<─────────────────────────────│
     │                              │
     │  6. ESTABLISHED              │
     │◄════════════════════════════►│
     │     (bidirectional flow)     │
     │                              │
     │  7. HEARTBEAT (every 5s)     │
     │<════════════════════════════>│
     │                              │
     │  N. SHUTDOWN                 │
     │─────────────────────────────>│
     │                              │
```

---

## Python Daemon Integration

```python
# cell0/engine/kernel_ipc.py

import asyncio
import socket
import struct
from dataclasses import dataclass
from typing import Optional, Callable, AsyncIterator
import hashlib

@dataclass
class SYPASMessage:
    """Python representation of SYPAS message"""
    msg_type: int
    priority: int
    capability_id: int
    payload: bytes
    sequence: int = 0
    timestamp: int = 0
    
    MAGIC = b'SYP\x00'
    VERSION = 2
    HEADER_SIZE = 32
    
    def to_bytes(self) -> bytes:
        """Serialize to wire format"""
        header = struct.pack(
            '>4sBBBBHQQQ',
            self.MAGIC,
            self.VERSION,
            self.msg_type,
            self.priority,
            0,  # flags
            self.capability_id,
            len(self.payload),
            self.sequence,
            self.timestamp
        )
        return header + self.payload
    
    @classmethod
    def from_bytes(cls, data: bytes) -> 'SYPASMessage':
        """Deserialize from wire format"""
        if len(data) < cls.HEADER_SIZE:
            raise ValueError("Message too short")
        
        magic, version, msg_type, priority, flags, cap_id, payload_len, seq, ts = \
            struct.unpack('>4sBBBBHQQQ', data[:cls.HEADER_SIZE])
        
        if magic != cls.MAGIC:
            raise ValueError(f"Invalid magic: {magic}")
        if version != cls.VERSION:
            raise ValueError(f"Version mismatch: {version}")
        
        payload = data[cls.HEADER_SIZE:cls.HEADER_SIZE + payload_len]
        
        return cls(
            msg_type=msg_type,
            priority=priority,
            capability_id=cap_id,
            payload=payload,
            sequence=seq,
            timestamp=ts
        )


class KernelIPCClient:
    """IPC client for daemon-to-kernel communication"""
    
    def __init__(self, socket_path: str = "/var/run/cell0/kernel.sock"):
        self.socket_path = socket_path
        self.sock: Optional[socket.socket] = None
        self._sequence = 0
        self._capability_token: Optional[bytes] = None
        self._handlers: dict[int, Callable] = {}
        
    async def connect(self) -> bool:
        """Establish connection to kernel"""
        try:
            self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            self.sock.setblocking(False)
            await asyncio.get_event_loop().sock_connect(
                self.sock, self.socket_path
            )
            
            # Perform handshake
            if not await self._handshake():
                self.sock.close()
                self.sock = None
                return False
            
            # Start message pump
            asyncio.create_task(self._message_pump())
            
            return True
        except Exception as e:
            print(f"Connection failed: {e}")
            return False
    
    async def _handshake(self) -> bool:
        """Perform protocol handshake"""
        handshake = SYPASMessage(
            msg_type=0x01,  # Handshake
            priority=0,
            capability_id=0,
            payload=json.dumps({
                'version': '2.0',
                'daemon_version': '1.2.0',
                'capabilities': ['agent_mgmt', 'compute', 'storage'],
                'pid': os.getpid(),
            }).encode()
        )
        
        await self._send_raw(handshake.to_bytes())
        
        # Wait for response
        response_data = await self._receive_raw()
        response = SYPASMessage.from_bytes(response_data)
        
        if response.msg_type == 0x01:  # Handshake response
            payload = json.loads(response.payload)
            self._session_id = payload.get('session_id')
            
            # Request capability token
            await self._request_capabilities(payload.get('required_attestation', []))
            
            return True
        
        return False
    
    async def send(self, msg_type: int, payload: bytes, priority: int = 128) -> int:
        """Send message to kernel"""
        self._sequence += 1
        
        msg = SYPASMessage(
            msg_type=msg_type,
            priority=priority,
            capability_id=self._capability_id if self._capability_token else 0,
            payload=payload,
            sequence=self._sequence,
            timestamp=int(time.time_ns())
        )
        
        await self._send_raw(msg.to_bytes())
        return self._sequence
    
    async def _message_pump(self):
        """Background message receiver"""
        while self.sock:
            try:
                data = await self._receive_raw()
                if not data:
                    break
                
                msg = SYPASMessage.from_bytes(data)
                await self._handle_message(msg)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"Message pump error: {e}")
    
    async def _handle_message(self, msg: SYPASMessage):
        """Dispatch message to appropriate handler"""
        handler = self._handlers.get(msg.msg_type)
        if handler:
            await handler(msg)
        
        # Handle heartbeat
        if msg.msg_type == 0x00:
            # Echo heartbeat back
            await self.send(0x00, b'pong', priority=0)
    
    async def spawn_agent(self, agent_type: str, config: dict) -> str:
        """Request kernel to spawn agent"""
        payload = json.dumps({
            'agent_type': agent_type,
            'config': config,
            'requested_caps': ['agent_spawn']
        }).encode()
        
        seq = await self.send(0x10, payload)  # AgentSpawn
        
        # Wait for response with timeout
        response = await self._wait_for_response(seq, timeout=5.0)
        
        if response and response.msg_type == 0x12:  # AgentStatus
            result = json.loads(response.payload)
            return result.get('agent_id')
        
        raise RuntimeError(f"Failed to spawn agent: {response}")
    
    async def _wait_for_response(self, sequence: int, timeout: float) -> Optional[SYPASMessage]:
        """Wait for response with matching sequence number"""
        future = asyncio.Future()
        self._pending_responses[sequence] = future
        
        try:
            return await asyncio.wait_for(future, timeout=timeout)
        except asyncio.TimeoutError:
            return None
        finally:
            self._pending_responses.pop(sequence, None)
    
    async def close(self):
        """Graceful shutdown"""
        if self.sock:
            await self.send(0x03, b'')  # Shutdown
            self.sock.close()
            self.sock = None
```

---

## Multi-Node Federation Extension

For distributed deployments, the SYPAS protocol extends with:

```rust
// Federation message extensions
#[repr(u8)]
pub enum FederationMessageType {
    NodeJoin = 0x80,
    NodeJoinAck = 0x81,
    NodeLeave = 0x82,
    NodeDiscovery = 0x83,
    SyncRequest = 0x84,
    SyncResponse = 0x85,
    ConsensusPrepare = 0x86,
    ConsensusCommit = 0x87,
    HeartbeatFederation = 0x88,
}

/// Node identity in federation
pub struct NodeIdentity {
    pub node_id: [u8; 32],
    pub public_key: [u8; 32],
    pub network_addr: SocketAddr,
    pub capabilities: u64,
    pub joined_at: u64,
    pub last_seen: u64,
    pub reputation: f32,
}

/// Federation routing table
pub struct FederationRouter {
    local_node: NodeIdentity,
    peers: HashMap<[u8; 32], NodeIdentity>,
    routes: RoutingTable,
    consensus: ConsensusEngine,
}
```

See `FEDERATION_DESIGN.md` for complete specification.

---

## Performance Targets

| Metric | Local (Unix Socket) | Remote (gRPC) | Shared Memory |
|--------|---------------------|---------------|---------------|
| Latency (p50) | < 100µs | < 5ms | < 10µs |
| Latency (p99) | < 500µs | < 20ms | < 50µs |
| Throughput | 100K msg/s | 10K msg/s | 1M msg/s |
| Max Payload | 64KB (inline) | 4MB | 8MB (ring buffer) |
| Connection Setup | < 5ms | < 100ms | < 1ms |

---

## Security Considerations

1. **Capability Tokens**
   - All operations require valid capability tokens
   - Tokens are short-lived (default: 1 hour)
   - Automatic refresh via heartbeat

2. **Attestation**
   - Daemon must attest to kernel on connection
   - Measurements include: binary hash, config hash, loaded modules
   - Remote attestation for federation nodes

3. **Transport Security**
   - Unix sockets: filesystem permissions (mode 0600)
   - gRPC: mTLS with mutual authentication
   - Shared memory: sealed with attestation key

4. **Audit Logging**
   - All capability minting logged
   - Failed authentication attempts logged
   - Resource allocation tracked per agent

---

## Implementation Timeline

- **Week 1**: Unix socket transport, basic message framing
- **Week 2**: Capability token system, handshake protocol
- **Week 3**: Shared memory transport for bulk data
- **Week 4**: gRPC fallback, federation extensions
- **Week 5**: Security hardening, audit logging
- **Week 6**: Performance optimization, stress testing

---

## References

- `kernel/src/ipc/mod.rs` - Rust kernel implementation
- `cell0/engine/kernel_ipc.py` - Python daemon implementation
- `docs/FEDERATION_DESIGN.md` - Multi-node specification
