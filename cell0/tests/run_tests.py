"""
Cell 0 OS - Automated Test Runner

CI Pipeline for running all tests with coverage reporting.

Usage:
    # Run all tests
    python tests/run_tests.py
    
    # Run specific categories
    python tests/run_tests.py --category unit
    python tests/run_tests.py --category integration
    python tests/run_tests.py --category security
    
    # Run with coverage
    python tests/run_tests.py --coverage
    
    # Generate HTML report
    python tests/run_tests.py --coverage --html-report
    
    # Run performance tests
    python tests/run_tests.py --performance
    
    # Run continuous testing (watch mode)
    python tests/run_tests.py --watch

Exit Codes:
    0 - All tests passed
    1 - Some tests failed
    2 - Critical security issues found
    3 - Configuration error
"""

import os
import sys
import time
import json
import argparse
import subprocess
import asyncio
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional

# Configuration
PROJECT_ROOT = Path(__file__).parent.parent
TESTS_DIR = PROJECT_ROOT / "tests"
REPORTS_DIR = TESTS_DIR / "test-reports"
COVERAGE_DIR = REPORTS_DIR / "coverage"

# Test categories
TEST_CATEGORIES = {
    "unit": TESTS_DIR / "unit",
    "integration": TESTS_DIR / "integration",
    "security": TESTS_DIR / "security",
    "performance": TESTS_DIR / "performance",
}

# Exit codes
EXIT_SUCCESS = 0
EXIT_TESTS_FAILED = 1
EXIT_SECURITY_CRITICAL = 2
EXIT_CONFIG_ERROR = 3


