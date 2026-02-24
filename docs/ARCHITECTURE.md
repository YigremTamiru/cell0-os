# Cell 0 OS Architecture

> **System design for the Cognitive Operating Layer — v1.3.0**

## Four-Layer Architecture Overview

Cell 0 OS is organized into four primary layers:

1. **Glassbox UI (Frontal Lobe)** — React-based Neural Glassbox served via the gateway portal (:18790)
2. **Node.js Gateway (Nervous System)** — WebSocket gateway (:18789, auto-selected if busy), portal (:18790), session persistence
3. **Python Intelligence + Meta-Agent (The Brain)** — COL orchestration with GoalManager (17 domains), EthicsConsensus (6 rules, JSONL audit log), and SelfImprovementEngine (5-minute OBSERVE→REFLECT→GOAL-SET→ACT→EVALUATE loop)
4. **Rust Kernel + Secure Sandbox (DNA)** — Immutable kernel policies, hardware-level sandbox enforcement

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           CELL 0 OS ARCHITECTURE                                 │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │           LAYER 1: GLASSBOX UI / FRONTAL LOBE (React)                    │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐ │   │
│  │  │   Discord   │  │  Telegram   │  │Neural Glassbx│  │  Chrome Ext     │ │   │
│  │  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘  └────────┬────────┘ │   │
│  └─────────┼────────────────┼────────────────┼──────────────────┼──────────┘   │
│            │                │                │                  │              │
│            └────────────────┴────────────────┴──────────────────┘              │
│                                   │                                            │
│                                   ▼                                            │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │         LAYER 2: NODE.JS GATEWAY / NERVOUS SYSTEM                        │   │
│  │           WebSocket :18789 (auto-selected) | Portal :18790               │   │
│  │                    Session persistence enabled                           │   │
│  │                         ┌─────────────┐                                  │   │
│  │                         │   Gateway   │                                  │   │
│  │                         │   Server    │                                  │   │
│  │                         └──────┬──────┘                                  │   │
│  └────────────────────────────────┼─────────────────────────────────────────┘   │
│                                   │                                            │
│                                   ▼                                            │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │      LAYER 3: PYTHON INTELLIGENCE + META-AGENT / THE BRAIN               │   │
│  │                                                                          │   │
│  │   ┌─────────────────────────────────────────────────────────────────┐   │   │
│  │   │                    COL Pipeline                                  │   │   │
│  │   │  ┌────────┐    ┌────────┐    ┌────────┐    ┌────────┐          │   │   │
│  │   │  │  STOP  │───▶│CLASSIFY│───▶│  LOAD  │───▶│ APPLY  │          │   │   │
│  │   │  └────────┘    └────────┘    └────────┘    └────────┘          │   │   │
│  │   │                      │                      │                   │   │   │
│  │   │                      ▼                      ▼                   │   │   │
│  │   │               ┌─────────────┐        ┌──────────┐              │   │   │
│  │   │               │Policy Check │        │Execute   │              │   │   │
│  │   │               └─────────────┘        └──────────┘              │   │   │
│  │   └─────────────────────────────────────────────────────────────────┘   │   │
│  │                                                                          │   │
│  │   ┌─────────────────────────────────────────────────────────────────┐   │   │
│  │   │                    Agent Lifecycle                               │   │   │
│  │   │  ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌─────────┐  │   │   │
│  │   │  │  Spawn   │───▶│Heartbeat │───▶│ Delegate │───▶│Terminate│  │   │   │
│  │   │  └──────────┘    └──────────┘    └──────────┘    └─────────┘  │   │   │
│  │   └─────────────────────────────────────────────────────────────────┘   │   │
│  │                                                                          │   │
│  │   ┌─────────────────────────────────────────────────────────────────┐   │   │
│  │   │              Meta-Agent: SelfImprovementEngine (5-min loop)      │   │   │
│  │   │  ┌─────────┐ ┌─────────┐ ┌──────────┐ ┌─────┐ ┌──────────┐   │   │   │
│  │   │  │ OBSERVE │▶│ REFLECT │▶│ GOAL-SET │▶│ ACT │▶│ EVALUATE │   │   │   │
│  │   │  └─────────┘ └─────────┘ └──────────┘ └─────┘ └──────────┘   │   │   │
│  │   │      GoalManager (17 domains)  |  EthicsConsensus (6 rules)    │   │   │
│  │   └─────────────────────────────────────────────────────────────────┘   │   │
│  │                                                                          │   │
│  └─────────────────────────────────────────────────────────────────────────┘   │
│                                   │                                            │
│                    ┌──────────────┼──────────────┐                            │
│                    │              │              │                            │
│                    ▼              ▼              ▼                            │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │                         SKILL LAYER                                      │   │
│  │  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐           │   │
│  │  │  read   │ │  write  │ │  edit   │ │  exec   │ │ browser │           │   │
│  │  └─────────┘ └─────────┘ └─────────┘ └─────────┘ └─────────┘           │   │
│  │  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐           │   │
│  │  │web_search│ │web_fetch│ │ message │ │   tts   │ │  nodes  │           │   │
│  │  └─────────┘ └─────────┘ └─────────┘ └─────────┘ └─────────┘           │   │
│  └─────────────────────────────────────────────────────────────────────────┘   │
│                                   │                                            │
│                                   ▼                                            │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │                        MEMORY LAYER                                      │   │
│  │  ┌──────────────────┐    ┌──────────────────┐    ┌─────────────────┐   │   │
│  │  │   Daily Notes    │    │   MEMORY.md      │    │  Session State  │   │   │
│  │  │  (YYYY-MM-DD.md) │    │ (Long-term mem)  │    │  (Runtime cache)│   │   │
│  │  └──────────────────┘    └──────────────────┘    └─────────────────┘   │   │
│  └─────────────────────────────────────────────────────────────────────────┘   │
│                                   │                                            │
│                                   ▼                                            │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │      LAYER 4: RUST KERNEL + SECURE SANDBOX / DNA                         │   │
│  │                  Immutable kernel policies                               │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐    │   │
│  │  │   Policy    │  │   Sandbox   │  │   Audit     │  │     1P      │    │   │
│  │  │   Engine    │  │   (Docker)  │  │    Log      │  │    Vault    │    │   │
│  │  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘    │   │
│  └─────────────────────────────────────────────────────────────────────────┘   │
│                                   │                                            │
│                                   ▼                                            │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │                       MODEL LAYER                                        │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐                      │   │
│  │  │    GPT-4    │  │    Claude   │  │    Kimi     │  + More...          │   │
│  │  │   OpenAI    │  │  Anthropic  │  │  Moonshot   │                      │   │
│  │  └─────────────┘  └─────────────┘  └─────────────┘                      │   │
│  └─────────────────────────────────────────────────────────────────────────┘   │
│                                                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

