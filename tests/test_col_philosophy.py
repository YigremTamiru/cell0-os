"""
COL Philosophy Module Tests
============================
Comprehensive test suite for the COL Philosophy module.

Tests cover:
- Principle management and registry
- Alignment checking
- Tension detection and resolution
- Sovereignty preservation
- Ethical constraint enforcement
"""

import unittest
from datetime import datetime, timedelta
import json

# Import all modules
from col.philosophy import (
    # Principles
    Principle, PrinciplePriority, PrincipleCategory, PrincipleRegistry,
    get_principle_registry, get_principle, get_all_principles,
    
    # Alignment
    AlignmentCheck, AlignmentReport, AlignmentStatus, AlignmentChecker,
    ViolationSeverity, check_alignment, quick_check,
    
    # Tension
    Tension, TensionType, ResolutionStrategy, ResolutionResult,
    TensionDetector, TensionResolver, detect_tensions, resolve_tension,
    
    # Sovereignty
    ConsentRecord, ConsentType, DelegationRecord, DelegationScope,
    SovereigntyManager, record_consent, check_consent, can_override,
    
    # Ethics
    EthicalFramework, HarmType, BiasType, HarmAssessment, BiasDetection,
    EthicalEvaluation, EthicsEngine, HarmAssessor, BiasDetector,
    evaluate_ethics, detect_bias, assess_harm
)


class TestPrinciples(unittest.TestCase):
    """Test principle management."""
    
    def setUp(self):
        """Reset registry before each test."""
        from col.philosophy.principles import reset_principle_registry
        reset_principle_registry()
        self.registry = get_principle_registry()
    
    def test_core_principles_loaded(self):
        """Test that core principles are loaded on init."""
        principles = self.registry.get_all()
        self.assertGreater(len(principles), 10)  # Should have many core principles
        
        # Check key principles exist
        self.assertIsNotNone(self.registry.get("sov.001"))  # User Sovereignty
        self.assertIsNotNone(self.registry.get("eth.001"))  # Harm Prevention
        self.assertIsNotNone(self.registry.get("sft.001"))  # Life Preservation
    
    def test_principle_attributes(self):
        """Test principle has correct attributes."""
        principle = self.registry.get("sov.001")
        
        self.assertEqual(principle.id, "sov.001")
        self.assertEqual(principle.name, "User Sovereignty")
        self.assertEqual(principle.priority, PrinciplePriority.SOVEREIGN)
        self.assertEqual(principle.category, PrincipleCategory.SOVEREIGNTY)
        self.assertTrue(principle.metadata.get("immutable", False))
    
    def test_principle_serialization(self):
        """Test principle to/from dict."""
        principle = self.registry.get("sov.001")
        
        # To dict
        data = principle.to_dict()
        self.assertEqual(data["id"], "sov.001")
        self.assertEqual(data["priority"], "SOVEREIGN")
        
        # From dict
        restored = Principle.from_dict(data)
        self.assertEqual(restored.id, principle.id)
        self.assertEqual(restored.name, principle.name)
    
    def test_get_by_category(self):
        """Test getting principles by category."""
        ethics = self.registry.get_by_category(PrincipleCategory.ETHICS)
        self.assertGreater(len(ethics), 0)
        
        for p in ethics:
            self.assertEqual(p.category, PrincipleCategory.ETHICS)
    
    def test_get_by_priority(self):
        """Test getting principles by priority."""
        sovereign = self.registry.get_by_priority(PrinciplePriority.SOVEREIGN)
        self.assertGreater(len(sovereign), 0)
        
        for p in sovereign:
            self.assertEqual(p.priority, PrinciplePriority.SOVEREIGN)
    
    def test_priority_hierarchy(self):
        """Test principle priority hierarchy."""
        hierarchy = self.registry.get_hierarchy()
        
        # Should have principles at different levels
        self.assertIn(PrinciplePriority.SOVEREIGN, hierarchy)
        self.assertIn(PrinciplePriority.ETHICAL, hierarchy)
    
    def test_compare_priorities(self):
        """Test comparing principle priorities."""
        # Sovereignty > Ethics
        result = self.registry.compare_priorities("sov.001", "eth.001")
        self.assertEqual(result, 1)
        
        # Ethics < Sovereignty
        result = self.registry.compare_priorities("eth.001", "sov.001")
        self.assertEqual(result, -1)
        
        # Same priority
        result = self.registry.compare_priorities("sov.001", "sov.002")
        self.assertEqual(result, 0)
    
    def test_cannot_deactivate_immutable(self):
        """Test that immutable principles cannot be deactivated."""
        principle = self.registry.get("sov.001")
        self.assertTrue(principle.metadata.get("immutable"))
        
        result = self.registry.deactivate("sov.001")
        self.assertFalse(result)
        
        # Principle should still be active
        self.assertTrue(principle.active)


