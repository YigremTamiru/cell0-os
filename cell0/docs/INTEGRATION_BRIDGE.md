# Kernel↔Daemon Integration Bridge Design

## Overview

The integration bridge is the critical connection between Cell 0's kernel (Rust) and daemon (Python). This document specifies the implementation approach for the SYPAS protocol bridge.

---

## Bridge Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         INTEGRATION BRIDGE                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │                        PYTHON SIDE (cell0d)                            │  │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐                │  │
│  │  │ KernelClient │  │ SYPASCodec   │  │ CapManager   │                │  │
│  │  │              │  │              │  │              │                │  │
│  │  │ - Connect    │  │ - Encode     │  │ - Mint       │                │  │
│  │  │ - Send/Recv  │  │ - Decode     │  │ - Verify     │                │  │
│  │  │ - Health     │  │ - Validate   │  │ - Refresh    │                │  │
│  │  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘                │  │
│  │         │                 │                 │                         │  │
│  │         └─────────────────┴─────────────────┘                         │  │
│  │                           │                                           │  │
│  │                    ┌──────▼───────┐                                   │  │
│  │                    │ Transport    │                                   │  │
│  │                    │ Manager      │                                   │  │
│  │                    │              │                                   │  │
│  │                    │ - UnixSocket │                                   │  │
│  │                    │ - GRPC       │                                   │  │
│  │                    │ - SharedMem  │                                   │  │
│  │                    └──────┬───────┘                                   │  │
│  └───────────────────────────┼───────────────────────────────────────────┘  │
│                              │                                              │
│                          ┌───▼────┐  Unix Domain Socket / Shared Memory   │
│                          │  SYP   │  ═══════════════════════════════════  │
│                          │  AS    │                                       │
│                          │ WIRE   │                                       │
│                          └───┬────┘                                       │
│                              │                                              │
├──────────────────────────────┼──────────────────────────────────────────────┤
│  ┌───────────────────────────▼───────────────────────────────────────────┐  │
│  │                        RUST SIDE (kernel)                              │  │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐                │  │
│  │  │ SYPASRouter  │  │ SYPASCodec   │  │ CapEnforcer  │                │  │
│  │  │              │  │              │  │              │                │  │
│  │  │ - Route      │  │ - Encode     │  │ - Validate   │                │  │
│  │  │ - Dispatch   │  │ - Decode     │  │ - Enforce    │                │  │
│  │  │ - Subscribe  │  │ - Validate   │  │ - Audit      │                │  │
│  │  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘                │  │
│  │         │                 │                 │                         │  │
│  │         └─────────────────┴─────────────────┘                         │  │
│  │                           │                                           │  │
│  │                    ┌──────▼───────┐                                   │  │
│  │                    │ Kernel Core  │                                   │  │
│  │                    │              │                                   │  │
│  │                    │ - Agent Mgmt │                                   │  │
│  │                    │ - Resources  │                                   │  │
│  │                    │ - Security   │                                   │  │
│  │                    └──────────────┘                                   │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Key Components

### Python Side (cell0/engine/kernel_bridge.py)

- **KernelBridge**: Main client class for daemon-to-kernel communication
- **SYPASCodec**: Message encoding/decoding
- **CapabilityToken**: Token management and verification
- **TransportManager**: Handles Unix sockets, gRPC, shared memory

### Rust Side (kernel/src/bridge/)

- **KernelBridge**: Server accepting daemon connections
- **SYPASRouter**: Message routing and dispatch
- **CapEnforcer**: Capability verification
- **ConnectionManager**: Active connection tracking

---

## Implementation Notes

1. **Transport Priority**:
   - Try Unix socket first (lowest latency)
   - Fall back to TCP+gRPC if unavailable
   - Use shared memory for bulk transfers >64KB

2. **Connection Lifecycle**:
   - Connect → Handshake → Attestation → Operation → Heartbeat → Shutdown
   - Auto-reconnect with exponential backoff
   - Graceful degradation if kernel unavailable

3. **Security**:
   - All operations require capability tokens
   - Tokens refreshed automatically before expiry
   - Unix socket permissions: 0600 (owner only)

4. **Error Handling**:
   - Retry on transient failures (E_RESOURCE, E_INTERNAL)
   - Re-authenticate on E_AUTH
   - Propagate fatal errors to caller

---

## Testing Strategy

1. Unit tests for codec (encode/decode roundtrip)
2. Integration tests with mock kernel
3. End-to-end tests with real kernel
4. Load tests for throughput/latency
5. Chaos tests for failure recovery

---

See IPC_PROTOCOL_SPEC.md for complete protocol details.
