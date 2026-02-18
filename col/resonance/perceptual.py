"""
COL Resonance Module - Perceptual Coherence
Cell 0 OS - TPV Architecture

Perceptual coherence ensures consistent interpretation across contexts.
This is the 'what' layer of TPV - how the system perceives, categorizes,
and maintains stable interpretations of reality.
"""

import asyncio
import math
import hashlib
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from typing import Any, Dict, List, Optional, Set, Tuple, Callable, Union
from collections import defaultdict
import json


class PerceptualDomain(Enum):
    """Domains of perception."""
    LINGUISTIC = auto()      # Text and language
    SEMANTIC = auto()        # Meaning and concepts
    EMOTIONAL = auto()       # Emotional tones
    CONTEXTUAL = auto()      # Situational context
    RELATIONAL = auto()      # Relationships between entities
    TEMPORAL = auto()        # Time-based patterns
    SPATIAL = auto()         # Spatial/structural patterns


class CoherenceLevel(Enum):
    """Levels of perceptual coherence."""
    DISSONANT = auto()       # Conflicting interpretations
    UNSTABLE = auto()        # Shifting, unclear
    EMERGING = auto()        # Pattern forming
    STABLE = auto()          # Consistent interpretation
    RESONANT = auto()        # Deeply coherent, harmonious


@dataclass
class PerceptualFrame:
    """A single perceptual snapshot."""
    frame_id: str
    domain: PerceptualDomain
    raw_input: Any
    interpretation: Dict[str, Any]
    confidence: float
    timestamp: float
    context_hash: str
    coherence_with_previous: float = 0.0
    
    def get_fingerprint(self) -> str:
        """Generate unique fingerprint of this perception."""
        data = f"{self.domain.name}:{json.dumps(self.interpretation, sort_keys=True)}"
        return hashlib.sha256(data.encode()).hexdigest()[:16]


@dataclass
class InterpretationCluster:
    """Cluster of similar interpretations."""
    cluster_id: str
    domain: PerceptualDomain
    centroid: Dict[str, Any]
    frames: List[PerceptualFrame] = field(default_factory=list)
    coherence_score: float = 0.0
    stability: float = 0.0  # How stable this interpretation is
    last_updated: float = field(default_factory=lambda: __import__('time').time())
    
    def add_frame(self, frame: PerceptualFrame) -> None:
        """Add a frame to the cluster."""
        self.frames.append(frame)
        self.last_updated = __import__('time').time()
        self._update_centroid()
        self._update_stability()
    
    def _update_centroid(self) -> None:
        """Update cluster centroid from frames."""
        if not self.frames:
            return
        # Simple centroid update - could use more sophisticated methods
        keys = self.frames[0].interpretation.keys()
        for key in keys:
            values = [f.interpretation.get(key) for f in self.frames if key in f.interpretation]
            if values and all(isinstance(v, (int, float)) for v in values if v is not None):
                self.centroid[key] = sum(v for v in values if v is not None) / len([v for v in values if v is not None])
    
    def _update_stability(self) -> None:
        """Update stability score based on frame consistency."""
        if len(self.frames) < 2:
            self.stability = 0.5
            return
        
        # Calculate variance in confidence
        confidences = [f.confidence for f in self.frames[-10:]]  # Last 10
        if confidences:
            mean_conf = sum(confidences) / len(confidences)
            variance = sum((c - mean_conf) ** 2 for c in confidences) / len(confidences)
            self.stability = max(0.0, 1.0 - variance)


@dataclass
class PerceptualSchema:
    """
    Stable pattern of interpretation across multiple contexts.
    
    A schema is like a lens - it provides a consistent way of
    perceiving and interpreting incoming information.
    """
    schema_id: str
    name: str
    domains: Set[PerceptualDomain]
    pattern: Dict[str, Any]  # The interpretive pattern
    confidence_threshold: float = 0.7
    activation_count: int = 0
    success_rate: float = 1.0
    created_at: float = field(default_factory=lambda: __import__('time').time())
    last_activated: Optional[float] = None
    
    def matches(self, perception: PerceptualFrame) -> float:
        """Return match score 0-1 between schema and perception."""
        if perception.domain not in self.domains:
            return 0.0
        
        # Compare pattern to interpretation
        matches = 0
        total = 0
        for key, expected in self.pattern.items():
            if key in perception.interpretation:
                actual = perception.interpretation[key]
                total += 1
                if isinstance(expected, (int, float)) and isinstance(actual, (int, float)):
                    # Numerical similarity
                    diff = abs(expected - actual)
                    matches += max(0.0, 1.0 - diff / max(abs(expected), 1.0))
                elif expected == actual:
                    matches += 1
        
        return matches / max(total, 1)
    
    def activate(self) -> None:
        """Record activation of this schema."""
        self.activation_count += 1
        self.last_activated = __import__('time').time()


