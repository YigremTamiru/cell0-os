# Core Architecture & Ecosystem

*“Cell 0 is an autonomous, post-quantum computational civilization.”*

Cell 0 OS natively solves the problem of "Language Fragmentation" in AI. The Node.js ecosystem is the undisputed king of asynchronous web scaling, while Python remains the undisputed sovereign of machine learning mathematics and Swarm logic.

We built a pristine native bridge between the two.

## 1. The Gateway (TypeScript / Node.js)

The Gateway is the hyper-concurrent frontal cortex. It executes on Port `18789`.
- **Purpose**: Manage the 11-Channel Router (WhatsApp, Slack, Discord), authenticate incoming webhook payloads via JWT/RBAC, and stream state telemetry back to the Nerve Portal.
- **Why Node.js?** Event-loop architecture. The Gateway never blocks. It takes inbound human text, parses the cryptographic token, packages the intent payload, and ships it via IPC. 

## 2. The Python Intelligence Engine (`cell0d.py`)

The Engine is the deep cognitive tissue. It executes invisibly in the background.
- **Purpose**: Calculate the Agent Ontology interactions, hold contextual state in vector arrays, compress logic flows (via Synthesis), and query the selected LLM (Claude/GPT/Llama).
- **The Bridge**: The Gateway (`src/agents/python-bridge.ts`) fires raw JSON-RPC commands down into the `cell0d` daemon.

## 3. The 51 Microservices Pipeline

Cell 0 OS does not rely on a monolithic function. 51 distinct, parallel microservices run simultaneously to process a single thought.

### The Lifecycle of a Prompt
1. **Reception**: A Discord message hits `src/channels/discord.ts`.
2. **Authentication**: `Security (Auth + JWT)` verifies the sender's UID against `identity.json`.
3. **Classification**: The string is sent over the JSON-RPC bridge to `col/classifier.py`. The intent is mathematically mapped.
4. **Routing**: The `Agent Router` directs the intent to the most optimal of the 66 active Specialists.
5. **Pre-flight Ethics**: `col/philosophy.py` parses the intended action sequence to prevent dangerous behavior.
6. **Execution**: The Agent activates a Phase 6 internal Node tool (e.g., `src/tools/sandbox.ts`) to mutate the physical computer filesystem.
7. **Synthesis Pipeline**: The results are compressed.
8. **Delivery**: The payload fires back up the Node stack to send the Discord reply.

## 4. The Immutable Kernel (Rust)

Below Node and Python lies the final frontier: the `~/.cell0/kernel/` security logic.
Even if a prompt-injection maliciously corrupts both the Node Gateway and the Python Daemon, the OS enforces cryptographically signed execution constraints via compiled Rust policy. Any attempt by an Agent to escape its designated `/workspace/` or initiate unauthorized `system.run` bash commands yields an immediate memory segmentation halt.
