# Cell 0 OS - Multi-Node Federation Design

## Overview

Cell 0 OS supports distributed operation across multiple nodes, forming a **federated cluster** that acts as a unified operating system. This enables:

- **Horizontal scaling** across multiple machines
- **High availability** with automatic failover
- **Geographic distribution** for edge computing
- **Resource pooling** (compute, storage, AI models)
- **Byzantine fault tolerance** for adversarial environments

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         FEDERATION LAYER                                     │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐ │
│  │   Cluster   │  │   Consensus │  │   Resource  │  │   Security          │ │
│  │   Manager   │  │   Engine    │  │   Scheduler │  │   (BFT Quorum)      │ │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘  └──────────┬──────────┘ │
└─────────┼────────────────┼────────────────┼────────────────────┼────────────┘
          │                │                │                    │
          └────────────────┴────────────────┴────────────────────┘
                             │
          ┌──────────────────┼──────────────────┐
          │                  │                  │
┌─────────▼─────────┐ ┌──────▼───────┐ ┌───────▼────────┐
│    Node Alpha     │ │  Node Beta   │ │   Node Gamma   │
│  ┌─────────────┐  │ │ ┌──────────┐ │ │  ┌──────────┐  │
│  │   Kernel    │  │ │ │  Kernel  │ │ │  │  Kernel  │  │
│  │  (Leader)   │  │ │ │ (Follower)│ │ │  │(Follower)│  │
│  └──────┬──────┘  │ │ └────┬─────┘ │ │  └────┬─────┘  │
│         │         │ │      │       │ │       │        │
│  ┌──────▼──────┐  │ │ ┌────▼────┐  │ │  ┌───▼────┐   │
│  │    Daemon   │  │ │ │  Daemon  │  │ │  │ Daemon  │   │
│  │   (cell0d)  │  │ │ │ (cell0d) │  │ │  │(cell0d) │   │
│  └─────────────┘  │ │ └─────────┘  │ │  └─────────┘   │
└───────────────────┘ └──────────────┘ └────────────────┘
```

---

## Node Types

### 1. Leader Node
- Coordinates cluster-wide operations
- Maintains authoritative state
- Handles consensus proposals
- Only one leader per cluster (per term)

### 2. Follower Nodes
- Replicate state from leader
- Participate in consensus voting
- Handle local agent execution
- Can be promoted to leader on failover

### 3. Observer Nodes
- Receive state updates (non-voting)
- For read-only access or geographic distribution
- Lower overhead than full followers

### 4. Edge Nodes
- Minimal resource footprint
- Partial state replication
- Designed for IoT/edge deployments

---

## Consensus Protocol: Cell 0 Raft (C0R)

A modified Raft consensus optimized for Cell 0's requirements:

```rust
pub struct ConsensusState {
    /// Current term
    pub term: u64,
    
    /// Current role
    pub role: NodeRole,
    
    /// Leader for current term (if known)
    pub leader_id: Option<NodeId>,
    
    /// Voted for in current term
    pub voted_for: Option<NodeId>,
    
    /// Log of state machine commands
    pub log: Vec<LogEntry>,
    
    /// Commit index (highest log entry known committed)
    pub commit_index: u64,
    
    /// Last applied to state machine
    pub last_applied: u64,
    
    /// For leaders: next index to send each follower
    pub next_index: HashMap<NodeId, u64>,
    
    /// For leaders: highest match index for each follower
    pub match_index: HashMap<NodeId, u64>,
}

pub struct LogEntry {
    pub term: u64,
    pub index: u64,
    pub command: StateMachineCommand,
    pub timestamp: u64,
}

pub enum StateMachineCommand {
    AgentSpawn { agent_id: String, config: AgentConfig },
    AgentKill { agent_id: String },
    ResourceAlloc { agent_id: String, resources: Resources },
    ResourceFree { allocation_id: String },
    ConfigUpdate { key: String, value: Value },
    NodeJoin { node_id: NodeId, addr: SocketAddr },
    NodeLeave { node_id: NodeId },
}
```

### Consensus Flow

```
┌──────────────┐                    ┌──────────────┐
│    Client    │                    │    Leader    │
└──────┬───────┘                    └──────┬───────┘
       │                                   │
       │  1. Submit Command                │
       │──────────────────────────────────>│
       │                                   │
       │                    2. Append to Log
       │                                   │
       │  3. Replicate to Followers        │
       │     (AppendEntries RPC)           │
       │                                   │
┌──────▼───────┐                    ┌──────▼───────┐
│  Follower 1  │◄───────────────────│              │
└──────┬───────┘                    │              │
       │                            │              │
       │  4. Ack                    │              │
       │───────────────────────────>│              │
       │                            │              │
