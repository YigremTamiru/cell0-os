"""
Cell 0 OS - Agent Discovery Service
Handles dynamic agent discovery, registration, and network formation.
"""

import asyncio
import hashlib
import json
import random
import socket
import struct
import time
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Dict, List, Optional, Set, Tuple, Callable
import ipaddress


class DiscoveryMethod(Enum):
    """Agent discovery mechanisms."""
    MULTICAST = auto()
    GOSSIP = auto()
    DHT = auto()
    STATIC = auto()
    RELAY = auto()


@dataclass
class DiscoveryMessage:
    """Discovery protocol message."""
    msg_type: str  # PING, PONG, JOIN, LEAVE, GOSSIP
    sender_id: str
    sender_host: str
    sender_port: int
    capabilities: List[str] = field(default_factory=list)
    timestamp: float = field(default_factory=time.time)
    ttl: int = 5  # Gossip TTL
    signature: Optional[str] = None


@dataclass
class DiscoveredAgent:
    """Discovered agent information."""
    agent_id: str
    host: str
    port: int
    capabilities: List[str]
    first_seen: float
    last_seen: float
    discovery_method: DiscoveryMethod
    metadata: Dict[str, Any] = field(default_factory=dict)
    trust_score: float = 0.5


@dataclass
class NetworkTopology:
    """Network topology view."""
    agents: Dict[str, DiscoveredAgent] = field(default_factory=dict)
    connections: Dict[str, Set[str]] = field(default_factory=lambda: defaultdict(set))
    partitions: List[Set[str]] = field(default_factory=list)
    diameter: int = 0
    average_degree: float = 0.0


class MulticastDiscovery:
    """Multicast-based discovery for local network."""
    
    MULTICAST_GROUP = "239.255.42.99"  # Cell 0 multicast address
    MULTICAST_PORT = 19000
    
    def __init__(self, agent_id: str, host: str, port: int):
        self.agent_id = agent_id
        self.host = host
        self.port = port
        self.sock: Optional[socket.socket] = None
        self.running = False
        self.discovered_callback: Optional[Callable[[DiscoveredAgent], None]] = None
        
    def set_discovery_callback(self, callback: Callable[[DiscoveredAgent], None]):
        """Set callback for newly discovered agents."""
        self.discovered_callback = callback
        
    async def start(self):
        """Start multicast discovery."""
        self.running = True
        
        # Create multicast socket
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind(("", self.MULTICAST_PORT))
        
        # Join multicast group
        group = socket.inet_aton(self.MULTICAST_GROUP)
        mreq = struct.pack("4sL", group, socket.INADDR_ANY)
        self.sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
        
        self.sock.setblocking(False)
        
        # Start listening
        asyncio.create_task(self._listen_loop())
        
        # Start periodic announcements
        asyncio.create_task(self._announce_loop())
        
    async def stop(self):
        """Stop multicast discovery."""
        self.running = False
        if self.sock:
            self.sock.close()
            
    async def _listen_loop(self):
        """Listen for multicast messages."""
        loop = asyncio.get_event_loop()
        
        while self.running:
            try:
                data, addr = await loop.sock_recvfrom(self.sock, 2048)
                await self._handle_message(data, addr)
            except Exception as e:
                await asyncio.sleep(0.1)
                
    async def _handle_message(self, data: bytes, addr: Tuple[str, int]):
        """Handle incoming multicast message."""
        try:
            msg = json.loads(data.decode())
            
            if msg.get("sender_id") == self.agent_id:
                return  # Ignore self
                
            if msg.get("msg_type") == "PING":
                # Send PONG response
                await self._send_pong(addr[0], msg.get("sender_port", self.port))
            elif msg.get("msg_type") == "PONG":
                # New agent discovered
                agent = DiscoveredAgent(
                    agent_id=msg["sender_id"],
                    host=msg["sender_host"],
                    port=msg["sender_port"],
                    capabilities=msg.get("capabilities", []),
                    first_seen=time.time(),
                    last_seen=time.time(),
                    discovery_method=DiscoveryMethod.MULTICAST,
                    metadata=msg.get("metadata", {})
                )
                
                if self.discovered_callback:
                    self.discovered_callback(agent)
                    
        except json.JSONDecodeError:
            pass
            
    async def _announce_loop(self):
        """Periodically announce presence."""
        while self.running:
            await self._send_ping()
            await asyncio.sleep(5.0)  # Announce every 5 seconds
            
    async def _send_ping(self):
        """Send discovery ping."""
        msg = {
            "msg_type": "PING",
            "sender_id": self.agent_id,
            "sender_host": self.host,
            "sender_port": self.port,
            "capabilities": [],
            "timestamp": time.time()
        }
        
        try:
            self.sock.sendto(
                json.dumps(msg).encode(),
                (self.MULTICAST_GROUP, self.MULTICAST_PORT)
            )
        except Exception:
            pass
            
    async def _send_pong(self, target_host: str, target_port: int):
        """Send discovery pong."""
        msg = {
            "msg_type": "PONG",
            "sender_id": self.agent_id,
            "sender_host": self.host,
            "sender_port": self.port,
            "capabilities": [],
            "timestamp": time.time()
        }
        
        try:
            self.sock.sendto(
                json.dumps(msg).encode(),
                (target_host, target_port)
            )
        except Exception:
            pass


