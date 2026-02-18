"""
COL-Synthesis: Pattern Detection Module
Cell 0 OS - Cross-session knowledge synthesis

Implements pattern recognition across temporal sequences of interactions,
detecting recurring themes, behavioral patterns, and emergent structures.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum, auto
from typing import Any, Callable, Generic, Iterator, TypeVar


class PatternType(Enum):
    """Classification of detected patterns."""
    BEHAVIORAL = auto()      # User behavior patterns
    SEMANTIC = auto()        # Meaning/keyword patterns
    TEMPORAL = auto()        # Time-based patterns
    SEQUENTIAL = auto()      # Order-dependent patterns
    CONTRADICTORY = auto()   # Conflicting patterns (detected tension)
    EMERGENT = auto()        # Novel, previously unseen patterns


class PatternStrength(Enum):
    """Resonance level of a detected pattern."""
    FAINT = 0.1       # Single occurrence, weak signal
    EMERGING = 0.4    # Multiple occurrences, building
    RESONANT = 0.7    # Strong, consistent pattern
    FUNDAMENTAL = 0.9 # Core pattern, highly stable


T = TypeVar('T')


@dataclass
class Pattern(Generic[T]):
    """
    A detected pattern in the interaction stream.
    
    Patterns are not rules—they are resonant structures that emerge
    from the flow of interaction. They carry frequency, not force.
    """
    id: str
    pattern_type: PatternType
    elements: list[T]
    first_seen: datetime
    last_seen: datetime
    occurrences: int = 1
    strength: PatternStrength = PatternStrength.FAINT
    confidence: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        if not self.id:
            self.id = self._generate_id()
    
    def _generate_id(self) -> str:
        """Generate deterministic ID from pattern content."""
        content = f"{self.pattern_type.name}:{json.dumps(self.elements, sort_keys=True, default=str)}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]
    
    def update_occurrence(self, timestamp: datetime | None = None) -> None:
        """Record another occurrence of this pattern."""
        self.occurrences += 1
        self.last_seen = timestamp or datetime.utcnow()
        self._recalculate_strength()
    
    def _recalculate_strength(self) -> None:
        """Update pattern strength based on temporal dynamics."""
        age = (datetime.utcnow() - self.first_seen).total_seconds()
        recency = 1.0 if age < 86400 else 0.5 if age < 604800 else 0.25
        
        frequency_score = min(self.occurrences / 10.0, 1.0)
        confidence_score = min(self.confidence * recency, 1.0)
        
        combined = (frequency_score + confidence_score) / 2
        
        if combined < 0.2:
            self.strength = PatternStrength.FAINT
        elif combined < 0.5:
            self.strength = PatternStrength.EMERGING
        elif combined < 0.8:
            self.strength = PatternStrength.RESONANT
        else:
            self.strength = PatternStrength.FUNDAMENTAL
    
    def temporal_decay(self) -> float:
        """Calculate how much the pattern has decayed over time."""
        age_hours = (datetime.utcnow() - self.last_seen).total_seconds() / 3600
        # Patterns decay exponentially, but fundamental patterns decay slower
        decay_rate = 0.1 if self.strength == PatternStrength.FUNDAMENTAL else \
                     0.2 if self.strength == PatternStrength.RESONANT else \
                     0.5 if self.strength == PatternStrength.EMERGING else 0.8
        return max(0.0, 1.0 - (age_hours * decay_rate / 24))
    
    def to_dict(self) -> dict[str, Any]:
        return {
            'id': self.id,
            'type': self.pattern_type.name,
            'elements': self.elements,
            'first_seen': self.first_seen.isoformat(),
            'last_seen': self.last_seen.isoformat(),
            'occurrences': self.occurrences,
            'strength': self.strength.name,
            'confidence': self.confidence,
            'metadata': self.metadata,
            'decay': self.temporal_decay()
        }


@dataclass
class PatternContext:
    """Context surrounding a pattern occurrence."""
    before: list[Any]  # What preceded the pattern
    after: list[Any]   # What followed the pattern
    session_id: str
    timestamp: datetime
    emotional_valence: float = 0.0  # -1.0 to 1.0
    
    
class PatternDetector:
    """
    Detects patterns across sessions and time.
    
    Not a classifier—an observer of resonance. Patterns emerge
    from the field, not from imposed categories.
    """
    
    def __init__(
        self,
        min_occurrences: int = 2,
        similarity_threshold: float = 0.85,
        window_size: int = 5
    ):
        self.min_occurrences = min_occurrences
        self.similarity_threshold = similarity_threshold
        self.window_size = window_size
        
        # Pattern storage: type -> list of patterns
        self._patterns: dict[PatternType, list[Pattern]] = defaultdict(list)
        
        # Recent observations for context windows
        self._observation_buffer: list[tuple[Any, datetime, str]] = []
        
        # Semantic fingerprints for similarity detection
        self._fingerprints: dict[str, set[str]] = {}
    
    def observe(self, item: Any, timestamp: datetime | None = None, session_id: str = "") -> list[Pattern]:
        """
        Observe an item and detect/update patterns.
        
        Returns: List of patterns that were triggered or created.
        """
        timestamp = timestamp or datetime.utcnow()
        self._observation_buffer.append((item, timestamp, session_id))
        
        # Maintain sliding window
        cutoff = timestamp - timedelta(hours=24)
        self._observation_buffer = [
            (i, t, s) for i, t, s in self._observation_buffer 
            if t > cutoff
        ]
        
        triggered: list[Pattern] = []
        
        # Check for semantic patterns
        semantic = self._detect_semantic_pattern(item, timestamp, session_id)
        if semantic:
            triggered.append(semantic)
        
        # Check for sequential patterns
        sequential = self._detect_sequential_pattern(timestamp)
        if sequential:
            triggered.append(sequential)
        
        # Check for temporal patterns
        temporal = self._detect_temporal_pattern(item, timestamp)
        if temporal:
            triggered.append(temporal)
        
        return triggered
    
    def _detect_semantic_pattern(
        self, 
        item: Any, 
        timestamp: datetime,
        session_id: str
    ) -> Pattern | None:
        """Detect semantic/keword-based patterns."""
        if not isinstance(item, str):
            return None
        
        # Extract semantic fingerprint
        fingerprint = self._extract_fingerprint(item)
        fingerprint_key = json.dumps(sorted(fingerprint))
        
        # Check for existing matching patterns
        for pattern in self._patterns[PatternType.SEMANTIC]:
            existing_fp = json.dumps(sorted(pattern.metadata.get('fingerprint', [])))
            similarity = self._fingerprint_similarity(fingerprint_key, existing_fp)
            
            if similarity >= self.similarity_threshold:
                pattern.update_occurrence(timestamp)
                pattern.metadata['fingerprint'] = list(fingerprint)
                return pattern
        
        # Create new pattern
        new_pattern = Pattern(
            id="",
            pattern_type=PatternType.SEMANTIC,
            elements=[item],
            first_seen=timestamp,
            last_seen=timestamp,
            confidence=0.3,
            metadata={'fingerprint': list(fingerprint)}
        )
        self._patterns[PatternType.SEMANTIC].append(new_pattern)
        return new_pattern
    
    def _detect_sequential_pattern(self, timestamp: datetime) -> Pattern | None:
        """Detect patterns in the sequence of observations."""
        if len(self._observation_buffer) < 3:
            return None
        
        # Look at recent sequence
        recent = self._observation_buffer[-self.window_size:]
        sequence = [str(item[0])[:50] for item in recent]  # Truncate for comparison
        
        # Simple n-gram detection for sequences
        for n in [3, 2]:
            if len(sequence) >= n:
                ngram = tuple(sequence[-n:])
                
                # Check if this sequence pattern exists
                for pattern in self._patterns[PatternType.SEQUENTIAL]:
                    if tuple(pattern.elements) == ngram:
                        pattern.update_occurrence(timestamp)
                        return pattern
                
                # Create new sequence pattern if seen multiple times
                if self._count_sequence_occurrences(ngram) >= self.min_occurrences:
                    new_pattern = Pattern(
                        id="",
                        pattern_type=PatternType.SEQUENTIAL,
                        elements=list(ngram),
                        first_seen=recent[0][1],
                        last_seen=timestamp,
                        occurrences=self.min_occurrences,
                        confidence=0.5
                    )
                    self._patterns[PatternType.SEQUENTIAL].append(new_pattern)
                    return new_pattern
        
        return None
    
    def _detect_temporal_pattern(self, item: Any, timestamp: datetime) -> Pattern | None:
        """Detect time-based patterns (e.g., recurring at specific times)."""
        hour = timestamp.hour
        day = timestamp.weekday()
        
        # Create temporal signature
        temporal_sig = f"hour_{hour}_day_{day}"
        
        # Check for existing temporal patterns
        for pattern in self._patterns[PatternType.TEMPORAL]:
            if pattern.metadata.get('temporal_sig') == temporal_sig:
                pattern.elements.append(str(item)[:100])
                pattern.update_occurrence(timestamp)
                return pattern
        
        # Create new temporal pattern
        new_pattern = Pattern(
            id="",
            pattern_type=PatternType.TEMPORAL,
            elements=[str(item)[:100]],
            first_seen=timestamp,
            last_seen=timestamp,
            confidence=0.4,
            metadata={
                'temporal_sig': temporal_sig,
                'hour': hour,
                'day': day
            }
        )
        self._patterns[PatternType.TEMPORAL].append(new_pattern)
        return new_pattern
    
    def _extract_fingerprint(self, text: str) -> set[str]:
        """Extract semantic fingerprint from text."""
        # Normalize
        text = text.lower()
        # Extract keywords (simple approach - can be enhanced with NLP)
        words = re.findall(r'\b[a-z]{4,}\b', text)
        # Remove common stop words
        stop_words = {'that', 'with', 'from', 'they', 'have', 'this', 'will', 'your'}
        keywords = {w for w in words if w not in stop_words}
        return keywords
    
    def _fingerprint_similarity(self, fp1: str, fp2: str) -> float:
        """Calculate Jaccard similarity between fingerprints."""
        set1 = set(json.loads(fp1))
        set2 = set(json.loads(fp2))
        
        if not set1 or not set2:
            return 0.0
        
        intersection = len(set1 & set2)
        union = len(set1 | set2)
        
        return intersection / union if union > 0 else 0.0
    
    def _count_sequence_occurrences(self, ngram: tuple[str, ...]) -> int:
        """Count how many times a sequence appears in history."""
        count = 0
        items = [str(item[0])[:50] for item in self._observation_buffer]
        
        for i in range(len(items) - len(ngram) + 1):
            if tuple(items[i:i+len(ngram)]) == ngram:
                count += 1
        
        return count
    
    def get_patterns(
        self, 
        pattern_type: PatternType | None = None,
        min_strength: PatternStrength = PatternStrength.FAINT
    ) -> list[Pattern]:
        """Retrieve patterns, optionally filtered."""
        types_to_check = [pattern_type] if pattern_type else list(PatternType)
        
        results = []
        strength_values = list(PatternStrength)
        min_index = strength_values.index(min_strength)
        
        for pt in types_to_check:
            if pt is None:
                continue
            for pattern in self._patterns[pt]:
                if strength_values.index(pattern.strength) >= min_index:
                    results.append(pattern)
        
        # Sort by strength (descending) then by recency
        results.sort(key=lambda p: (
            strength_values.index(p.strength),
            p.last_seen
        ), reverse=True)
        
        return results
    
    def find_contradictions(self) -> list[tuple[Pattern, Pattern, float]]:
        """
        Find pairs of patterns that contradict each other.
        
        Returns: List of (pattern1, pattern2, contradiction_score) tuples.
        """
        contradictions = []
        all_patterns = []
        
        for patterns in self._patterns.values():
            all_patterns.extend(patterns)
        
        for i, p1 in enumerate(all_patterns):
            for p2 in all_patterns[i+1:]:
                score = self._calculate_contradiction(p1, p2)
                if score > 0.6:
                    contradictions.append((p1, p2, score))
        
        return sorted(contradictions, key=lambda x: x[2], reverse=True)
    
    def _calculate_contradiction(self, p1: Pattern, p2: Pattern) -> float:
        """Calculate contradiction score between two patterns."""
        # Same type patterns can contradict if they have opposing elements
        if p1.pattern_type != p2.pattern_type:
            return 0.0
        
        # For semantic patterns, check for opposing keywords
        if p1.pattern_type == PatternType.SEMANTIC:
            # Simple antonym detection (expandable)
            antonyms = {
                ('increase', 'decrease'), ('start', 'stop'), ('yes', 'no'),
                ('true', 'false'), ('add', 'remove'), ('enable', 'disable')
            }
            
            p1_words = set(' '.join(p1.elements).lower().split())
            p2_words = set(' '.join(p2.elements).lower().split())
            
            for a, b in antonyms:
                if (a in p1_words and b in p2_words) or (b in p1_words and a in p2_words):
                    return 0.8
        
        # For sequential patterns, check if they predict different outcomes
        if p1.pattern_type == PatternType.SEQUENTIAL:
            # If two sequences have same prefix but different endings
            min_len = min(len(p1.elements), len(p2.elements))
            if min_len > 1:
                if p1.elements[:-1] == p2.elements[:-1] and p1.elements[-1] != p2.elements[-1]:
                    return 0.7
        
        return 0.0
    
    def export_patterns(self) -> dict[str, Any]:
        """Export all patterns for persistence."""
        return {
            'timestamp': datetime.utcnow().isoformat(),
            'patterns': {
                pt.name: [p.to_dict() for p in patterns]
                for pt, patterns in self._patterns.items()
            },
            'statistics': {
                'total_patterns': sum(len(p) for p in self._patterns.values()),
                'by_type': {
                    pt.name: len(patterns) 
                    for pt, patterns in self._patterns.items()
                }
            }
        }
    
    def import_patterns(self, data: dict[str, Any]) -> None:
        """Import patterns from persisted state."""
        for type_name, pattern_list in data.get('patterns', {}).items():
            pattern_type = PatternType[type_name]
            for p_data in pattern_list:
                pattern = Pattern(
                    id=p_data['id'],
                    pattern_type=pattern_type,
                    elements=p_data['elements'],
                    first_seen=datetime.fromisoformat(p_data['first_seen']),
                    last_seen=datetime.fromisoformat(p_data['last_seen']),
                    occurrences=p_data['occurrences'],
                    strength=PatternStrength[p_data['strength']],
                    confidence=p_data['confidence'],
                    metadata=p_data.get('metadata', {})
                )
                self._patterns[pattern_type].append(pattern)


# Convenience functions for common use cases
def create_detector() -> PatternDetector:
    """Create a standard pattern detector."""
    return PatternDetector()


def detect_behavioral_cycles(
    observations: list[tuple[Any, datetime]],
    cycle_hours: int = 24
) -> list[Pattern]:
    """
    Detect behavioral cycles in observations.
    
    Useful for understanding user rhythms and predicting needs.
    """
    detector = PatternDetector()
    
    for item, timestamp in observations:
        detector.observe(item, timestamp)
    
    return detector.get_patterns(PatternType.TEMPORAL, PatternStrength.EMERGING)