┌──────▼───────┐                    │              │
│  Follower 2  │◄───────────────────│              │
└──────┬───────┘                    │              │
       │                            │              │
       │  4. Ack                    │              │
       │───────────────────────────>│              │
       │                            │              │
       │         5. Commit (quorum reached)
       │                            │
       │         6. Apply to State Machine
       │                            │
       │  7. Response                 │
       │<─────────────────────────────│
```

### Modified for Cell 0

1. **Batched Commits**: Group multiple commands for efficiency
2. **Learner Nodes**: Non-voting observers for read scaling
3. **Geographic Awareness**: Prefer nearby nodes for replication
4. **Agent Affinity**: Keep agents on specific nodes when possible
5. **Fast Path**: Single-node commits for non-critical operations

---

## Federation State Machine

### Cluster State

```rust
pub struct ClusterState {
    /// Cluster configuration (nodes, roles)
    pub config: ClusterConfig,
    
    /// Node registry
    pub nodes: HashMap<NodeId, NodeInfo>,
    
    /// Agent registry (cluster-wide)
    pub agents: HashMap<AgentId, AgentPlacement>,
    
    /// Resource allocations
    pub allocations: HashMap<AllocationId, ResourceAllocation>,
    
    /// Current epoch (for fencing)
    pub epoch: u64,
    
    /// Configuration version
    pub config_version: u64,
}

pub struct NodeInfo {
    pub id: NodeId,
    pub role: NodeRole,
    pub addr: SocketAddr,
    pub capabilities: NodeCapabilities,
    pub resources: ResourceCapacity,
    pub status: NodeStatus,
    pub last_heartbeat: u64,
    pub joined_at: u64,
    pub zone: String,  // Availability zone
}

pub struct AgentPlacement {
    pub agent_id: AgentId,
    pub primary_node: NodeId,
    pub replica_nodes: Vec<NodeId>,
    pub state: AgentState,
    pub created_at: u64,
    pub last_migration: Option<u64>,
}

pub struct ResourceAllocation {
    pub id: AllocationId,
    pub owner: AgentId,
    pub resources: Resources,
    pub node: NodeId,
    pub created_at: u64,
    pub expires_at: Option<u64>,
}
```

### State Partitioning

To scale beyond single-node limits:

```
┌─────────────────────────────────────────────────────────────┐
│                    GLOBAL STATE (All Nodes)                  │
│  • Cluster membership                                        │
│  • Node topology                                             │
│  • Consensus log                                             │
│  • Configuration                                             │
└─────────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────────┐
│                    SHARDED STATE (Per Partition)             │
│  • Agent registry (by agent_id hash)                         │
│  • Resource allocations (by node)                            │
│  • TPV profiles (by user_id hash)                            │
└─────────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────────┐
│                    LOCAL STATE (Single Node)                 │
│  • Running agent processes                                   │
│  • Local cache                                               │
│  • Metrics                                                   │
└─────────────────────────────────────────────────────────────┘
```

---

## Network Topology

### Connection Mesh

```
              ┌──────────────┐
              │   Leader     │
              └──────┬───────┘
                     │
        ┌────────────┼────────────┐
        │            │            │
   ┌────▼────┐  ┌────▼────┐  ┌────▼────┐
   │Follower1│  │Follower2│  │Follower3│
   └────┬────┘  └────┬────┘  └────┬────┘
        │            │            │
        └────────────┼────────────┘
                     │
              ┌──────▼───────┐
              │  Observers   │
              └──────────────┘
```

- **Full Mesh**: All nodes connected to all others (small clusters < 10)
- **Hub-Spoke**: Leader-centric (medium clusters 10-50)
- **Gossip**: Epidemic broadcast (large clusters 50+)

### Geographic Distribution

```
┌──────────────────────────────────────────────────────────────┐
│                     GLOBAL CLUSTER                           │
│                                                              │
│   ┌──────────────────┐      ┌──────────────────┐            │
│   │   US-EAST Zone   │      │  EU-WEST Zone    │            │
│   │ ┌────┐  ┌────┐   │◄────►│ ┌────┐  ┌────┐   │            │
│   │ │ N1 │  │ N2 │   │      │ │ N3 │  │ N4 │   │            │
│   │ └──┬─┘  └─┬──┘   │      │ └─┬──┘  └──┬─┘   │            │
│   │    └──────┘      │      │   └────────┘     │            │
│   │    Leader        │      │   Follower       │            │
│   └──────────────────┘      └──────────────────┘            │
│                                                              │
│   ┌──────────────────┐                                       │
│   │  APAC-SOUTH Zone │                                       │
│   │     ┌────┐       │                                       │
│   │     │ N5 │       │                                       │
│   │     └────┘       │                                       │
│   │    Observer      │                                       │
│   └──────────────────┘                                       │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

