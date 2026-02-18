"""
COL-Synthesis: Insight Extraction Module
Cell 0 OS - Cross-session knowledge synthesis

Extracts meaningful insights from conversation history and interaction streams.
Insights are not summaries—they are emergent understandings that arise
from pattern recognition and contextual synthesis.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from typing import Any, Generic, TypeVar

from .patterns import Pattern, PatternType, PatternStrength


class InsightType(Enum):
    """Types of insights that can be extracted."""
    PREFERENCE = auto()      # User preferences discovered
    GOAL = auto()            # Goals or objectives inferred
    BLOCKER = auto()         # Obstacles or friction points
    CAPABILITY = auto()      # What the user can do
    NEED = auto()            # Unexpressed or emerging needs
    RELATIONSHIP = auto()    # Connections between concepts
    TENSION = auto()         # Conflicts or contradictions
    OPPORTUNITY = auto()     # Potential for action
    LEARNING = auto()        # Knowledge acquisition patterns


class InsightConfidence(Enum):
    """Confidence levels based on evidence quality."""
    SPECULATIVE = 0.2   # Single observation, weak signal
    PROBABLE = 0.5      # Multiple observations, building evidence
    LIKELY = 0.75       # Strong evidence, consistent pattern
    CERTAIN = 0.9       # High confidence, validated across contexts


T = TypeVar('T')


@dataclass
class Evidence:
    """
    Evidence supporting an insight.
    
    Evidence is not proof—it is the resonant trail
    that led to the insight's emergence.
    """
    source_type: str  # 'pattern', 'conversation', 'action', 'inference'
    source_id: str
    content: Any
    timestamp: datetime
    weight: float = 1.0  # How strongly this supports the insight
    
    def to_dict(self) -> dict[str, Any]:
        return {
            'source_type': self.source_type,
            'source_id': self.source_id,
            'content': str(self.content)[:200],
            'timestamp': self.timestamp.isoformat(),
            'weight': self.weight
        }


@dataclass
class Insight(Generic[T]):
    """
    An extracted insight about the user or interaction.
    
    Insights are living understandings that evolve with new evidence.
    They carry the weight of accumulated observation.
    """
    id: str
    insight_type: InsightType
    content: str
    confidence: InsightConfidence
    created_at: datetime
    updated_at: datetime
    evidence: list[Evidence] = field(default_factory=list)
    related_insights: list[str] = field(default_factory=list)  # IDs
    supporting_patterns: list[str] = field(default_factory=list)  # Pattern IDs
    metadata: dict[str, Any] = field(default_factory=dict)
    
    # Evolution tracking
    revision_count: int = 0
    superseded_by: str | None = None  # ID of newer insight that replaces this
    
    def __post_init__(self):
        if not self.id:
            self.id = self._generate_id()
    
    def _generate_id(self) -> str:
        """Generate deterministic ID from insight content."""
        content = f"{self.insight_type.name}:{self.content[:100]}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]
    
    def add_evidence(self, evidence: Evidence) -> None:
        """Add supporting evidence and update confidence."""
        self.evidence.append(evidence)
        self.updated_at = datetime.utcnow()
        self.revision_count += 1
        self._recalculate_confidence()
    
    def _recalculate_confidence(self) -> None:
        """Update confidence based on accumulated evidence."""
        total_weight = sum(e.weight for e in self.evidence)
        unique_sources = len(set(e.source_type for e in self.evidence))
        temporal_span = 0
        
        if len(self.evidence) > 1:
            timestamps = sorted(e.timestamp for e in self.evidence)
            temporal_span = (timestamps[-1] - timestamps[0]).total_seconds() / 86400  # days
        
        # Weight by: total evidence, source diversity, temporal consistency
        score = min(
            (total_weight * 0.4) + 
            (unique_sources * 0.2) + 
            (min(temporal_span / 7, 1.0) * 0.2) +  # Bonus for evidence spanning time
            (self.revision_count * 0.1),
            1.0
        )
        
        if score < 0.35:
            self.confidence = InsightConfidence.SPECULATIVE
        elif score < 0.65:
            self.confidence = InsightConfidence.PROBABLE
        elif score < 0.85:
            self.confidence = InsightConfidence.LIKELY
        else:
            self.confidence = InsightConfidence.CERTAIN
    
    def relates_to(self, other_insight_id: str) -> None:
        """Mark relationship to another insight."""
        if other_insight_id not in self.related_insights:
            self.related_insights.append(other_insight_id)
    
    def supports_pattern(self, pattern_id: str) -> None:
        """Link this insight to a supporting pattern."""
        if pattern_id not in self.supporting_patterns:
            self.supporting_patterns.append(pattern_id)
    
    def is_superseded(self, newer_insight_id: str) -> None:
        """Mark this insight as superseded by a newer one."""
        self.superseded_by = newer_insight_id
    
    def is_active(self) -> bool:
        """Check if this insight is still active (not superseded)."""
        return self.superseded_by is None
    
    def age_days(self) -> float:
        """Calculate age of insight in days."""
        return (datetime.utcnow() - self.created_at).total_seconds() / 86400
    
    def to_dict(self) -> dict[str, Any]:
        return {
            'id': self.id,
            'type': self.insight_type.name,
            'content': self.content,
            'confidence': self.confidence.name,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'evidence_count': len(self.evidence),
            'evidence': [e.to_dict() for e in self.evidence[:5]],  # Limit in export
            'related_insights': self.related_insights,
            'supporting_patterns': self.supporting_patterns,
            'revision_count': self.revision_count,
            'superseded_by': self.superseded_by,
            'is_active': self.is_active(),
            'metadata': self.metadata
        }


class InsightExtractor:
    """
    Extracts insights from patterns and interactions.
    
    Insights emerge from the field of observation—they are not
    extracted mechanically but recognized as resonant structures.
    """
    
    def __init__(self):
        self._insights: dict[str, Insight] = {}
        self._insights_by_type: dict[InsightType, list[str]] = {
            t: [] for t in InsightType
        }
        self._pattern_to_insights: dict[str, list[str]] = {}  # pattern_id -> insight_ids
    
    def extract_from_pattern(self, pattern: Pattern, context: dict[str, Any] | None = None) -> list[Insight]:
        """
        Extract insights from a detected pattern.
        
        Different pattern types yield different insight types.
        """
        insights: list[Insight] = []
        context = context or {}
        
        if pattern.pattern_type == PatternType.BEHAVIORAL:
            insights.extend(self._extract_behavioral_insights(pattern, context))
        
        elif pattern.pattern_type == PatternType.SEMANTIC:
            insights.extend(self._extract_semantic_insights(pattern, context))
        
        elif pattern.pattern_type == PatternType.TEMPORAL:
            insights.extend(self._extract_temporal_insights(pattern, context))
        
        elif pattern.pattern_type == PatternType.CONTRADICTORY:
            insights.extend(self._extract_tension_insights(pattern, context))
        
        elif pattern.pattern_type == PatternType.SEQUENTIAL:
            insights.extend(self._extract_sequential_insights(pattern, context))
        
        # Store insights and link to pattern
        for insight in insights:
            self._store_insight(insight)
            insight.supports_pattern(pattern.id)
            
            if pattern.id not in self._pattern_to_insights:
                self._pattern_to_insights[pattern.id] = []
            self._pattern_to_insights[pattern.id].append(insight.id)
        
        return insights
    
    def _extract_behavioral_insights(
        self, 
        pattern: Pattern, 
        context: dict[str, Any]
    ) -> list[Insight]:
        """Extract insights from behavioral patterns."""
        insights = []
        
        # Preference detection
        if pattern.occurrences >= 3 and pattern.strength.value >= PatternStrength.RESONANT.value:
            insight = Insight(
                id="",
                insight_type=InsightType.PREFERENCE,
                content=f"User shows consistent behavior: {pattern.elements[0] if pattern.elements else 'observed pattern'}",
                confidence=InsightConfidence.PROBABLE,
                created_at=pattern.first_seen,
                updated_at=pattern.last_seen,
                metadata={
                    'pattern_strength': pattern.strength.name,
                    'occurrences': pattern.occurrences
                }
            )
            insight.add_evidence(Evidence(
                source_type='pattern',
                source_id=pattern.id,
                content=pattern.elements,
                timestamp=pattern.last_seen,
                weight=0.7
            ))
            insights.append(insight)
        
        return insights
    
    def _extract_semantic_insights(
        self, 
        pattern: Pattern, 
        context: dict[str, Any]
    ) -> list[Insight]:
        """Extract insights from semantic patterns."""
        insights = []
        
        # Goal detection from repeated focus
        if pattern.occurrences >= 2 and len(pattern.elements) > 0:
            content = str(pattern.elements[0])
            
            # Simple goal indicators
            goal_indicators = ['want', 'need', 'goal', 'plan', 'trying to', 'working on']
            if any(ind in content.lower() for ind in goal_indicators):
                insight = Insight(
                    id="",
                    insight_type=InsightType.GOAL,
                    content=f"User goal detected: {content[:100]}",
                    confidence=InsightConfidence.PROBABLE,
                    created_at=pattern.first_seen,
                    updated_at=pattern.last_seen,
                    metadata={'indicators': goal_indicators}
                )
                insight.add_evidence(Evidence(
                    source_type='pattern',
                    source_id=pattern.id,
                    content=content,
                    timestamp=pattern.last_seen,
                    weight=0.6
                ))
                insights.append(insight)
        
        # Need detection
        need_indicators = ['struggling', 'difficult', 'hard to', 'can\'t', 'problem']
        if any(ind in str(pattern.elements).lower() for ind in need_indicators):
            insight = Insight(
                id="",
                insight_type=InsightType.NEED,
                content=f"Potential unmet need detected in pattern",
                confidence=InsightConfidence.SPECULATIVE,
                created_at=pattern.first_seen,
                updated_at=pattern.last_seen
            )
            insight.add_evidence(Evidence(
                source_type='pattern',
                source_id=pattern.id,
                content=pattern.elements,
                timestamp=pattern.last_seen,
                weight=0.5
            ))
            insights.append(insight)
        
        return insights
    
    def _extract_temporal_insights(
        self, 
        pattern: Pattern, 
        context: dict[str, Any]
    ) -> list[Insight]:
        """Extract insights from temporal patterns."""
        insights = []
        
        # Behavioral rhythm insight
        hour = pattern.metadata.get('hour')
        day = pattern.metadata.get('day')
        
        if hour is not None and pattern.occurrences >= 3:
            time_desc = f"{hour}:00"
            if day is not None:
                days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
                time_desc = f"{days[day]}s around {hour}:00"
            
            insight = Insight(
                id="",
                insight_type=InsightType.PREFERENCE,
                content=f"User shows temporal pattern: active during {time_desc}",
                confidence=InsightConfidence.LIKELY if pattern.occurrences >= 5 else InsightConfidence.PROBABLE,
                created_at=pattern.first_seen,
                updated_at=pattern.last_seen,
                metadata={'hour': hour, 'day': day}
            )
            insight.add_evidence(Evidence(
                source_type='pattern',
                source_id=pattern.id,
                content=f"Temporal occurrence at {time_desc}",
                timestamp=pattern.last_seen,
                weight=0.8
            ))
            insights.append(insight)
        
        return insights
    
    def _extract_tension_insights(
        self, 
        pattern: Pattern, 
        context: dict[str, Any]
    ) -> list[Insight]:
        """Extract insights from contradictory patterns (tensions)."""
        insights = []
        
        # Tension/conflict insight
        insight = Insight(
            id="",
            insight_type=InsightType.TENSION,
            content=f"Contradictory patterns detected: {pattern.elements[0] if pattern.elements else 'observed tension'}",
            confidence=InsightConfidence.LIKELY,
            created_at=pattern.first_seen,
            updated_at=pattern.last_seen,
            metadata={'contradiction_type': 'behavioral_inconsistency'}
        )
        insight.add_evidence(Evidence(
            source_type='pattern',
            source_id=pattern.id,
            content=pattern.elements,
            timestamp=pattern.last_seen,
            weight=0.75
        ))
        insights.append(insight)
        
        return insights
    
    def _extract_sequential_insights(
        self, 
        pattern: Pattern, 
        context: dict[str, Any]
    ) -> list[Insight]:
        """Extract insights from sequential patterns."""
        insights = []
        
        # Workflow/capability insight
        if pattern.occurrences >= 3:
            insight = Insight(
                id="",
                insight_type=InsightType.CAPABILITY,
                content=f"User follows consistent workflow: {' -> '.join(pattern.elements[:3])}",
                confidence=InsightConfidence.LIKELY,
                created_at=pattern.first_seen,
                updated_at=pattern.last_seen,
                metadata={'sequence_length': len(pattern.elements)}
            )
            insight.add_evidence(Evidence(
                source_type='pattern',
                source_id=pattern.id,
                content=pattern.elements,
                timestamp=pattern.last_seen,
                weight=0.7
            ))
            insights.append(insight)
        
        return insights
    
    def _store_insight(self, insight: Insight) -> None:
        """Store an insight, merging with existing if similar."""
        # Check for similar existing insight
        for existing_id, existing in self._insights.items():
            if self._insights_similar(existing, insight):
                # Merge evidence
                for evidence in insight.evidence:
                    existing.add_evidence(evidence)
                return
        
        # Store new insight
        self._insights[insight.id] = insight
        self._insights_by_type[insight.insight_type].append(insight.id)
    
    def _insights_similar(self, i1: Insight, i2: Insight) -> bool:
        """Check if two insights are similar enough to merge."""
        if i1.insight_type != i2.insight_type:
            return False
        
        # Simple content similarity
        content_sim = self._text_similarity(i1.content, i2.content)
        return content_sim > 0.7
    
    def _text_similarity(self, t1: str, t2: str) -> float:
        """Calculate simple text similarity."""
        words1 = set(t1.lower().split())
        words2 = set(t2.lower().split())
        
        if not words1 or not words2:
            return 0.0
        
        intersection = len(words1 & words2)
        union = len(words1 | words2)
        
        return intersection / union if union > 0 else 0.0
    
    def get_insights(
        self,
        insight_type: InsightType | None = None,
        min_confidence: InsightConfidence = InsightConfidence.SPECULATIVE,
        active_only: bool = True
    ) -> list[Insight]:
        """Retrieve insights with optional filtering."""
        confidence_order = list(InsightConfidence)
        min_index = confidence_order.index(min_confidence)
        
        if insight_type:
            insight_ids = self._insights_by_type.get(insight_type, [])
        else:
            insight_ids = list(self._insights.keys())
        
        results = []
        for iid in insight_ids:
            insight = self._insights.get(iid)
            if not insight:
                continue
            
            if active_only and not insight.is_active():
                continue
            
            if confidence_order.index(insight.confidence) < min_index:
                continue
            
            results.append(insight)
        
        # Sort by confidence (descending), then by recency
        results.sort(key=lambda i: (
            confidence_order.index(i.confidence),
            i.updated_at
        ), reverse=True)
        
        return results
    
    def get_insights_for_pattern(self, pattern_id: str) -> list[Insight]:
        """Get all insights derived from a specific pattern."""
        insight_ids = self._pattern_to_insights.get(pattern_id, [])
        return [self._insights[iid] for iid in insight_ids if iid in self._insights]
    
    def find_related_insights(self, insight_id: str, depth: int = 1) -> list[tuple[Insight, int]]:
        """
        Find insights related to the given insight.
        
        Returns: List of (insight, depth) tuples.
        """
        if insight_id not in self._insights:
            return []
        
        visited = {insight_id}
        related = []
        queue = [(rid, 1) for rid in self._insights[insight_id].related_insights]
        
        while queue and queue[0][1] <= depth:
            rid, d = queue.pop(0)
            if rid in visited:
                continue
            
            visited.add(rid)
            if rid in self._insights:
                related.append((self._insights[rid], d))
                
                if d < depth:
                    for next_rid in self._insights[rid].related_insights:
                        if next_rid not in visited:
                            queue.append((next_rid, d + 1))
        
        return related
    
    def consolidate(self) -> list[Insight]:
        """
        Consolidate insights: remove superseded ones, merge similar ones.
        
        Returns: List of consolidated insights.
        """
        active_insights = [i for i in self._insights.values() if i.is_active()]
        
        # Sort by confidence and recency
        active_insights.sort(
            key=lambda i: (list(InsightConfidence).index(i.confidence), i.updated_at),
            reverse=True
        )
        
        consolidated = []
        seen_content = set()
        
        for insight in active_insights:
            # Skip if very similar to already kept insight
            content_hash = hashlib.sha256(
                f"{insight.insight_type.name}:{insight.content[:50]}".encode()
            ).hexdigest()[:16]
            
            if content_hash not in seen_content:
                consolidated.append(insight)
                seen_content.add(content_hash)
        
        return consolidated
    
    def export_insights(self) -> dict[str, Any]:
        """Export all insights for persistence."""
        return {
            'timestamp': datetime.utcnow().isoformat(),
            'insights': [i.to_dict() for i in self._insights.values()],
            'statistics': {
                'total': len(self._insights),
                'by_type': {
                    t.name: len(ids) 
                    for t, ids in self._insights_by_type.items()
                },
                'active': sum(1 for i in self._insights.values() if i.is_active())
            }
        }
    
    def import_insights(self, data: dict[str, Any]) -> None:
        """Import insights from persisted state."""
        for i_data in data.get('insights', []):
            insight = Insight(
                id=i_data['id'],
                insight_type=InsightType[i_data['type']],
                content=i_data['content'],
                confidence=InsightConfidence[i_data['confidence']],
                created_at=datetime.fromisoformat(i_data['created_at']),
                updated_at=datetime.fromisoformat(i_data['updated_at']),
                related_insights=i_data.get('related_insights', []),
                supporting_patterns=i_data.get('supporting_patterns', []),
                revision_count=i_data.get('revision_count', 0),
                superseded_by=i_data.get('superseded_by'),
                metadata=i_data.get('metadata', {})
            )
            
            # Restore evidence
            for e_data in i_data.get('evidence', []):
                evidence = Evidence(
                    source_type=e_data['source_type'],
                    source_id=e_data['source_id'],
                    content=e_data['content'],
                    timestamp=datetime.fromisoformat(e_data['timestamp']),
                    weight=e_data['weight']
                )
                insight.evidence.append(evidence)
            
            self._insights[insight.id] = insight
            self._insights_by_type[insight.insight_type].append(insight.id)
