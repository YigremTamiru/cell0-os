"""
Unit Tests for Cell 0 OS Monitoring Module

Tests the health checking, metrics collection, and logging systems.
"""

import pytest
import asyncio
import time
import json
from datetime import datetime
from unittest.mock import Mock, patch, AsyncMock, MagicMock

# Import modules under test
from cell0.cell0.engine.monitoring.health import (
    HealthStatus,
    ComponentHealth,
    HealthReport,
    HealthChecker,
    get_health_checker,
)
from cell0.cell0.engine.monitoring.metrics import (
    Cell0Metrics,
    RequestTimer,
    InferenceTracker,
    get_metrics,
    setup_metrics,
    HAS_PROMETHEUS,
)
from cell0.cell0.engine.monitoring.logging_config import (
    configure_logging,
    get_logger,
)


# =============================================================================
# Health Check Tests
# =============================================================================

class TestHealthStatus:
    """Tests for HealthStatus enum"""
    
    def test_health_status_values(self):
        """Test health status enumeration values"""
        assert HealthStatus.HEALTHY.value == "healthy"
        assert HealthStatus.DEGRADED.value == "degraded"
        assert HealthStatus.UNHEALTHY.value == "unhealthy"
        assert HealthStatus.UNKNOWN.value == "unknown"
    
    def test_health_status_comparison(self):
        """Test health status severity ordering"""
        # Define severity order
        severity = {
            HealthStatus.HEALTHY: 0,
            HealthStatus.UNKNOWN: 1,
            HealthStatus.DEGRADED: 2,
            HealthStatus.UNHEALTHY: 3,
        }
        
        assert severity[HealthStatus.UNHEALTHY] > severity[HealthStatus.DEGRADED]
        assert severity[HealthStatus.DEGRADED] > severity[HealthStatus.HEALTHY]


class TestComponentHealth:
    """Tests for ComponentHealth dataclass"""
    
    def test_component_health_creation(self):
        """Test creating component health instance"""
        health = ComponentHealth(
            name="test_component",
            status=HealthStatus.HEALTHY,
            message="All systems operational",
            latency_ms=15.5,
            metadata={"version": "1.0.0"}
        )
        
        assert health.name == "test_component"
        assert health.status == HealthStatus.HEALTHY
        assert health.message == "All systems operational"
        assert health.latency_ms == 15.5
        assert health.metadata["version"] == "1.0.0"
        assert isinstance(health.timestamp, datetime)
    
    def test_component_health_to_dict(self):
        """Test serialization to dictionary"""
        health = ComponentHealth(
            name="test_component",
            status=HealthStatus.DEGRADED,
            message="High load detected",
            latency_ms=150.0,
            metadata={"cpu_percent": 85.5}
        )
        
        data = health.to_dict()
        
        assert data["name"] == "test_component"
        assert data["status"] == "degraded"
        assert data["message"] == "High load detected"
        assert data["latency_ms"] == 150.0
        assert data["metadata"]["cpu_percent"] == 85.5
        assert "timestamp" in data
    
    def test_component_health_default_values(self):
        """Test default values for optional fields"""
        health = ComponentHealth(
            name="minimal",
            status=HealthStatus.HEALTHY
        )
        
        assert health.message == ""
        assert health.latency_ms == 0.0
        assert health.metadata == {}
        assert isinstance(health.timestamp, datetime)


class TestHealthReport:
    """Tests for HealthReport dataclass"""
    
    def test_health_report_creation(self):
        """Test creating health report"""
        components = {
            "database": ComponentHealth(
                name="database",
                status=HealthStatus.HEALTHY,
                message="Connected"
            ),
            "cache": ComponentHealth(
                name="cache",
                status=HealthStatus.DEGRADED,
                message="Slow responses"
            )
        }
        
        report = HealthReport(
            overall=HealthStatus.DEGRADED,
            components=components
        )
        
        assert report.overall == HealthStatus.DEGRADED
        assert len(report.components) == 2
        assert report.version == "1.2.0"
        assert isinstance(report.timestamp, datetime)
    
    def test_health_report_to_dict(self):
        """Test health report serialization"""
        components = {
            "test": ComponentHealth(
                name="test",
                status=HealthStatus.HEALTHY
            )
        }
        
        report = HealthReport(
            overall=HealthStatus.HEALTHY,
            components=components
        )
        
        data = report.to_dict()
        
        assert data["status"] == "healthy"
        assert data["version"] == "1.2.0"
        assert "timestamp" in data
        assert "components" in data
        assert data["components"]["test"]["name"] == "test"


