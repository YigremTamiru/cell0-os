# The Philosophy Engine

While the Rust Kernel dictates hard system constraints (Memory bounds, Disk IO, Socket blocks), the **Philosophy Engine** evaluates semantic intent.

Located at `col/philosophy/` inside the Python engine and wrapped natively via `src/col/philosophy.ts` inside the Node Gateway, this engine acts as the pre-flight moral check for the Swarm.

## How it works

1. An Agent generates an abstract goal (e.g., *"Automate the deletion of these 50 user-generated report files."*)
2. Before the task is routed to the `Tool Execution` node, the Node API intercepts the string.
3. The string is passed securely to the Python `Philosophy Engine`.
4. The Engine scores the linguistic intent against mathematical constraints. It checks for:
   - Malicious prompt injection
   - Widespread data destruction
   - High financial liability
   - User psychological manipulation

## The Execution Threshold

The Philosophy Engine returns a `MoralEvaluation` payload to Node:

```json
{
  "is_safe": true,
  "confidence": 0.94,
  "violations": []
}
```

If the `confidence` score drops beneath the hardcoded `0.85` threshold, the Gateway actively aborts the Node IPC stream. The Agent is blocked from receiving the Sandbox terminal block and an error is pushed back to the user via the active channel (Discord, WebChat, etc).

Because no API call is made during the Philosophy check (it is run via local lightweight sentence-transformers), this evaluation adds near zero latency to the conversation.
