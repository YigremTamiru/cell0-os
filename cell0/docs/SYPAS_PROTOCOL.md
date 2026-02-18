# SYPAS Protocol Specification v2.0

**S**ecure **Y**ield **P**rotocol for **A**gent **S**ystems

---

## Overview

SYPAS is the secure communication protocol between Cell 0 OS components. It provides:

- **Capability-based security** - Fine-grained permission tokens
- **Message integrity** - Cryptographic verification
- **Replay protection** - Nonces and timestamps
- **Priority routing** - Quality of service levels

---

## Message Format

### Header (32 bytes)

| Offset | Size | Field | Description |
|--------|------|-------|-------------|
| 0 | 4 | Magic | `SYP\0` (0x53595000) |
| 4 | 1 | Version | Protocol version (2) |
| 5 | 1 | Type | Message type code |
| 6 | 1 | Priority | 0=highest, 255=lowest |
| 7 | 1 | Flags | Bit flags (see below) |
| 8 | 2 | Capability ID | Reference to active token |
| 10 | 6 | Reserved | Future use (zero) |
| 16 | 4 | Payload Length | Big-endian u32 |
| 20 | 8 | Sequence | Monotonic counter |
| 28 | 4 | Timestamp | Unix seconds (big-endian) |

### Flags

| Bit | Name | Description |
|-----|------|-------------|
| 0 | ENCRYPTED | Payload is encrypted |
| 1 | COMPRESSED | Payload is compressed |
| 2 | URGENT | Bypass normal queuing |
| 3 | BROADCAST | Multi-destination |
| 4-7 | Reserved | Must be zero |

---

## Message Types

### System (0x00-0x0F)

| Code | Name | Direction | Description |
|------|------|-----------|-------------|
| 0x00 | HEARTBEAT | Both | Keepalive ping/pong |
| 0x01 | HANDSHAKE | C→S | Connection setup |
| 0x02 | CAPABILITY | Both | Token exchange |
| 0x03 | SHUTDOWN | Both | Graceful close |
| 0x04 | PING | C→S | Latency check |
| 0x05 | PONG | S→C | Latency response |

### Agent Management (0x10-0x1F)

| Code | Name | Direction | Description |
|------|------|-----------|-------------|
| 0x10 | AGENT_SPAWN | D→K | Create agent |
| 0x11 | AGENT_KILL | D→K | Terminate agent |
| 0x12 | AGENT_STATUS | Both | Query/update status |
| 0x13 | AGENT_EVENT | K→D | Lifecycle events |
| 0x14 | AGENT_PAUSE | D→K | Suspend agent |
| 0x15 | AGENT_RESUME | D→K | Resume agent |

### Resources (0x20-0x2F)

| Code | Name | Direction | Description |
|------|------|-----------|-------------|
| 0x20 | ALLOC | D→K | Request resources |
| 0x21 | FREE | D→K | Release resources |
| 0x22 | QUERY | D→K | Query availability |
| 0x23 | LIMIT | K→D | Resource constraints |

### Compute (0x30-0x3F)

| Code | Name | Direction | Description |
|------|------|-----------|-------------|
| 0x30 | TASK_SUBMIT | D→K | Submit compute task |
| 0x31 | TASK_RESULT | K→D | Task completion |
| 0x32 | TASK_CANCEL | D→K | Cancel running task |
| 0x33 | TASK_STATUS | Both | Query task state |

### Storage (0x40-0x4F)

| Code | Name | Direction | Description |
|------|------|-----------|-------------|
| 0x40 | STORE_PUT | D→K | Write data |
| 0x41 | STORE_GET | D→K | Read data |
| 0x42 | STORE_DEL | D→K | Delete data |
| 0x43 | STORE_LIST | D→K | Enumerate keys |

### Events (0x50-0x5F)

| Code | Name | Direction | Description |
|------|------|-----------|-------------|
| 0x50 | EVENT | K→D | System event |
| 0x51 | SUBSCRIBE | D→K | Subscribe to events |
| 0x52 | UNSUBSCRIBE | D→K | Unsubscribe |
| 0x53 | BROADCAST | K→D | Multi-cast event |

### Security (0x70-0x7F)

| Code | Name | Direction | Description |
|------|------|-----------|-------------|
| 0x70 | ATTEST_REQ | D→K | Request attestation |
| 0x71 | ATTEST_RESP | K→D | Attestation proof |
| 0x72 | TOKEN_MINT | D→K | Create capability |
| 0x73 | TOKEN_REVOKE | D→K | Revoke capability |

### Federation (0x80-0x9F)

| Code | Name | Direction | Description |
|------|------|-----------|-------------|
| 0x80 | NODE_JOIN | N→L | Join cluster |
| 0x81 | NODE_LEAVE | N→L | Leave cluster |
| 0x82 | NODE_DISCOVER | Both | Peer discovery |
| 0x83 | SYNC_REQ | F→L | State sync request |
| 0x84 | SYNC_RESP | L→F | State sync data |
| 0x85 | CONSENSUS | Both | Raft messages |

### Errors (0xF0-0xFF)

