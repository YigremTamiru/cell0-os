# SYPAS Protocol Specification

## Sovereign Yield Protocol for Agent Synchronization

**Version:** 1.0.0  
**Status:** Draft  
**Last Updated:** 2026-02-11

---

## 1. Overview

SYPAS (Sovereign Yield Protocol for Agent Synchronization) is the inter-agent communication and scheduling subsystem for the Cell 0 kernel. It provides:

- **Message Passing**: Asynchronous communication between agents
- **Priority-Based Scheduling**: Fair CPU allocation with anti-starvation
- **Cooperative Multitasking**: Yield mechanism for responsive systems
- **Event Routing**: Efficient message delivery to handlers

### 1.1 Design Principles

1. **Sovereignty**: Each agent operates independently with clear boundaries
2. **Cooperation**: Agents yield control voluntarily for system health
3. **Fairness**: Priority scheduling with anti-starvation mechanisms
4. **Efficiency**: Zero-copy message passing where possible
5. **Reliability**: Error handling and graceful degradation

---

## 2. Protocol Architecture

### 2.1 Message Bus

The SYPAS message bus is the central nervous system of the kernel:

```
┌─────────────────────────────────────────────────────────────┐
│                     SYPAS Message Bus                        │
├─────────────────────────────────────────────────────────────┤
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐  │
│  │   Priority   │    │    Ring      │    │   Event      │  │
│  │    Queue     │───▶│   Buffer     │───▶│   Router     │  │
│  │  (Critical)  │    │  (Normal)    │    │              │  │
│  └──────────────┘    └──────────────┘    └──────────────┘  │
└─────────────────────────────────────────────────────────────┘
                              │
              ┌───────────────┼───────────────┐
              ▼               ▼               ▼
        ┌─────────┐     ┌─────────┐     ┌─────────┐
        │ Agent 1 │     │ Agent 2 │     │ Agent N │
        └─────────┘     └─────────┘     └─────────┘
```

### 2.2 Agent Model

Agents are the fundamental units of execution:

- Each agent has a unique 64-bit ID
- Agents communicate exclusively via messages
- No shared memory between agents (enforced isolation)
- Cooperative scheduling with yield points

---

## 3. Message Format

### 3.1 Header Structure

The message header is 48 bytes (packed):

```rust
#[repr(C, packed)]
struct MessageHeader {
    magic: u32,           // 0x53595041 ("SYPA")
    version: u16,         // Protocol version (1)
    message_type: u16,    // Message type identifier
    flags: u16,           // Message flags
    priority: u8,         // Priority level (0-3)
    reserved: u8,         // Reserved for future use
    source: u64,          // Source agent ID
    destination: u64,     // Destination agent ID
    message_id: u64,      // Unique message identifier
    timestamp: u64,       // Message timestamp (ticks)
    payload_size: u32,    // Payload size in bytes
    sequence: u16,        // Fragment sequence number
    total_fragments: u16, // Total fragments (1 = no fragmentation)
}
```

### 3.2 Message Types

| Type | Value | Description |
|------|-------|-------------|
| AgentRegister | 0x0001 | Agent registration request |
| AgentUnregister | 0x0002 | Agent unregistration |
| Heartbeat | 0x0003 | Keepalive signal |
| Ping | 0x0004 | Latency check request |
| Pong | 0x0005 | Latency check response |
| CapabilityRequest | 0x0100 | Request capability |
| CapabilityGrant | 0x0101 | Grant capability |
| LedgerUpdate | 0x0200 | Ledger state update |
| MemoryAlert | 0x0300 | Memory pressure warning |
| ThreatDetected | 0x0400 | Security threat alert |
| ResonanceSync | 0x0500 | Resonance synchronization |
| UserDefined | 0x1000+ | Application-specific |

### 3.3 Priority Levels

| Priority | Value | Use Case |
|----------|-------|----------|
| Low | 0 | Background tasks, logging |
| Normal | 1 | Standard agent communication |
| High | 2 | Urgent notifications |
| Critical | 3 | System alerts, threats |

Messages with High/Critical priority bypass the ring buffer and go directly to the priority queue.

### 3.4 Message Flags

| Flag | Value | Description |
|------|-------|-------------|
| None | 0x0000 | No special flags |
| RequiresAck | 0x0001 | Requires acknowledgment |
| IsAck | 0x0002 | This message is an acknowledgment |
| IsError | 0x0004 | Error response |
| IsEncrypted | 0x0008 | Payload is encrypted |
| IsCompressed | 0x0010 | Payload is compressed |
| IsFragmented | 0x0020 | Message is fragmented |
| IsLastFragment | 0x0040 | Last fragment of message |

---

## 4. Transport Layer

### 4.1 Ring Buffer

