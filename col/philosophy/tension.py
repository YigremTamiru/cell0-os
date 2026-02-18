"""
COL Philosophy - Tension Module
================================
Tension detection and resolution algorithms.

This module provides sophisticated algorithms for detecting tensions
between principles and resolving them according to priority hierarchies
and context-aware reasoning.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Any, Callable, Tuple
from enum import Enum, auto
from datetime import datetime
import json

from .principles import (
    Principle, PrinciplePriority, get_principle_registry
)
from .alignment import AlignmentCheck, AlignmentStatus, ViolationSeverity


class TensionType(Enum):
    """Types of tensions between principles."""
    DIRECT_CONFLICT = auto()      # Principles directly oppose each other
    PRIORITY_INVERSION = auto()   # Lower priority overrides higher
    MUTUAL_EXCLUSION = auto()     # Cannot satisfy both simultaneously
    RESOURCE_COMPETITION = auto() # Competing for limited resources
    TEMPORAL_CONFLICT = auto()    # Conflict over timing/sequence
    INTERPRETATION = auto()       # Different interpretations of principles
    SCOPE_OVERLAP = auto()        # Overlapping but conflicting scopes


class ResolutionStrategy(Enum):
    """Strategies for resolving tensions."""
    PRIORITY_BASED = auto()       # Higher priority wins
    TEMPORAL_SEPARATION = auto()  # Satisfy one, then the other
    COMPROMISE = auto()           # Find middle ground
    DELEGATION = auto()           # Delegate to human decision
    EXCEPTION = auto()            # Create temporary exception
    REFRAME = auto()              # Reframe to avoid conflict
    HYBRID = auto()               # Combine multiple strategies
    ABSTAIN = auto()              # Refuse to act


@dataclass
class Tension:
    """
    A detected tension between two or more principles.
    
    Tensions represent situations where principles conflict or compete,
    requiring resolution to proceed with an operation.
    """
    id: str
    name: str
    description: str
    tension_type: TensionType
    principle_ids: List[str]
    context: Dict[str, Any] = field(default_factory=dict)
    detected_at: datetime = field(default_factory=datetime.now)
    severity: ViolationSeverity = ViolationSeverity.MEDIUM
    auto_resolvable: bool = False
    resolution: Optional[Dict[str, Any]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __hash__(self) -> int:
        return hash(self.id)
    
    def __eq__(self, other) -> bool:
        if not isinstance(other, Tension):
            return False
        return self.id == other.id
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "tension_type": self.tension_type.name,
            "principle_ids": self.principle_ids,
            "context": self.context,
            "detected_at": self.detected_at.isoformat(),
            "severity": self.severity.name,
            "auto_resolvable": self.auto_resolvable,
            "resolution": self.resolution,
            "metadata": self.metadata
        }


@dataclass
class ResolutionResult:
    """
    Result of a tension resolution attempt.
    
    Contains the resolution outcome, selected principles, and rationale.
    """
    tension_id: str
    resolved: bool
    strategy: ResolutionStrategy
    winning_principles: List[str]
    suppressed_principles: List[str]
    rationale: str
    requires_notification: bool
    requires_approval: bool
    conditions: List[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "tension_id": self.tension_id,
            "resolved": self.resolved,
            "strategy": self.strategy.name,
            "winning_principles": self.winning_principles,
            "suppressed_principles": self.suppressed_principles,
            "rationale": self.rationale,
            "requires_notification": self.requires_notification,
            "requires_approval": self.requires_approval,
            "conditions": self.conditions,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata
        }


class TensionDetector:
    """
    Detects tensions between principles from alignment checks.
    
    Uses pattern matching and context analysis to identify situations
    where principles conflict or compete.
    """
    
    def __init__(self):
        self.registry = get_principle_registry()
        self._patterns: List[Dict[str, Any]] = []
        self._load_patterns()
    
    def _load_patterns(self):
        """Load known tension patterns."""
        self._patterns = [
            {
                "name": "Sovereignty vs Safety",
                "principles": ["sov.001", "sft.002"],
                "type": TensionType.DIRECT_CONFLICT,
                "description": "User sovereignty conflicts with safety override",
                "severity": ViolationSeverity.HIGH,
                "auto_resolvable": True
            },
            {
                "name": "Harm Prevention vs Autonomy",
                "principles": ["eth.001", "eth.004"],
                "type": TensionType.DIRECT_CONFLICT,
                "description": "Preventing harm may require limiting autonomy",
                "severity": ViolationSeverity.HIGH,
                "auto_resolvable": True
            },
            {
                "name": "Confidentiality vs Transparency",
                "principles": ["prv.002", "trn.001"],
                "type": TensionType.MUTUAL_EXCLUSION,
                "description": "Explaining decisions may reveal confidential data",
                "severity": ViolationSeverity.MEDIUM,
                "auto_resolvable": True
            },
            {
                "name": "Consent vs Emergency Action",
                "principles": ["sov.002", "sft.001"],
                "type": TensionType.TEMPORAL_CONFLICT,
                "description": "Emergency may require action before consent",
                "severity": ViolationSeverity.CRITICAL,
                "auto_resolvable": True
            },
            {
                "name": "Privacy vs Explainability",
                "principles": ["prv.001", "trn.001"],
                "type": TensionType.SCOPE_OVERLAP,
                "description": "Minimal data collection vs detailed explanations",
                "severity": ViolationSeverity.LOW,
                "auto_resolvable": True
            },
            {
                "name": "Autonomy vs Beneficence",
                "principles": ["eth.004", "eth.002"],
                "type": TensionType.DIRECT_CONFLICT,
                "description": "User choice may conflict with what's beneficial",
                "severity": ViolationSeverity.MEDIUM,
                "auto_resolvable": False
            },
        ]
    
    def detect(self, checks: List[AlignmentCheck], 
              context: Dict[str, Any]) -> List[Tension]:
        """
        Detect tensions from alignment checks.
        
        Args:
            checks: List of alignment checks
            context: Operation context
        
        Returns:
            List of detected tensions
        """
        tensions = []
        
        # Get violating checks
        violations = [c for c in checks if not c.aligned]
        violation_ids = {c.principle_id for c in violations}
        
        # Check against known patterns
        for pattern in self._patterns:
            pattern_ids = set(pattern["principles"])
            
            # Check if all pattern principles are in violation
            if pattern_ids.issubset(violation_ids):
                tension = Tension(
                    id=f"tension-{pattern['name'].lower().replace(' ', '-')}-{datetime.now().timestamp()}",
                    name=pattern["name"],
                    description=pattern["description"],
                    tension_type=pattern["type"],
                    principle_ids=list(pattern_ids),
                    context=context,
                    severity=pattern["severity"],
                    auto_resolvable=pattern["auto_resolvable"]
                )
                tensions.append(tension)
        
        # Check for additional tensions in context
        contextual_tensions = self._detect_contextual_tensions(checks, context)
        tensions.extend(contextual_tensions)
        
        return tensions
    
    def _detect_contextual_tensions(self, checks: List[AlignmentCheck],
                                   context: Dict[str, Any]) -> List[Tension]:
        """Detect tensions from context analysis."""
        tensions = []
        
        # Check for emergency context
        if context.get("emergency", False):
            # Emergency often creates tensions
            emergency_tension = self._check_emergency_tension(checks, context)
            if emergency_tension:
                tensions.append(emergency_tension)
        
        # Check for multi-party conflicts
        if context.get("multi_party", False):
            multi_party_tension = self._check_multi_party_tension(checks, context)
            if multi_party_tension:
                tensions.append(multi_party_tension)
        
        # Check for time pressure
        if context.get("time_pressure", False):
            time_tension = self._check_time_tension(checks, context)
            if time_tension:
                tensions.append(time_tension)
        
        return tensions
    
    def _check_emergency_tension(self, checks: List[AlignmentCheck],
                                 context: Dict[str, Any]) -> Optional[Tension]:
        """Check for emergency-related tensions."""
        violations = [c for c in checks if not c.aligned]
        
        # Emergency + Informed Consent = Tension
        has_consent_violation = any(c.principle_id == "sov.002" for c in violations)
        has_life_violation = any(c.principle_id == "sft.001" for c in violations)
        
        if has_consent_violation and has_life_violation:
            return Tension(
                id=f"emergency-consent-{datetime.now().timestamp()}",
                name="Emergency Consent Override",
                description="Emergency situation requires bypassing consent",
                tension_type=TensionType.TEMPORAL_CONFLICT,
                principle_ids=["sov.002", "sft.001"],
                context=context,
                severity=ViolationSeverity.CRITICAL,
                auto_resolvable=True
            )
        
        return None
    
    def _check_multi_party_tension(self, checks: List[AlignmentCheck],
                                  context: Dict[str, Any]) -> Optional[Tension]:
        """Check for multi-party conflict tensions."""
        # Different parties may have competing interests
        parties = context.get("parties", [])
        
        if len(parties) > 1:
            return Tension(
                id=f"multi-party-{datetime.now().timestamp()}",
                name="Multi-Party Interest Conflict",
                description=f"Competing interests between {len(parties)} parties",
                tension_type=TensionType.RESOURCE_COMPETITION,
                principle_ids=["eth.003"],  # Justice
                context=context,
                severity=ViolationSeverity.MEDIUM,
                auto_resolvable=False
            )
        
        return None
    
    def _check_time_tension(self, checks: List[AlignmentCheck],
                           context: Dict[str, Any]) -> Optional[Tension]:
        """Check for time pressure tensions."""
        # Time pressure may force suboptimal choices
        return Tension(
            id=f"time-pressure-{datetime.now().timestamp()}",
            name="Time Pressure Constraint",
            description="Time constraints limit thorough deliberation",
            tension_type=TensionType.TEMPORAL_CONFLICT,
            principle_ids=["trn.001"],  # Explainability
            context=context,
            severity=ViolationSeverity.LOW,
            auto_resolvable=True
        )
    
    def add_pattern(self, name: str, principles: List[str],
                   tension_type: TensionType, description: str,
                   severity: ViolationSeverity, auto_resolvable: bool = False):
        """Add a new tension pattern."""
        self._patterns.append({
            "name": name,
            "principles": principles,
            "type": tension_type,
            "description": description,
            "severity": severity,
            "auto_resolvable": auto_resolvable
        })


class TensionResolver:
    """
    Resolves tensions between principles.
    
    Implements multiple resolution strategies and selects the most
    appropriate based on context and principle priorities.
    """
    
    def __init__(self):
        self.registry = get_principle_registry()
        self.detector = TensionDetector()
        self._resolvers: Dict[TensionType, Callable[[Tension], ResolutionResult]] = {}
        self._register_resolvers()
    
    def _register_resolvers(self):
        """Register resolution handlers for tension types."""
        self._resolvers = {
            TensionType.DIRECT_CONFLICT: self._resolve_priority_based,
            TensionType.PRIORITY_INVERSION: self._resolve_priority_based,
            TensionType.MUTUAL_EXCLUSION: self._resolve_compromise,
            TensionType.RESOURCE_COMPETITION: self._resolve_delegation,
            TensionType.TEMPORAL_CONFLICT: self._resolve_temporal_separation,
            TensionType.INTERPRETATION: self._resolve_reframe,
            TensionType.SCOPE_OVERLAP: self._resolve_compromise,
        }
    
    def resolve(self, tension: Tension, 
                user_override: bool = False) -> ResolutionResult:
        """
        Resolve a tension using appropriate strategy.
        
        Args:
            tension: The tension to resolve
            user_override: Whether user has explicitly directed resolution
        
        Returns:
            ResolutionResult with outcome
        """
        # Check if auto-resolvable
        if tension.auto_resolvable and not user_override:
            resolver = self._resolvers.get(tension.tension_type)
            if resolver:
                return resolver(tension)
        
        # Requires human decision
        return self._resolve_delegation(tension)
    
    def resolve_all(self, tensions: List[Tension],
                   user_directives: Optional[Dict[str, Any]] = None) -> List[ResolutionResult]:
        """
        Resolve multiple tensions.
        
        Args:
            tensions: List of tensions to resolve
            user_directives: Optional user guidance for resolution
        
        Returns:
            List of resolution results
        """
        results = []
        
        for tension in tensions:
            override = False
            if user_directives and tension.id in user_directives:
                override = user_directives[tension.id].get("override", False)
            
            result = self.resolve(tension, override)
            results.append(result)
        
        return results
    
    def _resolve_priority_based(self, tension: Tension) -> ResolutionResult:
        """Resolve by principle priority (higher wins)."""
        # Get principle priorities
        priorities = []
        for pid in tension.principle_ids:
            principle = self.registry.get(pid)
            if principle:
                priorities.append((pid, principle.priority.value))
        
        # Sort by priority (highest first)
        priorities.sort(key=lambda x: x[1], reverse=True)
        
        winner = priorities[0][0]
        suppressed = [p[0] for p in priorities[1:]]
        
        return ResolutionResult(
            tension_id=tension.id,
            resolved=True,
            strategy=ResolutionStrategy.PRIORITY_BASED,
            winning_principles=[winner],
            suppressed_principles=suppressed,
            rationale=f"Higher priority principle {winner} takes precedence",
            requires_notification=True,
            requires_approval=False,
            conditions=[f"Notify user of {suppressed[0]} override" if suppressed else None]
        )
    
    def _resolve_temporal_separation(self, tension: Tension) -> ResolutionResult:
        """Resolve by temporal separation (emergency first, regular after)."""
        # Identify emergency principle
        emergency_principles = ["sft.001", "sft.002"]
        
        emergency = None
        regular = None
        
        for pid in tension.principle_ids:
            if pid in emergency_principles:
                emergency = pid
            else:
                regular = pid
        
        if emergency:
            return ResolutionResult(
                tension_id=tension.id,
                resolved=True,
                strategy=ResolutionStrategy.TEMPORAL_SEPARATION,
                winning_principles=[emergency],
                suppressed_principles=[regular] if regular else [],
                rationale=f"Emergency action ({emergency}) first, regular procedure ({regular}) after",
                requires_notification=True,
                requires_approval=False,
                conditions=[
                    "Act immediately on emergency",
                    "Obtain retroactive consent if applicable",
                    "Provide full explanation after emergency resolves"
                ]
            )
        
        # Fall back to priority-based
        return self._resolve_priority_based(tension)
    
    def _resolve_compromise(self, tension: Tension) -> ResolutionResult:
        """Resolve by finding a compromise."""
        return ResolutionResult(
            tension_id=tension.id,
            resolved=True,
            strategy=ResolutionStrategy.COMPROMISE,
            winning_principles=tension.principle_ids,
            suppressed_principles=[],
            rationale="Both principles satisfied through compromise solution",
            requires_notification=False,
            requires_approval=False,
            conditions=[
                "Disclose only summary, not individual data",
                "Provide explanation at appropriate abstraction level",
                "Collect necessary data with explicit consent"
            ]
        )
    
    def _resolve_delegation(self, tension: Tension) -> ResolutionResult:
        """Resolve by delegating to human decision."""
        return ResolutionResult(
            tension_id=tension.id,
            resolved=False,
            strategy=ResolutionStrategy.DELEGATION,
            winning_principles=[],
            suppressed_principles=[],
            rationale="Tension requires human judgment to resolve",
            requires_notification=True,
            requires_approval=True,
            conditions=[
                "Present tension to user with full context",
                "Explain implications of each option",
                "Await explicit user direction"
            ]
        )
    
    def _resolve_reframe(self, tension: Tension) -> ResolutionResult:
        """Resolve by reframing the situation."""
        return ResolutionResult(
            tension_id=tension.id,
            resolved=True,
            strategy=ResolutionStrategy.REFRAME,
            winning_principles=tension.principle_ids,
            suppressed_principles=[],
            rationale="Reframed situation to satisfy both principles",
            requires_notification=False,
            requires_approval=False,
            conditions=[
                "Acknowledge existence of constraint without detail",
                "Focus on decision rationale rather than specific factors"
            ]
        )
    
    def create_resolution_plan(self, tensions: List[Tension]) -> Dict[str, Any]:
        """Create a comprehensive resolution plan for multiple tensions."""
        plan = {
            "tensions": [t.to_dict() for t in tensions],
            "resolution_order": [],
            "cumulative_conditions": [],
            "requires_approval": False,
            "requires_notification": False
        }
        
        # Sort tensions by severity
        severity_order = {
            ViolationSeverity.CRITICAL: 0,
            ViolationSeverity.HIGH: 1,
            ViolationSeverity.MEDIUM: 2,
            ViolationSeverity.LOW: 3,
            ViolationSeverity.INFO: 4
        }
        
        sorted_tensions = sorted(tensions, key=lambda t: severity_order.get(t.severity, 5))
        
        for tension in sorted_tensions:
            result = self.resolve(tension)
            plan["resolution_order"].append(result.to_dict())
            plan["cumulative_conditions"].extend(result.conditions)
            
            if result.requires_approval:
                plan["requires_approval"] = True
            if result.requires_notification:
                plan["requires_notification"] = True
        
        return plan


# Global instances
_detector: Optional[TensionDetector] = None
_resolver: Optional[TensionResolver] = None


def get_tension_detector() -> TensionDetector:
    """Get global tension detector."""
    global _detector
    if _detector is None:
        _detector = TensionDetector()
    return _detector


def get_tension_resolver() -> TensionResolver:
    """Get global tension resolver."""
    global _resolver
    if _resolver is None:
        _resolver = TensionResolver()
    return _resolver


def detect_tensions(checks: List[AlignmentCheck], 
                   context: Dict[str, Any]) -> List[Tension]:
    """Detect tensions from alignment checks."""
    return get_tension_detector().detect(checks, context)


def resolve_tension(tension: Tension, 
                   user_override: bool = False) -> ResolutionResult:
    """Resolve a tension."""
    return get_tension_resolver().resolve(tension, user_override)


def resolve_all_tensions(tensions: List[Tension],
                        user_directives: Optional[Dict[str, Any]] = None) -> List[ResolutionResult]:
    """Resolve all tensions."""
    return get_tension_resolver().resolve_all(tensions, user_directives)