class TestHealthChecker:
    """Tests for HealthChecker class"""
    
    @pytest.fixture
    def checker(self):
        """Create fresh health checker"""
        return HealthChecker()
    
    @pytest.mark.asyncio
    async def test_register_check(self, checker):
        """Test registering health check functions"""
        async def mock_check():
            return ComponentHealth(
                name="mock",
                status=HealthStatus.HEALTHY
            )
        
        checker.register_check("mock_service", mock_check)
        
        assert "mock_service" in checker.checks
        assert checker.checks["mock_service"] == mock_check
    
    @pytest.mark.asyncio
    async def test_check_all_basic(self, checker):
        """Test running all health checks"""
        # Register a simple check
        async def simple_check():
            return ComponentHealth(
                name="simple",
                status=HealthStatus.HEALTHY,
                message="OK"
            )
        
        checker.register_check("simple", simple_check)
        
        report = await checker.check_all()
        
        assert isinstance(report, HealthReport)
        assert "simple" in report.components
        assert report.components["simple"].status == HealthStatus.HEALTHY
    
    @pytest.mark.asyncio
    async def test_check_all_with_failure(self, checker):
        """Test health check with failing component"""
        async def failing_check():
            raise Exception("Service unreachable")
        
        async def working_check():
            return ComponentHealth(
                name="working",
                status=HealthStatus.HEALTHY
            )
        
        checker.register_check("failing", failing_check)
        checker.register_check("working", working_check)
        
        report = await checker.check_all()
        
        assert report.overall == HealthStatus.UNHEALTHY
        assert report.components["failing"].status == HealthStatus.UNHEALTHY
        assert "Service unreachable" in report.components["failing"].message
        assert report.components["working"].status == HealthStatus.HEALTHY
    
    @pytest.mark.asyncio
    async def test_check_all_timeout(self, checker):
        """Test health check timeout handling"""
        async def slow_check():
            await asyncio.sleep(15)  # Longer than timeout
            return ComponentHealth(name="slow", status=HealthStatus.HEALTHY)
        
        checker.register_check("slow", slow_check)
        
        report = await checker.check_all()
        
        assert report.components["slow"].status == HealthStatus.UNHEALTHY
        assert "timed out" in report.components["slow"].message.lower()
    
    @pytest.mark.asyncio
    async def test_caching_behavior(self, checker):
        """Test that results are cached"""
        call_count = 0
        
        async def counting_check():
            nonlocal call_count
            call_count += 1
            return ComponentHealth(name="counter", status=HealthStatus.HEALTHY)
        
        checker.register_check("counter", counting_check)
        checker._cache_duration = 1  # 1 second cache
        
        # First call
        await checker.check_all()
        assert call_count == 1
        
        # Second call should use cache
        await checker.check_all()
        assert call_count == 1
        
        # Wait for cache to expire
        await asyncio.sleep(1.1)
        
        # Third call should run check again
        await checker.check_all()
        assert call_count == 2
    
    @pytest.mark.asyncio
    async def test_overall_health_calculation(self, checker):
        """Test overall health status calculation"""
        # All healthy
        checker.results = {
            "a": ComponentHealth("a", HealthStatus.HEALTHY),
            "b": ComponentHealth("b", HealthStatus.HEALTHY),
        }
        assert checker._calculate_overall() == HealthStatus.HEALTHY
        
        # One degraded
        checker.results["c"] = ComponentHealth("c", HealthStatus.DEGRADED)
        assert checker._calculate_overall() == HealthStatus.DEGRADED
        
        # One unhealthy (overrides degraded)
        checker.results["d"] = ComponentHealth("d", HealthStatus.UNHEALTHY)
        assert checker._calculate_overall() == HealthStatus.UNHEALTHY
    
    @pytest.mark.asyncio
    async def test_default_checks_exist(self, checker):
        """Test that default health checks are registered"""
        await checker.initialize()
        
        expected_checks = ["ollama", "signal", "disk", "memory", "tpv_store"]
        for check_name in expected_checks:
            assert check_name in checker.checks, f"Missing check: {check_name}"
    
    @pytest.mark.asyncio
    async def test_disk_check(self, checker):
        """Test disk space health check"""
        result = await checker._check_disk()
        
        assert isinstance(result, ComponentHealth)
        assert result.name == "disk"
        assert result.status in [HealthStatus.HEALTHY, HealthStatus.DEGRADED, HealthStatus.UNHEALTHY]
        assert "free" in result.message.lower() or "GB" in result.message
        assert "used_percent" in result.metadata
    
    @pytest.mark.asyncio
    async def test_memory_check(self, checker):
        """Test memory health check"""
        result = await checker._check_memory()
        
        # May be UNKNOWN if psutil not installed
        assert isinstance(result, ComponentHealth)
        assert result.name == "memory"
        assert result.status in list(HealthStatus)
    
    @pytest.mark.asyncio
    async def test_tpv_store_check(self, checker):
        """Test TPV store health check"""
        result = await checker._check_tpv_store()
        
        assert isinstance(result, ComponentHealth)
        assert result.name == "tpv_store"
        assert result.status in [HealthStatus.HEALTHY, HealthStatus.UNKNOWN]


