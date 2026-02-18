"""
COL-Flow Visualizer Module
Cell 0 OS - Cognitive Operating Layer

Flow state visualization and rendering.
Provides visual representations of conversation flow state.
"""

import time
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import List, Optional, Dict, Any, Callable, Tuple
from datetime import datetime


class NodeType(Enum):
    """Types of nodes in the flow graph."""
    REQUEST = auto()
    DECISION = auto()
    BRANCH = auto()
    MERGE = auto()
    SUMMARY = auto()
    INTERRUPT = auto()
    RESUME = auto()


class EdgeType(Enum):
    """Types of edges in the flow graph."""
    SEQUENCE = auto()
    DEPENDENCY = auto()
    PARALLEL = auto()
    CONDITIONAL = auto()
    INTERRUPT = auto()


class NodeStatus(Enum):
    """Status of a flow node."""
    PENDING = "⏳"
    ACTIVE = "▶️"
    COMPLETED = "✅"
    FAILED = "❌"
    BLOCKED = "🚫"
    SKIPPED = "⏭️"


@dataclass
class FlowNode:
    """A node in the flow graph."""
    id: str
    type: NodeType
    label: str
    status: NodeStatus = NodeStatus.PENDING
    metadata: Dict[str, Any] = field(default_factory=dict)
    x: float = 0.0
    y: float = 0.0
    width: float = 100.0
    height: float = 40.0
    color: str = "#3498db"
    icon: str = ""


@dataclass
class FlowEdge:
    """An edge connecting nodes in the flow graph."""
    source: str
    target: str
    type: EdgeType = EdgeType.SEQUENCE
    label: str = ""
    color: str = "#95a5a6"
    dashed: bool = False
    animated: bool = False


@dataclass
class FlowState:
    """Complete flow state representation."""
    nodes: Dict[str, FlowNode]
    edges: List[FlowEdge]
    viewport: Tuple[float, float, float, float]  # x, y, width, height
    timestamp: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)


