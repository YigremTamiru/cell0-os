"""
COL-Synthesis: Hypothesis Generation Module
Cell 0 OS - Cross-session knowledge synthesis

Automatically generates hypotheses from patterns, insights, and the knowledge graph.
Hypotheses are testable predictions that emerge from the synthesized understanding.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from typing import Any

from .knowledge_graph import KnowledgeGraph, Node, NodeType, EdgeType, EdgeStrength
from .insights import Insight, InsightType, InsightConfidence
from .patterns import Pattern, PatternType, PatternStrength


class HypothesisType(Enum):
    """Types of hypotheses that can be generated."""
    PREDICTIVE = auto()      # Predict future behavior/state
    CAUSAL = auto()          # Propose cause-effect relationships
    CORRELATIONAL = auto()   # Suggest statistical relationships
    EXPLANATORY = auto()     # Explain observed phenomena
    COMPARATIVE = auto()     # Compare entities or concepts
    INTERVENTION = auto()    # Propose actions to achieve outcomes


class HypothesisStatus(Enum):
    """Lifecycle status of a hypothesis."""
    PROPOSED = auto()       # Newly generated, untested
    UNDER_TEST = auto()     # Currently being evaluated
    CONFIRMED = auto()      # Evidence supports hypothesis
    PARTIALLY_CONFIRMED = auto()  # Some supporting evidence
    REJECTED = auto()       # Evidence contradicts hypothesis
    SUPERSEDED = auto()     # Replaced by better hypothesis


@dataclass
class TestResult:
    """
    Result of testing a hypothesis against evidence.
    """
    timestamp: datetime
    evidence_type: str
    evidence_id: str
    outcome: float  # -1.0 (reject) to 1.0 (confirm)
    notes: str = ""
    
    def to_dict(self) -> dict[str, Any]:
        return {
            'timestamp': self.timestamp.isoformat(),
            'evidence_type': self.evidence_type,
            'evidence_id': self.evidence_id,
            'outcome': self.outcome,
            'notes': self.notes
        }


@dataclass
class Hypothesis:
    """
    A generated hypothesis about the user or system.
    
    Hypotheses are provisional understandings—testable predictions
    that bridge current knowledge with future observation.
    """
    id: str
    hypothesis_type: HypothesisType
    statement: str  # The core hypothesis statement
    confidence: float  # 0.0 to 1.0
    status: HypothesisStatus
    created_at: datetime
    updated_at: datetime
    
    # Evidence and testing
    supporting_evidence: list[str] = field(default_factory=list)  # Evidence IDs
    contradicting_evidence: list[str] = field(default_factory=list)
    test_results: list[TestResult] = field(default_factory=list)
    
    # Attribution
    derived_from: list[str] = field(default_factory=list)  # Pattern/Insight IDs
    generated_by: str = ""  # Generation mechanism
    
    # Prediction
    predicted_outcome: str = ""
    testable_conditions: list[str] = field(default_factory=list)
    
    # Lifecycle
    superseded_by: str | None = None
    revision_count: int = 0
    
    # Metadata
    domain: str = ""  # Subject area
    priority: float = 0.5  # 0.0 to 1.0
    
    def __post_init__(self):
        if not self.id:
            self.id = self._generate_id()
    
    def _generate_id(self) -> str:
        """Generate deterministic ID from hypothesis content."""
        content = f"{self.hypothesis_type.name}:{self.statement[:100]}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]
    
    def add_evidence(self, evidence_id: str, supports: bool = True) -> None:
        """Add supporting or contradicting evidence."""
        if supports:
            if evidence_id not in self.supporting_evidence:
                self.supporting_evidence.append(evidence_id)
        else:
            if evidence_id not in self.contradicting_evidence:
                self.contradicting_evidence.append(evidence_id)
        
        self.updated_at = datetime.utcnow()
        self._recalculate_confidence()
    
    def add_test_result(self, result: TestResult) -> None:
        """Add a test result."""
        self.test_results.append(result)
        self.updated_at = datetime.utcnow()
        self.revision_count += 1
        self._recalculate_confidence()
    
    def _recalculate_confidence(self) -> None:
        """Update confidence based on evidence and test results."""
        support_score = len(self.supporting_evidence)
        contra_score = len(self.contradicting_evidence)
        
        # Test results
        test_score = 0.0
        if self.test_results:
            test_score = sum(r.outcome for r in self.test_results) / len(self.test_results)
        
        # Bayesian-inspired update
        if support_score + contra_score > 0:
            evidence_ratio = support_score / (support_score + contra_score)
        else:
            evidence_ratio = 0.5
        
        # Combine scores
        self.confidence = (evidence_ratio * 0.6) + (test_score * 0.4)
        self.confidence = max(0.0, min(1.0, self.confidence))
        
        # Update status
        if self.confidence > 0.8:
            self.status = HypothesisStatus.CONFIRMED
        elif self.confidence > 0.5:
            self.status = HypothesisStatus.PARTIALLY_CONFIRMED
        elif self.confidence < 0.2:
            self.status = HypothesisStatus.REJECTED
    
    def is_active(self) -> bool:
        """Check if hypothesis is still active (not superseded)."""
        return self.superseded_by is None and self.status != HypothesisStatus.REJECTED
    
    def supersede(self, newer_hypothesis_id: str) -> None:
        """Mark this hypothesis as superseded."""
        self.superseded_by = newer_hypothesis_id
        self.status = HypothesisStatus.SUPERSEDED
        self.updated_at = datetime.utcnow()
    
    def to_dict(self) -> dict[str, Any]:
        return {
            'id': self.id,
            'type': self.hypothesis_type.name,
            'statement': self.statement,
            'confidence': self.confidence,
            'status': self.status.name,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'supporting_evidence': self.supporting_evidence,
            'contradicting_evidence': self.contradicting_evidence,
            'test_results': [r.to_dict() for r in self.test_results],
            'derived_from': self.derived_from,
            'predicted_outcome': self.predicted_outcome,
            'testable_conditions': self.testable_conditions,
            'is_active': self.is_active(),
            'domain': self.domain,
            'priority': self.priority
        }


class HypothesisGenerator:
    """
    Generates hypotheses from patterns, insights, and knowledge graphs.
    
    Hypotheses emerge from the synthesis of understanding—not as
    random guesses, but as resonant predictions from the field.
    """
    
    def __init__(self):
        self._hypotheses: dict[str, Hypothesis] = {}
        self._by_type: dict[HypothesisType, list[str]] = {t: [] for t in HypothesisType}
        self._by_domain: dict[str, list[str]] = defaultdict(list)
    
    def generate_from_pattern(self, pattern: Pattern, context: dict[str, Any] | None = None) -> list[Hypothesis]:
        """Generate hypotheses from a detected pattern."""
        hypotheses = []
        context = context or {}
        
        if pattern.pattern_type == PatternType.TEMPORAL:
            h = self._generate_temporal_hypothesis(pattern)
            if h:
                hypotheses.append(h)
        
        elif pattern.pattern_type == PatternType.BEHAVIORAL:
            h = self._generate_behavioral_hypothesis(pattern)
            if h:
                hypotheses.append(h)
        
        elif pattern.pattern_type == PatternType.SEQUENTIAL:
            h = self._generate_sequential_hypothesis(pattern)
            if h:
                hypotheses.append(h)
        
        elif pattern.pattern_type == PatternType.SEMANTIC:
            h = self._generate_semantic_hypothesis(pattern)
            if h:
                hypotheses.append(h)
        
        # Store generated hypotheses
        for h in hypotheses:
            self._store_hypothesis(h)
            h.derived_from.append(pattern.id)
        
        return hypotheses
    
    def generate_from_insight(self, insight: Insight) -> list[Hypothesis]:
        """Generate hypotheses from an extracted insight."""
        hypotheses = []
        
        if insight.insight_type == InsightType.PREFERENCE:
            h = self._generate_preference_hypothesis(insight)
            if h:
                hypotheses.append(h)
        
        elif insight.insight_type == InsightType.GOAL:
            h = self._generate_goal_hypothesis(insight)
            if h:
                hypotheses.append(h)
        
        elif insight.insight_type == InsightType.NEED:
            h = self._generate_need_hypothesis(insight)
            if h:
                hypotheses.append(h)
        
        elif insight.insight_type == InsightType.TENSION:
            h = self._generate_tension_hypothesis(insight)
            if h:
                hypotheses.append(h)
        
        # Store
        for h in hypotheses:
            self._store_hypothesis(h)
            h.derived_from.append(insight.id)
        
        return hypotheses
    
    def generate_from_graph(self, graph: KnowledgeGraph) -> list[Hypothesis]:
        """Generate hypotheses from knowledge graph structure."""
        hypotheses = []
        
        # Find bridge connections (cross-domain hypotheses)
        bridges = graph.find_bridges()
        for source_label, target_label, edge in bridges:
            h = Hypothesis(
                id="",
                hypothesis_type=HypothesisType.CORRELATIONAL,
                statement=f"Concept '{source_label}' is meaningfully connected to '{target_label}' across domains",
                confidence=edge.strength.value,
                status=HypothesisStatus.PROPOSED,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
                domain="cross_domain",
                predicted_outcome=f"Observations of {source_label} may correlate with {target_label}",
                testable_conditions=[
                    f"Track co-occurrence of {source_label} and {target_label}",
                    f"Measure mutual information between concepts"
                ]
            )
            hypotheses.append(h)
        
        # Find central nodes (importance hypotheses)
        stats = graph.get_statistics()
        for node_id, centrality in stats.get('most_central', [])[:3]:
            node = graph.get_node(node_id)
            if node:
                h = Hypothesis(
                    id="",
                    hypothesis_type=HypothesisType.EXPLANATORY,
                    statement=f"'{node.label}' is a central concept in the user's knowledge structure",
                    confidence=centrality,
                    status=HypothesisStatus.PROPOSED,
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow(),
                    domain=str(node.node_type.name).lower(),
                    predicted_outcome=f"Changes to {node.label} will affect multiple related concepts",
                    priority=centrality
                )
                hypotheses.append(h)
        
        # Store
        for h in hypotheses:
            self._store_hypothesis(h)
        
        return hypotheses
    
    def _generate_temporal_hypothesis(self, pattern: Pattern) -> Hypothesis | None:
        """Generate hypothesis from temporal pattern."""
        hour = pattern.metadata.get('hour')
        if hour is None:
            return None
        
        return Hypothesis(
            id="",
            hypothesis_type=HypothesisType.PREDICTIVE,
            statement=f"User will exhibit similar behavior around {hour}:00 based on observed temporal pattern",
            confidence=pattern.confidence * 0.8,
            status=HypothesisStatus.PROPOSED,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            domain="behavioral_temporal",
            predicted_outcome=f"At approximately {hour}:00, user will engage in similar activities",
            testable_conditions=[
                f"Observe user activity at {hour}:00",
                f"Compare to pattern elements: {pattern.elements[:2]}"
            ]
        )
    
    def _generate_behavioral_hypothesis(self, pattern: Pattern) -> Hypothesis | None:
        """Generate hypothesis from behavioral pattern."""
        if not pattern.elements:
            return None
        
        behavior = str(pattern.elements[0])[:50]
        
        return Hypothesis(
            id="",
            hypothesis_type=HypothesisType.PREDICTIVE,
            statement=f"User will continue to exhibit '{behavior}' behavior under similar conditions",
            confidence=pattern.confidence * pattern.strength.value,
            status=HypothesisStatus.PROPOSED,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            domain="behavioral",
            predicted_outcome=f"Behavioral consistency will be observed in future similar contexts",
            testable_conditions=[
                "Present similar context to user",
                f"Observe for '{behavior}'"
            ]
        )
    
    def _generate_sequential_hypothesis(self, pattern: Pattern) -> Hypothesis | None:
        """Generate hypothesis from sequential pattern."""
        if len(pattern.elements) < 2:
            return None
        
        sequence = " -> ".join(pattern.elements[:3])
        
        return Hypothesis(
            id="",
            hypothesis_type=HypothesisType.CAUSAL,
            statement=f"Sequence '{sequence}' represents a causal or procedural relationship",
            confidence=pattern.confidence * 0.7,
            status=HypothesisStatus.PROPOSED,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            domain="procedural",
            predicted_outcome=f"Observing first step will predict subsequent steps",
            testable_conditions=[
                f"Trigger first element: {pattern.elements[0]}",
                f"Observe if sequence follows: {sequence}"
            ]
        )
    
    def _generate_semantic_hypothesis(self, pattern: Pattern) -> Hypothesis | None:
        """Generate hypothesis from semantic pattern."""
        # Check for semantic clusters
        if len(pattern.elements) >= 2:
            concepts = pattern.elements[:3]
            return Hypothesis(
                id="",
                hypothesis_type=HypothesisType.CORRELATIONAL,
                statement=f"Concepts {concepts} are semantically related in user's context",
                confidence=pattern.confidence * 0.6,
                status=HypothesisStatus.PROPOSED,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
                domain="semantic",
                predicted_outcome=f"Mentioning one concept increases likelihood of mentioning others",
                testable_conditions=[
                    f"Introduce concept: {concepts[0]}",
                    f"Track if related concepts emerge"
                ]
            )
        return None
    
    def _generate_preference_hypothesis(self, insight: Insight) -> Hypothesis | None:
        """Generate hypothesis from preference insight."""
        return Hypothesis(
            id="",
            hypothesis_type=HypothesisType.PREDICTIVE,
            statement=f"User preference: {insight.content[:100]}",
            confidence=list(InsightConfidence).index(insight.confidence) / 4.0,
            status=HypothesisStatus.PROPOSED,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            domain="preference",
            derived_from=[insight.id],
            predicted_outcome="User will make consistent choices aligned with this preference",
            testable_conditions=[
                "Present choice between alternatives",
                "Observe if choice aligns with preference"
            ]
        )
    
    def _generate_goal_hypothesis(self, insight: Insight) -> Hypothesis | None:
        """Generate hypothesis from goal insight."""
        return Hypothesis(
            id="",
            hypothesis_type=HypothesisType.INTERVENTION,
            statement=f"User is working toward: {insight.content[:100]}",
            confidence=list(InsightConfidence).index(insight.confidence) / 4.0,
            status=HypothesisStatus.PROPOSED,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            domain="goals",
            derived_from=[insight.id],
            predicted_outcome="Providing relevant assistance will accelerate goal achievement",
            testable_conditions=[
                "Offer assistance related to goal",
                "Measure progress or acceptance"
            ]
        )
    
    def _generate_need_hypothesis(self, insight: Insight) -> Hypothesis | None:
        """Generate hypothesis from need insight."""
        return Hypothesis(
            id="",
            hypothesis_type=HypothesisType.INTERVENTION,
            statement=f"Unmet need detected: {insight.content[:100]}",
            confidence=list(InsightConfidence).index(insight.confidence) / 4.0,
            status=HypothesisStatus.PROPOSED,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            domain="needs",
            derived_from=[insight.id],
            predicted_outcome="Addressing this need will reduce friction and increase satisfaction",
            testable_conditions=[
                "Provide resource addressing need",
                "Observe change in user behavior/sentiment"
            ]
        )
    
    def _generate_tension_hypothesis(self, insight: Insight) -> Hypothesis | None:
        """Generate hypothesis from tension insight."""
        return Hypothesis(
            id="",
            hypothesis_type=HypothesisType.EXPLANATORY,
            statement=f"Tension exists: {insight.content[:100]}",
            confidence=list(InsightConfidence).index(insight.confidence) / 4.0,
            status=HypothesisStatus.PROPOSED,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            domain="tension",
            derived_from=[insight.id],
            predicted_outcome="Resolving this tension will unlock progress",
            testable_conditions=[
                "Identify specific conflicting elements",
                "Propose resolution approach",
                "Measure if tension reduces"
            ]
        )
    
    def _store_hypothesis(self, hypothesis: Hypothesis) -> None:
        """Store a hypothesis, merging with similar ones if appropriate."""
        # Check for existing similar hypothesis
        for existing_id, existing in self._hypotheses.items():
            if self._hypotheses_similar(existing, hypothesis):
                # Merge evidence
                for derived in hypothesis.derived_from:
                    if derived not in existing.derived_from:
                        existing.derived_from.append(derived)
                existing.updated_at = datetime.utcnow()
                existing._recalculate_confidence()
                return
        
        # Store new hypothesis
        self._hypotheses[hypothesis.id] = hypothesis
        self._by_type[hypothesis.hypothesis_type].append(hypothesis.id)
        if hypothesis.domain:
            self._by_domain[hypothesis.domain].append(hypothesis.id)
    
    def _hypotheses_similar(self, h1: Hypothesis, h2: Hypothesis) -> bool:
        """Check if two hypotheses are similar enough to merge."""
        if h1.hypothesis_type != h2.hypothesis_type:
            return False
        
        # Simple text similarity
        words1 = set(h1.statement.lower().split())
        words2 = set(h2.statement.lower().split())
        
        if not words1 or not words2:
            return False
        
        intersection = len(words1 & words2)
        union = len(words1 | words2)
        
        return (intersection / union) > 0.7 if union > 0 else False
    
    def get_hypotheses(
        self,
        hypothesis_type: HypothesisType | None = None,
        min_confidence: float = 0.0,
        active_only: bool = True,
        domain: str | None = None
    ) -> list[Hypothesis]:
        """Retrieve hypotheses with filtering."""
        candidates = []
        
        if hypothesis_type:
            candidates = [self._hypotheses[hid] for hid in self._by_type.get(hypothesis_type, [])]
        elif domain:
            candidates = [self._hypotheses[hid] for hid in self._by_domain.get(domain, [])]
        else:
            candidates = list(self._hypotheses.values())
        
        results = []
        for h in candidates:
            if h.confidence < min_confidence:
                continue
            if active_only and not h.is_active():
                continue
            results.append(h)
        
        # Sort by priority (descending), then confidence
        results.sort(key=lambda h: (h.priority, h.confidence), reverse=True)
        return results
    
    def test_hypothesis(
        self,
        hypothesis_id: str,
        evidence_id: str,
        outcome: float,
        notes: str = ""
    ) -> bool:
        """Record a test result for a hypothesis."""
        if hypothesis_id not in self._hypotheses:
            return False
        
        result = TestResult(
            timestamp=datetime.utcnow(),
            evidence_type="observation",
            evidence_id=evidence_id,
            outcome=outcome,
            notes=notes
        )
        
        self._hypotheses[hypothesis_id].add_test_result(result)
        return True
    
    def export_hypotheses(self) -> dict[str, Any]:
        """Export all hypotheses for persistence."""
        return {
            'timestamp': datetime.utcnow().isoformat(),
            'hypotheses': [h.to_dict() for h in self._hypotheses.values()],
            'statistics': {
                'total': len(self._hypotheses),
                'by_type': {t.name: len(ids) for t, ids in self._by_type.items()},
                'by_status': {
                    status.name: sum(
                        1 for h in self._hypotheses.values() 
                        if h.status == status
                    )
                    for status in HypothesisStatus
                }
            }
        }
    
    def import_hypotheses(self, data: dict[str, Any]) -> None:
        """Import hypotheses from persisted state."""
        for h_data in data.get('hypotheses', []):
            hypothesis = Hypothesis(
                id=h_data['id'],
                hypothesis_type=HypothesisType[h_data['type']],
                statement=h_data['statement'],
                confidence=h_data['confidence'],
                status=HypothesisStatus[h_data['status']],
                created_at=datetime.fromisoformat(h_data['created_at']),
                updated_at=datetime.fromisoformat(h_data['updated_at']),
                supporting_evidence=h_data.get('supporting_evidence', []),
                contradicting_evidence=h_data.get('contradicting_evidence', []),
                derived_from=h_data.get('derived_from', []),
                predicted_outcome=h_data.get('predicted_outcome', ''),
                testable_conditions=h_data.get('testable_conditions', []),
                domain=h_data.get('domain', ''),
                priority=h_data.get('priority', 0.5)
            )
            
            # Restore test results
            for r_data in h_data.get('test_results', []):
                result = TestResult(
                    timestamp=datetime.fromisoformat(r_data['timestamp']),
                    evidence_type=r_data['evidence_type'],
                    evidence_id=r_data['evidence_id'],
                    outcome=r_data['outcome'],
                    notes=r_data.get('notes', '')
                )
                hypothesis.test_results.append(result)
            
            self._hypotheses[hypothesis.id] = hypothesis
            self._by_type[hypothesis.hypothesis_type].append(hypothesis.id)
            if hypothesis.domain:
                self._by_domain[hypothesis.domain].append(hypothesis.id)
