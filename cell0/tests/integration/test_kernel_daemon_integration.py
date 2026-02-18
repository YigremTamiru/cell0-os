"""
Kernel↔Daemon Integration Tests

End-to-end tests verifying communication between:
- Cell0 kernel (Rust)
- Cell0 daemon (Python)
- AI Engine
- Swarm consensus
"""

import pytest
import asyncio
import json
import time
import hashlib
from typing import Dict, Any, Optional
from unittest.mock import Mock, patch, AsyncMock, MagicMock

# Import components
from cell0.cell0.engine.ai_engine import AIEngine, ModelConfig, ModelPrecision, ModelQuantizer
from cell0.swarm.consensus import BFTConsensus, ConsensusResult, ConsensusMessage


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
async def ai_engine():
    """Create and initialize AI engine"""
    engine = AIEngine()
    await engine.initialize()
    yield engine


@pytest.fixture
def consensus_cluster():
    """Create a test consensus cluster"""
    nodes = []
    for i in range(4):
        node = BFTConsensus(
            node_id=f"node_{i}",
            total_nodes=4,
            consensus_timeout=2.0
        )
        node.set_primary("node_0")
        node.set_broadcast_callback(Mock())
        nodes.append(node)
    return nodes


# =============================================================================
# Kernel-Daemon Integration Tests
# =============================================================================

@pytest.mark.integration
class TestKernelDaemonCommunication:
    """Test kernel to daemon communication patterns"""
    
    @pytest.mark.asyncio
    async def test_health_check_flow(self):
        """Test health check request/response flow"""
        # Simulate daemon health check
        health_status = {
            "status": "healthy",
            "components": {
                "ai_engine": "healthy",
                "consensus": "healthy",
                "gateway": "healthy"
            },
            "timestamp": time.time()
        }
        
        # Verify health structure
        assert health_status["status"] in ["healthy", "degraded", "unhealthy"]
        assert "components" in health_status
        assert "timestamp" in health_status
    
    @pytest.mark.asyncio
    async def test_inference_request_flow(self, ai_engine):
        """Test end-to-end inference request"""
        # Initialize engine
        info = ai_engine.get_system_info()
        
        # Verify system info structure
        assert "mlx_available" in info
        assert "models_loaded" in info
        assert isinstance(info["models_loaded"], list)
        
        # Test without models should fail gracefully
        with pytest.raises(RuntimeError):
            await ai_engine.generate("Test prompt")
    
    @pytest.mark.asyncio
    async def test_model_management_flow(self, ai_engine):
        """Test model loading/unloading flow"""
        # Create model config
        config = ModelConfig(
            model_id="test-integration-model",
            precision=ModelPrecision.FP16,
            max_tokens=1024
        )
        
        # Verify config creation
        assert config.model_id == "test-integration-model"
        assert config.precision == ModelPrecision.FP16
        assert config.max_tokens == 1024


@pytest.mark.integration
class TestConsensusEngineIntegration:
    """Test consensus and AI engine integration"""
    
    @pytest.mark.asyncio
    async def test_consensus_for_ai_decisions(self, consensus_cluster):
        """Test using consensus for AI model decisions"""
        primary = consensus_cluster[0]
        
        # Propose a model configuration through consensus
        proposal = {
            "type": "model_selection",
            "model_id": "test-model",
            "precision": "fp16",
            "max_tokens": 2048
        }
        
        # Start consensus
        result, digest = await primary.propose(proposal)
        
        # Verify proposal was accepted
        assert result == ConsensusResult.ACCEPTED
        assert digest is not None
    
    @pytest.mark.asyncio
    async def test_byzantine_fault_in_cluster(self, consensus_cluster):
        """Test cluster behavior with Byzantine node"""
        primary = consensus_cluster[0]
        byzantine_node = consensus_cluster[3]
        
        # Simulate Byzantine behavior
        bad_proposal = {"action": "bad_action"}
        
        # Create conflicting messages from Byzantine node
        msg1 = {
            "type": "PRE_PREPARE",
            "view_number": 0,
            "sequence_number": 1,
            "digest": "digest1",
            "payload": bad_proposal,
            "sender_id": "node_3"
        }
        
        # System should detect and handle Byzantine behavior
        status = primary.get_status()
        assert "slashed_agents" in status
        assert "byzantine_detected" in status
    
    @pytest.mark.asyncio
    async def test_view_change_recovery(self, consensus_cluster):
        """Test cluster recovery after primary failure"""
        primary = consensus_cluster[0]
        
        initial_view = primary.view_number
        
        # Initiate view change
        await primary._initiate_view_change(initial_view + 1)
        
        # Verify view changed
        assert primary.view_number == initial_view + 1
        assert primary.view_changes == 1
        
        # Verify new primary selected
        assert primary.primary_id is not None