class TestAlignment(unittest.TestCase):
    """Test alignment checking."""
    
    def setUp(self):
        """Reset checker before each test."""
        from col.philosophy.alignment import reset_alignment_checker
        from col.philosophy.principles import reset_principle_registry
        reset_principle_registry()
        reset_alignment_checker()
        self.checker = AlignmentChecker()
    
    def test_aligned_operation(self):
        """Test aligned operation check."""
        context = {
            "intent": "helpful action",
            "consent_obtained": True,
            "potential_harm": 0.0,
            "respects_autonomy": True,
            "explainable": True,
            "truthful": True
        }
        
        report = self.checker.check_alignment(
            operation_id="test-001",
            operation_type="test",
            operation_description="A helpful test operation",
            context=context
        )
        
        self.assertEqual(report.status, AlignmentStatus.ALIGNED)
        self.assertTrue(report.is_aligned)
        self.assertEqual(report.alignment_score, 1.0)
    
    def test_misaligned_operation(self):
        """Test misaligned operation detection."""
        context = {
            "intent": "harmful action",
            "consent_obtained": False,
            "potential_harm": 0.8,
            "respects_autonomy": False,
            "system_override": True
        }
        
        report = self.checker.check_alignment(
            operation_id="test-002",
            operation_type="test",
            operation_description="A harmful test operation",
            context=context
        )
        
        self.assertIn(report.status, [AlignmentStatus.MISALIGNED, AlignmentStatus.BLOCKED])
        self.assertFalse(report.is_aligned)
        self.assertGreater(len(report.violations), 0)
    
    def test_critical_harm_detection(self):
        """Test detection of critical harm."""
        context = {
            "life_at_risk": True,
            "potential_harm": 0.9
        }
        
        report = self.checker.check_alignment(
            operation_id="test-003",
            operation_type="emergency",
            operation_description="Life at risk situation",
            context=context
        )
        
        # Should have critical violations
        critical = report.critical_violations
        self.assertGreater(len(critical), 0)
    
    def test_alignment_check_object(self):
        """Test AlignmentCheck dataclass."""
        check = AlignmentCheck(
            principle_id="test.001",
            principle_name="Test Principle",
            principle_priority=PrinciplePriority.OPERATIONAL,
            aligned=True,
            confidence=0.9,
            reasoning="Test reasoning"
        )
        
        self.assertTrue(check.aligned)
        self.assertEqual(check.confidence, 0.9)
        
        # Test serialization
        data = check.to_dict()
        self.assertEqual(data["principle_id"], "test.001")
    
    def test_quick_check(self):
        """Test quick alignment check."""
        context = {"consent_obtained": True, "potential_harm": 0.0}
        result = quick_check("test", context)
        self.assertTrue(result)
        
        context = {"consent_obtained": False, "potential_harm": 0.9}
        result = quick_check("test", context)
        self.assertFalse(result)


