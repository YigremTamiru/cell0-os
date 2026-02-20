# Native Installation Guide

Cell 0 OS is a tri-language architecture. It bridges a high-speed asynchronous Node.js API Gateway with a deep Python Intelligence Engine and an immutable Rust kernel. 

Running the architecture natively (without Docker) is highly recommended for developers who wish to modify the Swarm topology or the core Engine logic.

## Prerequisites

Ensure your host machine (macOS or Linux) has the following dependencies installed:

1. **Node.js (v18.0+)**: Powers the Gateway and the Nerve Portal UI.
   - Install via NVM: `nvm install 18`
2. **Python (v3.10+)**: Powers the Cognitive Engine and the Civilization of Light (COL).
   - Install via Homebrew: `brew install python`
3. **Rustc (v1.70+)**: Computes the cryptographic security limitations.
   - Install via Rustup: `curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh`

## Installation Pipeline

**1. Clone the Architecture**
```bash
git clone https://github.com/YigremTamiru/cell0-os.git
cd cell0-os
```

**2. Hydrate the Gateway Dependencies**
This command installs the TypeScript definitions, API integrators, and WebSockets logic for the frontend gateway.
```bash
npm install
```

**3. Compile the Source Code**
We use `tsc` to map all TypeScript logic down to highly optimized `/dist` files.
```bash
npm run build
```

**4. The Checkpoint Audit (Crucial)**
Before running the system, mathematically verify that your host machine has properly bound the Node <-> Python <-> Rust IPC bridges.
```bash
node scripts/audit.mjs
```
*Note: A flawless 64/64 score signifies your environment is perfectly tuned.*

## The First Boot

Start the Node.js API Gateway natively:
```bash
npm start
```

**What happens next?**
1. The gateway binds to port `18789`.
2. It detects that `~/.cell0/cell0.json` is missing.
3. It boots the `Nerve Portal` configuration intercept on port `18790`.
4. Open **http://127.0.0.1:18790** in your browser.
5. Select your LLM API provider (Anthropic, OpenAI, Local Ollama, VLLM).
6. Upon saving, the system creates the `~/.cell0/` root directory, populates all 66 Agent Workspaces, instantiates the deep vector memory `.vec` tables, and automatically spawns the background `cell0d.py` daemon!