class GossipDiscovery:
    """
    Gossip protocol for large-scale discovery.
    
    Uses epidemic-style information dissemination for scalability.
    """
    
    GOSSIP_INTERVAL = 1.0  # seconds
    GOSSIP_FANOUT = 3
    MAX_GOSSIP_PEERS = 10
    
    def __init__(self, agent_id: str):
        self.agent_id = agent_id
        self.peers: Dict[str, DiscoveredAgent] = {}
        self.known_agents: Dict[str, DiscoveredAgent] = {}
        self.running = False
        self.gossip_callbacks: List[Callable[[str, Any], None]] = []
        
        # Gossip state
        self.version_vectors: Dict[str, int] = {}
        self.digest_log: Dict[str, Set[str]] = {}  # Agent -> known digests
        
    def add_peer(self, agent: DiscoveredAgent):
        """Add a gossip peer."""
        self.peers[agent.agent_id] = agent
        self.known_agents[agent.agent_id] = agent
        
    def remove_peer(self, agent_id: str):
        """Remove a gossip peer."""
        self.peers.pop(agent_id, None)
        
    def register_callback(self, callback: Callable[[str, Any], None]):
        """Register gossip event callback."""
        self.gossip_callbacks.append(callback)
        
    async def start(self):
        """Start gossip protocol."""
        self.running = True
        asyncio.create_task(self._gossip_loop())
        asyncio.create_task(self._anti_entropy_loop())
        
    async def stop(self):
        """Stop gossip protocol."""
        self.running = False
        
    async def _gossip_loop(self):
        """Main gossip dissemination loop."""
        while self.running:
            await asyncio.sleep(self.GOSSIP_INTERVAL)
            
            if not self.peers:
                continue
                
            # Select random peers
            selected = self._select_gossip_peers()
            
            for peer_id in selected:
                await self._send_gossip(peer_id)
                
    def _select_gossip_peers(self) -> List[str]:
        """Select peers for gossip round."""
        if len(self.peers) <= self.GOSSIP_FANOUT:
            return list(self.peers.keys())
            
        # Weighted random selection favoring recent peers
        peers_with_weights = []
        for pid, agent in self.peers.items():
            age = time.time() - agent.last_seen
            weight = 1.0 / (1 + age)
            peers_with_weights.append((pid, weight))
            
        total_weight = sum(w for _, w in peers_with_weights)
        selected = []
        
        for _ in range(min(self.GOSSIP_FANOUT, len(peers_with_weights))):
            if not peers_with_weights:
                break
                
            r = random.uniform(0, total_weight)
            cumulative = 0
            
            for i, (pid, weight) in enumerate(peers_with_weights):
                cumulative += weight
                if r <= cumulative:
                    selected.append(pid)
                    total_weight -= weight
                    peers_with_weights.pop(i)
                    break
                    
        return selected
        
    async def _send_gossip(self, peer_id: str):
        """Send gossip to a peer."""
        # Create gossip digest
        digest = self._create_digest()
        
        msg = {
            "type": "GOSSIP_DIGEST",
            "sender_id": self.agent_id,
            "digest": digest,
            "timestamp": time.time()
        }
        
        await self._emit_gossip_event("send", {"peer": peer_id, "msg": msg})
        
    async def _anti_entropy_loop(self):
        """Periodic anti-entropy for consistency."""
        while self.running:
            await asyncio.sleep(30.0)  # Every 30 seconds
            
            if not self.peers:
                continue
                
            # Perform full sync with random peer
            peer_id = random.choice(list(self.peers.keys()))
            await self._full_sync(peer_id)
            
    async def _full_sync(self, peer_id: str):
        """Perform full state synchronization."""
        msg = {
            "type": "FULL_SYNC_REQUEST",
            "sender_id": self.agent_id,
            "known_agents": list(self.known_agents.keys())
        }
        
        await self._emit_gossip_event("full_sync", {"peer": peer_id, "msg": msg})
        
    def _create_digest(self) -> Dict[str, Any]:
        """Create gossip digest of known agents."""
        return {
            "agent_count": len(self.known_agents),
            "version_vector": dict(self.version_vectors),
            "recently_updated": [
                aid for aid, agent in self.known_agents.items()
                if time.time() - agent.last_seen < 60
            ][:10]  # Last 10 updated
        }
        
    async def handle_gossip(self, sender_id: str, msg: Dict):
        """Handle incoming gossip message."""
        msg_type = msg.get("type")
        
        if msg_type == "GOSSIP_DIGEST":
            await self._handle_digest(sender_id, msg)
        elif msg_type == "AGENT_UPDATE":
            await self._handle_agent_update(msg)
        elif msg_type == "FULL_SYNC_REQUEST":
            await self._handle_sync_request(sender_id, msg)
        elif msg_type == "FULL_SYNC_RESPONSE":
            await self._handle_sync_response(msg)
            
    async def _handle_digest(self, sender_id: str, msg: Dict):
        """Handle gossip digest."""
        digest = msg.get("digest", {})
        
        # Check for agents we don't know about
        remote_count = digest.get("agent_count", 0)
        
        if remote_count > len(self.known_agents):
            # Request updates for unknown agents
            await self._request_agent_updates(sender_id)
            
    async def _handle_agent_update(self, msg: Dict):
        """Handle agent information update."""
        agent_data = msg.get("agent", {})
        agent_id = agent_data.get("agent_id")
        
        if not agent_id or agent_id == self.agent_id:
            return
            
        # Update or create agent record
        if agent_id in self.known_agents:
            agent = self.known_agents[agent_id]
            agent.last_seen = time.time()
            agent.metadata.update(agent_data.get("metadata", {}))
        else:
            agent = DiscoveredAgent(
                agent_id=agent_id,
                host=agent_data.get("host", "unknown"),
                port=agent_data.get("port", 0),
                capabilities=agent_data.get("capabilities", []),
                first_seen=time.time(),
                last_seen=time.time(),
                discovery_method=DiscoveryMethod.GOSSIP,
                metadata=agent_data.get("metadata", {})
            )
            self.known_agents[agent_id] = agent
            
        # Update version vector
        self.version_vectors[agent_id] = msg.get("version", 0)
        
    async def _request_agent_updates(self, peer_id: str):
        """Request agent updates from peer."""
        msg = {
            "type": "AGENT_UPDATE_REQUEST",
            "sender_id": self.agent_id,
            "known_agents": list(self.known_agents.keys())
        }
        
        await self._emit_gossip_event("request_update", {"peer": peer_id, "msg": msg})
        
    async def _handle_sync_request(self, sender_id: str, msg: Dict):
        """Handle full sync request."""
        known = set(msg.get("known_agents", []))
        
        # Find agents they don't know about
        unknown_to_them = [
            {"agent_id": aid, "host": a.host, "port": a.port,
             "capabilities": a.capabilities, "metadata": a.metadata}
            for aid, a in self.known_agents.items()
            if aid not in known and aid != sender_id
        ]
        
        response = {
            "type": "FULL_SYNC_RESPONSE",
            "sender_id": self.agent_id,
            "agents": unknown_to_them
        }
        
        await self._emit_gossip_event("sync_response", {"peer": sender_id, "msg": response})
        
    async def _handle_sync_response(self, msg: Dict):
        """Handle full sync response."""
        for agent_data in msg.get("agents", []):
            agent_id = agent_data.get("agent_id")
            if agent_id and agent_id not in self.known_agents:
                agent = DiscoveredAgent(
                    agent_id=agent_id,
                    host=agent_data.get("host", "unknown"),
                    port=agent_data.get("port", 0),
                    capabilities=agent_data.get("capabilities", []),
                    first_seen=time.time(),
                    last_seen=time.time(),
                    discovery_method=DiscoveryMethod.GOSSIP,
                    metadata=agent_data.get("metadata", {})
                )
                self.known_agents[agent_id] = agent
                
    async def _emit_gossip_event(self, event_type: str, data: Dict):
        """Emit gossip event."""
        for callback in self.gossip_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    asyncio.create_task(callback(event_type, data))
                else:
                    callback(event_type, data)
            except Exception:
                pass
                
    def get_known_agents(self) -> Dict[str, DiscoveredAgent]:
        """Get all known agents."""
        return dict(self.known_agents)
        
    def get_network_topology(self) -> NetworkTopology:
        """Analyze network topology."""
        topology = NetworkTopology(agents=dict(self.known_agents))
        
        # Build connection graph
        for agent_id in self.known_agents:
            topology.connections[agent_id] = set()
            
        # Estimate connections based on gossip
        for agent_id in self.peers:
            if agent_id in topology.connections:
                topology.connections[agent_id].add(self.agent_id)
                topology.connections[self.agent_id].add(agent_id)
                
        # Calculate average degree
        if topology.connections:
            degrees = [len(conns) for conns in topology.connections.values()]
            topology.average_degree = sum(degrees) / len(degrees)
            
        return topology


