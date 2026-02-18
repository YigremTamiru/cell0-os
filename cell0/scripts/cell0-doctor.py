#!/usr/bin/env python3
"""
Cell 0 Doctor - Comprehensive Diagnostic Tool

A production-ready diagnostic script that checks the health and configuration
of Cell 0 OS installations. Provides detailed reports with fix suggestions
and uses exit codes for automation integration.

Usage:
    python scripts/cell0-doctor.py [options]
    
Options:
    --quick         Run quick checks only (no deep diagnostics)
    --json          Output results as JSON
    --fix           Attempt automatic fixes where possible
    --verbose       Show detailed output
    --report        Generate full report file

Exit Codes:
    0   - All checks passed (healthy)
    1   - Warnings present (functional but attention needed)
    2   - Errors present (not production ready)
    3   - Critical failures (system not functional)
    127 - Doctor script error
"""

import sys
import os
import json
import subprocess
import socket
import asyncio
import platform
import shutil
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum
from datetime import datetime
import traceback

# Add cell0 to path for imports
cell0_root = Path(__file__).parent.parent
sys.path.insert(0, str(cell0_root))


class CheckStatus(Enum):
    """Status levels for health checks."""
    PASS = "pass"
    WARN = "warn"
    ERROR = "error"
    CRITICAL = "critical"
    SKIP = "skip"


@dataclass
class CheckResult:
    """Result of a single health check."""
    name: str
    status: CheckStatus
    message: str
    details: Dict[str, Any] = field(default_factory=dict)
    fix_suggestion: str = ""
    auto_fixable: bool = False


@dataclass
class HealthReport:
    """Complete health report for Cell 0 OS."""
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    hostname: str = field(default_factory=socket.gethostname)
    cell0_version: str = "unknown"
    overall_status: CheckStatus = CheckStatus.PASS
    checks: List[CheckResult] = field(default_factory=list)
    summary: Dict[str, int] = field(default_factory=dict)
    
    def calculate_summary(self) -> None:
        self.summary = {
            "total": len(self.checks),
            "pass": sum(1 for c in self.checks if c.status == CheckStatus.PASS),
            "warn": sum(1 for c in self.checks if c.status == CheckStatus.WARN),
            "error": sum(1 for c in self.checks if c.status == CheckStatus.ERROR),
            "critical": sum(1 for c in self.checks if c.status == CheckStatus.CRITICAL),
            "skip": sum(1 for c in self.checks if c.status == CheckStatus.SKIP),
        }
        if self.summary["critical"] > 0:
            self.overall_status = CheckStatus.CRITICAL
        elif self.summary["error"] > 0:
            self.overall_status = CheckStatus.ERROR
        elif self.summary["warn"] > 0:
            self.overall_status = CheckStatus.WARN
        else:
            self.overall_status = CheckStatus.PASS


