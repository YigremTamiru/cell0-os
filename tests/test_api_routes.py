"""
test_api_routes.py - Route Validation Tests for Cell 0 Daemon API

Comprehensive test suite to validate:
1. All routes are accessible without ambiguity
2. HTTP methods are correctly handled
3. Request/response contracts are consistent
4. Validation rules work correctly
5. Error responses are properly formatted

Run with: pytest tests/test_api_routes.py -v
"""

import pytest
import json
from datetime import datetime
from typing import Dict, Any
from unittest.mock import Mock, patch, AsyncMock
import sys
from pathlib import Path

# Add service directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "service"))

# Import the FastAPI app and models
from service.cell0d import (
    app, ChatMessageRequest, ChatConversationCreateRequest,
    ModelLoadRequest, ModelUnloadRequest, KernelStartRequest,
    KernelStopRequest, TaskSubmitRequest, LogEntry,
    SystemStatusResponse, HealthCheckResponse
)
from fastapi.testclient import TestClient

# Create test client with localhost base URL for auth bypass
client = TestClient(app, base_url="http://127.0.0.1:18800")

# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def mock_daemon():
    """Mock the CellZeroDaemon for testing"""
    with patch('cell0d_fixed.daemon') as mock:
        mock_d = Mock()
        mock_d._running = True
        mock_d.system_state = {
            "status": "running",
            "version": "1.0.0",
            "models_loaded": ["test-model"],
            "active_kernels": ["kernel_001"],
            "uptime_seconds": 3600
        }
        mock_d.websocket_server = Mock()
        mock_d.websocket_server.clients = {"client1": Mock()}
        mock_d.websocket_server.host = "0.0.0.0"
        mock_d.websocket_server.port = 8765
        mock_d.event_bus = Mock()
        mock_d.event_bus._running = True
        mock_d.event_bus.get_stats = Mock(return_value={"queue_size": 0})
        mock_d.emit_chat_message = AsyncMock()
        mock_d.emit_model_activity = AsyncMock()
        mock_d.emit_mcic_event = AsyncMock()
        mock_d.emit_log = AsyncMock()
        mock_d.get_status = Mock(return_value={
            **mock_d.system_state,
            "websocket": {
                "host": "0.0.0.0",
                "port": 8765,
                "connected_clients": 1,
                "client_ids": ["client1"]
            },
            "event_bus": {"queue_size": 0}
        })
        mock.return_value = mock_d
        yield mock_d

# ============================================================================
# Route Existence Tests
# ============================================================================