class TestGetHealthChecker:
    """Tests for global health checker instance"""
    
    def test_singleton_pattern(self):
        """Test that get_health_checker returns singleton"""
        checker1 = get_health_checker()
        checker2 = get_health_checker()
        
        assert checker1 is checker2
    
    def test_returns_health_checker(self):
        """Test that function returns HealthChecker instance"""
        checker = get_health_checker()
        
        assert isinstance(checker, HealthChecker)


# =============================================================================
# Metrics Tests
# =============================================================================

class TestCell0Metrics:
    """Tests for Cell0Metrics class"""
    
    @pytest.fixture
    def metrics(self):
        """Create fresh metrics instance"""
        return Cell0Metrics()
    
    def test_metrics_initialization(self, metrics):
        """Test metrics are properly initialized"""
        # System metrics
        assert metrics.system_uptime is not None
        assert metrics.system_memory_usage is not None
        assert metrics.system_cpu_percent is not None
        
        # API metrics
        assert metrics.api_requests_total is not None
        assert metrics.api_request_duration is not None
        
        # Agent metrics
        assert metrics.agents_active is not None
        assert metrics.agents_total is not None
        
        # Inference metrics
        assert metrics.inference_requests is not None
        assert metrics.inference_latency is not None
        
        # COL metrics
        assert metrics.col_events is not None
        assert metrics.col_resonance is not None
    
    def test_info_metric_set(self, metrics):
        """Test info metric contains version info"""
        # Info metric should be set during initialization
        assert metrics.info is not None
    
    @patch('psutil.virtual_memory')
    @patch('psutil.cpu_percent')
    @patch('psutil.disk_usage')
    def test_update_system_metrics(self, mock_disk, mock_cpu, mock_memory, metrics):
        """Test updating system metrics"""
        # Mock psutil responses
        mock_memory.return_value = Mock(
            used=1024**3,
            percent=50.0,
            available=2 * 1024**3,
            total=4 * 1024**3
        )
        mock_cpu.return_value = 25.0
        mock_disk.return_value = Mock(
            used=100 * 1024**3,
            percent=75.0
        )
        
        metrics.update_system_metrics()
        
        # Should complete without error
        mock_memory.assert_called_once()
        mock_cpu.assert_called_once()
        mock_disk.assert_called_once()


class TestRequestTimer:
    """Tests for RequestTimer context manager"""
    
    @pytest.fixture
    def mock_metrics(self):
        """Create mock metrics"""
        metrics = Mock()
        metrics.api_requests_total = Mock()
        metrics.api_requests_total.labels = Mock(return_value=Mock())
        metrics.api_request_duration = Mock()
        metrics.api_request_duration.labels = Mock(return_value=Mock())
        return metrics
    
    def test_timer_records_success(self, mock_metrics):
        """Test timer records successful request"""
        with RequestTimer(mock_metrics, "GET", "/api/test"):
            time.sleep(0.01)
        
        # Verify metrics were recorded
        mock_metrics.api_requests_total.labels.assert_called_with(
            method="GET",
            endpoint="/api/test",
            status="success"
        )
        mock_metrics.api_request_duration.labels.assert_called_with(
            method="GET",
            endpoint="/api/test"
        )
    
    def test_timer_records_error(self, mock_metrics):
        """Test timer records failed request"""
        try:
            with RequestTimer(mock_metrics, "POST", "/api/error"):
                raise ValueError("Test error")
        except ValueError:
            pass
        
        # Verify error was recorded
        mock_metrics.api_requests_total.labels.assert_called_with(
            method="POST",
            endpoint="/api/error",
            status="error"
        )


