# Rust Kernel Security Policies

The deepest layer of the Cell 0 OS is the compiled Rust Kernel (`cell0/kernel/src/lib.rs`). 

The Master Node Gateway (`src/kernel/loader.ts`) actively monitors the filesystem at `~/.cell0/kernel/policies/`.

## What is a Kernel Policy?

While the Python `Philosophy Engine` judges *morality* and *confidence*, the Rust Kernel measures **absolute architectural constraints**.

If a massive Agent Swarm mathematically determines that taking down a specific network port is required to complete its goal, the Philosophy Engine might fail to catch it (if the logic implies the port was malicious). 

The Rust Kernel, however, does not negotiate.

## The `policies/` Directory

Policies are immutable `.json` files signed by cryptographic hashes. 

```json
{
  "id": "NET_BLOCK_EXTERNAL",
  "constraint": "SOCKET_BIND",
  "port_range": [0, 1024],
  "action": "DENY",
  "cryptographic_signature": "0xDEADBEEF..."
}
```

If an Agent process via the Python daemon attempts to mutate the physical host via the Node Gateway, the Node Gateway first asks the Rust FFI (Foreign Function Interface): *"Is this allowed?"*

If the signature mismatches, or the action violates the strict binary condition, the entire execution pipeline `panic!`s and halts immediately, preserving the safety of the host machine.

*Note: Modifying a Kernel component requires absolute root authority and a manual cryptographic re-signing of the `.json` bundle.*
