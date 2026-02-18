# Cell 0 OS Test Harness

Comprehensive testing suite for Cell 0 OS including unit tests, integration tests, security tests, and performance benchmarks.

## Structure

```
tests/
├── unit/                    # Unit tests for kernel modules
│   ├── test_monitoring.py   # Health, metrics, logging tests
│   └── test_security.py     # Auth, rate limiting tests
├── integration/             # End-to-end tests
│   └── test_daemon.py       # Daemon API/WebSocket tests
├── security/                # Security tests
│   └── test_security_fuzzing.py  # Fuzzing, injection tests
├── performance/             # Load testing
│   ├── locustfile.py        # Locust load tests
│   └── config.py            # Performance test config
├── test-reports/            # Test output
├── __init__.py              # Test package init
├── conftest.py              # Pytest configuration
└── run_tests.py             # Automated test runner
```

## Quick Start

### Run All Tests
```bash
python tests/run_tests.py
```

### Run Specific Categories
```bash
# Unit tests only
python tests/run_tests.py --category unit

# Integration tests
python tests/run_tests.py --category integration

# Security tests
python tests/run_tests.py --category security
```

### Run with Coverage
```bash
python tests/run_tests.py --coverage
```

### Continuous Testing (Watch Mode)
```bash
python tests/run_tests.py --watch
```

## Running Tests with Pytest

### Run all unit tests
```bash
pytest tests/unit/ -v
```

### Run with coverage
```bash
pytest tests/unit/ --cov=cell0 --cov-report=html
```

### Run specific test file
```bash
pytest tests/unit/test_monitoring.py -v
```

### Run with markers
```bash
# Run only unit tests
pytest -m unit

# Run everything except slow tests
pytest -m "not slow"

# Run integration tests
pytest -m integration
```

## Performance Testing

### Run Load Tests with Locust
```bash
cd tests/performance

# Run benchmark
python locustfile.py benchmark

# Run stress test
python locustfile.py stress

# Run soak test
python locustfile.py soak
```

### Run via Test Runner
```bash
python tests/run_tests.py --performance
```

## Security Testing

### Run Security Scanner
```bash
pytest tests/security/test_security_fuzzing.py -v
```

### Run Bandit Security Linter
```bash
bandit -r cell0/ -ll
```

## CI/CD

### GitHub Actions
Tests run automatically on:
- Push to `main` or `develop`
- Pull requests

### Test Matrix
- Python 3.10, 3.11, 3.12
- Unit tests
- Integration tests
- Security tests
- Code quality checks

### Local CI Simulation
```bash
# Install dependencies
pip install -r requirements-dev.txt

# Run full test suite
python tests/run_tests.py --coverage

# Run code quality checks
black --check cell0/ tests/
isort --check-only cell0/ tests/
flake8 cell0/ tests/
mypy cell0/
```

## Test Reports

Reports are generated in `tests/test-reports/`:
- JSON test results
- HTML coverage reports
- JUnit XML for CI integration

### View Coverage Report
```bash
open tests/test-reports/coverage-html/index.html
```

## Writing Tests

### Unit Test Example
```python
import pytest
from cell0.engine.monitoring.health import HealthStatus, ComponentHealth

class TestHealthStatus:
    def test_health_status_values(self):
        assert HealthStatus.HEALTHY.value == "healthy"
```

### Async Test Example
```python
@pytest.mark.asyncio
async def test_health_check(self):
    checker = HealthChecker()
    report = await checker.check_all()
    assert report.overall == HealthStatus.HEALTHY
```

### Security Test Example
```python
def test_sql_injection_resistance(self):
    payload = "' OR '1'='1"
    # Test that payload doesn't cause injection
```

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | All tests passed |
| 1 | Some tests failed |
| 2 | Critical security issues found |
| 3 | Configuration error |

## Troubleshooting

### Tests Failing to Import
```bash
# Ensure cell0 is in Python path
export PYTHONPATH=/path/to/cell0:$PYTHONPATH
```

### Missing Dependencies
```bash
pip install -r requirements-dev.txt
```

### Port Conflicts in Integration Tests
Edit `tests/integration/test_daemon.py` to use different ports:
```python
TEST_HTTP_PORT = 28800
TEST_WS_PORT = 28801
```

## Contributing

When adding new tests:
1. Place in appropriate category (unit/integration/security)
2. Use descriptive test names
3. Add docstrings explaining what is tested
4. Use fixtures for setup/teardown
5. Mark slow tests with `@pytest.mark.slow`

## Coverage Goals

- Unit tests: >80% coverage
- Integration tests: Core API paths
- Security tests: All input vectors
