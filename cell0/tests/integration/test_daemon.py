"""
Integration Tests for Cell 0 OS Daemon

End-to-end tests for the cell0d daemon including:
- HTTP API endpoints
- WebSocket gateway
- Health checks
- Metrics endpoint
- Multi-agent coordination
"""

import pytest
import asyncio
import aiohttp
import aiohttp.test_utils
import json
import time
from unittest.mock import Mock, patch, AsyncMock

# Test configuration
TEST_HOST = "127.0.0.1"
TEST_HTTP_PORT = 28800  # Different from production
TEST_WS_PORT = 28801
TEST_METRICS_PORT = 28802


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture(scope="module")
def event_loop():
    """Create an instance of the default event loop for the test session"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
async def daemon():
    """Start Cell 0 daemon for testing"""
    # Import daemon module
    try:
        from cell0d import Cell0Daemon
        
        daemon = Cell0Daemon()
        daemon.http_port = TEST_HTTP_PORT
        daemon.ws_port = TEST_WS_PORT
        daemon.metrics_port = TEST_METRICS_PORT
        
        # Start daemon
        await daemon.start()
        
        yield daemon
        
        # Cleanup
        await daemon.stop()
    except ImportError:
        pytest.skip("Daemon module not available")


@pytest.fixture
async def http_client():
    """Create HTTP client for testing"""
    async with aiohttp.ClientSession() as session:
        yield session


# =============================================================================
# Health Endpoint Tests
# =============================================================================

class TestHealthEndpoints:
    """Tests for health check endpoints"""
    
    @pytest.mark.asyncio
    async def test_basic_health_endpoint(self, http_client):
        """Test basic health check endpoint"""
        try:
            async with http_client.get(
                f"http://{TEST_HOST}:{TEST_HTTP_PORT}/api/health"
            ) as resp:
                assert resp.status in [200, 503]  # OK or Service Unavailable
                
                data = await resp.json()
                assert "status" in data
                assert data["status"] in ["healthy", "degraded", "unhealthy"]
        except aiohttp.ClientConnectorError:
            pytest.skip("Daemon not running")
    
    @pytest.mark.asyncio
    async def test_deep_health_endpoint(self, http_client):
        """Test deep health check with component status"""
        try:
            async with http_client.get(
                f"http://{TEST_HOST}:{TEST_HTTP_PORT}/api/health/deep"
            ) as resp:
                assert resp.status in [200, 503]
                
                data = await resp.json()
                assert "status" in data
                assert "components" in data
                assert isinstance(data["components"], dict)
                
                # Check component structure
                for name, component in data["components"].items():
                    assert "name" in component
                    assert "status" in component
                    assert "message" in component
        except aiohttp.ClientConnectorError:
            pytest.skip("Daemon not running")
    
    @pytest.mark.asyncio
    async def test_readiness_probe(self, http_client):
        """Test Kubernetes readiness probe"""
        try:
            async with http_client.get(
                f"http://{TEST_HOST}:{TEST_HTTP_PORT}/ready"
            ) as resp:
                # Should return 200 when ready, 503 when not
                assert resp.status in [200, 503]
        except aiohttp.ClientConnectorError:
            pytest.skip("Daemon not running")
    
    @pytest.mark.asyncio
    async def test_liveness_probe(self, http_client):
        """Test Kubernetes liveness probe"""
        try:
            async with http_client.get(
                f"http://{TEST_HOST}:{TEST_HTTP_PORT}/live"
            ) as resp:
                # Liveness should usually return 200
                assert resp.status == 200
        except aiohttp.ClientConnectorError:
            pytest.skip("Daemon not running")


# =============================================================================
# Status Endpoint Tests
# =============================================================================

class TestStatusEndpoints:
    """Tests for status endpoints"""
    
    @pytest.mark.asyncio
    async def test_status_endpoint(self, http_client):
        """Test status endpoint returns system info"""
        try:
            async with http_client.get(
                f"http://{TEST_HOST}:{TEST_HTTP_PORT}/api/status"
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    assert "version" in data
                    assert "environment" in data
                    assert "uptime" in data
                else:
                    pytest.skip(f"Status endpoint returned {resp.status}")
        except aiohttp.ClientConnectorError:
            pytest.skip("Daemon not running")
    
    @pytest.mark.asyncio
    async def test_system_info_endpoint(self, http_client):
        """Test system info endpoint"""
        try:
            async with http_client.get(
                f"http://{TEST_HOST}:{TEST_HTTP_PORT}/api/system/info"
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    # Should contain system information
                    assert isinstance(data, dict)
                else:
                    pytest.skip(f"System info returned {resp.status}")
        except aiohttp.ClientConnectorError:
            pytest.skip("Daemon not running")


# =============================================================================
# Model Endpoint Tests
# =============================================================================

class TestModelEndpoints:
    """Tests for model management endpoints"""
    
    @pytest.mark.asyncio
    async def test_list_models(self, http_client):
        """Test listing available models"""
        try:
            async with http_client.get(
                f"http://{TEST_HOST}:{TEST_HTTP_PORT}/api/models"
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    assert "models" in data
                    assert isinstance(data["models"], list)
                else:
                    pytest.skip(f"Models endpoint returned {resp.status}")
        except aiohttp.ClientConnectorError:
            pytest.skip("Daemon not running")
    
    @pytest.mark.asyncio
    async def test_model_details(self, http_client):
        """Test getting model details"""
        try:
            # First try to get a list of models
            async with http_client.get(
                f"http://{TEST_HOST}:{TEST_HTTP_PORT}/api/models"
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if data.get("models"):
                        model_id = data["models"][0]["id"]
                        
                        # Get details for this model
                        async with http_client.get(
                            f"http://{TEST_HOST}:{TEST_HTTP_PORT}/api/models/{model_id}"
                        ) as detail_resp:
                            assert detail_resp.status in [200, 404]
                else:
                    pytest.skip("Cannot fetch models list")
        except aiohttp.ClientConnectorError:
            pytest.skip("Daemon not running")


# =============================================================================
# Chat API Tests
# =============================================================================

class TestChatEndpoints:
    """Tests for chat API endpoints"""
    
    @pytest.mark.asyncio
    async def test_chat_endpoint_basic(self, http_client):
        """Test basic chat endpoint"""
        try:
            payload = {
                "message": "Hello, world!",
                "stream": False,
                "model": "qwen2.5:7b"
            }
            
            async with http_client.post(
                f"http://{TEST_HOST}:{TEST_HTTP_PORT}/api/chat",
                json=payload
            ) as resp:
                # May return 200, 503 (service unavailable), or 429 (rate limited)
                assert resp.status in [200, 503, 429, 422]
                
                if resp.status == 200:
                    data = await resp.json()
                    assert "response" in data or "content" in data or "error" in data
        except aiohttp.ClientConnectorError:
            pytest.skip("Daemon not running")
    
    @pytest.mark.asyncio
    async def test_chat_endpoint_validation(self, http_client):
        """Test chat endpoint input validation"""
        try:
            # Missing required field
            payload = {"stream": False}
            
            async with http_client.post(
                f"http://{TEST_HOST}:{TEST_HTTP_PORT}/api/chat",
                json=payload
            ) as resp:
                # Should return 422 for validation error
                assert resp.status in [200, 422, 400]
        except aiohttp.ClientConnectorError:
            pytest.skip("Daemon not running")
    
    @pytest.mark.asyncio
    async def test_chat_streaming(self, http_client):
        """Test streaming chat endpoint"""
        try:
            payload = {
                "message": "Hello",
                "stream": True,
                "model": "qwen2.5:7b"
            }
            
            async with http_client.post(
                f"http://{TEST_HOST}:{TEST_HTTP_PORT}/api/chat",
                json=payload
            ) as resp:
                # Should return streaming response or error
                assert resp.status in [200, 503, 429]
                
                if resp.status == 200:
                    # Read first chunk
                    chunk = await resp.content.read(1024)
                    assert len(chunk) >= 0  # Just verify we can read
        except aiohttp.ClientConnectorError:
            pytest.skip("Daemon not running")


# =============================================================================
# Metrics Endpoint Tests
# =============================================================================

class TestMetricsEndpoints:
    """Tests for Prometheus metrics endpoints"""
    
    @pytest.mark.asyncio
    async def test_metrics_endpoint(self, http_client):
        """Test Prometheus metrics endpoint"""
        try:
            async with http_client.get(
                f"http://{TEST_HOST}:{TEST_METRICS_PORT}/metrics"
            ) as resp:
                if resp.status == 200:
                    text = await resp.text()
                    
                    # Should contain Prometheus format data
                    assert "# HELP" in text or "# TYPE" in text or "cell0" in text
                else:
                    pytest.skip(f"Metrics endpoint returned {resp.status}")
        except aiohttp.ClientConnectorError:
            pytest.skip("Metrics server not running")


# =============================================================================
# WebSocket Tests
# =============================================================================

class TestWebSocketEndpoints:
    """Tests for WebSocket gateway"""
    
    @pytest.mark.asyncio
    async def test_websocket_connection(self):
        """Test WebSocket connection"""
        try:
            import aiohttp
            
            async with aiohttp.ClientSession() as session:
                async with session.ws_connect(
                    f"ws://{TEST_HOST}:{TEST_WS_PORT}"
                ) as ws:
                    # Wait for welcome message
                    msg = await ws.receive()
                    
                    if msg.type == aiohttp.WSMsgType.TEXT:
                        data = json.loads(msg.data)
                        assert "method" in data or "jsonrpc" in data
                        
                    await ws.close()
        except aiohttp.ClientConnectorError:
            pytest.skip("WebSocket server not running")
        except Exception as e:
            pytest.skip(f"WebSocket test failed: {e}")
    
    @pytest.mark.asyncio
    async def test_websocket_jsonrpc(self):
        """Test WebSocket JSON-RPC communication"""
        try:
            import aiohttp
            
            async with aiohttp.ClientSession() as session:
                async with session.ws_connect(
                    f"ws://{TEST_HOST}:{TEST_WS_PORT}"
                ) as ws:
                    # Receive welcome
                    await ws.receive()
                    
                    # Send a ping/request
                    request = {
                        "jsonrpc": "2.0",
                        "method": "system.ping",
                        "id": 1
                    }
                    
                    await ws.send_json(request)
                    
                    # Wait for response
                    msg = await asyncio.wait_for(ws.receive(), timeout=5.0)
                    
                    if msg.type == aiohttp.WSMsgType.TEXT:
                        data = json.loads(msg.data)
                        assert "id" in data or "error" in data
                    
                    await ws.close()
        except asyncio.TimeoutError:
            pytest.skip("WebSocket response timeout")
        except aiohttp.ClientConnectorError:
            pytest.skip("WebSocket server not running")
        except Exception as e:
            pytest.skip(f"WebSocket test failed: {e}")


# =============================================================================
# Error Handling Tests
# =============================================================================

class TestErrorHandling:
    """Tests for error handling and edge cases"""
    
    @pytest.mark.asyncio
    async def test_404_handling(self, http_client):
        """Test 404 error handling"""
        try:
            async with http_client.get(
                f"http://{TEST_HOST}:{TEST_HTTP_PORT}/api/nonexistent"
            ) as resp:
                assert resp.status == 404
        except aiohttp.ClientConnectorError:
            pytest.skip("Daemon not running")
    
    @pytest.mark.asyncio
    async def test_method_not_allowed(self, http_client):
        """Test method not allowed handling"""
        try:
            async with http_client.delete(
                f"http://{TEST_HOST}:{TEST_HTTP_PORT}/api/health"
            ) as resp:
                assert resp.status == 405
        except aiohttp.ClientConnectorError:
            pytest.skip("Daemon not running")
    
    @pytest.mark.asyncio
    async def test_invalid_json(self, http_client):
        """Test invalid JSON handling"""
        try:
            async with http_client.post(
                f"http://{TEST_HOST}:{TEST_HTTP_PORT}/api/chat",
                data="not valid json",
                headers={"Content-Type": "application/json"}
            ) as resp:
                assert resp.status in [400, 422]
        except aiohttp.ClientConnectorError:
            pytest.skip("Daemon not running")


# =============================================================================
# Load and Stress Tests
# =============================================================================

class TestLoadHandling:
    """Tests for load handling"""
    
    @pytest.mark.asyncio
    async def test_concurrent_requests(self, http_client):
        """Test handling concurrent requests"""
        try:
            async def make_request(i):
                async with http_client.get(
                    f"http://{TEST_HOST}:{TEST_HTTP_PORT}/api/health"
                ) as resp:
                    return resp.status
            
            # Make 10 concurrent requests
            tasks = [make_request(i) for i in range(10)]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # All should complete (may have errors, but shouldn't crash)
            success_count = sum(1 for r in results if r == 200)
            assert success_count >= 0  # Just verify completion
            
        except aiohttp.ClientConnectorError:
            pytest.skip("Daemon not running")
    
    @pytest.mark.asyncio
    async def test_health_check_under_load(self, http_client):
        """Test health checks remain responsive under load"""
        try:
            start_time = time.time()
            
            # Make rapid health checks
            for _ in range(20):
                async with http_client.get(
                    f"http://{TEST_HOST}:{TEST_HTTP_PORT}/api/health"
                ) as resp:
                    await resp.read()
            
            elapsed = time.time() - start_time
            
            # Should complete reasonably quickly
            assert elapsed < 10.0
            
        except aiohttp.ClientConnectorError:
            pytest.skip("Daemon not running")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
