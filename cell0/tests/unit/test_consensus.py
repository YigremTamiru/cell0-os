"""
Comprehensive Tests for Cell0 BFT Consensus Module

Tests PBFT-style consensus including:
- Basic consensus flow
- Byzantine fault detection
- View changes
- Quorum handling
- Message validation
- Slashing mechanisms
"""

import pytest
import asyncio
import time
from unittest.mock import Mock, AsyncMock, patch

# Import consensus module
from cell0.swarm.consensus import (
    BFTConsensus,
    FastBFTConsensus,
    ConsensusMessage,
    ConsensusInstance,
    ConsensusPhase,
    ConsensusResult,
    ByzantineEvidence,
)


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def basic_consensus():
    """Create a basic consensus instance for testing"""
    return BFTConsensus(
        node_id="node_0",
        total_nodes=4,  # Small cluster for testing
        consensus_timeout=1.0
    )


@pytest.fixture
def multi_node_cluster():
    """Create a cluster of consensus nodes"""
    nodes = []
    for i in range(4):
        node = BFTConsensus(
            node_id=f"node_{i}",
            total_nodes=4,
            consensus_timeout=1.0
        )
        node.set_primary("node_0")  # node_0 is primary
        nodes.append(node)
    return nodes


@pytest.fixture
def mock_callbacks(basic_consensus):
    """Setup mock callbacks for consensus"""
    broadcast_mock = Mock()
    send_mock = Mock()
    basic_consensus.set_broadcast_callback(broadcast_mock)
    basic_consensus.set_send_callback(send_mock)
    return basic_consensus, broadcast_mock, send_mock


# =============================================================================
# Basic Consensus Tests
# =============================================================================

class TestConsensusInitialization:
    """Test consensus engine initialization"""
    
    def test_basic_initialization(self, basic_consensus):
        """Test basic consensus initialization"""
        assert basic_consensus.node_id == "node_0"
        assert basic_consensus.total_nodes == 4
        assert basic_consensus.max_faulty == 1  # (4-1)//3 = 1
        assert basic_consensus.prepare_quorum == 3  # 4-1
        assert basic_consensus.commit_quorum == 3
        
    def test_quorum_calculation(self):
        """Test quorum calculations for different cluster sizes"""
        test_cases = [
            (4, 1, 3, 3),    # n=4, f=1
            (7, 2, 5, 5),    # n=7, f=2
            (10, 3, 7, 7),   # n=10, f=3
            (200, 66, 134, 134),  # Large cluster
        ]
        
        for total, max_faulty, prepare_q, commit_q in test_cases:
            consensus = BFTConsensus("test", total_nodes=total)
            assert consensus.max_faulty == max_faulty, f"Failed for n={total}"
            assert consensus.prepare_quorum == prepare_q
            assert consensus.commit_quorum == commit_q
            
    def test_initial_state(self, basic_consensus):
        """Test initial state of consensus engine"""
        assert basic_consensus.view_number == 0
        assert basic_consensus.sequence_number == 0
        assert basic_consensus.primary_id is None
        assert len(basic_consensus.instances) == 0
        assert len(basic_consensus.completed_instances) == 0
        assert len(basic_consensus.slashed_agents) == 0
        
    def test_set_primary(self, basic_consensus):
        """Test setting primary node"""
        basic_consensus.set_primary("node_1")
        assert basic_consensus.primary_id == "node_1"


class TestMessageValidation:
    """Test message validation logic"""
    
    def test_valid_message(self, basic_consensus):
        """Test validation of valid message"""
        msg = ConsensusMessage(
            msg_type="PREPARE",
            view_number=0,
            sequence_number=1,
            digest="abc123",
            payload={},
            sender_id="node_1"
        )
        assert basic_consensus._validate_message(msg) is True
        
    def test_invalid_sender(self, basic_consensus):
        """Test rejection of message from self"""
        msg = ConsensusMessage(
            msg_type="PREPARE",
            view_number=0,
            sequence_number=1,
            digest="abc123",
            payload={},
            sender_id="node_0"  # Same as node_id
        )
        assert basic_consensus._validate_message(msg) is False
        
    def test_slashed_agent_message(self, basic_consensus):
        """Test rejection of message from slashed agent"""
        basic_consensus.slashed_agents.add("bad_node")
        msg = ConsensusMessage(
            msg_type="PREPARE",
            view_number=0,
            sequence_number=1,
            digest="abc123",
            payload={},
            sender_id="bad_node"
        )
        assert basic_consensus._validate_message(msg) is False
        
    def test_empty_sender(self, basic_consensus):
        """Test rejection of message with empty sender"""
        msg = ConsensusMessage(
            msg_type="PREPARE",
            view_number=0,
            sequence_number=1,
            digest="abc123",
            payload={},
            sender_id=""
        )
        assert basic_consensus._validate_message(msg) is False