## Component Details

### Layer 1: Glassbox UI (Frontal Lobe)
React-based Neural Glassbox served via the gateway portal. Multiple entry points for user interaction:
- **Discord/Slack/Teams** - Team collaboration
- **Telegram/WhatsApp** - Mobile messaging
- **Web Chat** - Browser interface (native to Nerve Portal)
- **Chrome Extension** - Browser automation relay

### Layer 2: Node.js Gateway (Nervous System)
- WebSocket gateway on port **:18789** (with automatic port selection if the default is in use)
- Portal UI on port **:18790**
- Session persistence: gateway stores and restores session state across restarts
- Routes incoming requests from all 10 channel adapters
- Authentication, rate limiting, and request logging
- Exposes `cell0 channels` CLI command for channel management

### Layer 3: Python Intelligence + Meta-Agent (The Brain)
The core intelligence engine. Includes COL orchestration plus the self-improvement subsystem.

**COL Pipeline** — follows the **STOP → CLASSIFY → LOAD → APPLY → EXECUTE** pattern:
- **STOP:** Emergency halt and safety checks
- **CLASSIFY:** Intent classification and routing
- **LOAD:** Context and memory retrieval
- **APPLY:** Policy validation and command preparation
- **EXECUTE:** Skill invocation and result handling

**Meta-Agent: SelfImprovementEngine** (`src/agents/meta-agent.ts`) — 5-minute autonomous loop:
- **OBSERVE:** Collect system metrics and recent outcomes
- **REFLECT:** Analyze patterns and identify improvement areas
- **GOAL-SET:** Propose new goals via GoalManager
- **ACT:** Execute improvement actions within policy bounds
- **EVALUATE:** Measure outcomes and update goal states

**GoalManager** (`src/agents/goals.ts`):
- Manages 17 goal domains with JSON persistence
- Tracks goal state transitions and priority scoring

**EthicsConsensus** (`src/agents/ethics.ts`):
- Enforces 6 core ethical rules across all meta-agent actions
- Writes a JSONL audit log of every ethics evaluation

### Agent Lifecycle
Manages autonomous worker agents:
- **Spawn:** Create isolated sub-agents
- **Heartbeat:** Health monitoring
- **Delegate:** Task distribution
- **Terminate:** Cleanup and result aggregation

### Skill Layer
Extensible tool system:
- **Core:** read, write, edit, exec
- **Web:** browser, web_search, web_fetch
- **Communication:** message, tts
- **Device:** nodes, canvas
- **Custom:** User-defined skills

### Memory Layer
Three-tier memory system:
- **Daily Notes:** Session-scoped context
- **MEMORY.md:** Long-term curated knowledge
- **Session State:** Runtime cache

### Layer 4: Rust Kernel + Secure Sandbox (DNA)
Immutable kernel policies provide the foundation. Defense in depth:
- **Policy Engine:** Immutable command validation rules enforced at kernel level
- **Sandbox:** Docker containerization for sub-agent isolation
- **Audit Log:** Operation tracking (ethics audit in JSONL via EthicsConsensus)
- **1Password:** Credential management

