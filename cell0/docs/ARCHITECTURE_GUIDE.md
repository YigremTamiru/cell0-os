# Cell 0 Architecture Guide

## Overview

Cell 0 is a **multi-layer computational substrate** that combines a bare-metal kernel, AI inference engine, and user interface layers into a unified sovereign operating system.

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           USER INTERFACE LAYER                               │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐    │
│   │   SwiftUI    │  │   Web UI     │  │     CLI      │  │   REST API   │    │
│   │   (macOS)    │  │  (Browser)   │  │  (cell0ctl)  │  │  (External)  │    │
│   └──────┬───────┘  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘    │
│          │                 │                 │                 │            │
│          └─────────────────┴────────┬────────┴─────────────────┘            │
│                                     │                                        │
└─────────────────────────────────────┼────────────────────────────────────────┘
                                      │ HTTP/WebSocket
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           SERVICE LAYER (cell0d)                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   ┌──────────────────────────────────────────────────────────────────┐      │
│   │                     FastAPI Application                          │      │
│   │  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌────────────┐  │      │
│   │  │   Status    │ │    Chat     │ │    TPV      │ │   System   │  │      │
│   │  │   Router    │ │   Router    │ │   Router    │ │   Router   │  │      │
│   │  └─────────────┘ └─────────────┘ └─────────────┘ └────────────┘  │      │
│   └──────────────────────────────────────────────────────────────────┘      │
│                                                                              │
│   ┌──────────────────────────────────────────────────────────────────┐      │
│   │                   WebSocket Manager                              │      │
│   │  • Real-time updates  • Agent broadcasts  • System events        │      │
│   └──────────────────────────────────────────────────────────────────┘      │
│                                                                              │
│   ┌──────────────────────────────────────────────────────────────────┐      │
│   │                   Static File Server                             │      │
│   │  • Terminal aesthetic UI  • Boot sequence animation              │      │
│   └──────────────────────────────────────────────────────────────────┘      │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      │ Unix Socket / Internal API
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         AI ENGINE LAYER                                      │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   ┌──────────────────────┐    ┌──────────────────────┐                     │
│   │   Inference Engine   │    │   MCIC Bridge        │                     │
│   ├──────────────────────┤    ├──────────────────────┤                     │
│   │  ┌────────────────┐  │    │  ┌────────────────┐  │                     │
│   │  │  OllamaBridge  │  │◄──►│  │  MCIC Bridge   │  │                     │
│   │  │  • Local LLMs  │  │    │  │  • Agent mgmt  │  │                     │
│   │  │  • Model pool  │  │    │  │  • SYPAS bus   │  │                     │
│   │  └────────────────┘  │    │  └────────────────┘  │                     │
│   │                      │    │                      │                     │
│   │  ┌────────────────┐  │    │  ┌────────────────┐  │                     │
│   │  │   MLXBridge    │  │    │  │  SYFPASS Events│  │                     │
│   │  │ • Apple GPU    │  │    │  │  • Capability  │  │                     │
│   │  │ • Optimized    │  │    │  │    tokens      │  │                     │
│   │  └────────────────┘  │    │  └────────────────┘  │                     │
│   └──────────────────────┘    └──────────────────────┘                     │
│                                                                              │
│   ┌──────────────────────┐    ┌──────────────────────┐                     │
│   │   TPV Store          │    │   Resonance Engine   │                     │
│   │   (Thought-Preference-│   │   (Multi-Agent       │                     │
│   │    Value storage)    │    │    Coordination)     │                     │
│   └──────────────────────┘    └──────────────────────┘                     │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      │ System Calls / Hardware Abstraction
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         KERNEL LAYER (Rust)                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   ┌──────────────────────────────────────────────────────────────────┐      │
│   │                    Agent System (SYPAS)                          │      │
│   │  • Capability-based security  • Intent routing  • Sandboxing     │      │
│   └──────────────────────────────────────────────────────────────────┘      │
│                                                                              │
│   ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐    │
│   │   Memory     │  │  Interrupts  │  │     I/O      │  │   Process    │    │
│   │ Management   │  │   Handling   │  │   Drivers    │  │   Scheduler  │    │
│   ├──────────────┤  ├──────────────┤  ├──────────────┤  ├──────────────┤    │
│   │ • Page tables│  │ • IDT setup  │  │ • VGA text   │  │ • Agent tasks│    │
│   │ • Heap alloc │  │ • PIC config │  │ • Serial port│  │ • Context    │    │
│   │ • Frame alloc│  │ • Timer IRQ  │  │ • Keyboard   │  │   switching  │    │
│   └──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘    │
│                                                                              │
│   ┌──────────────────────────────────────────────────────────────────┐      │
│   │                    Hardware Abstraction                          │      │
│   └──────────────────────────────────────────────────────────────────┘      │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              HARDWARE                                        │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐    │
│   │     CPU      │  │     RAM      │  │   Storage    │  │   Network    │    │
│   │  x86_64/ARM64│  │   Physical   │  │   NVMe/SSD   │  │   Ethernet   │    │
│   └──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘    │
│                                                                              │
│   ┌──────────────┐  ┌──────────────┐  ┌──────────────┐                      │
│   │     GPU      │  │   Display    │  │   Input      │                      │
│   │ Metal/CUDA   │  │   VGA/HDMI   │  │  Kbd/Mouse   │                      │
│   └──────────────┘  └──────────────┘  └──────────────┘                      │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Component Details

