"""
Tests for Cell 0 OS Monitoring Module
"""

import pytest
import asyncio
import time
from pathlib import Path

# Test imports
from engine.monitoring import (
    # Metrics
    INFERENCE_REQUESTS,
    API_REQUESTS,
    AGENTS_ACTIVE,
    record_inference_metrics,
    update_agent_count,
    set_build_info,
    timer,
    
    # Logging
    set_trace_id,
    get_trace_id,
    clear_trace_id,
    trace_context,
    JSONFormatter,
    
    # Health
    HealthStatus,
    ComponentHealth,
    HealthReport,
    health_registry,
    check_disk_space,
    check_memory_usage,
)


class TestMetrics:
    """Test Prometheus metrics collection."""
    
    def test_metrics_import(self):
        """Test that metrics can be imported."""
        assert INFERENCE_REQUESTS is not None
        assert API_REQUESTS is not None
        assert AGENTS_ACTIVE is not None
    
    def test_update_agent_count(self):
        """Test updating agent count."""
        update_agent_count("test", 5)
        # Metric should be set (no exception raised)
    
    def test_record_inference_metrics(self):
        """Test recording inference metrics."""
        record_inference_metrics(
            model="test-model",
            status="success",
            latency=1.5,
            input_tokens=10,
            output_tokens=20
        )
        # Metrics should be recorded (no exception raised)
    
    @pytest.mark.asyncio
    async def test_timer_context_manager(self):
        """Test timer context manager."""
        from engine.monitoring.metrics import INFERENCE_LATENCY
        
        with timer(INFERENCE_LATENCY, {"model": "test"}):
            await asyncio.sleep(0.01)
        
        # Should complete without exception


class TestLogging:
    """Test structured logging."""
    
    def test_trace_id_management(self):
        """Test trace ID context management."""
        # Initially empty
        assert get_trace_id() == ""
        
        # Set trace ID
        tid = set_trace_id("test-trace-123")
        assert tid == "test-trace-123"
        assert get_trace_id() == "test-trace-123"
        
        # Clear trace ID
        clear_trace_id()
        assert get_trace_id() == ""
    
    def test_trace_context(self):
        """Test trace context manager."""
        with trace_context("my-trace"):
            assert get_trace_id() == "my-trace"
        
        # Should be cleared after context
        assert get_trace_id() == ""
    
    def test_json_formatter(self):
        """Test JSON log formatter."""
        import logging
        
        formatter = JSONFormatter(cell0_version="1.0.0")
        
        record = logging.LogRecord(
            name="test.logger",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test message",
            args=(),
            exc_info=None,
        )
        
        output = formatter.format(record)
        
        # Should be valid JSON
        import json
        data = json.loads(output)
        
        assert data["level"] == "INFO"
        assert data["logger"] == "test.logger"
        assert data["message"] == "Test message"
        assert "cell0" in data


class TestHealthChecks:
    """Test health check functionality."""
    
    def test_health_status_enum(self):
        """Test health status values."""
        assert HealthStatus.HEALTHY.value == "healthy"
        assert HealthStatus.DEGRADED.value == "degraded"
        assert HealthStatus.UNHEALTHY.value == "unhealthy"
    
    def test_component_health_creation(self):
        """Test creating component health."""
        health = ComponentHealth(
            name="test_component",
            status=HealthStatus.HEALTHY,
            message="All good",
            latency_ms=100.0,
        )
        
        assert health.name == "test_component"
        assert health.status == HealthStatus.HEALTHY
        assert health.message == "All good"
        
        # Test serialization
        data = health.to_dict()
        assert data["name"] == "test_component"
        assert data["status"] == "healthy"
    
    def test_health_report_http_status(self):
        """Test HTTP status code mapping."""
        report = HealthReport(
            status=HealthStatus.HEALTHY,
            timestamp="2026-01-01T00:00:00Z",
            version="1.0.0",
            uptime_seconds=100.0,
            components=[],
        )
        assert report.http_status_code == 200
        
        report.status = HealthStatus.DEGRADED
        assert report.http_status_code == 200
        
        report.status = HealthStatus.UNHEALTHY
        assert report.http_status_code == 503
    
    @pytest.mark.asyncio
    async def test_check_disk_space(self):
        """Test disk space check."""
        result = await check_disk_space("/")
        
        assert isinstance(result, ComponentHealth)
        assert result.name == "disk"
        assert result.status in [HealthStatus.HEALTHY, HealthStatus.DEGRADED, HealthStatus.UNHEALTHY]
        assert "percent_used" in result.metadata
    
    @pytest.mark.asyncio
    async def test_check_memory_usage(self):
        """Test memory usage check."""
        result = await check_memory_usage()
        
        assert isinstance(result, ComponentHealth)
        assert result.name == "memory"
        assert result.status in [HealthStatus.HEALTHY, HealthStatus.DEGRADED, HealthStatus.UNHEALTHY]


class TestHealthRegistry:
    """Test health check registry."""
    
    def test_registry_singleton(self):
        """Test that health registry exists."""
        assert health_registry is not None
    
    @pytest.mark.asyncio
    async def test_run_all_checks(self):
        """Test running all health checks."""
        report = await health_registry.run_all_checks()
        
        assert isinstance(report, HealthReport)
        assert report.version is not None
        assert len(report.components) > 0
        assert report.status in [HealthStatus.HEALTHY, HealthStatus.DEGRADED, HealthStatus.UNHEALTHY]


class TestIntegration:
    """Integration tests."""
    
    @pytest.mark.asyncio
    async def test_metrics_endpoint(self):
        """Test metrics HTTP handler."""
        from engine.monitoring import metrics_handler
        
        body, content_type, status = await metrics_handler(None)
        
        assert status == 200
        assert content_type is not None
        assert b"#" in body or b"cell0" in body
    
    @pytest.mark.asyncio
    async def test_health_handlers(self):
        """Test health check handlers."""
        from engine.monitoring import (
            basic_health_handler,
            deep_health_handler,
        )
        
        # Basic health
        body, status, headers = await basic_health_handler(None)
        assert status == 200
        assert body["status"] == "healthy"
        
        # Deep health
        body, status, headers = await deep_health_handler(None)
        assert status in [200, 503]
        assert "components" in body


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
