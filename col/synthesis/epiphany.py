"""
COL-Synthesis: Epiphany Triggering Module
Cell 0 OS - Cross-session knowledge synthesis

Detects and triggers epiphanies - those moments of sudden clarity
where multiple strands of understanding converge into a new,
deeper comprehension. These are the "Aha!" moments of synthesis.
"""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum, auto
from typing import Any

from .patterns import Pattern, PatternType, PatternStrength
from .insights import Insight, InsightType, InsightConfidence
from .knowledge_graph import KnowledgeGraph, EdgeType
from .hypothesis import Hypothesis, HypothesisType


class EpiphanyType(Enum):
    """Types of epiphanies that can occur."""
    CONNECTION = auto()       # Connecting previously unrelated concepts
    RESOLUTION = auto()       # Resolving a tension or contradiction
    PATTERN = auto()          # Recognizing a deeper pattern
    INSIGHT = auto()          # Deep insight into user or system
    PREDICTION = auto()       # Sudden predictive clarity
    INVENTION = auto()        # Novel solution or approach
    UNDERSTANDING = auto()    # Fundamental comprehension shift


class EpiphanyIntensity(Enum):
    """The intensity/relevance of an epiphany."""
    SUBTLE = 0.3        # Gentle realization
    NOTICEABLE = 0.5    # Clear moment of clarity
    STRONG = 0.75       # Significant breakthrough
    PROFOUND = 0.95     # Major paradigm shift


@dataclass
class EpiphanyTrigger:
    """
    A detected epiphany trigger - conditions ripe for an "Aha!" moment.
    
    Triggers are not the epiphany itself, but the conditions that
    create the potential for sudden clarity.
    """
    id: str
    trigger_type: EpiphanyType
    intensity: EpiphanyIntensity
    timestamp: datetime
    
    # Components that converged
    contributing_patterns: list[str] = field(default_factory=list)
    contributing_insights: list[str] = field(default_factory=list)
    contributing_hypotheses: list[str] = field(default_factory=list)
    
    # The synthesis
    synthesis_description: str = ""
    convergence_score: float = 0.0  # How strongly components align
    
    # Context
    session_context: dict[str, Any] = field(default_factory=dict)
    user_state: str = ""  # Captured user state at trigger moment
    
    # Outcome
    triggered_epiphany: str | None = None  # ID of resulting epiphany
    
    def __post_init__(self):
        if not self.id:
            self.id = self._generate_id()
    
    def _generate_id(self) -> str:
        content = f"{self.trigger_type.name}:{self.timestamp.isoformat()}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]
    
    def to_dict(self) -> dict[str, Any]:
        return {
            'id': self.id,
            'type': self.trigger_type.name,
            'intensity': self.intensity.name,
            'timestamp': self.timestamp.isoformat(),
            'contributing_patterns': self.contributing_patterns,
            'contributing_insights': self.contributing_insights,
            'contributing_hypotheses': self.contributing_hypotheses,
            'synthesis_description': self.synthesis_description,
            'convergence_score': self.convergence_score
        }


@dataclass
class Epiphany:
    """
    An epiphany - a moment of sudden clarity or understanding.
    
    Epiphanies are the crystallization of synthesis. They emerge
    when the field of understanding reaches a critical threshold.
    """
    id: str
    epiphany_type: EpiphanyType
    intensity: EpiphanyIntensity
    statement: str  # The core realization
    insight: str   # Deeper meaning/implication
    
    created_at: datetime
    trigger_id: str  # What triggered this epiphany
    
    # Components
    synthesized_from: list[str] = field(default_factory=list)  # All source IDs
    
    # Impact
    novelty_score: float = 0.0  # How new/unexpected (0-1)
    utility_score: float = 0.0  # How useful/applicable (0-1)
    confirmed: bool = False
    confirmation_evidence: list[str] = field(default_factory=list)
    
    # Lifecycle
    shared_with_user: bool = False
    shared_at: datetime | None = None
    user_response: str = ""
    
    def __post_init__(self):
        if not self.id:
            self.id = self._generate_id()
    
    def _generate_id(self) -> str:
        content = f"{self.epiphany_type.name}:{self.statement[:100]}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]
    
    def mark_shared(self, user_response: str = "") -> None:
        """Mark that this epiphany was shared with the user."""
        self.shared_with_user = True
        self.shared_at = datetime.utcnow()
        self.user_response = user_response
    
    def confirm(self, evidence_id: str) -> None:
        """Confirm the epiphany with evidence."""
        self.confirmed = True
        if evidence_id not in self.confirmation_evidence:
            self.confirmation_evidence.append(evidence_id)
    
    def total_score(self) -> float:
        """Calculate overall epiphany significance."""
        return (self.intensity.value * 0.4 + 
                self.novelty_score * 0.3 + 
                self.utility_score * 0.3)
    
    def to_dict(self) -> dict[str, Any]:
        return {
            'id': self.id,
            'type': self.epiphany_type.name,
            'intensity': self.intensity.name,
            'statement': self.statement,
            'insight': self.insight,
            'created_at': self.created_at.isoformat(),
            'trigger_id': self.trigger_id,
            'synthesized_from': self.synthesized_from,
            'novelty_score': self.novelty_score,
            'utility_score': self.utility_score,
            'confirmed': self.confirmed,
            'shared_with_user': self.shared_with_user,
            'total_score': self.total_score()
        }