class PerceptualCoherence:
    """
    Maintains consistent perception across contexts.
    
    This is the 'what' of TPV - ensuring that the system's
    interpretation of reality remains coherent and stable.
    """
    
    def __init__(
        self,
        coherence_threshold: float = 0.6,
        max_clusters: int = 100,
        max_schemas: int = 50,
    ):
        self.coherence_threshold = coherence_threshold
        self.frames: Dict[PerceptualDomain, List[PerceptualFrame]] = defaultdict(list)
        self.clusters: Dict[str, InterpretationCluster] = {}
        self.schemas: Dict[str, PerceptualSchema] = {}
        self.current_level: CoherenceLevel = CoherenceLevel.EMERGING
        
        # Domain coherence scores
        self.domain_coherence: Dict[PerceptualDomain, float] = {
            domain: 0.5 for domain in PerceptualDomain
        }
        
        # Cross-domain mappings
        self.cross_domain_links: Dict[Tuple[PerceptualDomain, PerceptualDomain], float] = {}
        
        self._lock = asyncio.Lock()
    
    async def perceive(
        self,
        domain: PerceptualDomain,
        raw_input: Any,
        interpretation: Dict[str, Any],
        confidence: float,
        context: Optional[Dict] = None,
    ) -> PerceptualFrame:
        """
        Process a new perception.
        
        This is the main entry point for adding perceptions to the system.
        """
        async with self._lock:
            import time
            
            # Create context hash
            context_hash = self._hash_context(context or {})
            
            # Create frame
            frame = PerceptualFrame(
                frame_id=f"frame_{domain.name}_{time.time():.6f}",
                domain=domain,
                raw_input=raw_input,
                interpretation=interpretation,
                confidence=confidence,
                timestamp=time.time(),
                context_hash=context_hash
            )
            
            # Calculate coherence with previous frames in same domain
            if self.frames[domain]:
                prev_frame = self.frames[domain][-1]
                frame.coherence_with_previous = self._calculate_similarity(
                    frame.interpretation, prev_frame.interpretation
                )
            
            # Store frame
            self.frames[domain].append(frame)
            
            # Update domain coherence
            await self._update_domain_coherence(domain, frame)
            
            # Add to or create cluster
            await self._cluster_frame(frame)
            
            # Try to activate schemas
            await self._activate_schemas(frame)
            
            # Update overall coherence level
            await self._update_coherence_level()
            
            return frame
    
    def _hash_context(self, context: Dict) -> str:
        """Create hash of context for comparison."""
        return hashlib.sha256(
            json.dumps(context, sort_keys=True, default=str).encode()
        ).hexdigest()[:16]
    
    def _calculate_similarity(self, a: Dict, b: Dict) -> float:
        """Calculate similarity between two interpretations."""
        if not a or not b:
            return 0.0
        
        # Jaccard-like similarity
        keys_a = set(a.keys())
        keys_b = set(b.keys())
        intersection = keys_a & keys_b
        union = keys_a | keys_b
        
        if not union:
            return 1.0
        
        # Weight by value similarity for common keys
        value_sim = 0.0
        for key in intersection:
            val_a = a[key]
            val_b = b[key]
            if val_a == val_b:
                value_sim += 1.0
            elif isinstance(val_a, (int, float)) and isinstance(val_b, (int, float)):
                diff = abs(val_a - val_b)
                max_val = max(abs(val_a), abs(val_b), 1.0)
                value_sim += 1.0 - (diff / max_val)
        
        return (len(intersection) / len(union)) * (value_sim / max(len(intersection), 1))
    
    async def _update_domain_coherence(self, domain: PerceptualDomain, frame: PerceptualFrame) -> None:
        """Update coherence score for a domain."""
        # Exponential moving average
        alpha = 0.3
        current = self.domain_coherence[domain]
        
        if frame.coherence_with_previous > 0:
            new_coherence = alpha * frame.coherence_with_previous + (1 - alpha) * current
            self.domain_coherence[domain] = new_coherence
    
    async def _cluster_frame(self, frame: PerceptualFrame) -> None:
        """Add frame to appropriate cluster or create new one."""
        # Find best matching cluster
        best_cluster = None
        best_match = 0.0
        
        for cluster in self.clusters.values():
            if cluster.domain == frame.domain:
                similarity = self._calculate_similarity(
                    frame.interpretation, cluster.centroid
                )
                if similarity > best_match and similarity > 0.6:
                    best_match = similarity
                    best_cluster = cluster
        
        if best_cluster:
            best_cluster.add_frame(frame)
        else:
            # Create new cluster
            import time
            cluster_id = f"cluster_{frame.domain.name}_{time.time():.6f}"
            cluster = InterpretationCluster(
                cluster_id=cluster_id,
                domain=frame.domain,
                centroid=frame.interpretation.copy(),
                frames=[frame]
            )
            self.clusters[cluster_id] = cluster
    
    async def _activate_schemas(self, frame: PerceptualFrame) -> List[PerceptualSchema]:
        """Activate schemas that match this frame."""
        activated = []
        
        for schema in self.schemas.values():
            match_score = schema.matches(frame)
            if match_score >= schema.confidence_threshold:
                schema.activate()
                activated.append(schema)
        
        return activated
    
    async def _update_coherence_level(self) -> None:
        """Update overall coherence level based on domain scores."""
        avg_coherence = sum(self.domain_coherence.values()) / len(self.domain_coherence)
        
        if avg_coherence > 0.9:
            self.current_level = CoherenceLevel.RESONANT
        elif avg_coherence > 0.75:
            self.current_level = CoherenceLevel.STABLE
        elif avg_coherence > 0.5:
            self.current_level = CoherenceLevel.EMERGING
        elif avg_coherence > 0.3:
            self.current_level = CoherenceLevel.UNSTABLE
        else:
            self.current_level = CoherenceLevel.DISSONANT
    
    async def create_schema(
        self,
        name: str,
        domains: Set[PerceptualDomain],
        pattern: Dict[str, Any],
        confidence_threshold: float = 0.7
    ) -> PerceptualSchema:
        """Create a new perceptual schema."""
        import time
        
        schema = PerceptualSchema(
            schema_id=f"schema_{name}_{time.time():.6f}",
            name=name,
            domains=domains,
            pattern=pattern,
            confidence_threshold=confidence_threshold
        )
        
        self.schemas[schema.schema_id] = schema
        return schema
    
    def get_domain_coherence(self, domain: PerceptualDomain) -> float:
        """Get coherence score for a specific domain."""
        return self.domain_coherence.get(domain, 0.0)
    
    def get_overall_coherence(self) -> float:
        """Get overall perceptual coherence across all domains."""
        return sum(self.domain_coherence.values()) / len(self.domain_coherence)
    
    def get_consistent_interpretations(
        self,
        domain: PerceptualDomain,
        min_confidence: float = 0.7
    ) -> List[Dict[str, Any]]:
        """Get interpretations that have remained consistent."""
        consistent = []
        for cluster in self.clusters.values():
            if (cluster.domain == domain and 
                cluster.stability >= min_confidence and
                len(cluster.frames) >= 3):
                consistent.append(cluster.centroid)
        return consistent
    
    def link_domains(
        self,
        domain_a: PerceptualDomain,
        domain_b: PerceptualDomain,
        strength: float
    ) -> None:
        """Create or update link between two perceptual domains."""
        key = tuple(sorted([domain_a, domain_b], key=lambda d: d.name))
        self.cross_domain_links[key] = max(0.0, min(1.0, strength))
    
    def get_perceptual_summary(self) -> Dict[str, Any]:
        """Get summary of perceptual coherence state."""
        return {
            "overall_coherence": self.get_overall_coherence(),
            "coherence_level": self.current_level.name,
            "domain_coherence": {
                domain.name: score 
                for domain, score in self.domain_coherence.items()
            },
            "total_frames": sum(len(frames) for frames in self.frames.values()),
            "total_clusters": len(self.clusters),
            "total_schemas": len(self.schemas),
            "cross_domain_links": len(self.cross_domain_links),
            "active_schemas": sum(
                1 for s in self.schemas.values() 
                if s.last_activated and __import__('time').time() - s.last_activated < 3600
            )
        }


# Import moved to top for module clarity (statistics not used in this file)
