# MCIC Architecture Documentation

## Overview

**MCIC** (Micro Controller Interface Core) is the civilization-grade kernel at the heart of Cell 0 OS. This document describes the mandatory kernel architecture, integration patterns, and security model.

**Version:** 2.0-MANDATORY  
**Caps Epoch:** 47  
**Status:** Kernel enforcement active

---

## Architecture Principles

### 1. Mandatory Kernel Policy

The MCIC kernel is **NOT OPTIONAL**. Cell 0 daemon (cell0d) requires the kernel to function:

- **Without kernel:** cell0d fails to start with clear error messages
- **With kernel:** Full system capabilities unlocked
- **Kernel failure:** Graceful degradation with retry logic

### 2. Orientational Continuity (OC)

All kernel operations maintain orientational continuity:

```
Cell 0 → Kernel Bridge → MCIC Kernel → Hardware
   ↑          ↑             ↑           ↑
   └──────────┴─────────────┴───────────┘
          Orientational Continuity Layer
```

### 3. Defense in Depth

Security enforced at multiple layers:

1. **Kernel-level:** System call validation
2. **Bridge-level:** Message authentication
3. **Application-level:** Capability-based access

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     CELL 0 DAEMON (cell0d)                   │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │   Web UI    │  │   Chat API  │  │   Agent Swarm       │  │
│  │  (FastAPI)  │  │  (WebSocket)│  │  (Async Tasks)      │  │
│  └──────┬──────┘  └──────┬──────┘  └──────────┬──────────┘  │
│         └─────────────────┴────────────────────┘             │
│                         │                                     │
│              ┌──────────▼──────────┐                         │
│              │   MCIC Manager      │ ← MANDATORY             │
│              │  (Kernel Lifecycle) │                         │
│              └──────────┬──────────┘                         │
└─────────────────────────┼───────────────────────────────────┘
                          │
              ┌───────────▼────────────┐
              │    MCIC Bridge         │  ← SYFPASS Protocol
              │  (Unix Domain Socket)  │
              └───────────┬────────────┘
                          │
┌─────────────────────────┼───────────────────────────────────┐
│              ┌──────────▼──────────┐                        │
│              │   MCIC KERNEL       │                        │
│              │  (Bare Metal Rust)  │                        │
│  ┌───────────┼─────────────────────┼───────────┐           │
│  │           │  Kernel Subsystems  │           │           │
│  │  ┌────────┴────┐  ┌────────────┴────┐      │           │
│  │  │   Memory    │  │   Security      │      │           │
│  │  │  Manager    │  │   Enforcer      │      │           │
│  │  └─────────────┘  └─────────────────┘      │           │
│  │  ┌─────────────┐  ┌─────────────────┐      │           │
│  │  │    Agent    │  │    SYFPASS      │      │           │
│  │  │  Scheduler  │  │     Router      │      │           │
│  │  └─────────────┘  └─────────────────┘      │           │
│  │  ┌─────────────┐  ┌─────────────────┐      │           │
│  │  │   Shared    │  │   Hardware      │      │           │
│  │  │   Memory    │  │   Abstraction   │      │           │
│  │  └─────────────┘  └─────────────────┘      │           │
│  └────────────────────────────────────────────┘           │
│                                                           │
│  Execution Modes:                                         │
│    • QEMU (Virtualized)  ← Default                        │
│    • Container (Simulated) ← Development                  │
│    • Hardware (Bare Metal) ← Production                   │
└───────────────────────────────────────────────────────────┘
```

---

## Kernel Lifecycle

### 1. Initialization Flow

```
cell0d starts
    │
    ▼
MCIC Manager initialized
    │
    ├── Check kernel binary exists?
    │   ├── No → Build kernel (if auto_build=True)
    │   │      └── Build failed → ERROR (if mandatory)
    │   └── Yes → Continue
    │
    ├── Check kernel running?
    │   ├── No → Start kernel (if auto_start=True)
    │   │      └── Start failed → ERROR (if mandatory)
    │   └── Yes → Continue
    │
    ├── Connect to kernel
    │   └── Connect failed → Retry with exponential backoff
    │       └── Max retries → ERROR (if mandatory)
    │
    └── Start health monitoring
        └── Monitor running → kernel HEALTHY