- Size: 1024 messages (configurable at compile time)
- Lock-free implementation using atomics
- Producer-consumer pattern
- Overflow: Oldest messages dropped (with statistics tracking)

### 4.2 Priority Queue

- Separate queues for each priority level
- Priority inversion handling
- FIFO within same priority (round-robin)

### 4.3 Event Routing

Messages are routed based on `message_type`:

```rust
match message.header.message_type {
    AgentRegister => handle_agent_register(msg),
    AgentUnregister => handle_agent_unregister(msg),
    Heartbeat => handle_heartbeat(msg),
    CapabilityRequest => handle_capability_request(msg),
    // ... etc
}
```

---

## 5. Scheduling

### 5.1 Agent States

```
┌──────────────┐
│ Unregistered │
└──────┬───────┘
       │ register
       ▼
┌──────────────┐    sleep    ┌───────────┐
│    Ready     │────────────▶│  Sleeping │
└──────┬───────┘             └─────┬─────┘
       │ schedule                  │ wake
       ▼                           ▼
┌──────────────┐    yield    ┌───────────┐
│   Running    │────────────▶│  Yielded  │
└──────┬───────┘             └───────────┘
       │ block
       ▼
┌──────────────┐    unblock  ┌───────────┐
│   Blocked    │────────────▶│   Ready   │
└──────────────┘             └───────────┘
```

### 5.2 Priority-Based Scheduling

1. **Priority Levels**: 4 levels (Idle, Normal, Elevated, Realtime)
2. **Quantum**: Base 100 ticks × priority multiplier (1× to 8×)
3. **Anti-Starvation**: Priority boost after 1000 idle ticks
4. **Round-Robin**: Within same priority, oldest runnable agent selected

### 5.3 Time-Slicing

```
Timeline:
  │ Agent A (Realtime) │ Agent B (Normal) │ Agent C (Idle) │
  │════════════════════│══════════════════│════════════════│
  │  Run: 800 ticks    │  Run: 200 ticks  │  Run: 100 ticks│
  │  Quantum: 800      │  Quantum: 200    │  Quantum: 100  │
  │════════════════════│══════════════════│════════════════│
  │  Priority: 3       │  Priority: 1     │  Priority: 0   │
```

### 5.4 Yield Mechanism

Agents should yield when:
- Work is complete
- Waiting for I/O or messages
- Running longer than 1000 ticks without yielding

System enforces yield at quantum expiration.

---

## 6. System Calls

### 6.1 Call Interface

All system calls return `Result<u64, SyscallError>`:

```rust
fn syscall(num: u64, arg0: u64, arg1: u64, arg2: u64, 
           arg3: u64, arg4: u64, arg5: u64) -> i64
```

Negative return values indicate errors (errno-style).

### 6.2 System Call Numbers

| Number | Name | Description |
|--------|------|-------------|
| 0 | exit | Terminate agent |
| 1 | yield | Yield control |
| 2 | send_message | Send message |
| 3 | receive_message | Receive message |
| 4 | register_agent | Register new agent |
| 5 | unregister_agent | Unregister agent |
| 6 | get_agent_info | Get agent information |
| 7 | set_priority | Change agent priority |
| 8 | sleep | Sleep for ticks |
| 9 | request_capability | Request capability |
| 10 | release_capability | Release capability |
| 11 | check_capability | Check capability |
| 12 | get_stats | Get system statistics |
| 13 | ping | Ping another agent |
| 14 | get_tick | Get current tick |
| 15 | get_agent_id | Get current agent ID |
| 16 | send_message_timeout | Send with timeout |
| 17 | receive_message_timeout | Receive with timeout |
| 18 | reply_message | Reply to message |
| 19 | broadcast_message | Broadcast to all |

### 6.3 Error Codes

| Code | Name | Description |
|------|------|-------------|
| 0 | Success | Operation succeeded |
| -1 | InvalidSyscall | Unknown syscall number |
| -2 | InvalidArgument | Invalid parameter |
| -3 | PermissionDenied | Insufficient permissions |
| -4 | AgentNotFound | Agent doesn't exist |
| -5 | BufferTooSmall | Buffer overflow |
| -6 | Timeout | Operation timed out |
| -7 | BusNotRunning | Message bus stopped |
| -8 | BufferFull | Message queue full |
| -9 | BufferEmpty | No messages available |
| -10 | InvalidMessage | Malformed message |
| -11 | AgentExists | Agent already registered |
| -12 | MaxAgentsReached | Agent limit reached |
| -13 | InvalidPriority | Invalid priority level |
| -99 | NotImplemented | Feature not implemented |

---

## 7. User-Space Bridge (cell0d)

### 7.1 Bridge Architecture