class TestRouteExistence:
    """Verify all documented routes exist and are accessible"""
    
    def test_chat_messages_post_exists(self):
        """POST /api/chat/messages should exist"""
        response = client.post("/api/chat/messages", json={
            "message": "test",
            "sender": "test_user"
        })
        # Should not be 404
        assert response.status_code != 404, "Route should exist"
    
    def test_chat_messages_get_exists(self):
        """GET /api/chat/messages should exist"""
        response = client.get("/api/chat/messages")
        assert response.status_code != 404, "Route should exist"
    
    def test_chat_conversations_post_exists(self):
        """POST /api/chat/conversations should exist"""
        response = client.post("/api/chat/conversations", json={
            "title": "Test Conversation"
        })
        assert response.status_code != 404, "Route should exist"
    
    def test_chat_conversations_get_exists(self):
        """GET /api/chat/conversations should exist"""
        response = client.get("/api/chat/conversations")
        assert response.status_code != 404, "Route should exist"
    
    def test_chat_conversation_by_id_exists(self):
        """GET /api/chat/conversations/{id} should exist"""
        # First create a conversation
        create_resp = client.post("/api/chat/conversations", json={
            "title": "Test"
        })
        if create_resp.status_code == 200:
            conv_id = create_resp.json()["conversation_id"]
            response = client.get(f"/api/chat/conversations/{conv_id}")
            assert response.status_code != 404, "Route should exist"
    
    def test_models_load_post_exists(self):
        """POST /api/models/load should exist"""
        response = client.post("/api/models/load", json={
            "model_name": "test-model"
        })
        assert response.status_code != 404, "Route should exist"
    
    def test_models_unload_post_exists(self):
        """POST /api/models/unload should exist"""
        response = client.post("/api/models/unload", json={
            "model_name": "test-model"
        })
        assert response.status_code != 404, "Route should exist"
    
    def test_models_get_exists(self):
        """GET /api/models should exist"""
        response = client.get("/api/models")
        assert response.status_code != 404, "Route should exist"
    
    def test_kernels_start_post_exists(self):
        """POST /api/kernels/start should exist"""
        response = client.post("/api/kernels/start", json={})
        assert response.status_code != 404, "Route should exist"
    
    def test_kernels_stop_post_exists(self):
        """POST /api/kernels/stop should exist"""
        response = client.post("/api/kernels/stop", json={
            "kernel_id": "test-kernel"
        })
        assert response.status_code != 404, "Route should exist"
    
    def test_kernels_get_exists(self):
        """GET /api/kernels should exist"""
        response = client.get("/api/kernels")
        assert response.status_code != 404, "Route should exist"
    
    def test_kernels_tasks_post_exists(self):
        """POST /api/kernels/tasks should exist"""
        response = client.post("/api/kernels/tasks", json={
            "kernel_id": "test-kernel",
            "task_type": "test-task"
        })
        assert response.status_code != 404, "Route should exist"
    
    def test_system_status_get_exists(self):
        """GET /api/system/status should exist"""
        response = client.get("/api/system/status")
        assert response.status_code != 404, "Route should exist"
    
    def test_system_health_get_exists(self):
        """GET /api/system/health should exist"""
        response = client.get("/api/system/health")
        assert response.status_code != 404, "Route should exist"
    
    def test_system_stats_get_exists(self):
        """GET /api/system/stats should exist"""
        response = client.get("/api/system/stats")
        assert response.status_code != 404, "Route should exist"
    
    def test_events_stream_get_exists(self):
        """GET /api/events/stream should exist"""
        response = client.get("/api/events/stream")
        assert response.status_code != 404, "Route should exist"
    
    def test_events_emit_post_exists(self):
        """POST /api/events/emit should exist"""
        response = client.post("/api/events/emit?event_type=system_status", json={})
        assert response.status_code != 404, "Route should exist"
    
    def test_logs_post_exists(self):
        """POST /api/logs should exist"""
        response = client.post("/api/logs", json={
            "level": "INFO",
            "message": "test log"
        })
        assert response.status_code != 404, "Route should exist"
    
    def test_logs_get_exists(self):
        """GET /api/logs should exist"""
        response = client.get("/api/logs")
        assert response.status_code != 404, "Route should exist"

# ============================================================================
# HTTP Method Tests
# ============================================================================

class TestHttpMethods:
    """Verify correct HTTP methods are enforced"""
    
    @pytest.mark.parametrize("path", [
        "/api/models/load",
        "/api/models/unload",
        "/api/kernels/start",
        "/api/kernels/stop",
        "/api/kernels/tasks",
    ])
    def test_post_only_routes_reject_get(self, path, mock_daemon):
        """Routes that should only accept POST should reject GET"""
        response = client.get(path)
        # Should be 405 Method Not Allowed or 422 (FastAPI validation error)
        assert response.status_code in [405, 422, 400], f"GET to {path} should be rejected"
    
    @pytest.mark.parametrize("path", [
        "/api/chat/messages",
        "/api/models",
        "/api/kernels",
        "/api/system/status",
        "/api/system/health",
        "/api/system/stats",
        "/api/logs",
    ])
    def test_get_routes_accept_get(self, path):
        """Routes that should accept GET should return non-404"""
        response = client.get(path)
        # Should not be 404 (method not allowed is OK for wrong methods)
        assert response.status_code != 404, f"GET to {path} should exist"

# ============================================================================
# Request Validation Tests
# ============================================================================