class TestDigestComputation:
    """Test cryptographic digest computation"""
    
    def test_digest_consistency(self, basic_consensus):
        """Test that same data produces same digest"""
        data = {"key": "value", "number": 42}
        digest1 = basic_consensus._compute_digest(data)
        digest2 = basic_consensus._compute_digest(data)
        assert digest1 == digest2
        assert len(digest1) == 64  # SHA-256 hex
        
    def test_digest_uniqueness(self, basic_consensus):
        """Test that different data produces different digests"""
        data1 = {"key": "value1"}
        data2 = {"key": "value2"}
        digest1 = basic_consensus._compute_digest(data1)
        digest2 = basic_consensus._compute_digest(data2)
        assert digest1 != digest2
        
    def test_digest_order_independence(self, basic_consensus):
        """Test that key order doesn't affect digest"""
        data1 = {"a": 1, "b": 2, "c": 3}
        data2 = {"c": 3, "a": 1, "b": 2}
        digest1 = basic_consensus._compute_digest(data1)
        digest2 = basic_consensus._compute_digest(data2)
        assert digest1 == digest2


# =============================================================================
# Consensus Flow Tests
# =============================================================================

class TestPrePreparePhase:
    """Test PRE-PREPARE phase handling"""
    
    @pytest.mark.asyncio
    async def test_primary_proposal(self, mock_callbacks):
        """Test that primary can propose"""
        consensus, broadcast_mock, _ = mock_callbacks
        consensus.set_primary("node_0")
        
        proposal = {"action": "test", "value": 42}
        result, digest = await consensus.propose(proposal)
        
        # Should return ACCEPTED and have broadcast
        assert result == ConsensusResult.ACCEPTED
        assert digest is not None
        assert len(digest) == 64  # SHA-256 hex
        
    @pytest.mark.asyncio
    async def test_non_primary_forwards(self, mock_callbacks):
        """Test that non-primary forwards to primary"""
        consensus, _, send_mock = mock_callbacks
        consensus.set_primary("node_1")  # Different primary
        
        proposal = {"action": "test"}
        result, digest = await consensus.propose(proposal)
        
        assert result == ConsensusResult.TIMEOUT  # Forwarded, not executed
        assert send_mock.called
        
    @pytest.mark.asyncio
    async def test_pre_prepare_from_non_primary(self, basic_consensus):
        """Test rejection of PRE-PREPARE from non-primary"""
        basic_consensus.set_primary("node_0")
        
        msg = ConsensusMessage(
            msg_type="PRE_PREPARE",
            view_number=0,
            sequence_number=1,
            digest="abc",
            payload={"test": "data"},
            sender_id="node_1"  # Not primary
        )
        
        result = await basic_consensus.handle_message(msg)
        # Should record Byzantine evidence
        assert len(basic_consensus.byzantine_evidence) == 1
        assert basic_consensus.byzantine_evidence[0].violation_type == "non_primary_pre_prepare"


class TestPreparePhase:
    """Test PREPARE phase handling"""
    
    @pytest.mark.asyncio
    async def test_prepare_quorum(self, multi_node_cluster):
        """Test that prepare quorum triggers commit"""
        nodes = multi_node_cluster
        
        # Setup first node as primary and create instance
        primary = nodes[0]
        primary.set_primary("node_0")
        
        # Mock broadcast to avoid network calls
        primary.set_broadcast_callback(Mock())
        
        proposal = {"action": "test"}
        
        # Create instance manually with proper digest
        digest = primary._compute_digest(proposal)
        instance = ConsensusInstance(
            instance_id="test_1",
            proposal=proposal,
            phase=ConsensusPhase.PRE_PREPARE,
            view_number=0,
            sequence_number=1,
            final_digest=digest,
            pre_prepare_received=True
        )
        primary.instances["test_1"] = instance
        primary.instance_by_seq[1] = instance
        
        # Send prepare messages from 3 nodes (quorum = 3)
        for i in range(3):
            msg = ConsensusMessage(
                msg_type="PREPARE",
                view_number=0,
                sequence_number=1,
                digest=digest,
                payload={},
                sender_id=f"node_{i+1}"
            )
            await primary.handle_message(msg)
        
        # Should have reached prepare quorum and transitioned to PREPARE phase
        assert len(instance.prepare_votes) >= 3
        assert instance.phase == ConsensusPhase.PREPARE