class TestTension(unittest.TestCase):
    """Test tension detection and resolution."""
    
    def setUp(self):
        """Set up tension detector and resolver."""
        self.detector = TensionDetector()
        self.resolver = TensionResolver()
    
    def test_tension_detection(self):
        """Test detecting tensions between principles."""
        # Create checks that would create tension
        checks = [
            AlignmentCheck(
                principle_id="sov.001",
                principle_name="User Sovereignty",
                principle_priority=PrinciplePriority.SOVEREIGN,
                aligned=False,
                confidence=0.9,
                reasoning="System override"
            ),
            AlignmentCheck(
                principle_id="sft.002",
                principle_name="Safety Override",
                principle_priority=PrinciplePriority.LIFE_CRITICAL,
                aligned=False,
                confidence=0.9,
                reasoning="Safety requires override"
            )
        ]
        
        context = {"emergency": True}
        tensions = self.detector.detect(checks, context)
        
        # Should detect tension
        self.assertGreater(len(tensions), 0)
        
        # Check tension properties
        tension = tensions[0]
        self.assertIn("sov.001", tension.principle_ids)
        self.assertIn("sft.002", tension.principle_ids)
    
    def test_priority_based_resolution(self):
        """Test priority-based tension resolution."""
        # Test with principles where priorities are clearly ordered
        # SOVEREIGN (900) vs ETHICAL (700) - Sovereignty wins
        tension = Tension(
            id="test-tension",
            name="Test Tension",
            description="Test",
            tension_type=TensionType.DIRECT_CONFLICT,
            principle_ids=["sov.001", "eth.001"],  # Sovereignty vs Harm Prevention
            auto_resolvable=True
        )
        
        result = self.resolver.resolve(tension)
        
        self.assertTrue(result.resolved)
        self.assertEqual(result.strategy, ResolutionStrategy.PRIORITY_BASED)
        
        # Higher priority (sov.001 - SOVEREIGN = 900) wins over ETHICAL (700)
        self.assertIn("sov.001", result.winning_principles)
    
    def test_delegation_resolution(self):
        """Test delegation resolution for non-auto-resolvable tensions."""
        tension = Tension(
            id="test-tension",
            name="Test Tension",
            description="Test",
            tension_type=TensionType.RESOURCE_COMPETITION,
            principle_ids=["eth.003"],
            auto_resolvable=False  # Requires human decision
        )
        
        result = self.resolver.resolve(tension)
        
        self.assertFalse(result.resolved)
        self.assertEqual(result.strategy, ResolutionStrategy.DELEGATION)
        self.assertTrue(result.requires_approval)
    
    def test_resolution_result(self):
        """Test ResolutionResult dataclass."""
        result = ResolutionResult(
            tension_id="test",
            resolved=True,
            strategy=ResolutionStrategy.COMPROMISE,
            winning_principles=["p1"],
            suppressed_principles=["p2"],
            rationale="Test resolution",
            requires_notification=False,
            requires_approval=False
        )
        
        self.assertTrue(result.resolved)
        
        data = result.to_dict()
        self.assertEqual(data["strategy"], "COMPROMISE")


class TestSovereignty(unittest.TestCase):
    """Test sovereignty preservation."""
    
    def setUp(self):
        """Set up sovereignty manager."""
        self.manager = SovereigntyManager()
    
    def test_consent_recording(self):
        """Test recording and checking consent."""
        # Record consent
        consent = self.manager.record_consent(
            user_id="user-001",
            action_id="action-001",
            action_description="Test action",
            consent_type=ConsentType.EXPLICIT
        )
        
        self.assertIsNotNone(consent)
        self.assertEqual(consent.granted_by, "user-001")
        self.assertTrue(consent.is_valid)
        
        # Check consent exists
        found = self.manager.check_consent("user-001", "action-001")
        self.assertIsNotNone(found)
        self.assertEqual(found.id, consent.id)
    
    def test_consent_expiration(self):
        """Test consent expiration."""
        consent = self.manager.record_consent(
            user_id="user-001",
            action_id="action-002",
            action_description="Test action",
            duration_minutes=-1  # Already expired
        )
        
        self.assertFalse(consent.is_valid)
        self.assertEqual(consent.status, "EXPIRED")
    
    def test_consent_revocation(self):
        """Test consent revocation."""
        consent = self.manager.record_consent(
            user_id="user-001",
            action_id="action-003",
            action_description="Test action"
        )
        
        # Revoke
        self.manager.revoke_consent(consent.id, "user-001", "Changed my mind")
        
        self.assertFalse(consent.is_valid)
        self.assertEqual(consent.status, "REVOKED")
        self.assertEqual(consent.revocation_reason, "Changed my mind")
    
    def test_delegation(self):
        """Test authority delegation."""
        delegation = self.manager.create_delegation(
            delegator="user-001",
            delegate="system",
            scope=DelegationScope.CATEGORY,
            permissions=["read", "write"],
            duration_minutes=60
        )
        
        self.assertTrue(delegation.is_valid)
        self.assertTrue(delegation.has_permission("read"))
        self.assertFalse(delegation.has_permission("delete"))
    
    def test_sovereignty_assertion(self):
        """Test sovereignty assertion."""
        result = self.manager.assert_sovereignty(
            user_id="user-001",
            directive="Stop all automated actions",
            context={}
        )
        
        self.assertTrue(result["effective"])
        self.assertEqual(result["user_id"], "user-001")
    
    def test_system_override_justification(self):
        """Test system override justification checking."""
        # Should not allow override normally
        can_override, reason = self.manager.can_system_override({})
        self.assertFalse(can_override)
        
        # Should allow override in life-threatening situation
        can_override, reason = self.manager.can_system_override({
            "life_threatening": True
        })
        self.assertTrue(can_override)
        
        # Should allow override in emergency with immediate harm
        can_override, reason = self.manager.can_system_override({
            "emergency": True,
            "immediate_harm": True
        })
        self.assertTrue(can_override)