class DHTDiscovery:
    """
    Distributed Hash Table based discovery.
    
    Uses Kademlia-style DHT for scalable agent location.
    """
    
    K_BUCKET_SIZE = 20
    ID_LENGTH = 160
    ALPHA = 3  # Parallelism parameter
    
    def __init__(self, agent_id: str, host: str, port: int):
        self.agent_id = agent_id
        self.host = host
        self.port = port
        self.node_id = self._hash_id(agent_id)
        
        # K-buckets (routing table)
        self.k_buckets: List[List[Dict]] = [[] for _ in range(self.ID_LENGTH)]
        
        # Storage
        self.storage: Dict[str, Any] = {}
        
        # Running state
        self.running = False
        
    def _hash_id(self, agent_id: str) -> int:
        """Hash agent ID to DHT key space."""
        return int(hashlib.sha1(agent_id.encode()).hexdigest(), 16)
        
    def _distance(self, node_a: int, node_b: int) -> int:
        """Calculate XOR distance between nodes."""
        return node_a ^ node_b
        
    def _bucket_index(self, node_id: int) -> int:
        """Find which k-bucket a node belongs to."""
        distance = self._distance(self.node_id, node_id)
        if distance == 0:
            return -1
        return distance.bit_length() - 1
        
    def add_node(self, node_id: str, host: str, port: int):
        """Add node to routing table."""
        nid = self._hash_id(node_id)
        bucket_idx = self._bucket_index(nid)
        
        if bucket_idx < 0:
            return
            
        bucket = self.k_buckets[bucket_idx]
        
        # Check if already in bucket
        for node in bucket:
            if node["node_id"] == node_id:
                node["last_seen"] = time.time()
                return
                
        # Add to bucket if not full
        if len(bucket) < self.K_BUCKET_SIZE:
            bucket.append({
                "node_id": node_id,
                "host": host,
                "port": port,
                "last_seen": time.time()
            })
        else:
            # Bucket full - ping oldest
            self._ping_oldest(bucket)
            
    def _ping_oldest(self, bucket: List[Dict]):
        """Ping oldest node in bucket to check if alive."""
        if not bucket:
            return
            
        oldest = min(bucket, key=lambda n: n["last_seen"])
        # Would send actual ping here
        oldest["last_seen"] = time.time()
        
    async def find_node(self, target_id: str) -> List[Dict]:
        """Find closest nodes to target."""
        target = self._hash_id(target_id)
        
        # Get closest from local routing table
        all_nodes = []
        for bucket in self.k_buckets:
            all_nodes.extend(bucket)
            
        # Sort by distance
        all_nodes.sort(key=lambda n: self._distance(target, self._hash_id(n["node_id"])))
        
        return all_nodes[:self.K_BUCKET_SIZE]
        
    async def find_value(self, key: str) -> Optional[Any]:
        """Find value in DHT."""
        # Check local storage
        if key in self.storage:
            return self.storage[key]
            
        # Search network
        # Would perform iterative FIND_VALUE here
        return None
        
    async def store(self, key: str, value: Any):
        """Store value in DHT."""
        # Store locally
        self.storage[key] = value
        
        # Replicate to closest nodes
        closest = await self.find_node(key)
        for node in closest[:self.ALPHA]:
            if node["node_id"] != self.agent_id:
                await self._send_store(node, key, value)
                
    async def _send_store(self, node: Dict, key: str, value: Any):
        """Send STORE message to node."""
        # Would send actual message
        pass
        
    def bootstrap(self, bootstrap_nodes: List[Tuple[str, int]]):
        """Bootstrap DHT with known nodes."""
        for host, port in bootstrap_nodes:
            # Would perform actual bootstrap
            pass


