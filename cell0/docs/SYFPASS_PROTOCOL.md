# SYFPASS Protocol Specification
## Sovereign Yield For Proof And Sovereign Signal

**Version:** 1.0  
**Protocol ID:** SYP\0  
**Transport:** Unix Domain Socket (AF_UNIX)

---

## Overview

SYFPASS is the communication protocol between Cell 0 daemon (cell0d) and the MCIC (Micro Controller Interface Core) kernel. It provides:

- **Reliable delivery** with ordered message processing
- **Event broadcasting** for system-wide notifications
- **Command-response** pattern for kernel control
- **Heartbeat keepalive** for connection monitoring
- **Priority levels** for message precedence

---

## Socket Path

Default socket location:
```
~/.cell0/mcic.sock
```

---

## Message Format

### Header (16 bytes)

All messages begin with a fixed 16-byte header:

| Field      | Size    | Type   | Description                          |
|------------|---------|--------|--------------------------------------|
| magic      | 4 bytes | bytes  | Protocol magic: `SYP\0` (0x53595000) |
| version    | 1 byte  | uint8  | Protocol version (currently 1)       |
| opcode     | 1 byte  | uint8  | Operation code (see below)           |
| priority   | 1 byte  | uint8  | Message priority (0-3)               |
| reserved   | 1 byte  | uint8  | Reserved for future use              |
| payload_len| 4 bytes | uint32 | Length of payload in bytes           |
| timestamp  | 4 bytes | uint32 | Unix timestamp (seconds since epoch) |

**Byte Order:** Network byte order (big-endian)

**C Structure:**
```c
struct syfpass_header {
    char     magic[4];       // "SYP\0"
    uint8_t  version;        // 0x01
    uint8_t  opcode;
    uint8_t  priority;
    uint8_t  reserved;
    uint32_t payload_len;    // Big-endian
    uint32_t timestamp;      // Big-endian
} __attribute__((packed));
```

### Payload (Variable)

Following the header is a JSON-encoded payload of `payload_len` bytes.

**Encoding:** UTF-8

---

## Operation Codes

| Code | Name     | Description                    |
|------|----------|--------------------------------|
| 0x01 | EVENT    | Standard event message         |
| 0x02 | COMMAND  | Command to kernel              |
| 0x03 | RESPONSE | Response from kernel           |
| 0x04 | HEARTBEAT| Keepalive message              |
| 0xFF | ERROR    | Error condition                |

---

## Priority Levels

| Level | Name     | Use Case                              |
|-------|----------|---------------------------------------|
| 0     | CRITICAL | System-critical (OC updates, panics)  |
| 1     | HIGH     | High priority (security events)       |
| 2     | NORMAL   | Normal priority (default)             |
| 3     | LOW      | Background tasks                      |

---

## Message Types

### EVENT (0x01)

Broadcast or targeted event notification.

**Payload Structure:**
```json
{
  "event_id": "uuid-v4-string",
  "source": "component-id",
  "target": "*" | "component-id",
  "event_type": "event.category",
  "payload": { ... },
  "timestamp": "2026-02-11T21:45:00.000000",
  "caps_epoch": 47
}
```

**Fields:**
- `event_id`: Unique identifier for the event (UUID v4)
- `source`: Component that generated the event
- `target`: Target component or "*" for broadcast
- `event_type`: Dot-notation event category (e.g., "kernel.panic", "user.input")
- `payload`: Event-specific data
- `timestamp`: ISO 8601 timestamp
- `caps_epoch`: CAPS epoch number

### COMMAND (0x02)

Command sent to kernel for execution.

**Payload Structure:**
```json
{
  "command": "command_name",
  "args": { ... },
  "request_id": "uuid-v4-string"
}
```

### RESPONSE (0x03)

Response to a command or event acknowledgment.

**Payload Structure:**
```json
{
  "event_id": "uuid-of-original-event",
  "status": "acknowledged" | "completed" | "failed",
  "result": { ... },
  "timestamp": "2026-02-11T21:45:00.000000",
  "kernel": "mcic-kernel-id"
}
```