```

### 2. State Machine

```
                    ┌──────────────┐
         ┌─────────►│   UNKNOWN    │◄────────┐
         │          └──────┬───────┘         │
         │                 │                 │
         │                 ▼                 │
    ┌────┴────┐     ┌──────────────┐   ┌────┴────┐
    │ STOPPED │◄────│ NOT_INSTALLED│   │  ERROR  │
    └────┬────┘     └──────┬───────┘   └────┬────┘
         │                 │                 │
         │                 ▼                 │
         │          ┌──────────────┐         │
         └─────────►│  NOT_BUILT   │─────────┘
                    └──────┬───────┘
                           │
                           ▼
                    ┌──────────────┐
         ┌─────────►│   STARTING   │◄────────┐
         │          └──────┬───────┘         │
         │                 │                 │
         │                 ▼                 │
    ┌────┴────┐     ┌──────────────┐   ┌────┴────┐
    │ DEGRADED│◄────│   RUNNING    ├───►│  PANIC  │
    └────┬────┘     └──────────────┘    └─────────┘
         │
         └────────► RECONNECTING
```

### 3. Exponential Backoff Retry

```python
retry_delay = INITIAL_RETRY_DELAY  # 1.0s
while not connected and attempts < MAX_RECONNECT_ATTEMPTS:
    attempt += 1
    
    if await connect():
        return True
    
    await sleep(retry_delay)
    retry_delay = min(retry_delay * BACKOFF_FACTOR, MAX_RETRY_DELAY)
    retry_delay *= (0.9 + 0.2 * random())  # Add jitter
```

---

## SYFPASS Protocol

**SYFPASS** (Sovereign Yield For Proof And Sovereign Signal) is the message protocol between cell0d and the MCIC kernel.

### Message Header (16 bytes)

```rust
struct SYFPASSHeader {
    magic: [u8; 4],      // "SYP\0"
    version: u8,         // Protocol version (1)
    opcode: u8,          // Operation code
    priority: u8,        // Priority level
    reserved: u8,        // Reserved
    payload_len: u32,    // Payload length (big-endian)
    timestamp: u32,      // Unix timestamp (big-endian)
}
```

### Operation Codes

| Code | Name      | Description                    |
|------|-----------|--------------------------------|
| 0x01 | EVENT     | Standard event message         |
| 0x02 | COMMAND   | Command to kernel              |
| 0x03 | RESPONSE  | Response from kernel           |
| 0x04 | HEARTBEAT | Keepalive message              |
| 0xFF | ERROR     | Error condition                |

### Priority Levels

| Level | Value | Use Case                      |
|-------|-------|-------------------------------|
| CRITICAL | 0x00 | OC updates, panics           |
| HIGH     | 0x01 | Security events              |
| NORMAL   | 0x02 | Standard messages            |
| LOW      | 0x03 | Background tasks             |

### Event Structure

```json
{
  "event_id": "uuid-v4",
  "source": "component_id",
  "target": "*" | "component_id",
  "event_type": "event.category",
  "payload": { ... },
  "timestamp": "2026-02-11T22:30:00Z",
  "caps_epoch": 47
}
```

---

## Kernel-Userspace Bridge

### Shared Memory for Large Data

For messages > 64KB, the kernel uses shared memory:

```
cell0d                              Kernel
   │                                  │
   │  1. Request SHM allocation       │
   ├─────────────────────────────────►│
   │                                  │
   │  2. SHM ID returned              │
   │◄─────────────────────────────────┤
   │                                  │
   │  3. Write data to SHM            │
   ├─────────────────────────────────►│
   │                                  │
   │  4. Send event (reference SHM)   │
   ├─────────────────────────────────►│
   │                                  │
   │  5. Kernel reads from SHM        │
   │                                  │
   │  6. Free SHM                     │
   ├─────────────────────────────────►│