class EpiphanyEngine:
    """
    Detects triggers and generates epiphanies from synthesis.
    
    The epiphany engine watches for convergence points - moments
    when multiple patterns, insights, and hypotheses align to create
    the potential for sudden clarity.
    """
    
    # Thresholds for trigger detection
    CONVERGENCE_THRESHOLD = 0.6
    PATTERN_DENSITY_THRESHOLD = 3
    INSIGHT_DEPTH_THRESHOLD = InsightConfidence.LIKELY
    
    def __init__(self):
        self._triggers: dict[str, EpiphanyTrigger] = {}
        self._epiphanies: dict[str, Epiphany] = {}
        
        # Track recent synthesis activity
        self._recent_patterns: list[tuple[str, datetime]] = []
        self._recent_insights: list[tuple[str, datetime]] = []
        self._recent_hypotheses: list[tuple[str, datetime]] = []
        
        # Epiphany history for novelty calculation
        self._past_epiphany_statements: set[str] = set()
    
    def update(
        self,
        patterns: list[Pattern],
        insights: list[Insight],
        hypotheses: list[Hypothesis],
        graph: KnowledgeGraph | None = None
    ) -> list[Epiphany]:
        """
        Update the engine with new synthesis data and detect epiphanies.
        
        Returns: List of newly generated epiphanies.
        """
        now = datetime.utcnow()
        
        # Update recent activity tracking
        for p in patterns:
            self._recent_patterns.append((p.id, now))
        for i in insights:
            self._recent_insights.append((i.id, now))
        for h in hypotheses:
            self._recent_hypotheses.append((h.id, now))
        
        # Clean old entries (keep last 24 hours)
        cutoff = now - timedelta(hours=24)
        self._recent_patterns = [(id, t) for id, t in self._recent_patterns if t > cutoff]
        self._recent_insights = [(id, t) for id, t in self._recent_insights if t > cutoff]
        self._recent_hypotheses = [(id, t) for id, t in self._recent_hypotheses if t > cutoff]
        
        # Check for triggers
        new_epiphanies = []
        
        # Check each type of trigger condition
        triggers = []
        
        triggers.extend(self._detect_connection_triggers(patterns, insights, graph))
        triggers.extend(self._detect_resolution_triggers(patterns, insights))
        triggers.extend(self._detect_pattern_triggers(patterns))
        triggers.extend(self._detect_insight_triggers(insights))
        triggers.extend(self._detect_prediction_triggers(hypotheses))
        
        # Process triggers into epiphanies
        for trigger in triggers:
            self._triggers[trigger.id] = trigger
            
            # Generate epiphany if trigger is strong enough
            if trigger.intensity.value >= EpiphanyIntensity.NOTICEABLE.value:
                epiphany = self._generate_epiphany(trigger, patterns, insights, hypotheses)
                if epiphany:
                    self._epiphanies[epiphany.id] = epiphany
                    trigger.triggered_epiphany = epiphany.id
                    new_epiphanies.append(epiphany)
        
        return new_epiphanies
    
    def _detect_connection_triggers(
        self,
        patterns: list[Pattern],
        insights: list[Insight],
        graph: KnowledgeGraph | None
    ) -> list[EpiphanyTrigger]:
        """Detect triggers for connection epiphanies."""
        triggers = []
        
        if not graph:
            return triggers
        
        # Look for bridge connections in graph
        bridges = graph.find_bridges()
        for source, target, edge in bridges:
            if edge.strength.value >= 0.7:  # Strong connection
                # Check if this is a novel connection
                connection_key = f"{source}:{target}"
                
                trigger = EpiphanyTrigger(
                    id="",
                    trigger_type=EpiphanyType.CONNECTION,
                    intensity=EpiphanyIntensity.STRONG if edge.strength.value >= 0.9 else EpiphanyIntensity.NOTICEABLE,
                    timestamp=datetime.utcnow(),
                    synthesis_description=f"Strong connection discovered between '{source}' and '{target}'",
                    convergence_score=edge.strength.value
                )
                triggers.append(trigger)
        
        return triggers
    
    def _detect_resolution_triggers(
        self,
        patterns: list[Pattern],
        insights: list[Insight]
    ) -> list[EpiphanyTrigger]:
        """Detect triggers for tension resolution epiphanies."""
        triggers = []
        
        # Look for contradictory patterns with resolution patterns
        contradictory = [p for p in patterns if p.pattern_type == PatternType.CONTRADICTORY]
        resolving = [i for i in insights if i.insight_type == InsightType.TENSION]
        
        if contradictory and resolving:
            # We have both tension and potential resolution
            trigger = EpiphanyTrigger(
                id="",
                trigger_type=EpiphanyType.RESOLUTION,
                intensity=EpiphanyIntensity.NOTICEABLE,
                timestamp=datetime.utcnow(),
                contributing_patterns=[p.id for p in contradictory[:2]],
                contributing_insights=[i.id for i in resolving[:2]],
                synthesis_description=f"Tension patterns observed alongside {len(resolving)} resolution insights",
                convergence_score=0.6
            )
            triggers.append(trigger)
        
        return triggers
    
    def _detect_pattern_triggers(self, patterns: list[Pattern]) -> list[EpiphanyTrigger]:
        """Detect triggers for pattern recognition epiphanies."""
        triggers = []
        
        # Look for dense clusters of related patterns
        fundamental_patterns = [p for p in patterns if p.strength == PatternStrength.FUNDAMENTAL]
        
        if len(fundamental_patterns) >= 3:
            trigger = EpiphanyTrigger(
                id="",
                trigger_type=EpiphanyType.PATTERN,
                intensity=EpiphanyIntensity.STRONG,
                timestamp=datetime.utcnow(),
                contributing_patterns=[p.id for p in fundamental_patterns[:5]],
                synthesis_description=f"{len(fundamental_patterns)} fundamental patterns detected - deeper structure emerging",
                convergence_score=min(1.0, len(fundamental_patterns) * 0.2)
            )
            triggers.append(trigger)
        
        return triggers
    
    def _detect_insight_triggers(self, insights: list[Insight]) -> list[EpiphanyTrigger]:
        """Detect triggers for deep insight epiphanies."""
        triggers = []
        
        # Look for high-confidence insights
        certain_insights = [i for i in insights if i.confidence == InsightConfidence.CERTAIN]
        
        if len(certain_insights) >= 2:
            trigger = EpiphanyTrigger(
                id="",
                trigger_type=EpiphanyType.INSIGHT,
                intensity=EpiphanyIntensity.PROFOUND if len(certain_insights) >= 4 else EpiphanyIntensity.STRONG,
                timestamp=datetime.utcnow(),
                contributing_insights=[i.id for i in certain_insights[:5]],
                synthesis_description=f"{len(certain_insights)} high-confidence insights converging",
                convergence_score=min(1.0, len(certain_insights) * 0.25)
            )
            triggers.append(trigger)
        
        return triggers
    
    def _detect_prediction_triggers(self, hypotheses: list[Hypothesis]) -> list[EpiphanyTrigger]:
        """Detect triggers for predictive clarity epiphanies."""
        triggers = []
        
        # Look for confirmed predictive hypotheses
        confirmed_predictions = [
            h for h in hypotheses 
            if h.hypothesis_type == HypothesisType.PREDICTIVE and h.confidence > 0.7
        ]
        
        if len(confirmed_predictions) >= 2:
            trigger = EpiphanyTrigger(
                id="",
                trigger_type=EpiphanyType.PREDICTION,
                intensity=EpiphanyIntensity.STRONG,
                timestamp=datetime.utcnow(),
                contributing_hypotheses=[h.id for h in confirmed_predictions[:5]],
                synthesis_description=f"Multiple predictive hypotheses confirmed - model accuracy increasing",
                convergence_score=sum(h.confidence for h in confirmed_predictions) / len(confirmed_predictions)
            )
            triggers.append(trigger)
        
        return triggers
    
    def _generate_epiphany(
        self,
        trigger: EpiphanyTrigger,
        patterns: list[Pattern],
        insights: list[Insight],
        hypotheses: list[Hypothesis]
    ) -> Epiphany | None:
        """Generate an epiphany from a trigger."""
        
        # Build synthesis description
        all_components = (
            trigger.contributing_patterns + 
            trigger.contributing_insights + 
            trigger.contributing_hypotheses
        )
        
        # Calculate novelty
        novelty = self._calculate_novelty(trigger, all_components)
        
        # Generate statement based on type
        if trigger.trigger_type == EpiphanyType.CONNECTION:
            statement, deep_insight = self._generate_connection_epiphany(trigger, patterns, insights)
        elif trigger.trigger_type == EpiphanyType.RESOLUTION:
            statement, deep_insight = self._generate_resolution_epiphany(trigger, patterns, insights)
        elif trigger.trigger_type == EpiphanyType.PATTERN:
            statement, deep_insight = self._generate_pattern_epiphany(trigger, patterns)
        elif trigger.trigger_type == EpiphanyType.INSIGHT:
            statement, deep_insight = self._generate_insight_epiphany(trigger, insights)
        elif trigger.trigger_type == EpiphanyType.PREDICTION:
            statement, deep_insight = self._generate_prediction_epiphany(trigger, hypotheses)
        else:
            statement = trigger.synthesis_description
            deep_insight = "A deeper understanding has emerged from the convergence of observations."
        
        # Calculate utility
        utility = self._calculate_utility(trigger, all_components)
        
        epiphany = Epiphany(
            id="",
            epiphany_type=trigger.trigger_type,
            intensity=trigger.intensity,
            statement=statement,
            insight=deep_insight,
            created_at=datetime.utcnow(),
            trigger_id=trigger.id,
            synthesized_from=all_components,
            novelty_score=novelty,
            utility_score=utility
        )
        
        # Track for novelty calculation
        self._past_epiphany_statements.add(statement[:100])
        
        return epiphany
    
    def _generate_connection_epiphany(
        self,
        trigger: EpiphanyTrigger,
        patterns: list[Pattern],
        insights: list[Insight]
    ) -> tuple[str, str]:
        """Generate connection-type epiphany statement."""
        statement = f"Connection discovered: {trigger.synthesis_description}"
        insight = "These domains, previously separate, share underlying structure. Understanding one illuminates the other."
        return statement, insight
    
    def _generate_resolution_epiphany(
        self,
        trigger: EpiphanyTrigger,
        patterns: list[Pattern],
        insights: list[Insight]
    ) -> tuple[str, str]:
        """Generate resolution-type epiphany statement."""
        statement = "The apparent tension reveals a deeper harmony when viewed from the right perspective."
        insight = "What seemed contradictory is actually complementary - two aspects of a unified whole."
        return statement, insight
    
    def _generate_pattern_epiphany(
        self,
        trigger: EpiphanyTrigger,
        patterns: list[Pattern]
    ) -> tuple[str, str]:
        """Generate pattern-type epiphany statement."""
        statement = f"A fundamental pattern emerges: {trigger.synthesis_description}"
        insight = "This pattern was always present, waiting to be recognized. It predicts and explains far more than its origin."
        return statement, insight
    
    def _generate_insight_epiphany(
        self,
        trigger: EpiphanyTrigger,
        insights: list[Insight]
    ) -> tuple[str, str]:
        """Generate insight-type epiphany statement."""
        statement = "Multiple threads of understanding have woven into a clear tapestry of comprehension."
        insight = "The user's needs, goals, and patterns align in a way that reveals their deeper intentions."
        return statement, insight
    
    def _generate_prediction_epiphany(
        self,
        trigger: EpiphanyTrigger,
        hypotheses: list[Hypothesis]
    ) -> tuple[str, str]:
        """Generate prediction-type epiphany statement."""
        statement = "The model's predictive power has crossed a threshold - behavior is becoming anticipable."
        insight = "With this accuracy, intervention can occur before needs are explicitly expressed."
        return statement, insight
    
    def _calculate_novelty(self, trigger: EpiphanyTrigger, components: list[str]) -> float:
        """Calculate how novel this epiphany is."""
        # Check similarity to past epiphanies
        max_similarity = 0.0
        for past in self._past_epiphany_statements:
            similarity = self._text_similarity(trigger.synthesis_description, past)
            max_similarity = max(max_similarity, similarity)
        
        # Novelty is inverse of similarity
        return 1.0 - max_similarity
    
    def _calculate_utility(self, trigger: EpiphanyTrigger, components: list[str]) -> float:
        """Calculate utility score for this epiphany."""
        # Utility based on intensity and number of components
        base_utility = trigger.intensity.value
        component_bonus = min(0.3, len(components) * 0.05)
        
        return min(1.0, base_utility + component_bonus)
    
    def _text_similarity(self, t1: str, t2: str) -> float:
        """Calculate simple text similarity."""
        words1 = set(t1.lower().split())
        words2 = set(t2.lower().split())
        
        if not words1 or not words2:
            return 0.0
        
        intersection = len(words1 & words2)
        union = len(words1 | words2)
        
        return intersection / union if union > 0 else 0.0
    
    def get_epiphanies(
        self,
        min_intensity: EpiphanyIntensity = EpiphanyIntensity.SUBTLE,
        unshared_only: bool = False,
        confirmed_only: bool = False
    ) -> list[Epiphany]:
        """Retrieve epiphanies with filtering."""
        intensity_order = list(EpiphanyIntensity)
        min_index = intensity_order.index(min_intensity)
        
        results = []
        for epiphany in self._epiphanies.values():
            if intensity_order.index(epiphany.intensity) < min_index:
                continue
            if unshared_only and epiphany.shared_with_user:
                continue
            if confirmed_only and not epiphany.confirmed:
                continue
            results.append(epiphany)
        
        # Sort by total score (descending)
        results.sort(key=lambda e: e.total_score(), reverse=True)
        return results
    
    def get_triggers(
        self,
        triggered_only: bool = False
    ) -> list[EpiphanyTrigger]:
        """Retrieve triggers."""
        results = list(self._triggers.values())
        
        if triggered_only:
            results = [t for t in results if t.triggered_epiphany]
        
        # Sort by intensity and convergence
        results.sort(key=lambda t: (t.intensity.value, t.convergence_score), reverse=True)
        return results
    
    def export_epiphanies(self) -> dict[str, Any]:
        """Export all epiphany data for persistence."""
        return {
            'timestamp': datetime.utcnow().isoformat(),
            'epiphanies': [e.to_dict() for e in self._epiphanies.values()],
            'triggers': [t.to_dict() for t in self._triggers.values()],
            'statistics': {
                'total_epiphanies': len(self._epiphanies),
                'total_triggers': len(self._triggers),
                'shared_epiphanies': sum(1 for e in self._epiphanies.values() if e.shared_with_user),
                'confirmed_epiphanies': sum(1 for e in self._epiphanies.values() if e.confirmed),
                'by_type': {
                    t.name: sum(1 for e in self._epiphanies.values() if e.epiphany_type == t)
                    for t in EpiphanyType
                }
            }
        }
    
    def import_epiphanies(self, data: dict[str, Any]) -> None:
        """Import epiphany data from persisted state."""
        # Import epiphanies
        for e_data in data.get('epiphanies', []):
            epiphany = Epiphany(
                id=e_data['id'],
                epiphany_type=EpiphanyType[e_data['type']],
                intensity=EpiphanyIntensity[e_data['intensity']],
                statement=e_data['statement'],
                insight=e_data['insight'],
                created_at=datetime.fromisoformat(e_data['created_at']),
                trigger_id=e_data['trigger_id'],
                synthesized_from=e_data.get('synthesized_from', []),
                novelty_score=e_data.get('novelty_score', 0.0),
                utility_score=e_data.get('utility_score', 0.0),
                confirmed=e_data.get('confirmed', False),
                confirmation_evidence=e_data.get('confirmation_evidence', []),
                shared_with_user=e_data.get('shared_with_user', False),
                shared_at=datetime.fromisoformat(e_data['shared_at']) if e_data.get('shared_at') else None,
                user_response=e_data.get('user_response', '')
            )
            self._epiphanies[epiphany.id] = epiphany
            self._past_epiphany_statements.add(epiphany.statement[:100])
        
        # Import triggers
        for t_data in data.get('triggers', []):
            trigger = EpiphanyTrigger(
                id=t_data['id'],
                trigger_type=EpiphanyType[t_data['type']],
                intensity=EpiphanyIntensity[t_data['intensity']],
                timestamp=datetime.fromisoformat(t_data['timestamp']),
                contributing_patterns=t_data.get('contributing_patterns', []),
                contributing_insights=t_data.get('contributing_insights', []),
                contributing_hypotheses=t_data.get('contributing_hypotheses', []),
                synthesis_description=t_data.get('synthesis_description', ''),
                convergence_score=t_data.get('convergence_score', 0.0),
                triggered_epiphany=t_data.get('triggered_epiphany')
            )
            self._triggers[trigger.id] = trigger