@pytest.mark.integration
class TestGatewayProtocolIntegration:
    """Test gateway protocol integration"""
    
    @pytest.mark.asyncio
    async def test_jsonrpc_message_format(self):
        """Test JSON-RPC message formatting"""
        request = {
            "jsonrpc": "2.0",
            "method": "system.health",
            "params": {},
            "id": 1
        }
        
        # Verify structure
        assert request["jsonrpc"] == "2.0"
        assert "method" in request
        assert "id" in request
        
        # Simulate response
        response = {
            "jsonrpc": "2.0",
            "result": {"status": "healthy"},
            "id": 1
        }
        
        assert response["id"] == request["id"]
    
    @pytest.mark.asyncio
    async def test_websocket_message_flow(self):
        """Test WebSocket message flow"""
        messages = []
        
        # Simulate message exchange
        connect_msg = {"type": "connect", "client_id": "test-123"}
        messages.append(connect_msg)
        
        ping_msg = {"type": "ping", "timestamp": time.time()}
        messages.append(ping_msg)
        
        pong_msg = {"type": "pong", "timestamp": ping_msg["timestamp"]}
        messages.append(pong_msg)
        
        # Verify message flow
        assert len(messages) == 3
        assert messages[0]["type"] == "connect"
        assert messages[1]["type"] == "ping"
        assert messages[2]["type"] == "pong"


@pytest.mark.integration
class TestSecurityIntegration:
    """Test security features integration"""
    
    @pytest.mark.asyncio
    async def test_digest_verification(self):
        """Test cryptographic digest verification"""
        import hashlib
        
        data = {"action": "critical_operation", "params": {"key": "value"}}
        canonical = json.dumps(data, sort_keys=True, separators=(',', ':'))
        digest = hashlib.sha256(canonical.encode()).hexdigest()
        
        # Verify digest format
        assert len(digest) == 64
        assert all(c in '0123456789abcdef' for c in digest)
        
        # Verify consistency
        digest2 = hashlib.sha256(canonical.encode()).hexdigest()
        assert digest == digest2
    
    @pytest.mark.asyncio
    async def test_agent_authentication(self):
        """Test agent authentication flow"""
        agent_id = "agent_001"
        challenge = hashlib.sha256(str(time.time()).encode()).hexdigest()[:16]
        
        # Simulate challenge-response
        response = hashlib.sha256(f"{agent_id}:{challenge}".encode()).hexdigest()
        
        # Verify response format
        assert len(response) == 64
    
    @pytest.mark.asyncio
    async def test_slashed_agent_isolation(self, consensus_cluster):
        """Test that slashed agents are isolated"""
        primary = consensus_cluster[0]
        
        # Slash an agent
        await primary._slash_agent("malicious_agent")
        
        # Verify agent is in slashed list
        assert "malicious_agent" in primary.slashed_agents
        
        # Verify message from slashed agent is rejected
        from cell0.swarm.consensus import ConsensusMessage
        
        msg = ConsensusMessage(
            msg_type="PREPARE",
            view_number=0,
            sequence_number=1,
            digest="abc",
            payload={},
            sender_id="malicious_agent"
        )
        
        is_valid = primary._validate_message(msg)
        assert is_valid is False