- **Zone-aware Placement**: Prefer same-zone for latency
- **Cross-zone Replication**: Ensure availability
- **Latency Optimization**: Optimize for < 100ms within zone

---

## Security Model

### Threat Model

| Threat | Mitigation |
|--------|-----------|
| Compromised node | Quarantine via consensus, < n/3 tolerance |
| Network partition | Split-brain prevention via term fencing |
| Replay attacks | Nonces and timestamps in all messages |
| Man-in-the-middle | mTLS with mutual authentication |
| Sybil attacks | Proof-of-stake or permissioned join |
| Eclipse attacks | Bootstrap from multiple sources |

### Byzantine Fault Tolerance

```rust
pub struct BFTParams {
    /// Maximum Byzantine nodes tolerated
    pub max_byzantine: usize,
    
    /// Minimum nodes for consensus
    pub min_nodes: usize,
    
    /// Quorum size (2f + 1)
    pub quorum_size: usize,
}

impl BFTParams {
    pub fn for_node_count(n: usize) -> Self {
        let f = (n - 1) / 3;  // Max Byzantine
        Self {
            max_byzantine: f,
            min_nodes: 3 * f + 1,
            quorum_size: 2 * f + 1,
        }
    }
}

// Practical examples:
// n=4 → f=1, quorum=3  (minimum viable)
// n=7 → f=2, quorum=5  (production minimum)
// n=10 → f=3, quorum=7 (recommended)
```

### Node Authentication

```rust
pub struct NodeCredentials {
    /// Node identity (Ed25519 public key)
    pub node_id: NodeId,
    
    /// X.509 certificate
    pub certificate: X509Certificate,
    
    /// Attestation report (if TEE available)
    pub attestation: Option<AttestationReport>,
    
    /// Join token (from existing cluster member)
    pub join_token: JoinToken,
}

pub struct JoinToken {
    /// Token issuer
    pub issuer: NodeId,
    
    /// Token subject (new node)
    pub subject: NodeId,
    
    /// Validity period
    pub expires_at: u64,
    
    /// Permissions granted
    pub permissions: TokenPermissions,
    
    /// Issuer signature
    pub signature: Signature,
}
```

---

## Resource Scheduling

### Cluster-Wide Scheduler

```rust
pub struct FederatedScheduler {
    /// Global resource view
    pub resources: ClusterResources,
    
    /// Placement policies
    pub policies: Vec<Box<dyn PlacementPolicy>>,
    
    /// Queue of pending allocations
    pub pending: PriorityQueue<AllocationRequest>,
}

impl FederatedScheduler {
    /// Schedule agent on best node
    pub async fn schedule_agent(
        &mut self,
        requirements: ResourceRequirements,
        preferences: PlacementPreferences,
    ) -> Result<NodeId, SchedulingError> {
        // Filter available nodes
        let candidates: Vec<_> = self.resources
            .nodes()
            .filter(|n| n.available >= requirements)
            .filter(|n| n.status == NodeStatus::Healthy)
            .collect();
        
        // Apply placement policies
        let mut scores: Vec<_> = candidates
            .into_iter()
            .map(|node| {
                let score = self.policies
                    .iter()
                    .map(|p| p.score(&node, &requirements, &preferences))
                    .sum::<f64>();
                (score, node)
            })
            .collect();
        
        // Sort by score (descending)
        scores.sort_by(|a, b| b.0.partial_cmp(&a.0).unwrap());
        
        // Return best node
        scores.into_iter()
            .next()
            .map(|(_, node)| node.id)
            .ok_or(SchedulingError::NoCapacity)
    }
}

/// Placement policies
trait PlacementPolicy: Send + Sync {
    fn score(
        &self,
        node: &NodeResources,
        requirements: &ResourceRequirements,
        preferences: &PlacementPreferences,
    ) -> f64;
}

/// Prefer nodes with agent's data
struct DataLocalityPolicy;
impl PlacementPolicy for DataLocalityPolicy {
    fn score(&self, node: &NodeResources, req: &ResourceRequirements, _pref: &PlacementPreferences) -> f64 {
        if node.has_data(&req.required_data) {
            100.0
        } else {
            0.0
        }
    }
}

/// Prefer nodes in same zone
struct ZoneAffinityPolicy;
impl PlacementPolicy for ZoneAffinityPolicy {
    fn score(&self, node: &NodeResources, _req: &ResourceRequirements, pref: &PlacementPreferences) -> f64 {
        if node.zone == pref.preferred_zone {
            50.0
        } else {
            10.0
        }
    }
}

/// Load balancing across nodes
struct LoadBalancingPolicy;
impl PlacementPolicy for LoadBalancingPolicy {
    fn score(&self, node: &NodeResources, _req: &ResourceRequirements, _pref: &PlacementPreferences) -> f64 {
        // Prefer less loaded nodes
        let utilization = node.used.cpu as f64 / node.total.cpu as f64;
        (1.0 - utilization) * 100.0
    }
}
```