class TestCommitPhase:
    """Test COMMIT phase handling"""
    
    @pytest.mark.asyncio
    async def test_commit_quorum_reaches_consensus(self, multi_node_cluster):
        """Test that commit quorum reaches consensus"""
        primary = multi_node_cluster[0]
        primary.set_primary("node_0")
        primary.set_broadcast_callback(Mock())
        
        proposal = {"action": "test"}
        digest = primary._compute_digest(proposal)
        
        # Create instance in PREPARE phase
        instance = ConsensusInstance(
            instance_id="test_1",
            proposal=proposal,
            phase=ConsensusPhase.PREPARE,
            view_number=0,
            sequence_number=1,
            final_digest=digest,
            pre_prepare_received=True,
            prepare_votes={"node_1", "node_2", "node_3"}
        )
        primary.instances["test_1"] = instance
        primary.instance_by_seq[1] = instance
        
        # Send commit messages from 3 nodes
        for i in range(3):
            msg = ConsensusMessage(
                msg_type="COMMIT",
                view_number=0,
                sequence_number=1,
                digest=digest,
                payload={},
                sender_id=f"node_{i+1}"
            )
            result = await primary.handle_message(msg)
        
        # Should have reached consensus
        assert instance.phase == ConsensusPhase.EXECUTED
        assert instance.result == ConsensusResult.ACCEPTED
        assert 1 in primary.completed_instances


# =============================================================================
# Byzantine Fault Tests
# =============================================================================

class TestByzantineDetection:
    """Test Byzantine fault detection"""
    
    @pytest.mark.asyncio
    async def test_conflicting_pre_prepare(self, basic_consensus):
        """Test detection of conflicting PRE-PREPARE messages"""
        basic_consensus.set_primary("node_0")
        basic_consensus.set_broadcast_callback(Mock())
        
        # First PRE-PREPARE
        msg1 = ConsensusMessage(
            msg_type="PRE_PREPARE",
            view_number=0,
            sequence_number=1,
            digest="digest1",
            payload={"value": 1},
            sender_id="node_0"
        )
        await basic_consensus._handle_pre_prepare(msg1)
        
        # Conflicting PRE-PREPARE for same sequence
        msg2 = ConsensusMessage(
            msg_type="PRE_PREPARE",
            view_number=0,
            sequence_number=1,
            digest="digest2",
            payload={"value": 2},
            sender_id="node_0"
        )
        result = await basic_consensus._handle_pre_prepare(msg2)
        
        assert result == ConsensusResult.BYZANTINE_FAULT
        assert len(basic_consensus.byzantine_evidence) >= 1
        
    @pytest.mark.asyncio
    async def test_suspicion_scoring(self, basic_consensus):
        """Test suspicion score accumulation"""
        await basic_consensus._record_suspicion("suspicious_node", "test_reason")
        assert basic_consensus.suspicion_scores["suspicious_node"] == 0.1
        
        # Multiple suspicions - need to exceed 1.0 to trigger slashing
        # Starting at 0.1, need 9 more to reach 1.0, but need > 1.0 to slash
        for _ in range(10):
            await basic_consensus._record_suspicion("suspicious_node", "test_reason")
        
        # Should be slashed after exceeding 1.0 (at 1.1 now)
        assert "suspicious_node" in basic_consensus.slashed_agents
        
    @pytest.mark.asyncio
    async def test_byzantine_slashing(self, basic_consensus):
        """Test agent slashing for Byzantine behavior"""
        await basic_consensus._slash_agent("byzantine_node")
        
        assert "byzantine_node" in basic_consensus.slashed_agents
        # Quorum should be recalculated
        assert basic_consensus.total_nodes == 4  # Original count
        # Active nodes reduced
        active = basic_consensus.total_nodes - len(basic_consensus.slashed_agents)
        assert active == 3


