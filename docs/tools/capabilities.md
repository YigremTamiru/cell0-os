# Agent Capabilities & Built-in Tools

Phase 6 of the Cell 0 OS integrated powerful systemic mutators directly into the Python Engine. These tools are automatically exposed to specific Agent Domains, allowing them to affect the physical and digital world.

All tools are wrapped via `src/tools/` in Node.js, ensuring that Agent execution runs exclusively through the local high-speed API Gateway.

## 1. Sandbox Bash Execution
- **Wrapper**: `src/tools/sandbox.ts`
- **Description**: Allows an Agent (like the `Code Weaver`) to write files, run compilers, and execute scripts securely.
- **Safety**: Bash execution is strictly jailed to the specific Agent's `~/.cell0/workspaces/<slug>/` isolated directory. A Node Agent cannot run `rm -rf /` against the host OS.

## 2. Live GUI Canvas
- **Wrapper**: `src/tools/canvas.ts`
- **Description**: Bridges Python's `cell0/gui/canvas_server.py`. Allows the `Image Muse` and `Design Nexus` agents to render HTML, CSS, React, or 3D graphics dynamically back to the Nerve Portal UI in real-time.

## 3. World Search
- **Wrapper**: `src/tools/web-search.ts`
- **Description**: Wraps the Python enhanced web-search module. Provides the Swarm with live access to DuckDuckGo, Wikipedia, and targeted web content scraping for RAG synthesis.

## 4. Temporal Cron (Scheduling)
- **Wrapper**: `src/tools/cron.ts`
- **Description**: Your Agents do not sleep. You can instruct the `Task Oracle` or `Finance Guardian` to check specific conditions every hour. This writes a persistence rule in `~/.cell0/runtime/cron/` which is natively monitored by the Node gateway.

## 5. Filesystem Workspace Access
- **Wrapper**: `src/tools/workspace.ts`
- **Description**: Grants Agents read/write access to their persistent storage blocks, distinct from their `.vec` (Vector Memory) files. Used for saving logs, generating PDFs, or persisting JSON data structures.