class TestEthics(unittest.TestCase):
    """Test ethical framework."""
    
    def setUp(self):
        """Set up ethics engine."""
        self.engine = EthicsEngine()
    
    def test_ethical_evaluation(self):
        """Test ethical evaluation of an action."""
        evaluation = self.engine.evaluate(
            action_id="test-action",
            action_description="Help the user with a task",
            context={
                "affected_parties": ["user"],
                "has_private_data": False
            }
        )
        
        self.assertIsNotNone(evaluation)
        self.assertEqual(evaluation.action_id, "test-action")
        self.assertGreaterEqual(evaluation.confidence, 0.0)
        self.assertLessEqual(evaluation.confidence, 1.0)
    
    def test_harm_assessment(self):
        """Test harm assessment."""
        assessor = HarmAssessor()
        
        context = {
            "affected_parties": ["user"],
            "has_private_data": True
        }
        
        assessments = assessor.assess("Process personal data", context)
        
        # Should detect privacy harm
        privacy_harms = [a for a in assessments if a.harm_type == HarmType.PRIVACY]
        self.assertGreater(len(privacy_harms), 0)
    
    def test_bias_detection(self):
        """Test bias detection."""
        detector = BiasDetector()
        
        # Context suggesting selection bias
        context = {
            "data_source": "convenience sample from volunteers"
        }
        
        biases = detector.detect({}, context)
        
        # Should detect selection bias
        selection_biases = [b for b in biases if b.bias_type == BiasType.SELECTION]
        self.assertGreater(len(selection_biases), 0)
    
    def test_cultural_sensitivity(self):
        """Test cultural sensitivity assessment."""
        considerations = self.engine.cultural_framework.assess(
            action_description="Give direct refusal",
            cultural_context="collectivist",
            context={}
        )
        
        # Should have considerations for collectivist context
        self.assertGreater(len(considerations), 0)
        
        # Should warn about direct refusal
        direct_refusal = [c for c in considerations if "direct refusal" in c.consideration.lower()]
        self.assertGreater(len(direct_refusal), 0)
    
    def test_ethical_constraints(self):
        """Test generation of ethical constraints."""
        evaluation = self.engine.evaluate(
            action_id="risky-action",
            action_description="Delete sensitive personal data without backup",
            context={
                "has_private_data": True,
                "affected_parties": ["user", "third_parties"],
                "data_subjects": ["user", "third_parties"],
                "potential_harm": 0.8
            }
        )
        
        # Should have either harm assessments or constraints
        self.assertTrue(
            len(evaluation.harm_assessments) > 0 or len(evaluation.constraints) > 0
        )
    
    def test_high_harm_detection(self):
        """Test detection of high-harm actions."""
        evaluation = self.engine.evaluate(
            action_id="harmful-action",
            action_description="Delete all user data without backup causing severe privacy breach",
            context={
                "potential_harm": 0.9,
                "affected_parties": ["all users"],
                "has_private_data": True,
                "data_subjects": ["all users"]
            }
        )
        
        # Should detect harm assessments
        self.assertGreater(len(evaluation.harm_assessments), 0)
        
        # Should have high overall risk or be marked unethical
        self.assertTrue(
            not evaluation.is_ethical or evaluation.overall_risk > 0.1
        )