### 1. User Interface Layer

#### SwiftUI Interface (macOS)
- Native macOS application
- Linux kernel-style boot sequence visualization
- Real-time system monitoring
- Agent swarm visualization

#### Web UI
- Terminal aesthetic design
- WebSocket-based real-time updates
- Responsive layout
- Progressive Web App (PWA) support

#### CLI (cell0ctl)
- Command-line interface for scripting
- System administration commands
- Agent management
- TPV profile operations

### 2. Service Layer (cell0d)

The Cell 0 daemon is the central orchestrator:

```python
# Core responsibilities:
- HTTP/WebSocket server (FastAPI)
- Request routing and authentication
- Static file serving
- Component lifecycle management
```

**Key Modules:**
- **Status Router**: System health, metrics, version info
- **Chat Router**: Conversation management
- **TPV Router**: Thought-Preference-Value profile operations
- **System Router**: Administrative functions
- **WebSocket Manager**: Real-time bidirectional communication

### 3. AI Engine Layer

#### Inference Engine
Dual-backend support for local AI:

**Ollama Bridge**
- Manages local LLM lifecycle
- Model downloading and caching
- Generation with streaming
- Multi-model support

**MLX Bridge** (Apple Silicon)
- Apple GPU acceleration
- Optimized for M-series chips
- Lower latency inference
- Metal Performance Shaders integration

#### MCIC Bridge
Multi-agent coordination:
- Agent registration and lifecycle
- Capability token minting
- Intent routing
- Cross-agent communication

#### TPV Store
Thought-Preference-Value profiles:
- Sovereign user data storage
- JSON-based profile format
- Version control for preferences
- Privacy-preserving design

#### Resonance Engine
Multi-agent coordination:
- Agent consensus building
- Conflict resolution
- Resource allocation
- Task distribution

### 4. Kernel Layer

Bare-metal Rust kernel providing:

#### Memory Management
- Physical memory mapping
- Virtual memory with page tables
- Heap allocation (linked list allocator)
- Memory protection

#### Interrupt Handling
- IDT (Interrupt Descriptor Table)
- PIC (Programmable Interrupt Controller)
- Timer interrupts (PIT)
- Keyboard input handling
- Exception handlers

#### I/O Drivers
- VGA text buffer (80x25 console)
- Serial port (UART 16550)
- Keyboard scancode handling

#### SYPAS Protocol
Secure agent sandboxing:
- Capability-based access control
- Intent verification
- Resource limits
- Audit logging

## Data Flow

