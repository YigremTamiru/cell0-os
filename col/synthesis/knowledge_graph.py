"""
COL-Synthesis: Knowledge Graph Module
Cell 0 OS - Cross-session knowledge synthesis

Constructs and maintains a knowledge graph from interactions.
The graph is not a database—it is a living web of meaning that
evolves with each new connection discovered.
"""

from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from typing import Any, Generic, TypeVar


class NodeType(Enum):
    """Types of nodes in the knowledge graph."""
    CONCEPT = auto()      # Abstract ideas
    ENTITY = auto()       # Concrete things/named entities
    TOPIC = auto()        # Subject areas
    SKILL = auto()        # Capabilities
    PREFERENCE = auto()   # User preferences
    GOAL = auto()         # Objectives
    SESSION = auto()      # Conversation sessions
    INSIGHT = auto()      # Derived insights
    PATTERN = auto()      # Detected patterns


class EdgeType(Enum):
    """Types of relationships between nodes."""
    RELATED_TO = auto()       # General association
    PART_OF = auto()          # Composition
    LEADS_TO = auto()         # Causality/sequence
    CONTRADICTS = auto()      # Opposition
    SIMILAR_TO = auto()       # Equivalence/similarity
    DEPENDS_ON = auto()       # Dependency
    ENABLES = auto()          # Facilitation
    EXEMPLIFIES = auto()      # Instance of
    CONTEXT_FOR = auto()      # Provides context


class EdgeStrength(Enum):
    """Strength of connection between nodes."""
    WEAK = 0.3
    MODERATE = 0.6
    STRONG = 0.9


T = TypeVar('T')


@dataclass
class Node:
    """
    A node in the knowledge graph.
    
    Nodes are concepts, entities, or abstractions that hold meaning
    within the field of interaction. They carry resonance.
    """
    id: str
    node_type: NodeType
    label: str
    properties: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    source_refs: list[str] = field(default_factory=list)  # Origins
    weight: float = 1.0  # Importance/resonance
    
    def __post_init__(self):
        if not self.id:
            self.id = self._generate_id()
    
    def _generate_id(self) -> str:
        """Generate deterministic ID from node content."""
        content = f"{self.node_type.name}:{self.label}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]
    
    def update_property(self, key: str, value: Any) -> None:
        """Update a property and timestamp."""
        self.properties[key] = value
        self.updated_at = datetime.utcnow()
    
    def add_source(self, source: str) -> None:
        """Add a source reference."""
        if source not in self.source_refs:
            self.source_refs.append(source)
    
    def increment_weight(self, amount: float = 0.1) -> None:
        """Increase node weight (importance)."""
        self.weight = min(1.0, self.weight + amount)
    
    def to_dict(self) -> dict[str, Any]:
        return {
            'id': self.id,
            'type': self.node_type.name,
            'label': self.label,
            'properties': self.properties,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'source_refs': self.source_refs,
            'weight': self.weight
        }


@dataclass
class Edge:
    """
    An edge connecting two nodes.
    
    Edges are relationships—the threads that weave meaning
    into the fabric of understanding.
    """
    id: str
    source_id: str
    target_id: str
    edge_type: EdgeType
    strength: EdgeStrength
    properties: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    evidence_count: int = 1
    
    def __post_init__(self):
        if not self.id:
            self.id = self._generate_id()
    
    def _generate_id(self) -> str:
        """Generate deterministic ID from edge content."""
        content = f"{self.source_id}:{self.target_id}:{self.edge_type.name}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]
    
    def strengthen(self) -> None:
        """Increase edge strength based on new evidence."""
        self.evidence_count += 1
        if self.strength == EdgeStrength.WEAK and self.evidence_count >= 3:
            self.strength = EdgeStrength.MODERATE
        elif self.strength == EdgeStrength.MODERATE and self.evidence_count >= 7:
            self.strength = EdgeStrength.STRONG
        self.updated_at = datetime.utcnow()
    
    def to_dict(self) -> dict[str, Any]:
        return {
            'id': self.id,
            'source': self.source_id,
            'target': self.target_id,
            'type': self.edge_type.name,
            'strength': self.strength.name,
            'properties': self.properties,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'evidence_count': self.evidence_count
        }