class TestEvidenceCollection:
    """Test Byzantine evidence collection"""
    
    @pytest.mark.asyncio
    async def test_evidence_recording(self, basic_consensus):
        """Test recording Byzantine evidence"""
        msg1 = ConsensusMessage(
            msg_type="PRE_PREPARE",
            view_number=0,
            sequence_number=1,
            digest="abc",
            payload={},
            sender_id="bad_node"
        )
        msg2 = ConsensusMessage(
            msg_type="PRE_PREPARE",
            view_number=0,
            sequence_number=1,
            digest="def",
            payload={},
            sender_id="bad_node"
        )
        
        await basic_consensus._record_byzantine_evidence(
            "bad_node",
            "conflicting_messages",
            [msg1, msg2]
        )
        
        assert len(basic_consensus.byzantine_evidence) == 1
        evidence = basic_consensus.byzantine_evidence[0]
        assert evidence.agent_id == "bad_node"
        assert evidence.violation_type == "conflicting_messages"
        assert len(evidence.conflicting_messages) == 2
        assert basic_consensus.byzantine_detected == 1


# =============================================================================
# View Change Tests
# =============================================================================

class TestViewChanges:
    """Test view change protocol"""
    
    @pytest.mark.asyncio
    async def test_view_change_initiation(self, basic_consensus):
        """Test view change initiation"""
        basic_consensus.set_primary("node_0")
        
        await basic_consensus._initiate_view_change(1)
        
        assert basic_consensus.view_number == 1
        assert basic_consensus.view_changes == 1
        # Primary should rotate
        assert basic_consensus.primary_id != "node_0"
        
    @pytest.mark.asyncio
    async def test_view_change_no_regression(self, basic_consensus):
        """Test that view number cannot decrease"""
        basic_consensus.view_number = 5
        
        await basic_consensus._initiate_view_change(3)
        
        # View should stay at 5
        assert basic_consensus.view_number == 5
        
    @pytest.mark.asyncio
    async def test_primary_rotation(self):
        """Test round-robin primary rotation"""
        consensus = BFTConsensus("node_0", total_nodes=4)
        consensus.set_broadcast_callback(Mock())
        
        # Manually test primary selection for each view starting from view 1
        # (view 0 is initial state and doesn't trigger view change)
        node_list = [f"node_{i}" for i in range(4)]
        
        for view in range(1, 9):  # Start from 1
            await consensus._initiate_view_change(view)
            expected_primary = node_list[view % len(node_list)]
            assert consensus.primary_id == expected_primary
            # Each view should have different primary (cycles every 4)
            if view < 4:
                assert expected_primary == f"node_{view}"


# =============================================================================
# Timeout and Failure Tests
# =============================================================================

class TestTimeouts:
    """Test timeout handling"""
    
    @pytest.mark.asyncio
    async def test_consensus_timeout(self, basic_consensus):
        """Test consensus timeout"""
        # Create instance that won't reach consensus
        instance = ConsensusInstance(
            instance_id="timeout_test",
            proposal={"test": "data"},
            phase=ConsensusPhase.PRE_PREPARE,
            view_number=0,
            sequence_number=1
        )
        basic_consensus.instances["timeout_test"] = instance
        
        # Trigger timeout
        await basic_consensus._consensus_timer("timeout_test")
        
        assert instance.phase == ConsensusPhase.FAILED
        assert instance.result == ConsensusResult.TIMEOUT


# =============================================================================
# Status and Metrics Tests
# =============================================================================

class TestStatusAndMetrics:
    """Test status reporting and metrics"""
    
    def test_get_status(self, basic_consensus):
        """Test status report generation"""
        basic_consensus.set_primary("node_0")
        basic_consensus.consensus_count = 10
        basic_consensus.success_count = 8
        
        status = basic_consensus.get_status()
        
        assert status["node_id"] == "node_0"
        assert status["primary_id"] == "node_0"
        assert status["total_nodes"] == 4
        assert status["max_faulty"] == 1
        assert status["consensus_count"] == 10
        assert status["success_count"] == 8
        assert status["success_rate"] == 0.8
        
    def test_verify_consensus(self, basic_consensus):
        """Test consensus verification"""
        # Create completed instance
        instance = ConsensusInstance(
            instance_id="completed",
            proposal={},
            phase=ConsensusPhase.EXECUTED,
            view_number=0,
            sequence_number=1,
            result=ConsensusResult.ACCEPTED
        )
        basic_consensus.instances["completed"] = instance
        
        assert basic_consensus.verify_consensus("completed") is True
        assert basic_consensus.verify_consensus("nonexistent") is False


