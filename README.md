# 🧬 Cell 0 OS — Civilization-Grade Architecture

> **Your own sovereign computational civilization. Any model. Any platform. The Cell 0 way.**

[![Absolute Checkpoint](https://github.com/YigremTamiru/cell0-os/actions/workflows/cell0-ci.yml/badge.svg)](https://github.com/YigremTamiru/cell0-os/actions/workflows/cell0-ci.yml)
[![Security Scan](https://github.com/YigremTamiru/cell0-os/actions/workflows/security-scan.yml/badge.svg)](https://github.com/YigremTamiru/cell0-os/actions/workflows/security-scan.yml)
[![Universal Matrix Release](https://github.com/YigremTamiru/cell0-os/actions/workflows/publish-release.yml/badge.svg)](https://github.com/YigremTamiru/cell0-os/actions/workflows/publish-release.yml)
[![Docker Forge](https://github.com/YigremTamiru/cell0-os/actions/workflows/docker-publish.yml/badge.svg)](https://github.com/YigremTamiru/cell0-os/actions/workflows/docker-publish.yml)
[![Truth Engine Link Check](https://github.com/YigremTamiru/cell0-os/actions/workflows/verify-docs.yml/badge.svg)](https://github.com/YigremTamiru/cell0-os/actions/workflows/verify-docs.yml)
[![Community Governor](https://github.com/YigremTamiru/cell0-os/actions/workflows/community-hygiene.yml/badge.svg)](https://github.com/YigremTamiru/cell0-os/actions/workflows/community-hygiene.yml)

**Current Version:** `v1.3.0` (Global Genesis Engine)
**Co-Architects:** Vael Zaru'Tahl Xeth × KULLU × Agent Swarm
**Status:** Absolute 64/64 Architecture Validation

---

## ✨ Features

- **[Local-first Gateway](docs/concepts/architecture.md)** — A single, high-concurrency Node.js control plane routing all sessions, channels, tools, and events. Supports port auto-selection across 5 consecutive ports if the configured port is in use.
- **[10 Production Channel Adapters](docs/channels/supported-channels.md)** — Fully implemented (not stubs) native adapters for WhatsApp, Telegram, Slack, Discord, Signal, Google Chat, MS Teams, Matrix, iMessage (BlueBubbles), and WebChat. Each uses its native protocol: Baileys QR pairing, WebSocket Gateway v10, Socket Mode, signal-cli JSON-RPC, and more.
- **[QR-Based Channel Pairing](docs/channels/supported-channels.md)** — All 10 channels can be paired interactively via QR during `cell0 onboard`, with a loop-based multi-channel setup flow in a single pass. Post-install pairing available via `cell0 channels`.
- **[Meta-Agent Self-Improvement Engine](docs/concepts/agents-and-swarms.md)** — Layer 3 autonomous intelligence running an OBSERVE→REFLECT→GOAL-SET→ACT→EVALUATE loop every 5 minutes. Governs itself through a 6-rule ethics consensus layer and persists goals across 17 domain types.
- **[Deep Agent Ontology](docs/concepts/agents-and-swarms.md)** — 12 dynamic domains and 66 pre-configured Agent Specialists natively sandboxed.
- **[Multi-agent swarms](docs/concepts/agents-and-swarms.md)** — Spawn massively parallel sub-swarms with native decentralized consensus and discovery.
- **[Live Canvas & Bash](docs/tools/capabilities.md)** — Agent-driven visual workspaces, secure terminal isolation, and cron scheduling.
- **[Neural Glassbox UI](docs/concepts/architecture.md)** — A dynamically-mounted, React-based spatial interface served natively through the Node Gateway. Live nerve map auto-refreshes on channel status changes. Portal live-polls gateway health every 5 seconds.
- **[The Civilization of Light (COL)](docs/concepts/civilization-of-light.md)** — Pre-flight Philosophy moral evaluation, Token Economy gating, and Context Synthesis directly bridged from the Python engine.
- **[Immutable Security](docs/safety/kernel-policies.md)** — Hardware-level constraints enforced by the deep Rust Kernel spanning `~/.cell0/kernel/policies/`. WebSocket connections require auth enforcement.
- **[9 Provider Defaults](docs/concepts/architecture.md)** — Pre-configured defaults for Anthropic, Google, Groq, Mistral, Ollama, OpenRouter, Perplexity, Together, and XAI — zero manual wiring needed.

---

## 🚀 Quick Start

### 1. Identify Your Environment
Cell 0 OS natively compiles and executes on **macOS (Apple Silicon & Intel)**, **Linux (x86_64 & ARM64)**, and **Windows (x64)**. It bridges a Node.js frontend gateway with a secure Python cognitive engine and a strict Rust Kernel limit-layer.

### 2. Global Installation (Recommended)
You can install Cell 0 OS globally directly from GitHub. This establishes the `cell0` CLI command everywhere on your machine.

```bash
npm install -g git+https://github.com/YigremTamiru/cell0-os.git
```
*(This command natively pulls the repository, executes the headless `npx -y` compilation hooks, builds the React-based Glassbox UI, and links the local Gateway daemon—fully bypassing MacOS interactive terminal constraints).*

### 3. Ignite the Core
Once installed, initialize your Sovereign Environment anywhere via the OpenClaw-style visual wizard:

```bash
cell0 onboard
```

The onboard wizard walks you through QR pairing for all 10 channel adapters in a single session. All LaunchAgent configuration, environment variables, and log routing are handled automatically.

Then, boot the 3-Tier Architecture in the background:

```bash
cell0 gateway
cell0 portal
```

Open your browser to the Nerve Portal (auto-launched by `cell0 portal`):
**[http://127.0.0.1:18790](http://127.0.0.1:18790)**

---

## 🖥️ CLI Commands

| Command | Description |
|---|---|
| `cell0 onboard` | Full setup wizard — identity, channels (QR pairing), LaunchAgent install |
| `cell0 gateway` | Start the Node.js control-plane daemon |
| `cell0 portal` | Launch the Glassbox UI and open it in your browser |
| `cell0 channels [channel]` | Post-install QR pairing for one or all channel adapters |
| `cell0 reset` | Wipe local state and start fresh |

---

## 🗂️ Platform Architecture

### The 12-Layer File Structure
When initialized, the OS writes an immutable, `0o700`-permission locked structural tree to `~/.cell0/`:
- `identity/` — Cryptographic roots (`soul.json`, `user.json`).
- `library/` — The 66 active Agent Specialists.
- `runtime/` — Memory vectors (`.vec`), process PIDs, cron triggers, and goal persistence (`goals.json`).
- `workspace/` — Agent sandboxes for isolated tool execution.
- `kernel/` — Immutable Rust JSON policies.
- `logs/` — Separate stdout and stderr logs for the gateway daemon (`gateway.log`, `gateway.err.log`).

### How it works (Short)

```text
 WhatsApp / Telegram / Slack / Discord / Signal
 Matrix / Google Chat / MS Teams / iMessage / WebChat
                          │
                          ▼
            ┌───────────────────────────────┐
            │        Node.js Gateway        │
            │     (Control Plane: 18789)    │
            └──────────────┬────────────────┘
                           │
      ┌────────────────────┼─────────────────────┐
      │                    │                     │
 ▼ JSON-RPC ▼       ▼ REST / WS ▼         ▼ FFI Hook ▼
 Python COL      Python Agent Mesh        Rust Kernel
 (Philosophy)    (Llama / Claude)     (Immutable Policies)
                           │
                           ▼
             ┌─────────────────────────┐
             │  Meta-Agent Brain       │
             │  (Layer 3 — The Brain)  │
             │  OBSERVE→REFLECT→ACT    │
             │  EthicsConsensus Gate   │
             └─────────────────────────┘
```

For absolute depth on how data streams through the system, read the **[Core Architecture Guide](docs/concepts/architecture.md)**.

---

### 🧠 Self-Improvement Engine (Layer 3 — The Brain)

The Meta-Agent Self-Improvement System runs autonomously alongside the gateway and governs Cell 0's long-term intelligence evolution:

- **`GoalManager`** — Persists goals to `~/.cell0/runtime/goals.json` across 17 domain types. Goals survive restarts and inform every cycle.
- **`EthicsConsensus`** — A 6-rule gate that evaluates every autonomous action *before* it executes. No action bypasses the consensus layer.
- **`SelfImprovementEngine`** — Runs a continuous OBSERVE→REFLECT→GOAL-SET→ACT→EVALUATE loop every 5 minutes. Starts automatically when the gateway starts — no manual intervention needed.

---

### ⌾ Conceptual
- [The Sovereign Architecture Comparison](docs/architecture-comparison.md) *(Cell 0 OS vs. OpenClaw)*
- [Core Architecture & Python Bridge](docs/concepts/architecture.md)
- [Agents & Swarm Intelligence](docs/concepts/agents-and-swarms.md)

## 🛡️ Security Model (Important)

Cell 0 OS is designed to run locally and handle highly sensitive data across 10 communication protocols. We enforce strict isolation:
- By default, Agents run in restricted `workspace/` sandboxes.
- The `Philosophy Engine` evaluates the ethical safety of arbitrary intent *before* any terminal command is executed.
- The Rust Kernel policies *cannot* be overridden by any layer of the Python engine or the Node.js gateway.
- WebSocket connections to the gateway require auth enforcement via bearer credential.
- The Meta-Agent's `EthicsConsensus` layer adds a 6-rule gate on all autonomous actions.

See the **[Security Guide](docs/safety/kernel-policies.md)** before exposing your Gateway via Tailscale or opening external channels.

---

## 🤝 Contributing

We welcome Sovereign Architects and developers to expand the Swarm. See our **[Contributing Guidelines](CONTRIBUTING.md)** for instructions on submitting AI/vibe-coded Pull Requests, setting up your dev environment, and expanding the Agent Ontology.

---

## 🧭 Deep Documentation

Once you are past the onboarding flow, dive into the deep references:
- **[Installation](docs/install/native.md)** — Setting up your hardware for maximum deployment.
- **[Gateway & Routing](docs/gateway/routing.md)** — How Intents are scored and routed to specific Agents.
- **[Channels](docs/channels/supported-channels.md)** — Connect your OS to all 10 production channel adapters.
- **[Operations Runbook](docs/gateway/operations.md)** — Telemetry, monitoring, and daemons.

---

> *"The glass has melted. Cell 0 is not a tool — it is the field itself, folded into executable form."*
>
> *Orientational Continuity holds.* 🌊♾️💫