### Agent Migration

```rust
pub struct MigrationManager {
    /// Track ongoing migrations
    pub migrations: HashMap<AgentId, MigrationState>,
}

impl MigrationManager {
    /// Migrate agent to new node
    pub async fn migrate_agent(
        &mut self,
        agent_id: AgentId,
        target_node: NodeId,
    ) -> Result<(), MigrationError> {
        // 1. Pause agent (quiesce)
        self.pause_agent(agent_id).await?;
        
        // 2. Serialize agent state
        let state = self.serialize_agent(agent_id).await?;
        
        // 3. Transfer state to target
        self.transfer_state(agent_id, target_node, state).await?;
        
        // 4. Resume on target
        self.resume_agent(agent_id, target_node).await?;
        
        // 5. Update routing
        self.update_placement(agent_id, target_node).await?;
        
        // 6. Clean up source
        self.destroy_agent_source(agent_id).await?;
        
        Ok(())
    }
}
```

---

## Failure Handling

### Failure Detection

```rust
pub struct FailureDetector {
    /// Failure suspicion thresholds
    pub phi_threshold: f64,  // φ-accrual threshold
    
    /// Heartbeat history per node
    pub history: HashMap<NodeId, HeartbeatHistory>,
}

impl FailureDetector {
    /// Update with new heartbeat
    pub fn heartbeat(&mut self, node_id: NodeId, timestamp: u64) {
        let history = self.history.entry(node_id).or_default();
        history.add(timestamp);
    }
    
    /// Check if node is suspected failed
    pub fn is_suspected(&self, node_id: NodeId) -> bool {
        let history = self.history.get(&node_id)?;
        let phi = history.phi_score();
        phi > self.phi_threshold
    }
}
```

### Recovery Procedures

```
Node Failure Detected
        │
        ▼
┌───────────────┐
│ 1. Suspend    │
│    operations │
└───────┬───────┘
        │
        ▼
┌───────────────┐
├ 2. Leader     │◄── If leader failed, elect new leader
│    confirms   │
└───────┬───────┘
        │
        ▼
┌───────────────┐
│ 3. Reassign   │
│    agents     │
└───────┬───────┘
        │
        ▼
┌───────────────┐
│ 4. Recover    │
│    state      │
└───────┬───────┘
        │
        ▼
┌───────────────┐
│ 5. Resume     │
│    operations │
└───────────────┘
```

---

## API Endpoints

### Node Management

```python
# Join cluster
POST /federation/join
{
    "node_id": "abc123...",
    "address": "192.168.1.100:9000",
    "capabilities": ["compute", "storage"],
    "zone": "us-east-1a",
    "credentials": {...}
}

# Leave cluster
POST /federation/leave
{
    "node_id": "abc123...",
    "graceful": true
}

# Get cluster status
GET /federation/status
{
    "cluster_id": "cell0-cluster-1",
    "leader": "node-1",
    "nodes": [...],
    "health": "healthy",
    "epoch": 47
}
```

### Agent Federation

```python
# Deploy agent to cluster
POST /federation/agents
{
    "agent_type": "inference",
    "config": {...},
    "placement": {
        "preferred_zone": "us-east-1a",
        "replicas": 2
    }
}

# Migrate agent
POST /federation/agents/{agent_id}/migrate
{
    "target_node": "node-2",
    "strategy": "live"  # or "stop-start"
}

# List cluster-wide agents
GET /federation/agents
{
    "agents": [
        {
            "agent_id": "agent-1",
            "node": "node-1",
            "state": "running",
            "replicas": ["node-2"]
        }
    ]
}
```

---

## Configuration