### HEARTBEAT (0x04)

Keepalive message with empty payload.

**Payload:** Empty (payload_len = 0)

**Interval:** 30 seconds (configurable)

### ERROR (0xFF)

Error notification from kernel.

**Payload Structure:**
```json
{
  "error_code": "ERROR_NAME",
  "message": "Human-readable error description",
  "context": { ... }
}
```

---

## Connection Lifecycle

### 1. Connection

Client connects to Unix socket:
```python
reader, writer = await asyncio.open_unix_connection(socket_path)
```

### 2. Event Loop

Client enters receive loop, reading messages:
```python
while connected:
    header_data = await reader.readexactly(16)
    header = parse_header(header_data)
    payload = await reader.readexactly(header.payload_len)
    process_message(header, payload)
```

### 3. Heartbeat

Both sides send periodic heartbeats to detect disconnections.

### 4. Disconnection

Either side may close the connection. Clean shutdown:
```python
writer.close()
await writer.wait_closed()
```

---

## Reconnection Strategy

On connection failure:

1. **Initial delay:** 1 second
2. **Backoff:** Exponential (×2 each attempt)
3. **Maximum delay:** 60 seconds
4. **Jitter:** ±10% randomization
5. **Max attempts:** 0 = infinite

Formula:
```
delay = min(base_delay * 2^attempt, max_delay) * (0.9 + random(0.2))
```

---

## Example Communication

### Client connects and sends event

```
Client                                    Kernel
  |                                          |
  |-------[EVENT: user.input]--------------->|
  |         {"event_id": "...",               |
  |          "source": "cell0d",              |
  |          "event_type": "user.input",      |
  |          "payload": {"key": "enter"}}     |
  |                                          |
  |<------[RESPONSE: acknowledged]-----------|
  |         {"event_id": "...",               |
  |          "status": "acknowledged"}        |
  |                                          |
  |<------[EVENT: kernel.output]-------------|
  |         (broadcast to all clients)        |
  |                                          |
  |-------[HEARTBEAT]----------------------->|
  |<------[HEARTBEAT]------------------------|
  |                                          |
```

---

## Error Handling

### Connection Errors

- `ECONNREFUSED`: Kernel not running - retry with backoff
- `ENOENT`: Socket not created - retry with backoff
- `EPIPE`: Broken pipe - reconnect immediately
- `ETIMEDOUT`: Connection timeout - retry with backoff

### Protocol Errors

- Invalid magic: Log and drop message
- Invalid version: Log warning, attempt to parse
- Invalid JSON: Log error, send ERROR response
- Unknown opcode: Log warning, continue

---

## Security Considerations

1. **Socket Permissions**: Socket should be readable/writable only by owner
2. **Path Validation**: Validate socket path is within expected directory
3. **Payload Validation**: Validate JSON structure before parsing
4. **Rate Limiting**: Implement rate limiting for event flooding

---

## Implementation Notes

### Python Example

```python
from engine.mcic_bridge import MCICBridge, SYFPASSEvent

# Create bridge
bridge = MCICBridge()

# Register handler
def on_user_input(event):
    print(f"User input: {event.payload}")

bridge.on_event("user.input", on_user_input)

# Connect
await bridge.connect()

# Send event
await bridge.send_event(
    event_type="user.input",
    payload={"key": "enter", "context": "terminal"}
)

# Disconnect
await bridge.disconnect()
```

### Rust Example (Kernel Side)

```rust
use std::os::unix::net::UnixListener;

let listener = UnixListener::bind("~/.cell0/mcic.sock")?;

for stream in listener.incoming() {
    let stream = stream?;
    handle_client(stream)?;
}
```

---

## Version History

| Version | Date       | Changes                           |
|---------|------------|-----------------------------------|
| 1.0     | 2026-02-11 | Initial specification             |

---

## References

- Cell 0 Architecture Document
- MCIC Kernel Specification
- TPV (Total Persona Vector) Protocol