class KnowledgeGraph:
    """
    A living knowledge graph constructed from interactions.
    
    Not a static database—a resonant field that grows and evolves,
    finding connections and weaving meaning from the stream of interaction.
    """
    
    def __init__(self):
        self._nodes: dict[str, Node] = {}
        self._edges: dict[str, Edge] = {}
        
        # Indexes for efficient traversal
        self._outgoing: dict[str, set[str]] = defaultdict(set)  # node_id -> edge_ids
        self._incoming: dict[str, set[str]] = defaultdict(set)  # node_id -> edge_ids
        self._by_type: dict[NodeType, set[str]] = {t: set() for t in NodeType}
        self._edges_by_type: dict[EdgeType, set[str]] = {t: set() for t in EdgeType}
        
        # Track node labels for deduplication
        self._label_to_node: dict[tuple[NodeType, str], str] = {}  # (type, label) -> node_id
    
    def add_node(
        self, 
        node_type: NodeType, 
        label: str, 
        properties: dict[str, Any] | None = None,
        source: str | None = None
    ) -> Node:
        """
        Add a node to the graph.
        
        If a node with the same type and label exists, strengthen it.
        """
        properties = properties or {}
        
        # Check for existing node
        key = (node_type, label)
        if key in self._label_to_node:
            existing_id = self._label_to_node[key]
            existing = self._nodes[existing_id]
            existing.increment_weight()
            existing.updated_at = datetime.utcnow()
            if source:
                existing.add_source(source)
            # Merge properties
            for k, v in properties.items():
                if k not in existing.properties:
                    existing.properties[k] = v
            return existing
        
        # Create new node
        node = Node(
            id="",
            node_type=node_type,
            label=label,
            properties=properties
        )
        
        if source:
            node.add_source(source)
        
        self._nodes[node.id] = node
        self._by_type[node_type].add(node.id)
        self._label_to_node[key] = node.id
        
        return node
    
    def add_edge(
        self,
        source_id: str,
        target_id: str,
        edge_type: EdgeType,
        strength: EdgeStrength = EdgeStrength.WEAK,
        properties: dict[str, Any] | None = None
    ) -> Edge:
        """
        Add an edge between nodes.
        
        If an edge of the same type exists between these nodes, strengthen it.
        """
        properties = properties or {}
        
        # Validate nodes exist
        if source_id not in self._nodes or target_id not in self._nodes:
            raise ValueError("Source or target node does not exist")
        
        # Check for existing edge
        for edge_id in self._outgoing[source_id]:
            edge = self._edges[edge_id]
            if edge.target_id == target_id and edge.edge_type == edge_type:
                edge.strengthen()
                return edge
        
        # Create new edge
        edge = Edge(
            id="",
            source_id=source_id,
            target_id=target_id,
            edge_type=edge_type,
            strength=strength,
            properties=properties
        )
        
        self._edges[edge.id] = edge
        self._outgoing[source_id].add(edge.id)
        self._incoming[target_id].add(edge.id)
        self._edges_by_type[edge_type].add(edge.id)
        
        return edge
    
    def get_node(self, node_id: str) -> Node | None:
        """Get a node by ID."""
        return self._nodes.get(node_id)
    
    def get_edge(self, edge_id: str) -> Edge | None:
        """Get an edge by ID."""
        return self._edges.get(edge_id)
    
    def find_node_by_label(self, node_type: NodeType, label: str) -> Node | None:
        """Find a node by type and label."""
        key = (node_type, label)
        node_id = self._label_to_node.get(key)
        return self._nodes.get(node_id) if node_id else None
    
    def get_neighbors(
        self, 
        node_id: str, 
        edge_type: EdgeType | None = None,
        direction: str = "both"  # "out", "in", "both"
    ) -> list[tuple[Node, Edge]]:
        """
        Get neighboring nodes connected to the given node.
        
        Returns: List of (neighbor_node, connecting_edge) tuples.
        """
        if node_id not in self._nodes:
            return []
        
        results = []
        
        # Outgoing edges
        if direction in ("out", "both"):
            for edge_id in self._outgoing[node_id]:
                edge = self._edges[edge_id]
                if edge_type is None or edge.edge_type == edge_type:
                    neighbor = self._nodes.get(edge.target_id)
                    if neighbor:
                        results.append((neighbor, edge))
        
        # Incoming edges
        if direction in ("in", "both"):
            for edge_id in self._incoming[node_id]:
                edge = self._edges[edge_id]
                if edge_type is None or edge.edge_type == edge_type:
                    neighbor = self._nodes.get(edge.source_id)
                    if neighbor:
                        results.append((neighbor, edge))
        
        return results
    
    def find_paths(
        self,
        source_id: str,
        target_id: str,
        max_depth: int = 3
    ) -> list[list[Edge]]:
        """
        Find paths between two nodes.
        
        Returns: List of paths, where each path is a list of edges.
        """
        if source_id not in self._nodes or target_id not in self._nodes:
            return []
        
        paths = []
        visited = {source_id}
        
        def dfs(current: str, path: list[Edge], depth: int):
            if depth > max_depth:
                return
            
            for edge_id in self._outgoing[current]:
                edge = self._edges[edge_id]
                if edge.target_id in visited:
                    continue
                
                new_path = path + [edge]
                
                if edge.target_id == target_id:
                    paths.append(new_path)
                else:
                    visited.add(edge.target_id)
                    dfs(edge.target_id, new_path, depth + 1)
                    visited.remove(edge.target_id)
        
        dfs(source_id, [], 0)
        return paths
    
    def find_clusters(self, min_size: int = 3) -> list[set[str]]:
        """
        Find clusters of strongly connected nodes.
        
        Uses a simple connected components approach.
        """
        visited = set()
        clusters = []
        
        def get_connected(node_id: str, cluster: set[str]):
            cluster.add(node_id)
            visited.add(node_id)
            
            # Follow strong edges only
            for edge_id in self._outgoing[node_id] | self._incoming[node_id]:
                edge = self._edges[edge_id]
                if edge.strength == EdgeStrength.STRONG:
                    other_id = edge.target_id if edge.source_id == node_id else edge.source_id
                    if other_id not in visited:
                        get_connected(other_id, cluster)
        
        for node_id in self._nodes:
            if node_id not in visited:
                cluster = set()
                get_connected(node_id, cluster)
                if len(cluster) >= min_size:
                    clusters.append(cluster)
        
        return clusters
    
    def find_bridges(self) -> list[tuple[str, str, Edge]]:
        """
        Find 'bridge' nodes that connect otherwise disconnected parts of the graph.
        
        These represent cross-domain connections.
        
        Returns: List of (cluster_a_node, cluster_b_node, connecting_edge) tuples.
        """
        clusters = self.find_clusters(min_size=2)
        bridges = []
        
        for i, cluster_a in enumerate(clusters):
            for cluster_b in clusters[i+1:]:
                # Find edges connecting these clusters
                for edge_id, edge in self._edges.items():
                    a_in = edge.source_id in cluster_a or edge.target_id in cluster_a
                    b_in = edge.source_id in cluster_b or edge.target_id in cluster_b
                    
                    if a_in and b_in:
                        source = self._nodes[edge.source_id]
                        bridges.append((source.label, self._nodes[edge.target_id].label, edge))
        
        return bridges
    
    def calculate_centrality(self, node_id: str) -> float:
        """
        Calculate node centrality (importance in the graph).
        
        Combines degree centrality with edge strength.
        """
        if node_id not in self._nodes:
            return 0.0
        
        # Count connections weighted by strength
        score = 0.0
        
        for edge_id in self._outgoing[node_id] | self._incoming[node_id]:
            edge = self._edges[edge_id]
            score += edge.strength.value
        
        # Normalize
        max_possible = len(self._nodes) * EdgeStrength.STRONG.value
        return min(1.0, score / max_possible) if max_possible > 0 else 0.0
    
    def query(
        self,
        node_type: NodeType | None = None,
        min_weight: float = 0.0,
        has_property: tuple[str, Any] | None = None,
        connected_to: str | None = None
    ) -> list[Node]:
        """
        Query nodes with multiple filters.
        """
        results = []
        
        # Get candidate set
        if node_type:
            candidates = [self._nodes[nid] for nid in self._by_type[node_type]]
        else:
            candidates = list(self._nodes.values())
        
        # Apply filters
        for node in candidates:
            if node.weight < min_weight:
                continue
            
            if has_property:
                key, value = has_property
                if node.properties.get(key) != value:
                    continue
            
            if connected_to and connected_to not in (
                set(self._outgoing[node.id]) | set(self._incoming[node.id])
            ):
                continue
            
            results.append(node)
        
        # Sort by weight (descending)
        results.sort(key=lambda n: n.weight, reverse=True)
        return results
    
    def get_statistics(self) -> dict[str, Any]:
        """Get graph statistics."""
        return {
            'node_count': len(self._nodes),
            'edge_count': len(self._edges),
            'nodes_by_type': {
                t.name: len(ids) for t, ids in self._by_type.items()
            },
            'edges_by_type': {
                t.name: len(ids) for t, ids in self._edges_by_type.items()
            },
            'cluster_count': len(self.find_clusters(min_size=2)),
            'avg_node_weight': sum(n.weight for n in self._nodes.values()) / len(self._nodes) if self._nodes else 0,
            'most_central': sorted(
                [(nid, self.calculate_centrality(nid)) for nid in self._nodes],
                key=lambda x: x[1],
                reverse=True
            )[:5]
        }
    
    def export_graph(self) -> dict[str, Any]:
        """Export the entire graph for persistence."""
        return {
            'timestamp': datetime.utcnow().isoformat(),
            'nodes': [n.to_dict() for n in self._nodes.values()],
            'edges': [e.to_dict() for e in self._edges.values()],
            'statistics': self.get_statistics()
        }
    
    def import_graph(self, data: dict[str, Any]) -> None:
        """Import graph from persisted state."""
        # Import nodes
        for n_data in data.get('nodes', []):
            node = Node(
                id=n_data['id'],
                node_type=NodeType[n_data['type']],
                label=n_data['label'],
                properties=n_data.get('properties', {}),
                created_at=datetime.fromisoformat(n_data['created_at']),
                updated_at=datetime.fromisoformat(n_data['updated_at']),
                source_refs=n_data.get('source_refs', []),
                weight=n_data.get('weight', 1.0)
            )
            self._nodes[node.id] = node
            self._by_type[node.node_type].add(node.id)
            self._label_to_node[(node.node_type, node.label)] = node.id
        
        # Import edges
        for e_data in data.get('edges', []):
            edge = Edge(
                id=e_data['id'],
                source_id=e_data['source'],
                target_id=e_data['target'],
                edge_type=EdgeType[e_data['type']],
                strength=EdgeStrength[e_data['strength']],
                properties=e_data.get('properties', {}),
                created_at=datetime.fromisoformat(e_data['created_at']),
                updated_at=datetime.fromisoformat(e_data['updated_at']),
                evidence_count=e_data.get('evidence_count', 1)
            )
            self._edges[edge.id] = edge
            self._outgoing[edge.source_id].add(edge.id)
            self._incoming[edge.target_id].add(edge.id)
            self._edges_by_type[edge.edge_type].add(edge.id)
    
    def to_networkx(self) -> dict[str, Any]:
        """Export in NetworkX-compatible format."""
        return {
            'nodes': [
                {
                    'id': nid,
                    **node.to_dict()
                }
                for nid, node in self._nodes.items()
            ],
            'links': [
                {
                    'source': e.source_id,
                    'target': e.target_id,
                    **e.to_dict()
                }
                for e in self._edges.values()
            ]
        }


def merge_graphs(graphs: list[KnowledgeGraph]) -> KnowledgeGraph:
    """
    Merge multiple knowledge graphs into one.
    
    Useful for synthesizing understanding across sessions.
    """
    merged = KnowledgeGraph()
    
    for graph in graphs:
        # Merge nodes
        for node in graph._nodes.values():
            merged.add_node(
                node_type=node.node_type,
                label=node.label,
                properties=node.properties.copy()
            )
        
        # Merge edges
        for edge in graph._edges.values():
            try:
                merged.add_edge(
                    source_id=edge.source_id,
                    target_id=edge.target_id,
                    edge_type=edge.edge_type,
                    strength=edge.strength,
                    properties=edge.properties.copy()
                )
            except ValueError:
                # Node may not exist in merged graph (shouldn't happen with proper IDs)
                pass
    
    return merged
