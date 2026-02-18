"""
COL-Synthesis: Cross-Session Knowledge Synthesis Module
Cell 0 OS - Cognitive Operating Layer

This module synthesizes understanding across all interactions, enabling:
- Pattern detection across multiple sessions
- Insight extraction from conversation history
- Knowledge graph construction from interactions
- Automatic hypothesis generation
- Contradiction detection in understanding
- Cross-domain connection discovery
- Epiphany triggering ("Aha!" moments)
- Long-term learning from user interactions
- Predictive modeling of user needs

"""

from __future__ import annotations

# Pattern detection
from .patterns import (
    Pattern,
    PatternType,
    PatternStrength,
    PatternContext,
    PatternDetector,
    detect_behavioral_cycles
)

# Insight extraction
from .insights import (
    Insight,
    InsightType,
    InsightConfidence,
    Evidence,
    InsightExtractor
)

# Knowledge graph
from .knowledge_graph import (
    Node,
    NodeType,
    Edge,
    EdgeType,
    EdgeStrength,
    KnowledgeGraph,
    merge_graphs
)

# Hypothesis generation
from .hypothesis import (
    Hypothesis,
    HypothesisType,
    HypothesisStatus,
    TestResult,
    HypothesisGenerator
)

# Epiphany triggering
from .epiphany import (
    Epiphany,
    EpiphanyType,
    EpiphanyIntensity,
    EpiphanyTrigger,
    EpiphanyEngine
)

__all__ = [
    # Patterns
    'Pattern',
    'PatternType',
    'PatternStrength',
    'PatternContext',
    'PatternDetector',
    'detect_behavioral_cycles',
    
    # Insights
    'Insight',
    'InsightType',
    'InsightConfidence',
    'Evidence',
    'InsightExtractor',
    
    # Knowledge Graph
    'Node',
    'NodeType',
    'Edge',
    'EdgeType',
    'EdgeStrength',
    'KnowledgeGraph',
    'merge_graphs',
    
    # Hypotheses
    'Hypothesis',
    'HypothesisType',
    'HypothesisStatus',
    'TestResult',
    'HypothesisGenerator',
    
    # Epiphanies
    'Epiphany',
    'EpiphanyType',
    'EpiphanyIntensity',
    'EpiphanyTrigger',
    'EpiphanyEngine',
]

__version__ = "0.1.0"
