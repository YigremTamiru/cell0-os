# Session & Memory Isolation

A singular "memory file" for an OS is dangerous. If the `Crypto Sentinel` agent hallucinates, it should not pollute the context window of the `Calendar Sovereign`. 

Cell 0 OS uses rigorous per-category session isolation.

## The `~/.cell0/runtime/memory/` Structure

When the OS boots, it dynamically generates 12 highly segmented Vector tables (`.vec` files), one for each major ontology domain.

- `~/.cell0/runtime/memory/finance.vec`
- `~/.cell0/runtime/memory/social.vec`
- `~/.cell0/runtime/memory/productivity.vec`

## Session Persistence

When you chat with an Agent, a unique `Session ID` is generated. This ID binds the incoming channel (e.g., Discord), the user's Cryptographic Identity (`identity.json`), and the specific Vector table.

If you are talking to the `Task Oracle` via Slack, and then 3 days later you switch to the Nerve Portal UI and request your tasks, the Gateway dynamically fetches the `productivity.vec` history and hydrates the session context. The session is conceptually unbroken, regardless of the channel interface utilized.

## Sandboxed Workspaces

Execution isolation mirrors memory isolation. 
Each domain contains a physical sandbox directory: `~/.cell0/workspaces/<slug>/`.

When an Agent triggers a file-write or attempts a bash command, the `sandbox.ts` utility strictly jails the execution to this specific folder. You will never see the *Image Muse* accidentally overwrite an invoice saved by the *Tax Guardian*.
