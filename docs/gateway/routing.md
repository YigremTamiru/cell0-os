# The Intent Router

The **Domain Router** (`src/gateway/router.ts`) is the traffic controller of the Cell 0 OS asynchronous Gateway. 

Because we have 66 Pre-Configured Agent Specialists, deciding *who* should handle a user's prompt is a computationally sensitive task. The Gateway runs a near-instantaneous intent classification algorithm to execute this.

## 1. Explicit Routing
The fastest path to a specific agent is via explicit commands. If a user prefixes their message from any channel (WhatsApp, Discord, etc.) with a routing tag, the Gateway bypasses semantic scoring:
- `/social Send a tweet...` -> Routes directly to *X Weaver*.
- `/finance Check my port...` -> Routes directly to *Crypto Sentinel*.

## 2. Source-Based Routing
If no explicit tag is present, the Gateway inspects the origin of the message. 
- A message arriving via the `slack.ts` channel adapter is heavily weighted toward the `Productivity` domain (triggering the *Task Oracle* or *Calendar Sovereign*).
- A message arriving via `bluebubbles.ts` (iMessage) is weighted toward the `Social` domain.

## 3. Semantic Intent Scoring (Recognition Seeds)
If the prompt is highly ambiguous or arrives via the neutral WebChat portal, the Gateway passes the raw string to `col/classifier.py` across the IPC bridge.

The Python Orchestrator uses a light, ultra-fast RAG vector lookup (Recognition Seeds) to semantically score the intent against the 12 ontology domains. The highest scoring domain "wins" the prompt, and the Master Orchestrator wakes the corresponding Specialist in their isolated `/workspace/`.