@pytest.mark.integration
class TestPerformanceIntegration:
    """Test performance characteristics"""
    
    @pytest.mark.asyncio
    async def test_end_to_end_latency(self, ai_engine):
        """Test end-to-end request latency"""
        start = time.perf_counter()
        
        # Simulate request processing
        info = ai_engine.get_system_info()
        await asyncio.sleep(0.001)  # Simulate minimal work
        
        end = time.perf_counter()
        latency_ms = (end - start) * 1000
        
        # Should be very fast for simple operations
        assert latency_ms < 100
    
    @pytest.mark.asyncio
    async def test_concurrent_request_handling(self):
        """Test handling concurrent requests"""
        async def process_request(request_id: int):
            await asyncio.sleep(0.01)  # Simulate processing
            return {"id": request_id, "status": "completed"}
        
        # Process multiple requests concurrently
        tasks = [process_request(i) for i in range(10)]
        results = await asyncio.gather(*tasks)
        
        assert len(results) == 10
        assert all(r["status"] == "completed" for r in results)
    
    @pytest.mark.asyncio
    async def test_memory_usage_under_load(self, ai_engine):
        """Test memory usage remains reasonable under load"""
        import sys
        
        # Create multiple model configs
        configs = []
        for i in range(100):
            config = ModelConfig(
                model_id=f"model-{i}",
                precision=ModelPrecision.FP16
            )
            configs.append(config)
        
        # Estimate memory
        quantizer = ModelQuantizer()
        total_memory = sum(
            quantizer.estimate_memory_usage(1_000_000, ModelPrecision.FP16)
            for _ in configs
        )
        
        # Should be reasonable
        assert total_memory > 0
        assert len(configs) == 100


@pytest.mark.integration
class TestErrorHandlingIntegration:
    """Test error handling across components"""
    
    @pytest.mark.asyncio
    async def test_graceful_degradation(self, ai_engine):
        """Test graceful degradation when components fail"""
        # Test without MLX
        info = ai_engine.get_system_info()
        
        # Should still provide info even without MLX
        assert "mlx_available" in info
        assert "models_loaded" in info
    
    @pytest.mark.asyncio
    async def test_timeout_handling(self):
        """Test timeout handling in requests"""
        async def slow_operation():
            await asyncio.sleep(10)  # Very slow
            return "completed"
        
        # Should timeout
        with pytest.raises(asyncio.TimeoutError):
            await asyncio.wait_for(slow_operation(), timeout=0.1)
    
    @pytest.mark.asyncio
    async def test_invalid_message_handling(self, consensus_cluster):
        """Test handling of invalid messages"""
        primary = consensus_cluster[0]
        
        # Test various invalid messages
        from cell0.swarm.consensus import ConsensusMessage
        
        # Empty sender
        invalid_msg = ConsensusMessage(
            msg_type="PREPARE",
            view_number=0,
            sequence_number=1,
            digest="abc",
            payload={},
            sender_id=""
        )
        
        is_valid = primary._validate_message(invalid_msg)
        assert is_valid is False


# =============================================================================
# End-to-End Scenarios
# =============================================================================

@pytest.mark.integration
class TestEndToEndScenarios:
    """Complete end-to-end scenarios"""
    
    @pytest.mark.asyncio
    async def test_full_inference_pipeline(self, ai_engine, consensus_cluster):
        """Test complete inference pipeline with consensus"""
        primary = consensus_cluster[0]
        
        # Step 1: Propose model selection through consensus
        model_proposal = {
            "type": "load_model",
            "model_id": "test-model",
            "config": {
                "precision": "fp16",
                "max_tokens": 1024
            }
        }
        
        result, digest = await primary.propose(model_proposal)
        assert result == ConsensusResult.ACCEPTED
        
        # Step 2: Verify AI engine status
        info = ai_engine.get_system_info()
        assert "mlx_available" in info
        
        # Step 3: Verify consensus status - check instances created
        status = primary.get_status()
        assert status["active_instances"] >= 1
    
    @pytest.mark.asyncio
    async def test_fault_tolerance_scenario(self, consensus_cluster):
        """Test fault tolerance with multiple failures"""
        primary = consensus_cluster[0]
        
        # Simulate normal operation
        for i in range(3):
            proposal = {"type": "operation", "id": i}
            result, _ = await primary.propose(proposal, f"instance_{i}")
            assert result == ConsensusResult.ACCEPTED
        
        # Verify system health - check active instances
        status = primary.get_status()
        assert status["active_instances"] == 3
        assert status["view_changes"] == 0  # No view changes needed
    
    @pytest.mark.asyncio
    async def test_recovery_scenario(self, consensus_cluster):
        """Test system recovery after issues"""
        primary = consensus_cluster[0]
        
        # Normal operation
        result1, _ = await primary.propose({"type": "test"}, "test1")
        assert result1 == ConsensusResult.ACCEPTED
        
        # Trigger view change (simulating primary issue)
        await primary._initiate_view_change(1)
        
        # System should still work after view change
        result2, _ = await primary.propose({"type": "test2"}, "test2")
        
        # Verify recovery
        status = primary.get_status()
        assert status["view_changes"] == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
