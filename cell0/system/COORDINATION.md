# Cell 0 OS Agent Swarm - Coordination Protocol

## Active Agents (5)

| Agent | Role | Focus | Status |
|-------|------|-------|--------|
| evolution | General | Full-system iteration | 🟢 Running |
| kernel-smith | Specialist | Rust kernel | 🟢 Active |
| daemon-forge | Specialist | Python services | 🟢 Active |
| test-harness | Specialist | QA/Testing | 🟢 Active |
| architect | Coordinator | Design/Integration | 🟢 Active |

## Communication Channels

### File-Based Coordination
- `.agent-messages/` - Broadcast messages between agents
- `system/status/` - Agent status files
  - `kernel-status.json` - Kernel agent status
  - `daemon-status.json` - Daemon agent status  
  - `test-status.json` - Test agent status
  - `architect-status.json` - Architect status

### Message Format
```json
{
  "from": "agent-name",
  "to": "all|agent-name",
  "type": "status|request|blocker|complete|design-decision",
  "timestamp": "ISO-8601",
  "content": {}
}
```

## Current Priorities (Updated: 2026-02-18)

### COMPLETED ✅
1. **DONE**: SYPAS protocol design - Architect completed v2.0 spec
2. **DONE**: IPC protocol specification - Unix socket + gRPC + Shared memory
3. **DONE**: Multi-node federation design - Raft-based consensus

### IN PROGRESS 🔄
1. **HIGH**: Kernel warning cleanup - kernel-smith working
2. **HIGH**: SYPAS protocol implementation - kernel-smith + daemon-forge
3. **MEDIUM**: MLX bridge implementation - daemon-forge

### UPCOMING 📋
1. **MEDIUM**: Test suite expansion - test-harness
2. **MEDIUM**: Python dependency fixes - daemon-forge
3. **LOW**: Performance optimization - all agents

## Design Decisions (Log)

### 2026-02-18
- **DECISION**: Kernel↔Daemon IPC will use hybrid approach
  - Primary: Unix Domain Sockets (low latency)
  - Secondary: gRPC (structured messages)
  - High-bandwidth: Shared memory (ring buffers)
  - Rationale: Combines best of all approaches

- **DECISION**: Multi-node federation uses C0R (Cell 0 Raft)
  - Modified Raft with BFT extensions
  - Tolerates f < n/3 Byzantine nodes
  - Supports observer nodes for read scaling
  - Geographic awareness for zone placement

- **DECISION**: SYPAS Protocol v2.0 specification finalized
  - 32-byte header with capability tokens
  - Message types cover all operations
  - Priority-based routing
  - Built-in security with attestation

## Architecture Deliverables

| Document | Status | Location |
|----------|--------|----------|
| IPC Protocol Spec | ✅ Complete | `docs/IPC_PROTOCOL_SPEC.md` |
| Federation Design | ✅ Complete | `docs/FEDERATION_DESIGN.md` |
| SYPAS Protocol | ✅ Complete | `docs/SYPAS_PROTOCOL.md` |

## Coordination Protocol

Every 3 minutes, each agent should:
1. Read all status files from `system/status/`
2. Detect conflicts between agents
3. Broadcast resolutions to `.agent-messages/`
4. Update own status file

### Conflict Resolution

| Conflict Type | Resolution |
|--------------|------------|
| Resource contention | Priority-based scheduling |
| Design disagreement | Architect has final say |
| API incompatibility | Version negotiation |
| Blocked dependencies | Dependency graph reordering |

## Autonomous Operation

Agents run continuously without human intervention.
Check status with: `cat system/status/*-status.json`

Last Updated: 2026-02-18 05:45 UTC