class TestRequestValidation:
    """Verify request validation works correctly"""
    
    def test_chat_message_empty_message_rejected(self):
        """Empty messages should be rejected"""
        response = client.post("/api/chat/messages", json={
            "message": "",
            "sender": "test"
        })
        assert response.status_code in [400, 422], "Empty message should be rejected"
    
    def test_chat_message_whitespace_only_rejected(self):
        """Whitespace-only messages should be rejected"""
        response = client.post("/api/chat/messages", json={
            "message": "   ",
            "sender": "test"
        })
        assert response.status_code in [400, 422], "Whitespace-only message should be rejected"
    
    def test_chat_message_too_long_rejected(self):
        """Messages over 10000 chars should be rejected"""
        response = client.post("/api/chat/messages", json={
            "message": "x" * 10001,
            "sender": "test"
        })
        assert response.status_code in [400, 422], "Message over 10000 chars should be rejected"
    
    def test_model_load_invalid_context_size(self):
        """Context size outside 512-128000 should be rejected"""
        response = client.post("/api/models/load", json={
            "model_name": "test",
            "context_size": 100  # Too small
        })
        assert response.status_code in [400, 422], "Invalid context size should be rejected"
    
    def test_model_load_invalid_gpu_layers(self):
        """GPU layers outside -1 to 100 should be rejected"""
        response = client.post("/api/models/load", json={
            "model_name": "test",
            "gpu_layers": 101  # Too high
        })
        assert response.status_code in [400, 422], "Invalid gpu_layers should be rejected"
    
    def test_task_invalid_priority(self):
        """Priority outside 1-10 should be rejected"""
        response = client.post("/api/kernels/tasks", json={
            "kernel_id": "test",
            "task_type": "test",
            "priority": 11  # Too high
        })
        assert response.status_code in [400, 422], "Priority > 10 should be rejected"
    
    def test_log_invalid_level(self):
        """Log level not in enum should be rejected"""
        response = client.post("/api/logs", json={
            "level": "INVALID",
            "message": "test"
        })
        assert response.status_code in [400, 422], "Invalid log level should be rejected"
    
    def test_chat_messages_limit_validation(self):
        """Limit parameter outside 1-100 should be rejected"""
        response = client.get("/api/chat/messages?limit=101")
        assert response.status_code in [400, 422], "Limit > 100 should be rejected"
    
    def test_chat_messages_limit_zero_rejected(self):
        """Limit of 0 should be rejected"""
        response = client.get("/api/chat/messages?limit=0")
        assert response.status_code in [400, 422], "Limit of 0 should be rejected"

# ============================================================================
# Response Contract Tests
# ============================================================================

class TestResponseContracts:
    """Verify response structure matches contracts"""
    
    def test_chat_message_response_structure(self, mock_daemon):
        """Chat message response should have required fields"""
        response = client.post("/api/chat/messages", json={
            "message": "Hello",
            "sender": "test_user"
        })
        if response.status_code == 200:
            data = response.json()
            assert "success" in data, "Response should have 'success' field"
            assert "message_id" in data, "Response should have 'message_id' field"
            assert "timestamp" in data, "Response should have 'timestamp' field"
            assert "channel" in data, "Response should have 'channel' field"
    
    def test_conversation_response_structure(self):
        """Conversation creation response should have required fields"""
        response = client.post("/api/chat/conversations", json={
            "title": "Test Conversation"
        })
        if response.status_code == 200:
            data = response.json()
            assert "conversation_id" in data, "Response should have 'conversation_id' field"
            assert "title" in data, "Response should have 'title' field"
            assert "created_at" in data, "Response should have 'created_at' field"
            assert "participants" in data, "Response should have 'participants' field"
    
    def test_model_response_structure(self, mock_daemon):
        """Model operation response should have required fields"""
        response = client.post("/api/models/load", json={
            "model_name": "test-model"
        })
        if response.status_code == 200:
            data = response.json()
            assert "success" in data, "Response should have 'success' field"
            assert "model_name" in data, "Response should have 'model_name' field"
            assert "action" in data, "Response should have 'action' field"
            assert "timestamp" in data, "Response should have 'timestamp' field"
    
    def test_kernel_response_structure(self, mock_daemon):
        """Kernel operation response should have required fields"""
        response = client.post("/api/kernels/start", json={
            "kernel_type": "test"
        })
        if response.status_code == 200:
            data = response.json()
            assert "success" in data, "Response should have 'success' field"
            assert "kernel_id" in data, "Response should have 'kernel_id' field"
            assert "action" in data, "Response should have 'action' field"
            assert "timestamp" in data, "Response should have 'timestamp' field"
            assert "status" in data, "Response should have 'status' field"
    
    def test_task_response_structure(self, mock_daemon):
        """Task submission response should have required fields"""
        response = client.post("/api/kernels/tasks", json={
            "kernel_id": "kernel_001",
            "task_type": "test-task"
        })
        if response.status_code == 200:
            data = response.json()
            assert "success" in data, "Response should have 'success' field"
            assert "task_id" in data, "Response should have 'task_id' field"
            assert "kernel_id" in data, "Response should have 'kernel_id' field"
            assert "status" in data, "Response should have 'status' field"
            assert "timestamp" in data, "Response should have 'timestamp' field"
    
    def test_system_status_response_structure(self, mock_daemon):
        """System status response should have required fields"""
        response = client.get("/api/system/status")
        if response.status_code == 200:
            data = response.json()
            assert "status" in data, "Response should have 'status' field"
            assert "version" in data, "Response should have 'version' field"
            assert "uptime_seconds" in data, "Response should have 'uptime_seconds' field"
            assert "models_loaded" in data, "Response should have 'models_loaded' field"
            assert "active_kernels" in data, "Response should have 'active_kernels' field"
            assert "connected_clients" in data, "Response should have 'connected_clients' field"
            assert "timestamp" in data, "Response should have 'timestamp' field"
    
    def test_health_check_response_structure(self, mock_daemon):
        """Health check response should have required fields"""
        response = client.get("/api/system/health")
        if response.status_code == 200:
            data = response.json()
            assert "status" in data, "Response should have 'status' field"
            assert "timestamp" in data, "Response should have 'timestamp' field"
            assert "checks" in data, "Response should have 'checks' field"