class AgentDiscoveryService:
    """
    Unified agent discovery service.
    
    Combines multiple discovery methods for robust agent finding.
    """
    
    def __init__(self, agent_id: str, host: str, port: int):
        self.agent_id = agent_id
        self.host = host
        self.port = port
        
        # Discovery methods
        self.multicast = MulticastDiscovery(agent_id, host, port)
        self.gossip = GossipDiscovery(agent_id)
        self.dht = DHTDiscovery(agent_id, host, port)
        
        # Unified agent registry
        self.discovered_agents: Dict[str, DiscoveredAgent] = {}
        self.agent_lock = asyncio.Lock()
        
        # Callbacks
        self.discovery_callbacks: List[Callable[[DiscoveredAgent], None]] = []
        
        # Setup callbacks
        self.multicast.set_discovery_callback(self._on_agent_discovered)
        self.gossip.register_callback(self._on_gossip_event)
        
        # Configuration
        self.enable_multicast = True
        self.enable_gossip = True
        self.enable_dht = True
        
    def on_agent_discovered(self, callback: Callable[[DiscoveredAgent], None]):
        """Register discovery callback."""
        self.discovery_callbacks.append(callback)
        
    async def start(self):
        """Start all discovery services."""
        if self.enable_multicast:
            await self.multicast.start()
        if self.enable_gossip:
            await self.gossip.start()
            
        # Start maintenance loop
        asyncio.create_task(self._maintenance_loop())
        
    async def stop(self):
        """Stop all discovery services."""
        if self.enable_multicast:
            await self.multicast.stop()
        if self.enable_gossip:
            await self.gossip.stop()
            
    async def _on_agent_discovered(self, agent: DiscoveredAgent):
        """Handle newly discovered agent."""
        async with self.agent_lock:
            # Check for existing
            if agent.agent_id in self.discovered_agents:
                existing = self.discovered_agents[agent.agent_id]
                existing.last_seen = time.time()
                
                # Merge capabilities
                for cap in agent.capabilities:
                    if cap not in existing.capabilities:
                        existing.capabilities.append(cap)
            else:
                self.discovered_agents[agent.agent_id] = agent
                
                # Add to gossip peers
                self.gossip.add_peer(agent)
                
        # Notify callbacks
        for callback in self.discovery_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    asyncio.create_task(callback(agent))
                else:
                    callback(agent)
            except Exception:
                pass
                
    async def _on_gossip_event(self, event_type: str, data: Dict):
        """Handle gossip events."""
        if event_type == "send":
            # Message sent
            pass
        elif event_type == "full_sync":
            # Full sync initiated
            pass
            
    async def _maintenance_loop(self):
        """Periodic maintenance tasks."""
        while True:
            await asyncio.sleep(10.0)
            
            async with self.agent_lock:
                now = time.time()
                
                # Remove stale agents
                stale_threshold = 300  # 5 minutes
                stale = [
                    aid for aid, agent in self.discovered_agents.items()
                    if now - agent.last_seen > stale_threshold
                ]
                
                for aid in stale:
                    del self.discovered_agents[aid]
                    self.gossip.remove_peer(aid)
                    
    def get_discovered_agents(self) -> Dict[str, DiscoveredAgent]:
        """Get all discovered agents."""
        return dict(self.discovered_agents)
        
    def get_agent(self, agent_id: str) -> Optional[DiscoveredAgent]:
        """Get specific agent info."""
        return self.discovered_agents.get(agent_id)
        
    def find_agents_by_capability(self, capability: str) -> List[DiscoveredAgent]:
        """Find agents with specific capability."""
        return [
            agent for agent in self.discovered_agents.values()
            if capability in agent.capabilities
        ]
        
    def get_discovery_stats(self) -> Dict:
        """Get discovery statistics."""
        return {
            "total_discovered": len(self.discovered_agents),
            "multicast_enabled": self.enable_multicast,
            "gossip_enabled": self.enable_gossip,
            "dht_enabled": self.enable_dht,
            "gossip_peers": len(self.gossip.peers),
            "network_topology": {
                "average_degree": self.gossip.get_network_topology().average_degree
            }
        }
