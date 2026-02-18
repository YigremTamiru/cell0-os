#!/usr/bin/env python3
"""
Cell 0 OS Installation Verification Script
Tests a fresh installation to ensure everything works correctly.

Usage:
    python scripts/verify_installation.py [--full]
"""

import sys
import os
import subprocess
import json
import time
import argparse
from pathlib import Path
from typing import List, Tuple, Optional

# Colors for output
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    BOLD = '\033[1m'
    END = '\033[0m'

def print_success(msg: str):
    print(f"{Colors.GREEN}✓{Colors.END} {msg}")

def print_error(msg: str):
    print(f"{Colors.RED}✗{Colors.END} {msg}")

def print_warning(msg: str):
    print(f"{Colors.YELLOW}⚠{Colors.END} {msg}")

def print_info(msg: str):
    print(f"{Colors.BLUE}ℹ{Colors.END} {msg}")

def print_section(title: str):
    print(f"\n{Colors.BOLD}{title}{Colors.END}")
    print("=" * 50)

class InstallationVerifier:
    def __init__(self, full_test: bool = False):
        self.full_test = full_test
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.cell0_home = Path(os.environ.get("CELL0_HOME", Path.home() / "cell0"))
        self.state_dir = Path(os.environ.get("CELL0_STATE_DIR", Path.home() / ".cell0"))
        
    def run_command(self, cmd: List[str], capture: bool = True, timeout: int = 30) -> Tuple[int, str, str]:
        """Run a command and return exit code, stdout, stderr"""
        try:
            result = subprocess.run(
                cmd,
                capture_output=capture,
                text=True,
                timeout=timeout
            )
            return result.returncode, result.stdout, result.stderr
        except subprocess.TimeoutExpired:
            return -1, "", "Command timed out"
        except Exception as e:
            return -1, "", str(e)
    
    def test_prerequisites(self) -> bool:
        """Test that all prerequisites are installed"""
        print_section("Testing Prerequisites")
        
        required = [
            ("python3", "--version"),
            ("git", "--version"),
            ("curl", "--version"),
        ]
        
        optional = [
            ("ollama", "--version"),
            ("cargo", "--version"),
            ("redis-cli", "--version"),
        ]
        
        all_good = True
        
        for cmd, arg in required:
            returncode, stdout, _ = self.run_command([cmd, arg])
            if returncode == 0:
                version = stdout.strip().split('\n')[0]
                print_success(f"{cmd}: {version}")
            else:
                print_error(f"{cmd}: not found")
                self.errors.append(f"Missing required dependency: {cmd}")
                all_good = False
        
        for cmd, arg in optional:
            returncode, stdout, _ = self.run_command([cmd, arg])
            if returncode == 0:
                version = stdout.strip().split('\n')[0]
                print_success(f"{cmd}: {version} (optional)")
            else:
                print_warning(f"{cmd}: not found (optional)")
                self.warnings.append(f"Optional dependency missing: {cmd}")
        
        # Check Python version
        returncode, stdout, _ = self.run_command(["python3", "--version"])
        if returncode == 0:
            version_str = stdout.strip().replace("Python ", "")
            major, minor, _ = version_str.split(".")
            if int(major) < 3 or (int(major) == 3 and int(minor) < 9):
                print_error(f"Python {version_str} is too old (need 3.9+)")
                self.errors.append(f"Python version {version_str} < 3.9")
                all_good = False
            else:
                print_success(f"Python version {version_str} meets requirements")
        
        return all_good
    
    def test_installation_structure(self) -> bool:
        """Test that installation directory structure is correct"""
        print_section("Testing Installation Structure")
        
        required_dirs = [
            self.cell0_home,
            self.cell0_home / "cell0",
            self.cell0_home / "config",
            self.cell0_home / "scripts",
        ]
        
        required_files = [
            self.cell0_home / "cell0d.py",
            self.cell0_home / "cell0ctl.py",
            self.cell0_home / "pyproject.toml",
            self.cell0_home / "install.sh",
        ]
        
        all_good = True
        
        for dir_path in required_dirs:
            if dir_path.exists():
                print_success(f"Directory exists: {dir_path}")
            else:
                print_error(f"Directory missing: {dir_path}")
                self.errors.append(f"Missing directory: {dir_path}")
                all_good = False
        
        for file_path in required_files:
            if file_path.exists():
                print_success(f"File exists: {file_path.name}")
            else:
                print_error(f"File missing: {file_path.name}")
                self.errors.append(f"Missing file: {file_path}")
                all_good = False
        
        return all_good
    
    def test_virtual_environment(self) -> bool:
        """Test Python virtual environment"""
        print_section("Testing Virtual Environment")
        
        venv_path = self.cell0_home / "venv"
        
        if not venv_path.exists():
            print_error("Virtual environment not found")
            self.errors.append("Virtual environment missing")
            return False
        
        print_success(f"Virtual environment exists: {venv_path}")
        
        # Test Python in venv
        python_path = venv_path / "bin" / "python"
        if python_path.exists():
            returncode, stdout, _ = self.run_command([str(python_path), "--version"])
            if returncode == 0:
                print_success(f"Venv Python: {stdout.strip()}")
            else:
                print_error("Venv Python not working")
                self.errors.append("Virtual environment Python not functional")
                return False
        
        # Test key packages
        packages = ["cell0", "fastapi", "websockets", "rich"]
        for pkg in packages:
            returncode, _, _ = self.run_command([
                str(python_path), "-c", f"import {pkg.split('-')[0]}"
            ])
            if returncode == 0:
                print_success(f"Package installed: {pkg}")
            else:
                print_error(f"Package missing: {pkg}")
                self.errors.append(f"Missing package: {pkg}")
        
        return True
    
    def test_state_directory(self) -> bool:
        """Test state directory structure"""
        print_section("Testing State Directory")
        
        required_dirs = [
            self.state_dir,
            self.state_dir / "data",
            self.state_dir / "logs",
            self.state_dir / "config",
        ]
        
        all_good = True
        
        for dir_path in required_dirs:
            if dir_path.exists():
                print_success(f"Directory exists: {dir_path}")
            else:
                print_warning(f"Directory missing: {dir_path}")
                self.warnings.append(f"State directory missing: {dir_path}")
        
        return all_good
    
    def test_cli(self) -> bool:
        """Test cell0ctl CLI"""
        print_section("Testing CLI")
        
        cli_path = self.cell0_home / "venv" / "bin" / "cell0ctl"
        if not cli_path.exists():
            cli_path = self.cell0_home / "cell0ctl.py"
        
        # Test version
        returncode, stdout, _ = self.run_command([str(cli_path), "--version"])
        if returncode == 0:
            print_success(f"CLI version: {stdout.strip()}")
        else:
            print_error("CLI version check failed")
            self.errors.append("CLI not working properly")
        
        # Test status (daemon may not be running)
        returncode, stdout, _ = self.run_command([str(cli_path), "status"])
        if returncode in [0, 1]:  # 0 = running, 1 = not running
            print_success("CLI status command works")
        else:
            print_error("CLI status command failed")
            self.errors.append("CLI status command not working")
            return False
        
        return True
    
    def test_daemon_startup(self) -> bool:
        """Test daemon can start"""
        if not self.full_test:
            print_info("Skipping daemon startup test (--full not specified)")
            return True
        
        print_section("Testing Daemon Startup")
        
        daemon_path = self.cell0_home / "venv" / "bin" / "cell0d"
        if not daemon_path.exists():
            daemon_path = self.cell0_home / "cell0d.py"
        
        print_info("Starting daemon...")
        
        # Start daemon in background
        env = os.environ.copy()
        env["CELL0_HOME"] = str(self.cell0_home)
        env["CELL0_STATE_DIR"] = str(self.state_dir)
        env["CELL0_ENV"] = "testing"
        
        try:
            process = subprocess.Popen(
                [str(daemon_path)],
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=str(self.cell0_home)
            )
            
            # Wait for startup
            time.sleep(5)
            
            # Test health endpoint
            returncode, stdout, _ = self.run_command([
                "curl", "-s", "http://localhost:18800/health"
            ], timeout=10)
            
            if returncode == 0:
                try:
                    health = json.loads(stdout)
                    if health.get("status") == "healthy":
                        print_success("Daemon is healthy")
                    else:
                        print_warning(f"Daemon health: {health.get('status')}")
                except json.JSONDecodeError:
                    print_warning("Could not parse health response")
            else:
                print_error("Daemon health check failed")
                self.errors.append("Daemon failed health check")
            
            # Stop daemon
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
            
            print_success("Daemon stopped")
            
        except Exception as e:
            print_error(f"Daemon startup failed: {e}")
            self.errors.append(f"Daemon startup error: {e}")
            return False
        
        return True
    
    def test_services(self) -> bool:
        """Test service files are in place"""
        print_section("Testing Service Configuration")
        
        if sys.platform == "darwin":
            plist_path = Path.home() / "Library/LaunchAgents/io.cell0.daemon.plist"
            if plist_path.exists():
                print_success(f"LaunchAgent exists: {plist_path}")
            else:
                print_warning("LaunchAgent not found")
                self.warnings.append("macOS LaunchAgent not installed")
        
        elif sys.platform.startswith("linux"):
            service_path = Path.home() / ".config/systemd/user/cell0d.service"
            if service_path.exists():
                print_success(f"Systemd service exists: {service_path}")
            else:
                print_warning("Systemd user service not found")
                self.warnings.append("Linux systemd service not installed")
        
        return True
    
    def generate_report(self) -> bool:
        """Generate final report"""
        print_section("Verification Report")
        
        if not self.errors and not self.warnings:
            print_success("All checks passed! Installation is healthy.")
            return True
        
        if self.warnings:
            print_warning(f"{len(self.warnings)} warning(s):")
            for w in self.warnings:
                print(f"  - {w}")
        
        if self.errors:
            print_error(f"{len(self.errors)} error(s) found:")
            for e in self.errors:
                print(f"  - {e}")
            return False
        
        return True
    
    def run_all(self) -> bool:
        """Run all verification tests"""
        print(f"\n{Colors.BOLD}Cell 0 OS Installation Verification{Colors.END}")
        print(f"Cell 0 Home: {self.cell0_home}")
        print(f"State Dir: {self.state_dir}")
        print(f"Full Test: {self.full_test}")
        
        tests = [
            self.test_prerequisites,
            self.test_installation_structure,
            self.test_virtual_environment,
            self.test_state_directory,
            self.test_cli,
            self.test_services,
            self.test_daemon_startup,
        ]
        
        for test in tests:
            try:
                test()
            except Exception as e:
                print_error(f"Test failed with exception: {e}")
                self.errors.append(f"Test exception: {e}")
        
        return self.generate_report()

def main():
    parser = argparse.ArgumentParser(description="Verify Cell 0 OS Installation")
    parser.add_argument("--full", action="store_true", help="Run full tests including daemon startup")
    parser.add_argument("--fix", action="store_true", help="Attempt to fix issues automatically")
    args = parser.parse_args()
    
    verifier = InstallationVerifier(full_test=args.full)
    success = verifier.run_all()
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
