# Agents & The Swarm Collective

Cell 0 OS ships with a profoundly deep Library Manifest detailing 12 ontological domains and **66 Pre-Configured Agent Specialists**.

## 1. The 12 Domains of Intelligence

All Agents live natively inside your `~/.cell0/library/` directory, isolated completely from one another to prevent prompt-bleed.
1. **Suggestions** (Urgent Priority, Cross-Domain Weaver)
2. **Recently Active** (Last-Used Memetic States)
3. **Social** (WhatsApp Mind, Telegram Nexus)
4. **Productivity** (Calendar Sovereign, Focus Keeper)
5. **Utilities** (System Monitor, Battery Oracle)
6. **Travel** (Map Navigator, Visa Sentinel)
7. **Finance** (Crypto Sentinel, Tax Guardian)
8. **Creativity** (Image Muse, 3D Modeler)
9. **Information & Reading** (Wikipedia Weaver, PDF Analyst)
10. **Entertainment** (Meme Generator, Gaming Nexus)
11. **Other** (Legacy App Bridge)
12. **Hidden** (Kernel Debugger)

## 2. Multi-Agent Swarms

Standard "LLM chains" are linear. Cell 0 Swarms are **parallel, decentralized, and infinitely scalable**.

When a task exceeds the cognitive threshold of a single Specialist, the Swarm Coordinator (`src/swarm/coordinator.ts`) dynamically spawns a localized intelligence array.

### Decentralized Consensus
Because LLMs hallucinate, Cell 0 Swarms utilize a mathematical peer-election algorithm. 

If you ask the OS to solve a complex coding task:
1. The Swarm Coordinator spins up 5 identical instances of the *Code Weaver* specialist.
2. All 5 instances solve the problem in isolation.
3. They use `swarm/consensus.py` to compare their results.
4. The system mathematically scores the highest-consensus branch and yields exactly one pristine output back to the user via the Node Gateway.

### Mesh Discovery
Using `swarm/discovery.py`, your local Cell 0 OS will continuously ping the local subnet (or your Tailscale VPN). If it detects another active Cell 0 Gateway (for instance, one running on your Mac and one running on your Linux server), their Swarms will interlink and share their collective compute processing power entirely automatically.