class TestInferenceTracker:
    """Tests for InferenceTracker context manager"""
    
    @pytest.fixture
    def mock_metrics(self):
        """Create mock metrics"""
        metrics = Mock()
        metrics.inference_requests = Mock()
        metrics.inference_requests.labels = Mock(return_value=Mock())
        metrics.inference_latency = Mock()
        metrics.inference_latency.labels = Mock(return_value=Mock())
        return metrics
    
    def test_tracker_records_success(self, mock_metrics):
        """Test tracker records successful inference"""
        with InferenceTracker(mock_metrics, "llama3.2:3b"):
            time.sleep(0.01)
        
        mock_metrics.inference_requests.labels.assert_called_with(
            model="llama3.2:3b",
            status="success"
        )
        mock_metrics.inference_latency.labels.assert_called_with(
            model="llama3.2:3b"
        )


class TestSetupMetrics:
    """Tests for metrics setup function"""
    
    def test_setup_returns_metrics(self):
        """Test setup returns Cell0Metrics instance"""
        # Note: This may start a server on port 18802
        # In real tests, use a different port or mock
        pass  # Skip to avoid port conflicts in tests
    
    def test_get_metrics_singleton(self):
        """Test get_metrics returns singleton"""
        # Reset global state for test
        import cell0.engine.monitoring.metrics as metrics_module
        original_metrics = metrics_module._metrics
        
        try:
            metrics_module._metrics = None
            
            m1 = get_metrics()
            m2 = get_metrics()
            
            assert m1 is m2
        finally:
            metrics_module._metrics = original_metrics


# =============================================================================
# Logging Tests
# =============================================================================

class TestConfigureLogging:
    """Tests for logging configuration"""
    
    def test_configure_logging_basic(self):
        """Test basic logging configuration"""
        # Should not raise exception
        configure_logging(level="INFO")
    
    def test_configure_logging_json_format(self):
        """Test JSON format logging"""
        configure_logging(level="DEBUG", json_format=True)
        # Should configure JSON formatter
    
    def test_get_logger(self):
        """Test getting logger instance"""
        logger = get_logger("test.module")
        
        assert logger.name == "test.module"


# =============================================================================
# Integration Tests
# =============================================================================

class TestMonitoringIntegration:
    """Integration tests for monitoring module"""
    
    @pytest.mark.asyncio
    async def test_full_health_check_flow(self):
        """Test complete health check flow"""
        checker = HealthChecker()
        await checker.initialize()
        
        report = await checker.check_all()
        
        assert isinstance(report, HealthReport)
        assert report.overall in list(HealthStatus)
        assert len(report.components) > 0
        
        # Verify all components have required fields
        for name, component in report.components.items():
            assert component.name == name
            assert isinstance(component.status, HealthStatus)
            assert isinstance(component.timestamp, datetime)
    
    def test_metrics_and_health_together(self):
        """Test metrics and health systems work together"""
        metrics = Cell0Metrics()
        checker = HealthChecker()
        
        # Both should be independently functional
        assert metrics is not None
        assert checker is not None


# =============================================================================
# Performance Tests
# =============================================================================

class TestMonitoringPerformance:
    """Performance tests for monitoring"""
    
    @pytest.mark.asyncio
    async def test_health_check_performance(self):
        """Test health check completes within reasonable time"""
        checker = HealthChecker()
        
        # Register fast check
        async def fast_check():
            return ComponentHealth("fast", HealthStatus.HEALTHY)
        
        checker.register_check("fast1", fast_check)
        checker.register_check("fast2", fast_check)
        checker.register_check("fast3", fast_check)
        
        start = time.time()
        await checker.check_all()
        elapsed = time.time() - start
        
        # Should complete in under 1 second for simple checks
        assert elapsed < 1.0
    
    def test_metrics_recording_overhead(self):
        """Test metrics recording has minimal overhead"""
        metrics = Cell0Metrics()
        
        iterations = 1000
        
        start = time.time()
        for _ in range(iterations):
            metrics.api_requests_total.labels(
                method="GET",
                endpoint="/test",
                status="success"
            ).inc()
        elapsed = time.time() - start
        
        # Should handle 1000 operations quickly
        assert elapsed < 1.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