class FlowVisualizer:
    """
    Visualizes conversation flow state.
    
    Capabilities:
    - Render flow graphs
    - Show execution progress
    - Visualize dependencies
    - Display pressure levels
    - ASCII/text rendering
    - Mermaid diagram generation
    - JSON export for external rendering
    """
    
    # Color scheme
    COLORS = {
        'normal': '#3498db',
        'elevated': '#f39c12',
        'high': '#e74c3c',
        'critical': '#9b59b6',
        'success': '#27ae60',
        'neutral': '#95a5a6',
        'background': '#2c3e50',
    }
    
    # Icons for node types
    ICONS = {
        NodeType.REQUEST: "📋",
        NodeType.DECISION: "🔀",
        NodeType.BRANCH: "🌿",
        NodeType.MERGE: "🔀",
        NodeType.SUMMARY: "📝",
        NodeType.INTERRUPT: "⏹️",
        NodeType.RESUME: "▶️",
    }
    
    def __init__(self):
        """Initialize visualizer."""
        self._nodes: Dict[str, FlowNode] = {}
        self._edges: List[FlowEdge] = []
        self._layout_engine = SimpleLayoutEngine()
    
    def add_node(
        self,
        node_id: str,
        node_type: NodeType,
        label: str,
        status: NodeStatus = NodeStatus.PENDING,
        metadata: Optional[Dict] = None,
        color: Optional[str] = None
    ) -> FlowNode:
        """Add a node to the flow."""
        node = FlowNode(
            id=node_id,
            type=node_type,
            label=label,
            status=status,
            metadata=metadata or {},
            color=color or self.COLORS['normal'],
            icon=self.ICONS.get(node_type, "")
        )
        self._nodes[node_id] = node
        return node
    
    def add_edge(
        self,
        source: str,
        target: str,
        edge_type: EdgeType = EdgeType.SEQUENCE,
        label: str = "",
        animated: bool = False
    ) -> FlowEdge:
        """Add an edge between nodes."""
        edge = FlowEdge(
            source=source,
            target=target,
            type=edge_type,
            label=label,
            animated=animated
        )
        self._edges.append(edge)
        return edge
    
    def update_node_status(self, node_id: str, status: NodeStatus):
        """Update a node's status."""
        if node_id in self._nodes:
            self._nodes[node_id].status = status
            
            # Update color based on status
            if status == NodeStatus.COMPLETED:
                self._nodes[node_id].color = self.COLORS['success']
            elif status == NodeStatus.FAILED:
                self._nodes[node_id].color = self.COLORS['high']
            elif status == NodeStatus.ACTIVE:
                self._nodes[node_id].color = self.COLORS['elevated']
    
    def render_ascii(self, compact: bool = False) -> str:
        """
        Render flow as ASCII art.
        
        Args:
            compact: Use compact representation
            
        Returns:
            ASCII representation
        """
        if not self._nodes:
            return "[Empty flow]"
        
        lines = []
        
        # Simple layout: just list nodes in order
        if compact:
            for node_id, node in self._nodes.items():
                icon = node.status.value if node.status else "○"
                lines.append(f"{icon} {node.label}")
        else:
            # Find execution order
            ordered = self._topological_sort()
            
            # Build ASCII tree
            for i, node_id in enumerate(ordered):
                node = self._nodes[node_id]
                icon = node.status.value if node.status else "○"
                
                # Find incoming edges
                incoming = [e for e in self._edges if e.target == node_id]
                
                if not incoming or i == 0:
                    # Start node
                    lines.append(f"{icon} {node.label}")
                else:
                    # Child node
                    prefix = "   " * self._get_depth(node_id)
                    connector = "└─" if i == len(ordered) - 1 else "├─"
                    lines.append(f"{prefix}{connector} {icon} {node.label}")
                
                # Show metadata if present
                if node.metadata and not compact:
                    for key, value in node.metadata.items():
                        if isinstance(value, (str, int, float)):
                            lines.append(f"      {key}: {value}")
        
        return "\n".join(lines)
    
    def render_mermaid(self) -> str:
        """
        Render flow as Mermaid diagram.
        
        Returns:
            Mermaid diagram syntax
        """
        lines = ["flowchart TD"]
        
        # Add nodes
        for node_id, node in self._nodes.items():
            # Clean label for mermaid
            label = node.label.replace('"', '"').replace("[", "(").replace("]", ")")
            icon = node.icon or ""
            
            # Node style
            style = ""
            if node.status == NodeStatus.COMPLETED:
                style = f":::done"
            elif node.status == NodeStatus.ACTIVE:
                style = f":::active"
            elif node.status == NodeStatus.FAILED:
                style = f":::fail"
            
            lines.append(f"    {node_id}[{icon} {label}]{style}")
        
        # Add edges
        for edge in self._edges:
            arrow = "-->"
            if edge.type == EdgeType.DEPENDENCY:
                arrow = "-.->"
            elif edge.type == EdgeType.CONDITIONAL:
                arrow = "-->|{label}|>".format(label=edge.label) if edge.label else "-->"
            
            lines.append(f"    {edge.source} {arrow} {edge.target}")
        
        # Add styles
        lines.append("    classDef done fill:#27ae60,stroke:#1e8449")
        lines.append("    classDef active fill:#f39c12,stroke:#d68910")
        lines.append("    classDef fail fill:#e74c3c,stroke:#c0392b")
        
        return "\n".join(lines)
    
    def render_json(self) -> Dict[str, Any]:
        """
        Render flow as JSON structure.
        
        Returns:
            JSON-serializable dictionary
        """
        # Compute layout
        self._layout_engine.layout(self._nodes, self._edges)
        
        return {
            "nodes": [
                {
                    "id": n.id,
                    "type": n.type.name,
                    "label": n.label,
                    "status": n.status.name,
                    "x": n.x,
                    "y": n.y,
                    "width": n.width,
                    "height": n.height,
                    "color": n.color,
                    "icon": n.icon,
                    "metadata": n.metadata
                }
                for n in self._nodes.values()
            ],
            "edges": [
                {
                    "source": e.source,
                    "target": e.target,
                    "type": e.type.name,
                    "label": e.label,
                    "color": e.color,
                    "dashed": e.dashed,
                    "animated": e.animated
                }
                for e in self._edges
            ],
            "timestamp": time.time()
        }
    
    def render_summary(self) -> str:
        """
        Render a text summary of flow state.
        
        Returns:
            Summary text
        """
        total = len(self._nodes)
        completed = sum(1 for n in self._nodes.values() if n.status == NodeStatus.COMPLETED)
        active = sum(1 for n in self._nodes.values() if n.status == NodeStatus.ACTIVE)
        failed = sum(1 for n in self._nodes.values() if n.status == NodeStatus.FAILED)
        pending = sum(1 for n in self._nodes.values() if n.status == NodeStatus.PENDING)
        
        lines = [
            "═" * 50,
            "           FLOW STATE SUMMARY",
            "═" * 50,
            f"  Total Nodes:    {total}",
            f"  ✅ Completed:   {completed}",
            f"  ▶️ Active:      {active}",
            f"  ⏳ Pending:     {pending}",
            f"  ❌ Failed:      {failed}",
            "─" * 50,
        ]
        
        # Show progress bar
        if total > 0:
            progress = completed / total
            bar_width = 30
            filled = int(bar_width * progress)
            bar = "█" * filled + "░" * (bar_width - filled)
            lines.append(f"  Progress: [{bar}] {progress*100:.0f}%")
        
        # Show active nodes
        if active > 0:
            lines.append("\n  Active:")
            for node in self._nodes.values():
                if node.status == NodeStatus.ACTIVE:
                    lines.append(f"    ▶️ {node.label}")
        
        # Show pending queue
        pending_nodes = [n for n in self._nodes.values() if n.status == NodeStatus.PENDING]
        if pending_nodes:
            lines.append("\n  Next:")
            for node in pending_nodes[:3]:
                lines.append(f"    ⏳ {node.label}")
        
        lines.append("═" * 50)
        
        return "\n".join(lines)
    
    def get_state(self) -> FlowState:
        """Get current flow state."""
        # Compute bounding box
        if self._nodes:
            xs = [n.x for n in self._nodes.values()]
            ys = [n.y for n in self._nodes.values()]
            viewport = (min(xs), min(ys), max(xs) - min(xs) + 150, max(ys) - min(ys) + 100)
        else:
            viewport = (0, 0, 800, 600)
        
        return FlowState(
            nodes=self._nodes.copy(),
            edges=self._edges.copy(),
            viewport=viewport,
            timestamp=time.time()
        )
    
    def _topological_sort(self) -> List[str]:
        """Topological sort of nodes."""
        # Build adjacency list
        graph = {n: [] for n in self._nodes}
        in_degree = {n: 0 for n in self._nodes}
        
        for edge in self._edges:
            if edge.source in graph and edge.target in graph:
                graph[edge.source].append(edge.target)
                in_degree[edge.target] += 1
        
        # Kahn's algorithm
        queue = [n for n, d in in_degree.items() if d == 0]
        result = []
        
        while queue:
            node = queue.pop(0)
            result.append(node)
            
            for neighbor in graph[node]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)
        
        return result
    
    def _get_depth(self, node_id: str) -> int:
        """Get depth of node in hierarchy."""
        depth = 0
        current = node_id
        
        for _ in range(len(self._nodes)):
            incoming = [e for e in self._edges if e.target == current]
            if not incoming:
                break
            current = incoming[0].source
            depth += 1
        
        return depth
    
    def clear(self):
        """Clear all nodes and edges."""
        self._nodes.clear()
        self._edges.clear()