### Model Layer
LLM provider abstraction:
- Multi-provider support
- Tier-based routing (Fast/Balanced/Power)
- Fallback mechanisms
- Cost optimization

## Channel Adapter Table

All 10 channel adapters are fully implemented (not stubs) as of v1.3.0.

| # | Channel | Adapter | Implementation Method | Status |
|---|---------|---------|----------------------|--------|
| 1 | WhatsApp | `src/channels/whatsapp.ts` | Baileys Web QR pairing | Implemented |
| 2 | Telegram | `src/channels/telegram.ts` | Native fetch (Bot API) | Implemented |
| 3 | Discord | `src/channels/discord.ts` | WebSocket Gateway API v10 | Implemented |
| 4 | Slack | `src/channels/slack.ts` | Socket Mode | Implemented |
| 5 | Signal | `src/channels/signal.ts` | signal-cli bridge | Implemented |
| 6 | Matrix | `src/channels/matrix.ts` | Client-Server API | Implemented |
| 7 | Google Chat | `src/channels/google-chat.ts` | Webhook | Implemented |
| 8 | MS Teams | `src/channels/msteams.ts` | Webhook | Implemented |
| 9 | BlueBubbles/iMessage | `src/channels/bluebubbles.ts` | Local server REST + WebSocket | Implemented |
| 10 | WebChat | `src/channels/webchat.ts` | Browser-native WebSocket | Implemented |

QR-based channels (WhatsApp) use `src/channels/setup/qr.ts` for credential pairing during first-time setup.

## Data Flow

```
User Request
     │
     ▼
┌─────────┐
│ Gateway │ ──▶ Authentication, Rate Limiting
└────┬────┘
     │
     ▼
┌─────────┐
│   COL   │ ──▶ Classify, Load Context, Apply Policies
└────┬────┘
     │
     ▼
┌─────────┐
│  Agent  │ ──▶ Spawn sub-agent (if needed)
└────┬────┘
     │
     ▼
┌─────────┐
│  Skill  │ ──▶ Execute tool
└────┬────┘
     │
     ▼
┌─────────┐
│  Memory │ ──▶ Update context
└────┬────┘
     │
     ▼
  Response
```

## Scalability Considerations

### Horizontal Scaling
- Gateway: Stateless, load-balancer ready
- Agents: Containerized, auto-scaling
- Memory: Shared storage (Redis/S3)

### Vertical Scaling
- Model tier selection based on task
- Caching for repeated operations
- Async processing for I/O-bound tasks

## Deployment Options

### Local (Development)
```
Gateway ──▶ COL ──▶ Skills ──▶ Local FS
              │
              └──▶ Local LLM (Ollama)
```

### Cloud (Production)
```
Load Balancer ──▶ Gateway Cluster ──▶ COL Instances
                                          │
                    ┌─────────────────────┼─────────────────────┐
                    │                     │                     │
                    ▼                     ▼                     ▼
              Skill Workers         Memory (Redis)        Model APIs
```

### Hybrid
```
On-Premise              │              Cloud
                        │
┌──────────────┐        │        ┌──────────────┐
│   Gateway    │◄───────┼───────►│   Gateway    │
└──────┬───────┘        │        └──────┬───────┘
       │                │               │
       ▼                │               ▼
┌──────────────┐        │        ┌──────────────┐
│ Local Skills │        │        │ Model APIs   │
│ (file, exec) │        │        │ (GPT-4, etc) │
└──────────────┘        │        └──────────────┘
```

## Performance Characteristics

| Component | P95 Latency | Throughput | Bottleneck |
|-----------|-------------|------------|------------|
| Gateway | < 10ms | 10K req/s | Network I/O |
| COL Classify | < 10ms | 5K ops/s | LLM call |
| Agent Spawn | < 100ms | 100/s | Container startup |
| Skill (file) | < 5ms | 10K ops/s | Disk I/O |
| Skill (web) | < 2s | 100/s | External API |
| Memory read | < 5ms | 50K ops/s | File system |

## Monitoring Points

```
┌─────────────────────────────────────────────────────────┐
│                    Metrics Pipeline                      │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  Gateway ──▶ Request count, latency, errors             │
│     │                                                   │
│  COL ──────▶ Classification accuracy, policy blocks     │
│     │                                                   │
│  Agents ───▶ Spawn rate, lifetime, success rate         │
│     │                                                   │
│  Skills ───▶ Invocation count, duration, errors         │
│     │                                                   │
│  Memory ───▶ Read/write latency, cache hit rate         │
│     │                                                   │
│  Models ───▶ Token usage, cost, latency                 │
│     │                                                   │
│     └──────▶ Prometheus/Grafana ──▶ Alerts              │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

## See Also

- [Benchmarks](./BENCHMARKS.md) - Performance data
- [Stability Matrix](./STABILITY_MATRIX.md) - Component maturity
- [KULLU.md](archive/KULLU.md) - COL protocol specification
