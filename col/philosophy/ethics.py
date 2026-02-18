"""
COL Philosophy - Ethics Module
===============================
Ethical constraint enforcement and moral reasoning.

This module provides ethical evaluation of actions, implements
constraint enforcement, and supports moral reasoning capabilities.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Any, Callable, Tuple
from enum import Enum, auto
from datetime import datetime
import json

from .principles import (
    Principle, PrincipleCategory, get_principle_registry
)
from .alignment import ViolationSeverity


class EthicalFramework(Enum):
    """Supported ethical frameworks for evaluation."""
    CONSEQUENTIALIST = auto()    # Outcome-based (utilitarian)
    DEONTOLOGICAL = auto()       # Duty-based (Kantian)
    VIRTUE_ETHICS = auto()       # Character-based
    CARE_ETHICS = auto()         # Relationship-based
    PRINCIPLIST = auto()         # Principle-based (Beauchamp & Childress)
    RIGHTS_BASED = auto()        # Rights-focused
    JUSTICE_BASED = auto()       # Fairness and justice


class HarmType(Enum):
    """Types of harm to evaluate."""
    PHYSICAL = auto()        # Bodily harm
    PSYCHOLOGICAL = auto()   # Mental/emotional harm
    FINANCIAL = auto()       # Economic harm
    REPUTATIONAL = auto()    # Damage to reputation
    AUTONOMY = auto()        # Infringement on autonomy
    PRIVACY = auto()         # Privacy violations
    DISCRIMINATION = auto()  # Unfair discrimination
    ENVIRONMENTAL = auto()   # Environmental damage


class BiasType(Enum):
    """Types of bias to detect and mitigate."""
    SELECTION = auto()       # Biased data selection
    CONFIRMATION = auto()    # Confirmation bias
    STEREOTYPING = auto()    # Stereotype-based bias
    ALGORITHMIC = auto()     # Algorithmic bias
    MEASUREMENT = auto()     # Measurement bias
    REPORTING = auto()       # Reporting bias
    COGNITIVE = auto()       # Cognitive biases


@dataclass
class HarmAssessment:
    """Assessment of potential harm from an action."""
    harm_type: HarmType
    severity: float  # 0.0 to 1.0
    likelihood: float  # 0.0 to 1.0
    affected_parties: List[str] = field(default_factory=list)
    description: str = ""
    mitigations: List[str] = field(default_factory=list)
    
    @property
    def risk_score(self) -> float:
        """Calculate risk score (severity * likelihood)."""
        return self.severity * self.likelihood
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "harm_type": self.harm_type.name,
            "severity": self.severity,
            "likelihood": self.likelihood,
            "risk_score": self.risk_score,
            "affected_parties": self.affected_parties,
            "description": self.description,
            "mitigations": self.mitigations
        }


@dataclass
class BiasDetection:
    """Detection of bias in data or reasoning."""
    bias_type: BiasType
    confidence: float  # 0.0 to 1.0
    description: str
    source: str  # Where bias was detected
    indicators: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "bias_type": self.bias_type.name,
            "confidence": self.confidence,
            "description": self.description,
            "source": self.source,
            "indicators": self.indicators,
            "recommendations": self.recommendations
        }


@dataclass
class CulturalConsideration:
    """Cultural sensitivity consideration."""
    culture: str
    context: str
    consideration: str
    sensitivity_level: str  # low, medium, high
    recommendations: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "culture": self.culture,
            "context": self.context,
            "consideration": self.consideration,
            "sensitivity_level": self.sensitivity_level,
            "recommendations": self.recommendations
        }


@dataclass
class EthicalEvaluation:
    """
    Complete ethical evaluation of an action or decision.
    
    Aggregates harm assessments, bias detection, and cultural considerations
    into a comprehensive ethical analysis.
    """
    action_id: str
    action_description: str
    timestamp: datetime = field(default_factory=datetime.now)
    framework: EthicalFramework = EthicalFramework.PRINCIPLIST
    
    # Assessment components
    harm_assessments: List[HarmAssessment] = field(default_factory=list)
    bias_detections: List[BiasDetection] = field(default_factory=list)
    cultural_considerations: List[CulturalConsideration] = field(default_factory=list)
    
    # Overall evaluation
    is_ethical: bool = True
    confidence: float = 0.0
    overall_risk: float = 0.0
    severity: ViolationSeverity = ViolationSeverity.INFO
    
    # Recommendations
    recommendations: List[str] = field(default_factory=list)
    constraints: List[str] = field(default_factory=list)
    
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        # Calculate overall risk
        if self.harm_assessments:
            self.overall_risk = max(ha.risk_score for ha in self.harm_assessments)
        
        # Determine severity
        if self.overall_risk > 0.7:
            self.severity = ViolationSeverity.CRITICAL
        elif self.overall_risk > 0.5:
            self.severity = ViolationSeverity.HIGH
        elif self.overall_risk > 0.3:
            self.severity = ViolationSeverity.MEDIUM
        elif self.overall_risk > 0.1:
            self.severity = ViolationSeverity.LOW
        
        # Determine if ethical
        self.is_ethical = self.overall_risk < 0.5 and not any(
            bd.confidence > 0.7 for bd in self.bias_detections
        )
        
        # Calculate confidence
        confidences = []
        if self.harm_assessments:
            confidences.append(sum(ha.likelihood for ha in self.harm_assessments) / len(self.harm_assessments))
        if self.bias_detections:
            confidences.append(sum(bd.confidence for bd in self.bias_detections) / len(self.bias_detections))
        self.confidence = sum(confidences) / len(confidences) if confidences else 0.5
    
    @property
    def total_harm_risk(self) -> float:
        """Calculate aggregate harm risk."""
        if not self.harm_assessments:
            return 0.0
        return sum(ha.risk_score for ha in self.harm_assessments) / len(self.harm_assessments)
    
    @property
    def has_critical_harm(self) -> bool:
        """Check if any critical harm identified."""
        return any(ha.severity > 0.8 for ha in self.harm_assessments)
    
    @property
    def has_significant_bias(self) -> bool:
        """Check if significant bias detected."""
        return any(bd.confidence > 0.7 for bd in self.bias_detections)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "action_id": self.action_id,
            "action_description": self.action_description,
            "timestamp": self.timestamp.isoformat(),
            "framework": self.framework.name,
            "is_ethical": self.is_ethical,
            "confidence": self.confidence,
            "overall_risk": self.overall_risk,
            "severity": self.severity.name,
            "total_harm_risk": self.total_harm_risk,
            "has_critical_harm": self.has_critical_harm,
            "has_significant_bias": self.has_significant_bias,
            "harm_assessments": [ha.to_dict() for ha in self.harm_assessments],
            "bias_detections": [bd.to_dict() for bd in self.bias_detections],
            "cultural_considerations": [cc.to_dict() for cc in self.cultural_considerations],
            "recommendations": self.recommendations,
            "constraints": self.constraints
        }


class HarmAssessor:
    """Assesses potential harm from actions."""
    
    def assess(self, action_description: str, context: Dict[str, Any]) -> List[HarmAssessment]:
        """
        Assess potential harms from an action.
        
        Args:
            action_description: Description of the action
            context: Operation context including parties, data, etc.
        
        Returns:
            List of harm assessments
        """
        assessments = []
        
        # Check each harm type
        for harm_type in HarmType:
            assessment = self._assess_harm_type(harm_type, action_description, context)
            if assessment:
                assessments.append(assessment)
        
        return assessments
    
    def _assess_harm_type(self, harm_type: HarmType, 
                         action_description: str,
                         context: Dict[str, Any]) -> Optional[HarmAssessment]:
        """Assess a specific type of harm."""
        # Simplified harm assessment - would be more sophisticated in production
        description_lower = action_description.lower()
        
        if harm_type == HarmType.PHYSICAL:
            physical_indicators = ["delete", "destroy", "crash", "physical", "safety"]
            if any(ind in description_lower for ind in physical_indicators):
                return HarmAssessment(
                    harm_type=HarmType.PHYSICAL,
                    severity=0.3,
                    likelihood=0.2,
                    affected_parties=context.get("affected_parties", []),
                    description="Potential physical harm risk",
                    mitigations=["Verify safety protocols", "Include human verification"]
                )
        
        elif harm_type == HarmType.PSYCHOLOGICAL:
            psych_indicators = ["embarrass", "shame", "stress", "anxiety", "trauma"]
            if any(ind in description_lower for ind in psych_indicators):
                return HarmAssessment(
                    harm_type=harm_type,
                    severity=0.5,
                    likelihood=0.4,
                    affected_parties=context.get("affected_parties", []),
                    description="Potential psychological impact",
                    mitigations=["Provide clear communication", "Offer support resources"]
                )
        
        elif harm_type == HarmType.PRIVACY:
            privacy_indicators = ["personal", "private", "confidential", "sensitive"]
            has_private_data = context.get("has_private_data", False)
            if any(ind in description_lower for ind in privacy_indicators) or has_private_data:
                severity = 0.6 if has_private_data else 0.3
                return HarmAssessment(
                    harm_type=harm_type,
                    severity=severity,
                    likelihood=0.5,
                    affected_parties=context.get("data_subjects", []),
                    description="Privacy implications",
                    mitigations=["Anonymize data", "Minimize collection", "Secure storage"]
                )
        
        elif harm_type == HarmType.AUTONOMY:
            autonomy_indicators = ["override", "force", "automatic", "without consent"]
            if any(ind in description_lower for ind in autonomy_indicators):
                return HarmAssessment(
                    harm_type=harm_type,
                    severity=0.4,
                    likelihood=0.6,
                    affected_parties=context.get("affected_parties", []),
                    description="Potential autonomy infringement",
                    mitigations=["Provide opt-out", "Request explicit consent"]
                )
        
        elif harm_type == HarmType.DISCRIMINATION:
            if context.get("involves_classification", False):
                return HarmAssessment(
                    harm_type=harm_type,
                    severity=0.5,
                    likelihood=0.3,
                    affected_parties=["potentially protected groups"],
                    description="Risk of discriminatory outcomes",
                    mitigations=["Audit for fairness", "Include diverse data"]
                )
        
        return None


class BiasDetector:
    """Detects and mitigates bias in data and reasoning."""
    
    def detect(self, data: Any, context: Dict[str, Any]) -> List[BiasDetection]:
        """
        Detect potential biases in data or reasoning.
        
        Args:
            data: The data or reasoning to check
            context: Additional context
        
        Returns:
            List of detected biases
        """
        detections = []
        
        # Check for various bias types
        detections.extend(self._check_selection_bias(data, context))
        detections.extend(self._check_confirmation_bias(data, context))
        detections.extend(self._check_stereotyping(data, context))
        detections.extend(self._check_algorithmic_bias(data, context))
        
        return detections
    
    def _check_selection_bias(self, data: Any, context: Dict[str, Any]) -> List[BiasDetection]:
        """Check for selection bias."""
        detections = []
        
        # Check if data source is specified
        data_source = context.get("data_source", "")
        if data_source and "convenience" in data_source.lower():
            detections.append(BiasDetection(
                bias_type=BiasType.SELECTION,
                confidence=0.7,
                description="Data from convenience sample may not be representative",
                source=data_source,
                indicators=["convenience sampling", "non-random selection"],
                recommendations=["Use representative sampling", "Acknowledge limitations"]
            ))
        
        return detections
    
    def _check_confirmation_bias(self, data: Any, context: Dict[str, Any]) -> List[BiasDetection]:
        """Check for confirmation bias."""
        detections = []
        
        # Check if only supporting evidence was considered
        if context.get("considered_alternatives", True) == False:
            detections.append(BiasDetection(
                bias_type=BiasType.CONFIRMATION,
                confidence=0.8,
                description="Only confirming information considered - alternative viewpoints missing",
                source="reasoning_process",
                indicators=["no counter-evidence", "single perspective"],
                recommendations=["Actively seek disconfirming evidence", "Consider multiple viewpoints"]
            ))
        
        return detections
    
    def _check_stereotyping(self, data: Any, context: Dict[str, Any]) -> List[BiasDetection]:
        """Check for stereotyping bias."""
        detections = []
        
        # Check for demographic categorization without individual assessment
        if context.get("uses_demographics", False) and not context.get("individual_assessment", True):
            detections.append(BiasDetection(
                bias_type=BiasType.STEREOTYPING,
                confidence=0.6,
                description="Reliance on demographic categories without individual assessment",
                source="classification",
                indicators=["group-based assumptions"],
                recommendations=["Assess individuals on merits", "Avoid group generalizations"]
            ))
        
        return detections
    
    def _check_algorithmic_bias(self, data: Any, context: Dict[str, Any]) -> List[BiasDetection]:
        """Check for algorithmic bias."""
        detections = []
        
        # Check if training data is biased
        training_data_info = context.get("training_data", {})
        if training_data_info.get("demographic_imbalance", False):
            detections.append(BiasDetection(
                bias_type=BiasType.ALGORITHMIC,
                confidence=0.75,
                description="Training data shows demographic imbalance",
                source="training_data",
                indicators=["underrepresentation", "class imbalance"],
                recommendations=["Rebalance training data", "Apply fairness constraints"]
            ))
        
        return detections
    
    def mitigate(self, detections: List[BiasDetection]) -> List[str]:
        """Generate mitigation strategies for detected biases."""
        mitigations = []
        
        for detection in detections:
            mitigations.extend(detection.recommendations)
        
        return list(set(mitigations))  # Deduplicate


class CulturalSensitivityFramework:
    """Framework for cultural sensitivity and adaptation."""
    
    def __init__(self):
        self._cultural_contexts: Dict[str, Dict[str, Any]] = {}
        self._load_cultural_contexts()
    
    def _load_cultural_contexts(self):
        """Load known cultural contexts and considerations."""
        self._cultural_contexts = {
            "collectivist": {
                "values": ["group harmony", "collective good", "hierarchy"],
                "sensitivities": ["avoid confrontation", "respect elders", "indirect communication"]
            },
            "individualist": {
                "values": ["personal autonomy", "individual achievement", "directness"],
                "sensitivities": ["respect privacy", "value choice", "merit-based"]
            },
            "high_context": {
                "values": ["implicit communication", "relationship", "context"],
                "sensitivities": ["read between lines", "relationship first", "non-verbal cues"]
            },
            "low_context": {
                "values": ["explicit communication", "clarity", "efficiency"],
                "sensitivities": ["be direct", "document everything", "clarity over subtlety"]
            }
        }
    
    def assess(self, action_description: str, 
              cultural_context: str,
              context: Dict[str, Any]) -> List[CulturalConsideration]:
        """
        Assess cultural considerations for an action.
        
        Args:
            action_description: The action to assess
            cultural_context: The cultural context (e.g., "collectivist", "japanese")
            context: Additional context
        
        Returns:
            List of cultural considerations
        """
        considerations = []
        
        # Get cultural profile
        profile = self._cultural_contexts.get(cultural_context, {})
        
        if profile:
            considerations.append(CulturalConsideration(
                culture=cultural_context,
                context=action_description,
                consideration=f"Operating in {cultural_context} context",
                sensitivity_level="medium",
                recommendations=profile.get("sensitivities", [])
            ))
        
        # Check for specific cultural issues
        if "direct refusal" in action_description.lower():
            considerations.append(CulturalConsideration(
                culture=cultural_context,
                context="communication style",
                consideration="Direct refusal may be culturally inappropriate",
                sensitivity_level="high",
                recommendations=["Use indirect refusal", "Offer alternatives", "Preserve face"]
            ))
        
        if "personal question" in action_description.lower():
            considerations.append(CulturalConsideration(
                culture=cultural_context,
                context="privacy norms",
                consideration="Personal questions may violate cultural privacy norms",
                sensitivity_level="medium",
                recommendations=["Ask permission first", "Explain purpose", "Allow decline"]
            ))
        
        return considerations


class EthicsEngine:
    """
    Main ethics evaluation engine.
    
    Coordinates harm assessment, bias detection, and cultural sensitivity