```

### Message Verification

All kernel messages are verified:

1. **Magic bytes:** Must be "SYP\0"
2. **Version:** Must match expected version
3. **Checksum:** CRC32 of payload
4. **Timestamp:** Must be within 30s of current time

---

## Kernel-Enforced Security

### System Call Verification

All system calls go through the kernel:

```
Agent Request
     │
     ▼
┌─────────────────┐
│  Kernel Bridge  │
└────────┬────────┘
         │
         ▼
┌─────────────────┐     ┌─────────────────┐
│ Security Check  │────►│ Allowed?        │
│  - Valid agent  │     │  Yes → Execute  │
│  - Valid call   │     │  No  → Deny     │
│  - Permissions  │     └─────────────────┘
└─────────────────┘
```

### Allowed System Calls

| Syscall          | Description              | Permission Required |
|------------------|--------------------------|---------------------|
| sys_read         | Read from file/socket    | IO_CAP              |
| sys_write        | Write to file/socket     | IO_CAP              |
| sys_mmap         | Map memory               | MEM_CAP             |
| sys_clone        | Create thread/process    | PROC_CAP            |
| mcic_event_send  | Send kernel event        | EVENT_CAP           |
| mcic_agent_spawn | Spawn new agent          | ADMIN_CAP           |

### Memory Protection

```rust
// Kernel memory management
pub struct MemoryManager {
    allocations: Map<AgentId, Region>,
    total_memory: usize,
    used_memory: usize,
}

impl MemoryManager {
    pub fn allocate(&mut self, agent: AgentId, size: usize) -> Result<Region, Error> {
        // Check quota
        if self.used_memory + size > self.total_memory {
            return Err(Error::OutOfMemory);
        }
        
        // Check agent limit
        if self.agent_usage(agent) + size > AGENT_MEMORY_LIMIT {
            return Err(Error::QuotaExceeded);
        }
        
        // Allocate with guard pages
        let region = unsafe { alloc_with_guard_pages(size) }?;
        self.allocations.insert(agent, region);
        
        Ok(region)
    }
}
```

### Process Isolation

Agents are isolated using:

1. **Separate memory spaces:** Each agent has isolated heap
2. **Capability tokens:** Agents only have granted capabilities
3. **Syscall filtering:** Unauthorized calls are blocked
4. **Resource quotas:** CPU/memory limits per agent

---

## Kernel Status UI

The kernel monitor provides real-time visibility:

### Metrics Displayed

| Metric | Description | Update Frequency |
|--------|-------------|------------------|
| State | Kernel operational state | Real-time |
| Uptime | Time since kernel start | 1 second |
| Messages/sec | Event throughput | 5 seconds |
| Active Agents | Number of running agents | Real-time |
| Memory Usage | RAM consumption | 10 seconds |
| CPU Usage | Processor utilization | 5 seconds |
| OC Status | Orientational continuity | Real-time |
| Caps Epoch | Current epoch | On change |

### Throughput Graph

```
Message Throughput (last 60s)

  50 msg/s ██████████████
           ██████████████
  25 msg/s ██████████████ ████
           ██████████████ ████ ██████
   0 msg/s ██████████████ ████ ██████ ████
