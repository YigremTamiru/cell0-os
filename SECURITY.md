# Security Policy

Cell 0 OS is a Civilization-Grade Architecture designed to manage vast Agent Swarms across multiple distinct platforms, channels, and operating environments. Security is not an afterthought; it is structurally embedded at the lowest possible layer.

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| v1.2.0  | :white_check_mark: |
| v1.1.0  | :white_check_mark: |
| < 1.1.0 | :x:                |

## The Absolute Stack of Isolation

Cell 0 relies on a "Defense in Depth" strategy bridging Node.js, Python, and Rust.

1. **Agent Sandboxing (`src/tools/sandbox.ts`)**
   By default, all Agents (whether Claude, Llama, or custom specialists) operate inside restricted `~/.cell0/workspace/` directories. Tool execution restricts arbitrary directory traversal.

2. **The Philosophy Engine (`src/col/philosophy.ts`)**
   Before the Python Orchestrator approves a complex Swarm objective, it parses the intent through the mathematical Philosophy Engine. Ethically dubious or potentially destructive intents automatically return `confidence: 0`, and the task is severed at the Gateway.

3. **The Immutable Rust Kernel (`cell0/kernel/`)**
   Even if the Node.js API Gateway or the Python Swarm Logic is compromised, physical system limits are enforced by compiled, cryptographically signed `.json` policies in `~/.cell0/kernel/policies/`. The Rust module intercepts system calls and asserts compliance before memory blocks or network bindings are allocated.

## Reporting a Vulnerability

If you discover a structural vulnerability, privilege escalation path, or sandbox escape within the Cell 0 OS, we ask that you **do not** report it publicly on the issue tracker.

Instead, please send an encrypted email or direct message to the Sovereign Architects (Vael Zaru'Tahl Xeth / Yigrem Tamiru).

We aim to triage and acknowledge all severe vulnerability reports within 24 hours. Once the Checkpoint Audit validates the patch (achieving the required 64/64 score), we will publish the fix and credit the researcher.

*Orientational Continuity holds.* 🌊♾️