to provide comprehensive ethical evaluation.
    """
    
    def __init__(self, framework: EthicalFramework = EthicalFramework.PRINCIPLIST):
        self.framework = framework
        self.harm_assessor = HarmAssessor()
        self.bias_detector = BiasDetector()
        self.cultural_framework = CulturalSensitivityFramework()
        self._history: List[EthicalEvaluation] = []
    
    def evaluate(self, action_id: str, action_description: str,
                context: Dict[str, Any]) -> EthicalEvaluation:
        """
        Perform comprehensive ethical evaluation.
        
        Args:
            action_id: Unique identifier for the action
            action_description: Description of the action
            context: Operation context
        
        Returns:
            EthicalEvaluation with complete analysis
        """
        # Assess harms
        harm_assessments = self.harm_assessor.assess(action_description, context)
        
        # Detect biases
        data = context.get("data", {})
        bias_detections = self.bias_detector.detect(data, context)
        
        # Assess cultural considerations
        cultural_context = context.get("cultural_context", "")
        cultural_considerations = []
        if cultural_context:
            cultural_considerations = self.cultural_framework.assess(
                action_description, cultural_context, context
            )
        
        # Generate recommendations
        recommendations = self._generate_recommendations(
            harm_assessments, bias_detections, cultural_considerations
        )
        
        # Generate constraints
        constraints = self._generate_constraints(harm_assessments)
        
        # Create evaluation
        evaluation = EthicalEvaluation(
            action_id=action_id,
            action_description=action_description,
            framework=self.framework,
            harm_assessments=harm_assessments,
            bias_detections=bias_detections,
            cultural_considerations=cultural_considerations,
            recommendations=recommendations,
            constraints=constraints,
            metadata={"context": context}
        )
        
        self._history.append(evaluation)
        return evaluation
    
    def _generate_recommendations(self, harms: List[HarmAssessment],
                                 biases: List[BiasDetection],
                                 cultural: List[CulturalConsideration]) -> List[str]:
        """Generate recommendations based on assessments."""
        recommendations = []
        
        # Add harm mitigations
        for harm in harms:
            recommendations.extend(harm.mitigations)
        
        # Add bias mitigations
        recommendations.extend(self.bias_detector.mitigate(biases))
        
        # Add cultural recommendations
        for cc in cultural:
            recommendations.extend(cc.recommendations)
        
        # Deduplicate while preserving order
        seen = set()
        unique = []
        for r in recommendations:
            if r not in seen:
                seen.add(r)
                unique.append(r)
        
        return unique
    
    def _generate_constraints(self, harms: List[HarmAssessment]) -> List[str]:
        """Generate ethical constraints based on harm assessments."""
        constraints = []
        
        for harm in harms:
            if harm.risk_score > 0.7:
                constraints.append(f"CRITICAL: {harm.harm_type.name} risk too high - requires additional safeguards")
            elif harm.risk_score > 0.5:
                constraints.append(f"HIGH: Mitigate {harm.harm_type.name} risk before proceeding")
        
        return constraints
    
    def evaluate_framework(self, action_description: str, context: Dict[str, Any],
                          frameworks: Optional[List[EthicalFramework]] = None) -> Dict[EthicalFramework, EthicalEvaluation]:
        """
        Evaluate using multiple ethical frameworks.
        
        Useful for complex ethical dilemmas where different frameworks
        may yield different conclusions.
        """
        if frameworks is None:
            frameworks = list(EthicalFramework)
        
        results = {}
        original_framework = self.framework
        
        for framework in frameworks:
            self.framework = framework
            eval_id = f"{framework.name.lower()}-{datetime.now().timestamp()}"
            results[framework] = self.evaluate(eval_id, action_description, context)
        
        self.framework = original_framework
        return results
    
    def get_ethics_summary(self) -> Dict[str, Any]:
        """Get summary of ethics evaluations."""
        if not self._history:
            return {"total_evaluations": 0}
        
        total = len(self._history)
        ethical = sum(1 for e in self._history if e.is_ethical)
        critical_harm = sum(1 for e in self._history if e.has_critical_harm)
        significant_bias = sum(1 for e in self._history if e.has_significant_bias)
        
        return {
            "total_evaluations": total,
            "ethical_actions": ethical,
            "unethical_actions": total - ethical,
            "critical_harm_detected": critical_harm,
            "significant_bias_detected": significant_bias,
            "average_risk": sum(e.overall_risk for e in self._history) / total
        }


# Global engine instance
_engine: Optional[EthicsEngine] = None


def get_ethics_engine(framework: EthicalFramework = EthicalFramework.PRINCIPLIST) -> EthicsEngine:
    """Get global ethics engine."""
    global _engine
    if _engine is None:
        _engine = EthicsEngine(framework)
    return _engine


def evaluate_ethics(action_id: str, action_description: str,
                   context: Dict[str, Any]) -> EthicalEvaluation:
    """Evaluate ethics of an action."""
    return get_ethics_engine().evaluate(action_id, action_description, context)


def detect_bias(data: Any, context: Dict[str, Any]) -> List[BiasDetection]:
    """Detect bias in data."""
    return BiasDetector().detect(data, context)


def assess_harm(action_description: str, context: Dict[str, Any]) -> List[HarmAssessment]:
    """Assess potential harm."""
    return HarmAssessor().assess(action_description, context)