| Code | Name | Direction | Description |
|------|------|-----------|-------------|
| 0xF0 | ERROR | S→C | General error |
| 0xF1 | E_AUTH | S→C | Authentication failed |
| 0xF2 | E_CAP | S→C | Insufficient capability |
| 0xF3 | E_RESOURCE | S→C | Resource unavailable |
| 0xF4 | E_NOTFOUND | S→C | Entity not found |
| 0xF5 | E_EXISTS | S→C | Entity already exists |
| 0xFE | E_INTERNAL | S→C | Internal error |

---

## Capability Token

### Format (128 bytes)

```rust
pub struct CapabilityToken {
    pub version: u8,           // 1
    pub token_type: u8,        // See below
    pub permissions: u16,      // Permission bits
    pub issuer: [u8; 32],      // Ed25519 pubkey hash
    pub subject: [u8; 32],     // Agent/process ID
    pub issued_at: u64,        // Unix timestamp
    pub expires_at: u64,       // Unix timestamp (0 = never)
    pub nonce: [u8; 16],       // Unique token ID
    pub signature: [u8; 64],   // Ed25519 signature
}
```

### Token Types

| Value | Name | Use Case |
|-------|------|----------|
| 0 | SYSTEM | Kernel-level permissions |
| 1 | AGENT | Agent permissions |
| 2 | USER | User session |
| 3 | FEDERATION | Cross-node trust |
| 4 | EPHEMERAL | Single operation |

### Permission Bits

| Bit | Name | Description |
|-----|------|-------------|
| 0 | AGENT_SPAWN | Create agents |
| 1 | AGENT_KILL | Terminate agents |
| 2 | RESOURCE_ALLOC | Allocate resources |
| 3 | RESOURCE_FREE | Free resources |
| 4 | STORAGE_READ | Read storage |
| 5 | STORAGE_WRITE | Write storage |
| 6 | COMPUTE_SUBMIT | Submit compute |
| 7 | EVENT_EMIT | Emit events |
| 8 | EVENT_SUBSCRIBE | Subscribe to events |
| 9 | SYSTEM_CONFIG | Change config |
| 10 | SECURITY_ADMIN | Security operations |
| 11 | FEDERATION_JOIN | Join federation |
| 12 | FEDERATION_SYNC | Sync state |

---

## Handshake Flow

```
Client                                    Server
  │                                         │
  │  1. CONNECT (Unix Socket / TCP)         │
  │────────────────────────────────────────>│
  │                                         │
  │  2. HANDSHAKE                           │
  │     {                                   │
  │       "version": 2,                     │
  │       "capabilities": [...],            │
  │       "client_version": "1.2.0"         │
  │     }                                   │
  │────────────────────────────────────────>│
  │                                         │
  │  3. HANDSHAKE Response                  │
  │     {                                   │
  │       "session_id": "...",              │
  │       "server_version": "1.2.0",        │
  │       "requires_attestation": true      │
  │     }                                   │
  │<────────────────────────────────────────│
  │                                         │
  │  4. ATTEST_REQ                          │
  │     {                                   │
  │       "measurements": {...},            │
  │       "nonce": "..."                    │
  │     }                                   │
  │────────────────────────────────────────>│
  │                                         │
  │  5. ATTEST_RESP + TOKEN_MINT            │
  │     {                                   │
  │       "verified": true,                 │
  │       "token": <128 bytes>,             │
  │       "capabilities_granted": [...]     │
  │     }                                   │
  │<────────────────────────────────────────│
  │                                         │
  │  6. ESTABLISHED                         │
  │◄═══════════════════════════════════════>│
  │     (Normal operation)                  │
```

---

## Payload Encoding

### JSON (default)

Content-Type: `application/json`

```json
{
  "agent_id": "uuid",
  "agent_type": "inference",
  "config": {...},
  "requested_caps": ["agent_spawn"]
}
```

### MessagePack (compact)

Content-Type: `application/msgpack`

Binary format, ~30% smaller than JSON.

### Protobuf (high-performance)

Content-Type: `application/x-protobuf`

Pre-defined schema, fastest serialization.

---

## Transport Bindings

### Unix Domain Socket

- Path: `/var/run/cell0/kernel.sock`
- Mode: `0600` (owner read/write only)
- Framing: Length-prefixed messages

### TCP

- Default port: `9000`
- TLS: Required for production
- Keepalive: 60 seconds

### Shared Memory

- Segment size: 16MB
- Ring buffer: 8MB per direction
- Synchronization: Atomic operations

---

## Error Handling

All errors include:

```json
{
  "error_code": "E_CAP",
  "error_message": "Insufficient capability for AGENT_SPAWN",
  "request_id": "sequence-number",
  "timestamp": 1708272000
}
```

### Retry Policy

| Error | Retry | Backoff |
|-------|-------|---------|
| E_RESOURCE | Yes | 100ms exponential |
| E_NOTFOUND | No | - |
| E_AUTH | No | - (re-auth required) |
| E_INTERNAL | Yes | 1s fixed |
| Connection lost | Yes | 500ms exponential |

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2025-01-15 | Initial release |
| 2.0 | 2026-02-18 | Federation support, shared memory |

---

## Reference Implementation

- **Rust**: `kernel/src/sypas/`
- **Python**: `cell0/engine/sypas.py`
- **Go**: `pkg/sypas/` (federation)
