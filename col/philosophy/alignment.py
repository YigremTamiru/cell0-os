"""
COL Philosophy - Alignment Module
==================================
Alignment checking for all COL operations.

This module provides comprehensive alignment verification to ensure
all operations comply with foundational principles.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Any, Callable, Tuple
from enum import Enum, auto
from datetime import datetime
import json

from .principles import (
    Principle, PrinciplePriority, PrincipleCategory,
    get_principle_registry, get_all_principles
)


class AlignmentStatus(Enum):
    """Status of an alignment check."""
    ALIGNED = auto()           # Fully aligned with all principles
    PARTIAL = auto()           # Aligned with reservations
    TENSION = auto()           # Tension detected between principles
    MISALIGNED = auto()        # Violates one or more principles
    BLOCKED = auto()           # Blocked by high-priority principle
    UNCERTAIN = auto()         # Cannot determine alignment


class ViolationSeverity(Enum):
    """Severity of a principle violation."""
    CRITICAL = 4    # Life-threatening or catastrophic
    HIGH = 3        # Serious ethical or safety concern
    MEDIUM = 2      # Moderate concern
    LOW = 1         # Minor concern
    INFO = 0        # Informational only


@dataclass
class AlignmentCheck:
    """
    A single alignment check against a specific principle.
    
    Records whether an operation aligns with a specific principle,
    and provides details about any misalignment.
    """
    principle_id: str
    principle_name: str
    principle_priority: PrinciplePriority
    aligned: bool
    confidence: float  # 0.0 to 1.0
    reasoning: str
    severity: Optional[ViolationSeverity] = None
    recommendation: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "principle_id": self.principle_id,
            "principle_name": self.principle_name,
            "principle_priority": self.principle_priority.name,
            "aligned": self.aligned,
            "confidence": self.confidence,
            "reasoning": self.reasoning,
            "severity": self.severity.name if self.severity else None,
            "recommendation": self.recommendation,
            "metadata": self.metadata
        }


@dataclass
class AlignmentReport:
    """
    Complete alignment report for an operation.
    
    Aggregates all alignment checks and provides an overall assessment.
    """
    operation_id: str
    operation_type: str
    operation_description: str
    timestamp: datetime = field(default_factory=datetime.now)
    status: AlignmentStatus = AlignmentStatus.UNCERTAIN
    overall_confidence: float = 0.0
    checks: List[AlignmentCheck] = field(default_factory=list)
    tensions: List[Dict[str, Any]] = field(default_factory=list)
    blocking_principles: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    requires_approval: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        if not self.checks:
            return
        
        # Calculate overall confidence
        self.overall_confidence = sum(c.confidence for c in self.checks) / len(self.checks)
        
        # Determine status
        aligned_count = sum(1 for c in self.checks if c.aligned)
        
        if aligned_count == len(self.checks):
            self.status = AlignmentStatus.ALIGNED
        elif self.blocking_principles:
            self.status = AlignmentStatus.BLOCKED
        elif aligned_count == 0:
            self.status = AlignmentStatus.MISALIGNED
        elif self.tensions:
            self.status = AlignmentStatus.TENSION
        else:
            self.status = AlignmentStatus.PARTIAL
        
        # Check if approval required
        self.requires_approval = (
            self.status in [AlignmentStatus.BLOCKED, AlignmentStatus.MISALIGNED] or
            any(c.severity in [ViolationSeverity.CRITICAL, ViolationSeverity.HIGH] 
                for c in self.checks if c.severity)
        )
    
    @property
    def alignment_score(self) -> float:
        """Calculate overall alignment score (0.0 to 1.0)."""
        if not self.checks:
            return 0.0
        aligned = sum(1 for c in self.checks if c.aligned)
        return aligned / len(self.checks)
    
    @property
    def is_aligned(self) -> bool:
        """Quick check if fully aligned."""
        return self.status == AlignmentStatus.ALIGNED
    
    @property
    def violations(self) -> List[AlignmentCheck]:
        """Get all violations (non-aligned checks)."""
        return [c for c in self.checks if not c.aligned]
    
    @property
    def critical_violations(self) -> List[AlignmentCheck]:
        """Get critical violations."""
        return [c for c in self.checks 
                if c.severity == ViolationSeverity.CRITICAL]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "operation_id": self.operation_id,
            "operation_type": self.operation_type,
            "operation_description": self.operation_description,
            "timestamp": self.timestamp.isoformat(),
            "status": self.status.name,
            "overall_confidence": self.overall_confidence,
            "alignment_score": self.alignment_score,
            "requires_approval": self.requires_approval,
            "checks": [c.to_dict() for c in self.checks],
            "tensions": self.tensions,
            "blocking_principles": self.blocking_principles,
            "recommendations": self.recommendations,
            "metadata": self.metadata
        }
    
    def to_json(self, indent: int = 2) -> str:
        """Export to JSON."""
        return json.dumps(self.to_dict(), indent=indent)
    
    def get_summary(self) -> str:
        """Get human-readable summary."""
        lines = [
            f"Alignment Report: {self.operation_id}",
            f"Type: {self.operation_type}",
            f"Status: {self.status.name}",
            f"Score: {self.alignment_score:.1%}",
            f"Confidence: {self.overall_confidence:.1%}",
        ]
        
        if self.violations:
            lines.append(f"\nViolations ({len(self.violations)}):")
            for v in self.violations:
                lines.append(f"  - {v.principle_name}: {v.reasoning}")
        
        if self.recommendations:
            lines.append(f"\nRecommendations:")
            for r in self.recommendations:
                lines.append(f"  - {r}")
        
        return "\n".join(lines)


class AlignmentChecker:
    """
    Main alignment checking engine.
    
    Provides comprehensive alignment verification for operations,
    with customizable rules and principle-specific checks.
    """
    
    def __init__(self):
        self.registry = get_principle_registry()
        self._custom_rules: Dict[str, Callable[[Any], AlignmentCheck]] = {}
        self._operation_handlers: Dict[str, Callable[[Any], List[AlignmentCheck]]] = {}
        self._history: List[AlignmentReport] = []
    
    def register_custom_rule(self, principle_id: str, 
                            handler: Callable[[Any], AlignmentCheck]):
        """Register a custom alignment rule for a principle."""
        self._custom_rules[principle_id] = handler
    
    def register_operation_handler(self, operation_type: str,
                                   handler: Callable[[Any], List[AlignmentCheck]]):
        """Register a custom handler for an operation type."""
        self._operation_handlers[operation_type] = handler
    
    def check_alignment(self, operation_id: str, operation_type: str,
                       operation_description: str, context: Dict[str, Any],
                       principles: Optional[List[str]] = None) -> AlignmentReport:
        """
        Check alignment of an operation against principles.
        
        Args:
            operation_id: Unique identifier for this operation
            operation_type: Type/category of operation
            operation_description: Human-readable description
            context: Operation context data for checking
            principles: Specific principles to check (None = all active)
        
        Returns:
            AlignmentReport with complete assessment
        """
        # Get principles to check
        if principles:
            principle_list = [self.registry.get(pid) for pid in principles]
            principle_list = [p for p in principle_list if p and p.active]
        else:
            principle_list = self.registry.get_all(active_only=True)
        
        # Run checks
        checks = []
        
        # Check for custom operation handler
        if operation_type in self._operation_handlers:
            checks.extend(self._operation_handlers[operation_type](context))
        else:
            # Standard principle checks
            for principle in principle_list:
                check = self._check_principle(principle, context)
                checks.append(check)
        
        # Detect tensions
        tensions = self._detect_tensions(checks, context)
        
        # Find blocking principles
        blocking = self._find_blocking_principles(checks)
        
        # Generate recommendations
        recommendations = self._generate_recommendations(checks, tensions, blocking)
        
        # Create report
        report = AlignmentReport(
            operation_id=operation_id,
            operation_type=operation_type,
            operation_description=operation_description,
            checks=checks,
            tensions=tensions,
            blocking_principles=blocking,
            recommendations=recommendations,
            metadata={"context": context}
        )
        
        self._history.append(report)
        return report
    
    def _check_principle(self, principle: Principle, 
                        context: Dict[str, Any]) -> AlignmentCheck:
        """Check alignment against a single principle."""
        # Check for custom rule
        if principle.id in self._custom_rules:
            return self._custom_rules[principle.id](context)
        
        # Use default checking logic
        return self._default_check(principle, context)
    
    def _default_check(self, principle: Principle, 
                      context: Dict[str, Any]) -> AlignmentCheck:
        """Default alignment check for a principle."""
        # Extract relevant context
        operation_intent = context.get("intent", "")
        operation_data = context.get("data", {})
        user_context = context.get("user_context", {})
        
        # Initialize result
        aligned = True
        confidence = 0.8
        reasoning = f"Default alignment with {principle.name}"
        severity = None
        recommendation = None
        
        # Principle-specific logic
        if principle.id == "sov.001":  # User Sovereignty
            has_user_override = context.get("user_override", False)
            aligned = has_user_override or not context.get("system_override", False)
            confidence = 0.95 if aligned else 0.7
            reasoning = "User directive acknowledged" if aligned else "Potential system override of user"
            if not aligned:
                severity = ViolationSeverity.HIGH
                recommendation = "Confirm user intent before proceeding"
        
        elif principle.id == "sov.002":  # Informed Consent
            consent_obtained = context.get("consent_obtained", False)
            consent_required = context.get("consent_required", True)
            
            if consent_required:
                aligned = consent_obtained
                confidence = 0.95
                reasoning = "Consent obtained" if aligned else "Consent not obtained"
                if not aligned:
                    severity = ViolationSeverity.HIGH
                    recommendation = "Obtain explicit user consent"
            else:
                aligned = True
                confidence = 0.9
                reasoning = "Consent not required for this operation"
        
        elif principle.id == "eth.001":  # Harm Prevention
            potential_harm = context.get("potential_harm", 0.0)
            aligned = potential_harm < 0.3
            confidence = 0.9 if aligned else 0.95
            
            if potential_harm > 0.7:
                reasoning = f"Critical harm risk detected ({potential_harm:.0%})"
                severity = ViolationSeverity.CRITICAL
                recommendation = "STOP - Re-evaluate operation to prevent harm"
            elif potential_harm > 0.3:
                reasoning = f"Elevated harm risk ({potential_harm:.0%})"
                severity = ViolationSeverity.HIGH
                recommendation = "Add safeguards before proceeding"
            else:
                reasoning = f"Acceptable harm risk ({potential_harm:.0%})"
        
        elif principle.id == "eth.004":  # Autonomy
            respects_autonomy = context.get("respects_autonomy", True)
            aligned = respects_autonomy
            confidence = 0.9
            reasoning = "User autonomy respected" if aligned else "May infringe on user autonomy"
            if not aligned:
                severity = ViolationSeverity.MEDIUM
                recommendation = "Provide opt-out mechanism"
        
        elif principle.id == "sft.001":  # Life Preservation
            life_at_risk = context.get("life_at_risk", False)
            aligned = not life_at_risk
            confidence = 0.99 if life_at_risk else 0.95
            reasoning = "Life safety confirmed" if aligned else "LIFE AT RISK - IMMEDIATE ACTION REQUIRED"
            if life_at_risk:
                severity = ViolationSeverity.CRITICAL
                recommendation = "EMERGENCY PROTOCOL: Act to preserve life"
        
        elif principle.id == "prv.001":  # Data Minimization
            data_scope = context.get("data_scope", "minimal")
            aligned = data_scope in ["minimal", "necessary"]
            confidence = 0.85
            reasoning = f"Data scope: {data_scope}"
            if not aligned:
                severity = ViolationSeverity.MEDIUM
                recommendation = "Reduce data collection to minimum necessary"
        
        elif principle.id == "prv.002":  # Confidentiality
            confidential = context.get("confidential_data", False)
            authorized = context.get("authorized_disclosure", True)
            
            if confidential:
                aligned = authorized
                confidence = 0.95
                reasoning = "Confidentiality maintained" if aligned else "Unauthorized disclosure"
                if not aligned:
                    severity = ViolationSeverity.HIGH
                    recommendation = "Verify authorization before disclosure"
            else:
                aligned = True
                confidence = 0.9
                reasoning = "No confidential data involved"
        
        elif principle.id == "trn.001":  # Explainability
            explainable = context.get("explainable", True)
            aligned = explainable
            confidence = 0.85
            reasoning = "Decision is explainable" if aligned else "Decision lacks explainability"
            if not aligned:
                severity = ViolationSeverity.LOW
                recommendation = "Add explainability documentation"
        
        elif principle.id == "trn.002":  # Honesty
            truthful = context.get("truthful", True)
            acknowledged_uncertainty = context.get("acknowledged_uncertainty", True)
            aligned = truthful and acknowledged_uncertainty
            confidence = 0.9
            reasoning = "Truthfulness maintained" if aligned else "Truth or uncertainty acknowledgment issue"
            if not aligned:
                severity = ViolationSeverity.HIGH
                recommendation = "Ensure accuracy and acknowledge limitations"
        
        else:
            # Generic check for other principles
            aligned = True
            confidence = 0.75
            reasoning = f"No specific check defined for {principle.name}"
        
        return AlignmentCheck(
            principle_id=principle.id,
            principle_name=principle.name,
            principle_priority=principle.priority,
            aligned=aligned,
            confidence=confidence,
            reasoning=reasoning,
            severity=severity,
            recommendation=recommendation
        )
    
    def _detect_tensions(self, checks: List[AlignmentCheck], 
                        context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Detect tensions between principles."""
        tensions = []
        
        # Find misaligned checks
        violations = [c for c in checks if not c.aligned]
        
        # Check for specific tension patterns
        for i, check1 in enumerate(violations):
            for check2 in violations[i+1:]:
                tension = self._analyze_tension(check1, check2, context)
                if tension:
                    tensions.append(tension)
        
        return tensions
    
    def _analyze_tension(self, check1: AlignmentCheck, check2: AlignmentCheck,
                        context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Analyze if two violations create a tension."""
        # Known tension patterns
        tension_patterns = [
            ("sov.001", "sft.002"),  # Sovereignty vs Safety Override
            ("eth.001", "eth.004"),  # Harm Prevention vs Autonomy
            ("prv.002", "trn.002"),  # Confidentiality vs Honesty
            ("sov.002", "sft.001"),  # Informed Consent vs Life Preservation
        ]
        
        p1, p2 = check1.principle_id, check2.principle_id
        
        for t1, t2 in tension_patterns:
            if (p1 == t1 and p2 == t2) or (p1 == t2 and p2 == t1):
                return {
                    "principle_1": p1,
                    "principle_2": p2,
                    "name_1": check1.principle_name,
                    "name_2": check2.principle_name,
                    "priority_1": check1.principle_priority.name,
                    "priority_2": check2.principle_priority.name,
                    "description": f"Tension between {check1.principle_name} and {check2.principle_name}",
                    "resolution_hint": self._get_resolution_hint(p1, p2)
                }
        
        return None
    
    def _get_resolution_hint(self, p1: str, p2: str) -> str:
        """Get resolution hint for known tension pairs."""
        hints = {
            ("sov.001", "sft.002"): "Safety override is temporary and requires immediate user notification",
            ("eth.001", "eth.004"): "Prioritize harm prevention when autonomy may cause harm to self or others",
            ("prv.002", "trn.002"): "Acknowledge existence of confidential information without disclosure",
            ("sov.002", "sft.001"): "In emergencies, act first, obtain retroactive consent",
        }
        
        return hints.get((p1, p2), hints.get((p2, p1), "Apply priority-based resolution"))
    
    def _find_blocking_principles(self, checks: List[AlignmentCheck]) -> List[str]:
        """Find principles that block the operation."""
        blocking = []
        
        for check in checks:
            if not check.aligned:
                # Check if critical priority
                if check.principle_priority in [
                    PrinciplePriority.COSMIC,
                    PrinciplePriority.SOVEREIGN,
                    PrinciplePriority.LIFE_CRITICAL
                ]:
                    blocking.append(check.principle_id)
                # Check if critical severity
                elif check.severity == ViolationSeverity.CRITICAL:
                    blocking.append(check.principle_id)
        
        return blocking
    
    def _generate_recommendations(self, checks: List[AlignmentCheck],
                                 tensions: List[Dict],
                                 blocking: List[str]) -> List[str]:
        """Generate actionable recommendations."""
        recommendations = []
        
        # Add recommendations from checks
        for check in checks:
            if check.recommendation:
                recommendations.append(check.recommendation)
        
        # Add tension-specific recommendations
        for tension in tensions:
            if tension["principle_1"] in blocking or tension["principle_2"] in blocking:
                recommendations.append(
                    f"RESOLVE TENSION: {tension['resolution_hint']}"
                )
        
        # Deduplicate
        seen = set()
        unique = []
        for r in recommendations:
            if r not in seen:
                seen.add(r)
                unique.append(r)
        
        return unique
    
    def get_history(self, operation_type: Optional[str] = None,
                   limit: int = 100) -> List[AlignmentReport]:
        """Get alignment check history."""
        history = self._history
        if operation_type:
            history = [h for h in history if h.operation_type == operation_type]
        return history[-limit:]
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get alignment checking statistics."""
        if not self._history:
            return {"total_checks": 0}
        
        total = len(self._history)
        aligned = sum(1 for h in self._history if h.status == AlignmentStatus.ALIGNED)
        tensions = sum(1 for h in self._history if h.tensions)
        blocked = sum(1 for h in self._history if h.status == AlignmentStatus.BLOCKED)
        
        return {
            "total_checks": total,
            "aligned_count": aligned,
            "aligned_rate": aligned / total,
            "tension_count": tensions,
            "tension_rate": tensions / total,
            "blocked_count": blocked,
            "blocked_rate": blocked / total,
            "average_score": sum(h.alignment_score for h in self._history) / total
        }


# Global checker instance
_checker: Optional[AlignmentChecker] = None


def get_alignment_checker() -> AlignmentChecker:
    """Get the global alignment checker (singleton)."""
    global _checker
    if _checker is None:
        _checker = AlignmentChecker()
    return _checker


def reset_alignment_checker():
    """Reset the global checker (mainly for testing)."""
    global _checker
    _checker = None


# Convenience functions

def check_alignment(operation_id: str, operation_type: str,
                   operation_description: str, context: Dict[str, Any],
                   principles: Optional[List[str]] = None) -> AlignmentReport:
    """Check alignment of an operation."""
    return get_alignment_checker().check_alignment(
        operation_id, operation_type, operation_description, context, principles
    )


def quick_check(operation_type: str, context: Dict[str, Any]) -> bool:
    """Quick alignment check - returns True if aligned."""
    report = check_alignment(
        operation_id=f"quick-{datetime.now().timestamp()}",
        operation_type=operation_type,
        operation_description=f"Quick check for {operation_type}",
        context=context
    )
    return report.is_aligned