```

---

## Files and Components

### Core Files

| File | Purpose |
|------|---------|
| `~/cell0/service/cell0d.py` | Main daemon - requires kernel |
| `~/cell0/service/mcic_manager.py` | Kernel lifecycle manager |
| `~/cell0/engine/mcic_bridge.py` | SYFPASS protocol bridge |
| `~/cell0/gui/kernel_monitor.py` | Real-time status UI |

### Kernel Files

| File | Purpose |
|------|---------|
| `~/cell0/kernel/src/main.rs` | Kernel entry point |
| `~/cell0/kernel/src/lib.rs` | Kernel library |
| `~/cell0/kernel/src/sypas/` | SYFPASS implementation |
| `~/cell0/kernel/src/security/` | Security subsystem |
| `~/cell0/kernel/src/memory/` | Memory management |
| `~/cell0/kernel/src/userspace/kernel_simulator.py` | Userspace simulator |

### Configuration

| Setting | Default | Description |
|---------|---------|-------------|
| `MCIC_MODE` | `container` | Kernel execution mode |
| `MCIC_MANDATORY` | `true` | Require kernel to start |
| `MCIC_AUTO_BUILD` | `true` | Auto-build if missing |
| `MCIC_AUTO_START` | `true` | Auto-start kernel |
| `MCIC_SOCKET_PATH` | `~/.cell0/mcic.sock` | Unix socket path |
| `MCIC_MAX_RETRY` | `10` | Max reconnection attempts |
| `MCIC_RETRY_DELAY` | `1.0` | Initial retry delay (seconds) |

---

## Error Handling

### Fatal Errors (when mandatory=True)

| Error Code | Cause | Recovery |
|------------|-------|----------|
| KERNEL_NOT_FOUND | Binary missing | Build kernel with cargo |
| KERNEL_START_FAILED | QEMU/container failed | Check logs |
| KERNEL_CONNECT_FAILED | Socket connection failed | Check if running |
| NOT_INITIALIZED | Manager not initialized | Call initialize() |

### Non-Fatal Warnings

| Warning | Cause | Action |
|---------|-------|--------|
| Connection lost | Kernel restart | Auto-reconnect |
| High latency | Kernel overloaded | Backoff |
| Stale heartbeat | Network issue | Health check |

---

## Testing

### Test Scenarios

1. **Kernel not installed:**
   ```bash
   rm -rf ~/cell0/kernel/target
   python ~/cell0/service/cell0d.py
   # Expected: ERROR - KERNEL_NOT_FOUND
   ```

2. **Kernel not running:**
   ```bash
   pkill -f mcic
   python ~/cell0/service/cell0d.py
   # Expected: Auto-start kernel
   ```

3. **Kernel crash during operation:**
   ```bash
   # Start cell0d
   pkill -f kernel_simulator
   # Expected: Reconnect with backoff
   ```

4. **Graceful without kernel:**
   ```python
   manager = MCICKernelManager(mandatory=False)
   await manager.initialize()  # Returns False, no error
   ```

---

## Migration from Optional to Mandatory

### Before (Optional Kernel)

```python
class Cell0Daemon:
    def __init__(self):
        self.mcic = MCICBridge()  # Might be None
        
    async def start(self):
        try:
            await self.mcic.connect()  # Optional
        except:
            pass  # Continue without kernel
```

### After (Mandatory Kernel)

```python
class Cell0Daemon:
    def __init__(self):
        self.mcic_manager = MCICKernelManager(mandatory=True)
        
    async def start(self):
        await self.mcic_manager.initialize()  # REQUIRED
        # Kernel guaranteed to be available
```

---

## Future Work

### Planned Enhancements

1. **Hardware Mode:** Native bare-metal execution
2. **Live Migration:** Move kernel between hosts
3. **Distributed Kernel:** Multi-node kernel federation
4. **Hardware Security:** TPM/TEE integration
5. **Kernel Updates:** Hot-patching without restart

### Research Areas

- Formal verification of kernel correctness
- Quantum-resistant cryptography
- Zero-knowledge proofs for agent identity
- Homomorphic encryption for shared memory

---

## References

- [Cell 0 OS README](../README.md)
- [SYFPASS Protocol Specification](./SYFPASS_PROTOCOL.md)
- [Kernel Security Model](./KERNEL_SECURITY.md)
- [Agent Lifecycle](./AGENT_LIFECYCLE.md)

---

**Document Version:** 1.0.0  
**Last Updated:** 2026-02-11  
**Maintainer:** Cell 0 Architecture Team