class TestRunner:
    """Cell 0 OS Test Runner"""
    
    def __init__(self, verbose: bool = False, fail_fast: bool = False):
        self.verbose = verbose
        self.fail_fast = fail_fast
        self.results: List[Dict[str, Any]] = []
        self.start_time: Optional[float] = None
        
        # Ensure report directories exist
        REPORTS_DIR.mkdir(parents=True, exist_ok=True)
        COVERAGE_DIR.mkdir(parents=True, exist_ok=True)
    
    def log(self, message: str, level: str = "info"):
        """Log a message"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        prefix = f"[{timestamp}]"
        
        if level == "error":
            print(f"{prefix} ❌ {message}", file=sys.stderr)
        elif level == "warning":
            print(f"{prefix} ⚠️  {message}")
        elif level == "success":
            print(f"{prefix} ✅ {message}")
        elif level == "info":
            print(f"{prefix} ℹ️  {message}")
        elif level == "header":
            print(f"\n{prefix} {'='*60}")
            print(f"{prefix} {message}")
            print(f"{prefix} {'='*60}")
    
    def run_command(self, cmd: List[str], cwd: Optional[Path] = None) -> subprocess.CompletedProcess:
        """Run a shell command"""
        if self.verbose:
            self.log(f"Running: {' '.join(cmd)}")
        
        result = subprocess.run(
            cmd,
            cwd=cwd or PROJECT_ROOT,
            capture_output=True,
            text=True
        )
        
        return result
    
    def check_dependencies(self) -> bool:
        """Check if required dependencies are installed"""
        self.log("Checking dependencies...", "header")
        
        required = ["pytest", "pytest-asyncio"]
        optional = ["pytest-cov", "pytest-html", "locust"]
        
        all_ok = True
        
        for package in required:
            result = self.run_command([sys.executable, "-m", "pip", "show", package])
            if result.returncode != 0:
                self.log(f"Missing required package: {package}", "error")
                all_ok = False
            else:
                self.log(f"Found: {package}", "success")
        
        for package in optional:
            result = self.run_command([sys.executable, "-m", "pip", "show", package])
            if result.returncode != 0:
                self.log(f"Optional package not found: {package}", "warning")
            else:
                self.log(f"Found: {package}", "success")
        
        return all_ok
    
    def run_unit_tests(self, coverage: bool = False) -> Dict[str, Any]:
        """Run unit tests"""
        self.log("Running Unit Tests", "header")
        
        cmd = [
            sys.executable, "-m", "pytest",
            "tests/unit/",
            "-v",
            "--tb=short",
        ]
        
        if coverage:
            cmd.extend([
                "--cov=cell0",
                "--cov-report=term-missing",
                f"--cov-report=html:{COVERAGE_DIR}/unit",
                f"--cov-report=xml:{COVERAGE_DIR}/unit-coverage.xml",
            ])
        
        if self.fail_fast:
            cmd.append("-x")
        
        result = self.run_command(cmd)
        
        return {
            "category": "unit",
            "returncode": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "passed": result.returncode == 0,
        }
    
    def run_integration_tests(self, coverage: bool = False) -> Dict[str, Any]:
        """Run integration tests"""
        self.log("Running Integration Tests", "header")
        
        cmd = [
            sys.executable, "-m", "pytest",
            "tests/integration/",
            "-v",
            "--tb=short",
        ]
        
        if coverage:
            cmd.extend([
                "--cov=cell0",
                "--cov-append",
                "--cov-report=term-missing",
                f"--cov-report=html:{COVERAGE_DIR}/integration",
            ])
        
        if self.fail_fast:
            cmd.append("-x")
        
        result = self.run_command(cmd)
        
        return {
            "category": "integration",
            "returncode": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "passed": result.returncode == 0,
        }
    
    def run_security_tests(self) -> Dict[str, Any]:
        """Run security tests"""
        self.log("Running Security Tests", "header")
        
        cmd = [
            sys.executable, "-m", "pytest",
            "tests/security/",
            "-v",
            "--tb=short",
        ]
        
        if self.fail_fast:
            cmd.append("-x")
        
        result = self.run_command(cmd)
        
        # Check for critical security issues in output
        has_critical = "critical" in result.stdout.lower() or "critical" in result.stderr.lower()
        
        return {
            "category": "security",
            "returncode": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "passed": result.returncode == 0,
            "critical_issues": has_critical,
        }
    
    def run_performance_tests(self, scenario: str = "benchmark") -> Dict[str, Any]:
        """Run performance/load tests"""
        self.log("Running Performance Tests", "header")
        
        locustfile = TESTS_DIR / "performance" / "locustfile.py"
        
        if not locustfile.exists():
            self.log(f"Locustfile not found: {locustfile}", "error")
            return {
                "category": "performance",
                "returncode": 1,
                "stdout": "",
                "stderr": "Locustfile not found",
                "passed": False,
            }
        
        # Run locust in headless mode
        cmd = [
            sys.executable, "-m", "locust",
            "-f", str(locustfile),
            "--headless",
            "-u", "10",  # 10 users
            "-r", "2",   # 2 users/second
            "-t", "30s", # 30 second test
            "--only-summary",
        ]
        
        result = self.run_command(cmd)
        
        return {
            "category": "performance",
            "returncode": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "passed": result.returncode == 0,
        }
    
    def generate_report(self) -> Dict[str, Any]:
        """Generate test report"""
        total_tests = len(self.results)
        passed_tests = sum(1 for r in self.results if r.get("passed", False))
        failed_tests = total_tests - passed_tests
        
        elapsed = time.time() - self.start_time if self.start_time else 0
        
        report = {
            "timestamp": datetime.now().isoformat(),
            "duration_seconds": elapsed,
            "summary": {
                "total": total_tests,
                "passed": passed_tests,
                "failed": failed_tests,
                "success_rate": passed_tests / total_tests if total_tests > 0 else 0,
            },
            "results": self.results,
        }
        
        # Save report to file
        report_file = REPORTS_DIR / f"test-report-{datetime.now().strftime('%Y%m%d-%H%M%S')}.json"
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        self.log(f"Report saved to: {report_file}")
        
        return report
    
    def print_summary(self, report: Dict[str, Any]):
        """Print test summary"""
        print("\n" + "="*60)
        print("TEST SUMMARY")
        print("="*60)
        
        summary = report["summary"]
        print(f"Total Categories: {summary['total']}")
        print(f"Passed: {summary['passed']} ✅")
        print(f"Failed: {summary['failed']} ❌")
        print(f"Success Rate: {summary['success_rate']*100:.1f}%")
        print(f"Duration: {report['duration_seconds']:.2f}s")
        print("="*60)
        
        # Print details for failed tests
        if summary['failed'] > 0:
            print("\nFailed Categories:")
            for result in self.results:
                if not result.get("passed", False):
                    print(f"  ❌ {result['category']}")
                    if result.get("stderr"):
                        # Print last few lines of stderr
                        lines = result["stderr"].strip().split('\n')[-5:]
                        for line in lines:
                            print(f"     {line}")
    
    def run_all(self, categories: List[str], coverage: bool = False, 
                performance: bool = False) -> int:
        """Run all specified tests"""
        self.start_time = time.time()
        
        self.log("Cell 0 OS Test Suite", "header")
        self.log(f"Project Root: {PROJECT_ROOT}")
        self.log(f"Categories: {', '.join(categories)}")
        
        # Check dependencies
        if not self.check_dependencies():
            self.log("Missing required dependencies. Install with: pip install -r requirements-dev.txt", "error")
            return EXIT_CONFIG_ERROR
        
        # Run tests for each category
        for category in categories:
            if category == "unit":
                result = self.run_unit_tests(coverage=coverage)
            elif category == "integration":
                result = self.run_integration_tests(coverage=coverage)
            elif category == "security":
                result = self.run_security_tests()
            elif category == "performance":
                if performance:
                    result = self.run_performance_tests()
                else:
                    self.log("Skipping performance tests (use --performance to run)", "info")
                    continue
            else:
                self.log(f"Unknown category: {category}", "warning")
                continue
            
            self.results.append(result)
            
            if self.fail_fast and not result["passed"]:
                self.log("Fail-fast enabled, stopping tests", "warning")
                break
        
        # Generate and print report
        report = self.generate_report()
        self.print_summary(report)
        
        # Determine exit code
        if any(r.get("critical_issues", False) for r in self.results):
            return EXIT_SECURITY_CRITICAL
        elif not all(r.get("passed", False) for r in self.results):
            return EXIT_TESTS_FAILED
        else:
            return EXIT_SUCCESS


def watch_mode():
    """Run tests in watch mode (continuous)"""
    print("🔍 Watch mode - Press Ctrl+C to stop")
    
    try:
        while True:
            runner = TestRunner(verbose=False)
            exit_code = runner.run_all(
                categories=["unit"],
                coverage=False,
                performance=False
            )
            
            if exit_code == EXIT_SUCCESS:
                print("\n✅ All tests passed - Watching for changes...")
            else:
                print("\n❌ Tests failed - Watching for changes...")
            
            # Wait before re-running
            time.sleep(5)
            
    except KeyboardInterrupt:
        print("\n👋 Stopping watch mode")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Cell 0 OS Test Runner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run_tests.py                    # Run all tests
  python run_tests.py --category unit    # Run only unit tests
  python run_tests.py --coverage         # Run with coverage
  python run_tests.py --watch            # Continuous testing
        """
    )
    
    parser.add_argument(
        "--category",
        choices=list(TEST_CATEGORIES.keys()) + ["all"],
        default="all",
        help="Test category to run"
    )
    parser.add_argument(
        "--coverage",
        action="store_true",
        help="Generate coverage reports"
    )
    parser.add_argument(
        "--performance",
        action="store_true",
        help="Run performance tests"
    )
    parser.add_argument(
        "--watch",
        action="store_true",
        help="Watch mode - continuous testing"
    )
    parser.add_argument(
        "--fail-fast",
        action="store_true",
        help="Stop on first failure"
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Verbose output"
    )
    
    args = parser.parse_args()
    
    # Watch mode
    if args.watch:
        watch_mode()
        return EXIT_SUCCESS
    
    # Determine categories to run
    if args.category == "all":
        categories = ["unit", "integration", "security"]
    else:
        categories = [args.category]
    
    # Run tests
    runner = TestRunner(verbose=args.verbose, fail_fast=args.fail_fast)
    exit_code = runner.run_all(
        categories=categories,
        coverage=args.coverage,
        performance=args.performance
    )
    
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