class SimpleLayoutEngine:
    """Simple layout engine for flow graphs."""
    
    def layout(self, nodes: Dict[str, FlowNode], edges: List[FlowEdge]):
        """Compute positions for nodes."""
        if not nodes:
            return
        
        # Simple grid layout
        x, y = 50, 50
        node_spacing = 150
        row_height = 100
        
        for node_id in nodes:
            node = nodes[node_id]
            node.x = x
            node.y = y
            
            x += node_spacing
            if x > 800:
                x = 50
                y += row_height


class PressureVisualizer:
    """Visualizes pressure levels in the flow."""
    
    def __init__(self):
        self.pressure_colors = {
            'NORMAL': '#27ae60',
            'ELEVATED': '#f39c12',
            'HIGH': '#e67e22',
            'CRITICAL': '#e74c3c',
        }
    
    def render_gauge(self, ratio: float, width: int = 40) -> str:
        """Render pressure as ASCII gauge."""
        filled = int(width * min(ratio, 1.0))
        bar = "█" * filled + "░" * (width - filled)
        
        if ratio < 0.7:
            indicator = "🟢"
        elif ratio < 0.85:
            indicator = "🟡"
        elif ratio < 1.0:
            indicator = "🟠"
        else:
            indicator = "🔴"
        
        return f"{indicator} [{bar}] {ratio*100:.0f}%"
    
    def render_multi_gauge(
        self,
        readings: Dict[str, float],
        labels: Optional[Dict[str, str]] = None,
        width: int = 30
    ) -> str:
        """Render multiple pressure gauges."""
        lines = []
        labels = labels or {}
        
        for key, ratio in readings.items():
            label = labels.get(key, key)
            filled = int(width * min(ratio, 1.0))
            bar = "█" * filled + "░" * (width - filled)
            
            lines.append(f"{label:15} [{bar}] {ratio*100:.0f}%")
        
        return "\n".join(lines)


# Convenience functions
def create_flow() -> FlowVisualizer:
    """Create a new flow visualizer."""
    return FlowVisualizer()


def visualize_requests(requests: List[Dict], dependencies: Optional[Dict] = None) -> str:
    """
    Quick visualization of requests.
    
    Args:
        requests: List of request dicts with 'id', 'label', 'status'
        dependencies: Dict of request_id -> list of dependency ids
        
    Returns:
        ASCII visualization
    """
    viz = FlowVisualizer()
    
    for req in requests:
        viz.add_node(
            node_id=req['id'],
            node_type=NodeType.REQUEST,
            label=req.get('label', req['id']),
            status=NodeStatus[req.get('status', 'PENDING')]
        )
    
    if dependencies:
        for target, sources in dependencies.items():
            for source in sources:
                viz.add_edge(source, target, EdgeType.DEPENDENCY)
    
    return viz.render_ascii()