"""
Cell 0 OS - Comprehensive Test Suite
=====================================

This package contains the complete test harness for Cell 0 OS:

Structure:
    unit/           - Unit tests for kernel modules
    integration/    - End-to-end daemon tests  
    security/       - Fuzzing and penetration tests
    performance/    - Load tests and benchmarks
    test-reports/   - Test execution reports

Usage:
    # Run all tests
    python -m pytest tests/ -v --cov=cell0 --cov-report=html
    
    # Run specific test categories
    python -m pytest tests/unit/ -v
    python -m pytest tests/integration/ -v
    python -m pytest tests/security/ -v
    
    # Run with load testing
    cd tests/performance && python locustfile.py benchmark
    
    # Generate coverage report
    pytest tests/ --cov=cell0 --cov-report=html --cov-report=xml

Author: Cell 0 Test Harness Agent
"""

import os
import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Test configuration
TEST_CONFIG = {
    "timeout": 30,
    "async_mode": "auto",
    "test_db": ":memory:",
    "mock_external": True,
}

def get_test_config():
    """Get test configuration"""
    return TEST_CONFIG.copy()