# =============================================================================
# Fast Consensus Tests
# =============================================================================

class TestFastBFTConsensus:
    """Test fast path consensus"""
    
    def test_fast_consensus_initialization(self):
        """Test fast consensus initialization"""
        consensus = FastBFTConsensus(
            node_id="node_0",
            total_nodes=4,
            optimistic_threshold=0.8
        )
        
        assert consensus.optimistic_threshold == 0.8
        assert consensus.optimistic_accepted == 0
        assert consensus.optimistic_rejected == 0
        
    @pytest.mark.asyncio
    async def test_fast_propose_fallback(self):
        """Test fast path falling back to PBFT"""
        consensus = FastBFTConsensus(
            node_id="node_0",
            total_nodes=4
        )
        consensus.set_primary("node_0")
        
        # Mock _collect_responses to return insufficient responses
        consensus._collect_responses = AsyncMock(return_value=[])
        
        proposal = {"action": "test"}
        result, digest = await consensus.propose_fast(proposal)
        
        # Should fall back to regular propose (which returns TIMEOUT without network)
        assert consensus.optimistic_rejected == 1


# =============================================================================
# Edge Cases and Stress Tests
# =============================================================================

class TestEdgeCases:
    """Test edge cases and boundary conditions"""
    
    def test_empty_proposal(self, basic_consensus):
        """Test handling of empty proposal"""
        digest = basic_consensus._compute_digest({})
        assert digest is not None
        assert len(digest) == 64
        
    def test_large_proposal(self, basic_consensus):
        """Test handling of large proposal"""
        large_data = {"key_" + str(i): "x" * 1000 for i in range(100)}
        digest = basic_consensus._compute_digest(large_data)
        assert digest is not None
        assert len(digest) == 64
        
    def test_special_characters(self, basic_consensus):
        """Test handling of special characters in data"""
        data = {
            "unicode": "Hello 世界 🌍",
            "special": "<script>alert('xss')</script>",
            "null": None,
            "bool": True
        }
        digest = basic_consensus._compute_digest(data)
        assert digest is not None
        
    @pytest.mark.asyncio
    async def test_duplicate_instance_id(self, mock_callbacks):
        """Test handling of duplicate instance IDs"""
        consensus, _, _ = mock_callbacks
        consensus.set_primary("node_0")
        
        proposal = {"action": "test"}
        
        # First proposal
        result1, digest1 = await consensus.propose(proposal, "instance_1")
        
        # Wait a bit for instance to be stored
        await asyncio.sleep(0.01)
        
        # Second proposal with same ID should return existing
        result2, digest2 = await consensus.propose({"action": "different"}, "instance_1")
        
        # Should return same digest (instance already exists)
        assert digest1 == digest2


class TestConcurrency:
    """Test concurrent operations"""
    
    @pytest.mark.asyncio
    async def test_concurrent_message_handling(self, basic_consensus):
        """Test handling concurrent messages"""
        basic_consensus.set_primary("node_0")
        basic_consensus.set_broadcast_callback(Mock())
        
        proposal = {"test": "data"}
        digest = basic_consensus._compute_digest(proposal)
        
        # Create instance
        instance = ConsensusInstance(
            instance_id="concurrent_test",
            proposal=proposal,
            phase=ConsensusPhase.PRE_PREPARE,
            view_number=0,
            sequence_number=1,
            final_digest=digest,
            pre_prepare_received=True
        )
        basic_consensus.instances["concurrent_test"] = instance
        basic_consensus.instance_by_seq[1] = instance
        
        # Send many prepare messages concurrently (unique nodes only)
        async def send_prepare(node_id):
            msg = ConsensusMessage(
                msg_type="PREPARE",
                view_number=0,
                sequence_number=1,
                digest=digest,
                payload={},
                sender_id=node_id
            )
            return await basic_consensus.handle_message(msg)
        
        # Use unique node IDs (only 3 needed for quorum)
        tasks = [send_prepare(f"node_{i}") for i in range(1, 4)]
        results = await asyncio.gather(*tasks)
        
        # All should complete without error
        assert len(results) == 3
        # Should have 3 unique votes (quorum reached)
        assert len(instance.prepare_votes) == 3


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
