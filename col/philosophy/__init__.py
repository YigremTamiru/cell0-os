"""
COL Philosophy Module
=====================
Cognitive Operating Layer - Philosophy Module

This module provides principle alignment, tension resolution, and ethical
framework for the Cell 0 OS. It ensures all operations align with
foundational principles while preserving user sovereignty.

Modules:
    principles: Core principle management and registry
    alignment: Alignment checking for operations
    tension: Tension detection and resolution
    sovereignty: User sovereignty preservation
    ethics: Ethical constraint enforcement

Usage:
    from col.philosophy import check_alignment, detect_tensions
    from col.philosophy import get_principle_registry, get_ethics_engine
"""

from .principles import (
    Principle,
    PrinciplePriority,
    PrincipleCategory,
    PrincipleRegistry,
    get_principle_registry,
    get_principle,
    get_all_principles,
    get_principles_by_category,
    get_principles_by_priority,
)

from .alignment import (
    AlignmentCheck,
    AlignmentReport,
    AlignmentStatus,
    AlignmentChecker,
    ViolationSeverity,
    get_alignment_checker,
    check_alignment,
    quick_check,
)

from .tension import (
    Tension,
    TensionType,
    ResolutionStrategy,
    ResolutionResult,
    TensionDetector,
    TensionResolver,
    get_tension_detector,
    get_tension_resolver,
    detect_tensions,
    resolve_tension,
    resolve_all_tensions,
)

from .sovereignty import (
    ConsentRecord,
    ConsentType,
    DelegationRecord,
    DelegationScope,
    SovereigntyManager,
    get_sovereignty_manager,
    record_consent,
    check_consent,
    assert_sovereignty,
    can_override,
)

from .ethics import (
    EthicalFramework,
    HarmType,
    BiasType,
    HarmAssessment,
    BiasDetection,
    CulturalConsideration,
    EthicalEvaluation,
    EthicsEngine,
    HarmAssessor,
    BiasDetector,
    get_ethics_engine,
    evaluate_ethics,
    detect_bias,
    assess_harm,
)

__version__ = "1.0.0"
__all__ = [
    # Principles
    "Principle",
    "PrinciplePriority",
    "PrincipleCategory",
    "PrincipleRegistry",
    "get_principle_registry",
    "get_principle",
    "get_all_principles",
    "get_principles_by_category",
    "get_principles_by_priority",
    
    # Alignment
    "AlignmentCheck",
    "AlignmentReport",
    "AlignmentStatus",
    "AlignmentChecker",
    "ViolationSeverity",
    "get_alignment_checker",
    "check_alignment",
    "quick_check",
    
    # Tension
    "Tension",
    "TensionType",
    "ResolutionStrategy",
    "ResolutionResult",
    "TensionDetector",
    "TensionResolver",
    "get_tension_detector",
    "get_tension_resolver",
    "detect_tensions",
    "resolve_tension",
    "resolve_all_tensions",
    
    # Sovereignty
    "ConsentRecord",
    "ConsentType",
    "DelegationRecord",
    "DelegationScope",
    "SovereigntyManager",
    "get_sovereignty_manager",
    "record_consent",
    "check_consent",
    "assert_sovereignty",
    "can_override",
    
    # Ethics
    "EthicalFramework",
    "HarmType",
    "BiasType",
    "HarmAssessment",
    "BiasDetection",
    "CulturalConsideration",
    "EthicalEvaluation",
    "EthicsEngine",
    "HarmAssessor",
    "BiasDetector",
    "get_ethics_engine",
    "evaluate_ethics",
    "detect_bias",
    "assess_harm",
]