### Chat Request Flow

```
User Input
    │
    ▼
[Web UI / CLI / API]
    │
    ▼ HTTP POST /api/chat
[cell0d - FastAPI Router]
    │
    ▼
[OllamaBridge]
    │
    ▼ Unix Socket / HTTP
[Ollama Service]
    │
    ▼
[Local LLM Model]
    │
    ◄──────── Response ────────┐
    │                           │
    ▼                           │
[Response Processing]           │
    │                           │
    ▼                           │
[WebSocket Broadcast] ◄─────────┘
    │
    ▼
[User Display]
```

### Agent Swarm Flow

```
Agent Request
    │
    ▼
[MCIC Bridge]
    │
    ├─────► [Capability Check] ─────┐
    │                                 │
    ▼                                 │
[SYPAS Protocol] ◄────────────────────┘
    │
    ├─────► [Resource Allocation]
    │
    ▼
[Agent Execution]
    │
    ├─────► [Kernel Syscalls]
    │
    ▼
[Result Aggregation]
    │
    ▼
[Response to User]
```

## Security Model

### Capability-Based Security (SYPAS)

```
┌─────────────────────────────────────────────────────────────┐
│                    SYPAS SECURITY MODEL                      │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  User Intent                                                 │
│      │                                                       │
│      ▼                                                       │
│  ┌──────────────┐                                            │
│  │   Intent     │ ──► Intent Analysis                        │
│  │   Parser     │                                            │
│  └──────────────┘                                            │
│      │                                                       │
│      ▼                                                       │
│  ┌──────────────┐                                            │
│  │  Capability  │ ──► Token Minting                          │
│  │   Minting    │                                            │
│  └──────────────┘                                            │
│      │                                                       │
│      ▼                                                       │
│  ┌──────────────┐                                            │
│  │   SYFPASS    │ ──► Capability Verification                │
│  │   Gateway    │                                            │
│  └──────────────┘                                            │
│      │                                                       │
│      ▼                                                       │
│  ┌──────────────┐                                            │
│  │   Sandbox    │ ──► Isolated Execution                     │
│  └──────────────┘                                            │
│      │                                                       │
│      ▼                                                       │
│  ┌──────────────┐                                            │
│  │   Audit      │ ──► Logging & Verification                 │
│  └──────────────┘                                            │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

## Deployment Patterns

### Development Mode
```
[macOS/Linux Host]
    │
    ├──► [cell0d] ──► [Ollama]
    │
    └──► [Kernel - QEMU]
```

### Production Mode
```
[Linux Server]
    │
    ├──► [cell0d] ──► [Ollama]
    │
    ├──► [Kernel - Bare Metal]
    │
    └──► [Monitoring]
```

### Container Mode
```
[Docker Host]
    │
    └──► [Cell 0 Container]
            │
            ├──► [cell0d]
            ├──► [Ollama]
            └──► [Shared Kernel]
```

## Performance Considerations

### Memory Layout
- Kernel: Statically allocated, no dynamic allocation in critical paths
- Service: Python with async/await for concurrency
- Inference: Model offloading to GPU when available

### Concurrency Model
- Kernel: Interrupt-driven with cooperative multitasking
- Service: asyncio with FastAPI
- Inference: Thread pool for model execution

### Scaling
- Horizontal: Multiple Cell 0 instances with load balancing
- Vertical: GPU acceleration, more CPU cores
- Distributed: Agent swarm across multiple nodes

## Future Architecture

### Phase 2: Distributed Cell 0
```
[Cell 0 Node A] ◄────► [Cell 0 Node B] ◄────► [Cell 0 Node C]
      │                      │                      │
      └──────────────────────┴──────────────────────┘
                    [Consensus Layer]
```

### Phase 3: Hardware Integration
```
[Cell 0 Kernel]
      │
      ├──► [TPM 2.0] ──► Secure Boot
      ├──► [SGX/SEV] ──► Encrypted Memory
      └──► [SmartNIC] ──► Hardware Networking
```