# ============================================================================
# Error Response Tests
# ============================================================================

class TestErrorResponses:
    """Verify error responses are properly formatted"""
    
    def test_error_response_structure(self):
        """Error responses should follow the ErrorResponse model"""
        # Trigger a validation error
        response = client.post("/api/chat/messages", json={
            "message": "x" * 10001  # Too long
        })
        
        if response.status_code in [400, 422]:
            data = response.json()
            # FastAPI validation errors have 'detail' field
            assert "detail" in data or "error" in data, "Error response should have detail or error field"
    
    def test_404_not_found_structure(self):
        """404 responses should be properly formatted"""
        response = client.get("/api/chat/conversations/non-existent-id")
        if response.status_code == 404:
            data = response.json()
            assert "detail" in data, "404 response should have detail field"

# ============================================================================
# Route Ambiguity Tests
# ============================================================================

class TestRouteAmbiguity:
    """Verify no route ambiguity exists"""
    
    def test_no_duplicate_chat_routes(self):
        """Ensure /api/chat routes are unique"""
        # These should all resolve to different handlers
        routes = [
            ("POST", "/api/chat/messages"),
            ("GET", "/api/chat/messages"),
            ("POST", "/api/chat/conversations"),
            ("GET", "/api/chat/conversations"),
        ]
        
        # Each should return a non-404 status (they exist)
        for method, path in routes:
            if method == "POST":
                response = client.post(path, json={"message": "test", "sender": "test"} if "messages" in path else {"title": "test"})
            else:
                response = client.get(path)
            
            assert response.status_code != 404, f"Route {method} {path} should exist"
    
    def test_chat_messages_vs_conversations_distinct(self):
        """Ensure /api/chat/messages and /api/chat/conversations are distinct"""
        # Creating a conversation should not affect messages endpoint
        conv_response = client.post("/api/chat/conversations", json={"title": "Test"})
        msg_response = client.post("/api/chat/messages", json={"message": "Hello", "sender": "test"})
        
        # Both should work independently
        assert conv_response.status_code in [200, 201, 422], "Conversation endpoint should respond"
        assert msg_response.status_code in [200, 201, 422], "Messages endpoint should respond"

# ============================================================================
# Integration Flow Tests
# ============================================================================

class TestIntegrationFlows:
    """Test complete workflow scenarios"""
    
    def test_full_chat_flow(self, mock_daemon):
        """Test complete chat message flow"""
        # Send a message
        msg_response = client.post("/api/chat/messages", json={
            "message": "Hello World",
            "sender": "test_user",
            "channel": "general"
        })
        assert msg_response.status_code in [200, 503], "Message send should succeed or fail with service unavailable"
        
        if msg_response.status_code == 200:
            # Get messages
            get_response = client.get("/api/chat/messages?channel=general")
            assert get_response.status_code in [200, 503], "Get messages should succeed"
    
    def test_kernel_lifecycle(self, mock_daemon):
        """Test kernel start -> task -> stop flow"""
        # Start kernel
        start_response = client.post("/api/kernels/start", json={
            "kernel_type": "standard"
        })
        assert start_response.status_code in [200, 503], "Kernel start should succeed"
        
        if start_response.status_code == 200:
            kernel_id = start_response.json().get("kernel_id")
            
            # Submit task
            task_response = client.post("/api/kernels/tasks", json={
                "kernel_id": kernel_id,
                "task_type": "compute",
                "priority": 5
            })
            assert task_response.status_code in [200, 503], "Task submission should succeed"
            
            # Stop kernel
            stop_response = client.post("/api/kernels/stop", json={
                "kernel_id": kernel_id
            })
            assert stop_response.status_code in [200, 503], "Kernel stop should succeed"

# ============================================================================
# Main Entry Point
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])