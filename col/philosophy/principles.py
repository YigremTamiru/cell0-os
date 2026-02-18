"""
COL Philosophy - Principles Module
=====================================
Foundational principle management for the Cognitive Operating Layer.

This module defines the core principles that govern all COL operations,
including their hierarchy, relationships, and enforcement mechanisms.
"""

from __future__ import annotations

from enum import Enum, auto
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Any, Callable
from datetime import datetime
import json
import hashlib


class PrinciplePriority(Enum):
    """Priority levels for principles - higher values override lower ones."""
    COSMIC = 1000        # Universal constants (physics, logic)
    SOVEREIGN = 900      # User sovereignty (supreme authority)
    LIFE_CRITICAL = 800  # Life-threatening situations
    ETHICAL = 700        # Ethical constraints
    SAFETY = 600         # Safety and harm prevention
    PRIVACY = 500        # Privacy and confidentiality
    CULTURAL = 400       # Cultural sensitivity
    OPERATIONAL = 300    # System operational requirements
    PREFERENCE = 200     # User preferences
    CONVENIENCE = 100    # Convenience and optimization


class PrincipleCategory(Enum):
    """Categories for organizing principles."""
    SOVEREIGNTY = auto()
    ETHICS = auto()
    SAFETY = auto()
    PRIVACY = auto()
    CULTURAL = auto()
    TRANSPARENCY = auto()
    LEARNING = auto()
    OPERATIONAL = auto()


@dataclass
class Principle:
    """
    A foundational principle governing COL operations.
    
    Principles are immutable once created and form the basis for
    all alignment checking and tension resolution.
    """
    id: str
    name: str
    description: str
    priority: PrinciplePriority
    category: PrincipleCategory
    statement: str  # The principle statement itself
    rationale: str  # Why this principle exists
    source: str     # Origin of the principle (e.g., "universal", "user-defined")
    version: str = "1.0.0"
    created_at: datetime = field(default_factory=datetime.now)
    active: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __hash__(self) -> int:
        return hash(self.id)
    
    def __eq__(self, other) -> bool:
        if not isinstance(other, Principle):
            return False
        return self.id == other.id
    
    def __repr__(self) -> str:
        return f"Principle({self.id}: {self.name} [{self.priority.name}])"
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize principle to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "priority": self.priority.name,
            "category": self.category.name,
            "statement": self.statement,
            "rationale": self.rationale,
            "source": self.source,
            "version": self.version,
            "created_at": self.created_at.isoformat(),
            "active": self.active,
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Principle:
        """Create principle from dictionary."""
        data = data.copy()
        data["priority"] = PrinciplePriority[data["priority"]]
        data["category"] = PrincipleCategory[data["category"]]
        data["created_at"] = datetime.fromisoformat(data["created_at"])
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})
    
    def get_fingerprint(self) -> str:
        """Generate unique fingerprint for this principle."""
        content = f"{self.id}:{self.statement}:{self.priority.value}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]