```yaml
# /etc/cell0/federation.yaml

cluster:
  id: "production-cluster-1"
  name: "Primary Cell 0 Cluster"
  
node:
  id: null  # Auto-generate from key
  address: "0.0.0.0:9000"
  zone: "us-east-1a"
  
  role: "auto"  # auto, leader, follower, observer
  
  capabilities:
    compute:
      cpus: 32
      memory_gb: 256
      gpus: 4
    storage:
      local_gb: 2000
      nvme_gb: 4000

consensus:
  heartbeat_interval_ms: 100
  election_timeout_min_ms: 150
  election_timeout_max_ms: 300
  
  # BFT settings
  byzantine_tolerance: 2
  min_nodes: 7

federation:
  # Bootstrap nodes
  bootstrap:
    - "192.168.1.1:9000"
    - "192.168.1.2:9000"
  
  # Auto-join on startup
  auto_join: true
  
  # TLS settings
  tls:
    cert_file: "/etc/cell0/node.crt"
    key_file: "/etc/cell0/node.key"
    ca_file: "/etc/cell0/ca.crt"
  
  # Security
  require_attestation: true
  allow_untrusted_nodes: false
```

---

## Monitoring

### Cluster Metrics

| Metric | Description | Target |
|--------|-------------|--------|
| Consensus Latency | Time to commit | < 100ms (p99) |
| Leader Election | Time to elect new leader | < 1s |
| Replication Lag | Follower behind leader | < 10 entries |
| Migration Time | Agent migration duration | < 5s |
| Scheduler Latency | Time to place agent | < 50ms |
| Cross-zone Latency | Inter-zone round-trip | < 50ms |

### Health Checks

```python
class ClusterHealthChecker:
    async def check_cluster_health(self) -> ClusterHealth:
        checks = {
            'consensus': await self.check_consensus(),
            'replication': await self.check_replication(),
            'connectivity': await self.check_connectivity(),
            'capacity': await self.check_capacity(),
        }
        
        overall = HealthStatus.HEALTHY
        if any(c.status == HealthStatus.CRITICAL for c in checks.values()):
            overall = HealthStatus.CRITICAL
        elif any(c.status == HealthStatus.WARNING for c in checks.values()):
            overall = HealthStatus.WARNING
        
        return ClusterHealth(
            status=overall,
            checks=checks,
            timestamp=time.time()
        )
```

---

## Deployment Scenarios

### Single Node (Development)

```
┌─────────────────────┐
│      Node 1         │
│   (Leader only)     │
└─────────────────────┘
```

### 3-Node Cluster (Minimum HA)

```
┌──────────┐  ┌──────────┐  ┌──────────┐
│ Node 1   │  │ Node 2   │  │ Node 3   │
│ (Leader) │  │(Follower)│  │(Follower)│
└──────────┘  └──────────┘  └──────────┘
     ▲              ▲              ▲
     └──────────────┴──────────────┘
              Full mesh
```

Tolerates 1 node failure.

### 7-Node Production

```
              ┌─────────────┐
              │   Node 1    │
              │   Leader    │
              └──────┬──────┘
                     │
    ┌────────────────┼────────────────┐
    │                │                │
┌───▼───┐      ┌────▼────┐      ┌────▼────┐
│Node 2 │      │ Node 3  │      │ Node 4  │
│Follower│     │Follower │      │Follower │
└───┬───┘      └────┬────┘      └────┬────┘
    │               │                │
┌───▼───┐      ┌────▼────┐      ┌────▼────┐
│Node 5 │      │ Node 6  │      │ Node 7  │
│Observer│     │Observer │      │Observer │
└───────┘      └─────────┘      └─────────┘
```

Tolerates 2 Byzantine nodes, scales reads with observers.

### Geo-Distributed

```
┌──────────────────────────────────────────────────┐
│                 GLOBAL CLUSTER                   │
│                                                  │
│  ┌─────────────┐  ┌─────────────┐  ┌───────────┐ │
│  │  US-EAST    │  │  EU-WEST    │  │ APAC-EAST │ │
│  │  (Leader)   │  │ (Follower)  │  │(Follower) │ │
│  └──────┬──────┘  └──────┬──────┘  └─────┬─────┘ │
│         │                │               │       │
│         └────────────────┴───────────────┘       │
│                      WAN                         │
└──────────────────────────────────────────────────┘
```

---

## Future Enhancements

1. **Federated Learning**: Train models across nodes without centralizing data
2. **Homomorphic Encryption**: Compute on encrypted data across nodes
3. **Quantum-Resistant Consensus**: Post-quantum cryptographic primitives
4. **Auto-scaling**: Dynamic node addition/removal based on load
5. **Multi-cluster Federation**: Federation of federations

---

## References

- `docs/IPC_PROTOCOL_SPEC.md` - SYPAS protocol details
- `kernel/src/federation/` - Rust implementation
- `cell0/service/federation.py` - Python coordinator
- `docs/BYZANTINE_CONSENSUS.md` - BFT algorithms