The SYPAS bridge allows user-space processes (cell0d) to communicate with kernel agents:

```
┌─────────────┐         ┌─────────────┐         ┌─────────────┐
│  User App   │◄───────►│   cell0d    │◄───────►│   Kernel    │
│             │  IPC    │   (Bridge)  │  SYPAS  │   SYPAS     │
└─────────────┘         └─────────────┘         └─────────────┘
```

### 7.2 Bridge Protocol

1. **Registration**: cell0d registers as a proxy agent
2. **Message Forwarding**: User messages are wrapped and forwarded
3. **Capability Translation**: User capabilities mapped to agent capabilities
4. **Event Delivery**: Kernel events delivered to subscribed users

### 7.3 Bridge Message Format

Extended header for bridge messages:

```rust
struct BridgeMessage {
    // Standard SYPAS header
    header: MessageHeader,
    // Bridge-specific fields
    user_pid: u64,        // User process ID
    bridge_id: u64,       // Bridge agent ID
    session_token: u64,   // Session authentication
}
```

---

## 8. Security Model

### 8.1 Agent Isolation

- No shared memory between agents
- All communication via message passing
- Capability-based access control
- Sandboxed execution environment

### 8.2 Capability System

Capabilities are represented as a 64-bit bitmap:

| Bit | Capability | Description |
|-----|------------|-------------|
| 0 | SPAWN | Create new agents |
| 1 | TERMINATE | Kill other agents |
| 2 | NETWORK | Network access |
| 3 | STORAGE | Persistent storage |
| 4 | MEMORY_ALLOC | Allocate extra memory |
| 5 | HIGH_PRIORITY | Elevate priority |
| 6 | SYSTEM_INFO | Read system stats |
| 7 | DEBUG | Debug capabilities |
| 8-63 | RESERVED | Future use |

### 8.3 Message Authentication

- All kernel-originated messages signed
- Capability tokens validated on each use
- Session tokens for bridge connections
- Audit logging for security events

---

## 9. Performance Characteristics

### 9.1 Latency Targets

| Operation | Target Latency |
|-----------|---------------|
| Send Message (Ring Buffer) | < 100 ns |
| Send Message (Priority Queue) | < 200 ns |
| Context Switch | < 500 ns |
| System Call | < 1 μs |
| Scheduler Decision | < 1 μs |

### 9.2 Throughput Targets

| Metric | Target |
|--------|--------|
| Messages/Second | 1M+ |
| Context Switches/Second | 100K+ |
| Maximum Agents | 256 |
| Message Queue Depth | 1024 |

### 9.3 Memory Footprint

| Component | Memory |
|-----------|--------|
| Per-Agent Overhead | ~256 bytes |
| Ring Buffer | ~4 MB |
| Priority Queues | ~1 MB |
| Message Headers | ~48 KB |
| Total (256 agents) | ~10 MB |

---

## 10. Implementation Notes

### 10.1 Lock-Free Data Structures

The SYPAS implementation uses lock-free structures for:
- Ring buffer head/tail pointers
- Message ID generation
- Statistics counters

Spinlocks are used for:
- Priority queues (per-level)
- Agent table modifications
- Statistics aggregation

### 10.2 Memory Ordering

- `SeqCst` for all atomic operations (safety over performance)
- Can be relaxed to `Acquire/Release` after thorough testing

### 10.3 No-Std Compatibility

SYPAS is designed for bare-metal environments:
- No heap allocation in hot paths
- Fixed-size arrays and pools
- Static initialization where possible

---

## 11. Future Extensions

### 11.1 Planned Features

1. **Message Compression**: Transparent payload compression
2. **Encryption**: End-to-end message encryption
3. **Multicast**: Efficient multi-destination messages
4. **Message Persistence**: Durable message queue
5. **Remote Agents**: Agent communication across nodes

### 11.2 Research Areas

1. **Work-Stealing**: Dynamic load balancing
2. **NUMA Awareness**: Memory affinity for agents
3. **Real-Time Guarantees**: Hard real-time scheduling
4. **Formal Verification**: Prove correctness of core algorithms

---

## 12. Appendix

### 12.1 Glossary

- **Agent**: A unit of execution in the Cell 0 kernel
- **Capability**: A permission token for system operations
- **Quantum**: Time slice allocated to an agent
- **Ring Buffer**: Circular FIFO buffer for messages
- **Yield**: Voluntary relinquishing of CPU control

### 12.2 References

- Cell 0 Architecture Document
- Kernel Design Specification
- Capability-Based Security Model

### 12.3 Revision History

| Version | Date | Changes |
|---------|------|---------|
| 0.1.0 | 2026-02-01 | Initial draft |
| 1.0.0 | 2026-02-11 | First complete specification |

---

**End of Specification**