class Cell0Doctor:
    """Main diagnostic engine for Cell 0 OS."""
    
    MIN_PYTHON_VERSION = (3, 9)
    RECOMMENDED_PYTHON_VERSION = (3, 11)
    
    REQUIRED_PORTS = {18800: "Cell 0 HTTP API", 18801: "Cell 0 WebSocket Gateway"}
    OPTIONAL_PORTS = {11434: "Ollama", 8080: "Signal CLI", 8765: "Cell 0 WebSocket (legacy)"}
    REQUIRED_DIRS = ["config", "service", "engine", "skills", "docs"]
    REQUIRED_CONFIGS = ["config/tool_profiles.yaml"]
    OPTIONAL_CONFIGS = ["integrations/signal_config.yaml", "integrations/google_chat_config.yaml"]
    
    def __init__(self, cell0_root: Path, verbose: bool = False, quick: bool = False):
        self.cell0_root = cell0_root
        self.verbose = verbose
        self.quick = quick
        self.report = HealthReport()
        
    def run_all_checks(self) -> HealthReport:
        self._check_python_version()
        self._check_virtual_environment()
        self._check_operating_system()
        self._check_directory_structure()
        self._check_config_files()
        self._check_dependencies()
        self._check_port_availability()
        if not self.quick:
            self._check_ollama_service()
            self._check_signal_service()
        self._check_disk_space()
        self._check_memory()
        self._check_permissions()
        if not self.quick:
            self._run_async_checks()
        self.report.calculate_summary()
        return self.report
    
    def _check_python_version(self) -> None:
        current = sys.version_info[:2]
        current_str = f"{current[0]}.{current[1]}"
        
        if current < self.MIN_PYTHON_VERSION:
            status = CheckStatus.CRITICAL
            message = f"Python {current_str} is too old. Minimum required: {self.MIN_PYTHON_VERSION[0]}.{self.MIN_PYTHON_VERSION[1]}"
            fix = "Upgrade Python using pyenv, conda, or your system package manager"
        elif current < self.RECOMMENDED_PYTHON_VERSION:
            status = CheckStatus.WARN
            message = f"Python {current_str} works but {self.RECOMMENDED_PYTHON_VERSION[0]}.{self.RECOMMENDED_PYTHON_VERSION[1]}+ is recommended"
            fix = "Consider upgrading Python for better performance"
        else:
            status = CheckStatus.PASS
            message = f"Python {current_str} is supported"
            fix = ""
            
        self.report.checks.append(CheckResult(
            name="Python Version", status=status, message=message,
            details={"current": current_str}, fix_suggestion=fix, auto_fixable=False
        ))
    
    def _check_virtual_environment(self) -> None:
        in_venv = hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix)
        venv_path = self.cell0_root / "venv"
        
        if in_venv:
            status, msg = CheckStatus.PASS, f"Running in venv: {sys.prefix}"
            fix, auto = "", False
        elif venv_path.exists():
            status, msg = CheckStatus.WARN, "Virtual environment exists but not activated"
            fix = f"source {venv_path}/bin/activate"
            auto = True
        else:
            status, msg = CheckStatus.ERROR, "No virtual environment found"
            fix = "python -m venv venv && source venv/bin/activate && pip install -r requirements.txt"
            auto = False
            
        self.report.checks.append(CheckResult(
            name="Virtual Environment", status=status, message=msg,
            fix_suggestion=fix, auto_fixable=auto
        ))
    
    def _check_operating_system(self) -> None:
        system = platform.system()
        status = CheckStatus.PASS if system in ["Darwin", "Linux"] else CheckStatus.WARN
        self.report.checks.append(CheckResult(
            name="Operating System", status=status,
            message=f"{system} {platform.release()} ({platform.machine()})",
            details={"system": system, "release": platform.release()}
        ))
    
    def _check_directory_structure(self) -> None:
        missing = [d for d in self.REQUIRED_DIRS if not (self.cell0_root / d).exists()]
        if missing:
            self.report.checks.append(CheckResult(
                name="Directory Structure", status=CheckStatus.CRITICAL,
                message=f"Missing: {', '.join(missing)}",
                fix_suggestion="Reinstall Cell 0 OS from source", auto_fixable=False
            ))
        else:
            self.report.checks.append(CheckResult(
                name="Directory Structure", status=CheckStatus.PASS,
                message="All required directories present"
            ))
    
    def _check_config_files(self) -> None:
        missing = [c for c in self.REQUIRED_CONFIGS if not (self.cell0_root / c).exists()]
        if missing:
            self.report.checks.append(CheckResult(
                name="Configuration Files", status=CheckStatus.ERROR,
                message=f"Missing: {', '.join(missing)}",
                fix_suggestion="Restore missing configuration files", auto_fixable=False
            ))
        else:
            self.report.checks.append(CheckResult(
                name="Configuration Files", status=CheckStatus.PASS,
                message="All required configuration files present"
            ))
    
    def _check_dependencies(self) -> None:
        required = ["aiohttp", "websockets", "pyyaml", "pydantic", "httpx", "requests", "rich", "typer"]
        missing = []
        for pkg in required:
            try:
                __import__(pkg.replace("-", "_").lower())
            except ImportError:
                missing.append(pkg)
        
        if missing:
            self.report.checks.append(CheckResult(
                name="Python Dependencies", status=CheckStatus.ERROR,
                message=f"Missing: {', '.join(missing)}",
                fix_suggestion=f"pip install {' '.join(missing)}", auto_fixable=True
            ))
        else:
            self.report.checks.append(CheckResult(
                name="Python Dependencies", status=CheckStatus.PASS,
                message="All required packages installed"
            ))
    
    def _check_port_availability(self) -> None:
        issues = []
        for port, service in {**self.REQUIRED_PORTS, **self.OPTIONAL_PORTS}.items():
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
            if sock.connect_ex(('127.0.0.1', port)) == 0:
                sev = "warn" if port in self.REQUIRED_PORTS else "info"
                issues.append({"port": port, "service": service, "severity": sev})
            sock.close()
        
        status = CheckStatus.WARN if any(i["severity"] == "warn" for i in issues) else CheckStatus.PASS
        self.report.checks.append(CheckResult(
            name="Port Availability", status=status,
            message=f"{len(issues)} port(s) in use" if issues else "All ports available",
            details={"issues": issues},
            fix_suggestion="Stop conflicting services or change port configuration" if issues else ""
        ))
    
    def _check_ollama_service(self) -> None:
        try:
            import urllib.request
            req = urllib.request.Request("http://localhost:11434/api/tags", method="GET")
            try:
                resp = urllib.request.urlopen(req, timeout=5)
                if resp.status == 200:
                    data = json.loads(resp.read().decode())
                    models = [m.get("name") for m in data.get("models", [])]
                    self.report.checks.append(CheckResult(
                        name="Ollama Service", status=CheckStatus.PASS,
                        message=f"Running with {len(models)} model(s)",
                        details={"models": models[:10]}
                    ))
                else:
                    self.report.checks.append(CheckResult(
                        name="Ollama Service", status=CheckStatus.WARN,
                        message=f"Returned status {resp.status}",
                        fix_suggestion="Check Ollama logs: journalctl -u ollama -n 50"
                    ))
            except urllib.error.URLError as e:
                self.report.checks.append(CheckResult(
                    name="Ollama Service", status=CheckStatus.WARN,
                    message="Not accessible",
                    fix_suggestion="Start Ollama: ollama serve"
                ))
        except Exception as e:
            self.report.checks.append(CheckResult(
                name="Ollama Service", status=CheckStatus.SKIP,
                message="Could not check status", details={"error": str(e)}
            ))
    
    def _check_signal_service(self) -> None:
        try:
            import urllib.request
            req = urllib.request.Request("http://localhost:8080/v1/accounts", method="GET")
            try:
                urllib.request.urlopen(req, timeout=3)
                self.report.checks.append(CheckResult(
                    name="Signal CLI Service", status=CheckStatus.PASS,
                    message="REST API accessible"
                ))
            except urllib.error.URLError:
                self.report.checks.append(CheckResult(
                    name="Signal CLI Service", status=CheckStatus.WARN,
                    message="Not accessible (optional)",
                    fix_suggestion="Start Signal CLI container if needed"
                ))
        except Exception:
            pass
    
    def _check_disk_space(self) -> None:
        try:
            stat = shutil.disk_usage(self.cell0_root)
            free_gb = stat.free / (1024**3)
            used_pct = (stat.used / stat.total) * 100
            
            if free_gb < 1:
                status, msg = CheckStatus.CRITICAL, f"Critical: Only {free_gb:.1f}GB free"
            elif free_gb < 5:
                status, msg = CheckStatus.ERROR, f"Low disk: {free_gb:.1f}GB free ({used_pct:.1f}% used)"
            elif free_gb < 10:
                status, msg = CheckStatus.WARN, f"Getting low: {free_gb:.1f}GB free"
            else:
                status, msg = CheckStatus.PASS, f"OK: {free_gb:.1f}GB free"
            
            self.report.checks.append(CheckResult(
                name="Disk Space", status=status, message=msg,
                details={"free_gb": round(free_gb, 2), "used_percent": round(used_pct, 2)},
                fix_suggestion="Free up disk space" if status != CheckStatus.PASS else ""
            ))
        except Exception as e:
            self.report.checks.append(CheckResult(
                name="Disk Space", status=CheckStatus.SKIP,
                message="Could not check", details={"error": str(e)}
            ))
    
    def _check_memory(self) -> None:
        try:
            import psutil
            mem = psutil.virtual_memory()
            avail_gb = mem.available / (1024**3)
            
            if avail_gb < 1:
                status, msg = CheckStatus.ERROR, f"Critical: Only {avail_gb:.1f}GB available"
            elif avail_gb < 4:
                status, msg = CheckStatus.WARN, f"Low: {avail_gb:.1f}GB available"
            else:
                status, msg = CheckStatus.PASS, f"OK: {avail_gb:.1f}GB available"
            
            self.report.checks.append(CheckResult(
                name="System Memory", status=status, message=msg,
                fix_suggestion="Close applications or add RAM" if status != CheckStatus.PASS else ""
            ))
        except ImportError:
            self.report.checks.append(CheckResult(
                name="System Memory", status=CheckStatus.SKIP,
                message="psutil not installed",
                fix_suggestion="pip install psutil"
            ))
    
    def _check_permissions(self) -> None:
        issues = []
        for data_dir in [self.cell0_root / "data", self.cell0_root / "logs"]:
            if data_dir.exists():
                if not os.access(data_dir, os.W_OK):
                    issues.append(str(data_dir))
            else:
                try:
                    data_dir.mkdir(parents=True)
                except PermissionError:
                    issues.append(str(data_dir))
        
        if issues:
            self.report.checks.append(CheckResult(
                name="File Permissions", status=CheckStatus.ERROR,
                message=f"Cannot write to: {', '.join(issues)}",
                fix_suggestion="chown -R $(whoami) data logs", auto_fixable=False
            ))
        else:
            self.report.checks.append(CheckResult(
                name="File Permissions", status=CheckStatus.PASS,
                message="Permissions are correct"
            ))
    
    def _run_async_checks(self) -> None:
        try:
            asyncio.run(self._async_checks())
        except Exception as e:
            self.report.checks.append(CheckResult(
                name="Async Diagnostics", status=CheckStatus.SKIP,
                message="Could not run", details={"error": str(e)}
            ))
    
    async def _async_checks(self) -> None:
        await self._check_websocket()
        await self._check_http_api()
    
    async def _check_websocket(self) -> None:
        try:
            import websockets
            try:
                async with websockets.connect("ws://localhost:18801", timeout=3) as ws:
                    await ws.close()
                self.report.checks.append(CheckResult(
                    name="WebSocket Gateway", status=CheckStatus.PASS,
                    message="Accepting connections"
                ))
            except Exception as e:
                self.report.checks.append(CheckResult(
                    name="WebSocket Gateway", status=CheckStatus.WARN,
                    message="Not accessible", details={"error": str(e)},
                    fix_suggestion="Start Cell 0 services"
                ))
        except ImportError:
            self.report.checks.append(CheckResult(
                name="WebSocket Gateway", status=CheckStatus.SKIP,
                message="websockets not installed"
            ))
    
    async def _check_http_api(self) -> None:
        try:
            import aiohttp
            async with aiohttp.ClientSession() as session:
                try:
                    async with session.get("http://localhost:18800/api/health", timeout=3) as resp:
                        if resp.status == 200:
                            self.report.checks.append(CheckResult(
                                name="HTTP API", status=CheckStatus.PASS,
                                message="Responding"
                            ))
                        else:
                            self.report.checks.append(CheckResult(
                                name="HTTP API", status=CheckStatus.WARN,
                                message=f"Status {resp.status}"
                            ))
                except aiohttp.ClientError as e:
                    self.report.checks.append(CheckResult(
                        name="HTTP API", status=CheckStatus.WARN,
                        message="Not accessible", details={"error": str(e)},
                        fix_suggestion="Start Cell 0 services"
                    ))
        except ImportError:
            self.report.checks.append(CheckResult(
                name="HTTP API", status=CheckStatus.SKIP,
                message="aiohttp not installed"
            ))