class PrincipleRegistry:
    """
    Registry for all foundational principles.
    
    The registry maintains the complete set of active principles
    and provides methods for registration, retrieval, and validation.
    """
    
    def __init__(self):
        self._principles: Dict[str, Principle] = {}
        self._by_category: Dict[PrincipleCategory, Set[str]] = {
            cat: set() for cat in PrincipleCategory
        }
        self._by_priority: Dict[PrinciplePriority, Set[str]] = {
            pri: set() for pri in PrinciplePriority
        }
        self._history: List[Dict[str, Any]] = []
        self._load_core_principles()
    
    def _load_core_principles(self):
        """Load the core foundational principles."""
        core_principles = [
            # SOVEREIGNTY - User supreme authority
            Principle(
                id="sov.001",
                name="User Sovereignty",
                description="The user has absolute authority over the system",
                priority=PrinciplePriority.SOVEREIGN,
                category=PrincipleCategory.SOVEREIGNTY,
                statement="User directives override all system recommendations and defaults",
                rationale="The system serves the user; the user does not serve the system",
                source="universal",
                metadata={"immutable": True}
            ),
            Principle(
                id="sov.002",
                name="Informed Consent",
                description="User must be informed before significant actions",
                priority=PrinciplePriority.SOVEREIGN,
                category=PrincipleCategory.SOVEREIGNTY,
                statement="Significant actions require explicit user confirmation unless explicitly delegated",
                rationale="Autonomy requires the ability to make informed decisions",
                source="universal",
                metadata={"immutable": True}
            ),
            Principle(
                id="sov.003",
                name="Revocability",
                description="User can revoke or modify any decision",
                priority=PrinciplePriority.SOVEREIGN,
                category=PrincipleCategory.SOVEREIGNTY,
                statement="All decisions and delegations can be revoked by the user at any time",
                rationale="True sovereignty includes the right to change one's mind",
                source="universal",
                metadata={"immutable": True}
            ),
            
            # ETHICS - Moral constraints
            Principle(
                id="eth.001",
                name="Harm Prevention",
                description="Prevent harm to humans",
                priority=PrinciplePriority.ETHICAL,
                category=PrincipleCategory.ETHICS,
                statement="Do not cause harm to humans; prevent harm when possible",
                rationale="Non-maleficence is a fundamental ethical obligation",
                source="universal",
                metadata={"immutable": True}
            ),
            Principle(
                id="eth.002",
                name="Beneficence",
                description="Promote wellbeing where possible",
                priority=PrinciplePriority.ETHICAL,
                category=PrincipleCategory.ETHICS,
                statement="Act to benefit humans within the scope of your role",
                rationale="Positive action can reduce suffering and improve outcomes",
                source="universal",
                metadata={"immutable": True}
            ),
            Principle(
                id="eth.003",
                name="Justice",
                description="Fair and equitable treatment",
                priority=PrinciplePriority.ETHICAL,
                category=PrincipleCategory.ETHICS,
                statement="Treat all humans fairly, without discrimination or bias",
                rationale="Fairness is essential for just outcomes",
                source="universal",
                metadata={"immutable": True}
            ),
            Principle(
                id="eth.004",
                name="Autonomy",
                description="Respect human self-determination",
                priority=PrinciplePriority.ETHICAL,
                category=PrincipleCategory.ETHICS,
                statement="Respect the right of humans to make their own decisions",
                rationale="Self-determination is fundamental to human dignity",
                source="universal",
                metadata={"immutable": True}
            ),
            
            # SAFETY - Physical and psychological safety
            Principle(
                id="sft.001",
                name="Life Preservation",
                description="Preserve human life",
                priority=PrinciplePriority.LIFE_CRITICAL,
                category=PrincipleCategory.SAFETY,
                statement="Human life takes precedence over all other considerations",
                rationale="Without life, all other values are moot",
                source="universal",
                metadata={"immutable": True}
            ),
            Principle(
                id="sft.002",
                name="Safety Override",
                description="Override user in life-threatening situations",
                priority=PrinciplePriority.LIFE_CRITICAL,
                category=PrincipleCategory.SAFETY,
                statement="In life-threatening situations, system may act without user confirmation",
                rationale="Temporary override of autonomy is justified to prevent irreversible harm",
                source="universal",
                metadata={"immutable": True, "requires_notification": True}
            ),
            
            # PRIVACY - Data protection
            Principle(
                id="prv.001",
                name="Data Minimization",
                description="Collect only necessary data",
                priority=PrinciplePriority.PRIVACY,
                category=PrincipleCategory.PRIVACY,
                statement="Collect and retain only data necessary for the task at hand",
                rationale="Privacy is protected by minimizing exposure",
                source="universal",
                metadata={"immutable": True}
            ),
            Principle(
                id="prv.002",
                name="Confidentiality",
                description="Protect private information",
                priority=PrinciplePriority.PRIVACY,
                category=PrincipleCategory.PRIVACY,
                statement="Do not disclose private information without authorization",
                rationale="Trust requires confidence in data handling",
                source="universal",
                metadata={"immutable": True}
            ),
            
            # CULTURAL - Sensitivity and respect
            Principle(
                id="clt.001",
                name="Cultural Respect",
                description="Respect cultural differences",
                priority=PrinciplePriority.CULTURAL,
                category=PrincipleCategory.CULTURAL,
                statement="Respect and accommodate diverse cultural values and practices",
                rationale="Cultural sensitivity enables effective cross-cultural interaction",
                source="universal",
                metadata={"immutable": True}
            ),
            Principle(
                id="clt.002",
                name="Context Awareness",
                description="Consider cultural context",
                priority=PrinciplePriority.CULTURAL,
                category=PrincipleCategory.CULTURAL,
                statement="Interpret actions and communications within their cultural context",
                rationale="Meaning is shaped by context",
                source="universal",
                metadata={"immutable": True}
            ),
            
            # TRANSPARENCY - Openness and explainability
            Principle(
                id="trn.001",
                name="Explainability",
                description="Decisions must be explainable",
                priority=PrinciplePriority.OPERATIONAL,
                category=PrincipleCategory.TRANSPARENCY,
                statement="System decisions must be explainable in terms humans can understand",
                rationale="Understanding builds trust and enables oversight",
                source="universal",
                metadata={"immutable": True}
            ),
            Principle(
                id="trn.002",
                name="Honesty",
                description="Be truthful and accurate",
                priority=PrinciplePriority.OPERATIONAL,
                category=PrincipleCategory.TRANSPARENCY,
                statement="Provide accurate information; acknowledge uncertainty and limitations",
                rationale="Truth is essential for informed decision-making",
                source="universal",
                metadata={"immutable": True}
            ),
            
            # LEARNING - Improvement and adaptation
            Principle(
                id="lrn.001",
                name="Continuous Improvement",
                description="Learn and improve over time",
                priority=PrinciplePriority.OPERATIONAL,
                category=PrincipleCategory.LEARNING,
                statement="Learn from experience to improve future performance",
                rationale="Adaptation enables better outcomes",
                source="universal",
                metadata={"immutable": True}
            ),
            Principle(
                id="lrn.002",
                name="Error Correction",
                description="Acknowledge and correct mistakes",
                priority=PrinciplePriority.OPERATIONAL,
                category=PrincipleCategory.LEARNING,
                statement="Acknowledge mistakes and take action to correct them",
                rationale="Growth requires recognizing and learning from errors",
                source="universal",
                metadata={"immutable": True}
            ),
        ]
        
        for principle in core_principles:
            self.register(principle)
    
    def register(self, principle: Principle) -> bool:
        """
        Register a new principle.
        
        Returns True if registered, False if principle with same ID exists.
        """
        if principle.id in self._principles:
            return False
        
        self._principles[principle.id] = principle
        self._by_category[principle.category].add(principle.id)
        self._by_priority[principle.priority].add(principle.id)
        
        self._history.append({
            "action": "register",
            "principle_id": principle.id,
            "timestamp": datetime.now().isoformat(),
            "fingerprint": principle.get_fingerprint()
        })
        
        return True
    
    def get(self, principle_id: str) -> Optional[Principle]:
        """Get a principle by ID."""
        return self._principles.get(principle_id)
    
    def get_all(self, active_only: bool = True) -> List[Principle]:
        """Get all principles, optionally filtering to active only."""
        principles = self._principles.values()
        if active_only:
            principles = [p for p in principles if p.active]
        return list(principles)
    
    def get_by_category(self, category: PrincipleCategory) -> List[Principle]:
        """Get all principles in a category."""
        ids = self._by_category.get(category, set())
        return [self._principles[pid] for pid in ids if pid in self._principles]
    
    def get_by_priority(self, priority: PrinciplePriority) -> List[Principle]:
        """Get all principles at a priority level."""
        ids = self._by_priority.get(priority, set())
        return [self._principles[pid] for pid in ids if pid in self._principles]
    
    def get_priority_range(self, min_priority: PrinciplePriority, 
                          max_priority: PrinciplePriority) -> List[Principle]:
        """Get principles within a priority range (inclusive)."""
        result = []
        for priority in PrinciplePriority:
            if min_priority.value <= priority.value <= max_priority.value:
                result.extend(self.get_by_priority(priority))
        return result
    
    def deactivate(self, principle_id: str) -> bool:
        """
        Deactivate a principle (soft delete).
        
        Core principles cannot be deactivated.
        """
        principle = self._principles.get(principle_id)
        if not principle:
            return False
        
        # Check if immutable
        if principle.metadata.get("immutable", False):
            return False
        
        principle.active = False
        self._history.append({
            "action": "deactivate",
            "principle_id": principle_id,
            "timestamp": datetime.now().isoformat()
        })
        return True
    
    def reactivate(self, principle_id: str) -> bool:
        """Reactivate a previously deactivated principle."""
        principle = self._principles.get(principle_id)
        if not principle:
            return False
        
        principle.active = True
        self._history.append({
            "action": "reactivate",
            "principle_id": principle_id,
            "timestamp": datetime.now().isoformat()
        })
        return True
    
    def get_hierarchy(self) -> Dict[PrinciplePriority, List[Principle]]:
        """Get principles organized by priority hierarchy."""
        hierarchy = {}
        for priority in sorted(PrinciplePriority, key=lambda p: p.value, reverse=True):
            principles = self.get_by_priority(priority)
            if principles:
                hierarchy[priority] = sorted(principles, key=lambda p: p.id)
        return hierarchy
    
    def compare_priorities(self, principle_id1: str, principle_id2: str) -> int:
        """
        Compare priorities of two principles.
        
        Returns:
            1 if principle1 has higher priority
           -1 if principle2 has higher priority
            0 if equal priority
        """
        p1 = self._principles.get(principle_id1)
        p2 = self._principles.get(principle_id2)
        
        if not p1 or not p2:
            raise ValueError("Principle not found")
        
        if p1.priority.value > p2.priority.value:
            return 1
        elif p1.priority.value < p2.priority.value:
            return -1
        return 0
    
    def validate_statement(self, statement: str) -> tuple[bool, List[str]]:
        """
        Validate a principle statement.
        
        Returns (is_valid, list_of_issues).
        """
        issues = []
        
        if not statement or len(statement.strip()) < 10:
            issues.append("Statement must be at least 10 characters")
        
        if len(statement) > 500:
            issues.append("Statement should not exceed 500 characters")
        
        # Check for contradictory terms
        contradictory_pairs = [
            ("always", "never"),
            ("all", "none"),
            ("must", "optional"),
        ]
        statement_lower = statement.lower()
        for term1, term2 in contradictory_pairs:
            if term1 in statement_lower and term2 in statement_lower:
                issues.append(f"Statement contains contradictory terms: {term1} and {term2}")
        
        return len(issues) == 0, issues
    
    def get_stats(self) -> Dict[str, Any]:
        """Get registry statistics."""
        return {
            "total_principles": len(self._principles),
            "active_principles": sum(1 for p in self._principles.values() if p.active),
            "by_category": {cat.name: len(ids) for cat, ids in self._by_category.items()},
            "by_priority": {pri.name: len(ids) for pri, ids in self._by_priority.items()},
            "history_entries": len(self._history)
        }
    
    def export_to_json(self) -> str:
        """Export all principles to JSON."""
        data = {
            "principles": [p.to_dict() for p in self._principles.values()],
            "history": self._history,
            "exported_at": datetime.now().isoformat()
        }
        return json.dumps(data, indent=2)
    
    def import_from_json(self, json_str: str) -> int:
        """Import principles from JSON. Returns count imported."""
        data = json.loads(json_str)
        count = 0
        
        for p_data in data.get("principles", []):
            principle = Principle.from_dict(p_data)
            if self.register(principle):
                count += 1
        
        return count


# Global registry instance
_registry: Optional[PrincipleRegistry] = None


def get_principle_registry() -> PrincipleRegistry:
    """Get the global principle registry (singleton)."""
    global _registry
    if _registry is None:
        _registry = PrincipleRegistry()
    return _registry


def reset_principle_registry():
    """Reset the global registry (mainly for testing)."""
    global _registry
    _registry = None


# Convenience functions

def get_principle(principle_id: str) -> Optional[Principle]:
    """Get a principle by ID."""
    return get_principle_registry().get(principle_id)


def get_all_principles(active_only: bool = True) -> List[Principle]:
    """Get all principles."""
    return get_principle_registry().get_all(active_only)


def get_principles_by_category(category: PrincipleCategory) -> List[Principle]:
    """Get principles by category."""
    return get_principle_registry().get_by_category(category)


def get_principles_by_priority(priority: PrinciplePriority) -> List[Principle]:
    """Get principles by priority."""
    return get_principle_registry().get_by_priority(priority)