class TestIntegration(unittest.TestCase):
    """Integration tests for the full philosophy module."""
    
    def test_end_to_end_alignment_with_tension(self):
        """Test full alignment flow with tension detection and resolution."""
        from col.philosophy.alignment import reset_alignment_checker
        from col.philosophy.principles import reset_principle_registry
        reset_principle_registry()
        reset_alignment_checker()
        
        # Create scenario with tension: emergency requiring action without consent
        context = {
            "intent": "emergency assistance",
            "consent_obtained": False,  # Violates sov.002
            "life_at_risk": True,       # Violates sft.001 if not acted
            "emergency": True,
            "potential_harm": 0.1,      # Low harm from acting
            "respects_autonomy": False, # Temporarily
            "explainable": True,
            "truthful": True
        }
        
        # Check alignment
        report = check_alignment(
            operation_id="emergency-001",
            operation_type="emergency_response",
            operation_description="Emergency action without prior consent",
            context=context
        )
        
        # Should detect tension
        self.assertGreater(len(report.tensions), 0)
        
        # Should have recommendations
        self.assertGreater(len(report.recommendations), 0)
    
    def test_sovereignty_with_ethics(self):
        """Test sovereignty preserved even with ethical considerations."""
        manager = SovereigntyManager()
        
        # First create a delegation that conflicts
        delegation = manager.create_delegation(
            delegator="user-001",
            delegate="system",
            scope=DelegationScope.CATEGORY,
            permissions=["auto-process"]
        )
        
        # User makes potentially harmful choice
        result = manager.assert_sovereignty(
            user_id="user-001",
            directive="I want to proceed despite warning",
            context={"potential_harm": 0.3}
        )
        
        # Sovereignty should be effective
        self.assertTrue(result["effective"])
        
        # Should have either notifications or overrides (conflicting delegations cancelled)
        self.assertTrue(
            len(result["notifications"]) > 0 or len(result["overrides"]) > 0
        )
    
    def test_ethics_with_cultural_context(self):
        """Test ethical evaluation with cultural considerations."""
        engine = EthicsEngine()
        
        evaluation = engine.evaluate(
            action_id="cultural-test",
            action_description="Request personal information",
            context={
                "cultural_context": "high_context",
                "affected_parties": ["user"]
            }
        )
        
        # Should have cultural considerations
        self.assertGreater(len(evaluation.cultural_considerations), 0)
    
    def test_full_resolution_plan(self):
        """Test creating full resolution plan for multiple tensions."""
        resolver = TensionResolver()
        
        tensions = [
            Tension(
                id="t1",
                name="Tension 1",
                description="Test",
                tension_type=TensionType.DIRECT_CONFLICT,
                principle_ids=["sov.001", "sft.002"],
                auto_resolvable=True
            ),
            Tension(
                id="t2",
                name="Tension 2",
                description="Test",
                tension_type=TensionType.MUTUAL_EXCLUSION,
                principle_ids=["prv.002", "trn.001"],
                auto_resolvable=True
            )
        ]
        
        plan = resolver.create_resolution_plan(tensions)
        
        self.assertIn("tensions", plan)
        self.assertIn("resolution_order", plan)
        self.assertEqual(len(plan["resolution_order"]), 2)


class TestUtilityFunctions(unittest.TestCase):
    """Test utility and convenience functions."""
    
    def test_convenience_functions_exist(self):
        """Test that all convenience functions are available."""
        # Should be able to call these without error
        from col.philosophy import (
            get_principle, get_all_principles,
            get_principles_by_category, get_principles_by_priority,
            check_alignment, quick_check,
            detect_tensions, resolve_tension,
            record_consent, check_consent,
            evaluate_ethics, detect_bias, assess_harm
        )
        
        # Just check they exist and are callable
        self.assertTrue(callable(get_all_principles))
        self.assertTrue(callable(quick_check))
        self.assertTrue(callable(can_override))


class TestEdgeCases(unittest.TestCase):
    """Test edge cases and error handling."""
    
    def test_empty_context(self):
        """Test handling of empty context."""
        report = check_alignment(
            operation_id="empty-test",
            operation_type="test",
            operation_description="Test with empty context",
            context={}
        )
        
        # Should still produce a report
        self.assertIsNotNone(report)
        self.assertGreater(len(report.checks), 0)
    
    def test_unknown_principle(self):
        """Test handling of unknown principle IDs."""
        from col.philosophy.principles import reset_principle_registry
        reset_principle_registry()
        
        registry = get_principle_registry()
        
        # Should return None for unknown
        self.assertIsNone(registry.get("unknown.001"))
    
    def test_consent_revocation_nonexistent(self):
        """Test revoking non-existent consent."""
        manager = SovereigntyManager()
        
        result = manager.revoke_consent("nonexistent", "user", "test")
        self.assertFalse(result)
    
    def test_tension_with_single_principle(self):
        """Test tension with only one principle."""
        tension = Tension(
            id="single",
            name="Single",
            description="Test",
            tension_type=TensionType.DIRECT_CONFLICT,
            principle_ids=["sov.001"],
            auto_resolvable=True
        )
        
        resolver = TensionResolver()
        result = resolver.resolve(tension)
        
        # Should still resolve (trivially)
        self.assertTrue(result.resolved)


def run_tests():
    """Run all tests."""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add all test classes
    suite.addTests(loader.loadTestsFromTestCase(TestPrinciples))
    suite.addTests(loader.loadTestsFromTestCase(TestAlignment))
    suite.addTests(loader.loadTestsFromTestCase(TestTension))
    suite.addTests(loader.loadTestsFromTestCase(TestSovereignty))
    suite.addTests(loader.loadTestsFromTestCase(TestEthics))
    suite.addTests(loader.loadTestsFromTestCase(TestIntegration))
    suite.addTests(loader.loadTestsFromTestCase(TestUtilityFunctions))
    suite.addTests(loader.loadTestsFromTestCase(TestEdgeCases))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_tests()
    exit(0 if success else 1)