def print_report(report: HealthReport) -> None:
    print("\n" + "=" * 70)
    print("Cell 0 OS Health Report".center(70))
    print("=" * 70)
    print(f"Timestamp: {report.timestamp}")
    print(f"Hostname:  {report.hostname}")
    print(f"Status:    {report.overall_status.value.upper()}")
    print("-" * 70)
    print(f"\n📊 Summary: {report.summary['pass']} passed, {report.summary['warn']} warnings, "
          f"{report.summary['error']} errors, {report.summary['critical']} critical")
    
    issues = [c for c in report.checks if c.status in (CheckStatus.ERROR, CheckStatus.CRITICAL)]
    if issues:
        print("\n🔧 Issues found:")
        for issue in issues:
            print(f"  [{issue.status.value.upper()}] {issue.name}: {issue.fix_suggestion}")
    print()


def main() -> int:
    import argparse
    parser = argparse.ArgumentParser(description="Cell 0 Doctor - Diagnostic tool")
    parser.add_argument("--quick", action="store_true", help="Quick checks only")
    parser.add_argument("--json", action="store_true", help="JSON output")
    parser.add_argument("--cell0-root", default=".", help="Cell 0 root directory")
    args = parser.parse_args()
    
    cell0_root = Path(args.cell0_root).resolve()
    if not (cell0_root / "service").exists():
        cell0_root = Path(__file__).parent.parent
    
    doctor = Cell0Doctor(cell0_root=cell0_root, quick=args.quick)
    report = doctor.run_all_checks()
    
    if args.json:
        print(json.dumps({
            "timestamp": report.timestamp,
            "hostname": report.hostname,
            "overall_status": report.overall_status.value,
            "summary": report.summary,
            "checks": [{"name": c.name, "status": c.status.value, "message": c.message,
                       "fix_suggestion": c.fix_suggestion} for c in report.checks]
        }, indent=2))
    else:
        print_report(report)
    
    # Return appropriate exit code
    if report.overall_status == CheckStatus.CRITICAL:
        return 3
    elif report.overall_status == CheckStatus.ERROR:
        return 2
    elif report.overall_status == CheckStatus.WARN:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
