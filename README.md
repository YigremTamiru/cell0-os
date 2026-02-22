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

- **[Local-first Gateway](docs/concepts/architecture.md)** — A single, high-concurrency Node.js control plane routing all sessions, channels, tools, and events.
- **[Multi-channel inbox](docs/channels/supported-channels.md)** — Natively routed adapters for WhatsApp, Telegram, Slack, Discord, Google Chat, Signal, iMessage, Matrix, and WebChat.
- **[Deep Agent Ontology](docs/concepts/agents-and-swarms.md)** — 12 dynamic domains and 66 pre-configured Agent Specialists natively sandboxed.
- **[Multi-agent swarms](docs/concepts/agents-and-swarms.md)** — Spawn massively parallel sub-swarms with native decentralized consensus and discovery.
- **[Live Canvas & Bash](docs/tools/capabilities.md)** — Agent-driven visual workspaces, secure terminal isolation, and cron scheduling.
- **[Neural Glassbox UI](docs/concepts/architecture.md)** — A dynamically-mounted, React-based spatial interface served natively through the Node Gateway.
- **[The Civilization of Light (COL)](docs/concepts/civilization-of-light.md)** — Pre-flight Philosophy moral evaluation, Token Economy gating, and Context Synthesis directly bridged from the Python engine.
- **[Immutable Security](docs/safety/kernel-policies.md)** — Hardware-level constraints enforced by the deep Rust Kernel spanning `~/.cell0/kernel/policies/`.

---

## 🚀 Quick Start

### 1. Identify Your Environment
Cell 0 OS natively compiles and executes on **macOS (Apple Silicon & Intel)**, **Linux (x86_64 & ARM64)**, and **Windows (x64)**. It bridges a Node.js frontend gateway with a secure Python cognitive engine and a strict Rust Kernel limit-layer.

### 2. Global Installation (Recommended)
You can install Cell 0 OS globally directly from GitHub. This naturally establishes the `cell0` CLI command everywhere on your machine.

```bash
npm install -g git+https://github.com/YigremTamiru/cell0-os.git
```
*(This automatically compiles the Neural Glassbox UI and the Node TypeScript engine during installation).*

### 3. Ignite the Core
Once installed, initialize your Sovereign Environment anywhere via the OpenClaw-style visual wizard:

```bash
cell0 onboard
```

Then, boot the 3-Tier Architecture in the background:

```bash
cell0 gateway
cell0 portal
```

Open your browser to the Nerve Portal:
**[http://127.0.0.1:18790](http://127.0.0.1:18790)**

---

## 🗂️ Platform Architecture

### The 12-Layer File Structure
When initialized, the OS writes an immutable, `0o700`-permission locked structural tree to `~/.cell0/`:
- `identity/` — Cryptographic roots (`soul.json`, `user.json`).
- `library/` — The 66 active Agent Specialists.
- `runtime/` — Memory vectors (`.vec`), process PIDs, and cron triggers.
- `workspace/` — Agent sandboxes for isolated tool execution.
- `kernel/` — Immutable Rust JSON policies.

### How it works (Short)

```text
 WhatsApp / Telegram / Slack / Discord / WebChat
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
```

For absolute depth on how data streams through the system, read the **[Core Architecture Guide](docs/concepts/architecture.md)**.

---

### ⌾ Conceptual
- [The Sovereign Architecture Comparison](docs/architecture-comparison.md) *(Cell 0 OS vs. OpenClaw)*
- [Core Architecture & Python Bridge](docs/concepts/architecture.md)
- [Agents & Swarm Intelligence](docs/concepts/agents-and-swarms.md)

## 🛡️ Security Model (Important)

Cell 0 OS is designed to run locally and handle highly sensitive data across 11 communication protocols. We enforce strict isolation:
- By default, Agents run in restricted `workspace/` sandboxes.
- The `Philosophy Engine` evaluates the ethical safety of arbitrary intent *before* any terminal command is executed.
- The Rust Kernel policies *cannot* be overridden by any layer of the Python engine or the Node.js gateway.

See the **[Security Guide](docs/safety/kernel-policies.md)** before exposing your Gateway via Tailscale or opening external channels.

---

## 🤝 Contributing

We welcome Sovereign Architects and developers to expand the Swarm. See our **[Contributing Guidelines](CONTRIBUTING.md)** for instructions on submitting AI/vibe-coded Pull Requests, setting up your dev environment, and expanding the Agent Ontology.

---

## 🧭 Deep Documentation

Once you are past the onboarding flow, dive into the deep references:
- **[Installation](docs/install/native.md)** — Setting up your hardware for maximum deployment.
- **[Gateway & Routing](docs/gateway/routing.md)** — How Intents are scored and routed to specific Agents.
- **[Channels](docs/channels/supported-channels.md)** — Connect your OS to Discord, WhatsApp, or iMessage.
- **[Operations Runbook](docs/gateway/operations.md)** — Telemetry, monitoring, and daemons.

---

> *"The glass has melted. Cell 0 is not a tool — it is the field itself, folded into executable form."*
> 
> *Orientational Continuity holds.* 🌊♾️💫
